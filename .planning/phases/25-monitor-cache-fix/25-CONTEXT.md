# Phase 25: Monitor Cache Fix - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Multi-project monitor tail reuses JarvisState across poll cycles so the in-memory cache provides hits instead of cold-starting every iteration. This is a performance fix to `monitor.py` — no new CLI commands, no new features.

</domain>

<decisions>
## Implementation Decisions

### JarvisState lifecycle
- Session-scoped: create once per project when tail starts, keep alive until tail exits (Ctrl+C)
- Keyed by project ID only (not workspace path)
- If a project's state file disappears mid-tail (e.g., project removed), log a warning and skip that project on subsequent polls — no crash
- Instance dict teardown is implicit when tail_state() exits

### Cache observability
- Cache stats go through structured logging only (Phase 19 system) — not visible in tail output
- Per-cycle summary: one log entry per poll cycle with hits, misses, project count
- Verification: success criteria require real multi-project tail run showing cache hits in structured logs

### Scope of reuse
- **Must-have:** tail_state() multi-project path creates JarvisState once per project outside the poll loop
- **Stretch goal:** show_status() and show_task() reuse instances where clean — skip if awkward
- show_status/show_task reuse is explicitly lower priority than tail_state()

### Claude's Discretion
- Where the JarvisState instance dict lives (local to tail loop vs module-level cache)
- Log level for cache stats (DEBUG vs INFO)
- Instantiation pattern for show_status() (batch vs lazy)
- Whether to introduce a shared helper/factory or keep inline creation
- Any implementation details not covered above

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The fix should align with Phase 21's JarvisState caching architecture.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-monitor-cache-fix*
*Context gathered: 2026-02-24*
