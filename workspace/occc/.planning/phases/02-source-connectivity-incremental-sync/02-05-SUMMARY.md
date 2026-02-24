---
phase: 02-source-connectivity-incremental-sync
plan: 05
subsystem: scheduler
tags: [scheduler, background-sync, heartbeat, nextjs]
requires:
  - phase: 02-source-connectivity-incremental-sync
    provides: shared incremental sync engine, connector store, health normalization
provides:
  - Periodic background sync orchestration with 1-hour interval and health-state guards
  - Fire-and-forget background sync API endpoint (/api/connectors/sync/background)
  - Client-side BackgroundSyncTrigger component for automatic heartbeat while app is active
affects: [sync-runtime, api, layout]
tech-stack:
  added: []
  patterns:
    - Client-side heartbeat triggering server-side fire-and-forget background tasks
    - Singleton-style module-level lock for scheduler concurrency control
key-files:
  created:
    - src/lib/sync/scheduler.ts
    - src/app/api/connectors/sync/background/route.ts
    - src/components/sync/BackgroundSyncTrigger.tsx
    - tests/connectors/scheduler.test.ts
  modified:
    - src/app/layout.tsx
    - .planning/phases/02-source-connectivity-incremental-sync/PLAN.md
key-decisions:
  - "Use a client-side heartbeat (BackgroundSyncTrigger) to trigger the server-side scheduler, ensuring it runs without a separate dedicated cron process."
  - "Scheduler skips connectors in `syncing`, `rate_limited`, or `auth_expired` states to respect provider constraints and user health controls."
  - "Concurrency is managed via a simple module-level `isSyncRunning` lock to prevent redundant checks."
patterns-established:
  - "Background tasks are triggered by fire-and-forget API calls from the client heartbeat."
requirements-completed: [INTG-03, PERF-02]
duration: 10min
completed: 2026-02-24
---

# Phase 02 Plan 05: Background Sync Scheduler Summary

**Background sync is now automatic, using a client-side heartbeat to trigger a server-side scheduler that respects health-state guards and a 1-hour sync interval.**

## Accomplishments
- Implemented `runBackgroundSync` in `src/lib/sync/scheduler.ts` with interval checks and status filtering.
- Added `/api/connectors/sync/background` POST endpoint to expose the scheduler.
- Added `BackgroundSyncTrigger` client component and integrated it into the root layout for automatic periodic triggers.
- Verified scheduler logic with unit tests covering health guards and interval enforcement.

## Decisions Made
- Chose client-side heartbeat for simplicity in a Next.js environment without a persistent server process, while still providing "active session" background sync.
- Implemented fire-and-forget execution in the scheduler to avoid blocking the API response while long-running syncs proceed.

## Issues Encountered
- `bun test` module mocking syntax differed from Vitest; corrected by using `mock.module` and `mock.restore`.

## Next Phase Readiness
- Phase 2 is now feature-complete, including automatic background synchronization.
- System is ready for Phase 3: Decision Summaries with Provenance.
