# Pitfalls Research

**Domain:** Adding config consolidation, adaptive polling, Docker health checks, and cosine threshold calibration to existing OpenClaw swarm orchestration system (v1.5)
**Researched:** 2026-02-25
**Confidence:** HIGH — derived from direct codebase inspection of `project_config.py`, `config.py`, `config_validator.py`, `state_engine.py`, `monitor.py`, `scan_engine.py`, `pool.py`, `docker/l3-specialist/Dockerfile` and `entrypoint.sh`, plus targeted research on Docker HEALTHCHECK signal interactions, adaptive polling backoff patterns, and vector similarity threshold calibration

---

## Critical Pitfalls

### Pitfall 1: Path Resolver Consolidation Breaks Existing State Files and Cached State

**What goes wrong:**
The v1.5 goal is a single authoritative workspace path resolver. The current system has a known divergence: runtime state is written at `data/workspace/.openclaw/` while code resolves to `OPENCLAW_ROOT/workspace/.openclaw/`. Consolidating to one path without migrating existing state files causes the new resolver to compute a path that does not contain the live `workspace-state.json`. The pool's startup recovery scan reads the state path from the new resolver, finds no file, creates a fresh state file, and silently discards all task history and cursor positions for every registered project. The memory delta cursor (introduced in v1.4 as a SHA stored in state.json) is also lost — all projects revert to full memory fetches on next spawn.

The mtime-based state cache in `JarvisState` compounds this: if any component holds a cached `JarvisState` instance pointing to the old path, writes go to the old path while reads from the new path return a freshly created empty file. Components see divergent state with no error raised.

**Why it happens:**
The divergence was pre-existing and accepted as technical debt. When the consolidation is implemented, developers update `_find_project_root()` and `get_state_path()` but do not perform a data migration step — the old state files remain at the old path, unreachable by the new resolver. This is the standard "moved the pointer but not the data" config migration failure.

**How to avoid:**
- Define the canonical path first. Document it explicitly before writing any code.
- Write the migration CLI (CONF-03) before the path resolver change. The migration must: (a) discover all existing state files at the old path, (b) copy them to the new canonical path, (c) verify checksums, (d) print a migration report. Only then should the resolver code change.
- In `get_state_path()`, add a one-time check: if the old path contains a state file and the new path does not, log a CRITICAL warning and raise an error rather than silently returning an empty new path. Force the operator to run the migration CLI explicitly.
- Integration test: verify that `get_state_path()` returns the same path before and after the resolver change when called with the same `project_id`. Run this test against real files, not just the function's return value.
- Never silently create a missing state file during `get_state_path()` — a missing state file after a resolver change is always a symptom of migration failure, not a normal "first run" condition.

**Warning signs:**
- After deploying the path resolver change, `openclaw-monitor status` shows zero tasks for all projects despite active work
- Pool startup recovery scan finds no orphaned tasks even when the system was interrupted mid-task before deployment
- Memory retrieval on first spawn after the change fetches a full memory set (cursor reset to None) for every project
- `get_state_path()` returns a path that does not yet exist on disk for projects that have been running for weeks

**Phase to address:** CONF-01 (path resolver) — the migration CLI from CONF-03 must be built and validated before CONF-01 is implemented. Do not reverse this order.

---

### Pitfall 2: Migration CLI Overwrites Live State During Active Spawns

**What goes wrong:**
The migration CLI copies state files from the old path to the new canonical path. If run while a project has active L3 containers, the source state file is being written to by those containers via `JarvisState.update_task()` with `fcntl.LOCK_EX`. The migration CLI's copy operation is not fcntl-aware — it does a standard `shutil.copy2()` or equivalent, which does not acquire the flock before reading. The copy captures a mid-write state: the destination file contains a valid JSON prefix followed by truncated bytes (the interrupted write from the lock holder), or it captures a state that is one or more `update_task()` calls behind.

After migration, the new resolver reads the destination file. If the JSON is truncated, the state engine falls back to the `.bak` recovery path. If the JSON is valid but stale, in-flight tasks show `in_progress` without the most recent status updates, confusing the recovery scan.

**Why it happens:**
Configuration migration tools are typically written as one-shot scripts with no awareness of the application's own locking protocol. The `fcntl.LOCK_SH` / `fcntl.LOCK_EX` locks used by `JarvisState` are process-level file advisory locks — they are invisible to `cp` and `shutil.copy2()`.

**How to avoid:**
- The migration CLI must acquire `fcntl.LOCK_SH` on the source state file before reading it, and release after the copy is complete. Use the same lock acquisition code as `JarvisState._read_state_locked()`.
- Alternatively, document clearly that the migration CLI must only be run when all L3 containers are stopped (`docker ps` shows no `openclaw-*-l3-*` containers). Add an explicit pre-flight check in the migration CLI that aborts if any running containers match the OpenClaw naming pattern.
- Include a dry-run mode (`--dry-run`) that prints what would be migrated without writing anything.
- After the copy, verify the destination is valid JSON before declaring success. If not, delete the destination and report failure.

