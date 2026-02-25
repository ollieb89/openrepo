---
phase: 45-path-resolver-constants-foundation
plan: 02
subsystem: orchestration/config
tags: [path-resolver, constants, config, refactor, migration]
dependency_graph:
  requires:
    - phase: 45-01
      provides: [get_project_root, get_state_path, get_snapshot_dir, DEFAULT_POOL_*, MEMORY_CONTEXT_BUDGET in config.py]
  provides:
    - All call sites (project_config, pool, spawn, monitor, snapshot, init, soul_renderer, suggest, migrate_state, project CLI) import path functions and constants from config.py
    - project_config.py cleaned of path resolvers and pool defaults dict
    - Zero duplicated constant definitions outside config.py
  affects: [phase-46, phase-47, phase-48, phase-49]
tech-stack:
  added: []
  patterns: [single-source-of-truth-constants, import-from-config-not-project-config]
key-files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/project_config.py
    - packages/orchestration/src/openclaw/snapshot.py
    - packages/orchestration/src/openclaw/__init__.py
    - packages/orchestration/src/openclaw/init.py
    - packages/orchestration/src/openclaw/soul_renderer.py
    - packages/orchestration/src/openclaw/cli/monitor.py
    - packages/orchestration/src/openclaw/cli/suggest.py
    - packages/orchestration/src/openclaw/cli/migrate_state.py
    - packages/orchestration/src/openclaw/cli/project.py
    - skills/spawn/spawn.py
    - skills/spawn/pool.py
    - packages/orchestration/tests/test_spawn_memory.py
key-decisions:
  - "pool.py init builds defaults dict inline from DEFAULT_POOL_* constants rather than .copy() from a dict — constant-referencing pattern, not a new dict"
  - "init.py uses get_active_project_id() with fallback to 'default' for get_state_path/get_snapshot_dir calls that previously used optional project_id"
  - "soul_renderer.py aliases get_project_root as _find_project_root at import time to minimize diff size while aligning to config source"
patterns-established:
  - "Call sites import path functions from openclaw.config, not openclaw.project_config"
  - "Pool defaults: reference DEFAULT_POOL_* constants instead of dict literals"
requirements-completed: [CONF-01, CONF-05]
duration: 6min
completed: 2026-02-25
---

# Phase 45 Plan 02: Call Site Migration Summary

**All path resolvers and pool/memory constants migrated to config.py as sole source of truth — 9 files updated, 151 tests pass, zero duplicated definitions remain.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-02-25T04:06:48Z
- **Completed:** 2026-02-25T04:12:43Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- project_config.py cleaned: removed `_find_project_root`, `get_state_path`, `get_snapshot_dir`, `_POOL_CONFIG_DEFAULTS`; `get_pool_config()` now builds defaults from `DEFAULT_POOL_*` imports
- spawn.py, pool.py, monitor.py migrated from Path(__file__) and local constants to config.py imports
- 8 additional call sites fixed (init.py, __init__.py, soul_renderer.py, suggest.py, migrate_state.py, project.py) that imported removed symbols from project_config
- test_spawn_memory.py updated to import `MEMORY_CONTEXT_BUDGET` from `openclaw.config`
- All 151 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate project_config.py and snapshot.py** - `9017e28` (feat)
2. **Task 2: Migrate spawn.py, pool.py, monitor.py, and tests** - `3325025` (feat)
3. **Task 3: Verify no duplicated constants remain** - `a0ba1ca` (feat)

## Files Created/Modified
- `packages/orchestration/src/openclaw/project_config.py` - Removed path resolver functions and _POOL_CONFIG_DEFAULTS; get_pool_config() uses DEFAULT_POOL_* imports
- `packages/orchestration/src/openclaw/snapshot.py` - get_snapshot_dir imported from config not project_config
- `packages/orchestration/src/openclaw/__init__.py` - Re-exports get_state_path, get_snapshot_dir from config
- `packages/orchestration/src/openclaw/init.py` - Imports from config; resolves project_id via get_active_project_id()
- `packages/orchestration/src/openclaw/soul_renderer.py` - Aliases get_project_root as _find_project_root from config
- `packages/orchestration/src/openclaw/cli/monitor.py` - Uses get_project_root() and get_state_path() from config in _discover_projects()
- `packages/orchestration/src/openclaw/cli/suggest.py` - Lazy imports updated from project_config to config
- `packages/orchestration/src/openclaw/cli/migrate_state.py` - All imports from config
- `packages/orchestration/src/openclaw/cli/project.py` - _find_project_root alias from config
- `skills/spawn/spawn.py` - Local MEMORY_CONTEXT_BUDGET removed; Path(__file__) root removed; imports from config
- `skills/spawn/pool.py` - _POOL_DEFAULTS removed; DEFAULT_POOL_* constants from config; get_state_path/get_snapshot_dir from config
- `packages/orchestration/tests/test_spawn_memory.py` - MEMORY_CONTEXT_BUDGET from openclaw.config

