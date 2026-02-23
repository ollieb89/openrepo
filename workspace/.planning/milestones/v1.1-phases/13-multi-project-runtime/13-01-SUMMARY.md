---
phase: 13-multi-project-runtime
plan: 01
subsystem: infra
tags: [docker, containers, project-identity, pool-management, spawn]

# Dependency graph
requires:
  - phase: 12-soul-templating
    provides: project_config.py with get_active_project_id, get_state_path(project_id)
provides:
  - Project-aware container spawning with namespaced names, Docker labels, and OPENCLAW_PROJECT env var
  - _validate_project_id() enforcing 1-20 char alphanumeric+hyphen constraint
  - PoolRegistry managing per-project L3ContainerPool instances with independent semaphores
  - entrypoint.sh defense-in-depth guard rejecting containers without OPENCLAW_PROJECT
affects: [14-project-cli, 15-multi-project-e2e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Project identity captured once at spawn entry, threaded explicitly — never re-read from ambient config mid-flight"
    - "PoolRegistry lazy-init pattern: get_pool(project_id) creates pool on first call, returns same instance thereafter"
    - "State file resolved per-call via get_state_path(project_id) — no cached state_file attribute"

key-files:
  created: []
  modified:
    - skills/spawn_specialist/spawn.py
    - skills/spawn_specialist/pool.py
    - docker/l3-specialist/entrypoint.sh

key-decisions:
  - "Container names namespaced as openclaw-{project_id}-l3-{task_id} to prevent cross-project collisions"
  - "project_id defaults to None with fallback to get_active_project_id() preserving backward compatibility"
  - "No global cross-project semaphore — per-project limits of 3 are sufficient (per prior research decision)"
  - "entrypoint.sh hard-fails via bash :? expansion if OPENCLAW_PROJECT missing — defense-in-depth"

patterns-established:
  - "Thread project_id explicitly: resolve once at entry, pass as parameter to all downstream calls"
  - "PoolRegistry.get_pool(project_id): idempotent pool creation, identity by project_id key"

requirements-completed: [MPR-01, MPR-02, MPR-03, MPR-05, MPR-06]

# Metrics
duration: 3min
completed: 2026-02-23
---

# Phase 13 Plan 01: Multi-Project Runtime Summary

**Project-scoped L3 container spawning with namespaced names, Docker labels, OPENCLAW_PROJECT env var, and PoolRegistry for per-project semaphore isolation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-23T19:22:27Z
- **Completed:** 2026-02-23T19:25:01Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `_validate_project_id()` with regex enforcing 1-20 char alphanumeric+hyphen constraint — spawn hard-fails before any Docker or state operations if project_id is invalid
- Updated `spawn_l3_specialist()` to accept `project_id`, namespace container names as `openclaw-{project_id}-l3-{task_id}`, inject `OPENCLAW_PROJECT` env var, add `openclaw.project` and `openclaw.task.type` labels, and thread project_id to all state/config calls
- Added `PoolRegistry` class giving each project its own `L3ContainerPool` with an independent asyncio semaphore — two projects each get up to 3 concurrent containers without contention
- Added `OPENCLAW_PROJECT` guard to `entrypoint.sh` — containers spawned without project context exit immediately with clear error message

## Task Commits

Each task was committed atomically:

1. **Task 1: Add project identity to spawn.py and entrypoint.sh** - `9e08bdd` (feat)
2. **Task 2: Add PoolRegistry and project_id threading to pool.py** - `86f4fb2` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `skills/spawn_specialist/spawn.py` - Added _validate_project_id(), project_id param to spawn_l3_specialist(), namespaced container name, OPENCLAW_PROJECT env var, openclaw.project label, project-scoped state path
- `skills/spawn_specialist/pool.py` - Added project_id to L3ContainerPool.__init__, removed self.state_file, added PoolRegistry class, updated spawn_task() convenience function, added --project CLI arg
- `docker/l3-specialist/entrypoint.sh` - Added OPENCLAW_PROJECT required env var guard

## Decisions Made
- Container names follow `openclaw-{project_id}-l3-{task_id}` pattern — project prefix before `l3` tier marker for readable `docker ps` output
- `_validate_project_id` placed at module level in spawn.py so it can be imported and tested independently
- `PoolRegistry` does not enforce a global cross-project cap — per-project limits of 3 are the correct scope boundary (per prior research)
- `spawn_task()` convenience function resolves project_id early and passes to pool constructor, maintaining the "resolve once, thread explicitly" pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- L3 container lifecycle is now fully project-aware
- Phase 14 (Project CLI) can use PoolRegistry.get_pool(project_id) to route tasks to the correct per-project pool
- Phase 15 (multi-project E2E tests) can verify container name isolation by spawning tasks for two projects and confirming names differ

---
*Phase: 13-multi-project-runtime*
*Completed: 2026-02-23*
