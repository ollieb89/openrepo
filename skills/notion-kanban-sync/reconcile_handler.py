"""
Reconcile handler for the notion-kanban-sync skill.

Detects drift between OpenClaw project state and Notion and applies
corrections-only repairs. Never deletes Notion pages — uses Archived status.

Allowed correction types:
  1. _reconcile_missing_projects   — OpenClaw project not in Notion → create Projects DB row
  2. _reconcile_status_mismatch    — OpenClaw-linked card has wrong Status → correct to match OpenClaw
  3. _reconcile_missing_relations  — Card has OpenClaw Phase ID but no Project relation → backfill
  4. _reconcile_dangling_cards     — Card points to non-existent OpenClaw phase → Archived

NOT allowed:
  - Deleting any Notion page
  - Writing Status on Notion-owned (unlinked) cards
  - Writing Notion-owned fields: Priority, Notes, Target Week

Public API:
    handle_reconcile(payload, result) -> None
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# OpenClaw project state reader
# ------------------------------------------------------------------

def _get_openclaw_root() -> Path:
    """Return the OpenClaw root directory.

    Reads OPENCLAW_ROOT env var first; falls back to ~/.openclaw.
    """
    root = os.environ.get("OPENCLAW_ROOT")
    if root:
        return Path(root)
    return Path.home() / ".openclaw"


def _read_openclaw_projects() -> List[Dict[str, Any]]:
    """Read all OpenClaw project configs from projects/ directory.

    Returns a list of dicts with keys: project_id, name, workspace.
    Projects with missing or unreadable project.json are skipped with a warning.
    """
    root = _get_openclaw_root()
    projects_dir = root / "projects"
    if not projects_dir.exists():
        logger.warning("reconcile: projects dir not found at %s", projects_dir)
        return []

    projects: List[Dict[str, Any]] = []
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        project_json = entry / "project.json"
        if not project_json.exists():
            continue
        try:
            with open(project_json, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            project_id = data.get("id", entry.name)
            projects.append({
                "project_id": project_id,
                "name": data.get("name", project_id),
                "workspace": data.get("workspace", ""),
                "raw": data,
            })
        except Exception as exc:
            logger.warning("reconcile: failed to read %s: %s", project_json, exc)

    logger.info("reconcile: found %d OpenClaw projects", len(projects))
    return projects


def _get_expected_phase_ids_for_project(project_id: str) -> Set[str]:
    """Read ROADMAP.md (if present) and extract phase IDs as dedupe keys.

    Returns a set of "{project_id}:{phase_id}" strings representing phases
    that exist in OpenClaw for this project.

    Falls back to empty set if ROADMAP.md is absent or unreadable.
    Phase IDs are extracted as simple numeric strings from lines like "## Phase 45".
    """
    root = _get_openclaw_root()
    roadmap_path = root / ".planning" / "ROADMAP.md"
    if not roadmap_path.exists():
        return set()

    phase_ids: Set[str] = set()
    try:
        text = roadmap_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            # Match lines like "| 45 |" or "Phase 45" patterns
            # We look for numbers after "Phase " or at start of table rows
            if stripped.startswith("## Phase ") or stripped.startswith("### Phase "):
                parts = stripped.split()
                if len(parts) >= 2:
                    phase_num = parts[-1].rstrip(":")
                    if phase_num.isdigit():
                        phase_ids.add(f"{project_id}:{phase_num}")
            elif stripped.startswith("|"):
                # Table row: extract phase number from first data column
                cells = [c.strip() for c in stripped.split("|")]
                if len(cells) > 2:
                    possible_num = cells[1].strip()
                    if possible_num.isdigit():
                        phase_ids.add(f"{project_id}:{possible_num}")
    except Exception as exc:
        logger.warning("reconcile: failed to parse ROADMAP.md for %s: %s", project_id, exc)

    return phase_ids


# ------------------------------------------------------------------
# Notion property extraction helpers
# ------------------------------------------------------------------

def _get_rich_text_value(prop: Dict[str, Any]) -> str:
    """Extract plain text from a Notion rich_text property dict."""
    parts = prop.get("rich_text", [])
    return "".join(p.get("plain_text", "") for p in parts).strip()


def _get_select_value(prop: Dict[str, Any]) -> str:
    """Extract select value from a Notion select property dict."""
    sel = prop.get("select")
    if not sel:
        return ""
    return sel.get("name", "")


def _get_relation_page_ids(prop: Dict[str, Any]) -> List[str]:
    """Extract page IDs from a Notion relation property dict."""
    relations = prop.get("relation", [])
    return [r.get("id", "") for r in relations if r.get("id")]


# ------------------------------------------------------------------
# Expected status derivation
# ------------------------------------------------------------------

# Maps OpenClaw phase state strings to expected Notion status values
# Currently we use a simple heuristic from card Status — if OpenClaw
# says a phase is "active" (i.e., it's in ROADMAP as current), it should
# be "In Progress". Completed phases should be "Done".
# The reconcile logic reads the existing Notion status and compares against
# expected state from the OpenClaw workspace-state.json if available.

def _get_workspace_phase_statuses(project_id: str) -> Dict[str, str]:
    """Read workspace-state.json for a project and return phase → expected_status map.

    Returns a dict of "{project_id}:{phase_id}" → expected Notion status.
    Falls back to empty dict if state file is not accessible.
    """
    root = _get_openclaw_root()
    # Standard path: <workspace>/.openclaw/<project_id>/workspace-state.json
    # We need the workspace from project.json to find it
    project_json_path = root / "projects" / project_id / "project.json"
    if not project_json_path.exists():
        return {}

    try:
        with open(project_json_path, "r", encoding="utf-8") as fh:
            proj_data = json.load(fh)
        workspace = proj_data.get("workspace", "")
        if not workspace:
            return {}

        state_path = Path(workspace) / ".openclaw" / project_id / "workspace-state.json"
        if not state_path.exists():
            return {}

        with open(state_path, "r", encoding="utf-8") as fh:
            state = json.load(fh)

        phase_statuses: Dict[str, str] = {}
        phases = state.get("phases", {})
        for phase_id, phase_info in phases.items():
            if not isinstance(phase_info, dict):
                continue
            status = phase_info.get("status", "")
            dedupe_key = f"{project_id}:{phase_id}"
            if status == "in_progress":
                phase_statuses[dedupe_key] = "In Progress"
            elif status == "completed":
                phase_statuses[dedupe_key] = "Done"
            elif status == "blocked":
                phase_statuses[dedupe_key] = "Waiting"
            # pending phases: don't force a status — leave as Notion decided

        return phase_statuses

    except Exception as exc:
        logger.debug("reconcile: could not read workspace state for %s: %s", project_id, exc)
        return {}


# ------------------------------------------------------------------
# Correction functions
# ------------------------------------------------------------------

def _reconcile_missing_projects(
    openclaw_projects: List[Dict[str, Any]],
    notion_project_ids: Set[str],
    client: Any,
    proj_db_id: str,
    proj_ds_id: str,
    result: Any,
) -> None:
    """Create Projects DB rows for OpenClaw projects not yet in Notion.

    Only creates the Projects DB row — no triage card (that's event_sync's job).
    """
    from notion_sync import _title, _rich_text, _url, _select  # noqa: PLC0415

    now_iso = datetime.now(timezone.utc).isoformat()
    created_count = 0

    for proj in openclaw_projects:
        project_id = proj["project_id"]
        if project_id in notion_project_ids:
            continue

        logger.info("reconcile: creating missing project row for %s", project_id)
        proj_properties: Dict[str, Any] = {
            "Name": _title(proj["name"]),
            "OpenClaw ID": _rich_text(project_id),
            "Type": _select("Dev Project"),
            "Status": _select("Active"),
            "Current Phase": _rich_text(""),
            "Milestone": _rich_text(""),
            "Sync Status": _rich_text(f"OK: reconcile created at {now_iso}"),
            "Sync Error": _rich_text(""),
        }
        workspace = proj.get("workspace", "")
        if workspace:
            proj_properties["Repo/Path"] = _url(workspace)

        try:
            page = client.create_page(proj_db_id, proj_properties)
            page_id = page["id"]
            result.record_mutation("created", "projects_db", page_id, project_id)
            created_count += 1
        except Exception as exc:
            result.record_error(f"reconcile missing project ({project_id}): {exc}")
            logger.error("reconcile: failed to create project row for %s: %s", project_id, exc)

    if created_count:
        logger.info("reconcile: created %d missing project row(s)", created_count)


def _reconcile_status_mismatch(
    openclaw_projects: List[Dict[str, Any]],
    notion_cards: List[Dict[str, Any]],
    client: Any,
    result: Any,
) -> None:
    """Correct Notion Status on OpenClaw-linked cards where it mismatches OpenClaw state.

    Only writes Status if _should_write_status() returns True (i.e., the card is
    OpenClaw-linked). Never touches Notion-owned cards.
    """
    from notion_sync import _should_write_status, _select  # noqa: PLC0415

    now_iso = datetime.now(timezone.utc).isoformat()

    # Build combined expected status map from all projects
    expected_statuses: Dict[str, str] = {}
    for proj in openclaw_projects:
        project_id = proj["project_id"]
        project_statuses = _get_workspace_phase_statuses(project_id)
        expected_statuses.update(project_statuses)

    if not expected_statuses:
        logger.info("reconcile: no workspace state available — skipping status mismatch check")
        return

    # Build index: dedupe_key → card
    cards_by_dedupe: Dict[str, Dict[str, Any]] = {}
    for card in notion_cards:
        props = card.get("properties", {})
        phase_id_value = _get_rich_text_value(props.get("OpenClaw Phase ID", {}))
        if phase_id_value:
            cards_by_dedupe[phase_id_value] = card

    corrected_count = 0
    for dedupe_key, expected_status in expected_statuses.items():
        card = cards_by_dedupe.get(dedupe_key)
        if card is None:
            # Card doesn't exist in Notion — missing projects handles creation
            continue

        if not _should_write_status(card):
            # Card is Notion-owned — never correct its Status
            continue

        props = card.get("properties", {})
        current_status = _get_select_value(props.get("Status", {}))

        if current_status == expected_status:
            # In sync — no correction needed
            result.record_skip()
            continue

        logger.info(
            "reconcile: status mismatch for %s — Notion=%r expected=%r — correcting",
            dedupe_key, current_status, expected_status,
        )
        try:
            client.update_page(card["id"], {
                "Status": _select(expected_status),
                "Last Synced": {"date": {"start": now_iso}},
            })
            result.record_mutation("updated", "cards_db", card["id"], dedupe_key)
            corrected_count += 1
        except Exception as exc:
            result.record_error(f"reconcile status mismatch ({dedupe_key}): {exc}")
            logger.error("reconcile: failed to correct status for %s: %s", dedupe_key, exc)

    if corrected_count:
        logger.info("reconcile: corrected %d status mismatch(es)", corrected_count)


def _reconcile_missing_relations(
    notion_cards: List[Dict[str, Any]],
    notion_projects_by_id: Dict[str, str],
    client: Any,
    result: Any,
) -> None:
    """Backfill Project relation on cards that have an OpenClaw Phase ID but no Project relation.

    A card is considered to need backfill when:
    - It has a non-empty OpenClaw Phase ID (format: "{project_id}:{phase_id}")
    - Its Project relation is empty
    - The project_id extracted from the Phase ID maps to a known Projects DB page
    """
    from notion_sync import _relation  # noqa: PLC0415

    now_iso = datetime.now(timezone.utc).isoformat()
    backfilled_count = 0

    for card in notion_cards:
        props = card.get("properties", {})
        phase_id_value = _get_rich_text_value(props.get("OpenClaw Phase ID", {}))
        if not phase_id_value or ":" not in phase_id_value:
            continue

        # Extract project_id from dedupe key (format: "project_id:phase_id")
        project_id = phase_id_value.split(":")[0]

        # Check if relation is already set
        current_relation = _get_relation_page_ids(props.get("Project", {}))
        if current_relation:
            # Already has a project relation — no backfill needed
            continue

        # Look up the Projects DB page for this project
        project_page_id = notion_projects_by_id.get(project_id)
        if not project_page_id:
            logger.debug(
                "reconcile missing_relations: no Notion project page for project_id=%s (card %s)",
                project_id, phase_id_value,
            )
            continue

        logger.info(
            "reconcile: backfilling Project relation for card %s → project %s",
            phase_id_value, project_id,
        )
        try:
            client.update_page(card["id"], {
                "Project": _relation([project_page_id]),
                "Last Synced": {"date": {"start": now_iso}},
            })
            result.record_mutation("updated", "cards_db", card["id"], phase_id_value)
            backfilled_count += 1
        except Exception as exc:
            result.record_error(f"reconcile missing relation ({phase_id_value}): {exc}")
            logger.error("reconcile: failed to backfill relation for %s: %s", phase_id_value, exc)

    if backfilled_count:
        logger.info("reconcile: backfilled %d missing relation(s)", backfilled_count)


def _reconcile_dangling_cards(
    notion_cards: List[Dict[str, Any]],
    openclaw_project_ids: Set[str],
    openclaw_phase_keys: Set[str],
    client: Any,
    result: Any,
) -> None:
    """Archive cards whose OpenClaw Phase ID points to a phase that no longer exists.

    A card is dangling when its OpenClaw Phase ID:
    - Contains a project_id that is NOT in the current OpenClaw projects set, OR
    - Contains a dedupe_key that is NOT in the known phase keys

    Uses Archived status — never deletes.
    """
    from notion_sync import _select, _should_write_status  # noqa: PLC0415

    now_iso = datetime.now(timezone.utc).isoformat()
    archived_count = 0

    for card in notion_cards:
        props = card.get("properties", {})
        phase_id_value = _get_rich_text_value(props.get("OpenClaw Phase ID", {}))
        if not phase_id_value or ":" not in phase_id_value:
            # No OpenClaw Phase ID — this is a Notion-owned or capture card, skip
            continue

        project_id = phase_id_value.split(":")[0]

        # Check if this is a dangling reference
        is_dangling = (
            project_id not in openclaw_project_ids
            or (openclaw_phase_keys and phase_id_value not in openclaw_phase_keys)
        )

        if not is_dangling:
            continue

        # Only archive if OpenClaw-linked (redundant since we checked Phase ID, but belt+suspenders)
        if not _should_write_status(card):
            continue

        current_status = _get_select_value(props.get("Status", {}))
        if current_status == "Archived":
            # Already archived
            result.record_skip()
            continue

        logger.info(
            "reconcile: archiving dangling card %s (phase no longer in OpenClaw)",
            phase_id_value,
        )
        try:
            client.update_page(card["id"], {
                "Status": _select("Archived"),
                "Last Synced": {"date": {"start": now_iso}},
            })
            result.record_mutation("updated", "cards_db", card["id"], phase_id_value)
            archived_count += 1
        except Exception as exc:
            result.record_error(f"reconcile dangling card ({phase_id_value}): {exc}")
            logger.error("reconcile: failed to archive dangling card %s: %s", phase_id_value, exc)

    if archived_count:
        logger.info("reconcile: archived %d dangling card(s)", archived_count)


# ------------------------------------------------------------------
# Paginated query helper
# ------------------------------------------------------------------

def _query_all(client: Any, ds_id: str, filter_: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Query all rows from a Notion DB, paginating if needed (>100 results).

    Uses cursor-based pagination following Notion API conventions.
    bulk_mode sleep between pages is handled by client._request().
    """
    results: List[Dict[str, Any]] = []
    start_cursor: Optional[str] = None

    while True:
        payload: Dict[str, Any] = {}
        if filter_:
            payload["filter"] = filter_
        if start_cursor:
            payload["start_cursor"] = start_cursor

        response = client._request("POST", f"/v1/data_sources/{ds_id}/query", json=payload)
        page_results = response.get("results", [])
        results.extend(page_results)

        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")
        if not has_more or not next_cursor:
            break
        start_cursor = next_cursor

    return results


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def handle_reconcile(payload: Dict[str, Any], result: Any) -> None:
    """Run full drift detection and apply corrections.

    Steps:
      1. Read OpenClaw project states from projects/ directory
      2. Fetch all Notion data (Projects DB + active Cards DB)
      3. Build comparison sets
      4. Apply the 4 allowed correction types
      5. Set result.extra with drift report

    Sets client.bulk_mode = True for all API calls (0.35s between requests).
    Always restores bulk_mode = False when done.

    Args:
        payload: The reconcile request dict (may be empty for full reconcile).
        result:  SyncResult instance for recording mutations/errors.
    """
    from notion_client import NotionClient  # noqa: PLC0415 — token not required at import

    logger.info("reconcile: starting drift detection")

    # --- Step 1: Read OpenClaw state ---
    openclaw_projects = _read_openclaw_projects()
    openclaw_project_ids: Set[str] = {p["project_id"] for p in openclaw_projects}

    # Build full set of known phase dedupe keys from workspace-state.json
    openclaw_phase_keys: Set[str] = set()
    for proj in openclaw_projects:
        project_id = proj["project_id"]
        phase_statuses = _get_workspace_phase_statuses(project_id)
        openclaw_phase_keys.update(phase_statuses.keys())
        # Also add from ROADMAP.md for completeness
        roadmap_keys = _get_expected_phase_ids_for_project(project_id)
        openclaw_phase_keys.update(roadmap_keys)

    try:
        client = NotionClient()
        client._bulk_mode = True  # enable inter-request rate-limit sleep

        # --- Step 2: Fetch all Notion data ---
        proj_db_id, proj_ds_id, cards_db_id, cards_ds_id = client._get_db_ids()

        logger.info("reconcile: querying Projects DB (all rows)")
        all_notion_projects = _query_all(client, proj_ds_id)

        logger.info("reconcile: querying Cards DB (active cards)")
        all_notion_cards = _query_all(client, cards_ds_id, filter_={
            "property": "Status",
            "select": {"does_not_equal": "Archived"},
        })

        # --- Step 3: Build comparison sets ---
        # Notion projects indexed by OpenClaw ID property
        notion_project_ids: Set[str] = set()
        notion_projects_by_id: Dict[str, str] = {}  # project_id → Notion page_id
        for page in all_notion_projects:
            props = page.get("properties", {})
            openclaw_id = _get_rich_text_value(props.get("OpenClaw ID", {}))
            if openclaw_id:
                notion_project_ids.add(openclaw_id)
                notion_projects_by_id[openclaw_id] = page["id"]

        logger.info(
            "reconcile: %d OpenClaw projects, %d Notion projects, %d active Notion cards",
            len(openclaw_project_ids), len(notion_project_ids), len(all_notion_cards),
        )

        # Track counts before corrections for drift report
        mutations_before = result.created + result.updated

        # --- Step 4: Apply corrections ---
        logger.info("reconcile: step 1/4 — missing projects")
        _reconcile_missing_projects(
            openclaw_projects,
            notion_project_ids,
            client,
            proj_db_id,
            proj_ds_id,
            result,
        )

        logger.info("reconcile: step 2/4 — status mismatches")
        _reconcile_status_mismatch(
            openclaw_projects,
            all_notion_cards,
            client,
            result,
        )

        logger.info("reconcile: step 3/4 — missing relations")
        _reconcile_missing_relations(
            all_notion_cards,
            notion_projects_by_id,
            client,
            result,
        )

        logger.info("reconcile: step 4/4 — dangling cards")
        _reconcile_dangling_cards(
            all_notion_cards,
            openclaw_project_ids,
            openclaw_phase_keys,
            client,
            result,
        )

        # --- Step 5: Drift report ---
        mutations_after = result.created + result.updated
        corrections_made = mutations_after - mutations_before
        archived_count = sum(
            1 for m in result.mutations
            if m.get("action") == "updated" and m.get("target") == "cards_db"
        )
        in_sync_count = len(all_notion_cards) - corrections_made

        result.extra = {
            "corrections_made": corrections_made,
            "in_sync_count": max(0, in_sync_count),
            "archived_count": archived_count,
        }

        logger.info(
            "reconcile: done — corrections=%d in_sync=%d archived=%d errors=%d",
            corrections_made,
            result.extra["in_sync_count"],
            archived_count,
            len(result.errors),
        )

    except Exception as exc:
        result.record_error(f"reconcile fatal: {exc}")
        logger.exception("reconcile: fatal error during drift detection")

    finally:
        # Always restore bulk_mode regardless of success/failure
        try:
            client._bulk_mode = False  # type: ignore[name-defined]
        except Exception:
            pass
