---
phase: 02-source-connectivity-incremental-sync
plan: 01
subsystem: api
tags: [connectors, sync, checkpoints, health, progress]
requires:
  - phase: 01-04
    provides: project runtime/testing baseline and privacy-safe persistence boundaries
provides:
  - Durable connector runtime contracts and per-source checkpoint persistence.
  - Shared incremental sync engine with checkpoint-after-persist semantics and restart-safe progress snapshots.
  - Connector APIs for list/config fetch and manual sync-now execution through the shared engine.
affects: [connectors, sync-runtime, diagnostics, api, tests]
tech-stack:
  added: []
  patterns: [checkpoint-after-persist, per-source cursor keys, shared sync runner, normalized health classification]
key-files:
  created:
    - src/lib/types/connectors.ts
    - src/lib/connectors/store.ts
    - src/lib/sync/checkpoints.ts
    - src/lib/sync/health.ts
    - src/lib/sync/engine.ts
    - src/app/api/connectors/route.ts
    - src/app/api/connectors/[id]/sync/route.ts
    - .planning/phases/02-source-connectivity-incremental-sync/02-01-SUMMARY.md
  modified:
    - tests/connectors/sync-engine.test.ts
key-decisions:
  - "Connector runtime state/checkpoints/progress are persisted in one durable JSON store keyed by connector and source."
  - "Checkpoints advance only after successful upsert of each sync batch to guarantee safe resume semantics."
  - "Health transitions are normalized centrally (401/403 auth_expired, 429 rate_limited) with locked priority ordering for diagnostics/UI."
patterns-established:
  - "Use runIncrementalSync as the only manual sync-now execution path to avoid provider-specific one-offs in routes."
  - "Emit and persist per-source progress snapshots at each stage transition for restart-safe visibility."
requirements-completed: [INTG-03, INTG-04, PERF-02]
duration: 31 min
completed: 2026-02-24
---

# Phase 02 Plan 01: Connector Runtime Foundation and Resumable Sync Core Summary

**Shared connector sync runtime now persists source-scoped checkpoints and progress, resumes incrementally from saved cursors, and exposes sync-now through common connector APIs.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-02-24T13:25:00Z
- **Completed:** 2026-02-24T13:56:01Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Added typed connector runtime contracts covering source scope, cursors, health states, and progress snapshots.
- Implemented persistent connector state/checkpoint/progress storage with per-connector and per-source keying.
- Built a shared incremental sync engine and wired connector APIs (`/api/connectors`, `/api/connectors/[id]/sync`) to use it.
- Added sync-engine tests for source checkpoint separation, checkpoint-after-persist behavior, resumable runs, progress snapshots, and normalized health transitions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define connector, cursor, and health contracts with persistent store support** - `03595b6` (feat)
2. **Task 2: Implement shared incremental engine and sync-now endpoint with checkpoint-after-persist semantics** - `0482644` (feat)

## Files Created/Modified
- `src/lib/types/connectors.ts` - Connector runtime contracts for health, checkpoints, stages, and progress.
- `src/lib/connectors/store.ts` - Durable JSON-backed connector runtime store for connector state, checkpoints, and progress snapshots.
- `src/lib/sync/checkpoints.ts` - Source-aware checkpoint load/save primitives and key builder.
- `src/lib/sync/health.ts` - Shared health classifier and priority utilities.
- `src/lib/sync/engine.ts` - Shared incremental sync runner with checkpoint-after-persist and progress snapshot emission.
- `src/app/api/connectors/route.ts` - Connector listing/config fetch route with checkpoint/progress response support.
- `src/app/api/connectors/[id]/sync/route.ts` - Manual sync-now trigger route backed by shared sync engine.
- `tests/connectors/sync-engine.test.ts` - Regression coverage for resumable sync semantics and health normalization.

## Decisions Made
- Implemented source-aware checkpoint keying as `connectorId::sourceId` to prevent cursor collisions across sources.
- Kept progress snapshots persistent and stage-based (`loading_checkpoint`, `scanning`, `persisting`, `saving_checkpoint`, `completed`) so UI/diagnostics can recover after interruption.
- Centralized health normalization and priority handling into `src/lib/sync/health.ts` for reuse across adapters/routes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Runtime store path needed lazy resolution for test/runtime isolation**
- **Found during:** Task 1 verification
- **Issue:** Store path was resolved at import time, preventing test override via `CONNECTOR_RUNTIME_STORE_PATH` and causing permission errors.
- **Fix:** Switched to lazy store path resolution for each read/write operation.
- **Files modified:** `src/lib/connectors/store.ts`
- **Verification:** `npm run test -- tests/connectors/sync-engine.test.ts`
- **Committed in:** `03595b6`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for reliable verification and environment-safe persistence behavior; no scope expansion.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 02-01 foundation is complete for resumable connector sync orchestration.
- Next plans can implement provider-specific Slack/tracker adapters on top of shared runtime primitives and APIs.

## Self-Check: PASSED
- Key files exist on disk (`src/lib/sync/checkpoints.ts`, `src/lib/sync/health.ts`, `src/lib/sync/engine.ts`, `src/app/api/connectors/[id]/sync/route.ts`).
- Plan commits found: `03595b6`, `0482644`.
- Required verification passed: `npm run lint` and `npm run test -- tests/connectors/sync-engine.test.ts`.

---
*Phase: 02-source-connectivity-incremental-sync*
*Completed: 2026-02-24*
