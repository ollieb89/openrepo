# Phase 79: INTG-01 Live E2E Execution - Research

**Researched:** 2026-03-06
**Domain:** Live system orchestration verification — Playwright browser automation + CLI dispatch + VERIFICATION.md documentation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Claude drives the full run using Playwright MCP (`mcp__playwright__*` tools) for dashboard observation + CLI tools for L1 directive dispatch — no manual steps required from the user during execution
- Plan includes full service startup tasks: Docker, memU (`make memory-up`), gateway, dashboard (`make dashboard`) — each service is health-checked before proceeding to the next startup step
- Verification does not begin until all services are confirmed healthy
- Fail fast with diagnosis: if any service health check fails, stop and report exactly which service is down and what to fix — do not attempt partial verification when infrastructure is unavailable
- Use Playwright MCP (`mcp__playwright__*` tools) already available in session — navigate to http://localhost:6987, interact with task rows, observe terminal panel, inspect SSE via network or DOM state, full interaction: clicks, waits for elements, DOM inspection, screenshots for evidence

### Claude's Discretion
- Evidence format: what to capture as proof for each criterion (screenshots, log excerpts, console output)
- Whether to also verify Phase 74 human_needed items (DASH-01, DASH-03) in the same run
- Wording of VERIFICATION.md updates
- How long to wait for each criterion before marking as failed

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTG-01 | End-to-end test: L1 dispatches via gateway → L2 decomposes → L3 spawns with populated SOUL → output streams to dashboard → events flow → metrics update | This phase closes the live execution gap for the 4 criteria deferred in Phase 77. All infrastructure to support INTG-01 was implemented in phases 68-77 and documented in 78. Phase 79 provides the execution and documentation evidence. |
</phase_requirements>

---

## Summary

Phase 79 is a pure verification-and-documentation phase — no code changes. The goal is to execute the 4 live success criteria that were deferred from Phase 77 (documented in `77-E2E-CHECKLIST.md`) against a fully running system, then update the Phase 77 VERIFICATION.md with live results.

The four criteria are: (1) L3 task appears in task board within 5s of L1 directive, (2) live output stream visible in terminal panel when task row is clicked, (3) post-completion metrics and pipeline timeline visible, (4) SSE event stream shows task.created/started/output/completed in order with no gap exceeding 2s. Optionally, the same live run can close the Phase 74 DASH-01 and DASH-03 human_needed items simultaneously since the same running dashboard satisfies those conditions.

The execution approach is fully automated: Playwright MCP tools drive browser observation, and the `openclaw agent` CLI drives L1 directive dispatch. No user interaction is required during execution. The plan must structure service startup as sequential gated steps, followed by criterion execution in the exact order of the checklist, followed by VERIFICATION.md documentation updates.

**Primary recommendation:** Structure the plan as three sequential waves — (Wave 0) service startup and health checks, (Wave 1) live criterion execution with evidence capture, (Wave 2) VERIFICATION.md documentation updates. Treat the service startup tasks as prerequisite gates, not optional steps.

---

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Playwright MCP (`mcp__playwright__*`) | In-session | Browser navigation, DOM inspection, screenshots, network monitoring | Locked by user decision; already available in session |
| `openclaw agent` CLI | Installed | L1 directive dispatch | Canonical L1 dispatch path per architecture |
| `make memory-up` | Repo | Start memU Docker service | Standard repo command for memU |
| `make dashboard` | Repo | Start Next.js dashboard on :6987 | Standard repo command for dashboard |
| `curl` | System | Health check endpoints | Standard HTTP probe |

### Health Check Commands
| Service | Command | Expected Response |
|---------|---------|------------------|
| Gateway | `curl http://localhost:18789/health` | HTTP 200 |
| Dashboard | `curl http://localhost:6987` | HTTP 200 |
| memU | `make memory-health` | "memU service: healthy" |
| Docker | `docker ps` | Zero-exit (any output) |

### L1 Directive Command (exact)
```bash
openclaw agent --agent clawdia_prime --message "Write a hello world Python script"
```

This is the exact command from `77-E2E-CHECKLIST.md`. Use verbatim.

---

## Architecture Patterns

