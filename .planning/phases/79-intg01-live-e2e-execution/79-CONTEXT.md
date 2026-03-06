# Phase 79: INTG-01 Live E2E Execution - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Execute the 4 deferred live success criteria from `77-E2E-CHECKLIST.md` with all system components running simultaneously, then document results in an updated Phase 77 VERIFICATION.md. No new code changes — this is verification execution and documentation only.

The 4 criteria:
1. L1 dispatch → L3 task appears in task board within 5s
2. Live output stream visible when task row clicked
3. Post-completion metrics + pipeline timeline row
4. Event stream completeness (task.created/started/output/completed in order, no gap > 2s)

</domain>

<decisions>
## Implementation Decisions

### Execution approach
- Claude drives the full run using Playwright MCP (mcp__playwright tools) for dashboard observation + CLI tools for L1 directive dispatch
- No manual steps required from the user during execution

### Service startup
- Plan includes full service startup tasks: Docker, memU (`make memory-up`), gateway, dashboard (`make dashboard`)
- Each service is health-checked before proceeding to the next startup step
- Verification does not begin until all services are confirmed healthy

### Failure handling
- Fail fast with diagnosis: if any service health check fails, stop and report exactly which service is down and what to fix
- Do not attempt partial verification when infrastructure is unavailable
- Clear diagnostic output > silent failure

### Browser observation
- Use Playwright MCP (`mcp__playwright__*` tools) already available in session
- Navigate to http://localhost:6987, interact with task rows, observe terminal panel, inspect SSE via network or DOM state
- Full interaction: clicks, waits for elements, DOM inspection, screenshots for evidence

### Claude's Discretion
- Evidence format: what to capture as proof for each criterion (screenshots, log excerpts, console output)
- Whether to also verify Phase 74 human_needed items (DASH-01, DASH-03) in the same run
- Wording of VERIFICATION.md updates
- How long to wait for each criterion before marking as failed

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `77-E2E-CHECKLIST.md`: Canonical checklist at `.planning/phases/77-integration-e2e-verification/77-E2E-CHECKLIST.md` — 4 criteria with exact steps
- `74-VALIDATION.md`: Phase 74 browser smoke-test at `.planning/phases/74-dashboard-streaming-ui/74-VALIDATION.md` — DASH-01/DASH-03 items
- Playwright MCP tools: `mcp__playwright__browser_navigate`, `mcp__playwright__browser_click`, `mcp__playwright__browser_snapshot`, `mcp__playwright__browser_wait_for`, `mcp__playwright__browser_take_screenshot`, `mcp__playwright__browser_network_requests`

### Established Patterns
- VERIFICATION.md format: frontmatter (`phase`, `verified`, `status`, `score`, `human_verification`), Observable Truths table, Required Artifacts table — see `75-VERIFICATION.md` as canonical reference
- Service startup: `make memory-up` (memU Docker service, port 18791), `make dashboard` (Next.js, port 6987), gateway started separately
- Health checks: `curl http://localhost:18789/health` (gateway), `make memory-health` (memU), `curl http://localhost:6987` (dashboard)

### Integration Points
- Phase 77 VERIFICATION.md to update: `.planning/phases/77-integration-e2e-verification/77-VERIFICATION.md`
- Phase 74 VERIFICATION.md (may update DASH-01/DASH-03 items): `.planning/phases/74-dashboard-streaming-ui/74-VERIFICATION.md`
- L1 directive command: `openclaw agent --agent clawdia_prime --message "Write a hello world Python script"`
- Dashboard URL: http://localhost:6987

</code_context>

<specifics>
## Specific Ideas

- The E2E checklist in `77-E2E-CHECKLIST.md` is the authoritative source for step-by-step execution — follow it exactly
- Criterion 4 (event stream) is observed via browser devtools/network tab SSE endpoint; Playwright network request inspection can capture this
- The 5-second timeout for criterion 1 is strict — measure wall-clock time from directive dispatch to task board appearance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 79-intg01-live-e2e-execution*
*Context gathered: 2026-03-06*
