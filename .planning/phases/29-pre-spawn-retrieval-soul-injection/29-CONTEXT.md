# Phase 29: Pre-Spawn Retrieval + SOUL Injection - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Before an L3 container is created, retrieve relevant memories from memU and inject them into the SOUL template so the agent starts with accumulated context from past tasks. The retrieval happens in spawn.py, formatted as a markdown section, and delivered to the container via a mounted temp file. Graceful degradation when memU is unavailable.

</domain>

<decisions>
## Implementation Decisions

### Retrieval query strategy
- Retrieval scoped to current project only (project_id filter) — no cross-project memories
- Query composition (task description, skill hint, combination): Claude's discretion
- Number of results to fetch: Claude's discretion (balance with 2,000-char budget)
- Relevance threshold (cutoff vs inject all): Claude's discretion

### Memory section formatting
- Bullet list format under a `## Memory Context` section header
- Each bullet includes a short source tag, e.g., `(from L2 review)` or `(memorized 2d ago)`
- When no memories are retrieved, the section is hidden entirely — no header, no placeholder, blank render
- Matches success criterion 4: `$memory_context` renders as blank when empty

### Spawn-time rendering flow
- Memory retrieval and injection happens in `spawn.py` before container creation — `soul_renderer.py` stays unchanged
- spawn.py calls memU `/retrieve`, formats the memory bullets, then writes a memory-augmented SOUL to a temp file
- Temp file mounted read-only into the L3 container; L3 entrypoint reads it at a known path
- Sync vs async retrieval timing: Claude's discretion (must degrade gracefully per RET-04)
- Logging: log count + total char count on injection, e.g., "Injected 4 memories (1,847 chars) into SOUL"

### Budget allocation
- Pure relevance-ranked ordering from memU — no type-based priority or reserved slots
- Hard budget: 2,000 characters, hardcoded as a constant (not configurable per project)
- Budget scope (whether header/markup counts against limit): Claude's discretion
- Trimming strategy (drop lowest-ranked vs truncate long items): Claude's discretion
- Memory Context section placed at the end of the SOUL, after all existing sections

### Claude's Discretion
- Query composition details (what fields to send to memU /retrieve)
- Number of results to request from memU
- Relevance score threshold (if any)
- Sync with timeout vs async retrieval approach
- Budget accounting (total rendered vs content only)
- Trimming strategy when exceeding budget

</decisions>

<specifics>
## Specific Ideas

- Memory bullets should look like: `- Previous task on auth module was rejected: missing error handling for expired tokens (from L2 review)`
- The source tag should be short — parenthetical at the end of each bullet
- Log format example: `Injected 4 memories (1,847 chars) into SOUL`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-pre-spawn-retrieval-soul-injection*
*Context gathered: 2026-02-24*
