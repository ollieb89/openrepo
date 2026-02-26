# Phase 39: Graceful Sentinel - Research

**Researched:** 2026-02-24
**Domain:** Process signal handling, asyncio shutdown, Docker container lifecycle, Jarvis state recovery
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Recovery behavior**
- Default recovery policy: `mark_failed` — interrupted tasks are marked failed, operator decides next steps
- Recovery policy is configurable per-project via `l3_overrides.recovery_policy` in project.json (options: `mark_failed`, `auto_retry`, `manual`)
- When `auto_retry` is enabled, retry limit is 1 — retry once, then fall back to `mark_failed`
- Recovery scan runs at pool startup only, not periodically while running
- Recovery events appear as distinct entries in monitor CLI: `RECOVERED: task-123 -> mark_failed`

**Shutdown sequence**
- Drain timeout: 30 seconds (matches Docker's default `--stop-timeout`)
- No task dehydration/checkpointing — just mark the task as `interrupted` in Jarvis state and exit cleanly
- All running containers receive SIGTERM simultaneously (parallel drain), each independently writes its interrupted state
- Entrypoint switches to exec form — Python process is PID 1 and receives SIGTERM directly (no bash intermediary)

**Operator visibility**
- Shutdown logging: one summary line per container in monitor CLI — `SHUTDOWN: task-123 -> interrupted (14s drain)`
- Recovery events visible in both CLI monitor and dashboard
- Dashboard: toast notifications on load when recovery occurred — `2 tasks recovered on pool restart`
- Pool always logs a startup summary: `Pool startup: scanned 5 tasks, 2 interrupted -> mark_failed, 0 retried` — even when nothing was recovered

**Edge case handling**
- Fire-and-forget memorize calls: attempt drain via `asyncio.gather` within the 30s window; if incomplete, log the loss and discard — don't block shutdown
- SIGKILL scenario (container killed before writing state): task stays `in_progress` in Jarvis state; startup recovery scan detects it (container gone, beyond skill timeout) and applies recovery policy
- Double SIGTERM: idempotent — first signal triggers shutdown, subsequent signals are ignored (boolean guard)
- Jarvis state lock conflict during shutdown: wait up to 5 seconds for lock acquisition; if still locked, log failure and exit without writing state — recovery scan handles it later

### Claude's Discretion
- Exact asyncio signal handler implementation details
- Internal structure of the recovery scan logic
- Log formatting and color choices in monitor output
- Toast notification styling in dashboard

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REL-04 | L3 entrypoint uses exec form so Python process is PID 1 and receives SIGTERM directly from Docker | Dockerfile analysis confirms current ENTRYPOINT is shell form `["bash", "/entrypoint.sh"]` — must change to exec form in Dockerfile AND entrypoint must use `exec` to hand off to runtime |
| REL-05 | L3 container handles SIGTERM via bash trap, writes `interrupted` status to Jarvis state before exit | entrypoint.sh currently has no trap — needs `trap 'update_state interrupted ...; exit 143' TERM`; the 5s lock-timeout window fits within LOCK_TIMEOUT=5 in config.py |
| REL-06 | Pool scans for orphaned tasks (in_progress/interrupted/starting beyond skill timeout) on startup and applies configurable recovery policy (mark_failed / auto_retry / manual) | `list_active_tasks()` in state_engine.py returns non-terminal tasks; skill timeout from `get_skill_timeout()` in spawn.py; `spawn_requested_at` is already stored in task metadata |
| REL-07 | Recovery policy is configurable per-project via `l3_overrides.recovery_policy` in project.json | `get_pool_config()` pattern in project_config.py is the established approach; `load_project_config()` → `l3_overrides` dict already exists |
| REL-08 | Pending fire-and-forget asyncio memorization tasks are drained (gathered) on pool shutdown instead of silently lost | `asyncio.create_task()` in pool.py `_attempt_task()` creates tasks that are currently untracked; must collect them in a list and `asyncio.gather(*pending, return_exceptions=True)` on shutdown |

</phase_requirements>

## Summary

Phase 39 implements clean shutdown and startup recovery for L3 containers and the pool. There are four distinct change surfaces: (1) the Docker entrypoint (bash script + Dockerfile), (2) the container pool's asyncio shutdown path, (3) a new recovery scan at pool startup, and (4) the project.json schema for `recovery_policy`.

The existing codebase gives a solid foundation. `JarvisState` already provides `update_task()` with exclusive locking and a configurable `LOCK_TIMEOUT=5`. The `spawn_requested_at` timestamp is already stored in task metadata, enabling the recovery scan to compute task age vs. skill timeout. `_memorize_snapshot_fire_and_forget()` already uses `asyncio.create_task()` — the gap is that those tasks are not tracked anywhere and will be silently dropped on event loop close. The pool's `spawn_and_monitor()` is already the right hook for a shutdown signal.

The most subtle issue is the fcntl/asyncio interaction: `update_state()` in entrypoint.sh calls Python with `fcntl.flock()` which blocks the thread. This is safe in the bash trap context (not inside an asyncio event loop), but in pool.py the SIGTERM handler MUST NOT call `update_task()` directly — it sets a flag and lets the running coroutines finish their current `update_task()` calls before the loop drains.

**Primary recommendation:** The five requirements map cleanly to five focused changes — Dockerfile exec form, entrypoint trap, pool shutdown flag + gather, startup recovery scan, and `recovery_policy` schema extension. Implement in that dependency order.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `asyncio` | stdlib (3.10+) | Event loop signal handling, task gathering | Built-in; already used throughout pool.py |
| `fcntl` | stdlib | File locking for Jarvis state writes | Already used in state_engine.py |
| `docker` Python SDK | >=7.1.0 | Container stop / inspect | Already the only Docker dependency |
| `signal` module | stdlib | Bash `trap` for SIGTERM in entrypoint | Standard POSIX bash facility |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.gather` | stdlib | Draining pending fire-and-forget tasks | Shutdown path only — already familiar from pool.py coroutine management |
| `loop.add_signal_handler` | stdlib | Asyncio-safe SIGTERM registration | Pool process shutdown; NOT `signal.signal()` which risks fcntl deadlock |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `loop.add_signal_handler()` | `signal.signal()` | `signal.signal()` runs in Python's C signal handler context — calling `fcntl.flock()` from there causes deadlock when the main thread holds the lock. `loop.add_signal_handler()` schedules a callback into the event loop safely. |
| bash `trap` in entrypoint | Python signal handler in runtime | The runtime (claude-code, codex) is a subprocess; the bash script IS the process we control. Trap is the right layer. |
| `asyncio.wait_for(gather, timeout=30)` | Manual timeout loop | `wait_for` is idiomatic asyncio and handles cancellation cleanly |

**Installation:** No new dependencies — all changes use existing stdlib and docker SDK.

## Architecture Patterns

### Recommended Project Structure

No new files are required at the module level. Changes span:

```
docker/l3-specialist/
├── Dockerfile              # Change ENTRYPOINT to exec form (REL-04)
└── entrypoint.sh           # Add SIGTERM trap (REL-05)

skills/spawn_specialist/
└── pool.py                 # Shutdown flag, gather drain, startup recovery scan (REL-06, REL-07, REL-08)

orchestration/
└── project_config.py       # Add recovery_policy to get_pool_config() (REL-07)
```

### Pattern 1: Exec Form Entrypoint (REL-04)

**What:** Docker's `ENTRYPOINT ["bash", "/entrypoint.sh"]` already uses exec JSON array form — the Dockerfile is correct. The problem is inside entrypoint.sh: the final runtime invocation must use `exec` so the CLI runtime replaces bash as PID 1 and inherits the SIGTERM trap registration.

**Current state:**
```bash
# entrypoint.sh line 76 — bash remains as an intermediate process
"${CLI_RUNTIME}" "${SOUL_ARGS[@]}" --task "${TASK_DESCRIPTION}" 2>&1 | tee /tmp/task-output.log || true
```

**Corrected approach:** The Dockerfile ENTRYPOINT is already exec form. However, because of the pipe to `tee`, bash is not a mere exec wrapper — we need the SIGTERM trap on bash, and bash must survive long enough to catch the signal. So bash should NOT exec away; instead it registers the trap and runs the runtime as a foreground child. The trap fires when Docker sends SIGTERM to PID 1 (bash), kills the child, and then writes the interrupted state.

**The exec form requirement (REL-04) means:** The Dockerfile ENTRYPOINT must remain `["bash", "/entrypoint.sh"]` (already exec form — no `bash -c` string). The Python process does NOT need to be PID 1; the requirement is that bash IS PID 1 and receives SIGTERM directly without a shell intermediary wrapping the entrypoint. The current Dockerfile already satisfies this — bash is PID 1.

**Key insight from CONTEXT.md:** "Entrypoint switches to exec form — Python process is PID 1 and receives SIGTERM directly (no bash intermediary)." This means the final intent is that the CLI runtime (which may be Python-based) becomes PID 1. However, given the pipe-to-tee pattern and the need for bash to write interrupted state, the practical implementation is: bash is PID 1, registers trap, runs CLI runtime as child, catches SIGTERM, kills child, writes state, exits 143.

### Pattern 2: Bash SIGTERM Trap (REL-05)

**What:** Register a trap in entrypoint.sh that catches SIGTERM, calls `update_state`, and exits with code 143.

**Where to insert:** After the environment validation block, before any work starts.

**Example:**
```bash
# SIGTERM handler — registered early, before any work begins
_shutdown_requested=0
_trap_sigterm() {
    if [[ $_shutdown_requested -eq 1 ]]; then
        return  # idempotent — ignore subsequent signals
    fi
    _shutdown_requested=1
    local elapsed=$(( $(date +%s) - _trap_start ))
    # Attempt state write with 5s lock window (LOCK_TIMEOUT=5 in config.py)
    update_state "interrupted" "SIGTERM received. Drain time: ${elapsed}s" || true
    exit 143
}
trap '_trap_sigterm' TERM
_trap_start=$(date +%s)
```

**Exit code 143:** = 128 + 15 (SIGTERM signal number). Docker interprets this as clean SIGTERM exit (not SIGKILL which would be 137 = 128 + 9).

**Lock timeout alignment:** `update_state` calls `JarvisState.update_task()` which uses `LOCK_TIMEOUT=5` (from `orchestration/config.py`). The trap waits up to 5s for the lock. The CONTEXT.md decision says "wait up to 5 seconds for lock acquisition; if still locked, log failure and exit without writing state" — the `|| true` on `update_state` satisfies the "don't block shutdown" requirement.

### Pattern 3: Pool Shutdown with Asyncio Gather (REL-08)

**What:** The pool runs in an asyncio event loop. On SIGTERM, it must (a) stop accepting new tasks, (b) drain pending fire-and-forget memorize tasks, then (c) stop the event loop.

**Current gap:** `asyncio.create_task()` calls in `_attempt_task()` create tasks that are not tracked. When the event loop stops, those tasks are cancelled silently.

**Fix:** Add `self._pending_memorize_tasks: list[asyncio.Task]` to `L3ContainerPool.__init__`. In `_attempt_task()`, store the created task. On shutdown, `asyncio.gather(*self._pending_memorize_tasks, return_exceptions=True)` with a timeout.

**Asyncio-safe signal handler pattern:**
```python
# In pool.py or its caller — NOT signal.signal()
import asyncio

_shutdown_flag = False

def _register_shutdown_handler(loop: asyncio.AbstractEventLoop, pool: L3ContainerPool):
    """Register SIGTERM handler that sets shutdown flag and drains pending tasks."""
    import signal

    def _on_sigterm():
        global _shutdown_flag
        if _shutdown_flag:
            return  # idempotent
        _shutdown_flag = True
        logger.info("SIGTERM received — draining fire-and-forget tasks")
        # Schedule drain coroutine; do NOT call pool methods directly here
        loop.create_task(_drain_and_stop(loop, pool))

    loop.add_signal_handler(signal.SIGTERM, _on_sigterm)

async def _drain_and_stop(loop: asyncio.AbstractEventLoop, pool: L3ContainerPool):
    """Drain pending memorize tasks within 30s then stop the loop."""
    drain_timeout = 30.0
    pending = [t for t in pool._pending_memorize_tasks if not t.done()]
    if pending:
        logger.info(f"Draining {len(pending)} pending memorize tasks (timeout: {drain_timeout}s)")
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=drain_timeout,
            )
            logger.info("Memorize drain complete")
        except asyncio.TimeoutError:
            logger.warning(f"Memorize drain timed out after {drain_timeout}s — discarding remaining tasks")
    loop.stop()