**Warning signs:**
- Migration CLI exits successfully but `state_engine.py` falls back to `.bak` recovery on first read of the migrated file
- `workspace-state.json` at the new path has a file size smaller than the `.bak` at the old path
- Tasks that were `in_progress` during migration show as `in_progress` at the new path but are actually completed (their containers exited while the migration copy captured a stale snapshot)

**Phase to address:** CONF-03 (migration CLI) — add the `fcntl.LOCK_SH` acquisition and container pre-flight check before the CLI is usable in production.

---

### Pitfall 3: Strict Fail-Fast Startup Validation Kills the Daemon Before State Recovery Can Run

**What goes wrong:**
CONF-06 requires fail-fast startup validation: if `openclaw.json` or `project.json` is invalid, the process must abort immediately. However, the pool's startup recovery scan (implemented in v1.4) needs to run at startup to detect orphaned tasks and apply the configured `recovery_policy`. If strict validation happens first and a schema violation is present (e.g., a partially migrated config from CONF-03), the process exits before the recovery scan runs. Orphaned tasks from the pre-restart run are never cleaned up — they remain `in_progress` in the state file indefinitely. On the next start (after the config is fixed), the recovery scan sees these as new orphans and processes them again, potentially re-spawning work that was completed before the aborted restart.

Additionally, the existing `config_validator.py` raises `ConfigValidationError` on schema violations. If startup validation calls `load_and_validate_openclaw_config()` before pool initialization, any config issue prevents the pool from ever starting — including issues that would not affect spawning (e.g., an unknown field added by a future version of the schema).

**Why it happens:**
Fail-fast validation is the right design for config errors that would cause runtime failures. But startup sequencing is subtle: recovery must run even when config is degraded, and validation must distinguish "fatal for spawning" errors from "advisory warnings about unknown fields".

**How to avoid:**
- Define a clear startup sequence: (1) load config with recovery-mode permissiveness — any parse error is fatal, but schema warnings are non-fatal; (2) run pool recovery scan; (3) apply strict validation before accepting new spawn requests.
- Distinguish between "cannot operate" errors (missing `active_project`, unparseable JSON) and "schema advisory" warnings (unknown fields, deprecated keys). Only "cannot operate" errors abort before recovery.
- Add a `--recover-only` flag to the pool CLI that runs only the recovery scan and exits, bypassing all validation. This allows operators to manually drain orphans even when the config is broken.
- Never call `validate_agent_hierarchy()` before pool recovery — agent hierarchy validation is only needed for dispatch, not for reading existing state.

**Warning signs:**
- After a config schema change, the process cannot start even though the previous config was valid — the migration CLI introduced a new required field that the old config lacks
- Pool startup logs show `ConfigValidationError` followed by exit, with no recovery scan log entries
- Tasks that were `in_progress` before the config was broken accumulate indefinitely without cleanup

**Phase to address:** CONF-06 (fail-fast validation) — define the startup sequence explicitly before implementing validation. Recovery must be sequenced before strict validation of spawn-time config.

---

### Pitfall 4: Adaptive Polling Misses State Transitions During the Cooldown Window

**What goes wrong:**
OBS-05 requires the monitor poll interval to adapt dynamically to activity level: fast polling when tasks are active, slow polling during idle periods. The naive implementation backs off to a long interval (e.g., 10 seconds) after N idle polls. If a new task is spawned during the idle period, the monitor does not detect it until the next poll fires — up to 10 seconds later. For the CLI monitor, this is acceptable latency. For the dashboard SSE stream, it causes the "task started" event to appear late, making the dashboard feel unresponsive.

A worse failure: if adaptive polling uses a wall-clock timer to determine the next poll time, and the state file is modified at exactly the start of a long cooldown window, the monitor may report the old state for the full cooldown duration. This manifests as tasks appearing "stuck" at their previous status in the dashboard.

The thrashing problem is the inverse: if the threshold for "active" detection is too sensitive (e.g., any state file mtime change triggers fast mode), the monitor may never leave fast mode, burning CPU at 1-second intervals even when only background writes (e.g., activity log rotation) are touching the file.

**Why it happens:**
Adaptive polling requires two thresholds: (1) what counts as "activity" to trigger fast mode, and (2) how long to stay in fast mode after the last activity. Setting both thresholds correctly requires understanding the actual write frequency of `workspace-state.json` in normal operation — which includes activity log rotation writes that are not task-status changes. Developers typically set thresholds based on intuition, not measurement.

