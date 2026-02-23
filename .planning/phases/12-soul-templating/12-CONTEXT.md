# Phase 12: SOUL Templating - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate L2 agent identity (SOUL.md) files from a default template with variable substitution at project init time. Support per-project section-level overrides that merge with the default template. The existing PumplAI SOUL.md must be reproducible from template + override with semantically identical output to the v1.0 hardcoded file (golden baseline test).

</domain>

<decisions>
## Implementation Decisions

### Template structure
- Default template is a "generic L2 agent" — not PumplAI-specific
- PumplAI provides overrides to reproduce its current SOUL.md exactly
- New projects without overrides get the generic default with variables filled in
- Section structure at Claude's discretion (current 3-section pattern as starting point: HIERARCHY, CORE GOVERNANCE, BEHAVIORAL PROTOCOLS)
- Override granularity is at the ## section level — override replaces an entire section
- Title line (`# Soul: $agent_name ($tier)`) is auto-generated from variables, not overridable content

### Override merge behavior
- Override file uses same markdown format as SOUL.md — partial file with ## section headers for sections being replaced
- Sections NOT in the override are kept from the default template (additive override model)
- New sections in the override (not in default template) are allowed and appended to output
- Variable substitution ($project_name, $tech_stack_*, etc.) happens in both default template and override files

### Claude's Discretion
- Exact section names and content of the generic default template
- Variable naming beyond $project_name and $tech_stack_* (contract details)
- How missing/undefined variables are handled
- Renderer invocation method (CLI command, function call, etc.)
- Where rendered output is written
- Error handling for malformed overrides

</decisions>

<specifics>
## Specific Ideas

- The golden baseline test is critical: running the renderer against the PumplAI project must produce a file that diffs empty against the v1.0 hardcoded `agents/pumplai_pm/agent/SOUL.md`
- Override file location is `projects/<id>/soul-override.md` per requirements CFG-05

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-soul-templating*
*Context gathered: 2026-02-23*
