"""
notion-kanban-sync skill — main entry point.

Dispatches incoming skill requests by request_type:
  - event_sync   : routes event envelopes to project/phase handlers
  - capture      : conversational capture (Plan 05)
  - reconcile    : drift detection (Plan 06)

Usage (CLI):
    python3 notion_sync.py '{"request_type":"event_sync","event":{...}}'

Usage (skill dispatch):
    openclaw agent --skill notion-kanban-sync --payload '{...}'
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level project page ID cache (avoids repeated queries per invocation)
_project_page_id_cache: Dict[str, Optional[str]] = {}

# Fields owned by Notion — OpenClaw NEVER writes these
_NOTION_OWNED_FIELDS = frozenset({"Priority", "Notes", "Target Week"})


# ------------------------------------------------------------------
# Structured result
# ------------------------------------------------------------------

class SyncResult:
    """Structured result tracking mutations, errors, and counts for an invocation."""

    def __init__(self, request_type: str) -> None:
        self.request_type = request_type
        self.created: int = 0
        self.updated: int = 0
        self.skipped: int = 0
        self.errors: List[str] = []
        self.mutations: List[Dict[str, Any]] = []

    def record_mutation(
        self,
        action: str,
        target: str,
        page_id: str,
        dedupe_key: str,
    ) -> None:
        """Record a successful Notion mutation."""
        if action == "created":
            self.created += 1
        elif action == "updated":
            self.updated += 1
        self.mutations.append({
            "action": action,
            "target": target,
            "notion_page_id": page_id,
            "dedupe_key": dedupe_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_skip(self) -> None:
        """Record a skipped mutation (no-op — nothing to update)."""
        self.skipped += 1

    def record_error(self, error_msg: str) -> None:
        """Record a failed mutation."""
        self.errors.append(error_msg)
        logger.error("Notion sync error: %s", error_msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_type": self.request_type,
            "result": {
                "created": self.created,
                "updated": self.updated,
                "skipped": self.skipped,
                "errors": self.errors,
                "mutations": self.mutations,
            },
        }


# ------------------------------------------------------------------
# Notion property formatting helpers
# ------------------------------------------------------------------

def _rich_text(value: str) -> Dict[str, Any]:
    return {"rich_text": [{"text": {"content": value}}]}


def _select(value: str) -> Dict[str, Any]:
    return {"select": {"name": value}}


def _date(iso_str: str) -> Dict[str, Any]:
    return {"date": {"start": iso_str}}


def _title(value: str) -> Dict[str, Any]:
    return {"title": [{"text": {"content": value}}]}


def _url(value: str) -> Dict[str, Any]:
    return {"url": value}


def _relation(page_ids: List[str]) -> Dict[str, Any]:
    return {"relation": [{"id": pid} for pid in page_ids]}


# ------------------------------------------------------------------
# Field ownership guards
# ------------------------------------------------------------------

def _get_rich_text_value(prop: Dict[str, Any]) -> str:
    """Extract plain text from a Notion rich_text property dict.

    Returns an empty string if the property is empty, missing, or malformed.
    """
    parts = prop.get("rich_text", [])
    return "".join(p.get("plain_text", "") for p in parts).strip()


def _is_openclaw_linked(page: Dict[str, Any]) -> bool:
    """Return True if a Cards DB page is managed by OpenClaw.

    OpenClaw owns Status on a card only when the card was created by an
    OpenClaw event — indicated by a non-empty OpenClaw Phase ID or
    OpenClaw Event Anchor property.
    """
    return _should_write_status(page)


def _should_write_status(page: Dict[str, Any]) -> bool:
    """Return True only if OpenClaw owns Status on this card.

    Status ownership rule (SPEC Decision #12):
    - Cards with non-empty OpenClaw Phase ID or OpenClaw Event Anchor
      are OpenClaw-linked → OpenClaw owns Status.
    - All other cards (Conversation-captured, Manual, unlinked) are
      Notion-owned → never write Status.
    """
    props = page.get("properties", {})
    phase_id_value = _get_rich_text_value(props.get("OpenClaw Phase ID", {}))
    if phase_id_value:
        return True
    anchor_value = _get_rich_text_value(props.get("OpenClaw Event Anchor", {}))
    if anchor_value:
        return True
    return False


def _safe_set_status(properties: Dict[str, Any], page: Dict[str, Any], new_status: str) -> Dict[str, Any]:
    """Add Status to properties dict only if OpenClaw owns it for this page.

    If the card is not linked to an OpenClaw event, Status is Notion-owned and
    must not be overwritten. Skipped writes are logged but not counted here —
    callers that need to increment result.skipped must do so explicitly.
    """
    if _should_write_status(page):
        properties["Status"] = _select(new_status)
    else:
        page_id = page.get("id", "<unknown>")
        logger.info("Skipping Status write on Notion-owned card %s", page_id)
    return properties


# ------------------------------------------------------------------
# Project relation lookup (with module-level cache)
# ------------------------------------------------------------------

def _find_project_page_id(client: Any, project_id: str) -> Optional[str]:
    """Query Projects DB for the page matching the given OpenClaw project_id.

    Caches the result in _project_page_id_cache to avoid repeated API calls
    within a single invocation.

    Returns the Notion page_id string, or None if not found.
    """
    if project_id in _project_page_id_cache:
        return _project_page_id_cache[project_id]

    try:
        _, proj_ds_id, _, _ = client._get_db_ids()
        results = client.query_database(proj_ds_id, filter_={
            "property": "OpenClaw ID",
            "rich_text": {"equals": project_id},
        })
        page_id = results[0]["id"] if results else None
        _project_page_id_cache[project_id] = page_id
        return page_id
    except Exception as exc:
        logger.warning("Failed to look up project page for %s: %s", project_id, exc)
        return None


# ------------------------------------------------------------------
# Project event handlers
# ------------------------------------------------------------------

def _sync_project_registered(event: Dict[str, Any], result: SyncResult) -> None:
    """Handle project_registered: upsert Projects DB row + create triage card.

    Field ownership: only OpenClaw-owned fields are written.
    Notion-owned fields (Priority, Notes) are never touched.
    """
    from notion_client import NotionClient  # local import — only when token is set

    project_id = event.get("project_id", "")
    payload = event.get("payload", {})
    project_name = payload.get("name", project_id)
    workspace_path = payload.get("workspace_path", "")
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        client = NotionClient()
        proj_db_id, proj_ds_id, cards_db_id, cards_ds_id = client._get_db_ids()

        # Upsert Projects DB row
        proj_properties: Dict[str, Any] = {
            "Name": _title(project_name),
            "OpenClaw ID": _rich_text(project_id),
            "Type": _select("Dev Project"),
            "Status": _select("Active"),
            "Current Phase": _rich_text(""),
            "Milestone": _rich_text(""),
            "Sync Status": _rich_text(f"OK: project_registered at {now_iso}"),
            "Sync Error": _rich_text(""),
        }
        if workspace_path:
            proj_properties["Repo/Path"] = _url(workspace_path)

        proj_upsert = client.upsert_by_dedupe(
            proj_db_id,
            proj_ds_id,
            "OpenClaw ID",
            project_id,
            proj_properties,
        )
        result.record_mutation(
            proj_upsert["action"],
            "projects_db",
            proj_upsert["page_id"],
            project_id,
        )
        project_page_id = proj_upsert["page_id"]
        # Update cache
        _project_page_id_cache[project_id] = project_page_id

        # Create triage card in Cards DB
        triage_dedupe_key = f"{project_id}:triage"
        triage_properties: Dict[str, Any] = {
            "Name": _title(f"{project_name}: Project setup / triage"),
            "Status": _select("Backlog"),
            "Area": _select("Dev"),
            "Card Type": _select("Task"),
            "Capture Source": _select("OpenClaw Event"),
            "OpenClaw Phase ID": _rich_text(triage_dedupe_key),
            "Last Synced": _date(now_iso),
            "Project": _relation([project_page_id]),
        }
        triage_upsert = client.upsert_by_dedupe(
            cards_db_id,
            cards_ds_id,
            "OpenClaw Phase ID",
            triage_dedupe_key,
            triage_properties,
        )
        result.record_mutation(
            triage_upsert["action"],
            "cards_db",
            triage_upsert["page_id"],
            triage_dedupe_key,
        )

    except Exception as exc:
        result.record_error(f"project_registered ({project_id}): {exc}")


def _sync_project_removed(event: Dict[str, Any], result: SyncResult) -> None:
    """Handle project_removed: set Projects DB row Status to Archived.

    Never deletes — reconcile never deletes per SPEC.
    """
    from notion_client import NotionClient

    project_id = event.get("project_id", "")
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        client = NotionClient()
        _, proj_ds_id, _, _ = client._get_db_ids()

        results = client.query_database(proj_ds_id, filter_={
            "property": "OpenClaw ID",
            "rich_text": {"equals": project_id},
        })
        if not results:
            result.record_skip()
            logger.warning("project_removed: no Projects DB row found for %s", project_id)
            return

        page_id = results[0]["id"]
        client.update_page(page_id, {
            "Status": _select("Archived"),
            "Sync Status": _rich_text(f"Archived at {now_iso}"),
            "Sync Error": _rich_text(""),
        })
        result.record_mutation("updated", "projects_db", page_id, project_id)

    except Exception as exc:
        result.record_error(f"project_removed ({project_id}): {exc}")


# ------------------------------------------------------------------
# Phase event handlers
# ------------------------------------------------------------------

def _sync_phase_started(event: Dict[str, Any], result: SyncResult) -> None:
    """Handle phase_started: upsert phase card (Status=In Progress), update Projects DB."""
    from notion_client import NotionClient

    project_id = event.get("project_id", "")
    phase_id = event.get("phase_id", "")
    payload = event.get("payload", {})
    phase_name = payload.get("phase_name", "")
    dedupe_key = f"{project_id}:{phase_id}"
    now_iso = datetime.now(timezone.utc).isoformat()

    if phase_name:
        card_name = f"Phase {phase_id}: {phase_name}"
    else:
        card_name = f"Phase {phase_id}"

    try:
        client = NotionClient()
        proj_db_id, proj_ds_id, cards_db_id, cards_ds_id = client._get_db_ids()

        # Resolve project page ID for relation
        project_page_id = _find_project_page_id(client, project_id)

        # Build card properties (create path — includes Status and Area)
        card_properties: Dict[str, Any] = {
            "Name": _title(card_name),
            "Status": _select("In Progress"),
            "Area": _select("Dev"),
            "Card Type": _select("Phase"),
            "Capture Source": _select("OpenClaw Event"),
            "OpenClaw Phase ID": _rich_text(dedupe_key),
            "Last Synced": _date(now_iso),
        }
        if project_page_id:
            card_properties["Project"] = _relation([project_page_id])

        # Check if card already exists (for update path — ownership guard)
        existing = client.query_database(cards_ds_id, filter_={
            "property": "OpenClaw Phase ID",
            "rich_text": {"equals": dedupe_key},
        })

        if existing:
            # Update path: apply status ownership guard
            existing_page = existing[0]
            update_props: Dict[str, Any] = {
                "Name": _title(card_name),
                "OpenClaw Phase ID": _rich_text(dedupe_key),
                "Last Synced": _date(now_iso),
            }
            if project_page_id:
                update_props["Project"] = _relation([project_page_id])
            # Status guard: only update if OpenClaw-linked
            update_props = _safe_set_status(update_props, existing_page, "In Progress")
            page = client.update_page(existing_page["id"], update_props)
            page_id = existing_page["id"]
            result.record_mutation("updated", "cards_db", page_id, dedupe_key)
        else:
            # Create path: write all fields including Status (OpenClaw-created)
            page = client.create_page(cards_db_id, card_properties)
            page_id = page["id"]
            result.record_mutation("created", "cards_db", page_id, dedupe_key)

        # Update Projects DB Current Phase + Sync Status
        _update_project_current_phase(client, project_id, proj_db_id, proj_ds_id, card_name, now_iso, result)

        # Append activity
        try:
            client.append_activity(page_id, f"phase_started: Phase {phase_id}")
        except Exception as exc:
            logger.warning("Failed to append activity for phase_started %s: %s", dedupe_key, exc)

    except Exception as exc:
        result.record_error(f"phase_started ({dedupe_key}): {exc}")


def _sync_phase_completed(event: Dict[str, Any], result: SyncResult) -> None:
    """Handle phase_completed: update phase card Status to Done, append activity."""
    from notion_client import NotionClient

    project_id = event.get("project_id", "")
    phase_id = event.get("phase_id", "")
    dedupe_key = f"{project_id}:{phase_id}"
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        client = NotionClient()
        _, _, cards_db_id, cards_ds_id = client._get_db_ids()
        _, proj_ds_id, _, _ = client._get_db_ids()

        existing = client.query_database(cards_ds_id, filter_={
            "property": "OpenClaw Phase ID",
            "rich_text": {"equals": dedupe_key},
        })
        if not existing:
            result.record_skip()
            logger.info("phase_completed: no card found for dedupe_key=%s, skipping", dedupe_key)
            return

        existing_page = existing[0]
        page_id = existing_page["id"]

        update_props: Dict[str, Any] = {
            "Last Synced": _date(now_iso),
        }
        update_props = _safe_set_status(update_props, existing_page, "Done")
        client.update_page(page_id, update_props)
        result.record_mutation("updated", "cards_db", page_id, dedupe_key)

        # Update Projects DB — mark phase as completed
        payload = event.get("payload", {})
        phase_name = payload.get("phase_name", "")
        completed_label = f"Completed: Phase {phase_id}" + (f": {phase_name}" if phase_name else "")
        _update_project_current_phase(client, project_id, None, proj_ds_id, completed_label, now_iso, result)

        # Append activity
        try:
            client.append_activity(page_id, f"phase_completed: Phase {phase_id}")
        except Exception as exc:
            logger.warning("Failed to append activity for phase_completed %s: %s", dedupe_key, exc)

    except Exception as exc:
        result.record_error(f"phase_completed ({dedupe_key}): {exc}")


def _sync_phase_blocked(event: Dict[str, Any], result: SyncResult) -> None:
    """Handle phase_blocked: update phase card Status to Waiting, append blocker to activity."""
    from notion_client import NotionClient

    project_id = event.get("project_id", "")
    phase_id = event.get("phase_id", "")
    payload = event.get("payload", {})
    dedupe_key = f"{project_id}:{phase_id}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Extract blocker details from payload
    blocker_detail = payload.get("blocker", payload.get("reason", f"Phase {phase_id} blocked"))

    try:
        client = NotionClient()
        _, _, _, cards_ds_id = client._get_db_ids()

        existing = client.query_database(cards_ds_id, filter_={
            "property": "OpenClaw Phase ID",
            "rich_text": {"equals": dedupe_key},
        })
        if not existing:
            result.record_skip()
            logger.info("phase_blocked: no card found for dedupe_key=%s, skipping", dedupe_key)
            return

        existing_page = existing[0]
        page_id = existing_page["id"]

        update_props: Dict[str, Any] = {
            "Last Synced": _date(now_iso),
        }
        update_props = _safe_set_status(update_props, existing_page, "Waiting")
        client.update_page(page_id, update_props)
        result.record_mutation("updated", "cards_db", page_id, dedupe_key)

        # Append blocker details to activity
        try:
            client.append_activity(page_id, f"phase_blocked: {blocker_detail}")
        except Exception as exc:
            logger.warning("Failed to append activity for phase_blocked %s: %s", dedupe_key, exc)

    except Exception as exc:
        result.record_error(f"phase_blocked ({dedupe_key}): {exc}")


# ------------------------------------------------------------------
# Projects DB update helper
# ------------------------------------------------------------------

def _update_project_current_phase(
    client: Any,
    project_id: str,
    proj_db_id: Optional[str],
    proj_ds_id: str,
    current_phase_label: str,
    now_iso: str,
    result: SyncResult,
) -> None:
    """Update the Projects DB row's Current Phase and Sync Status fields.

    Non-fatal — errors are recorded but do not stop the caller.
    """
    try:
        proj_results = client.query_database(proj_ds_id, filter_={
            "property": "OpenClaw ID",
            "rich_text": {"equals": project_id},
        })
        if not proj_results:
            logger.info("_update_project_current_phase: no row for project_id=%s", project_id)
            return
        proj_page_id = proj_results[0]["id"]
        client.update_page(proj_page_id, {
            "Current Phase": _rich_text(current_phase_label),
            "Sync Status": _rich_text(f"OK at {now_iso}"),
            "Sync Error": _rich_text(""),
        })
    except Exception as exc:
        logger.warning("Failed to update Projects DB current phase for %s: %s", project_id, exc)
        result.record_error(f"update_project_current_phase ({project_id}): {exc}")


# ------------------------------------------------------------------
# Container event helpers
# ------------------------------------------------------------------

def _load_config() -> Dict[str, Any]:
    """Load skills/notion-kanban-sync/config.json relative to this file.

    Returns an empty dict on failure (degraded mode using defaults).
    """
    import json as _json
    import os as _os
    config_path = _os.path.join(_os.path.dirname(__file__), "config.json")
    try:
        with open(config_path) as fh:
            return _json.load(fh)
    except Exception as exc:
        logger.warning("Failed to load notion-kanban-sync config: %s — using defaults", exc)
        return {}


def _evaluate_meaningful_rule(event: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return True if the container event is 'meaningful' and warrants card creation.

    The meaningful container rule (deterministic, from SPEC Decision #6):
      1. Runtime > meaningful_container_runtime_min minutes (default 10)
      2. requires_human_review is True
      3. failure_category is one of: tests_failed, lint_failed, deploy_failed

    Any single condition being True makes the container meaningful.
    """
    payload = event.get("payload", {})
    runtime_seconds: float = payload.get("runtime_seconds", 0)
    requires_human_review: bool = payload.get("requires_human_review", False)
    failure_category: Optional[str] = payload.get("failure_category")

    meaningful_runtime_min: float = config.get("meaningful_container_runtime_min", 10)
    meaningful_runtime_threshold: float = meaningful_runtime_min * 60  # convert to seconds

    actionable_failures = {"tests_failed", "lint_failed", "deploy_failed"}

    return (
        runtime_seconds > meaningful_runtime_threshold
        or bool(requires_human_review)
        or failure_category in actionable_failures
    )


def _find_parent_phase_card(
    client: Any,
    cards_ds_id: str,
    project_id: str,
    phase_id: str,
) -> Optional[Dict[str, Any]]:
    """Query Cards DB for the parent phase card via openclaw_phase_id dedupe key.

    Returns the Notion page dict, or None if not found.
    Logs a warning for orphan container events (no parent phase card).
    """
    dedupe_key = f"{project_id}:{phase_id}"
    try:
        results = client.query_database(cards_ds_id, filter_={
            "property": "OpenClaw Phase ID",
            "rich_text": {"equals": dedupe_key},
        })
        if not results:
            logger.warning(
                "_find_parent_phase_card: no card found for dedupe_key=%s — orphan container event",
                dedupe_key,
            )
            return None
        return results[0]
    except Exception as exc:
        logger.warning("_find_parent_phase_card: query failed for %s: %s", dedupe_key, exc)
        return None


# ------------------------------------------------------------------
# Container event handlers
# ------------------------------------------------------------------

def _sync_container_completed(event: Dict[str, Any], result: SyncResult) -> None:
    """Handle container_completed events.

    Meaningful rule evaluation:
    - Routine container (rule not met): append to parent phase card Activity only
    - Meaningful container (rule met): create child card + append to Activity

    Always appends to parent phase card Activity regardless of meaningful rule.
    """
    from notion_client import NotionClient  # local import — only when token is set

    project_id = event.get("project_id", "")
    phase_id = event.get("phase_id", "")
    container_id = event.get("container_id", "")
    payload = event.get("payload", {})
    runtime_seconds: int = payload.get("runtime_seconds", 0)
    now_iso = datetime.now(timezone.utc).isoformat()

    config = _load_config()

    try:
        client = NotionClient()
        cards_db_id, _, cards_ds_id, _ = client._get_db_ids()

        # Find parent phase card
        parent_card = _find_parent_phase_card(client, cards_ds_id, project_id, phase_id)
        if parent_card is None:
            result.record_skip()
            return

        parent_page_id = parent_card["id"]

        # Evaluate meaningful container rule
        is_meaningful = _evaluate_meaningful_rule(event, config)

        if is_meaningful:
            # Create child card in Cards DB
            event_anchor = f"{project_id}:{container_id}:container_completed"
            project_page_id = _find_project_page_id(client, project_id)

            child_properties: Dict[str, Any] = {
                "Name": _title(f"L3: {container_id} ({runtime_seconds}s)"),
                "Status": _select("Done"),
                "Area": _select("Dev"),
                "Card Type": _select("Task"),
                "Capture Source": _select("OpenClaw Event"),
                "OpenClaw Event Anchor": _rich_text(event_anchor),
                "Last Synced": _date(now_iso),
            }
            if project_page_id:
                child_properties["Project"] = _relation([project_page_id])

            # Use upsert to ensure idempotency on replay
            _, _, cards_db_id_fresh, cards_ds_id_fresh = client._get_db_ids()
            child_upsert = client.upsert_by_dedupe(
                cards_db_id_fresh,
                cards_ds_id_fresh,
                "OpenClaw Event Anchor",
                event_anchor,
                child_properties,
            )
            result.record_mutation(
                child_upsert["action"],
                "cards_db",
                child_upsert["page_id"],
                event_anchor,
            )

        # Always append to parent phase card Activity (best-effort)
        activity_line = f"container_completed: {container_id} ({runtime_seconds}s)"
        try:
            client.append_activity(parent_page_id, activity_line)
        except Exception as exc:
            logger.warning(
                "Failed to append activity for container_completed %s:%s: %s",
                project_id, container_id, exc,
            )

        # If not meaningful and no card was created, record skip
        if not is_meaningful:
            result.record_skip()

    except Exception as exc:
        result.record_error(f"container_completed ({project_id}:{container_id}): {exc}")


def _sync_container_failed(event: Dict[str, Any], result: SyncResult) -> None:
    """Handle container_failed events.

    Meaningful rule evaluation:
    - Routine failure: append failure to parent phase card Activity only
    - Meaningful failure (actionable category): create child card (Status=Waiting, Card Type=Bug)

    Retries exhausted rule:
    - If payload.retry_count >= config.retry_max_attempts: set parent phase card Status to
      Waiting (only if OpenClaw-linked) and append additional activity.

    Always appends to parent phase card Activity regardless of meaningful rule.
    """
    from notion_client import NotionClient  # local import — only when token is set

    project_id = event.get("project_id", "")
    phase_id = event.get("phase_id", "")
    container_id = event.get("container_id", "")
    payload = event.get("payload", {})
    exit_code: int = payload.get("exit_code", 1)
    retry_count: int = payload.get("retry_count", 0)
    now_iso = datetime.now(timezone.utc).isoformat()

    config = _load_config()
    retry_max_attempts: int = config.get("retry_max_attempts", 3)

    try:
        client = NotionClient()
        cards_db_id, _, cards_ds_id, _ = client._get_db_ids()

        # Find parent phase card
        parent_card = _find_parent_phase_card(client, cards_ds_id, project_id, phase_id)
        if parent_card is None:
            result.record_skip()
            return

        parent_page_id = parent_card["id"]

        # Evaluate meaningful container rule
        is_meaningful = _evaluate_meaningful_rule(event, config)

        if is_meaningful:
            # Create child card — failure card uses Bug type
            event_anchor = f"{project_id}:{container_id}:container_failed"
            project_page_id = _find_project_page_id(client, project_id)

            child_properties: Dict[str, Any] = {
                "Name": _title(f"L3: {container_id} failed (exit {exit_code})"),
                "Status": _select("Waiting"),
                "Area": _select("Dev"),
                "Card Type": _select("Bug"),
                "Capture Source": _select("OpenClaw Event"),
                "OpenClaw Event Anchor": _rich_text(event_anchor),
                "Last Synced": _date(now_iso),
            }
            if project_page_id:
                child_properties["Project"] = _relation([project_page_id])

            _, _, cards_db_id_fresh, cards_ds_id_fresh = client._get_db_ids()
            child_upsert = client.upsert_by_dedupe(
                cards_db_id_fresh,
                cards_ds_id_fresh,
                "OpenClaw Event Anchor",
                event_anchor,
                child_properties,
            )
            result.record_mutation(
                child_upsert["action"],
                "cards_db",
                child_upsert["page_id"],
                event_anchor,
            )

        # Always append to parent phase card Activity (best-effort)
        activity_line = f"container_failed: {container_id} (exit {exit_code})"
        try:
            client.append_activity(parent_page_id, activity_line)
        except Exception as exc:
            logger.warning(
                "Failed to append activity for container_failed %s:%s: %s",
                project_id, container_id, exc,
            )

        # Retries exhausted rule — set parent phase Status to Waiting (guard: OpenClaw-linked only)
        if retry_count >= retry_max_attempts:
            update_props: Dict[str, Any] = {
                "Last Synced": _date(now_iso),
            }
            update_props = _safe_set_status(update_props, parent_card, "Waiting")
            if "Status" in update_props:
                # Status was written — guard passed
                client.update_page(parent_page_id, update_props)
                result.record_mutation("updated", "cards_db", parent_page_id, f"{project_id}:{phase_id}")
            else:
                # Guard blocked Status write — still update Last Synced
                client.update_page(parent_page_id, update_props)
                result.record_skip()

            # Append retries-exhausted activity
            try:
                client.append_activity(parent_page_id, "retries exhausted — phase blocked")
            except Exception as exc:
                logger.warning(
                    "Failed to append retries-exhausted activity for %s:%s: %s",
                    project_id, phase_id, exc,
                )
        elif not is_meaningful:
            result.record_skip()

    except Exception as exc:
        result.record_error(f"container_failed ({project_id}:{container_id}): {exc}")


# ------------------------------------------------------------------
# Request dispatchers
# ------------------------------------------------------------------

def handle_event_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route event envelopes to the appropriate handler.

    Accepted event types:
      project_registered, project_removed,
      phase_started, phase_completed, phase_blocked,
      container_completed, container_failed

    Returns a SyncResult dict with created/updated/skipped/errors/mutations.
    """
    result = SyncResult("event_sync")
    event = payload.get("event", {})
    event_type = event.get("event_type", "")

    logger.info("handle_event_sync: event_type=%s", event_type)

    if event_type == "project_registered":
        _sync_project_registered(event, result)
    elif event_type == "project_removed":
        _sync_project_removed(event, result)
    elif event_type == "phase_started":
        _sync_phase_started(event, result)
    elif event_type == "phase_completed":
        _sync_phase_completed(event, result)
    elif event_type == "phase_blocked":
        _sync_phase_blocked(event, result)
    elif event_type == "container_completed":
        _sync_container_completed(event, result)
    elif event_type == "container_failed":
        _sync_container_failed(event, result)
    else:
        logger.warning("handle_event_sync: unknown event_type=%s — skipping", event_type)
        result.record_skip()

    return result.to_dict()


def handle_capture(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle conversational capture requests.

    Routes to capture_handler.handle_capture() which supports:
    - Single cards with keyword-based area inference
    - Batch input (comma/newline/semicolon separated titles)
    - Capture hash deduplication (idempotent replay)
    - Urgency-based status inference

    Returns SyncResult dict with created/updated/skipped/errors/mutations.
    Each mutation includes: title, area, status, area_inferred.
    """
    from capture_handler import handle_capture as _do_capture  # noqa: PLC0415

    result = SyncResult("capture")
    _do_capture(payload, result)
    return result.to_dict()


def handle_reconcile(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle reconcile requests.

    Implemented in Plan 05.
    """
    result = SyncResult("reconcile")
    logger.info("handle_reconcile: reconcile not yet implemented (Plan 05)")
    result.record_skip()
    return result.to_dict()


def main(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point — dispatch by request_type.

    Accepted request_type values: event_sync, capture, reconcile.
    Returns a structured result dict.
    """
    request_type = payload.get("request_type", "")

    if request_type == "event_sync":
        return handle_event_sync(payload)
    elif request_type == "capture":
        return handle_capture(payload)
    elif request_type == "reconcile":
        return handle_reconcile(payload)
    else:
        logger.error("Unknown request_type: %s", request_type)
        result = SyncResult(request_type or "unknown")
        result.record_error(f"Unknown request_type: {request_type!r}")
        return result.to_dict()


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import json
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.load(sys.stdin)
    result = main(payload)
    print(json.dumps(result, indent=2))
