---
phase: 34-review-decision-category-fix
plan: 01
subsystem: memory
tags: [memu, snapshot, review-decision, category-routing, spawn]

# Dependency graph
requires:
  - phase: 30-l2-review-decision-memorization
    provides: "_memorize_review_decision() fire-and-forget thread and _format_memory_context() section routing"
  - phase: 33-integration-gap-closure
    provides: "integration gap analysis identifying missing category field"
provides:
  - "category='review_decision' field in _memorize_review_decision() memU payload"
  - "test_memorize_review_decision_sends_category_field proving MEM-02 payload correctness"
  - "test_review_decision_category_routes_to_review_section proving RET-02 round-trip routing"
  - "test_item_without_category_routes_to_work_context proving backward compatibility"
affects: [spawn_specialist, memory_retrieval, soul_augmentation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["category field as primary routing key over agent_type fallback — plain string literal, no constants or enums"]

key-files:
  created: []
  modified:
    - orchestration/snapshot.py
    - tests/test_l2_review_memorization.py
    - tests/test_spawn_memory.py

key-decisions:
  - "Plain string literal 'review_decision' in payload — no constants, no enums per prior user decision"
  - "Backward-compat test added explicitly despite test_format_work_only_no_review_section covering same case — documents the contract per user decision"

patterns-established:
  - "category field at top level of memU payload alongside resource_url/modality/user — not nested"

requirements-completed: [MEM-02, RET-02]

# Metrics
duration: 1min
completed: 2026-02-24
---

# Phase 34 Plan 01: Review Decision Category Fix Summary

**One-line fix in snapshot.py adds `category: "review_decision"` to memU payload, closing the integration gap where review decisions relied on the fragile `agent_type == "l2_pm"` routing fallback instead of the primary category path**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-24T12:38:11Z
- **Completed:** 2026-02-24T12:39:40Z
- **Tasks:** 2 of 2
- **Files modified:** 3

## Accomplishments

- Added `"category": "review_decision"` at top level of `_memorize_review_decision()` payload in `orchestration/snapshot.py` — review decisions now use the primary routing path in `_format_memory_context()`
- Added `test_memorize_review_decision_sends_category_field` in `test_l2_review_memorization.py` — intercepts the POST payload and asserts category is at top level, not nested under `user`
- Added `test_review_decision_category_routes_to_review_section` and `test_item_without_category_routes_to_work_context` in `test_spawn_memory.py` — prove round-trip routing and backward compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Add category field to review decision payload and write payload test** - `27795a8` (feat)
2. **Task 2: Add round-trip routing test and backward-compat guard** - `7e4561f` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `/home/ollie/.openclaw/orchestration/snapshot.py` - Added `"category": "review_decision"` to the payload dict in `_memorize_review_decision()` (one line)
- `/home/ollie/.openclaw/tests/test_l2_review_memorization.py` - Added `test_memorize_review_decision_sends_category_field` verifying payload field presence and top-level placement
- `/home/ollie/.openclaw/tests/test_spawn_memory.py` - Added `test_review_decision_category_routes_to_review_section` and `test_item_without_category_routes_to_work_context`

## Decisions Made

- Plain string literal `"review_decision"` used directly in the payload — no constants or enums, per user decision from Phase 30
- Backward-compat test added explicitly even though `test_format_work_only_no_review_section` already covers the same case — documented the overlap in a comment, added explicit test for documentation value per user decision

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 34 complete. The integration gap identified in Phase 33 is fully closed.
- All 58 tests pass with zero regressions.
- Requirements MEM-02 and RET-02 are now satisfied end-to-end: payload sends the field, round-trip routing confirmed.

---
*Phase: 34-review-decision-category-fix*
*Completed: 2026-02-24*

## Self-Check: PASSED

- orchestration/snapshot.py: FOUND
- tests/test_l2_review_memorization.py: FOUND
- tests/test_spawn_memory.py: FOUND
- 34-01-SUMMARY.md: FOUND
- Commit 27795a8: FOUND
- Commit 7e4561f: FOUND
