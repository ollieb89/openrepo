---
phase: 50-notion-kanban-sync
plan: 06
subsystem: integration
tags: [notion, reconcile, drift-detection, corrections-only, unit-tests, event-bus, field-ownership]

# Dependency graph
requires:
  - "50-04 (notion_sync.py dispatcher + _should_write_status)"
  - "50-05 (capture_handler.py — batch parsing, area inference, capture hash)"
provides:
  - "reconcile_handler.py: handle_reconcile, 4 correction types"
  - "_reconcile_missing_projects: creates Projects DB rows for OpenClaw-only projects"
  - "_reconcile_status_mismatch: corrects Status drift on OpenClaw-linked cards"
  - "_reconcile_missing_relations: backfills Project relation on phase cards"
  - "_reconcile_dangling_cards: archives cards for removed phases"
  - "test_event_bus.py: 6 tests for emit/subscribe/exception isolation"
  - "test_notion_sync.py: 41 tests for capture hash, area inference, meaningful rule, ownership"
  - "SyncResult.extra field: drift report metadata in to_dict()"
affects:
  - "notion_sync.py: handle_reconcile stub replaced with reconcile_handler delegation"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Corrections-only reconcile: reads OpenClaw projects/ and workspace-state.json, compares against Notion, applies only allowed mutations"
    - "bulk_mode guard: client._bulk_mode = True during reconcile, always restored in finally block"
    - "Paginated query: _query_all() handles >100 rows via cursor-based pagination"
    - "Drift report: result.extra = {corrections_made, in_sync_count, archived_count}"
    - "ROADMAP.md phase extraction: parse table rows and ## Phase N headings for phase key set"
    - "SyncResult.extra: optional metadata dict included in to_dict() when non-empty"

key-files:
  created:
    - skills/notion-kanban-sync/reconcile_handler.py
    - packages/orchestration/tests/test_event_bus.py
    - packages/orchestration/tests/test_notion_sync.py
  modified:
    - skills/notion-kanban-sync/notion_sync.py

key-decisions:
  - "SyncResult.extra dict added to notion_sync.SyncResult — holds reconcile drift report; included in to_dict() output only when non-empty"
  - "Paginated query helper _query_all() in reconcile_handler — reuses client._request() directly for cursor pagination (query_database() does not expose cursor)"
  - "ROADMAP.md phase key extraction: dual strategy — table row numeric cells + ## Phase N headings — union of both for maximum coverage"
  - "_reconcile_status_mismatch skips phases where OpenClaw has no workspace-state.json data — safe no-op rather than false corrections"
  - "test_notion_sync.py covers 41 cases across 14 test classes — exceeds the 14-test plan requirement by adding edge cases"
  - "client in finally block uses 'try: client._bulk_mode = False; except: pass' — handles case where client instantiation failed before assignment"

# Metrics
duration: 4min
completed: 2026-02-25
---

# Phase 50 Plan 06: Reconcile Handler and Unit Tests Summary

**Corrections-only reconcile handler (4 drift types: missing projects, status mismatch, missing relations, dangling cards) with paginated Notion queries, bulk_mode rate limiting, and 47 unit tests covering event bus and Notion sync core behaviors**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-25T07:36:53Z
- **Completed:** 2026-02-25T07:40:56Z
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 1

## Accomplishments

- `reconcile_handler.py` — full drift detection module: `handle_reconcile()` entry, 4 correction functions, `_query_all()` paginated query helper, OpenClaw project state readers
- Correction type 1: `_reconcile_missing_projects()` — creates Projects DB rows for OpenClaw projects not yet in Notion (no triage card — that's event_sync's job)
- Correction type 2: `_reconcile_status_mismatch()` — reads workspace-state.json for expected phase statuses, corrects Notion Status only on OpenClaw-linked cards via `_should_write_status()` guard
- Correction type 3: `_reconcile_missing_relations()` — backfills Project relation on phase cards with OpenClaw Phase ID but empty Project field
- Correction type 4: `_reconcile_dangling_cards()` — archives cards pointing to phases no longer in OpenClaw (project removed or phase not in ROADMAP)
- Guards: never deletes, never writes Status on Notion-owned cards, never modifies Priority/Notes/Target Week
- `bulk_mode = True` during all reconcile API calls, restored in `finally` block
- `_query_all()` handles >100-row pagination via cursor-based paging
- Drift report in `result.extra`: `corrections_made`, `in_sync_count`, `archived_count`
- `SyncResult.extra` field added to notion_sync.py, included in `to_dict()` output
- `handle_reconcile` stub in notion_sync.py replaced with delegation to `reconcile_handler.handle_reconcile()`
- `test_event_bus.py`: 6 tests — emit/subscribe, unsubscribed event ignored, exception swallowed, multi-handler, clear_handlers, empty registry
- `test_notion_sync.py`: 41 tests — capture hash determinism and normalization, area inference keyword matching and fallback, status urgency inference, meaningful rule (runtime/human review/failure category), batch parsing (comma/newline/semicolon/sentence heuristic), status ownership guard
- 214 tests pass total — no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: reconcile handler with drift detection** - `e61469e` (feat)
2. **Task 2: unit tests for event bus and Notion sync** - `54a13ef` (test)