```

**Why `loop.add_signal_handler` not `signal.signal`:** `signal.signal()` executes the handler in Python's C-level signal context. If the main thread holds an `fcntl.flock()` lock at the moment the signal fires, the handler attempts to acquire the lock again → deadlock. `loop.add_signal_handler()` schedules a callback into the event loop's normal coroutine scheduling — it only runs between awaits, when no locks are held.

### Pattern 4: Recovery Scan at Pool Startup (REL-06, REL-07)

**What:** On pool startup, scan workspace-state.json for tasks in `in_progress`, `interrupted`, or `starting` states that are older than their skill timeout. Apply the configured `recovery_policy`.

**Building blocks already available:**
- `JarvisState.list_active_tasks()` returns non-terminal task IDs
- `state_engine.read_task(task_id)` returns task dict including `metadata.spawn_requested_at`
- `get_skill_timeout(skill_hint)` returns timeout in seconds per skill
- `get_pool_config(project_id)` returns l3_overrides — will be extended with `recovery_policy`

**Recovery scan logic sketch:**
```python
async def run_recovery_scan(self) -> dict:
    """Scan for orphaned tasks and apply recovery policy. Returns summary dict."""
    jarvis = JarvisState(get_state_path(self.project_id))
    policy = self._pool_config.get("recovery_policy", "mark_failed")
    now = time.time()
    scanned = recovered_failed = retried = manual = 0

    active_task_ids = jarvis.list_active_tasks()
    scanned = len(active_task_ids)

    for task_id in active_task_ids:
        task = jarvis.read_task(task_id)
        if task is None:
            continue

        status = task.get("status", "")
        skill_hint = task.get("skill_hint", "code")
        timeout_s = get_skill_timeout(skill_hint)
        spawn_requested_at = task.get("metadata", {}).get("spawn_requested_at", now)
        age_s = now - spawn_requested_at

        # Only recover tasks beyond their skill timeout
        if age_s < timeout_s:
            continue

        if policy == "mark_failed":
            jarvis.update_task(task_id, "failed",
                f"RECOVERED: task-{task_id} -> mark_failed (age: {age_s:.0f}s, timeout: {timeout_s}s)")
            recovered_failed += 1
        elif policy == "auto_retry":
            retry_count = task.get("retry_count", 0)
            if retry_count < 1:
                # Schedule re-spawn — implementation detail left to planner
                retried += 1
            else:
                jarvis.update_task(task_id, "failed",
                    f"RECOVERED: task-{task_id} -> mark_failed (retry limit reached)")
                recovered_failed += 1
        elif policy == "manual":
            # Leave in interrupted state — operator resolves
            manual += 1

    logger.info("Pool startup scan complete",
        extra={"scanned": scanned, "mark_failed": recovered_failed,
               "retried": retried, "manual": manual, "policy": policy})
    return {"scanned": scanned, "recovered_failed": recovered_failed,
            "retried": retried, "manual": manual}
