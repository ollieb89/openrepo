# Phase 28: L3 Auto-Memorization - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

After a successful L3 task completes, its semantic snapshot is memorized in memU via a fire-and-forget HTTP call. MEMU_API_URL is injected into L3 containers at spawn time via openclaw.json config. Memorization does not delay container exit or hold pool slots. Retrieval and SOUL injection are Phase 29; L3 in-execution queries are Phase 31.

</domain>

<decisions>
## Implementation Decisions

### What gets memorized
- Store the full semantic snapshot as-is (git diff + metadata) as the memory content
- Include the full git diff — no truncation or summarization
- No size limit per memory item; let memU handle chunking/embedding
- Use existing snapshot metadata only (task_id, agent, timestamp, files changed) — no additional fields needed

### Trigger timing & lifecycle
- Memorize on successful L3 task completion only — failures, timeouts, and rejections are not memorized
- Fire memorization after the snapshot is created but before the pool slot is released
- Fire-and-forget via `asyncio.create_task` with an exception handler that logs a warning on failure — no retry, no blocking

### MEMU env var injection
- MEMU_API_URL value sourced from `openclaw.json` config (new field)
- Always inject the env var into L3 containers regardless of memU availability — no health check at spawn time
- The actual memorization call happens in the orchestration layer (Python), not inside the L3 container
- L3 gets the env var to prepare for Phase 31 (in-execution queries), not for this phase's memorization flow

### Memory attribution
- Use the L3 specialist's agent ID (e.g. "l3_specialist") as the agent_id in MemoryClient
- Tag each memory with task_type (code/test) and file paths touched
- Use category prefix "l3_outcome" to distinguish from future memory types (Phase 30 will use "l2_review")

### Claude's Discretion
- HTTP timeout for the fire-and-forget memorization call
- Additional MEMU env vars beyond MEMU_API_URL (if needed for clean implementation)
- Memory title/summary generation approach (auto-generate from snapshot or use task description)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The MemoryClient from Phase 27 provides the interface; this phase wires it into the L3 lifecycle at the right point.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 28-l3-auto-memorization*
*Context gathered: 2026-02-24*