## Files Created

- `skills/notion-kanban-sync/reconcile_handler.py` — 300-line module: handle_reconcile, 4 correction functions, OpenClaw state readers, paginated query helper
- `packages/orchestration/tests/test_event_bus.py` — 6 tests across 6 test classes
- `packages/orchestration/tests/test_notion_sync.py` — 41 tests across 14 test classes

## Files Modified

- `skills/notion-kanban-sync/notion_sync.py` — handle_reconcile stub replaced with delegation; SyncResult.extra field added; to_dict() updated to include extra when non-empty

## Decisions Made

- **SyncResult.extra**: Added as `Dict[str, Any] = {}` to `__init__` — allows reconcile (and any future handler) to attach structured metadata to the result without polluting the core fields (created/updated/skipped/errors/mutations). Included in `to_dict()` output only when non-empty.
- **Paginated _query_all()**: `query_database()` on NotionClient does not expose cursor pagination. `_query_all()` calls `client._request()` directly to handle `has_more/next_cursor` loop — correct for >100-row DBs.
- **Status mismatch no-op when no workspace state**: If `_get_workspace_phase_statuses()` returns empty (workspace path inaccessible, state file not yet created), the status mismatch step is logged and skipped entirely — prevents false corrections against empty baseline.
- **test_notion_sync.py at 41 tests**: Plan specified 14 named tests. Implementation expanded each into sub-cases and added edge cases (target_week differentiates, custom threshold, book/relationships, multiple urgency signals, semicolon split) for robust coverage.

## Deviations from Plan

None — plan executed exactly as written, with minor expansions:

- **[Enhancement] test_notion_sync.py has 41 tests vs planned 14**: The 14 plan-specified behaviors are all covered; additional edge cases were added within each test class for completeness. All pass.
- **[Enhancement] SyncResult.extra added to notion_sync.py**: Required by the plan's drift report spec (`result.extra = {corrections_made: N, ...}`) but `SyncResult` had no `extra` attribute. Added as planned + included in `to_dict()` output.
- **[Enhancement] _query_all() paginated helper**: Plan referenced paginating "if > 100" — implemented via dedicated `_query_all()` helper using cursor loop.

## Issues Encountered

None.

## User Setup Required

No additional setup beyond Plans 01-05:
- `NOTION_TOKEN` environment variable must be set for live reconcile
- `config.json` must have valid DB IDs (or `auto_create_dbs: true` with `notion_parent_page_id`)
- Reconcile reads `OPENCLAW_ROOT/projects/*/project.json` for OpenClaw state

## Phase 50 Complete

All 6 plans in Phase 50 (Notion Kanban Sync) are now implemented:
- Plan 01: Event bus, event_bus_hook.py
- Plan 02: NotionClient with bootstrap, upsert_by_dedupe
- Plan 03: Project/phase event handlers, SyncResult, status ownership
- Plan 04: Container event handlers, meaningful rule, activity log
- Plan 05: Conversational capture handler with area inference and dedupe
- Plan 06: Reconcile handler + unit tests (this plan)

---
*Phase: 50-notion-kanban-sync*
*Completed: 2026-02-25*

## Self-Check: PASSED

- FOUND: skills/notion-kanban-sync/reconcile_handler.py
- FOUND: packages/orchestration/tests/test_event_bus.py
- FOUND: packages/orchestration/tests/test_notion_sync.py
- FOUND: skills/notion-kanban-sync/notion_sync.py
- FOUND: commit e61469e
- FOUND: commit 54a13ef