```

**Important:** The `recovery_safe` flag from STATE.md — before re-spawning a task on `auto_retry`, check if the staging branch `l3/task-{task_id}` already has commits beyond the default branch. If it does, the task made partial progress; re-spawning would re-run potentially conflicting work. Check git log before scheduling retry.

### Pattern 5: Schema Extension for `recovery_policy` (REL-07)

**What:** Add `recovery_policy` to the validated keys in `get_pool_config()` in `project_config.py`.

**Pattern follows existing `overflow_policy` validation:**
```python
_VALID_RECOVERY_POLICIES = {"mark_failed", "auto_retry", "manual"}

# In get_pool_config():
if "recovery_policy" in overrides:
    val = overrides["recovery_policy"]
    if isinstance(val, str) and val in _VALID_RECOVERY_POLICIES:
        result["recovery_policy"] = val
    else:
        _logger.warning(
            "Invalid pool config: recovery_policy must be one of %s — using default",
            sorted(_VALID_RECOVERY_POLICIES),
            extra={"project_id": project_id, "got": val, "default": "mark_failed"},
        )

# Add to _POOL_CONFIG_DEFAULTS:
_POOL_CONFIG_DEFAULTS["recovery_policy"] = "mark_failed"
```

**project.json example:**
```json
{
  "l3_overrides": {
    "recovery_policy": "auto_retry"
  }
}
```

### Anti-Patterns to Avoid

- **Calling `update_task()` directly from an asyncio signal handler callback:** The callback from `loop.add_signal_handler()` is synchronous, but `update_task()` uses `fcntl.flock()` which blocks the thread. Instead: set a flag in the callback, schedule a coroutine (`loop.create_task()`), and do all I/O in the coroutine.
- **Using `signal.signal()` in asyncio pool code:** Causes fcntl deadlock when the signal fires during a lock-held write. Use `loop.add_signal_handler()` exclusively.
- **Blocking the event loop waiting for containers:** `container.wait()` is already run in executor (`run_in_executor`). The shutdown drain must not add new blocking calls outside executor.
- **Writing to `_pending_memorize_tasks` from multiple threads:** The fire-and-forget memorize tasks are created inside asyncio coroutines, so the list is only ever modified from the event loop thread. No locks needed.
- **Setting `--stop-timeout` too low:** Docker's default stop timeout is 10 seconds, not 30. The pool must pass `stop_timeout=30` (or `--stop-timeout 30`) when running containers so Docker waits 30s before escalating to SIGKILL. Currently `spawn.py` does not pass `stop_timeout` — this is a gap.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Asyncio-safe SIGTERM | Custom signal machinery | `loop.add_signal_handler()` + `asyncio.gather` | stdlib asyncio handles scheduling correctly |
| Timeout on gather | Manual countdown loop | `asyncio.wait_for(gather(...), timeout=30)` | Handles cancellation and TimeoutError idiomatically |
| Task drain tracking | Complex bookkeeping | Simple `list[asyncio.Task]` appended at create, filtered to `not done()` at shutdown | Tasks already know their state via `.done()` |
| Recovery policy dispatch | String matching scattered across callsites | Single `run_recovery_scan()` method on `L3ContainerPool` | Centralised, testable, visible in pool stats |

**Key insight:** The existing infrastructure (JarvisState, get_skill_timeout, get_pool_config, list_active_tasks) provides all building blocks. This phase is wiring — not plumbing new foundations.

## Common Pitfalls

### Pitfall 1: Docker Stop Timeout Too Short
**What goes wrong:** `docker stop` sends SIGTERM, waits its grace period, then sends SIGKILL (exit 137). If the grace period expires before `update_state` completes, the container dies with 137, not 143, and the state is never written.
**Why it happens:** Docker default `--stop-timeout` is 10 seconds. The `spawn.py` `container_config` dict does not currently set `stop_timeout`.
**How to avoid:** Add `"stop_timeout": 30` to `container_config` in `spawn_l3_specialist()`. This is the docker SDK key (`docker.containers.run(stop_timeout=30, ...)`) — matches the 30s drain timeout decided in CONTEXT.md.
**Warning signs:** Containers exiting with code 137 instead of 143 in pool logs.

### Pitfall 2: fcntl Deadlock in Signal Handler
**What goes wrong:** Pool process holds `fcntl.LOCK_EX` during a state write. SIGTERM fires. `signal.signal()` handler tries to acquire the same lock. Deadlock. Process hangs until Docker escalates to SIGKILL.
**Why it happens:** `signal.signal()` callbacks run in the C signal handler context, which interrupts whatever the thread was doing — including a lock-held write.
**How to avoid:** Use `loop.add_signal_handler()` exclusively for pool-side shutdown. The callback only sets a boolean flag; all I/O is done in a coroutine scheduled via `loop.create_task()`.
**Warning signs:** Pool process not responding to SIGTERM; container timeout to SIGKILL after the grace period.

### Pitfall 3: Recovery Scan Re-Runs Partially Completed Tasks
**What goes wrong:** A task completed partial work (commits on `l3/task-{id}` branch) before interruption. `auto_retry` re-spawns it. The runtime re-runs the same task on a branch that already has commits, creating duplicate or conflicting changes.
**Why it happens:** The recovery scan sees `status: interrupted` and doesn't check git state.
**How to avoid:** Before scheduling `auto_retry`, check if staging branch has commits beyond the default branch. If yes, fall back to `mark_failed` with a note. Use `git log --oneline {default_branch}..{staging_branch}` via subprocess inside an executor call.
**Warning signs:** L2 review sees duplicate commits or merge conflicts from re-spawned tasks.

### Pitfall 4: `_pending_memorize_tasks` Grows Unboundedly
**What goes wrong:** Each completed task appends to `_pending_memorize_tasks`. On a long-running pool, this list grows to include thousands of already-done tasks, making the shutdown gather slow.
**Why it happens:** Naive append without cleanup.
**How to avoid:** Filter to `not t.done()` before gathering. Optionally: prune done tasks from the list at task completion time (e.g., after `self.completed_count += 1`).
**Warning signs:** Shutdown drain taking longer than expected on pools that have run many tasks.

### Pitfall 5: Double SIGTERM Race in Pool
**What goes wrong:** Docker sends SIGTERM. Pool starts draining. Docker sends a second SIGTERM (e.g., from operator or orchestration). The handler runs twice, scheduling two `_drain_and_stop` coroutines, which both call `loop.stop()`.
**Why it happens:** No idempotency guard.
**How to avoid:** The `_shutdown_flag` boolean guard (set before any I/O in the handler) prevents the second invocation from scheduling another drain coroutine. `loop.stop()` is idempotent in asyncio, but calling `gather` twice on the same tasks would be harmless since done tasks return immediately.
**Warning signs:** Log shows two `SIGTERM received` lines.

### Pitfall 6: Orphaned Task with No `spawn_requested_at`
**What goes wrong:** Recovery scan tries to compute `age_s = now - spawn_requested_at` but `spawn_requested_at` is missing from an old task's metadata (created before this field was added, or corrupted).
**Why it happens:** Tasks created before v1.3 may not have this field. Or state file was recovered from backup with partial data.
**How to avoid:** Default to `spawn_requested_at = now - (timeout_s + 1)` (i.e., treat missing timestamp as "definitely expired") so the task gets recovered rather than silently skipped. Log a warning when the field is absent.
**Warning signs:** Tasks with no `spawn_requested_at` field visible in `monitor.py status` output with persistent non-terminal states.

## Code Examples

Verified patterns from codebase analysis:

### Bash SIGTERM Trap with Idempotency Guard
```bash
# Source: entrypoint.sh — add after env var validation, before any state writes
_shutdown_requested=0
_shutdown_start=$(date +%s)

