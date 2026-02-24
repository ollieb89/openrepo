---
phase: 01-local-first-core-privacy-guardrails
plan: 03
subsystem: privacy
tags: [privacy, minimization, provenance, persistence, metadata]
requires:
  - phase: 01-01
    provides: guard-first privacy boundaries and project-scoped consent controls
provides:
  - Allowlist-based persistence minimization contract with default raw-content rejection.
  - Provenance defaults (source link, timestamp, connector label) on persisted metadata records.
  - OpenClaw persistence write helper that stores only minimized metadata records.
affects: [privacy, persistence, ingestion, trust-signals]
tech-stack:
  added: []
  patterns: [allowlist persistence contract, provenance defaults, raw-content write rejection]
key-files:
  created:
    - src/lib/privacy/minimization.ts
    - tests/privacy/minimization.test.ts
  modified:
    - src/lib/openclaw.ts
    - src/lib/types.ts
    - src/lib/types/privacy.ts
key-decisions:
  - "Raw-content/body-like fields are rejected by default at persistence boundaries; strip behavior is opt-in only for controlled callers."
  - "Persisted metadata contracts require provenance defaults so trust signals are always present even when upstream payloads omit them."
patterns-established:
  - "Persistence write paths must invoke minimization before writing to disk."
  - "Only source/thread/time/connector/entity/provenance fields are retained for persisted metadata records."
requirements-completed: [PRIV-01, PRIV-03]
duration: 12 min
completed: 2026-02-24
---

# Phase 01 Plan 03: Metadata Minimization and Provenance Defaults Summary

**Allowlist-only metadata persistence with default raw-content rejection and guaranteed provenance defaults for trust visibility**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-24T12:43:30Z
- **Completed:** 2026-02-24T12:55:36Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- Added a typed minimization module that retains only allowlisted persistence fields and rejects raw/body content by default.
- Wired minimization into an OpenClaw write path (`appendMinimizedRecord`) so disk writes enforce metadata-only storage.
- Added regression tests for reject-by-default behavior, strip mode, nested raw-field blocking, and provenance defaulting.

## Task Commits

Each task was committed atomically:

1. **Task 1: Enforce metadata-minimization contracts for storage and provenance fields** - `bac29b3` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `src/lib/privacy/minimization.ts` - Allowlist minimization logic, raw-content key detection, and provenance defaults.
- `src/lib/openclaw.ts` - Added minimized metadata write helper that rejects raw fields before persistence.
- `src/lib/types/privacy.ts` - Added persisted metadata/provenance contracts and raw-content mode types.
- `src/lib/types.ts` - Added persisted task record type using the privacy metadata contract.
- `tests/privacy/minimization.test.ts` - Regression tests covering reject/strip/default provenance behaviors.

## Decisions Made
- Enforced fail-closed persistence defaults (`reject`) for raw content and body-like fields.
- Required provenance defaults (source link, timestamp, connector label) on persisted metadata records.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `PRIV-03` storage minimization contract is now implemented and regression-tested.
- Remaining phase work is `01-02` for privacy center/audit UX completion.

---
*Phase: 01-local-first-core-privacy-guardrails*
*Completed: 2026-02-24*
