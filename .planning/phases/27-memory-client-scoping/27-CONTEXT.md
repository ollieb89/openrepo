# Phase 27: Memory Client + Scoping - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

A Python wrapper class (`MemoryClient`) in the orchestration layer that makes per-project and per-agent scoping structurally mandatory for all memory operations. The client wraps the memU REST API (Phase 26) and is consumed by spawn.py (Phase 28+) and review flows (Phase 30). This phase does NOT implement the callers — only the client and its tests.

</domain>

<decisions>
## Implementation Decisions

### Client Interface Design
- Async client using `httpx.AsyncClient` — matches spawn.py's existing asyncio patterns
- Standalone module at `orchestration/memory_client.py` — not inside state_engine.py
- Constructor: `MemoryClient(base_url, project_id, agent_type)` — both scoping params required at construction time
- Methods return typed dataclasses (`MemorizeResult`, `RetrieveResult`) — not raw dicts
- Async context manager support: `async with MemoryClient(...) as client:` for clean httpx cleanup

### Error & Degradation Behavior
- Sentinel values on failure — `health()` returns False, `memorize()` returns None, `retrieve()` returns `[]`
- No exceptions propagated to callers — memory is always non-blocking
- Split timeouts: 3s for retrieve, 10s for memorize (embedding generation is slow)
- No retries — single attempt, fail fast, return sentinel
- Log warnings via `get_logger()` structured logging when memU is unreachable — operators see degradation

### Agent Type Scoping Model
- Strict `AgentType(str, Enum)` with values: `l2_pm`, `l3_code`, `l3_test`
- `agent_type` set once in constructor — all calls auto-tag with it
- `memorize()` auto-includes `project_id` + `agent_type` in payload — caller can't forget
- `retrieve()` returns memories from ALL agent types within the project — cross-pollination within project boundary
- Scoping is enforced at the client level: `MemoryClient(base_url, project_id)` — no project_id means no client

### Integration Surface
- Per-call instance lifecycle — spawn.py creates a new MemoryClient per spawn/review cycle, short-lived
- memU service URL from `MEMU_SERVICE_URL` environment variable with fallback to `http://memu-server:18791`
- Standalone test file: `tests/test_memory_client.py` with isolation test, health test, and scoping tests

### Claude's Discretion
- Exact dataclass field names and shapes for MemorizeResult / RetrieveResult
- Whether to use `@dataclass(frozen=True)` or regular dataclasses
- httpx connection pool settings
- Test fixtures and mocking approach (httpx mock vs live service)

</decisions>

<specifics>
## Specific Ideas

- Constructor-enforced scoping pattern: if you can't construct a MemoryClient without project_id, you can't accidentally call memorize/retrieve without it
- The two-project isolation test is a key success criterion — write for project A, retrieve for project B, expect zero results
- Follow v1.2 patterns: `get_logger("memory_client")` for structured JSON logging

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-memory-client-scoping*
*Context gathered: 2026-02-24*
