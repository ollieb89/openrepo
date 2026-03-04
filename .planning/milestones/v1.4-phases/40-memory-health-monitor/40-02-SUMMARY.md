---
phase: 40-memory-health-monitor
plan: 02
subsystem: dashboard
tags: [next.js, react, health-scan, memory-hygiene, tailwind, typescript]

# Dependency graph
requires:
  - phase: 40-01
    provides: "POST /memories/health-scan, GET /memories/health-flags, PUT /memories/{id} FastAPI endpoints"
provides:
  - "POST /api/memory/health-scan Next.js proxy route — forwards to memU health-scan endpoint"
  - "PUT /api/memory/[id] Next.js proxy route — memory content update via dashboard"
  - "HealthTab component — summary bar, flag list sorted by score, Run Scan button, dismiss/conflict actions"
  - "MemoryPanel health state — healthFlags Map, activeTab, showOnlyFlagged, runHealthScan(), scheduled scan interval"
  - "MemoryRow health badge rendering — orange (stale) / red (conflict) pill with click handler"
  - "MemoryTable Health column with healthFlags prop threading"
affects:
  - 40-03 (if applicable — settings modal could extend HealthTab)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HealthFlag interface exported from HealthTab.tsx — single source of truth for type shared across Panel/Row/Table"
    - "healthFlags Map<string, HealthFlag> keyed by memory_id — O(1) lookup per MemoryRow render"
    - "useCallback wraps runHealthScan to stabilize scheduled scan interval effect dependency"
    - "Scheduled scan setInterval inside useEffect with activeTab guard — only fires on health tab, clears on unmount"
    - "showOnlyFlagged filter added to filteredItems useMemo — no separate filtered array needed"

key-files:
  created:
    - workspace/occc/src/app/api/memory/health-scan/route.ts
    - workspace/occc/src/components/memory/HealthTab.tsx
  modified:
    - workspace/occc/src/app/api/memory/[id]/route.ts
    - workspace/occc/src/components/memory/MemoryPanel.tsx
    - workspace/occc/src/components/memory/MemoryRow.tsx
    - workspace/occc/src/components/memory/MemoryTable.tsx

key-decisions:
  - "HealthFlag interface exported from HealthTab.tsx so Panel/Row/Table all import from one location — avoids duplicate type definitions"
  - "healthFlags Map keyed by memory_id for O(1) lookup in MemoryRow render without array .find()"
  - "useCallback on runHealthScan with healthSettings as dep — prevents stale closure in setInterval effect"
  - "Scheduled interval guards: activeTab === health AND projectId non-null — prevents scanning on list tab or before project loads"
  - "handleOpenConflict and handleOpenSettings use toast.info as placeholders — conflict modal and settings modal deferred to future plan"

patterns-established:
  - "Tab bar pattern: border-b-2 on active tab, border-transparent on inactive — matches other dashboard tab usages"
  - "Health flag badge: button element with stopPropagation — allows click-through to conflict handler without expanding row"

requirements-completed: [QUAL-04, QUAL-05]

# Metrics
duration: 4min
completed: 2026-02-24
---

# Phase 40 Plan 02: Memory Health Monitor Dashboard Summary

**Health dashboard UI — POST/PUT proxy routes, HealthTab with summary bar and flag list, orange/red health badges on MemoryRow, scan trigger with scheduled interval, and flagged filter toggle in MemoryPanel**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-24T17:39:17Z
- **Completed:** 2026-02-24T17:43:59Z
- **Tasks:** 2
- **Files modified:** 6 (2 created + 4 modified)

## Accomplishments

- `POST /api/memory/health-scan` route proxies to memU `/memories/health-scan` following existing `getMemuUrl()` pattern
- `PUT /api/memory/[id]` added alongside existing DELETE handler in `[id]/route.ts` — memory content updates from dashboard
- `HealthTab.tsx` — new component with summary bar (stale/conflict count chips), flag list sorted by score descending, Run Scan button (spinner when running), dismiss button for stale flags, "View Conflict" button for conflict flags, gear settings button, and empty state
- `MemoryPanel.tsx` — tab bar (Memories / Health) with count badge, health state management (`healthFlags` Map, `scanRunning`, `showOnlyFlagged`, `activeTab`), `runHealthScan()` async function, scheduled scan `setInterval` with cleanup, flagged filter toggle when flags exist
- `MemoryRow.tsx` — optional `healthFlag` prop with orange (stale) / red (conflict) pill badge, clickable for conflict handler
- `MemoryTable.tsx` — `healthFlags` Map and `onOpenConflict` props threaded to MemoryRow, Health column header added

## Task Commits

Each task was committed atomically:

1. **Task 1: Next.js API proxy routes** — `77954d9` (feat)
2. **Task 2: Health badges, HealthTab, scan trigger** — `fd9fd14` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `workspace/occc/src/app/api/memory/health-scan/route.ts` — Created: POST proxy to memU health-scan
- `workspace/occc/src/app/api/memory/[id]/route.ts` — Added PUT handler alongside DELETE
- `workspace/occc/src/components/memory/HealthTab.tsx` — Created: summary bar, flag list, scan trigger
- `workspace/occc/src/components/memory/MemoryPanel.tsx` — Added health state, tab bar, runHealthScan, scheduled interval, filter toggle
- `workspace/occc/src/components/memory/MemoryRow.tsx` — Added healthFlag prop and badge rendering
- `workspace/occc/src/components/memory/MemoryTable.tsx` — Added healthFlags prop threading and Health column header

## Decisions Made

- `HealthFlag` interface exported from `HealthTab.tsx` as the single source of truth — Panel, Row, and Table all import from one location, avoiding duplicate type definitions that could drift.
- `healthFlags` uses `Map<string, HealthFlag>` keyed by `memory_id` for O(1) lookup per row render — no `.find()` traversal on every MemoryRow.
- `runHealthScan` wrapped in `useCallback` with `healthSettings` as dependency — prevents stale closure in scheduled `setInterval` effect.
- `handleOpenConflict` and `handleOpenSettings` emit `toast.info` placeholders — conflict modal and settings modal are deferred (not in QUAL-04/05 scope).
- Scheduled interval guards on `activeTab === 'health'` AND `projectId` non-null — prevents unnecessary scans on the list tab or before project selection.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed present:
- `~/.openclaw/workspace/occc/src/app/api/memory/health-scan/route.ts` — FOUND
- `~/.openclaw/workspace/occc/src/app/api/memory/[id]/route.ts` — FOUND (contains PUT)
- `~/.openclaw/workspace/occc/src/components/memory/HealthTab.tsx` — FOUND
- `~/.openclaw/workspace/occc/src/components/memory/MemoryPanel.tsx` — FOUND (contains healthFlags)
- `~/.openclaw/workspace/occc/src/components/memory/MemoryRow.tsx` — FOUND (contains flag_type)
- `~/.openclaw/workspace/occc/src/components/memory/MemoryTable.tsx` — FOUND

Commits confirmed present:
- `77954d9` — FOUND
- `fd9fd14` — FOUND

TypeScript: 0 errors in modified files (pre-existing SummaryStream.tsx error unrelated)

---
*Phase: 40-memory-health-monitor*
*Completed: 2026-02-24*
