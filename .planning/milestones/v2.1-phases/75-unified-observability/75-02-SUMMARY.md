---
phase: 75-unified-observability
plan: "02"
subsystem: dashboard-pipeline-timeline
tags: [typescript, react, nextjs, vitest, tdd, pipeline, metrics]
dependency_graph:
  requires: [75-01]
  provides: [pipeline-timeline-ui, pipeline-strip-component, task-pulse-expand]
  affects: [dashboard-metrics-page, dashboard-mission-control]
tech_stack:
  added: []
  patterns: [useSWR-per-task-cache-key, pure-function-export-for-testing, inner-subcomponent-unconditional-hook]
key_files:
  created:
    - packages/dashboard/src/lib/hooks/usePipeline.ts
    - packages/dashboard/src/components/metrics/PipelineStrip.tsx
    - packages/dashboard/src/components/metrics/PipelineSection.tsx
    - packages/dashboard/tests/api/pipeline/pipeline-filter.test.ts
    - packages/dashboard/tests/components/metrics/PipelineStrip.test.ts
    - packages/dashboard/tests/components/mission-control/TaskPulse.test.ts
  modified:
    - packages/dashboard/src/app/api/pipeline/route.ts
    - packages/dashboard/src/components/mission-control/TaskPulse.tsx
    - packages/dashboard/src/app/metrics/page.tsx
decisions:
  - "ExpandedPipelineRow inner subcomponent calls usePipeline unconditionally to avoid conditional hook violation"
  - "matchesStageFilter returns false (not 'all' impossible type) when no active stage found"
  - "TaskPulse includes failed/escalating tasks in visible list — operators need to see failures"
  - "Auto-expand tracks tasks where shouldAutoExpand passes on initial mount via taskIdKey derived key"
metrics:
  duration: "6min"
  completed_date: "2026-03-05"
  tasks_completed: 3
  files_modified: 9
  tests_added: 10
---

# Phase 75 Plan 02: Pipeline Timeline UI Summary

Pipeline timeline UI (OBSV-02) built with shared PipelineStrip component (6 equal-width segments, status coloring), inline task expand in TaskPulse on Mission Control, and PipelineSection aggregate view on Metrics page — all backed by a per-task SWR hook with filtered /api/pipeline endpoint.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Test scaffolds + filterPipelines + usePipeline hook | 7026501 | route.ts, usePipeline.ts, 3 test files |
| 2 | PipelineStrip + PipelineSection components | 957f15f | PipelineStrip.tsx, PipelineSection.tsx |
| 3 | TaskPulse inline expand + Metrics page wiring | 5ec00ce | TaskPulse.tsx, metrics/page.tsx |

## Artifacts Delivered

- **`/api/pipeline/route.ts`**: Added `filterPipelines(pipelines, taskId?)` named export; handler uses it replacing inline `slice(0,20)`. `?taskId=X` returns single matching task; omitted returns up to 20.
- **`usePipeline`**: SWR hook with per-task cache key `/api/pipeline?project=${p}&taskId=${t}`, 5s refresh when filtering by task, 10s otherwise.
- **`PipelineStrip`**: 6 `flex-1` segments in a `flex gap-0.5 w-full` container. `getPipelineStripSegmentClass(status)` exported pure function for testing (green/blue+pulse/red/dashed-gray). Duration labels below strip only when `stage.duration !== undefined`. `compact` prop switches h-3/h-4. Incomplete timing warning icon for non-pending stages missing timestamp.
- **`PipelineSection`**: Aggregate pipeline list on Metrics page. Client-side filters: status, stage (L1/L2/L3), duration bucket (<30s/30s-5m/>5m). Loading skeleton, empty state, max 20 items.
- **`TaskPulse`**: `getExpandedIds(prev, taskId, shiftKey)` exported pure function. Click expands/collapses, shift-click multi-expand, keyboard Enter/Space, chevron indicator. `ExpandedPipelineRow` inner subcomponent renders PipelineStrip + elapsed/stage/retry metadata + View logs + Retry stub. Failed/escalating tasks included in visible list. Auto-expand on mount for failed/escalating and in_progress tasks with L2 elapsed > 60s.

## Tests

| Suite | Tests | Result |
|-------|-------|--------|
| pipeline-filter | 2 | GREEN |
| PipelineStrip | 5 | GREEN |
| TaskPulse | 3 | GREEN |
| Total new | 10 | GREEN |
| Full suite | 125/127 | 2 pre-existing connector failures |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript error in PipelineSection — comparison of non-overlapping types**
- **Found during:** Task 3 (tsc check)
- **Issue:** `matchesStageFilter` returned `stageFilter === 'all'` in the no-active-stage branch, but at that point `stageFilter` is already known to be `'L1' | 'L2' | 'L3'` (guard above), making the comparison impossible per TS narrowing
- **Fix:** Changed to return `false` when no active stage found
- **Files modified:** `packages/dashboard/src/components/metrics/PipelineSection.tsx`
- **Commit:** 5ec00ce

**2. [Rule 1 - Bug] TypeScript error in TaskPulse — implicit any on pipeline stages find callback**
- **Found during:** Task 3 (tsc check)
- **Issue:** `pipeline?.stages?.find(s => ...)` without explicit type annotation gave `s` an implicit `any` type
- **Fix:** Added explicit type annotation `(s: { status: string })` on callback parameter
- **Files modified:** `packages/dashboard/src/components/mission-control/TaskPulse.tsx`
- **Commit:** 5ec00ce

## Self-Check: PASSED

- [x] All 9 key files exist on disk
- [x] All 3 task commits present in git log (7026501, 957f15f, 5ec00ce)
- [x] 10 new tests GREEN; full suite 125/127 (pre-existing connector failures out of scope)
- [x] tsc --noEmit: 0 new source errors (pre-existing .next/types error unchanged)
