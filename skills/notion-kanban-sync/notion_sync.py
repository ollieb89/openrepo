"""
notion-kanban-sync skill — main entry point.

Dispatches incoming skill requests by request_type:
  - event_sync   : routes event envelopes to project/phase handlers
  - capture      : conversational capture (Plan 04)
  - reconcile    : drift detection (Plan 05)

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

def _is_openclaw_linked(page: Dict[str, Any]) -> bool:
    """Return True if a Cards DB page is managed by OpenClaw.

    OpenClaw owns Status on a card only when the card was created by an
    OpenClaw event — indicated by a non-empty OpenClaw Phase ID or
    OpenClaw Event Anchor property.
    """
    props = page.get("properties", {})

    phase_id_prop = props.get("OpenClaw Phase ID", {})
    phase_id_parts = phase_id_prop.get("rich_text", [])
    phase_id_value = "".join(p.get("plain_text", "") for p in phase_id_parts).strip()
    if phase_id_value:
        return True

    anchor_prop = props.get("OpenClaw Event Anchor", {})
    anchor_parts = anchor_prop.get("rich_text", [])
    anchor_value = "".join(p.get("plain_text", "") for p in anchor_parts).strip()
    if anchor_value:
        return True

    return False


def _safe_set_status(properties: Dict[str, Any], page: Dict[str, Any], new_status: str) -> Dict[str, Any]:
    """Add Status to properties dict only if OpenClaw owns it for this page.

    If the card is not linked to an OpenClaw event, Status is Notion-owned and
    must not be overwritten.
    """
    if _is_openclaw_linked(page):
        properties["Status"] = _select(new_status)
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
# Request dispatchers
# ------------------------------------------------------------------

def handle_event_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route event envelopes to the appropriate handler.

    Accepted event types:
      project_registered, project_removed,
      phase_started, phase_completed, phase_blocked,
      container_completed, container_failed (Plan 04 placeholder)

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
    elif event_type in ("container_completed", "container_failed"):
        # Placeholder — implemented in Plan 04
        logger.info("handle_event_sync: %s handling deferred to Plan 04", event_type)
        result.record_skip()
    else:
        logger.warning("handle_event_sync: unknown event_type=%s — skipping", event_type)
        result.record_skip()

    return result.to_dict()


def handle_capture(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle conversational capture requests.

    Implemented in Plan 04.
    """
    result = SyncResult("capture")
    logger.info("handle_capture: conversational capture not yet implemented (Plan 04)")
    result.record_skip()
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
