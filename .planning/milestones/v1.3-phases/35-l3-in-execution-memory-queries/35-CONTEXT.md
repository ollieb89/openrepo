# Phase 35: L3 In-Execution Memory Queries - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

L3 containers can query memU for task-specific context during execution via HTTP calls that are independent of SOUL injection. This extends the existing spawn-time memory injection (Phase 26-32) with on-demand mid-execution lookups. Depends on Phase 33 (network access + MEMU_API_URL wiring). No new memU API endpoints — uses existing retrieve endpoint.

</domain>

<decisions>
## Implementation Decisions

### Query interface design
- Raw HTTP calls directly against MEMU_API_URL — no wrapper scripts, no helper libraries
- Query payload is text-only — L3 sends a natural language query string
- SOUL template gets a new section with a concrete example: endpoint URL, HTTP method, payload format, and expected response shape
- Runtime-agnostic: works with claude-code, codex, gemini-cli (all support HTTP)

### Failure & fallback behavior
- If memU is unreachable: fail silently, continue task execution — consistent with existing spawn.py graceful degradation pattern
- If memU returns empty results: log a debug-level note that no memories matched (for observability / future tuning)
- 5-second timeout on all memory queries — prevents slow memU from eating into task skill timeouts (code: 600s, test: 300s)
- Timeout guidance included explicitly in SOUL example

### Query scoping & filtering
- Agent context (project_id, task_type from container env vars) included in query payload automatically — helps memU rank relevance
- Result count uses server-side default — L3 doesn't specify limits
- Free-text semantic search only — no category filters, no structured query params
- Project scoping strategy: Claude's discretion

### Usage patterns & triggers
- SOUL includes suggested triggers: "Consider querying memU when you encounter an unfamiliar pattern, hit an error, or need project conventions"
- No hard limit on number of queries per task execution — let agents use it freely
- On-demand usage — agents decide when extra context would help

### Testing approach
- Integration test that proves L3 can query memU from inside a container
- Uses a mock HTTP endpoint (no live memU dependency) that mimics the retrieve response
- Validates success criteria #1: POST to retrieve endpoint returns relevant memory items

### Claude's Discretion
- Project scoping strategy (project-only vs global fallback)
- Exact SOUL template wording and placement
- Mock endpoint implementation details
- How agent context fields map to memU API parameters

</decisions>

<specifics>
## Specific Ideas

- SOUL example should be copy-pasteable — show the exact curl/HTTP call so L3 agents don't guess the API shape
- Follow existing graceful degradation pattern from spawn.py memory retrieval
- Empty-result logging enables future analysis of query hit rates and memory quality

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 35-l3-in-execution-memory-queries*
*Context gathered: 2026-02-24*
