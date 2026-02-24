---
phase: 02-source-connectivity-incremental-sync
plan: 04
subsystem: ui
tags: [connectors, sync-health, recovery, dashboard, nextjs]
requires:
  - phase: 02-source-connectivity-incremental-sync
    provides: shared incremental sync engine, persisted checkpoints/progress, normalized health ordering
provides:
  - Shared connector health endpoint aggregating stage, counters, throughput, retry/backoff, and checkpoint context
  - Dual visibility surfaces for sync state (settings dashboard + always-visible header indicator) backed by one hook/API source
  - Persistent recovery cards with auth-expired hard-stop/reconnect CTA and resume-from-checkpoint guidance
  - Transient completion/failure sync toasts aligned with persistent recovery state
affects: [phase-02, connectors, settings-ui, header-ui, sync-runtime]
tech-stack:
  added: []
  patterns:
    - Shared health/progress endpoint consumed by all sync-status UI surfaces
    - Recovery UX combines transient notifications with persistent action cards
key-files:
  created:
    - src/app/api/connectors/health/route.ts
    - src/lib/hooks/useSyncStatus.ts
    - src/components/connectors/SyncDashboard.tsx
    - src/components/layout/HeaderSyncStatus.tsx
    - src/components/common/SyncToast.tsx
    - tests/connectors/sync-status.test.tsx
  modified:
    - src/app/settings/connectors/page.tsx
    - src/components/layout/Header.tsx
key-decisions:
  - "Both compact and detailed sync surfaces consume `/api/connectors/health` to keep status ordering and semantics identical."
  - "Recovery cards preserve last checkpoint/source context so retry/resume behavior is explicit and confidence-building."
  - "`auth_expired` is treated as a hard-stop state for retry/resume and always presents reconnect CTA while retaining last successful sync context."
patterns-established:
  - "Status priority ordering remains locked across backend + UI (`auth_expired > error > rate_limited > syncing > connected > disconnected`)."
  - "Connector actions resolve provider-aware sync routes from one hook (`slack`, `tracker`, fallback by connector id)."
requirements-completed: [INTG-04, PERF-02, INTG-03]
duration: 3min
completed: 2026-02-24
---

# Phase 02: Source Connectivity & Incremental Sync Summary

**Sync visibility now ships as a shared health/status system with dual UI surfaces, actionable recovery controls, and completion/failure notifications backed by preserved checkpoint context.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-24T14:13:02Z
- **Completed:** 2026-02-24T14:15:15Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Added `/api/connectors/health` to aggregate connector progress snapshots, counters, stage, throughput, retry/backoff metadata, and checkpoint context.
- Added `useSyncStatus` and connected both `SyncDashboard` and `HeaderSyncStatus` to one truth source for consistent status priority rendering.
- Added persistent recovery cards (`Retry`, `Reconnect`, `Resume now`) with auth-expired hard-stop behavior and explicit checkpoint-based resume messaging.
- Added transient sync completion/failure toasts via `SyncToast` while keeping persistent cards for ongoing recovery context.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build sync dashboard and compact status indicator powered by a shared health/progress API** - `7ec4c4d` (feat)
2. **Task 2: Add persistent recovery cards and transient toasts for completion/failure and resume actions** - `593921b` (feat)

## Files Created/Modified
- `src/app/api/connectors/health/route.ts` - Aggregated connector health/progress endpoint for dashboard + header.
- `src/lib/hooks/useSyncStatus.ts` - Shared polling hook, status-priority helpers, and provider-aware sync/reconnect action mapping.
- `src/components/connectors/SyncDashboard.tsx` - Detailed sync surface with counters, stage, throughput, retry/backoff, per-source rows, and persistent recovery cards.
- `src/components/layout/HeaderSyncStatus.tsx` - Always-visible compact traffic-light sync indicator.
- `src/components/common/SyncToast.tsx` - Transient completion/failure notifications based on status transitions.
- `src/app/settings/connectors/page.tsx` - Integrates dashboard, toast observer, and reconnect anchors for provider sections.
- `src/components/layout/Header.tsx` - Injects compact sync status indicator into global header.
- `tests/connectors/sync-status.test.tsx` - Validates status ordering, route mapping, payload aggregation, and auth-expired recovery semantics.

## Decisions Made
- Keep dual sync visibility surfaces coupled to one API/hook source to avoid semantic drift in health priority or progress meaning.
- Compute/reveal retry backoff metadata in health payload so users get actionable context beyond generic failure states.
- Keep reconnect actions explicit and provider-targeted through connector section anchors while hard-blocking auth-expired retry/resume.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 sync visibility and recovery UX requirements are now covered by shared backend/frontend status semantics.
- Remaining Phase 2 execution can proceed to `02-05` with connector observability/recovery baselines now established.

---
*Phase: 02-source-connectivity-incremental-sync*
*Completed: 2026-02-24*
