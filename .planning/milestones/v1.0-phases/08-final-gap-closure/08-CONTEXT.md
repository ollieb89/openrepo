# Phase 8: Final Gap Closure - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all remaining v1.0 audit gaps: fix SSE client payload handling (DSH-02), create pumplai_pm L2 config (HIE-02), and formalize COM-02 spec deviation acceptance. Three targeted fixes to reach 16/16 requirements satisfied and 5/5 E2E flows complete.

</domain>

<decisions>
## Implementation Decisions

### SSE Payload Handling (DSH-02)
- SSE becomes the **primary data path** — `useSwarmState.ts` directly consumes `{agents, metrics, state, lastUpdated}` from SSE events instead of using SSE as a nudge to trigger SWR revalidation
- SWR polling demoted to **fallback only** — kicks in when SSE disconnects, not as a parallel data source
- **Both server and client fixed** — server-side `/api/swarm/stream` must emit full `{agents, metrics, state, lastUpdated}` payloads; client-side hook must parse and apply them directly
- The current `data.updated` nudge pattern is replaced entirely

### L2 Config Structure (HIE-02)
- **Mirror L3 config schema** — same top-level keys (`id`, `name`, `level`, `reports_to`, `skill_registry`, etc.) with L2-appropriate values
- **Skill registry** includes three skills: `spawn_specialist`, `router`, and `review` (for L3 work review/merge decisions)
- **Both hierarchy directions explicit**: `reports_to: "clawdia_prime"` AND `delegates_to: "l3_specialist"`
- **File location**: `agents/pumplai_pm/agent/config.json` (alongside existing IDENTITY.md and SOUL.md)
- No container/runtime fields (L2 is persistent, not ephemeral)

### COM-02 Deviation Formalization
- **Preserve original requirement text** in REQUIREMENTS.md with deviation annotation: "Deviation: CLI routing replaces lane queues. Accepted [date]." — maintains audit trail
- **Update both documents**: REQUIREMENTS.md (mark SATISFIED with deviation note) AND v1.0-MILESTONE-AUDIT.md (reflect 16/16 satisfied)
- Status column changes from "Pending" to "Satisfied" with deviation note

### Claude's Discretion
- Malformed SSE event handling strategy (ignore vs partial merge)
- Whether to show a connection mode indicator on the dashboard (polling vs live)
- Whether to accept the COM-02 deviation (recommended: accept — CLI routing functionally meets the intent) or implement lane queues
- Exact L2 config field values beyond the structural decisions above

</decisions>

<specifics>
## Specific Ideas

- The SSE fix should be end-to-end verifiable: emit from server, consume in client, display in dashboard — all in one flow
- L2 config should make the 3-tier hierarchy fully introspectable from config files alone (L1 lists subordinates, L2 lists reports_to + delegates_to, L3 lists reports_to + spawned_by)
- COM-02 annotation style should be consistent with how other requirement status changes are documented

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-final-gap-closure*
*Context gathered: 2026-02-23*
