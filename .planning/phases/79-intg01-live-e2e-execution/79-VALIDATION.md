---
phase: 79
slug: intg01-live-e2e-execution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 79 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright MCP (browser observation) + bash assertions (CLI) |
| **Config file** | none — all verification driven by plan task steps |
| **Quick run command** | Execute individual criterion task step |
| **Full suite command** | Execute all 4 criterion tasks sequentially in Wave 1 |
| **Estimated runtime** | ~10–20 minutes (service startup + live task execution) |

---

## Sampling Rate

- **After every task commit:** Capture screenshot + DOM snapshot as inline evidence
- **After every plan wave:** Wave 1 completion = all 4 INTG-01 criteria observed and documented
- **Before `/gsd:verify-work`:** All 4 criteria must be VERIFIED (not DEFERRED) in VERIFICATION.md
- **Max feedback latency:** Each criterion produces evidence before moving to next

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 79-01-01 | 01 | 0 | INTG-01 | infra-gate | `docker ps && make memory-health && curl http://localhost:18789/health && curl -sf http://localhost:6987 -o /dev/null` | ❌ in-task | ⬜ pending |
| 79-01-02 | 01 | 0 | INTG-01 | infra-gate | `openclaw-project list` | ❌ in-task | ⬜ pending |
| 79-01-03 | 01 | 1 | INTG-01 | live/observational | Playwright DOM wait + timestamp delta (< 5000ms) | ❌ in-task | ⬜ pending |
| 79-01-04 | 01 | 1 | INTG-01 | live/observational | Playwright click + DOM snapshot (terminal panel visible) | ❌ in-task | ⬜ pending |
| 79-01-05 | 01 | 1 | INTG-01 | live/observational | Playwright navigate + DOM snapshot (/metrics completed_count > N) | ❌ in-task | ⬜ pending |
| 79-01-06 | 01 | 1 | INTG-01 | live/observational | `mcp__playwright__browser_network_requests` SSE event order | ❌ in-task | ⬜ pending |
| 79-01-07 | 01 | 2 | INTG-01 | documentation | Edit 77-VERIFICATION.md: rows 7-10 DEFERRED→VERIFIED, status→verified, score→10/10 | ❌ in-task | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Docker images pre-built — `docker images openclaw-l3-specialist` shows image; if absent run `make docker-l3`
- [ ] Active project configured — `openclaw-project list` shows at least one project
- [ ] Gateway startup path confirmed — if `:18789` not responding, surface startup command from `openclaw/` submodule

*All infrastructure already exists — Wave 0 is verification gates only, no new file creation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| L3 task appears in task board within 5s | INTG-01 | Live system execution; Playwright observes browser DOM in real time | Navigate to :6987 in fresh session, start network monitoring, dispatch `openclaw agent --agent clawdia_prime --message "Write a hello world Python script"`, wait for task row with 5s timeout |
| Live output streams in terminal panel | INTG-01 | Requires running L3 container with active output | Click task row, verify terminal panel opens with log lines |
| Post-completion metrics visible | INTG-01 | Requires task to complete full lifecycle | Navigate to /metrics after task completion, verify completed_count > previous and pipeline timeline row present |
| SSE event stream order (task.created/started/output/completed) | INTG-01 | Must monitor SSE stream BEFORE dispatch (not retroactive) | Open fresh browser session → start network monitoring → then dispatch; inspect network events for SSE stream ordering |

---

## Validation Sign-Off

- [ ] All tasks have inline evidence capture (screenshot + DOM snapshot) or Wave 0 gate
- [ ] SSE network monitoring opened BEFORE dispatch (non-retroactive — critical)
- [ ] Wave 0 gates: Docker, memU, gateway, dashboard, project all healthy before criterion execution
- [ ] 5-second timing measured with explicit timestamps (T0 = before CLI dispatch, T1 = DOM change)
- [ ] VERIFICATION.md updates written AFTER all 4 criteria evaluated (not incrementally)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
