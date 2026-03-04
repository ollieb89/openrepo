---
phase: 72-gateway-only-dispatch
plan: "01"
subsystem: router, config, cli
tags: [gateway, dispatch, bootstrap, execFileSync-removal, cli]
dependency_graph:
  requires: []
  provides: [gateway-only-dispatch, bootstrap-mode, ensure-gateway]
  affects: [skills/router/index.js, openclaw.config, openclaw-monitor, openclaw-project]
tech_stack:
  added: []
  patterns: [gateway-only-dispatch, bootstrap-mode-env-var, async-gateway-health-check]
key_files:
  created:
    - packages/orchestration/tests/test_gateway_bootstrap.py
  modified:
    - skills/router/index.js
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/src/openclaw/cli/monitor.py
    - packages/orchestration/src/openclaw/cli/project.py
decisions:
  - "Propose directives route through gateway HTTP API (POST /api/agent/__propose__/message) — no subprocess fallback"
  - "Gateway unreachable error includes 'openclaw gateway start' remediation hint"
  - "ensure_gateway() skips check entirely in bootstrap mode — no conditional health check"
  - "monitor status is bootstrap-safe by omission (no ensure_gateway() call) per plan spec"
  - "tail --events calls ensure_gateway() before run_tail_events() — bridge requires gateway"
metrics:
  duration_minutes: 2
  completed_date: "2026-03-04"
  tasks_completed: 2
  files_modified: 4
  files_created: 1
  tests_added: 10
  tests_total: 721
requirements_satisfied:
  - GATE-01
  - GATE-02
  - GATE-03
---

# Phase 72 Plan 01: Gateway-Only Dispatch Summary

**One-liner:** Gateway-only router dispatch with `OPENCLAW_BOOTSTRAP` mode and startup health check — `execFileSync` fallback fully removed, `ensure_gateway()` wired into long-running CLI commands.

## Objective

Remove the `execFileSync` CLI subprocess fallback from the router so all directive routing goes exclusively through the gateway HTTP API. Add bootstrap mode (`OPENCLAW_BOOTSTRAP=1` / `--bootstrap`) for setup commands that don't need a gateway. Add a startup health check that fails fast when the gateway is unavailable outside bootstrap mode.

## Tasks Completed

| # | Name | Commit | Files Modified |
|---|------|--------|----------------|
| 1 | Remove execFileSync fallback and propose subprocess from router | 719f7df | skills/router/index.js |
| 2 (RED) | Add failing tests for ensure_gateway and is_bootstrap_mode | 133e27c | packages/orchestration/tests/test_gateway_bootstrap.py |
| 2 (GREEN) | Add ensure_gateway() and bootstrap mode to Python CLI | 671d9d5 | config.py, monitor.py, project.py |

## What Was Built

### Router Changes (skills/router/index.js)
- Removed `const { execFileSync } = require('child_process')` import entirely
- Replaced propose subprocess block with gateway HTTP API call (`POST /api/agent/__propose__/message`)
- Replaced catch-fallback block with clear `DispatchError("Gateway unreachable at localhost:{port}. Start it with: openclaw gateway start")`
- Zero `execFileSync` references remain — `grep -r "execFileSync" skills/router/` returns nothing

### Config Additions (packages/orchestration/src/openclaw/config.py)
- `is_bootstrap_mode()`: reads `OPENCLAW_BOOTSTRAP` env var; returns `True` only when value is `"1"`
- `_ensure_gateway_async()`: async helper that checks gateway health and calls `sys.exit(1)` with FATAL message when unhealthy (non-bootstrap)
- `ensure_gateway()`: synchronous wrapper using `asyncio.run()` — designed for CLI startup use

### CLI Wiring
**monitor.py:**
- Added `--bootstrap` flag to main parser; sets `OPENCLAW_BOOTSTRAP=1` before dispatch
- `tail --events` now calls `ensure_gateway()` before `run_tail_events()` — event streaming requires bridge
- `tail` (polling mode), `status`, `task`, `pool` commands do NOT call `ensure_gateway()` — bootstrap-safe

**project.py:**
- Added `--bootstrap` flag to main parser; sets `OPENCLAW_BOOTSTRAP=1` before dispatch
- All project subcommands (init, list, switch, remove) are setup operations — no `ensure_gateway()` call

### Tests (packages/orchestration/tests/test_gateway_bootstrap.py)
10 new tests covering:
- `is_bootstrap_mode()` with OPENCLAW_BOOTSTRAP=1, =0, unset, empty string, "true"
- `ensure_gateway()` exits with code 1 on unhealthy gateway
- `ensure_gateway()` prints FATAL message with "openclaw gateway start" to stderr
- `ensure_gateway()` succeeds silently on healthy gateway
- `ensure_gateway()` skips health check entirely in bootstrap mode (gateway_healthy not called)

## Deviations from Plan

None — plan executed exactly as written.

The only clarification made: the plan's Task 2 action described wiring `ensure_gateway()` for `tail --events` specifically. The existing `main()` dispatch called `tail_state()` unconditionally regardless of `args.events` (the events dispatch was missing). This was addressed as part of the intended wiring — the `ensure_gateway()` call is gated on `getattr(args, 'events', False)` and the `run_tail_events()` call was moved into that branch, matching the plan's intent.

## Verification Results

1. `grep -r "execFileSync" skills/router/` — PASS: no results
2. `grep -r "child_process" skills/router/` — PASS: no results
3. `node -c skills/router/index.js` — PASS: syntax valid
4. `uv run pytest packages/orchestration/tests/test_gateway_bootstrap.py -v` — PASS: 10/10
5. `uv run pytest packages/orchestration/tests/ -v` — PASS: 721/721 (no regressions)
6. `OPENCLAW_BOOTSTRAP=1 uv run python -c "from openclaw.config import ensure_gateway; ensure_gateway(); print('OK')"` — prints OK

## Requirements Satisfied

- **GATE-01**: Zero execFileSync references in skills/router/ — router dispatches via gateway HTTP API only
- **GATE-02**: ensure_gateway() wired into long-running CLI commands with fatal-error-on-failure behavior
- **GATE-03**: Bootstrap mode env var + CLI flag accepted by monitor and project CLIs, skips gateway check

## Self-Check: PASSED

- FOUND: packages/orchestration/tests/test_gateway_bootstrap.py
- FOUND: skills/router/index.js
- FOUND: packages/orchestration/src/openclaw/config.py
- FOUND: .planning/phases/72-gateway-only-dispatch/72-01-SUMMARY.md
- FOUND: commit 719f7df (feat: remove execFileSync fallback)
- FOUND: commit 133e27c (test: add failing tests)
- FOUND: commit 671d9d5 (feat: add ensure_gateway and bootstrap mode)
