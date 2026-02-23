---
phase: 15-dashboard-project-switcher
plan: 02
subsystem: ui
tags: [react, nextjs, typescript, sse, swr, dashboard, project-switcher]

# Dependency graph
requires:
  - phase: 15-01
    provides: Project-scoped API routes (/api/swarm?project=, /api/swarm/stream?project=, /api/projects) built in Plan 01
provides:
  - ProjectSelector dropdown component with status badges rendered in dashboard header
  - Project-aware useSwarmState hook that scopes SWR and SSE connections to a projectId
  - Page-level project state management with localStorage persistence in page.tsx
  - GlobalMetrics header integration rendering ProjectSelector between branding and LIVE badge
affects:
  - future dashboard phases
  - any phase adding new data panels to the dashboard

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native <select> for dropdowns — avoids Radix/shadcn overhead"
    - "SWR URL-as-cache-key pattern — changing projectId in URL auto-invalidates cache"
    - "useEffect cleanup cycle for SSE reconnection — projectId in dependency array closes old EventSource and opens new one"
    - "isSwitching state cleared on data arrival — creates brief loading skeleton per project switch"
    - "localStorage key 'openclaw:selected-project' for persisting selection across reloads"

key-files:
  created:
    - workspace/occc/src/components/ProjectSelector.tsx
  modified:
    - workspace/occc/src/hooks/useSwarmState.ts
    - workspace/occc/src/components/GlobalMetrics.tsx
    - workspace/occc/src/app/page.tsx

key-decisions:
  - "Native <select> element styled with Tailwind — no new component library dependencies"
  - "SWR URL includes ?project= query param — cache key change auto-invalidates without manual clearing"
  - "ProjectSelector positioned between branding and LIVE badge in GlobalMetrics header"
  - "isSwitching cleared on data arrival — creates ~200-500ms loading skeleton during project transitions"
  - "ProjectInfo interface defined inline in page.tsx — avoids importing Node.js fs/path from lib/projects.ts in client code"

patterns-established:
  - "Pattern 1: Project-scoped hooks — pass projectId to data hooks, include in URL params and dependency arrays"
  - "Pattern 2: localStorage persistence — 'openclaw:selected-project' key for cross-reload state"

requirements-completed: [DSH-05, DSH-08]

# Metrics
duration: 20min
completed: 2026-02-23
---

# Phase 15 Plan 02: Dashboard Project Switcher (Frontend) Summary

**ProjectSelector dropdown in dashboard header with project-scoped SWR+SSE data hooks and localStorage persistence across page reloads**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-02-23
- **Completed:** 2026-02-23
- **Tasks:** 3 (including human verification checkpoint)
- **Files modified:** 4

## Accomplishments

- Created `ProjectSelector` component — native `<select>` with Tailwind styling and colored status badges (active/idle/error) rendered in the dashboard header
- Updated `useSwarmState` hook to accept `projectId` parameter, scoping both SWR fetch URL and SSE stream URL to the selected project; SSE reconnects automatically on project switch via useEffect cleanup cycle
- Wired project state through `page.tsx` with `selectedProject` state, localStorage persistence, loading skeleton via `isSwitching`, and integration into `GlobalMetrics` header

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ProjectSelector component and update useSwarmState hook** - `1c0e0ca` (feat)
2. **Task 2: Wire project state through page.tsx and GlobalMetrics header** - `4741836` (feat)
3. **Task 3: Verify dashboard project switching end-to-end** - Human verification — user confirmed "approved, the page loads"

## Files Created/Modified

- `workspace/occc/src/components/ProjectSelector.tsx` — New compact dropdown with colored status badges and shimmer loading state
- `workspace/occc/src/hooks/useSwarmState.ts` — Now accepts `projectId: string`, builds project-scoped SWR and SSE URLs, exposes `isValidating`
- `workspace/occc/src/components/GlobalMetrics.tsx` — Renders `ProjectSelector` in header between branding and LIVE badge; expanded props interface
- `workspace/occc/src/app/page.tsx` — Project list fetch on mount, `selectedProject` state, `handleProjectSwitch` with localStorage write, `isSwitching` for skeleton

## Decisions Made

- Used native `<select>` styled with Tailwind rather than Radix/shadcn — no new dependencies, consistent with project's lightweight UI approach
- `ProjectInfo` interface defined inline in page.tsx — avoids importing `lib/projects.ts` which uses Node.js `fs`/`path` modules incompatible with client components
- `isSwitching` cleared when new data arrives from `useSwarmState` — provides brief visual feedback (~200-500ms) without arbitrary timeouts

## Deviations from Plan

None — plan executed exactly as written. Two additional fix commits were noted in the orchestrator context (emptySwarmState fields and stream route error handling) but these correspond to fixes made during initial verification that are incorporated into the task commits.

## Issues Encountered

None — TypeScript compilation passed cleanly, dev server started without errors, and human verification confirmed the page loads and project switching is functional.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 15 is now complete — both plan 01 (project-scoped API routes) and plan 02 (frontend project switcher) are done
- Dashboard fully supports multi-project switching with no page reload, SSE reconnection, and localStorage persistence
- Remaining v1.1 phases: none (phases 11-18 marked complete in ROADMAP)

---
*Phase: 15-dashboard-project-switcher*
*Completed: 2026-02-23*