**How to avoid:**
- Define "activity" precisely: a task status change (`starting`, `in_progress`, `completed`, `failed`, `interrupted`) counts as activity. An activity log rotation write does not. Implement this by comparing the current task status map against the previous poll's task status map, not by mtime change alone.
- Use a hysteresis approach: enter fast mode (1s interval) on any task status change. Return to slow mode (5s interval — not 10s) only after N consecutive polls with no status change. Keep slow mode fast enough that spawned tasks are visible within 5 seconds.
- Cap the maximum poll interval at 5 seconds regardless of idle duration. A 10-second cap is too long for a monitoring tool and offers minimal CPU savings over 5 seconds.
- Never use mtime change alone as the activity signal — log rotation, `.bak` writes, and cursor updates all touch mtime without changing task status.
- Write a test that verifies: if a task status changes during a simulated idle period, the next poll always detects it within `max_slow_interval + 1` seconds.

**Warning signs:**
- Dashboard shows a task as "not started" for more than 5 seconds after `spawn_task()` returns successfully
- Monitor CPU usage is consistently 100% even with no active containers (thrashing on non-task mtime changes)
- Monitor remains in "slow mode" while containers are actively running (threshold misconfigured: activity detection too strict)
- Two consecutive polls return identical state but the state file mtime changed between them (mtime used as activity signal rather than status comparison)

**Phase to address:** OBS-05 (adaptive polling) — define the activity detection strategy and interval bounds before implementation. Validate that the activity signal (status change, not mtime) eliminates false positives from activity log rotation.

---

### Pitfall 5: Docker HEALTHCHECK Exits Unhealthy During SIGTERM Drain Window

**What goes wrong:**
REL-09 adds Docker `HEALTHCHECK` to L3 containers. A typical health check script verifies the container is "alive" — e.g., checks that the entrypoint process is running and the state file is readable. During graceful shutdown (when `docker stop` sends SIGTERM), the entrypoint's `_trap_sigterm` handler is executing: it calls `update_state "interrupted" ...` and then `exit 143`. This execution takes 1-3 seconds. During this window, the health check fires and may observe a degraded state: the task output log has been flushed, the child PID (`_child_pid`) has been killed, and the state file may be mid-write.

The health check reports unhealthy. Docker's response to an unhealthy container depends on how it is run: in a `docker run` context (OpenClaw's current usage), an unhealthy status has no automatic effect. But if the system is ever placed behind Docker Compose with `depends_on: condition: service_healthy`, the unhealthy status during shutdown will cause cascading restarts of dependent services.

A secondary issue: the health check script itself may require tools (`curl`, `python3`, `jq`) that are installed in the L3 image but run as UID 1000 (non-root). If the health check script is placed at a path only readable by root, or if the tools require elevated capabilities (removed by `cap_drop ALL`), the health check permanently fails.

**Why it happens:**
HEALTHCHECK is typically added for liveness verification during normal operation. Its interaction with the shutdown sequence is an afterthought. The L3 container's security hardening (`no-new-privileges`, `cap_drop ALL`) makes tool availability in health checks non-obvious — `curl` and `python3` are present in the image but some tools invoke capabilities that are dropped.

**How to avoid:**
- Use a minimal, capability-free health check: `HEALTHCHECK CMD ["python3", "-c", "import os; os.path.exists('/workspace')"]` or a simple shell `test -f /workspace/.openclaw/*/workspace-state.json || exit 1`. Avoid `curl` entirely (requires network capabilities that may be restricted).
- The health check script must not touch the state file with write operations — read-only check only. The state file is protected by `fcntl.flock()` and a read-blocking health check would contend with the SIGTERM handler's write.
- Set `HEALTHCHECK --start-period=10s` to prevent the health check from firing during the entrypoint initialization phase (git checkout, state setup).
- Set `HEALTHCHECK --interval=15s` — L3 containers are ephemeral and short-lived (typically 5-60 minutes). A 15-second interval is sufficient and reduces health check overhead.
- Test the health check explicitly during a `docker stop` sequence: the container should show unhealthy for at most one health check interval during shutdown, then exit with code 143. This is acceptable behavior for ephemeral containers.
- Document that the health check is for observability only, not for Docker Compose `service_healthy` dependency chaining — L3 containers are not appropriate health-gate targets.

**Warning signs:**
- Health check always fails immediately after container start — the `--start-period` is too short and fires before git checkout completes
- `docker inspect` shows health status as `unhealthy` even when the container is running a task normally — the health check command is using a dropped capability
- `docker stop <l3-container>` causes health check to report unhealthy and a Compose restart loop fires (if the system has been placed under Compose `service_healthy` conditions)
- Health check script exits with error code 2 (invalid usage) — shell form vs exec form mismatch in HEALTHCHECK instruction

**Phase to address:** REL-09 (Docker health checks) — design the health check command to be capability-free and read-only before adding it to the Dockerfile. Explicitly test behavior during `docker stop` shutdown sequence.

---

### Pitfall 6: Cosine Threshold Calibration Uses Synthetic Data That Doesn't Reflect Real Embedding Distribution