### Execution Order — Non-Negotiable

The 4 checklist criteria have a strict execution dependency order:

```
Criterion 1: dispatch → task appears (5s window)
    ↓
Criterion 2: click task row → terminal panel opens (requires task from criterion 1)
    ↓
Criterion 3: wait for completion → navigate metrics page (requires task to complete)
    ↓
Criterion 4: SSE event stream inspection (must observe DURING criteria 1-3 run, or replay from network tab)
```

Criterion 4 requires monitoring the SSE stream concurrently while executing criteria 1-3. The Playwright network request tool (`mcp__playwright__browser_network_requests`) must be observed before/during dispatch, not after the task completes.

### Service Startup Pattern — Sequential Gated

```
[Task 1] Verify Docker running
    → on fail: STOP + report "docker daemon not running"
[Task 2] Start memU (make memory-up) + health check
    → on fail: STOP + report memU failure
[Task 3] Start gateway + health check curl :18789/health
    → on fail: STOP + report gateway failure
[Task 4] Start dashboard (make dashboard) + curl :6987
    → on fail: STOP + report dashboard failure
[Task 5] Verify project configured (openclaw-project list)
    → on fail: STOP + report project configuration missing
```

**Each step is its own plan task.** This enables fail-fast diagnosis at the exact failure point.

### Evidence Capture Pattern

For each criterion, capture three types of evidence:
1. **Screenshot** via `mcp__playwright__browser_take_screenshot` — visual proof
2. **DOM snapshot** via `mcp__playwright__browser_snapshot` — structural proof
3. **Timing measurement** — wall-clock time from action to observable state change

The 5-second constraint on Criterion 1 requires recording:
- T0: timestamp immediately before `openclaw agent` dispatch command
- T1: timestamp when task row appears in DOM
- Delta: T1 - T0 must be < 5s

### VERIFICATION.md Update Pattern

The Phase 77 VERIFICATION.md at `.planning/phases/77-integration-e2e-verification/77-VERIFICATION.md` must be updated following the established format from `75-VERIFICATION.md` (canonical reference).

Changes required:
1. Frontmatter: change `status: human_needed` to `status: verified` (if all 4 pass), update `score` to `10/10`
2. Observable Truths table rows 7-10: change `DEFERRED (Phase 79)` to `VERIFIED` with evidence text
3. Add a new `### Phase 79 Live Execution Results` section with execution date, evidence summary, and sign-off
4. Requirements Coverage row for INTG-01: update from `PARTIALLY SATISFIED (automated)` to `FULLY SATISFIED`

If Phase 74 DASH-01/DASH-03 items are also verified in the same run, update `.planning/phases/74-dashboard-streaming-ui/74-VERIFICATION.md` in the same wave — truths 2 and 3 from `DEFERRED (Phase 79)` to `VERIFIED`.

### Playwright Tool Usage Map

| Criterion Step | Playwright Tool | What to Look For |
|---------------|----------------|-----------------|
| Navigate to dashboard | `mcp__playwright__browser_navigate` | URL http://localhost:6987 loads |
| Observe task board before dispatch | `mcp__playwright__browser_snapshot` | Baseline: task count N |
| Wait for new task row | `mcp__playwright__browser_wait_for` | New row with task ID appears |
| Capture task appearance | `mcp__playwright__browser_take_screenshot` | Task row visible |
| Click task row | `mcp__playwright__browser_click` | Terminal panel opens |
| Verify live output | `mcp__playwright__browser_snapshot` | Terminal panel DOM has lines |
| Navigate to metrics | `mcp__playwright__browser_navigate` | /metrics page |
| Verify completed count | `mcp__playwright__browser_snapshot` | Completed count > previous |
| Verify pipeline timeline | `mcp__playwright__browser_snapshot` | Pipeline row with stages |
| Inspect SSE events | `mcp__playwright__browser_network_requests` | SSE stream with event types |

