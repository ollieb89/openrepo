---
phase: 36-dashboard-memory-panel
plan: 01
subsystem: ui
tags: [next.js, typescript, swr, react-toastify, memory, api-proxy]

requires:
  - phase: 35-l3-in-execution-memory-queries
    provides: memU REST API endpoints (GET /memories, POST /retrieve, DELETE /memories/{id}) and project-scoped memory system

provides:
  - MemoryItem and MemoryListResponse TypeScript types (defensive optional fields)
  - GET /api/memory proxy route (list + semantic search with memU response normalization)
  - DELETE /api/memory/[id] proxy route forwarding to memU
  - useMemory SWR hook with project-scoped cache key and mutate
  - Memory nav item in Sidebar
  - ToastContainer mounted globally in layout.tsx

affects: [36-02, 36-03]

tech-stack:
  added: [react-toastify (ToastContainer wired, already in package.json)]
  patterns:
    - "Next.js API route proxy to internal memU service (avoids CORS, hides service URL)"
    - "SWR null-key disables fetch when projectId is null"
    - "memU response normalization: Array.isArray(data) ? data : (data.items ?? [])"

key-files:
  created:
    - workspace/occc/src/lib/types/memory.ts
    - workspace/occc/src/lib/hooks/useMemory.ts
    - workspace/occc/src/app/api/memory/route.ts
    - workspace/occc/src/app/api/memory/[id]/route.ts
  modified:
    - workspace/occc/src/components/layout/Sidebar.tsx
    - workspace/occc/src/app/layout.tsx

key-decisions:
  - "memU response normalization applied for both GET /memories (plain array) and POST /retrieve (array or object) endpoints"
  - "useMemory uses revalidateOnFocus: false and no refreshInterval — memory items do not change in real-time"
  - "ToastContainer placed inside ThemeProvider (after ProjectProvider) so theme context is available"
  - "Brain/nerve SVG icon (Heroicons outline style) used for Memory sidebar nav item"

patterns-established:
  - "Pattern: proxy API route reads memuUrl via readOpenClawConfig() config.memory.memu_api_url with localhost:18791 fallback"
  - "Pattern: SWR hook exposes mutate for optimistic delete by callers (Plans 02/03)"

requirements-completed: [DSH-11, DSH-14]

duration: 2min
completed: 2026-02-24
---

# Phase 36 Plan 01: Dashboard Memory Panel — API Plumbing Summary

**Next.js API proxy routes, MemoryItem types, useMemory SWR hook, Memory sidebar link, and global ToastContainer wired for occc memory panel**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-24T13:55:25Z
- **Completed:** 2026-02-24T13:57:18Z
- **Tasks:** 2
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- Created MemoryItem TypeScript type with defensive optional fields and index signature to handle unknown memU response fields
- Built GET /api/memory proxy with dual-mode support (browse via GET /memories, search via POST /retrieve) and response normalization for both array and object shapes
- Built DELETE /api/memory/[id] proxy forwarding to memU with proper error handling
- Created useMemory SWR hook with project-scoped cache keys, null-key disabling when no project, and mutate exposed for optimistic deletes
- Added Memory nav item to Sidebar (after Metrics) with brain/nerve SVG icon matching existing icon style
- Mounted ToastContainer globally in layout.tsx with react-toastify CSS import

## Task Commits

Each task was committed atomically:

1. **Task 1: API proxy routes + TypeScript types** - `a3c7da2` (feat)
2. **Task 2: SWR hook + sidebar nav + ToastContainer** - `76c893e` (feat)

## Files Created/Modified
- `workspace/occc/src/lib/types/memory.ts` - MemoryItem interface (defensive optional fields + index signature) and MemoryListResponse type
- `workspace/occc/src/app/api/memory/route.ts` - GET proxy to memU list and retrieve endpoints with response normalization
- `workspace/occc/src/app/api/memory/[id]/route.ts` - DELETE proxy forwarding to memU delete endpoint
- `workspace/occc/src/lib/hooks/useMemory.ts` - SWR hook with project+search params, no polling, mutate exposed
- `workspace/occc/src/components/layout/Sidebar.tsx` - Memory nav item added after Metrics
- `workspace/occc/src/app/layout.tsx` - ToastContainer mounted globally with react-toastify CSS import

## Decisions Made
- memU response normalization pattern applied in both GET endpoints: `Array.isArray(data) ? data : (data.items ?? [])` to handle both plain array (GET /memories) and object (POST /retrieve) response shapes
- useMemory uses `revalidateOnFocus: false` with no `refreshInterval` — memory items are not real-time data
- ToastContainer placed after ProjectProvider but inside ThemeProvider so it can access theme context for dark mode
- Brain/nerve Heroicons outline SVG used for Memory nav item to represent memory/recall

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- 5 pre-existing TypeScript errors in test files (bun:test module not found, privacy-guard type error) — unrelated to new files, pre-existing and out of scope per deviation rules.

## Next Phase Readiness
- All plumbing complete: types, API routes, SWR hook, nav wiring, and ToastContainer ready
- Plans 02 and 03 can consume useMemory hook and call /api/memory endpoints immediately
- No blockers

---
*Phase: 36-dashboard-memory-panel*
*Completed: 2026-02-24*

## Self-Check: PASSED

All files verified present:
- workspace/occc/src/lib/types/memory.ts: FOUND
- workspace/occc/src/lib/hooks/useMemory.ts: FOUND
- workspace/occc/src/app/api/memory/route.ts: FOUND
- workspace/occc/src/app/api/memory/[id]/route.ts: FOUND
- .planning/phases/36-dashboard-memory-panel/36-01-SUMMARY.md: FOUND

All commits verified: a3c7da2 (Task 1), 76c893e (Task 2)