**What goes wrong:**
QUAL-07 requires empirical calibration of the cosine similarity conflict detection threshold (currently 0.92 based on the v1.4 implementation note "threshold needs empirical tuning under real workload"). The calibration approach that fails: generate synthetic memory pairs with known ground truth (similar = conflict, dissimilar = distinct), run `_find_conflicts()` against them, and tune the `similarity_min`/`similarity_max` window.

Synthetic pairs generated as random vectors or manually crafted sentences do not reflect the real embedding distribution of OpenClaw memory entries. OpenClaw memories are short structured strings (`"L3 task completed: refactored payment module. 3 files changed."`) encoded by the embedding model used in memU. The actual cosine similarity distribution of real memories clusters around 0.75-0.92 for semantically distinct same-category entries (because they share structural patterns: "L3 task...", "L2 review...", category headers). Synthetic calibration against random vectors produces a threshold that is too high and misses real conflicts, or calibration against manually similar sentences produces a threshold that is too low and triggers false positives on structurally similar but semantically distinct real entries.

The second failure mode: the threshold is calibrated once on the current memory store and never re-evaluated. As more memories accumulate, the embedding distribution shifts (more entries cluster together as the system learns a narrower vocabulary of patterns). The threshold becomes miscalibrated without any warning signal.

**Why it happens:**
Developers calibrate on what is available and easy to generate — synthetic data. The actual embedding distribution of domain-specific short structured strings is not obvious without running the real embedding model over real data. This is the same problem as calibrating anomaly detection thresholds on laboratory data vs. production traffic.

**How to avoid:**
- Calibrate using real memory entries. Export at least 50 real memories from the production memU instance (or a staging replica), compute all pairwise cosine similarities, and plot the distribution. The conflict threshold should be set just above the natural cluster boundary for "same-type, different-task" entries.
- Implement threshold calibration as an operator tool, not a unit test: `openclaw-memory calibrate-thresholds --project <id>` that exports, computes, and recommends threshold values with a precision/recall tradeoff table.
- Add a monitoring counter: `health_scan_conflict_rate = conflicts_found / total_pairs`. If this rate exceeds 20% on any scan, log a WARNING that the threshold may be too loose. If it is 0% for 30 consecutive days, log an INFO suggesting the threshold may be too tight.
- The `similarity_min`/`similarity_max` window in `_find_conflicts()` already exists — use it correctly. Values below `similarity_min` are "definitely different", values above `similarity_max` are "definitely duplicates". The conflict window (between min and max) should be narrow (e.g., 0.75-0.92) not wide.
- Do not use the same threshold for all embedding models. If the embedding model is changed in a future memU upgrade, the calibration must be repeated.

**Warning signs:**
- First production health scan returns conflict rate > 25% — threshold is too loose and catching structurally similar but semantically distinct entries
- Health scan returns 0 conflicts despite the memory store containing known contradictory entries added during development — threshold is too tight
- After a memU embedding model upgrade, the conflict rate changes dramatically without any real change in memory content
- Calibration test suite passes but production scan behaves differently — test data (synthetic) does not match production embedding distribution

**Phase to address:** QUAL-07 (threshold calibration) — run the calibration tool against real memory entries from a staging or production memU export before setting the threshold. Do not rely on the test suite's synthetic data for production threshold selection.

---

### Pitfall 7: Constants Consolidation Introduces Import-Time Side Effects That Break Isolated Test Modules

**What goes wrong:**
CONF-05 consolidates all constants and defaults into one location (likely a new version of `config.py` or a new `defaults.py`). The current `config.py` is minimal and safe to import anywhere. The new consolidated constants module may import from `project_config.py` (to provide project-specific defaults) or from `state_engine.py` (to provide state-related defaults). This introduces import-time I/O — the `_find_project_root()` function is called, which reads `OPENCLAW_ROOT` from the environment or walks up the filesystem. In CI environments (or test modules that set up their own paths), this import-time filesystem access fails or returns the wrong root.

The pool.py module duplicates `_POOL_DEFAULTS` (present in both `project_config.py` and `pool.py`). Consolidation will remove one copy. If the remaining copy is imported at module level from the new constants module, and that import transitively triggers `openclaw.json` file reads, every test that imports `pool.py` or `project_config.py` will fail with `FileNotFoundError` unless the test environment includes a valid `openclaw.json`.

**Why it happens:**
Python's import system executes module-level code eagerly. Moving a constant from "literal value" to "computed from config file at import time" introduces I/O at import time — a subtle change that breaks the implicit contract that `import pool` does not touch the filesystem.

