---
phase: 39-graceful-sentinel
verified: 2026-02-24T17:05:00Z
status: passed
score: 4/4 success criteria verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "Pool startup scans workspace-state.json for tasks stuck in in_progress/interrupted/starting beyond the skill timeout and applies the configured recovery policy without manual intervention — run_recovery_scan() is now called in spawn_task() before spawn_and_monitor()"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "docker stop an active L3 container and inspect workspace-state.json"
    expected: "Task status transitions to 'interrupted' before exit; container exits with code 143 not 137"
    why_human: "Requires a live Docker daemon with an active L3 container running a real CLI runtime"
---

# Phase 39: Graceful Sentinel Verification Report

**Phase Goal:** L3 containers and pool shut down cleanly on SIGTERM — interrupted tasks are recorded in Jarvis state and automatically recovered on restart
**Verified:** 2026-02-24T17:05:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plan 39-04)

## Re-verification Summary

Previous verification (2026-02-24T16:47:43Z) found 1 blocker: `run_recovery_scan()` was fully implemented on `L3ContainerPool` but never called from any startup path. Plan 39-04 fixed this by wiring the call into `spawn_task()` at line 1101, also fixing the except path to populate `pool_cfg` (previously only set `max_concurrent`) and assigning `pool._pool_config = pool_cfg` before the call.

Gap is confirmed closed. All 4 success criteria now verified. 95/95 tests pass with no regressions.

---

## Goal Achievement

### Observable Truths (from Phase Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `docker stop` on L3 container produces exit code 143, task state transitions to `interrupted` before exit | VERIFIED | entrypoint.sh: SIGTERM trap writes `interrupted` via `update_state`, exits 143; spawn.py: `stop_timeout=30`; 7 static analysis tests pass |
| 2 | Pool startup scans workspace-state.json for orphaned tasks beyond skill timeout and applies recovery policy without manual intervention | VERIFIED | pool.py line 1101: `await pool.run_recovery_scan()` called in `spawn_task()` after pool creation, before `spawn_and_monitor()`; 11 recovery scan tests pass |
| 3 | Recovery policy settable per project via `l3_overrides.recovery_policy` in project.json, takes effect on next pool startup | VERIFIED | project_config.py: `_POOL_CONFIG_DEFAULTS` has `"recovery_policy": "mark_failed"`, `_VALID_RECOVERY_POLICIES` validates all three values; validation mirrors `overflow_policy` pattern |
| 4 | Fire-and-forget memorize tasks in flight at shutdown are drained via asyncio.gather before event loop stops — no pending task silently discarded | VERIFIED | pool.py: `_pending_memorize_tasks` list tracks tasks, `drain_pending_memorize_tasks()` uses `asyncio.wait_for(asyncio.gather(...))`, `register_shutdown_handler()` uses `loop.add_signal_handler`; 6 drain tests pass |

