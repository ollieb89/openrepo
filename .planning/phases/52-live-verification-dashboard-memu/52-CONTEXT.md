# Phase 52: Live Verification — Dashboard & memU - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm v1.4 dashboard and memory features work end-to-end with live services. This is a verification phase covering 9 specific tests: health scan badges, conflict panel, suggestion acceptance, sidebar counts, settings persistence, and memU API integration. Fixes for discovered bugs happen in-phase. No new features.

</domain>

<decisions>
## Implementation Decisions

### Service prerequisites
- Plan includes full startup steps for dashboard and memU (not assumed running)
- Include a pre-flight health check (curl endpoints) to confirm services are up before running tests
- Use real data from an existing project (not seeded test data) — more realistic verification
- For test state setup: use API/CLI calls where straightforward (e.g., POST a memory), manual dashboard interaction for complex scenarios (e.g., triggering a conflict)

### Pass/fail evidence
- Structured JSON log per test with timestamps, status, and relevant response data
- Screenshots captured for all UI-based tests (health badges, conflict panel, sidebar badge, suggestions page)
- API tests: appropriate detail per test (full request+response for critical paths, status+key fields for simpler checks)

### Failure handling
- Run all 9 tests first (log and continue on failure), then address failures in priority order
- Bugs discovered during verification are fixed in-phase and re-verified — keeps the loop tight
- If memU or dashboard is unresponsive, plan includes basic troubleshooting before marking blocked

### Claude's Discretion
- Which project to use as test target (pick based on richest memory data)
- Storage location for verification log and screenshots (phase dir vs data dir — follow project conventions)
- Whether structured log records full run history (initial fail + fix + re-pass) or just final state
- API evidence detail level per test
- Service recovery troubleshooting depth

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 52-live-verification-dashboard-memu*
*Context gathered: 2026-02-25*