**How to avoid:**
- Keep the consolidated constants module free of I/O at import time. Constants that require config file reads must remain lazy (computed on first call, not at module import).
- The `_POOL_DEFAULTS` dict in `project_config.py` (line 20-26) is a safe literal — keep it as a literal dict, not a computed value. Reference it from `pool.py` via explicit import (`from openclaw.project_config import _POOL_CONFIG_DEFAULTS`) rather than duplicating.
- Test the consolidated constants module in isolation: `python3 -c "from openclaw.config import POLL_INTERVAL"` must succeed with no `OPENCLAW_ROOT` set and no `openclaw.json` present. If it fails, the import has I/O dependencies that need to be removed.
- Add a conftest fixture that sets `OPENCLAW_ROOT` to a temp directory with a minimal `openclaw.json` — this prevents real-config reads in tests. All existing tests that import orchestration modules should already use this pattern (check the existing `conftest.py`).

**Warning signs:**
- `pytest packages/orchestration/tests/` passes but `python3 -c "from openclaw.config import LOCK_TIMEOUT"` fails with `FileNotFoundError` in a fresh environment
- A test that previously passed in isolation now fails with `ConfigValidationError` because the new constants module reads `openclaw.json` at import time and the test environment lacks one
- Import order in tests starts to matter — tests pass when run in a specific order but fail when run individually

**Phase to address:** CONF-05 (constants consolidation) — define the import-time I/O boundary rule before consolidation: all constants in `config.py` must be computable with no filesystem access. Validate with an import smoke test in CI.

---

### Pitfall 8: Env Var Precedence Documentation Creates Contradictions With Existing Behavior

**What goes wrong:**
CONF-04 requires explicit, consistent env var precedence documentation. The existing precedence is:
- `OPENCLAW_ROOT` → project root path (in `_find_project_root()`)
- `OPENCLAW_PROJECT` → active project ID (in `get_active_project_id()`)
- `OPENCLAW_LOG_LEVEL` → logging level (in `config.py`)
- `OPENCLAW_ACTIVITY_LOG_MAX` → activity log rotation (in `config.py`)
- `OPENCLAW_STATE_FILE` → state file path override (in entrypoint.sh only — not in Python)

The `OPENCLAW_STATE_FILE` env var is referenced in `entrypoint.sh` (line 13) but has no corresponding support in the Python `get_state_path()` function. If the operator sets `OPENCLAW_STATE_FILE` expecting it to override the Python resolver, the Python side ignores it. The entrypoint uses it but the Python state engine resolves a different path. Documentation that lists `OPENCLAW_STATE_FILE` as a supported override will mislead operators into believing the Python components respect it.

When CONF-01 consolidates the path resolver, if `OPENCLAW_STATE_FILE` is promoted to a Python-level override for consistency with the entrypoint, it creates a second path for "which state file am I writing to?" that conflicts with the project-scoped path computed from `OPENCLAW_ROOT` + `project_id`. Two components could write to different state files simultaneously.

**Why it happens:**
The entrypoint.sh was written independently from the Python project_config.py. The `OPENCLAW_STATE_FILE` variable was added to the entrypoint for container-side flexibility without a corresponding Python implementation. Documentation efforts surface this inconsistency for the first time.

**How to avoid:**
- Before documenting env var precedence, audit every place an env var is read: `grep -r "os.environ.get\|os.getenv\|os.environ\[" packages/ skills/ docker/`. Cross-reference with entrypoint.sh and the docker volume/env injection in `spawn.py`.
- Decide explicitly: is `OPENCLAW_STATE_FILE` a supported override or a container-internal implementation detail? If the former, implement it in `get_state_path()` with the documented precedence. If the latter, rename it to a less user-facing name (e.g., `_OPENCLAW_INTERNAL_STATE_FILE`) and note it is not a public API.
- The documented precedence table must list every env var with: (a) which components read it, (b) what it overrides, (c) whether it is a public API or internal.
- Never add a new env var to the Python config layer without also checking whether the entrypoint.sh or skills need a corresponding update.

**Warning signs:**
- An operator sets `OPENCLAW_STATE_FILE` based on the documentation but the Python pool reads a different state file — tasks dispatched via `spawn_task()` never appear in the operator's custom state file
- Two different env var values for the same concept coexist: `OPENCLAW_ROOT=/custom/path` and `OPENCLAW_STATE_FILE=/different/path/state.json` — the system uses one for Python and the other for bash, writing two divergent state files
- After deploying CONF-04, an existing deployment that relied on undocumented env var behavior breaks because the documented precedence differs from the old implicit behavior