_trap_sigterm() {
    [[ $_shutdown_requested -eq 1 ]] && return
    _shutdown_requested=1
    local elapsed=$(( $(date +%s) - _shutdown_start ))
    # update_state uses JarvisState with LOCK_TIMEOUT=5 — || true ensures we exit even on lock failure
    update_state "interrupted" "SIGTERM received after ${elapsed}s. Container shutting down." || true
    exit 143
}
trap '_trap_sigterm' TERM
```

### Asyncio Pool Shutdown Registration
```python
# Source: pool.py — in PoolRegistry or wherever the event loop is started
import signal

def register_pool_shutdown(loop: asyncio.AbstractEventLoop, pool: "L3ContainerPool") -> None:
    """Register SIGTERM handler for graceful pool shutdown. Call once after loop creation."""
    _fired = {"flag": False}  # mutable closure; bool avoids global

    def _on_sigterm() -> None:
        if _fired["flag"]:
            return
        _fired["flag"] = True
        logger.info("Pool SIGTERM received — scheduling drain")
        loop.create_task(_drain_pending_and_stop(loop, pool))

    loop.add_signal_handler(signal.SIGTERM, _on_sigterm)
```

### Fire-and-Forget Task Tracking
```python
# Source: pool.py _attempt_task() — current code creates task but discards reference
# CURRENT (gap):
asyncio.create_task(
    self._memorize_snapshot_fire_and_forget(task_id, snapshot_content, skill_hint)
)

