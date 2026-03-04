# Phase 72: Gateway-Only Dispatch - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove the execFileSync CLI subprocess fallback from the router — all directive routing (including propose) goes exclusively through the gateway HTTP API. Add a bootstrap mode so setup/diagnostic CLI commands work without a running gateway. Add a startup health check that fails fast when the gateway is unavailable outside bootstrap mode.

</domain>

<decisions>
## Implementation Decisions

### Fallback removal strategy
- Immediate hard error when gateway is unreachable — no retry, no fallback
- Error message includes problem + remediation: "Gateway unreachable at localhost:18789. Start it with: openclaw gateway start"
- Remove the catch-fallback block from dispatchDirective() (lines 140-160 in index.js) — minimal diff, gateway failure becomes a clear thrown error
- Remove `require('child_process')` import entirely (propose also moves to gateway API, so no execFileSync usage remains)

### Bootstrap mode scope
- Activated via both env var (OPENCLAW_BOOTSTRAP=1) and --bootstrap CLI flag
- Bootstrap commands (no gateway needed): project init, project list, project switch, monitor status — read-only/setup operations only
- Subtle info-level log line when in bootstrap mode: "Running in bootstrap mode (no gateway)"
- If dispatch attempted in bootstrap mode: clear bootstrap-aware error "Cannot dispatch: running in bootstrap mode. Remove OPENCLAW_BOOTSTRAP=1 and ensure gateway is running."

### Startup health check
- Single check at orchestration startup for long-running commands (monitor tail, agent run, gateway-dependent operations) — not periodic
- Fatal startup error: stderr message + exit code 1. "FATAL: Gateway not responding at localhost:18789. Start it with: openclaw gateway start"
- Reuse existing `gateway_healthy()` function from config.py (httpx + 3s timeout) — no new check needed
- Wire through shared `ensure_gateway()` function called from long-running CLI entry points — single check point, easy to maintain
- Skip health check entirely when OPENCLAW_BOOTSTRAP=1 or --bootstrap is set

### Propose command path
- Move propose to gateway API — consistent with all-gateway-dispatch vision and satisfies GATE-01 success criterion (`grep -r "execFileSync" skills/router/` returns no results)
- Remove execFileSync('openclaw-propose', ...) call at line 109 in router/index.js

### Claude's Discretion
- Whether to create a new `/api/propose` endpoint or reuse `/api/agent/:id/message` for propose routing
- Propose response format — keep same shape or normalize to gateway envelope
- Exact implementation of --bootstrap flag parsing across CLI commands
- How ensure_gateway() integrates with the existing CLI entry point structure

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Success criteria are prescriptive:
1. Removing the gateway while the router is running causes dispatch to fail with a clear error — not silently fall back to execFileSync
2. `grep -r "execFileSync" skills/router/` returns no results
3. Running `openclaw monitor status` with `OPENCLAW_BOOTSTRAP=1` succeeds even when the gateway process is not running
4. Starting the orchestration layer without bootstrap mode and without a gateway running produces a fatal startup error with a human-readable message

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gateway_client.py`: Full async HTTP client with `dispatch()` and `dispatch_stream()` methods — Python-side gateway dispatch already exists
- `config.py:gateway_healthy()`: Async health check with httpx + 3s timeout — ready to wire into startup
- `config.py:get_gateway_config()`: Extracts gateway config from openclaw.json — port, token, etc.
- `config_validator.py`: Schema validation already requires `gateway.port` — config structure is solid

### Established Patterns
- `event_bus.emit()` is the single canonical publish path (Phase 70 decision) — dispatch should follow similar "single path" philosophy
- Bridge failure = warning, not crash (Phase 70) — but gateway failure in non-bootstrap mode IS fatal (different pattern, intentional)
- OPENCLAW_ROOT and env var conventions for portability (Phase 68, DEBT-03)
- State engine wraps event publishing in try/except — events never fail core operations

### Integration Points
- `skills/router/index.js`: Main file to modify — remove execFileSync fallback, remove propose subprocess call, remove child_process import
- `packages/orchestration/src/openclaw/config.py`: Wire ensure_gateway() using existing gateway_healthy()
- CLI entry points (cli/monitor.py, cli/project.py): Add ensure_gateway() calls for long-running commands, bootstrap bypass for setup commands
- Gateway server: May need new propose endpoint depending on approach chosen

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 72-gateway-only-dispatch*
*Context gathered: 2026-03-04*