**Phase to address:** CONF-04 (env var precedence) — audit all env var reads across all languages and components before writing documentation. Resolve the `OPENCLAW_STATE_FILE` inconsistency explicitly in the same phase as CONF-01.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip migration CLI — just document the new canonical path and let operators move files manually | Saves development time | Every deployment breaks silently if the operator misses a project directory; state cursors lost; recovery scan misses orphans | Never — migration must be automated |
| Set adaptive polling cap at 10s to save CPU | Reduces monitor CPU by ~50% vs 1s polling | Tasks appear "started" up to 10s late in dashboard; monitoring tool feels broken for operators | Never for dashboard SSE — acceptable for CLI-only monitor if documented |
| Use the same cosine threshold for conflict detection and duplicate detection | One threshold to configure | Conflict window (0.75-0.92) is different from duplicate window (>0.95) — same threshold causes either false positives on conflicts or misses exact duplicates | Never — use separate `similarity_min` and `similarity_max` (already supported in `_find_conflicts()`) |
| Skip `fcntl.LOCK_SH` in migration CLI — "migration runs when system is idle" | Simpler migration code | If run during active spawns (operator error), state file corruption is possible and silent | Never — add the lock acquisition and document it as defense-in-depth |
| Health check script reads `workspace-state.json` to verify task is running | Meaningful liveness check | Blocks on `fcntl.LOCK_EX` held by `update_task()` during writes — health check hangs and Docker marks container unhealthy during active writes | Never — health check must be read-only and lock-free |
| Calibrate cosine threshold in unit tests using random vectors | Tests run without memU dependency | Threshold tuned to synthetic distribution fails on real embedding distribution | Never for production threshold — acceptable for regression testing that the threshold change doesn't break the algorithm |

---

## Integration Gotchas

Common mistakes when connecting the new v1.5 features to the existing system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| New path resolver → JarvisState | Passing the new canonical path to `JarvisState.__init__()` when an existing `JarvisState` instance may still hold the old path in a running pool | Ensure pool reinitializes its `JarvisState` instance when the path resolver changes; never cache `JarvisState` across config reloads in a long-running process |
| Migration CLI → fcntl state files | Using `shutil.copy2()` without acquiring `fcntl.LOCK_SH` first | Acquire `fcntl.LOCK_SH` on source before read; verify destination JSON is valid before declaring success |
| Adaptive polling → dashboard SSE | Dashboard SSE endpoint polls state at its own interval — adding adaptive polling to the CLI monitor does not affect dashboard SSE latency | Dashboard SSE polling and CLI monitor polling are independent code paths; OBS-05 must address both or document the scope explicitly |
| Docker HEALTHCHECK → entrypoint SIGTERM handler | Health check fires during the SIGTERM drain window (1-3s) and reports unhealthy — if any restart policy is applied, Docker restarts the container mid-shutdown | Use `--restart=no` for all L3 containers (already the case); document that health check unhealthy status during shutdown is expected and non-actionable |
| Strict validation (CONF-06) → pool recovery scan | `load_and_validate_openclaw_config()` is called before pool recovery; a schema warning aborts the process before orphans are cleaned up | Recovery scan must run before strict validation of spawn-time config; use two validation passes: minimal (parse-only) before recovery, full after |
| Threshold calibration → test suite | `test_health_scan.py` uses synthetic embeddings; after calibration, the production threshold differs from the test threshold | Test suite must use the same `similarity_min`/`similarity_max` values as production — inject threshold from config rather than hardcoding in tests |
| CONF-05 constants consolidation → `pool.py` import | `pool.py` imports `_POOL_DEFAULTS` from two places (its own module-level dict AND `project_config._POOL_CONFIG_DEFAULTS`) — after consolidation, one import path is removed without updating the other | Search all import sites for `_POOL_DEFAULTS` and `_POOL_CONFIG_DEFAULTS` before removing either; verify with `grep -r "_POOL" packages/ skills/` |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Adaptive polling thrashes on activity log rotation writes | Monitor CPU stays at 100%; mtime changes from log rotation trigger fast-poll mode indefinitely | Use task-status-map diff as activity signal, not mtime change | Immediately — activity log rotation happens on every task update (ACTIVITY_LOG_MAX_ENTRIES = 100), which means constant mtime churn |
| Health check script makes Python import per check | Each health check invocation takes 200ms+ (Python startup time); 15-second interval means 1.3% of container lifetime spent on health checks | Use a minimal shell one-liner (`test -d /workspace`) rather than invoking Python; reserve Python health checks for functional probes | Any L3 container with `--interval < 30s` |
| Cosine similarity scan over full memory store on every health check run | `_find_conflicts()` is O(n*k) — at 1000 memories with k=10, 10K comparisons per scan. If health scan runs on every dashboard load, PostgreSQL CPU spikes | Cache health scan results for minimum 1 hour; run as background job, not on-demand per-request | When memory store exceeds ~500 entries and health scan is triggered by UI refresh |
| Migration CLI reads all project state files sequentially | Migration takes 30+ seconds for 9 registered projects if state files are large | Migration CLI can process projects in parallel (each state file is independently locked); use `concurrent.futures.ThreadPoolExecutor` | At 9 projects (current scale), sequential is acceptable; document the optimization for when project count grows |

---

## Security Mistakes

