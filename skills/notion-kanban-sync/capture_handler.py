"""
Conversational capture handler for the notion-kanban-sync skill.

Converts life-task captures ("remind me to renew gym", "add: file taxes")
into Notion Cards DB entries with:
- Keyword-based area inference
- Capture hash for idempotent deduplication
- Status inference from urgency language
- Batch input parsing (comma/newline/semicolon separated)

Public API:
    handle_capture(payload, result) -> None
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Config loading (reads area_keywords from config.json)
# ------------------------------------------------------------------

def _load_config() -> Dict[str, Any]:
    """Load skill config.json from the same directory as this file."""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# Area inference
# ------------------------------------------------------------------

def _infer_area(title: str, area_keywords: Dict[str, List[str]]) -> Tuple[str, bool]:
    """Infer the life area for a captured title using keyword matching.

    Iterates areas in config order: Health, Finance, Learning, Relationships, Admin.
    First keyword match wins (case-insensitive substring match).

    Returns:
        (area_name, inferred=True) — always inferred=True for this path.
        Falls back to ("Admin", True) when no keywords match.
    """
    lower_title = title.lower()
    for area, keywords in area_keywords.items():
        for keyword in keywords:
            if keyword.lower() in lower_title:
                return area, True
    # Fallback — best guess
    return "Admin", True


# ------------------------------------------------------------------
# Status inference
# ------------------------------------------------------------------

_URGENCY_SIGNALS = frozenset([
    "urgent", "asap", "today", "tomorrow", "this week", "deadline", "now",
])


def _infer_status(title: str) -> str:
    """Infer card Status from urgency language in the title.

    Returns "This Week" if any urgency signal is present, "Backlog" otherwise.
    """
    lower = title.lower()
    for signal in _URGENCY_SIGNALS:
        if signal in lower:
            return "This Week"
    return "Backlog"


# ------------------------------------------------------------------
# Capture hash
# ------------------------------------------------------------------

def _compute_capture_hash(title: str, area: str, target_week: str = "") -> str:
    """Compute a 12-char SHA-256 hash for deduplication.

    Parts: title (normalised) + area (normalised) + optional target_week.
    Keys sorted alphabetically and joined as "key:value|key:value".

    This ensures replaying the same capture request produces the same hash
    and therefore updates the existing card rather than creating a duplicate.
    """
    parts: Dict[str, str] = {
        "area": area.strip().lower(),
        "title": title.strip().lower(),
    }
    if target_week:
        parts["target_week"] = target_week.strip().lower()

    normalized = "|".join(f"{k}:{v}" for k, v in sorted(parts.items()))
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


# ------------------------------------------------------------------
# Batch parsing
# ------------------------------------------------------------------

def _parse_batch(capture: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Split a capture dict into individual items if the title is batch-formatted.

    Detects batch separators:
    - Comma-separated (unless the string looks like a natural sentence with
      punctuation markers like ". ", "? ", "! ")
    - Newline-separated
    - Semicolon-separated

    Each item in the batch inherits the shared area/status/notes from the
    original capture dict but gets its own title.

    Single items return a list of one dict.
    """
    title = capture.get("title", "")

    # Newline-separated (highest priority — unambiguous)
    if "\n" in title:
        titles = [t.strip() for t in title.split("\n") if t.strip()]
    # Semicolon-separated
    elif ";" in title:
        titles = [t.strip() for t in title.split(";") if t.strip()]
    # Comma-separated — only if the title looks like a list, not a sentence
    elif "," in title and not any(c in title for c in [". ", "? ", "! "]):
        titles = [t.strip() for t in title.split(",") if t.strip()]
    else:
        titles = [title]

    items: List[Dict[str, Any]] = []
    for t in titles:
        item = dict(capture)
        item["title"] = t
        items.append(item)
    return items


# ------------------------------------------------------------------
# Single-capture processor
# ------------------------------------------------------------------

