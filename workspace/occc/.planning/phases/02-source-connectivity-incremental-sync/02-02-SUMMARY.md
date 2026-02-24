---
phase: 02-source-connectivity-incremental-sync
plan: 02
subsystem: api
tags: [slack, connectors, oauth, incremental-sync, ui]
requires:
  - phase: 02-01
    provides: shared connector runtime, checkpoint persistence, health normalization, and sync engine delegation
provides:
  - Slack workspace OAuth/connect flow with persisted connector metadata.
  - Slack channel discovery and persisted selected-channel sync scope.
  - Slack incremental sync adapter using timestamp cursors and first-sync window semantics via shared sync engine.
  - Connectors settings UI card for connect/scope/sync-now with shared health-status messaging.
affects: [connectors, sync-runtime, settings-ui, api, tests]
tech-stack:
  added: []
  patterns: [single-workspace slack connector id, channel-scoped source selection, first-sync-window defaulting, shared health status UX]
key-files:
  created:
    - src/lib/connectors/slack.ts
    - src/app/api/connectors/slack/oauth/route.ts
    - src/app/api/connectors/slack/channels/route.ts
    - src/app/api/connectors/slack/sync/route.ts
    - src/components/connectors/SlackConnectorCard.tsx
    - src/lib/hooks/useConnectorStatus.ts
    - src/app/settings/connectors/page.tsx
    - tests/connectors/slack-adapter.test.ts
    - .planning/phases/02-source-connectivity-incremental-sync/02-02-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md
key-decisions:
  - "Slack integration is anchored to one persisted connector id (`connector-slack-primary`) to enforce single-workspace scope."
  - "Slack sync route always delegates ingestion execution to `runIncrementalSync` so checkpoint-after-persist and health normalization remain centralized."
  - "Connector settings UI reuses existing shared statuses (`connected`, `syncing`, `rate_limited`, `auth_expired`, `error`, `disconnected`) and maps only actionable hint text."
patterns-established:
  - "Provider adapter modules own provider API semantics (OAuth/channel/history) and register once into the shared sync engine."
  - "Channel scope persistence writes selected channel ids into connector metadata and resets runtime source list for re-discovery."
requirements-completed: [INTG-01, INTG-03]
duration: 28 min
completed: 2026-02-24
---

# Phase 02 Plan 02: Slack Connectivity and Channel-Scoped Incremental Ingestion Summary

**Slack connectivity now supports one-workspace OAuth, persisted channel-scoped sync, and incremental timestamp-based ingestion surfaced through connectors settings UI with shared health semantics.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-02-24T13:36:00Z
- **Completed:** 2026-02-24T14:04:15Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Implemented a Slack adapter with OAuth token metadata usage, channel discovery, selected-channel filtering, and timestamp-cursor incremental history scanning.
- Added Slack API routes for OAuth connect, channel scope read/write, and sync-now execution through the shared incremental sync engine.
- Added connectors settings UI (`SlackConnectorCard`) and `useConnectorStatus` hook for connect, channel selection, first-sync window, sync-now, and health/action hints.
- Added adapter tests validating selected-channel scope and incremental cursor/window behavior; reran sync-engine regression tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement Slack adapter, OAuth/connect routes, and channel-scope persistence** - `03c695f` (feat)
2. **Task 2: Add Slack connector card UX for connect state, channel scope, and sync-now control** - `d7da534` (feat)

## Files Created/Modified
- `src/lib/connectors/slack.ts` - Slack adapter, OAuth workspace connect, channel selection persistence, adapter registration, and status hint utilities.
- `src/app/api/connectors/slack/oauth/route.ts` - OAuth code exchange entrypoint for Slack workspace connection.
- `src/app/api/connectors/slack/channels/route.ts` - Channel discovery response + selected channel scope persistence endpoint.
- `src/app/api/connectors/slack/sync/route.ts` - Slack sync-now endpoint that enforces first-run window semantics and delegates to shared sync engine.
- `src/components/connectors/SlackConnectorCard.tsx` - Connector card UI for status, connect, scope selection, and manual sync.
- `src/lib/hooks/useConnectorStatus.ts` - SWR-based connector/channel status hook with connect/save/sync actions.
- `src/app/settings/connectors/page.tsx` - Connectors settings page hosting Slack connector management UI.
- `tests/connectors/slack-adapter.test.ts` - Adapter tests for first-sync window and incremental resume cursor behavior.

## Decisions Made
- Kept one-workspace enforcement via fixed connector id (`connector-slack-primary`) rather than allowing multiple Slack connector records.
- Stored channel selection and first-sync window in connector metadata and used source rediscovery to honor changes without bespoke cache invalidation paths.
- Kept UI state naming aligned to existing shared health statuses and only added hint text for actionable errors (`rate_limited`, `auth_expired`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Planned Slack file set did not exist in repository baseline**
- **Found during:** Task 1 setup
- **Issue:** Plan-targeted Slack adapter/routes/tests files were absent, which blocked direct modification flow.
- **Fix:** Created the planned files at the specified paths and wired them to existing shared connector runtime primitives.
- **Files modified:** `src/lib/connectors/slack.ts`, `src/app/api/connectors/slack/oauth/route.ts`, `src/app/api/connectors/slack/channels/route.ts`, `src/app/api/connectors/slack/sync/route.ts`, `tests/connectors/slack-adapter.test.ts`
- **Verification:** `npm run lint && npm run test -- tests/connectors/slack-adapter.test.ts tests/connectors/sync-engine.test.ts`
- **Committed in:** `03c695f`

**2. [Rule 3 - Blocking] Client hook imported server-side connector module**
- **Found during:** Task 2 verification pass
- **Issue:** `useConnectorStatus` initially imported from `src/lib/connectors/slack.ts`, which is server-oriented and unsafe for client bundles.
- **Fix:** Replaced import with local connector id constant and kept hook client-safe.
- **Files modified:** `src/lib/hooks/useConnectorStatus.ts`
- **Verification:** `npm run lint`
- **Committed in:** `d7da534`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required for successful implementation in the current repository state; no scope creep beyond plan intent.

## Issues Encountered
None

## User Setup Required
Manual Slack app configuration is still required for live OAuth:
- Set `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` in runtime environment.
- Configure Slack app OAuth redirect URI to match the value used in connector settings.

## Next Phase Readiness
- Slack connector flow is present end-to-end for connect/scope/sync behavior and shared health-state visibility.
- Phase 02 can proceed with remaining tracker connector and higher-level integration plans (`02-03`, `02-04`).

## Self-Check: PASSED
- Key files exist on disk for this plan.
- Task commits present: `03c695f`, `d7da534`.
- Required verification passed for this plan's tasks.

---
*Phase: 02-source-connectivity-incremental-sync*
*Completed: 2026-02-24*
