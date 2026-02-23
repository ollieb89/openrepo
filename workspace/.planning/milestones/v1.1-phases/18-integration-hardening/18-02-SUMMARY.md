---
phase: 18-integration-hardening
plan: 02
subsystem: orchestration
tags: [soul-renderer, init, soul-generation, skip-if-exists, force-flag]

# Dependency graph
requires:
  - phase: 12-soul-templating
    provides: soul_renderer.py write_soul() function and template pipeline
  - phase: 16-multi-project-init
    provides: project_config.py get_active_project_id() for resolving active project at init

provides:
  - write_soul() skip_if_exists parameter (returns None when file exists and skip=True)
  - CLI --force flag for manual SOUL.md regeneration overwriting existing file
  - initialize_workspace() auto-generates SOUL.md for active project on first run

affects:
  - Any caller of write_soul() — return type is now Optional[Path]
  - initialize_workspace() callers expecting return dict (soul_written key added)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred local import inside function body to avoid circular imports between orchestration modules"
    - "skip_if_exists guard pattern: check before render, return None as sentinel for skipped"
    - "Non-fatal side effect in init: try/except around optional SOUL generation preserves directory creation success"

key-files:
  created: []
  modified:
    - orchestration/soul_renderer.py
    - orchestration/init.py

key-decisions:
  - "CLI --write defaults to skip-if-exists (safe default); --force must be explicit to overwrite"
  - "SOUL generation failure in initialize_workspace() is non-fatal — directory creation already succeeded"
  - "Deferred import (from .soul_renderer import write_soul inside function body) avoids circular import"
  - "Return None (not raise) when skip_if_exists=True and file exists — lets callers distinguish skip vs write"

patterns-established:
  - "skip_if_exists pattern: check existence before expensive render, return None sentinel on skip"
  - "Non-fatal optional work in init: wrap in try/except, log warning, never block primary init path"

requirements-completed: [CFG-04, CFG-05]

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 18 Plan 02: Integration Hardening — SOUL Auto-Init Summary

**write_soul() gains skip_if_exists + Optional[Path] return; initialize_workspace() auto-generates SOUL.md for active project with non-fatal guard and soul_written in return dict**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-23T21:09:13Z
- **Completed:** 2026-02-23T21:10:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- write_soul() extended with skip_if_exists parameter: skips render+write when file exists, returns None as sentinel
- CLI --write now defaults to skip-if-exists (safe default); --force flag added for explicit overwrite
- initialize_workspace() auto-calls write_soul(project_id, skip_if_exists=True) after directory creation
- SOUL generation failure in initialize_workspace() is non-fatal (try/except, logged as warning)
- Return dict from initialize_workspace() includes soul_written boolean

## Task Commits

Each task was committed atomically:

1. **Task 1: Add skip_if_exists to write_soul() and --force to CLI** - `303320f` (feat)
2. **Task 2: Wire write_soul() call into initialize_workspace()** - `f352b6a` (feat)

## Files Created/Modified
- `orchestration/soul_renderer.py` - write_soul() gains skip_if_exists param + Optional[Path] return; CLI --force flag added
- `orchestration/init.py` - initialize_workspace() wires write_soul() with skip-if-exists guard, soul_written in return dict

## Decisions Made
- CLI --write defaults to skip-if-exists (safe default); --force must be explicit to overwrite existing SOUL.md
- SOUL generation failure is non-fatal — directory creation already succeeded, SOUL generation is supplementary
- Deferred local import inside function body (from .soul_renderer import write_soul) avoids circular import risk
- Return None rather than raise when skip_if_exists=True and file exists — cleaner caller pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CFG-04 (SOUL template rendered at init time) and CFG-05 (override mechanism triggered at runtime) are now closed
- New projects will auto-receive SOUL.md on first initialize_workspace() call
- Existing projects are protected from accidental overwrite; --force provides the manual escape hatch
- No blockers for subsequent Phase 18 plans

---
*Phase: 18-integration-hardening*
*Completed: 2026-02-23*

## Self-Check: PASSED

- orchestration/soul_renderer.py: FOUND
- orchestration/init.py: FOUND
- .planning/phases/18-integration-hardening/18-02-SUMMARY.md: FOUND
- Commit 303320f (Task 1): FOUND
- Commit f352b6a (Task 2): FOUND
