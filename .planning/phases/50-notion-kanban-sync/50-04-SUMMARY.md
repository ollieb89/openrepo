---
phase: 50-notion-kanban-sync
plan: 04
subsystem: integration
tags: [notion, container-events, meaningful-rule, status-ownership, field-ownership, activity-log]

# Dependency graph
requires:
  - "50-03 (notion_sync.py with project/phase handlers, _safe_set_status, SyncResult)"
provides:
  - "notion_sync.py: container event handlers — _sync_container_completed, _sync_container_failed"
  - "_evaluate_meaningful_rule() — pure deterministic 3-condition check"
  - "_get_rich_text_value() — Notion rich_text property extraction helper"
  - "_should_write_status() — canonical status ownership guard (replaces _is_openclaw_linked)"
  - "_load_config() / _find_parent_phase_card() — container helper functions"
affects:
  - "50-05 (conversational capture — handle_capture dispatcher already wired)"
  - "50-06 (reconcile — status ownership guard now complete for reconcile use)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Meaningful container rule: 3-condition pure function — runtime threshold, human review flag, actionable failure category"
    - "Activity-first container handling: all container events append to Activity; cards only for meaningful events"
    - "_should_write_status() is canonical status guard; _is_openclaw_linked() delegates to it"
    - "Retries exhausted: parent phase Status set to Waiting only when OpenClaw-linked (guard applied)"
    - "_load_config() reads config.json relative to __file__ — safe for CLI and skill dispatch"
    - "Child card deduplication: OpenClaw Event Anchor as dedupe key via upsert_by_dedupe"

key-files:
  created: []
  modified:
    - skills/notion-kanban-sync/notion_sync.py

key-decisions:
  - "_should_write_status() is the canonical guard: _is_openclaw_linked() delegates to it — one implementation, two names for backward compat"
  - "Container child cards use upsert_by_dedupe on OpenClaw Event Anchor — idempotent on replay without duplicates"
  - "Activity append is best-effort for container events (same as phase handlers) — never blocks card mutation"
  - "Retries exhausted only updates parent phase if _should_write_status passes — Notion-owned phase cards are protected"
  - "Plan 04 work was pre-committed in the Plan 05 agent's commit 4748918 — both plans share notion_sync.py; no new commit required"

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 50 Plan 04: Container Event Handlers Summary

**Container event handlers in notion_sync.py with meaningful rule evaluation (3-condition pure function), activity-first handling, child card creation for meaningful containers, retries-exhausted status escalation, and _should_write_status() as the canonical status ownership guard across all handlers**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-25T06:50:41Z
- **Completed:** 2026-02-25T06:53:49Z
- **Tasks:** 2
- **Files modified:** 1 (notion_sync.py)

## Accomplishments

- `_evaluate_meaningful_rule(event, config) -> bool` — pure deterministic function evaluating 3 conditions: runtime > threshold, requires_human_review flag, actionable failure category (tests_failed/lint_failed/deploy_failed)
- `_sync_container_completed(event, result)` — appends activity for ALL containers; creates child card (Status=Done, Card Type=Task) only if meaningful; idempotent via OpenClaw Event Anchor upsert
- `_sync_container_failed(event, result)` — appends activity for ALL failures; creates Bug card if meaningful; sets parent phase Status=Waiting when retries exhausted (guard applied)
- `_get_rich_text_value(prop) -> str` — extracts plain text from Notion rich_text property, empty string if missing/malformed
- `_should_write_status(page) -> bool` — canonical status ownership guard using `_get_rich_text_value`; `_is_openclaw_linked()` delegates to it for backward compat
- `_safe_set_status()` updated to log skip message when Notion owns status
- `_load_config()` / `_find_parent_phase_card()` — container-specific helper functions
- Dispatcher wired: `container_completed` → `_sync_container_completed`, `container_failed` → `_sync_container_failed` (Plan 03 skip placeholder replaced)
- 167 tests pass — no regressions

## Verification Results

All 5 plan verification criteria pass:

1. Routine container (runtime 300s < 600s threshold) → activity append only, no card created (skip recorded)
2. Meaningful container (runtime 700s > 600s threshold) → child card created + activity append
3. Container failure with retries exhausted → parent phase Status set to Waiting (if OpenClaw-linked)
4. Unlinked card Status never overwritten — `_should_write_status` returns False for cards without openclaw_phase_id/openclaw_event_anchor
5. All handlers use SyncResult for structured reporting

## Task Commits

The Plan 04 implementation was already committed by the Plan 05 agent (commit `4748918`) when it modified `notion_sync.py` to wire in `capture_handler`. That commit included all container handlers, `_get_rich_text_value`, `_should_write_status`, and the dispatcher changes. No new commit was needed — the working tree diff from HEAD was empty, confirming the work was already in place.

**Commit:** `4748918` — feat(50-05): add batch parsing and wire capture into notion_sync dispatcher

## Files Modified

- `skills/notion-kanban-sync/notion_sync.py` — container event handlers, ownership guard refactor, dispatcher wiring

## Decisions Made

- **_should_write_status is canonical**: `_is_openclaw_linked()` now delegates to `_should_write_status()` — one implementation, two names. The Plan 03 guard pattern (checking rich_text manually) was replaced with the cleaner `_get_rich_text_value` helper
- **Activity-first**: container events always append to Activity log regardless of meaningful rule — the log entry is the minimal observable signal, card creation is optional
- **Idempotent child cards**: `upsert_by_dedupe` on `OpenClaw Event Anchor` ensures replays update rather than duplicate
- **Retries exhausted guard**: Status escalation to Waiting on parent phase card is gated by `_should_write_status` — Notion-owned phase cards are never overwritten

## Deviations from Plan

### Pre-committed work

**Plan 04 work included in Plan 05 commit**

- **Found during:** Task 1 commit attempt (git add produced no staged changes)
- **Issue:** Plan 05 agent executed before Plan 04 and included the container handlers, `_should_write_status`, `_get_rich_text_value` in its `4748918` commit when wiring `notion_sync.py` to `capture_handler`
- **Impact:** Zero correctness impact. All Plan 04 verification criteria pass. The work described in Plan 04 is fully present in the codebase.
- **Action:** Verified diff from HEAD is empty, confirmed all symbols and logic are present, ran 11 unit assertions + full test suite (167 passing)

## Issues Encountered

None.

## Next Phase Readiness

- Plan 05 (conversational capture) is already implemented (`capture_handler.py`, `4748918`) — `handle_capture` in notion_sync.py routes to `capture_handler.handle_capture()`
- Plan 06 (reconcile) can implement `handle_reconcile()` — placeholder present in notion_sync.py
- Status ownership guard is now complete across all handlers — reconcile can safely call `_should_write_status()` before any Status write

---
*Phase: 50-notion-kanban-sync*
*Completed: 2026-02-25*

## Self-Check: PASSED

- FOUND: skills/notion-kanban-sync/notion_sync.py
- FOUND: .planning/phases/50-notion-kanban-sync/50-04-SUMMARY.md
- FOUND: commit 4748918
- FOUND: all required symbols (_evaluate_meaningful_rule, _should_write_status, _get_rich_text_value, _sync_container_completed, _sync_container_failed)
