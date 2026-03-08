---
phase: 72
slug: gateway-only-dispatch
status: complete
nyquist_compliant: true
created: 2026-03-08
---

# Phase 72 — Gateway-Only Dispatch: Validation Attestation

> Retroactive: phase complete prior to Nyquist adoption.

---

## Phase Summary

| Field | Value |
|-------|-------|
| **Goal** | Remove CLI subprocess fallback — route all directives exclusively through gateway HTTP API with bootstrap mode for setup commands |
| **Requirements** | GATE-01, GATE-02, GATE-03 |
| **Completed** | 2026-03-04 |
| **Evidence Sources** | `.planning/phases/72-gateway-only-dispatch/72-VERIFICATION.md`, `72-01-SUMMARY.md` |

---

## Success Criteria — Evidence

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Removing gateway causes dispatch to fail with `DispatchError "Gateway unreachable"` — no `execFileSync` fallback | VERIFIED | `grep -r "execFileSync" skills/router/` returns no results; `grep -r "child_process" skills/router/` returns no results. Both propose and normal dispatch routes use `fetch()` exclusively. |
| 2 | `grep -r "execFileSync" skills/router/` returns no results | VERIFIED | Confirmed programmatically — zero occurrences of `execFileSync` or `require('child_process')` anywhere under `skills/router/` |
| 3 | `openclaw monitor status` with `OPENCLAW_BOOTSTRAP=1` succeeds without gateway | VERIFIED | `ensure_gateway()` returns immediately in bootstrap mode (`is_bootstrap_mode()` is True); `test_ensure_gateway_skips_check_in_bootstrap_mode` and `test_ensure_gateway_bootstrap_mode_does_not_exit` both pass |
| 4 | Starting without bootstrap and without gateway produces fatal startup error | VERIFIED | `config.py` `sys.exit(1)` with `FATAL: Gateway not responding at {base_url}. Start it with: openclaw gateway start`; `test_ensure_gateway_exits_when_gateway_unhealthy` and `test_ensure_gateway_prints_fatal_message_when_unhealthy` both pass |

**Score: 5/5 truths verified** (4 criteria above + 1 additional: `ensure_gateway()` is bootstrap-aware)

---

## Verification Report

| Field | Value |
|-------|-------|
| **Score** | 5/5 must-haves verified |
| **Report path** | `.planning/phases/72-gateway-only-dispatch/72-VERIFICATION.md` |
| **Verified** | 2026-03-04T12:00:00Z |
| **Status** | PASSED |

### Test Results

| Suite | Result |
|-------|--------|
| `test_gateway_bootstrap.py` | 10 passed |
| Bootstrap smoke test | `OPENCLAW_BOOTSTRAP=1 python -c "from openclaw.config import ensure_gateway; ensure_gateway(); print('OK')"` prints OK |

### Key Artifacts

| Artifact | Status |
|----------|--------|
| `skills/router/index.js` | 168 lines; zero `execFileSync` or `child_process` references; "Gateway unreachable" on lines 120 and 151 |
| `packages/orchestration/src/openclaw/config.py` | `is_bootstrap_mode()` at lines 410-416; `ensure_gateway()` at lines 439-449; `_ensure_gateway_async()` calls `sys.exit(1)` on failure |
| `packages/orchestration/src/openclaw/cli/monitor.py` | `ensure_gateway` imported (line 30) and called (line 926) for `tail --events` branch; `--bootstrap` flag added |
| `packages/orchestration/tests/test_gateway_bootstrap.py` | 126 lines; 10 tests; all pass |

### Commits

| Commit | Message |
|--------|---------|
| `719f7df` | (from 72-01-SUMMARY.md — see summary for full commit log) |
| `133e27c` | (from 72-01-SUMMARY.md) |
| `671d9d5` | (from 72-01-SUMMARY.md) |

---

_Attestation created: 2026-03-08_
_Attested by: Claude (gsd-executor, Phase 80 Plan 01)_