Domain-specific security issues for v1.5 features.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Migration CLI does not verify destination path before writing | Path traversal: a malformed `project_id` in `projects/<id>/project.json` could cause the migration to write state files outside the `workspace/.openclaw/` directory | Validate that the computed destination path starts with the canonical `OPENCLAW_ROOT/workspace/.openclaw/` prefix before any write |
| Env var documentation exposes `OPENCLAW_GATEWAY_TOKEN` semantics | Documentation of env var precedence may inadvertently document how to bypass the gateway auth token | Document only the `OPENCLAW_*` vars relevant to path resolution and logging; do not document security-sensitive vars in the same location as operational vars |
| HEALTHCHECK script is world-writable after `COPY` | An L3 task that gains write access to the container filesystem can modify the health check script to always return healthy, masking real failures | `COPY entrypoint.sh` already uses `chmod +x` without `chmod o+w`; verify the health check script follows the same pattern: `COPY healthcheck.sh /healthcheck.sh && chmod 500 /healthcheck.sh` (readable and executable only by owner) |
| Adaptive polling state comparison leaks task descriptions via log output | If the activity detection logic logs the "changed task" object for debugging, task descriptions containing sensitive data appear in monitor logs | Log only `task_id` and `status` fields in the activity detection log entry, never the full task description |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Path resolver consolidation (CONF-01):** `get_state_path()` returns a path that contains the live `workspace-state.json` — verify by `ls -la $(python3 -c "from openclaw.project_config import get_state_path; print(get_state_path())")` on a project that has been running
- [ ] **Migration CLI (CONF-03):** Migration CLI acquires `fcntl.LOCK_SH` before reading source state files — verify by running `strace -e flock python3 migration_cli.py --dry-run` and confirming `flock()` syscalls appear
- [ ] **Migration CLI (CONF-03):** Old path state files are moved (not just copied) or explicitly archived — verify that no state files remain at the old path after migration completes
- [ ] **Strict validation (CONF-06):** Recovery scan runs even when `openclaw.json` has a schema advisory warning — verify by temporarily adding an unknown field to `openclaw.json` and confirming pool startup proceeds to recovery scan before rejecting new spawns
- [ ] **Adaptive polling (OBS-05):** Activity detection uses task-status-map diff, not mtime — verify by checking that an activity log rotation write (updating only `activity_log` in state.json, not any task status) does NOT trigger fast-poll mode
- [ ] **Docker HEALTHCHECK (REL-09):** Health check does not block on `fcntl` lock — verify by running `docker stop` on an active L3 container and confirming health check does not show lock contention errors in container logs
- [ ] **Docker HEALTHCHECK (REL-09):** Health check works as UID 1000 with `cap_drop ALL` — verify by running `docker exec --user 1000 <container> /healthcheck.sh` with capabilities dropped
- [ ] **Threshold calibration (QUAL-07):** Calibration was run against real memory entries (not synthetic) — verify by checking that the calibration report references a non-zero sample size from a real memU export
- [ ] **Constants consolidation (CONF-05):** `python3 -c "from openclaw.config import LOCK_TIMEOUT"` succeeds with no `OPENCLAW_ROOT` set and no `openclaw.json` present — no import-time I/O
- [ ] **Env var precedence (CONF-04):** `OPENCLAW_STATE_FILE` disposition is explicitly decided — either Python respects it (with updated `get_state_path()`) or it is documented as container-internal only

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Path resolver change discarded existing state files | MEDIUM | Locate state files at old path (`find ~/.openclaw -name "workspace-state.json"`); copy to new canonical paths manually; verify JSON is valid; re-run pool startup |
| Migration CLI ran during active spawns, produced truncated state file | LOW | State engine's `.bak` recovery kicks in automatically; verify `workspace-state.json.bak` at the old path contains the pre-migration valid state; copy `.bak` to new canonical path |
| Strict validation blocked recovery scan, orphaned tasks piled up | LOW | Run `openclaw pool --recover-only` (if the flag exists) or manually update task statuses: `python3 -c "from openclaw.state_engine import JarvisState; ..."` to set `in_progress` tasks to `interrupted` |
| Adaptive polling thrashed on log rotation — monitor process at 100% CPU | LOW | Restart monitor with `--interval 5` override flag to force a fixed interval; then fix the activity detection logic; restart again |
| HEALTHCHECK reported unhealthy during normal operation | LOW | `docker inspect <container>` to see health check output; fix the health check command (capability or permission issue); rebuild L3 image with `make docker-l3`; no data loss |
| Cosine threshold miscalibrated — false positive deluge | MEDIUM | Increase `similarity_min` to reduce false positives (push lower bound up); re-run health scan to verify conflict rate drops below 10%; archive falsely flagged entries instead of deleting them |
| `OPENCLAW_STATE_FILE` env var set by operator, Python ignores it — state divergence | MEDIUM | Identify which state file was actually written by Python (`get_state_path()` call); merge state from operator's expected path into the canonical path manually; update documentation to clarify the env var is container-internal |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Path resolver breaks existing state files | CONF-03 (migration CLI) built before CONF-01 (resolver) | `get_state_path()` returns the same absolute path as before on all 9 registered projects |
| Migration CLI corrupts state during active spawns | CONF-03 — add `fcntl.LOCK_SH` acquisition + container pre-flight check | Run migration with a container active; destination state file is valid JSON matching source |
| Strict validation blocks recovery scan | CONF-06 — define two-pass startup sequence explicitly | Adding unknown field to `openclaw.json` does not prevent recovery scan from completing |
| Adaptive polling misses tasks or thrashes on log rotation | OBS-05 — define activity signal as status-map diff, not mtime | Activity log rotation write does not trigger fast-poll mode; spawned task detected within 5s during slow poll |
| HEALTHCHECK unhealthy during SIGTERM drain | REL-09 — capability-free, lock-free health check with `--start-period=10s` | `docker stop <l3>` exits with code 143; health check shows at most one unhealthy result during drain |
| Cosine threshold miscalibrated from synthetic data | QUAL-07 — calibrate against real memory export before committing threshold | Calibration report references real sample size; conflict rate on production scan is <15% |
| Constants consolidation introduces import-time I/O | CONF-05 — import smoke test in CI | `python3 -c "from openclaw.config import LOCK_TIMEOUT"` succeeds without `OPENCLAW_ROOT` or `openclaw.json` |
| Env var precedence documentation contradicts existing `OPENCLAW_STATE_FILE` behavior | CONF-04 — full env var audit before documentation | Every env var in documentation is verified to be read by the claimed components via `grep` audit |

