---
phase: 02-source-connectivity-incremental-sync
plan: 03
subsystem: api
tags: [connectors, github, linear, incremental-sync, nextjs]

requires:
  - phase: 02-source-connectivity-incremental-sync
    provides: shared connector runtime, checkpoint persistence, health normalization
provides:
  - Tracker adapter abstraction with provider config validation
  - GitHub Issues incremental tracker adapter using update-time checkpoint cursor
  - Linear incremental tracker adapter using paginated GraphQL updates
  - Tracker connector API + UI for provider selection, connect/reconnect, and sync trigger
affects: [phase-02, connectors, sync-engine, settings-ui]

tech-stack:
  added: []
  patterns:
    - Provider-specific adapters delegated through a shared incremental sync engine
    - Tracker metadata configuration validated before adapter execution

key-files:
  created:
    - src/lib/connectors/tracker.ts
    - src/lib/connectors/tracker-github.ts
    - src/lib/connectors/tracker-linear.ts
    - src/app/api/connectors/tracker/route.ts
    - src/app/api/connectors/tracker/sync/route.ts
    - src/components/connectors/TrackerConnectorCard.tsx
    - tests/connectors/tracker-adapter.test.ts
  modified: []

key-decisions:
  - "GitHub incremental cursor is keyed by (updatedAt, recordId) so reopened/closed/edited issues are re-ingested safely."
  - "Linear incremental sync uses GraphQL pagination with updatedAt filtering and the same cursor tuple for dedupe."
  - "Tracker connector API keeps one canonical connector id (`connector-tracker`) and exposes explicit `auth_expired` reauth signaling for UI."

patterns-established:
  - "Tracker adapters expose normalized records and rely on shared health classification in sync engine error handling."
  - "Connector card health presentation preserves explicit auth/rate-limit/error semantics instead of collapsing to generic failures."

requirements-completed: [INTG-02, INTG-03]

duration: 4min
completed: 2026-02-24
---

# Phase 02: Source Connectivity & Incremental Sync Summary

**Tracker connectivity now supports GitHub Issues and Linear with update-time incremental ingestion and explicit connector health UX for connect/reconnect/sync flows**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-24T14:00:30Z
- **Completed:** 2026-02-24T14:04:37Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added provider-agnostic tracker connector primitives and config validation.
- Implemented incremental tracker adapters for GitHub and Linear with checkpointed changed-record capture.
- Added tracker connector API/UI flow for provider selection, sync-now, and explicit `auth_expired` reconnect behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement tracker adapter layer and provider-specific incremental sync for GitHub and Linear** - `6ec1d91` (feat)
2. **Task 2: Add tracker connector API and UI for provider selection, connect state, and sync control** - `1032274` (feat)

## Files Created/Modified
- `src/lib/connectors/tracker.ts` - Tracker provider abstraction, config parsing, and request helpers.
- `src/lib/connectors/tracker-github.ts` - GitHub Issues incremental adapter using updated-at cursor semantics.
- `src/lib/connectors/tracker-linear.ts` - Linear GraphQL incremental adapter with pagination + updated-at filters.
- `src/app/api/connectors/tracker/route.ts` - Tracker configuration API and state payload endpoint.
- `src/app/api/connectors/tracker/sync/route.ts` - Tracker sync trigger route delegating to shared sync engine.
- `src/components/connectors/TrackerConnectorCard.tsx` - Provider-selectable connector UI with connect/reconnect/sync controls.
- `tests/connectors/tracker-adapter.test.ts` - Adapter coverage for changed-record re-ingestion, pagination, and health mapping.

## Decisions Made
- Use tuple cursor ordering (`updatedAt`, `recordId`) in both tracker adapters to avoid duplicate replay while still capturing same-item updates.
- Keep one logical tracker connector state id (`connector-tracker`) and treat provider as mutable configuration.
- Expose non-collapsed health labels in UI to keep `auth_expired` actionable and distinct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Repository pathing differed from planned connector layout**
- **Found during:** Task 2 (Tracker connector UI/API integration)
- **Issue:** Planned settings page path was absent in this workspace; tracker UI needed to be delivered as reusable component/API first.
- **Fix:** Implemented owned tracker API + card component paths without editing unowned settings page files.
- **Files modified:** `src/app/api/connectors/tracker/route.ts`, `src/components/connectors/TrackerConnectorCard.tsx`
- **Verification:** `npm run lint` passed.
- **Committed in:** `1032274`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Core plan behavior shipped; connector card is ready for page integration where ownership allows.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tracker adapter and connector APIs are in place for continued Phase 2 provider integration.
- Remaining Phase 2 plans should integrate the tracker card into owned settings surfaces and complete remaining connectivity tasks.

---
*Phase: 02-source-connectivity-incremental-sync*
*Completed: 2026-02-24*
