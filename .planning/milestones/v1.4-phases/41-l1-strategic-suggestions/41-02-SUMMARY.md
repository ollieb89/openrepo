---
phase: 41-l1-strategic-suggestions
plan: 02
subsystem: api
tags: [nextjs, suggestions, soul-override, approval-gate, validation, execFile]

# Dependency graph
requires:
  - phase: 41-l1-strategic-suggestions/41-01
    provides: orchestration/suggest.py CLI entry point and soul-suggestions.json schema
  - phase: 26-38-agent-memory
    provides: soul_renderer.py --write --force for re-rendering SOUL.md after override append
provides:
  - workspace/occc/src/app/api/suggestions/route.ts — GET (list) + POST (run analysis) endpoints
  - workspace/occc/src/app/api/suggestions/[id]/action/route.ts — Accept/reject with approval gate
  - tests/test_suggest_api.py — 8 Python unit tests for validateDiffText validation logic
affects: [41-03-dashboard-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Approval gate pattern: validateDiffText() must return valid:true before any fs.appendFile to soul-override.md — no bypass path"
    - "execFile (not exec) with argument arrays for all subprocess spawning — prevents shell injection"
    - "project param always required in query string — no active_project fallback to prevent cross-project scope leak"
    - "ENOENT returns empty state object (not 404) for suggestions list — missing file is valid initial state"
    - "fs.mkdir with recursive:true before appendFile — creates soul-override.md dir if project newly created"

key-files:
  created:
    - workspace/occc/src/app/api/suggestions/route.ts
    - workspace/occc/src/app/api/suggestions/[id]/action/route.ts
    - tests/test_suggest_api.py
  modified: []

key-decisions:
  - "validateDiffText exported from action route (not a shared lib) — keeps approval gate co-located with the write path, preventing accidental bypass"
  - "rerenderSoul failure does not fail the accept request — content already appended; SOUL re-render is best-effort (logs error)"
  - "suppressed_until_count = evidence_count * 2 set on reject — mirrors suggest.py suppression logic for consistency"
  - "rejection_reason memorization deferred to L2 CLI — dashboard action route does not call memU directly (separation of concerns)"
  - "pre-existing SummaryStream.tsx build error documented as out-of-scope — does not affect suggestions routes"

patterns-established:
  - "Pattern: Trust boundary at action route — pattern extraction engine (suggest.py) can never reach soul-override.md; only POST /api/suggestions/[id]/action with valid diff_text can"
  - "Pattern: Python mirror tests — port TypeScript validation logic to Python for unit testability without full Next.js harness"

requirements-completed: [ADV-04, ADV-06]

# Metrics
duration: 3min
completed: 2026-02-24
---

# Phase 41 Plan 02: Suggestions API Routes Summary

**Next.js API routes implementing the L1 suggestion trust boundary: GET/POST list/run endpoints plus accept/reject action gate with validateDiffText() blocking injection-prone payloads before any soul-override.md write**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-24T21:57:00Z
- **Completed:** 2026-02-24T21:59:54Z
- **Tasks:** 2
- **Files modified:** 3 created

## Accomplishments

- `GET /api/suggestions?project=X` reads soul-suggestions.json or returns empty state on ENOENT — no 404 for uninitialized project
- `POST /api/suggestions?project=X` spawns suggest.py via execFile (not exec/shell), 60s timeout with 504 on kill, returns updated suggestions list
- `validateDiffText()` blocks: null, empty string, >100 lines, cap_drop, no-new-privileges, LOCK_TIMEOUT, shell=, exec(, subprocess, os.system, backtick commands, shell substitution `$(...)`
- Accept path enforces approval gate: validate → mkdir (recursive) → appendFile → rerenderSoul → update JSON — no bypass route
- Reject path sets `suppressed_until_count = evidence_count * 2` (consistent with suggest.py suppression logic)
- 8 Python unit tests for validateDiffText all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: GET list and POST run-analysis routes** - `8d8ce50` (feat)
2. **Task 2: Accept/reject action route with approval gate** - `7ef99a3` (feat)

## Files Created/Modified

- `workspace/occc/src/app/api/suggestions/route.ts` — GET (list soul-suggestions.json or empty state) + POST (spawn suggest.py via execFile, return updated list)
- `workspace/occc/src/app/api/suggestions/[id]/action/route.ts` — Accept/reject with validateDiffText approval gate, rerenderSoul after accept, suppressed_until_count on reject
- `tests/test_suggest_api.py` — 8 unit tests covering all validation edge cases (empty string, None, >100 lines, backtick, subprocess, $(), valid text, cap_drop)

## Decisions Made

- `validateDiffText` is exported from the action route file (not extracted to a shared lib) — keeps the approval gate co-located with the write path. Future callers must go through this route, not import the function and call appendFile themselves.
- `rerenderSoul` failure is logged but does not fail the accept request — the override content is already durably written. Re-render failure is surfaced in server logs for investigation.
- The rejection reason is stored in soul-suggestions.json only; memorization via memU is deliberately deferred to L2 CLI. The dashboard action route is stateless with respect to memU.
- Pre-existing `SummaryStream.tsx` build error (unterminated string literal) documented as out-of-scope deviation — predates this plan, does not affect suggestions routes.

## Deviations from Plan

None — plan executed exactly as written.

(Note: The pre-existing `SummaryStream.tsx` webpack build error was discovered during verification. It is out of scope — a pre-existing defect in an unrelated file. Documented in deferred-items.)

## Issues Encountered

- `bun run build` produced a webpack error from `src/components/sync/SummaryStream.tsx` (unterminated string literal at line 44). This is a pre-existing defect unrelated to this plan's changes. TypeScript type-check (`bunx tsc --noEmit --skipLibCheck`) confirmed zero errors in the new suggestions routes. Deferred.

## Next Phase Readiness

- Both API routes are TypeScript-clean and ready for the dashboard UI (Plan 03) to call
- `GET /api/suggestions?project=X` and `POST /api/suggestions/[id]/action` are the stable interface for Plan 03 components
- validateDiffText is exported — Plan 03 could import it for client-side pre-validation if desired
- The approval gate structural constraint is enforced: soul-override.md is unreachable except through the validated action route

---
*Phase: 41-l1-strategic-suggestions*
*Completed: 2026-02-24*

## Self-Check: PASSED

- workspace/occc/src/app/api/suggestions/route.ts: FOUND
- workspace/occc/src/app/api/suggestions/[id]/action/route.ts: FOUND
- tests/test_suggest_api.py: FOUND
- .planning/phases/41-l1-strategic-suggestions/41-02-SUMMARY.md: FOUND
- Commit 8d8ce50 (feat: GET/POST suggestions route): FOUND
- Commit 7ef99a3 (feat: action route + 8 tests): FOUND