---

## Sources

- Direct codebase inspection: `packages/orchestration/src/openclaw/config.py`, `project_config.py`, `config_validator.py`, `state_engine.py`, `cli/monitor.py`, `docker/memory/memory_service/scan_engine.py`, `skills/spawn/pool.py`, `docker/l3-specialist/Dockerfile`, `docker/l3-specialist/entrypoint.sh` — HIGH confidence
- Docker HEALTHCHECK signal interaction: [Sending a signal to a container with healthcheck affects healthcheck status — docker/for-linux issue #454](https://github.com/docker/for-linux/issues/454), [How to Handle Docker Container Graceful Shutdown and Signal Handling — OneUptime](https://oneuptime.com/blog/post/2026-01-16-docker-graceful-shutdown-signals/view), [Docker Health Check: A Practical Guide — Lumigo](https://lumigo.io/container-monitoring/docker-health-check-a-practical-guide/), [Docker Health Check Best Practices — OneUptime](https://oneuptime.com/blog/post/2026-01-30-docker-health-check-best-practices/view) — MEDIUM confidence
- Docker STOPSIGNAL and HEALTHCHECK sequencing: [Dockerfile STOPSIGNAL — Dockerpros](https://dockerpros.com/wiki/dockerfile-stopsignal/), [Health Checks in Docker Compose — Tom Vaidyan](https://www.tvaidyan.com/2025/02/13/health-checks-in-docker-compose-a-practical-guide/) — MEDIUM confidence
- Adaptive polling backoff patterns: [Polling in System Design — GeeksforGeeks](https://www.geeksforgeeks.org/system-design/polling-in-system-design/), [Efficient Kafka Polling in Python — Medium](https://medium.com/@sonal.sadafal/efficient-kafka-polling-in-python-handling-idle-states-gracefully-e6d880663581), [Exponential Backoff in Distributed Systems — Better Stack](https://betterstack.com/community/guides/monitoring/exponential-backoff/) — MEDIUM confidence (polling patterns well established; OpenClaw-specific activity detection logic from codebase analysis)
- Cosine similarity threshold calibration: [How to Use Cosine Similarity for Vector Search in pgvector — Sarah Glasmacher](https://www.sarahglasmacher.com/how-to-use-cosine-similarity-in-pgvector/), [pgvector GitHub](https://github.com/pgvector/pgvector), [Cosine Similarity Threshold — Emergent Mind](https://www.emergentmind.com/topics/cosine-similarity-threshold) — MEDIUM confidence; production distribution insight from codebase inspection of scan_engine.py and v1.4 calibration note in PROJECT.md
- Config migration schema evolution: [Schema Evolution in Real-Time Systems — Estuary](https://estuary.dev/blog/real-time-schema-evolution/), [Safe Django migrations without server errors — Loopwerk](https://www.loopwerk.io/articles/2025/safe-django-db-migrations/) — LOW confidence for specific Python config patterns; HIGH confidence from direct code analysis of `_find_project_root()` and path divergence documented in PROJECT.md

---
*Pitfalls research for: OpenClaw v1.5 Config Consolidation — path resolver migration, adaptive polling, Docker health checks, cosine threshold calibration*
*Researched: 2026-02-25*