### Anti-Patterns to Avoid
- **Starting verification before all services are healthy:** Even one unhealthy service causes ambiguous results. The health gate is mandatory.
- **Measuring the 5-second window subjectively:** Record explicit timestamps — T0 before CLI command, T1 at DOM change.
- **Using `mcp__playwright__browser_wait_for` with no timeout:** Always specify a timeout (5000ms for criterion 1) to distinguish timeout failures from infinite waits.
- **Updating VERIFICATION.md before all 4 criteria pass:** Document results after all criteria are evaluated, not incrementally during the run.
- **Conflating Playwright snapshot with screenshot:** `browser_snapshot` gives structured DOM; `browser_take_screenshot` gives visual PNG. Both are needed — DOM for evidence, screenshot for human review.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE event stream monitoring | Custom EventSource client | `mcp__playwright__browser_network_requests` to inspect Network tab EventStream | Already available, captures browser-observed traffic |
| Dashboard health check | Custom HTTP client | `curl http://localhost:6987` | Simple and already in the established pattern |
| Timing measurement | Complex timing infrastructure | Record bash timestamps via `date +%s%N` before/after CLI command | Sufficient precision for 5-second window |
| VERIFICATION.md format | New format invention | Match existing `75-VERIFICATION.md` structure verbatim | Planner and verifier expect stable format |

---

## Common Pitfalls

### Pitfall 1: Gateway Not Running at Plan Execution Time
**What goes wrong:** The plan tasks assume the gateway process is started by a `make` command, but the Makefile has no `make gateway` target — gateway startup is not a make target.
**Why it happens:** The gateway is started as part of the OpenClaw CLI/runtime (`openclaw` command), not as a separate Docker service or make target.
**How to avoid:** The gateway startup step should check if the gateway responds at :18789, and if not, provide instructions for how to start it (likely `cd openclaw && node dist/index.js` or `openclaw` runtime startup). The plan task should try health check first, and if it fails, surface the startup command needed. This is a "fail fast with diagnosis" scenario per the locked decision.
**Warning signs:** `curl http://localhost:18789/health` returns connection refused even after memU and Docker are healthy.

### Pitfall 2: No Active Project Configured
**What goes wrong:** `openclaw agent --agent clawdia_prime --message "..."` fails because no active project is set, or the project's workspace path doesn't exist.
**Why it happens:** L1 dispatch requires an active project with a configured workspace. This is a prerequisite that can be absent on a clean machine.
**How to avoid:** Before criterion execution, run `openclaw-project list` and verify at least one project appears. Check that the active project has a valid workspace path. If not, the plan task should surface the setup command.
**Warning signs:** `openclaw agent` returns an error about missing project or workspace.

### Pitfall 3: 5-Second Timing Window Too Tight for Cold System
**What goes wrong:** On a cold system (fresh Docker, all services just started), the first L1 → L3 dispatch may take longer than 5 seconds because Docker image pulls, network setup, or L2 initialization add latency.
**Why it happens:** The 5-second window was defined for a warm system. Cold starts have additional overhead.
**How to avoid:** The plan should note that Docker images must be pre-built (`make docker-l3`) before criterion execution begins. If criterion 1 times out (>5s), the diagnostic should include whether this is a cold-start issue vs. a pipeline failure. Record actual elapsed time regardless.
**Warning signs:** Task appears in task board but at 7-8 seconds elapsed; Docker image pull visible in output.

### Pitfall 4: SSE Network Inspection Requires Open DevTools Before Dispatch
**What goes wrong:** `mcp__playwright__browser_network_requests` only captures requests made after the tool starts monitoring. If the SSE connection was established before Phase 79 execution begins, the event stream may not be captured.
**Why it happens:** Playwright network monitoring is not retroactive.
**How to avoid:** The plan must explicitly open the dashboard in a fresh browser session (new navigation) before dispatch, so the SSE connection is established and monitored from the start. The network request inspection for criterion 4 must happen before the dispatch command is issued.
**Warning signs:** `browser_network_requests` shows no SSE connection or empty event stream despite visible task updates in the DOM.

### Pitfall 5: Dashboard Running in Wrong Mode
**What goes wrong:** `make dashboard` starts `pnpm run dev` (Next.js dev server). If a production build is cached or a different port is in use, the dashboard at :6987 may serve stale code without the streaming UI components from Phase 74.
**Why it happens:** Port conflicts or stale processes from previous sessions.
**How to avoid:** Before starting, run `make stop-dashboard` to ensure the port is clean. Then `make dashboard`. Verify the page loads current code by checking the page title or version indicator.
**Warning signs:** Dashboard at :6987 responds but task board doesn't show the terminal panel on click (Phase 74 UI absent).

