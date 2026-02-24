# Phase 19: Structured Logging - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

All orchestration components emit structured JSON logs with configurable levels, giving operators a consistent, machine-readable audit trail. Replaces ad-hoc print statements in operational code paths. Does NOT change CLI human-facing output (monitor tables, init feedback). Covers both host-side orchestration and L3 container entrypoint.

</domain>

<decisions>
## Implementation Decisions

### Log output destination
- Structured JSON logs go to stderr only (stdout reserved for CLI human output)
- Design handler setup so adding a file handler later is a config change, not a code change
- L3 containers also emit structured JSON via the same format — unified log format across host and containers

### Configuration UX
- Two config sources: env var (`OPENCLAW_LOG_LEVEL`) and `openclaw.json` top-level `"logging"` key
- Config file sets default, env var overrides
- One global log level (no per-component granularity)
- Default level: WARNING when nothing is configured

### Print migration boundary
- **Keep as stdout prints (no migration):** Monitor CLI output (status tables, tail output, task details), init.py interactive feedback (checkmarks, info lines)
- **Migrate to structured logs:** Error prints currently on stderr (e.g., "Error reading state"), spawn.py/pool.py container lifecycle events, state_engine operational events, snapshot operational events
- Rule of thumb: user-facing CLI output stays as prints; internal operational events and errors become structured logs

### Log field schema
- Format: JSONL (one JSON object per line)
- Timestamps: ISO 8601 / RFC 3339 (e.g., `2026-02-24T14:30:00.123Z`)
- Base fields (always present): `timestamp`, `level`, `component`, `message`
- Context fields (when available): `task_id`, `project_id`
- Components can add arbitrary extra fields via `extra` dict (e.g., spawn adds `container_name`, state_engine adds `lock_wait_ms`)

### Claude's Discretion
- How structured logs interleave with human output during monitor tail (visibility/suppression UX)
- Logging module internal architecture (Python logging vs custom)
- L3 entrypoint implementation details for structured output
- Exact openclaw.json schema for the logging config section

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Should align with Python logging best practices and be familiar to operators who've used structured logging in other systems.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-structured-logging*
*Context gathered: 2026-02-24*
