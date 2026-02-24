# Phase 39: Graceful Sentinel - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

L3 containers and the pool shut down cleanly on SIGTERM. Interrupted tasks are recorded in Jarvis state and automatically recovered on restart. Covers: SIGTERM handling, task state dehydration, recovery scan on startup, fire-and-forget memorize drain, and per-project recovery policy configuration.

</domain>

<decisions>
## Implementation Decisions

### Recovery behavior
- Default recovery policy: `mark_failed` — interrupted tasks are marked failed, operator decides next steps
- Recovery policy is configurable per-project via `l3_overrides.recovery_policy` in project.json (options: `mark_failed`, `auto_retry`, `manual`)
- When `auto_retry` is enabled, retry limit is 1 — retry once, then fall back to `mark_failed`
- Recovery scan runs at pool startup only, not periodically while running
- Recovery events appear as distinct entries in monitor CLI: `RECOVERED: task-123 -> mark_failed`

### Shutdown sequence
- Drain timeout: 30 seconds (matches Docker's default `--stop-timeout`)
- No task dehydration/checkpointing — just mark the task as `interrupted` in Jarvis state and exit cleanly
- All running containers receive SIGTERM simultaneously (parallel drain), each independently writes its interrupted state
- Entrypoint switches to exec form — Python process is PID 1 and receives SIGTERM directly (no bash intermediary)

### Operator visibility
- Shutdown logging: one summary line per container in monitor CLI — `SHUTDOWN: task-123 -> interrupted (14s drain)`
- Recovery events visible in both CLI monitor and dashboard
- Dashboard: toast notifications on load when recovery occurred — `2 tasks recovered on pool restart`
- Pool always logs a startup summary: `Pool startup: scanned 5 tasks, 2 interrupted -> mark_failed, 0 retried` — even when nothing was recovered

### Edge case handling
- Fire-and-forget memorize calls: attempt drain via `asyncio.gather` within the 30s window; if incomplete, log the loss and discard — don't block shutdown
- SIGKILL scenario (container killed before writing state): task stays `in_progress` in Jarvis state; startup recovery scan detects it (container gone, beyond skill timeout) and applies recovery policy
- Double SIGTERM: idempotent — first signal triggers shutdown, subsequent signals are ignored (boolean guard)
- Jarvis state lock conflict during shutdown: wait up to 5 seconds for lock acquisition; if still locked, log failure and exit without writing state — recovery scan handles it later

### Claude's Discretion
- Exact asyncio signal handler implementation details
- Internal structure of the recovery scan logic
- Log formatting and color choices in monitor output
- Toast notification styling in dashboard

</decisions>

<specifics>
## Specific Ideas

- Exit code 143 (SIGTERM) expected from clean container shutdown, not 137 (SIGKILL)
- Recovery scan should check for tasks in `in_progress`, `interrupted`, or `starting` states beyond the skill timeout
- Use `loop.add_signal_handler()` for asyncio SIGTERM handling (not `signal.signal()` — avoids fcntl deadlock risk per v1.4 research)
- Pass `--stop-timeout 30` on `docker run` to align Docker's grace period with the drain timeout

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 39-graceful-sentinel*
*Context gathered: 2026-02-24*
