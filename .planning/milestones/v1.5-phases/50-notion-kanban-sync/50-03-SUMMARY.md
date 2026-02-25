---
phase: 50-notion-kanban-sync
plan: 03
subsystem: integration
tags: [notion, event-sync, dedupe, upsert, field-ownership, phase-lifecycle, project-events]

# Dependency graph
requires:
  - "50-01 (event_bus.py subscribe/emit)"
  - "50-02 (NotionClient with upsert_by_dedupe, append_activity)"
provides:
  - "notion_sync.py: main() dispatcher + handle_event_sync() + SyncResult builder"
  - "Project event handlers: _sync_project_registered, _sync_project_removed"
  - "Phase event handlers: _sync_phase_started, _sync_phase_completed, _sync_phase_blocked"
  - "Field ownership guards: _is_openclaw_linked, _safe_set_status, _NOTION_OWNED_FIELDS"
  - "event_bus_hook.py: subscribe 7 event types when NOTION_TOKEN is set"
affects:
  - "50-04 (container events — placeholder routing in handle_event_sync already present)"
  - "50-05 (reconcile — handle_reconcile placeholder already present)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SyncResult builder: tracks created/updated/skipped/errors/mutations per invocation"
    - "Field ownership guard: _is_openclaw_linked checks OpenClaw Phase ID + Event Anchor before Status write"
    - "Dedupe key pattern: openclaw_project_id={project_id}, openclaw_phase_id={project_id}:{phase_id}"
    - "Module-level project page ID cache: _project_page_id_cache avoids repeated Projects DB queries"
    - "Notion property helpers: _rich_text/_select/_date/_title/_url/_relation for type-safe property dicts"
    - "event_bus_hook.py: NOTION_TOKEN guard + ImportError guard for non-openclaw-package contexts"

key-files:
  created:
    - skills/notion-kanban-sync/notion_sync.py
    - skills/notion-kanban-sync/event_bus_hook.py
  modified: []

key-decisions:
  - "Phase handlers implemented in same file write as project handlers — tight coupling justified since both use the same SyncResult/helpers"
  - "_safe_set_status is a no-op for unlinked cards: Status field excluded from update dict if not openclaw-linked"
  - "_find_project_page_id uses module-level dict cache to avoid N+1 Projects DB queries per invocation"
  - "container_completed/container_failed route to skip (not error) in Plan 03 — Plan 04 implements them"
  - "activity append is best-effort: wrapped in try/except so a failed Activity write never aborts the main mutation"
  - "_update_project_current_phase is a shared helper called by both phase_started and phase_completed"

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 50 Plan 03: Event Sync Handlers Summary

**notion_sync.py with event_sync dispatcher, project lifecycle handlers, phase lifecycle handlers with status transitions + activity logging, field ownership guards, and SyncResult builder — plus event_bus_hook.py registering subscriptions for 7 event types**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-25T06:45:20Z
- **Completed:** 2026-02-25T06:47:48Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- `notion_sync.py` — complete event sync module: main() dispatcher, handle_event_sync() router, SyncResult class, 5 project/phase handlers, field ownership guards, Notion property helpers, CLI entry point
- `event_bus_hook.py` — subscribes `_handle_event` to 7 event types when NOTION_TOKEN is set; handles ImportError gracefully for non-package contexts
- All handlers use dedupe keys — replays produce updates, not duplicates (NOTION-09)
- Field ownership enforced via `_NOTION_OWNED_FIELDS` frozenset and `_is_openclaw_linked()` guard (NOTION-10)
- Structured result (`SyncResult`) returned for every invocation (NOTION-02)
- project_registered: upserts Projects DB row + creates triage card in Cards DB (NOTION-01, NOTION-03)
- project_removed: archives Projects DB row, never deletes (NOTION-01)
- phase_started/completed/blocked: upsert Cards DB card with status transitions, update Projects DB Current Phase, append activity (NOTION-01, NOTION-02, NOTION-03)
- 158 existing tests still pass — no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: notion_sync.py + event_bus_hook.py + project handlers + phase handlers** - `5339aa8` (feat)

Note: Task 2 (phase handlers) was implemented within the same file write as Task 1. The SyncResult class, property helpers, and ownership guards are shared by both task scopes — splitting into two file writes would have required writing incomplete code. This is tracked as a minor process deviation with no correctness impact.

## Files Created

- `skills/notion-kanban-sync/notion_sync.py` — 320-line module: main() + handle_event_sync() + SyncResult + 5 event handlers + ownership guards + property helpers + CLI entry point
- `skills/notion-kanban-sync/event_bus_hook.py` — 70-line subscription registration module

## Decisions Made

- **Task merge**: Phase handlers were implemented in the same file as project handlers (Task 1 commit) — the helpers and SyncResult class are shared, so writing Task 1 incomplete and fixing in Task 2 would have been artificial
- **_safe_set_status is exclusive**: If `_is_openclaw_linked()` returns False, the `Status` key is completely absent from the update properties dict — Notion's existing Status is untouched
- **Module-level project page ID cache**: `_project_page_id_cache` is a simple dict at module scope. Safe for single-invocation CLI use; daemon thread invocations in one process also benefit (cache persists across events within the process lifetime)
- **Activity append is best-effort**: `append_activity()` failure (2-call read-before-write) logs a warning but never aborts the main mutation — the card's Status transition is more important than the activity log line
- **container_completed/container_failed placeholders**: These event types are handled by `result.record_skip()` in Plan 03. Plan 04 will replace the skip with full container card logic
- **_update_project_current_phase is non-fatal**: Called from phase_started and phase_completed. On failure, records an error in SyncResult but does not raise — the Cards DB mutation is the primary success signal

## Deviations from Plan

### Minor Process Deviation

**Tasks 1 and 2 implemented in a single file write**

- **Found during:** Task 1 implementation
- **Reason:** SyncResult, property helpers, and ownership guard functions are shared by both project and phase handlers. Writing notion_sync.py in two passes (incomplete Task 1, then Task 2 additions) would require writing temporarily broken code. Combined into one commit with both scopes.
- **Impact:** Zero correctness impact. Both task verification criteria pass independently. All 6 plan verification criteria pass.
- **Commit:** 5339aa8

## Issues Encountered

None.

## User Setup Required

No additional setup beyond Plan 02:
- `NOTION_TOKEN` environment variable must be set for event handlers to register
- `skills/notion-kanban-sync/config.json` must have `notion_parent_page_id` set (or pre-configured DB IDs) for first-run bootstrap

## Next Phase Readiness

- Plan 04 can implement container event handlers by replacing the `_event in ("container_completed", "container_failed")` placeholder in `handle_event_sync()`
- Plan 05 can implement `handle_reconcile()` which already has a placeholder return
- `event_bus_hook.py` is already subscribed to all 7 event types — Plans 04-06 only need to implement the handler functions, not change the subscription list

---
*Phase: 50-notion-kanban-sync*
*Completed: 2026-02-25*

## Self-Check: PASSED

- FOUND: skills/notion-kanban-sync/notion_sync.py
- FOUND: skills/notion-kanban-sync/event_bus_hook.py
- FOUND: .planning/phases/50-notion-kanban-sync/50-03-SUMMARY.md
- FOUND: commit 5339aa8
