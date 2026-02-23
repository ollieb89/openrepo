# Phase 9: Integration Wiring Cleanup - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix all 3 cross-phase integration debt items (INT-01, INT-02, INT-03) surfaced by the v1.0 milestone audit integration checker. This phase wires existing pieces together correctly — no new capabilities, just making the existing L1/L2/L3 hierarchy, skill registry, and container management actually connect as designed.

</domain>

<decisions>
## Implementation Decisions

### Agent hierarchy schema (INT-01)
- Add `level` and `reports_to` fields **inline on each agent entry** in `openclaw.json`
- `level` uses **numeric values: 1, 2, 3** — matches existing L1/L2/L3 naming convention
- `reports_to` is an **agent ID string, null for L1** (e.g. L3 specialist `reports_to: "pumplai_pm"`, L2 `reports_to: "clawdia_prime"`, L1 `reports_to: null`)
- **Validate `reports_to` references on load** — warn if an agent references a `reports_to` ID that doesn't exist in the agents list. Catches typos and broken wiring early.

### Phantom skill resolution (INT-02)
- **Create `skills/review_skill/`** as a stub (do NOT remove the config reference)
- Stub is **Python** — aligns with L2 PumplAI_PM's Python-based orchestration layer and spawn_specialist pattern
- Follows the **same directory structure** as existing skills (router_skill, spawn_specialist) — config registration, entry point convention
- When invoked: **log the review request and return success** — non-blocking acknowledged response

### Container label strategy (INT-03)
- Set **`openclaw.managed=true`** plus **`openclaw.task_id`** and **`openclaw.level=3`** labels on spawned containers in `spawn.py`
- Use **`openclaw.*` prefix namespace** for all labels — prevents collisions with other Docker tooling
- **No backward compatibility needed** — L3 containers are ephemeral, old unlabeled containers clean up naturally
- `listSwarmContainers` filters by **label only** — single source of truth, no name pattern fallback

### Cross-fix coordination
- **Separate commits per INT item** — one commit per fix for clean audit trail, easier review/revert/bisect
- **Manual smoke test per fix** — verify: 1) hierarchy renders, 2) review_skill responds, 3) container has labels, 4) no WARN on delegation
- COM-01 delegation WARN fix validated with successful roundtrip after schema change

### Claude's Discretion
- COM-01 WARN fix location — Claude investigates the actual WARN source and fixes wherever it originates (router_skill sender vs receiving agent consumer)
- Execution ordering of INT-01/INT-02/INT-03 — Claude determines optimal sequence based on dependencies
- Internal structure of review_skill stub (exact logging format, response schema)
- Validation error severity (WARN vs FATAL for invalid `reports_to` references)

</decisions>

<specifics>
## Specific Ideas

- Validation should use DFS or similar to detect circular `reports_to` chains (agent reporting to itself or sub-agent)
- Labels should include `openclaw.level` on containers so monitoring can distinguish L3 specialist containers from other Docker workloads
- The stub review_skill should be minimal but discoverable — future phases can flesh it out into actual review functionality

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-integration-wiring-cleanup*
*Context gathered: 2026-02-23*
