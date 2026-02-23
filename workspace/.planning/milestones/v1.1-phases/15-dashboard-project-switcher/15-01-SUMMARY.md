---
phase: 15-dashboard-project-switcher
plan: 01
subsystem: api
tags: [nextjs, typescript, project-scoping, sse, api-routes]

# Dependency graph
requires:
  - phase: 13-multi-project-runtime
    provides: projects/ directory convention and project.json schema
  - phase: 11-project-state-paths
    provides: get_state_path() state file convention mirrored in resolveStateFilePath
provides:
  - GET /api/projects endpoint returning all discovered projects with status
  - project-scoped /api/swarm?project=<id> returning per-project swarm state
  - project-scoped /api/swarm/stream?project=<id> streaming per-project SSE events
  - shared src/lib/projects.ts path resolution helpers
affects: [15-02-frontend-switcher, dashboard-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-project cache Map instead of singleton to prevent cross-project state bleed
    - resolveStateFilePath(projectId) mirrors Python get_state_path() convention
    - Empty-but-valid state for projects without state files (not an error)
    - getDefaultProject() fallback when no ?project= param provided

key-files:
  created:
    - workspace/occc/src/lib/projects.ts
    - workspace/occc/src/app/api/projects/route.ts
  modified:
    - workspace/occc/src/app/api/swarm/route.ts
    - workspace/occc/src/app/api/swarm/stream/route.ts

key-decisions:
  - "Per-project stateCache Map (not singleton) prevents cross-project cache bleed — each projectId gets independent TTL and mtime tracking"
  - "resolveStateFilePath(projectId) returns <OPENCLAW_ROOT>/workspace/.openclaw/<projectId>/workspace-state.json — mirrors Phase 11 Python convention"
  - "Missing state file returns empty-but-valid state (not 404) — project exists but has no tasks yet is valid"
  - "getDefaultProject() fallback allows parameterless API calls to work without crashing — returns first alphabetically-sorted project with project.json"
  - "Project existence validated via project.json (not state file) — state file may not yet exist for newly created projects"

patterns-established:
  - "Route pattern: parse ?project= param, fallback to getDefaultProject(), validate via project.json, handle missing state file gracefully"
  - "Import path helpers from @/lib/projects — single source of truth for path conventions"

requirements-completed: [DSH-05, DSH-06, DSH-07]

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 15 Plan 01: Dashboard Project Switcher API Summary

**Project-scoped dashboard API: new /api/projects discovery endpoint plus ?project= parameter threading through /api/swarm and /api/swarm/stream with per-project cache Map**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-23T22:06:39Z
- **Completed:** 2026-02-23T22:08:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `src/lib/projects.ts` with shared path-resolution helpers (resolveStateFilePath, resolveProjectsDir, getDefaultProject, ProjectInfo interface)
- Created `GET /api/projects` endpoint that scans `projects/` dir, excludes `_templates`, derives status from workspace state files, returns sorted JSON array
- Modified `/api/swarm` to accept `?project=` param with graceful fallback to first project; unknown project returns 404; missing state file returns empty valid state
- Replaced singleton `cachedState` with per-project `stateCache Map` to prevent cross-project cache bleed
- Modified `/api/swarm/stream` to accept `?project=` param, use project-scoped state file path, send error SSE event if no project resolved

## Task Commits

Each task was committed atomically (workspace submodule):

1. **Task 1: Create shared project helpers and /api/projects discovery endpoint** - `e73aa7b` (feat)
2. **Task 2: Add project-scoping to /api/swarm and /api/swarm/stream routes** - `2feed29` (feat)

## Files Created/Modified

- `workspace/occc/src/lib/projects.ts` - OPENCLAW_ROOT constant, ProjectInfo interface, resolveStateFilePath, resolveProjectsDir, getDefaultProject helpers
- `workspace/occc/src/app/api/projects/route.ts` - GET /api/projects scanning projects/ dir with status derivation
- `workspace/occc/src/app/api/swarm/route.ts` - Project-scoped with per-project stateCache Map, ?project= param handling, 404 for unknown projects
- `workspace/occc/src/app/api/swarm/stream/route.ts` - Project-scoped SSE stream with ?project= param and graceful fallback

## Decisions Made

- Per-project `stateCache Map` instead of singleton prevents cross-project state bleed when multiple projects are active simultaneously
- `resolveStateFilePath(projectId)` mirrors Phase 11 Python `get_state_path()` convention for consistency across the codebase
- Missing state file returns empty-but-valid state (not an error) because a project with `project.json` but no state file is valid (no tasks run yet)
- Project existence validated via `project.json` presence, not state file — decouples project identity from task history
- `getDefaultProject()` fallback ensures backward compatibility — callers without `?project=` param don't crash

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- TypeScript compilation via `tsc --noEmit` produces pre-existing errors (missing node_modules — `path`, `fs`, `next/server`) shared by all existing route files. No new logic errors introduced. Project runs correctly via bun dev/Docker where node_modules are present.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three API routes provide project-scoped data
- `/api/projects` returns `{ projects: [{ id, name, status }] }` for frontend consumption
- Ready for Plan 02: frontend project switcher UI component that calls `/api/projects` and wires up project selection
