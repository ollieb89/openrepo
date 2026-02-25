---
phase: 44-v1.4-tech-debt-cleanup
plan: 01
subsystem: infra
tags: [makefile, dashboard, typescript, openclaw-root, audit]

# Dependency graph
requires:
  - phase: 43-v1.4-gap-closure
    provides: audit record of OPENCLAW_ROOT soft dependency and SummaryStream.tsx parse error as tech debt items
provides:
  - OPENCLAW_ROOT guard in Makefile dashboard target (exits non-zero with clear ERROR when unset)
  - README Dashboard section updated to packages/dashboard path + export OPENCLAW_ROOT instruction
  - SummaryStream.tsx parse error resolved (buffer.split literal newline -> escape sequence)
  - v1.4-MILESTONE-AUDIT.md stale-patch-target item marked RESOLVED with test evidence
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Makefile env var guard pattern: @if [ -z \"$$VAR\" ]; then echo ERROR; exit 1; fi before recipe"

key-files:
  created: []
  modified:
    - Makefile
    - README.md
    - packages/dashboard/src/components/sync/SummaryStream.tsx
    - .planning/v1.4-MILESTONE-AUDIT.md

key-decisions:
  - "Use exit 1 (hard guard) not soft-warn in Makefile dashboard target — soft-warn allows silent failures which is exactly the ADV-03 issue being fixed"
  - "Use $$ (double dollar) in Makefile recipes for shell variable references — single $ is expanded by Make and silently becomes empty"

patterns-established:
  - "Makefile env var guard: @if [ -z \"$$VAR\" ]; ... exit 1 pattern prevents silent misconfiguration at tooling layer"

requirements-completed:
  - TECH-DEBT-44-A
  - TECH-DEBT-44-B
  - TECH-DEBT-44-C

# Metrics
duration: 10min
completed: 2026-02-25
---

# Phase 44 Plan 01: v1.4 Tech Debt Cleanup Summary

**OPENCLAW_ROOT guard added to make dashboard, README Dashboard section corrected to packages/dashboard, SummaryStream.tsx parse error fixed, and stale-patch-target audit item resolved with 17/17 test evidence**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-25T~12:00Z
- **Completed:** 2026-02-25T~12:10Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `make dashboard` now prints a clear ERROR and exits non-zero if OPENCLAW_ROOT is unset — prevents silent ADV-03 path failures on fresh deployments
- README.md Dashboard section updated: "Run locally" uses `export OPENCLAW_ROOT=...` + `make dashboard`; "Run via Docker" uses `packages/dashboard/` (was `workspace/occc/`)
- SummaryStream.tsx line 44 fixed: `buffer.split('\n')` (was literal embedded newline — TypeScript parse error)
- v1.4-MILESTONE-AUDIT.md stale-patch-target cross-milestone item updated to RESOLVED (Phase 44) in both YAML frontmatter and Tech Debt Summary prose section

## Task Commits

Each task was committed atomically:

1. **Task 1: Makefile OPENCLAW_ROOT guard + README Dashboard fix** - `3e4cb5c` (fix)
2. **Task 2: SummaryStream.tsx literal-newline parse error fix** - `55b19f1` (fix)
3. **Task 3: Verify stale patch paths + update audit record** - `107a516` (docs)

## Files Created/Modified
- `Makefile` — dashboard target now includes OPENCLAW_ROOT guard (exit 1 on unset) before bun install/run
- `README.md` — Dashboard "Run locally" and "Run via Docker" sections updated to packages/dashboard, export OPENCLAW_ROOT step added
- `packages/dashboard/src/components/sync/SummaryStream.tsx` — Line 44: `buffer.split('\\n')` replaces two-line literal-newline expression
- `.planning/v1.4-MILESTONE-AUDIT.md` — Cross-milestone stale-patch item marked RESOLVED in YAML + prose; SummaryStream.tsx item remains as-is (pre-existing, closed by Task 2)

## Decisions Made
- Used hard `exit 1` guard (not soft-warn) in Makefile dashboard target — soft-warn allows silent failure, which is the exact problem being fixed (ADV-03 returns empty state when OPENCLAW_ROOT unset)
- Used `$$` (double dollar) in Makefile recipe for shell variables — single `$` is expanded by Make and silently produces empty string, defeating the guard

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Test verification passed on first run: 17/17 tests pass with `-W all`, zero MagicMock warnings. Full suite: 148/148 green.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

All Phase 44 success criteria satisfied:
1. `make dashboard` without OPENCLAW_ROOT fails with clear ERROR — verified via unset + make dashboard test
2. README.md Dashboard section uses `export OPENCLAW_ROOT=...` and `packages/dashboard` (not `workspace/occc`)
3. SummaryStream.tsx: `buffer.split('\n')` on single line — TypeScript parse error resolved
4. v1.4-MILESTONE-AUDIT.md stale-patch-target item: RESOLVED (Phase 44) with test evidence
5. `uv run pytest tests/ -v` from `packages/orchestration`: 148 passed, 0 errors

Phase 44 is complete (1 plan). v1.4 tech debt cleanup done.

## Self-Check: PASSED

- FOUND: Makefile (OPENCLAW_ROOT guard verified)
- FOUND: README.md (export OPENCLAW_ROOT + packages/dashboard verified)
- FOUND: packages/dashboard/src/components/sync/SummaryStream.tsx (buffer.split('\\n') verified)
- FOUND: .planning/v1.4-MILESTONE-AUDIT.md (RESOLVED Phase 44 in both locations verified)
- FOUND: 44-01-SUMMARY.md
- Commits 3e4cb5c, 55b19f1, 107a516 all exist in git log
- Test suite: 148/148 passed, 0 errors

---
*Phase: 44-v1.4-tech-debt-cleanup*
*Completed: 2026-02-25*
