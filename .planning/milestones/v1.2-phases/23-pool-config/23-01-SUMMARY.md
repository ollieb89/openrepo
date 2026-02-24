---
phase: 23-pool-config
plan: 01
subsystem: infra
tags: [pool, concurrency, semaphore, hot-reload, project-config, l3-specialist]

# Dependency graph
requires:
  - phase: 22-observability-metrics
    provides: pool saturation tracking and lock_wait_ms metrics already in pool.py
  - phase: 20-reliability-hardening
    provides: config_validator.py with collect-all validation strategy
provides:
  - get_pool_config() helper returning validated pool settings from project.json l3_overrides
  - Non-fatal pool config validation in config_validator.py (advisory warnings only)
  - Config-driven PoolRegistry that reads project.json fresh on every get_pool() call
  - Hot-reload semantics: max_concurrent changes take effect on next spawn without restart
  - _pool_config attached to pool instances for overflow policy use in Plan 02
affects: [23-pool-config-02, spawn_specialist, pool_registry, project_config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hot-reload config: read project.json fresh on every spawn call — no caching, no restart needed"
    - "Non-fatal validation: pool config issues log warnings and fall back to defaults, never block spawns"
    - "Semaphore hot-swap: recreate asyncio.Semaphore in-place on max_concurrent change without disrupting running containers"

key-files:
  created: []
  modified:
    - orchestration/project_config.py
    - orchestration/config_validator.py
    - orchestration/__init__.py
    - skills/spawn_specialist/pool.py

key-decisions:
  - "Pool config reads project.json fresh on every get_pool() call — supports hot-reload without restart (locked decision from CONTEXT.md)"
  - "Invalid pool config values log a warning and fall back to defaults — never raise, never block spawns"
  - "Semaphore is recreated in-place when max_concurrent changes — running containers not disrupted"
  - "max_per_project parameter removed from PoolRegistry.__init__() — now fully config-driven via get_pool_config()"
  - "_pool_config attached to every pool instance for future use by overflow policy (Plan 02)"

patterns-established:
  - "get_pool_config(): always returns a complete, valid config dict with no exceptions — safe to call unconditionally"
  - "PoolRegistry.get_pool() wraps get_pool_config() in try/except with fallback to _POOL_DEFAULTS"

requirements-completed: [POOL-01]

# Metrics
duration: 3min
completed: 2026-02-24
---

# Phase 23 Plan 01: Pool Config Summary

**Config-driven per-project L3 pool concurrency via project.json l3_overrides with hot-reload semantics and non-fatal validation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-24T03:11:20Z
- **Completed:** 2026-02-24T03:13:48Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `get_pool_config(project_id)` to `orchestration/project_config.py` — reads pool settings from project.json l3_overrides, falls back to safe defaults for missing or invalid values, never raises
- Extended `config_validator.py` with `_validate_pool_config()` — non-fatal advisory warnings for invalid pool config values within `validate_project_config()`
- Rewrote `PoolRegistry.get_pool()` to read project.json fresh on every call — supports hot-reload when l3_overrides.max_concurrent is changed without restarting orchestration
- Removed hardcoded `max_concurrent=3` from PoolRegistry and `spawn_task()` — now fully config-driven with `_POOL_DEFAULTS` as fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pool config loader and validation** - `f09a1df` (feat)
2. **Task 2: Config-driven PoolRegistry with hot-reload and dynamic semaphore** - `051a90a` (feat)

## Files Created/Modified
- `orchestration/project_config.py` - Added `get_pool_config()`, `_POOL_CONFIG_DEFAULTS`, `_VALID_POOL_MODES`, `_VALID_OVERFLOW_POLICIES`
- `orchestration/config_validator.py` - Added `_validate_pool_config()`, wired into `validate_project_config()` as non-fatal advisory step
- `orchestration/__init__.py` - Added `get_pool_config` to public API and `__all__`
- `skills/spawn_specialist/pool.py` - Config-driven `PoolRegistry.get_pool()`, `_POOL_DEFAULTS` constant, updated `spawn_task()` and `L3ContainerPool.__init__` docstring

## Decisions Made
- Pool config reads project.json fresh on every `get_pool()` call (hot-reload without restart) — matches locked decision from CONTEXT.md
- Invalid pool config values produce a warning log and fall back to defaults — consistent with "never crash or block spawns" locked decision
- Semaphore recreated in-place when `max_concurrent` changes — running containers not disrupted (asyncio.Semaphore is reassigned on pool instance)
- `max_per_project` parameter removed from `PoolRegistry.__init__()` entirely — config is now the sole source of truth with `_POOL_DEFAULTS` as fallback
- `_pool_config` attached to each pool instance to support overflow policy logic in Plan 02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 (overflow policy enforcement) can read `pool._pool_config["overflow_policy"]` and `pool._pool_config["queue_timeout_s"]` — those fields are now live on every pool instance
- Projects can set `l3_overrides.max_concurrent` in their project.json to limit concurrency immediately on next spawn

## Self-Check: PASSED

All files found. All commits verified.

---
*Phase: 23-pool-config*
*Completed: 2026-02-24*
