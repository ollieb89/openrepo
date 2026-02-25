---
phase: 50-notion-kanban-sync
plan: 05
subsystem: integration
tags: [notion, conversational-capture, area-inference, capture-hash, dedupe, batch-parsing]

# Dependency graph
requires:
  - "50-03 (notion_sync.py dispatcher + SyncResult)"
  - "50-02 (NotionClient with upsert_by_dedupe)"
provides:
  - "capture_handler.py: handle_capture, _infer_area, _infer_status, _compute_capture_hash, _parse_batch"
  - "_process_single_capture: Cards DB create/update with capture_hash dedupe"
  - "notion_sync.handle_capture: wired to capture_handler, no longer a stub"
affects:
  - "notion_sync.py: capture dispatch now live (Plan 05)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Capture hash: SHA-256[:12] over sorted key:value pairs (title+area+target_week) for idempotent dedupe"
    - "Area inference: ordered keyword scan over config.area_keywords dict, Admin fallback"
    - "Batch parsing: comma/newline/semicolon split with sentence heuristic guard"
    - "Notes enrichment: '(area inferred)' appended when area was not explicit"
    - "Mutation enrichment: title/area/status/area_inferred added to result.mutations for ClawdiaPrime display"

key-files:
  created:
    - skills/notion-kanban-sync/capture_handler.py
  modified:
    - skills/notion-kanban-sync/notion_sync.py

key-decisions:
  - "_parse_batch sentence heuristic: skips comma-split when '. ', '? ', or '! ' appears — avoids splitting natural sentences"
  - "Status ownership on update: explicit status in payload is respected; no ownership guard needed for capture cards since they are not Notion-owned"
  - "Notes append on update: existing Notes text is read from page properties and combined with new notes payload"
  - "handle_capture in notion_sync.py delegates entirely to capture_handler — no logic duplication"
  - "Admin fallback: unknown title area falls back to Admin (not None/error) per SPEC best-guess policy"
  - "card_type=Task for Dev area, Life Task for all others — consistent with Cards DB schema options"

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 50 Plan 05: Conversational Capture Handler Summary

**capture_handler.py with keyword-based area inference, SHA-256 capture hash deduplication, batch input parsing, urgency status inference, and wired into notion_sync.py dispatcher**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-25T06:50:50Z
- **Completed:** 2026-02-25T06:52:50Z
- **Tasks:** 2
- **Files created:** 1
- **Files modified:** 1

## Accomplishments

- `capture_handler.py` — complete conversational capture module: `handle_capture()` entry, `_parse_batch()`, `_process_single_capture()`, `_infer_area()`, `_infer_status()`, `_compute_capture_hash()`
- `notion_sync.handle_capture()` stub replaced with delegation to `capture_handler.handle_capture()` — capture request_type is now live
- Area inference: keyword scan over `config.area_keywords`, ordered (Health → Finance → Learning → Relationships → Admin), Admin fallback for no-match
- Capture hash: `sha256(sorted key:value pairs)[:12]` — deterministic, replay-safe (NOTION-04)
- Batch parsing: `"gym, taxes, call mom"` → 3 cards; `"\n"`-separated → individual items; sentence heuristic prevents splitting natural-language text
- Dedupe: `query_database` by `Capture Hash` → update existing; no match → create new card
- `(area inferred)` note appended to Cards DB Notes when area was keyword-inferred (not explicit)
- Status field carries `title/area/status/area_inferred` metadata in each mutation for ClawdiaPrime summary messages ("Added 'Renew gym' to Health / This Week")
- 167 existing tests pass — no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: capture_handler.py with area inference, capture hash, and dedupe** - `1c2613f` (feat)
2. **Task 2: batch parsing + notion_sync dispatcher wiring** - `4748918` (feat)

## Files Created

- `skills/notion-kanban-sync/capture_handler.py` — 225-line module: handle_capture, _parse_batch, _process_single_capture, _infer_area, _infer_status, _compute_capture_hash

## Files Modified

- `skills/notion-kanban-sync/notion_sync.py` — handle_capture stub replaced with capture_handler delegation (+14 lines, -6 lines)

## Decisions Made

- **Sentence heuristic in _parse_batch**: Comma-separated titles are only split if the text does NOT contain `. `, `? `, or `! ` — avoids splitting natural sentences like "Go to the gym. Also, pay taxes." This is a conservative heuristic (false negatives over false positives).
- **Status ownership on capture update**: Explicit `status` in the capture payload is written directly; no `_is_openclaw_linked()` ownership guard needed since capture cards are created by OpenClaw (Capture Hash is our ownership marker). Notion-owned fields (Priority, Target Week) are still never written.
- **Admin fallback is always `inferred=True`**: Even if "Admin" happens to match a keyword, the flag is set the same way — consistency over cleverness.
- **card_type=Task for Dev area**: Aligns with existing SPEC — Dev phase cards use "Task", life-area cards use "Life Task".
- **_load_config() called per-invocation in _process_single_capture**: Simple and correct for CLI use; for high-frequency event-driven use, a caller could inject config. Kept simple per YAGNI.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

No additional setup beyond Plans 01-04:
- `NOTION_TOKEN` environment variable must be set
- `skills/notion-kanban-sync/config.json` must have `area_keywords` section (already present with defaults)

## Next Phase Readiness

- Plan 06 can implement `handle_reconcile()` by replacing the stub in `notion_sync.py`
- `capture_handler.py` is standalone — no changes needed to event_bus_hook.py for capture (ClawdiaPrime calls via skill dispatch, not event bus)

---
*Phase: 50-notion-kanban-sync*
*Completed: 2026-02-25*

## Self-Check: PASSED

- FOUND: skills/notion-kanban-sync/capture_handler.py
- FOUND: skills/notion-kanban-sync/notion_sync.py
- FOUND: .planning/phases/50-notion-kanban-sync/50-05-SUMMARY.md
- FOUND: commit 1c2613f
- FOUND: commit 4748918