**Score:** 4/4 success criteria verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docker/l3-specialist/entrypoint.sh` | SIGTERM trap with idempotency guard, exit 143 | VERIFIED | `_shutdown_requested=0` guard, `trap '_trap_sigterm' TERM`, `update_state "interrupted"`, `exit 143` |
| `docker/l3-specialist/Dockerfile` | exec form ENTRYPOINT | VERIFIED | `ENTRYPOINT ["bash", "/entrypoint.sh"]` — JSON array form confirmed |
| `skills/spawn_specialist/spawn.py` | `stop_timeout=30` in container config | VERIFIED | `"stop_timeout": 30` with REL-05 comment |
| `skills/spawn_specialist/pool.py` | `_pending_memorize_tasks`, drain method, shutdown handler, `run_recovery_scan()` wired | VERIFIED | All methods implemented and called; `await pool.run_recovery_scan()` at line 1101 in `spawn_task()` |
| `orchestration/project_config.py` | `recovery_policy` validation in `get_pool_config()` | VERIFIED | `_POOL_CONFIG_DEFAULTS`, `_VALID_RECOVERY_POLICIES`, validation block present |
| `tests/test_entrypoint_shutdown.py` | 7 static analysis tests | VERIFIED | All 7 pass |
| `tests/test_pool_shutdown.py` | 6 drain/signal tests | VERIFIED | All 6 pass |
| `tests/test_recovery_scan.py` | 11 recovery policy + wiring tests | VERIFIED | All 11 pass (10 existing + 1 new `test_spawn_task_calls_recovery_scan`) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| entrypoint.sh trap handler | orchestration/state_engine.py | `update_state "interrupted"` python3 call | WIRED | Trap calls `update_state()` which invokes `JarvisState.update_task()` via inline Python |
| spawn.py container_config | Docker daemon | `"stop_timeout": 30` | WIRED | Dict key passed to Docker SDK on container creation |
| pool.py `_attempt_task()` | `_pending_memorize_tasks` list | `asyncio.create_task()` result appended | WIRED | `mem_task = asyncio.create_task(...)` then `self._pending_memorize_tasks.append(mem_task)` |
| pool.py SIGTERM handler | `asyncio.gather` | `drain_pending_memorize_tasks()` in `_drain_and_stop()` | WIRED | `register_shutdown_handler()` → `_on_sigterm()` → `loop.create_task(_drain_and_stop())` → `drain_pending_memorize_tasks()` |
| pool.py `spawn_task()` | `L3ContainerPool.run_recovery_scan()` | `await pool.run_recovery_scan()` at line 1101 | WIRED | Called after `pool._pool_config = pool_cfg` (line 1100), before `spawn_and_monitor()` (line 1102) — gap confirmed closed |
| pool.py `run_recovery_scan()` | project_config.py `get_pool_config()` | `self._pool_config.get("recovery_policy")` | WIRED | `_pool_config` now guaranteed populated via both try and except paths in `spawn_task()` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REL-04 | 39-01 | L3 entrypoint uses exec form so Python process is PID 1 and receives SIGTERM directly from Docker | SATISFIED | Dockerfile exec form confirmed; `test_dockerfile_exec_form` passes |
| REL-05 | 39-01 | L3 container handles SIGTERM via bash trap, writes `interrupted` status to Jarvis state before exit | SATISFIED | entrypoint.sh trap writes `interrupted` and exits 143; `test_entrypoint_has_sigterm_trap` passes |
| REL-06 | 39-03 + 39-04 | Pool scans for orphaned tasks (in_progress/interrupted/starting beyond skill timeout) on startup and applies configurable recovery policy | SATISFIED | `run_recovery_scan()` called at pool.py:1101 in `spawn_task()` before `spawn_and_monitor()`; `test_spawn_task_calls_recovery_scan` confirms call order |
| REL-07 | 39-03 | Recovery policy is configurable per-project via `l3_overrides.recovery_policy` in project.json | SATISFIED | project_config.py validates and returns `recovery_policy`; default `mark_failed`; `test_project_config_recovery_policy_validation` passes |
| REL-08 | 39-02 | Pending fire-and-forget asyncio memorization tasks are drained (gathered) on pool shutdown instead of silently lost | SATISFIED | `drain_pending_memorize_tasks()` + `register_shutdown_handler()` fully implemented and tested; 6 drain tests pass |

**Orphaned requirements check:** All 5 requirement IDs (REL-04 through REL-08) are claimed by plans in this phase and satisfied. None are orphaned.

---

### Anti-Patterns Found

None. The previous blocker (`run_recovery_scan()` defined but never called) is resolved. The three `pass` statements in pool.py remain legitimate: empty exception class, silencing `QueueEmpty` on drain, and silencing `CancelledError` on log task cancellation.

---

### Human Verification Required

#### 1. L3 Container Graceful Shutdown End-to-End

**Test:** Build the L3 container image, spawn a container with a long-running task, run `docker stop <container_name>`, observe container exit code and workspace-state.json.
**Expected:** Container exits with code 143 (not 137); workspace-state.json shows the task status as `interrupted` with a timestamp from before container exit.
**Why human:** Requires a live Docker daemon, a real L3 container spawned via `spawn.py`, and a task running for more than 10 seconds to trigger the stop-timeout path.

---

## Gap Closure Evidence

### Gap Closed: run_recovery_scan() wired into spawn_task()

**Previous state:** `run_recovery_scan()` implemented at pool.py:683, zero call sites in any startup path.

**Fixed state** (pool.py lines 1091-1108):

```python
# Read pool config from project.json for config-driven max_concurrent
try:
    pool_cfg = get_pool_config(project_id)
    max_concurrent = pool_cfg["max_concurrent"]
except Exception:
    pool_cfg = _POOL_DEFAULTS.copy()          # fixed: except path now sets pool_cfg
    max_concurrent = _POOL_DEFAULTS["max_concurrent"]

pool = L3ContainerPool(max_concurrent=max_concurrent, project_id=project_id)
pool._pool_config = pool_cfg                  # added: config available to run_recovery_scan()
await pool.run_recovery_scan()                # added: gap closed
return await pool.spawn_and_monitor(...)
```

**Test added:** `test_spawn_task_calls_recovery_scan` in `tests/test_recovery_scan.py` — asserts `run_recovery_scan` called exactly once and before `spawn_and_monitor` via mock call order tracking.

**Test suite:** 95/95 tests pass. 0 regressions.

---

_Verified: 2026-02-24T17:05:00Z_
_Verifier: Claude (gsd-verifier)_