def _process_single_capture(capture: Dict[str, Any], result: Any) -> None:
    """Process one capture item: infer area/status, dedupe, create or update card.

    Args:
        capture: Dict with keys: title, area (optional), status (optional),
                 notes (optional), source (optional), target_week (optional).
        result:  SyncResult instance from notion_sync.py.
    """
    from notion_client import NotionClient  # noqa: PLC0415 — token not required at import time

    title = capture.get("title", "").strip()
    if not title:
        logger.warning("_process_single_capture: empty title, skipping")
        result.record_skip()
        return

    explicit_area = capture.get("area", "")
    explicit_status = capture.get("status", "")
    notes_payload = capture.get("notes", "")
    source = capture.get("source", "conversation")
    target_week = capture.get("target_week", "")

    # --- Area resolution ---
    if explicit_area:
        area = explicit_area
        was_inferred = False
    else:
        config = _load_config()
        area_keywords = config.get("area_keywords", {})
        area, was_inferred = _infer_area(title, area_keywords)

    # --- Status resolution ---
    status = explicit_status if explicit_status else _infer_status(title)

    # --- Card Type ---
    card_type = "Task" if area == "Dev" else "Life Task"

    # --- Compute capture hash for dedupe ---
    capture_hash = _compute_capture_hash(title, area, target_week)

    # --- Notes: append "(area inferred)" when inferred ---
    notes_final = notes_payload or ""
    if was_inferred and notes_final:
        notes_final = f"{notes_final} (area inferred)"
    elif was_inferred:
        notes_final = "(area inferred)"

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        client = NotionClient()
        _, _, cards_db_id, cards_ds_id = client._get_db_ids()

        # --- Dedupe: search by capture_hash ---
        existing = client.query_database(cards_ds_id, filter_={
            "property": "Capture Hash",
            "rich_text": {"equals": capture_hash},
        })

        if existing:
            # --- Update path ---
            existing_page = existing[0]
            page_id = existing_page["id"]
            update_props: Dict[str, Any] = {
                "Last Synced": {"date": {"start": now_iso}},
            }

            # Append new notes if provided
            if notes_payload:
                existing_props = existing_page.get("properties", {})
                existing_notes_parts = existing_props.get("Notes", {}).get("rich_text", [])
                existing_notes = "".join(p.get("plain_text", "") for p in existing_notes_parts).strip()
                combined_notes = f"{existing_notes}\n{notes_payload}".strip() if existing_notes else notes_payload
                update_props["Notes"] = {"rich_text": [{"text": {"content": combined_notes[:2000]}}]}

            # Status: only update if explicitly provided AND card is not Notion-owned
            # For capture cards, we wrote the card — they are OpenClaw-linked via Capture Hash.
            # However, if explicit_status is supplied we respect it for update too.
            if explicit_status:
                update_props["Status"] = {"select": {"name": explicit_status}}

            client.update_page(page_id, update_props)
            result.record_mutation("updated", "cards_db", page_id, capture_hash)
            result.mutations[-1].update({
                "title": title,
                "area": area,
                "status": status,
                "area_inferred": was_inferred,
            })
            logger.info(
                "capture updated (dedupe hit): title=%r area=%s status=%s hash=%s",
                title, area, status, capture_hash,
            )

        else:
            # --- Create path ---
            card_properties: Dict[str, Any] = {
                "Name": {"title": [{"text": {"content": title}}]},
                "Status": {"select": {"name": status}},
                "Area": {"select": {"name": area}},
                "Card Type": {"select": {"name": card_type}},
                "Capture Source": {"select": {"name": "Conversation"}},
                "Capture Hash": {"rich_text": [{"text": {"content": capture_hash}}]},
                "Last Synced": {"date": {"start": now_iso}},
            }
            if notes_final:
                card_properties["Notes"] = {"rich_text": [{"text": {"content": notes_final[:2000]}}]}
            if target_week:
                card_properties["Target Week"] = {"date": {"start": target_week}}

            page = client.create_page(cards_db_id, card_properties)
            page_id = page["id"]
            result.record_mutation("created", "cards_db", page_id, capture_hash)
            result.mutations[-1].update({
                "title": title,
                "area": area,
                "status": status,
                "area_inferred": was_inferred,
            })
            logger.info(
                "capture created: title=%r area=%s status=%s inferred=%s hash=%s",
                title, area, status, was_inferred, capture_hash,
            )

    except Exception as exc:
        result.record_error(f"capture ({title!r}): {exc}")
        logger.exception("capture error for title=%r", title)


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def handle_capture(payload: Dict[str, Any], result: Any) -> None:
    """Handle a conversational capture request.

    Supports:
    - Single card: {"capture": {"title": "renew gym", "area": "Health"}}
    - Batch:       {"capture": {"title": "gym, taxes, call mom"}}
    - With notes:  {"capture": {"title": "file taxes", "notes": "by April 15"}}
    - With status: {"capture": {"title": "urgent: dentist appt", "status": "This Week"}}

    Writes results into the shared SyncResult via result.record_mutation()
    and result.record_error().
    """
    capture = payload.get("capture", {})
    items = _parse_batch(capture)
    logger.info("handle_capture: %d item(s) to process", len(items))
    for item in items:
        _process_single_capture(item, result)