## Decisions Made

1. **pool.py init defaults dict built inline** — When `_POOL_DEFAULTS.copy()` was used as the initial `_pool_config` value, replaced with an inline dict referencing `DEFAULT_POOL_*` constants. No separate dict variable needed.
2. **init.py project_id fallback to "default"** — `get_state_path` and `get_snapshot_dir` now require `project_id`. For `init.py` which previously called them without arguments, we resolve via `get_active_project_id()` with a `"default"` fallback string on error.
3. **soul_renderer.py alias pattern** — `from .config import get_project_root as _find_project_root` preserves all internal call sites without change.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed init.py importing removed symbols from project_config**
- **Found during:** Task 1 (import verification)
- **Issue:** `init.py` imported `get_state_path` and `get_snapshot_dir` from `project_config` and called them without `project_id` argument (old signature was `Optional[str]`)
- **Fix:** Updated import to `config`; resolved `project_id` via `get_active_project_id()` with fallback; updated both `initialize_workspace` and `verify_workspace` function bodies
- **Files modified:** `packages/orchestration/src/openclaw/init.py`
- **Verification:** Import check succeeded after fix
- **Committed in:** 9017e28 (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed __init__.py re-exporting removed symbols from project_config**
- **Found during:** Task 1 (import verification)
- **Issue:** Package `__init__.py` re-exported `get_state_path` and `get_snapshot_dir` from `project_config` in the public API
- **Fix:** Updated to import `get_state_path` and `get_snapshot_dir` from `config` directly
- **Files modified:** `packages/orchestration/src/openclaw/__init__.py`
- **Verification:** Import check succeeded after fix
- **Committed in:** 9017e28 (Task 1 commit)

**3. [Rule 3 - Blocking] Fixed soul_renderer.py importing _find_project_root from project_config**
- **Found during:** Task 1 (import verification)
- **Issue:** `soul_renderer.py` imported the private `_find_project_root` function from `project_config`
- **Fix:** Changed to `from .config import get_project_root as _find_project_root`
- **Files modified:** `packages/orchestration/src/openclaw/soul_renderer.py`
- **Verification:** Import check succeeded after fix
- **Committed in:** 9017e28 (Task 1 commit)

**4. [Rule 3 - Blocking] Fixed suggest.py, migrate_state.py, project.py importing removed symbols**
- **Found during:** Task 3 (verification grep)
- **Issue:** Three CLI modules still imported `_find_project_root`, `get_state_path`, or `get_snapshot_dir` from `project_config`
- **Fix:** Updated all three to import from `openclaw.config`
- **Files modified:** `suggest.py`, `migrate_state.py`, `project.py`
- **Verification:** All 151 tests pass after fix
- **Committed in:** a0ba1ca (Task 3 commit)

**5. [Rule 1 - Bug] Fixed pool.py self.project_root using Path(__file__).parent.parent.parent**
- **Found during:** Task 3 (verification grep)
- **Issue:** `L3ContainerPool.__init__` still set `self.project_root = Path(__file__).parent.parent.parent` for divergent root derivation
- **Fix:** Replaced with lazy `get_project_root()` call from `openclaw.config`
- **Files modified:** `skills/spawn/pool.py`
- **Verification:** All 151 tests pass after fix
- **Committed in:** a0ba1ca (Task 3 commit)

---

**Total deviations:** 5 auto-fixed (4 blocking import fixes, 1 bug fix)
**Impact on plan:** All auto-fixes were direct consequences of removing symbols from project_config — expected collateral cleanup. No scope creep.

## Issues Encountered
None beyond the blocking import issues documented above.

## Next Phase Readiness
- CONF-01 and CONF-05 requirements fully satisfied
- Phase 45 complete — config.py is the authoritative source for all path resolvers and constants
- Phase 46 (Schema Validation + Fail-Fast Startup) can proceed — depends on config.py path resolution which is now clean

## Self-Check: PASSED

- [x] `45-02-SUMMARY.md` exists
- [x] `project_config.py` exists with path resolver functions and pool defaults removed
- [x] `spawn.py` exists with MEMORY_CONTEXT_BUDGET and Path(__file__) root removed
- [x] `pool.py` exists with _POOL_DEFAULTS removed
- [x] Commit 9017e28 exists in git log
- [x] Commit 3325025 exists in git log
- [x] Commit a0ba1ca exists in git log
- [x] 151 tests pass

---
*Phase: 45-path-resolver-constants-foundation*
*Completed: 2026-02-25*