---

## Code Examples

### Exact Dispatch Command (from 77-E2E-CHECKLIST.md)
```bash
# Source: .planning/phases/77-integration-e2e-verification/77-E2E-CHECKLIST.md
openclaw agent --agent clawdia_prime --message "Write a hello world Python script"
```

### Health Check Sequence (established pattern from CONTEXT.md)
```bash
# Gateway health check
curl http://localhost:18789/health

# memU health check
make memory-health
# Expected output: "memU service: healthy"

# Dashboard health check
curl -sf http://localhost:6987 -o /dev/null && echo "dashboard: healthy"

# Docker check
docker ps
```

### Timing Measurement Pattern
```bash
# Record T0 before dispatch
T0=$(date +%s%3N)  # milliseconds

openclaw agent --agent clawdia_prime --message "Write a hello world Python script"

# T1 is recorded when Playwright confirms task row appears in DOM
# Delta = T1 - T0 must be < 5000ms
```

### 77-VERIFICATION.md Observable Truths Table — Target State After Phase 79
```markdown
# Current (deferred) rows 7-10 become:
| 7 | Full task lifecycle visible in dashboard Mission Control in real time | Live | VERIFIED | Phase 79 live execution 2026-03-06: task appeared in task board within Xs of directive; screenshot evidence captured. |
| 8 | L3 container output streams to terminal panel within 2 seconds of log line | Live | VERIFIED | Phase 79: terminal panel opened on task row click; live log lines visible; auto-scroll active. |
| 9 | Metrics page reflects completed task count after full lifecycle | Live | VERIFIED | Phase 79: metrics page /metrics shows completed_count = N+1 after task completion; pipeline timeline row with L1→L2→L3 stages visible. |
| 10 | Gateway routes task from L1 dispatch through L3 completion end-to-end | Live | VERIFIED | Phase 79: full L1→L2→L3 pipeline executed without error; SSE stream showed task.created/started/output/completed in order. |
```

### Frontmatter Change in 77-VERIFICATION.md
```yaml
# Before (current state):
status: human_needed
score: 6/10 automated must-haves verified

# After Phase 79 (if all 4 pass):
status: verified
score: 10/10
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual human verification steps | Claude drives Playwright MCP for browser observation | Phase 79 decision | Fully automated live verification without user interaction |
| 4 live criteria marked "DEFERRED" | Same 4 criteria executed and documented as VERIFIED | Phase 79 | INTG-01 changes from PARTIALLY SATISFIED to FULLY SATISFIED |

**Deprecated/outdated:**
- `human_needed` status in 77-VERIFICATION.md: replaced by `verified` once Phase 79 completes
- `human_verification` YAML block in 77-VERIFICATION.md: items become historical record, not active checklist items

---

## Open Questions

1. **Gateway startup command**
   - What we know: Gateway health check is at `curl http://localhost:18789/health`. No `make gateway` target exists in the Makefile.
   - What's unclear: The exact command to start the gateway process if it is not already running. The `openclaw` Node.js runtime in `openclaw/` (submodule) appears to be the gateway, started via `openclaw` CLI or `node dist/index.js`.
   - Recommendation: The plan's service startup task should include: (1) check if gateway is running via health check, (2) if not, surface the startup command from the `openclaw` submodule README or `package.json` scripts, (3) fail fast with clear instructions if gateway cannot be started.

2. **Whether to verify Phase 74 DASH-01/DASH-03 in the same run**
   - What we know: Both items are marked "DEFERRED (Phase 79)" in `74-VERIFICATION.md`. The same live dashboard session satisfies both. User has marked this as Claude's discretion.
   - What's unclear: Risk of scope creep vs. efficiency gain.
   - Recommendation: YES — do it in the same run. The marginal cost is low (the dashboard is already open, the task is already running), and it closes two additional deferred items. Add optional tasks to the plan for DASH-01/DASH-03 verification, clearly labeled as secondary scope.

