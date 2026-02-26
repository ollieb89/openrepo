# Phase 55: Self-Directed Task Decomposition - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable L3 agents to perform self-directed task breakdown and planning before executing tasks, keeping implementation strictly within the L3 lifecycle and utilizing Event Bus and state engine integrations.
</domain>

<decisions>
## Implementation Decisions

### Planning Format
- **Storage:** Emitted as an Event Bus payload
- **Emission:** Sent as a single complete plan event
- **Start Trigger:** Agent proceeds immediately to execution without blocking for orchestrator approval

### Execution Boundary
- **Processing:** Agent executes steps inline sequentially
- **Progress Tracking:** Sent via Event Bus updates
- **Detail Level:** Detailed metadata (output snippets, duration, confidence adjustments)
- **Timeouts:** Agent must emit heartbeat events for long-running steps

### Plan Validation
- **Method:** LLM self-reflection pass
- **Remediation:** Auto-regenerate plan with a configurable retry limit
- **Model:** Same Primary Model as the plan generation
- **Verification:** Agent is permitted to run read-only commands (e.g. `ls`, `cat`) to ground its assumptions statically

### Fallback Behavior
- **Immediate Reaction:** Auto-modify remaining steps and retry upon unexpected error
- **Scope:** Regenerate only the remaining steps, keeping completed ones untouched
- **Final Fallback:** Transition to BLOCKED and escalate to orchestrator
- **Intervention:** Orchestrator or human operator can directly edit the plan before unblocking

### Claude's Discretion
- **Format:** The exact structural format of the plan (e.g., JSON schema, Markdown lists) is left to Claude's discretion to optimize for prompt adherence and parsing reliability.
</decisions>

<specifics>
## Specific Ideas

No specific structural format requirements — open to standard approaches as long as it fits cleanly into the Event Bus payload.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope
</deferred>

---

*Phase: 55-self-directed-task-decomposition*
*Context gathered: 2026-02-26*
