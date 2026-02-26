---
phase: 41-l1-strategic-suggestions
plan: 01
subsystem: orchestration
tags: [pattern-extraction, keyword-clustering, soul-suggestions, memory-client, asyncio]

# Dependency graph
requires:
  - phase: 26-38-agent-memory
    provides: MemoryClient.retrieve() for querying rejection memories
  - phase: 40-memory-health-monitor
    provides: scan_engine.py stdlib-only module pattern (testable without external deps)
provides:
  - orchestration/suggest.py — pattern extraction engine + CLI entry point
  - tests/test_suggest.py — 11 unit tests for clustering, suppression, schema
  - soul-suggestions.json schema and write protocol (workspace/.openclaw/<project_id>/)
affects: [41-02-api-routes, 41-03-dashboard-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sys.path guard: replace script dir with project root before stdlib imports to prevent orchestration/logging.py shadowing"
    - "Lazy imports in function bodies for testability without full orchestration stack"
    - "Atomic file write: write to .json.tmp then rename to destination"
    - "MAX_CLUSTER_FRACTION filter: discard clusters spanning >50% of corpus as too generic"
    - "Rejection suppression via suppressed_until_count = evidence_count * 2 on rejected entries"

key-files:
  created:
    - orchestration/suggest.py
    - tests/test_suggest.py
  modified: []

key-decisions:
  - "Activity log (workspace-state.json) used as primary corpus; memU as supplementary — engine works even when memU is empty or down"
  - "keyword frequency clustering (stdlib) chosen over embedding-based clustering — no live memU dependency, works on plain text"
  - "sys.path guard added before asyncio import to prevent orchestration/logging.py shadowing stdlib logging in Python 3.14"
  - "suggest.py has zero imports of soul_renderer write functions — structural approval gate enforced at module boundary (ADV-06)"
  - "Suppression fingerprint derived from md5 of keyword so rejected suggestions are matched even after evidence count changes"

patterns-established:
  - "Pattern: stdlib-only extraction engine — no new deps, importable in test env without full orchestration stack"
  - "Pattern: soul-suggestions.json is write-only from suggest.py; soul-override.md is never touched by extraction engine"

requirements-completed: [ADV-01, ADV-02, ADV-03]

# Metrics
duration: 25min
completed: 2026-02-24
---

# Phase 41 Plan 01: Pattern Extraction Engine Summary

**Keyword-frequency clustering engine that queries memU + workspace-state.json activity logs, generates SOUL amendment suggestions with rejection suppression, and writes to soul-suggestions.json — with structural gate preventing soul-override.md writes**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-24T21:50:17Z
- **Completed:** 2026-02-24T21:55:00Z
- **Tasks:** 2
- **Files modified:** 2 created

## Accomplishments

- Pattern extraction engine (`orchestration/suggest.py`) with 11 functions: keyword extraction, memory clustering, suggestion builder, suppression check, activity log loader, async run_extraction pipeline, and CLI entry point
- Dual-corpus approach: activity log entries (primary) merged with memU rejection memories (supplementary) with content-hash deduplication
- Rejection suppression: rejected suggestions track `suppressed_until_count = evidence_count * 2`; re-surface only when new cluster exceeds that count
- Structural approval gate enforced: `suggest.py` imports zero soul_renderer write functions — verified by grep
- 11 unit tests (all passing) covering keyword filtering, cluster threshold, lookback window, generic cluster discard, schema completeness, suppression active/cleared/absent, and fingerprint format

## Task Commits

Each task was committed atomically:

1. **Task 1: Pattern extraction engine** - `c543601` (feat)
2. **Task 2: Unit tests for extraction engine** - `08de164` (test)

## Files Created/Modified

- `orchestration/suggest.py` — Pattern extraction engine + CLI entry point (457 lines)
- `tests/test_suggest.py` — 11 pure unit tests for clustering, suppression, schema (308 lines)

## Decisions Made

- Activity log from `workspace-state.json` used as primary corpus: memU may have sparse rejection data at current project scale (STATE.md blocker note), but the activity log always captures failed/interrupted task entries via Jarvis Protocol.
- `sys.path` guard added before `import asyncio` at module top-level: Python 3.14 was resolving `asyncio → concurrent.futures → logging` to `orchestration/logging.py` instead of stdlib when running `python3 orchestration/suggest.py`. Fixed by replacing the script's directory on `sys.path` with the project root before any stdlib imports.
- Suppression fingerprint uses `hashlib.md5(keyword.encode()).hexdigest()[:6]` — same computation as the suggestion id — so the suppression check can match by id without storing a separate fingerprint field.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed sys.path shadowing causing asyncio ImportError**
- **Found during:** Task 1 verification (`python3 orchestration/suggest.py --help`)
- **Issue:** When run directly, Python adds `orchestration/` to `sys.path[0]`, causing asyncio's transitive `import logging` to resolve to `orchestration/logging.py` instead of stdlib logging.
- **Fix:** Added a `sys.path` guard block before all stdlib imports that replaces `orchestration/` on `sys.path` with the project root directory.
- **Files modified:** `orchestration/suggest.py`
- **Verification:** `python3 orchestration/suggest.py --help` prints usage without error.
- **Committed in:** `c543601` (Task 1 commit)

**2. [Rule 1 - Bug] Fixed contradictory test assertion in test_extract_keywords_filters_stopwords**
- **Found during:** Task 2 test run (2 failures)
- **Issue:** Test asserted `"agent" in result` but `agent` is in `DOMAIN_STOPWORDS` — contradictory.
- **Fix:** Removed the contradictory assertion; kept the correct assertions about `"the"`, `"to"` (length-filtered), and `"complete"` (passes both filters).
- **Files modified:** `tests/test_suggest.py`
- **Committed in:** `08de164` (Task 2 commit)

**3. [Rule 1 - Bug] Fixed test_cluster_memories_threshold failing due to MAX_CLUSTER_FRACTION**
- **Found during:** Task 2 test run
- **Issue:** Test used 7 total memories with 5 containing 'filepath' (71%), exceeding MAX_CLUSTER_FRACTION=0.5 and causing the cluster to be discarded as too generic.
- **Fix:** Added 5 padding memories (unrelated content) to bring total to 12; 'filepath' now spans 5/12 ≈ 42% < 50% threshold.
- **Files modified:** `tests/test_suggest.py`
- **Committed in:** `08de164` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 bugs found during verification)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## Next Phase Readiness

- `orchestration/suggest.py` is complete and CLI-tested; `python3 orchestration/suggest.py --project pumplai --dry-run` returns 0 suggestions gracefully when memU is down
- `soul-suggestions.json` schema established and documented — Plan 02 (API routes) can read/write using the same schema
- The structural gate (suggest.py never imports soul_renderer write functions) is verified and committed

## Self-Check: PASSED

- orchestration/suggest.py: FOUND
- tests/test_suggest.py: FOUND
- 41-01-SUMMARY.md: FOUND
- Commit c543601 (feat: suggest.py): FOUND
- Commit 08de164 (test: test_suggest.py): FOUND

---
*Phase: 41-l1-strategic-suggestions*
*Completed: 2026-02-24*