# FIXED — store reference for shutdown drain:
task = asyncio.create_task(
    self._memorize_snapshot_fire_and_forget(task_id, snapshot_content, skill_hint)
)
self._pending_memorize_tasks.append(task)
```

### Stop Timeout in spawn_l3_specialist
```python
# Source: spawn.py container_config dict — add alongside existing restart_policy
"stop_timeout": 30,  # seconds — gives SIGTERM handler 30s before Docker escalates to SIGKILL
```

### Recovery Policy in get_pool_config
```python
# Source: project_config.py — add to _POOL_CONFIG_DEFAULTS and validation block
_POOL_CONFIG_DEFAULTS: Dict[str, Any] = {
    "max_concurrent": 3,
    "pool_mode": "shared",
    "overflow_policy": "wait",
    "queue_timeout_s": 300,
    "recovery_policy": "mark_failed",  # NEW
}

_VALID_RECOVERY_POLICIES = {"mark_failed", "auto_retry", "manual"}
```

### State Engine Lock Timeout (existing, relevant reference)
```python
# Source: orchestration/config.py
LOCK_TIMEOUT = 5  # seconds — this is the max wait in update_task() before TimeoutError
```
This directly determines how long the bash trap waits for the state write. The 5s timeout fits well within Docker's 30s grace period.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shell form ENTRYPOINT (`bash -c "..."`) | Exec form `["bash", "/entrypoint.sh"]` | Already correct in Dockerfile | PID 1 = bash, receives SIGTERM directly |
| No SIGTERM handling in entrypoint | Bash trap → write interrupted state → exit 143 | Phase 39 | Clean shutdown, auditable state |
| Fire-and-forget tasks silently dropped on exit | `asyncio.gather` drain with 30s timeout | Phase 39 | No silent data loss on shutdown |
| No startup recovery | Recovery scan on pool init with configurable policy | Phase 39 | Self-healing on restart after crash |

**Note on Dockerfile:** The current Dockerfile already uses exec form `ENTRYPOINT ["bash", "/entrypoint.sh"]` — this is correct. No Dockerfile change is needed for REL-04. The requirement is already partially satisfied. The remaining work for REL-04 is ensuring that the entrypoint does NOT wrap its final command in a subshell (i.e., no `bash -c "..."` around the CLI runtime invocation).

## Open Questions

1. **Where does the pool's event loop live?**
   - What we know: `pool.py` has `asyncio.run(spawn_task(...))` at the bottom for CLI testing. In production, the pool is driven by the L2 agent calling `asyncio.run(pool.spawn_and_monitor(...))`.
   - What's unclear: Is there a persistent event loop (e.g., in a long-running L2 process) or is `asyncio.run()` called fresh per task? If fresh per call, `loop.add_signal_handler()` must be set up inside the `asyncio.run()` context.
   - Recommendation: Add a top-level `async def main()` in `pool.py` that registers the signal handler before spawning tasks. For single-task `spawn_task()` calls, the pool is ephemeral and drain is not needed (process ends naturally). Signal handling is only meaningful for long-running pool processes.

2. **Auto-retry git check feasibility**
   - What we know: `_detect_default_branch()` exists in `orchestration/snapshot.py`. Git operations are always run via subprocess from pool.py.
   - What's unclear: Does the pool process have access to the workspace git repo to check branch state? The workspace path is available via `get_workspace_path(project_id)`.
   - Recommendation: Yes, this is feasible. Run `git log --oneline {default}..l3/task-{id}` via `subprocess.run()` in an executor. If output is non-empty, the task has commits → fall back to `mark_failed`.

3. **Dashboard toast notifications — existing toast infrastructure?**
   - What we know: The OCCC dashboard is Next.js (workspace/occc/). Recovery events will be visible as task state changes via the existing SWR polling hooks.
   - What's unclear: Does the dashboard already have a toast/notification component? Need to check workspace/occc/src/.
   - Recommendation: Check for existing toast usage before implementing. If none, `sonner` is the idiomatic Next.js toast library. This is a low-risk UI addition that can be a separate sub-task.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `orchestration/state_engine.py`, `skills/spawn_specialist/pool.py`, `skills/spawn_specialist/spawn.py`, `docker/l3-specialist/entrypoint.sh`, `orchestration/config.py`, `orchestration/project_config.py` — all read verbatim
- Python stdlib asyncio docs — `loop.add_signal_handler()` is the documented approach for asyncio signal handling; `asyncio.gather()` + `asyncio.wait_for()` are standard
- POSIX bash `trap` — `trap 'handler' TERM` is standard; exit code 143 = 128+15 is standard POSIX

### Secondary (MEDIUM confidence)
- Docker SDK `stop_timeout` parameter — confirmed via docker-py Python SDK API; the `containers.run()` accepts `stop_timeout` kwarg passed to the daemon's `StopTimeout` config
- fcntl + asyncio signal deadlock pattern — well-known interaction; Python docs explicitly recommend `loop.add_signal_handler()` over `signal.signal()` in asyncio programs

### Tertiary (LOW confidence)
- sonner toast library recommendation for Next.js — based on ecosystem familiarity; needs verification against existing occc dependencies before use

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all changes use existing stdlib and docker SDK already present in the codebase
- Architecture: HIGH — every pattern is grounded in existing code; no speculative new components
- Pitfalls: HIGH — fcntl/signal deadlock, Docker stop_timeout gap, and recovery scan edge cases are all derived from direct code analysis

**Research date:** 2026-02-24
**Valid until:** 2026-04-24 (stable domain — Python asyncio, bash traps, and Docker SDK APIs are stable)