3. **Project configuration state at plan execution time**
   - What we know: `openclaw agent --agent clawdia_prime --message "..."` requires an active project with a valid workspace.
   - What's unclear: Whether a project is already configured in the current environment.
   - Recommendation: The Wave 0 service startup tasks should include a project verification step: `openclaw-project list` and check for at least one project. If absent, the task should surface the `openclaw-project init` command and stop.

---

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` (key absent) — treat as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright MCP (browser) + bash assertions (CLI) |
| Config file | none — all verification driven by plan task steps |
| Quick run command | n/a — each criterion is a discrete plan task step |
| Full suite command | Execute all 4 criterion tasks sequentially in Wave 1 |

**Note:** This phase has no automated unit tests. All validation is observational — Playwright browser observation and CLI output inspection. The "test" is the plan task execution itself.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTG-01 | L1 dispatch → task appears in task board within 5s | live/observational | Playwright DOM wait + timestamp delta | ❌ executed as plan step |
| INTG-01 | L3 live output stream visible in terminal panel | live/observational | Playwright click + DOM snapshot | ❌ executed as plan step |
| INTG-01 | Post-completion metrics + pipeline timeline visible | live/observational | Playwright navigate + DOM snapshot | ❌ executed as plan step |
| INTG-01 | SSE event stream: task.created/started/output/completed in order | live/observational | Playwright network_requests inspection | ❌ executed as plan step |
| DASH-01 | Terminal panel streams SSE output (secondary scope) | live/observational | Playwright DOM observation | ❌ executed as plan step |
| DASH-03 | Auto-scroll pauses on scroll-up, resumes on scroll-to-bottom (secondary scope) | live/observational | Playwright scroll + DOM snapshot | ❌ executed as plan step |

### Sampling Rate

- **Per criterion:** Screenshot + DOM snapshot captured as inline evidence
- **Per wave:** All criteria in Wave 1 constitute the full verification suite
- **Phase gate:** All 4 INTG-01 criteria pass before VERIFICATION.md updates are written

### Wave 0 Gaps

All infrastructure for this phase already exists. No new test files to create.

- [ ] **Verify Docker images pre-built** — run `docker images openclaw-l3-specialist` and `docker images openclaw-base` before criterion execution; if absent, run `make docker-l3` to avoid cold-start timing issues in criterion 1
- [ ] **Verify active project** — run `openclaw-project list`; if empty, surface `openclaw-project init` instructions and stop
- [ ] **Verify gateway startup path** — confirm how to start gateway if `:18789` is not responding; check `openclaw/package.json` scripts or README

None of these are test file creation gaps — they are pre-execution verification steps for the plan.

---

## Sources

### Primary (HIGH confidence)
- `.planning/phases/77-integration-e2e-verification/77-E2E-CHECKLIST.md` — canonical checklist with exact 4 criteria and steps
- `.planning/phases/77-integration-e2e-verification/77-VERIFICATION.md` — current state of 77 verification, showing exactly which rows need updating
- `.planning/phases/74-dashboard-streaming-ui/74-VERIFICATION.md` — secondary scope items deferred to Phase 79
- `.planning/phases/79-intg01-live-e2e-execution/79-CONTEXT.md` — locked decisions, Playwright tools, health check commands
- `Makefile` — exact service startup and health check commands

### Secondary (MEDIUM confidence)
- `.planning/phases/75-unified-observability/75-VERIFICATION.md` — canonical reference format for VERIFICATION.md structure
- `CLAUDE.md` architecture section — service ports, health check patterns, gateway/memU architecture

### Tertiary (LOW confidence)
- Gateway startup command: not confirmed from Makefile; needs validation against `openclaw/` submodule

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tools explicitly locked in CONTEXT.md, commands confirmed in Makefile and checklist
- Architecture: HIGH — execution sequence is dictated by checklist; patterns confirmed from existing VERIFICATION.md files
- Pitfalls: MEDIUM-HIGH — gateway startup pitfall is LOW confidence (exact command unconfirmed); timing and SSE pitfalls are HIGH confidence from established patterns

**Research date:** 2026-03-06
**Valid until:** 2026-03-13 (stable — no moving parts, all tools are in-repo or in-session)
