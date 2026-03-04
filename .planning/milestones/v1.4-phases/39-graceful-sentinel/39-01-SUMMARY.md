---
phase: 39-graceful-sentinel
plan: 01
subsystem: l3-container-shutdown
tags: [sigterm, docker, bash-trap, graceful-shutdown, reliability]
dependency_graph:
  requires: []
  provides: [l3-sigterm-handling, l3-stop-timeout]
  affects: [docker/l3-specialist/entrypoint.sh, skills/spawn_specialist/spawn.py]
tech_stack:
  added: []
  patterns: [bash-sigterm-trap, docker-stop-timeout, background-process-wait]
key_files:
  created:
    - tests/test_entrypoint_shutdown.py
  modified:
    - docker/l3-specialist/entrypoint.sh
    - skills/spawn_specialist/spawn.py
decisions:
  - "CLI runtime backgrounded with pipe-to-tee and wait so PID 1 (bash) remains free to receive SIGTERM"
  - "_child_pid captures the tee PID (last pipeline stage); killing tee sends SIGPIPE to CLI runtime — acceptable shutdown path"
  - "stop_timeout=30 matches drain window from CONTEXT.md; exceeds JarvisState LOCK_TIMEOUT (5s) plus overhead"
metrics:
  duration_seconds: 69
  completed: "2026-02-24"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 39 Plan 01: L3 Entrypoint SIGTERM Handling Summary

SIGTERM trap added to entrypoint.sh with idempotency guard, 143 exit code, and Docker stop_timeout=30 in spawn.py.

## What Was Built

L3 container entrypoint now catches `SIGTERM` (sent by `docker stop`) and performs a clean shutdown:

1. Writes `interrupted` status to Jarvis state with elapsed time
2. Kills the CLI runtime child process (SIGPIPE via tee pipe kill)
3. Exits with code 143 (128 + 15) rather than being killed with 137 (SIGKILL)

Docker is now given 30 seconds of grace before escalating to SIGKILL, which is sufficient for `update_state()` to complete even under lock contention (JarvisState LOCK_TIMEOUT is 5s).

## Tasks Completed

| # | Name | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Add SIGTERM trap to entrypoint.sh | f797a1f | docker/l3-specialist/entrypoint.sh |
| 2 | Add stop_timeout to spawn.py and create tests | 7e2dbfb | skills/spawn_specialist/spawn.py, tests/test_entrypoint_shutdown.py |

## Implementation Details

### entrypoint.sh Changes

- Added `_shutdown_requested=0` flag before trap registration
- Added `_trap_sigterm()` function: idempotency guard, elapsed-time calculation, state write, child kill, exit 143
- Registered trap with `trap '_trap_sigterm' TERM` immediately after `update_state` helper, before git config
- Added `_task_start_time=$(date +%s)` for elapsed time tracking in trap message
- CLI runtime invocation changed from foreground pipe to: `command 2>&1 | tee /tmp/task-output.log &` + `_child_pid=$!` + `wait $_child_pid || true` + `EXIT_CODE=$?`

### spawn.py Changes

- Added `"stop_timeout": 30` to `container_config` dict adjacent to `restart_policy`
- Documented in comment: must be >= JarvisState LOCK_TIMEOUT (5s) + overhead; 30s matches CONTEXT.md drain window

### Tests (7 static analysis, no Docker daemon required)

- `test_entrypoint_has_sigterm_trap` — confirms trap line present
- `test_entrypoint_trap_is_idempotent` — confirms `_shutdown_requested` flag and guard
- `test_entrypoint_exits_143` — confirms correct exit code
- `test_entrypoint_trap_before_work` — confirms trap line number < `update_state "starting"` line number
- `test_dockerfile_exec_form` — confirms `ENTRYPOINT ["bash", "/entrypoint.sh"]` JSON array form
- `test_spawn_has_stop_timeout` — confirms `"stop_timeout": 30` in spawn.py
- `test_entrypoint_child_backgrounded` — confirms `_child_pid=$!` and `wait $_child_pid`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `~/.openclaw/docker/l3-specialist/entrypoint.sh` — FOUND, contains trap
- `~/.openclaw/skills/spawn_specialist/spawn.py` — FOUND, contains stop_timeout
- `~/.openclaw/tests/test_entrypoint_shutdown.py` — FOUND, 7 tests all pass
- Commit f797a1f — FOUND
- Commit 7e2dbfb — FOUND
