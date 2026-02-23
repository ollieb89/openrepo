# Phase 5: Wiring Fixes & Initialization - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Close two specific integration gaps from the v1.0 milestone audit: fix broken L1→L2 delegation wiring (COM-01) and initialize the missing snapshots directory (COM-04). No new capabilities — just make existing components work together end-to-end.

</domain>

<decisions>
## Implementation Decisions

### L1 Config & Skill Registry
- Create a **full L1 config.json** (not minimal) — include identity ref, gateway endpoint, and other L1 settings alongside skill_registry
- Register **router_skill only** in skill_registry — other skills (spawn_specialist, etc.) are wired in future phases
- Config format and file location are Claude's discretion based on existing codebase patterns

### Delegation Flow Behavior
- "End-to-end" success = **gateway message roundtrip** — L1 sends through gateway, gets response back. Proves wiring works.
- Include **basic error handling** — clear error messages when gateway or L2 is unreachable (not just happy path)
- Gateway endpoint source for router_skill is Claude's discretion based on what exists
- Verification via **automated script** that tests the delegation flow and reports pass/fail

### Snapshots Directory Setup
- Directory creation must be **idempotent** — safe to run multiple times, checks existence first
- Whether to create empty or with baseline snapshot is Claude's discretion
- Bake into **startup integration** — snapshots dir is guaranteed to exist when system starts
- Verification via **automated test script** that creates a test snapshot and verifies capture

### Claude's Discretion
- Config.json format (whether to match L2 pattern or create L1-specific structure)
- Config.json file location (agents/clawdia_prime/agent/ or elsewhere)
- Router skill's gateway endpoint source (L1 config.json vs openclaw.json)
- Whether to seed snapshots dir with baseline snapshot or leave empty

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint: this is gap closure, not new features. Keep changes minimal and targeted.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-wiring-fixes*
*Context gathered: 2026-02-18*
