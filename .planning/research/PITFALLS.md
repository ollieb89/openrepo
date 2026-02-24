# Pitfalls Research

**Domain:** Adding Operational Maturity to an existing Docker-based AI swarm orchestration system (OpenClaw v1.4)
**Researched:** 2026-02-24
**Confidence:** HIGH — derived from direct codebase inspection of v1.3 implementation (state_engine.py, spawn.py, pool.py, snapshot.py, memory_client.py), targeted web research on Docker signal handling, pgvector production patterns, agentic AI security, and delta snapshot consistency

---

## Critical Pitfalls

### Pitfall 1: SIGTERM Never Reaches Python — Shell Form Entrypoint Absorbs the Signal

**What goes wrong:**
The L3 container `entrypoint.sh` is launched via the Docker `CMD` or `ENTRYPOINT` instruction. If these use **shell form** (e.g., `CMD entrypoint.sh`), Docker spawns `/bin/sh -c entrypoint.sh` as PID 1. The shell becomes PID 1 and receives SIGTERM. Bash does not automatically forward signals to child processes — it absorbs SIGTERM and either ignores it or handles it itself without propagating to the Python/Claude process running inside. The Claude Code subprocess running the agent task is never signalled. Docker times out after 10 seconds (the `docker stop` grace period) and sends SIGKILL, which tears down the container without any state dehydration.

The L2 pool manager (`pool.py`) also uses `asyncio.wait_for(loop.run_in_executor(None, container.wait), timeout=timeout_seconds)`. If the host process itself receives SIGTERM (e.g., when OpenClaw is restarted), the asyncio event loop does not automatically cancel in-flight `run_in_executor` threads because Python's default SIGTERM handling does not inject a CancellationError into the event loop. In-flight pool slots appear to still hold tasks, but the state file never gets updated to a clean terminal status.

**Why it happens:**
Docker's shell form is the path of least resistance and is used in most tutorials. The distinction between shell form (`CMD script.sh`) and exec form (`CMD ["script.sh"]`) is easily overlooked. Python signal handlers (`signal.signal(SIGTERM, handler)`) only work if the Python process is PID 1 or receives the forwarded signal — neither is guaranteed when wrapped in a shell. Developers test shutdown manually (`Ctrl+C` → SIGINT), which Python handles differently than SIGTERM, masking the problem.

**How to avoid:**
- Use **exec form** in the L3 Dockerfile: `ENTRYPOINT ["bash", "/entrypoint.sh"]` rather than `ENTRYPOINT /entrypoint.sh`. This makes bash PID 1 directly.
- Inside `entrypoint.sh`, use `exec python3 ...` (or `exec claude-code ...`) for the final command. `exec` replaces the shell process with the child, making the Python/Claude process PID 1 and receiving signals directly.
- Add a SIGTERM handler to the L2 Python pool manager using `loop.add_signal_handler(signal.SIGTERM, shutdown_callback)` — this is the asyncio-safe way to register signal handlers (not `signal.signal()`, which is not safe in async loops).
- Verify signal delivery by testing with `docker stop <container>` and checking exit code — graceful shutdown produces exit code 0 or 143, SIGKILL produces exit code 137.

**Warning signs:**
- `docker stop <container>` takes exactly 10 seconds (the default grace period) before the container dies — this means SIGTERM was never processed and Docker fell back to SIGKILL
- Exit code 137 in container exit records (137 = 128 + 9 = SIGKILL)
- State file (`workspace-state.json`) shows tasks stuck in `in_progress` after a container is force-stopped
- No log entries from the SIGTERM handler code path appearing in structured logs during shutdown

**Phase to address:** SIGTERM/Graceful Shutdown phase — the exec form change must be made in the Dockerfile and entrypoint before any state dehydration logic is built, or the dehydration code will never be reached

---

### Pitfall 2: State Dehydration Inside a SIGTERM Handler Deadlocks on the fcntl Lock

**What goes wrong:**
The graceful shutdown plan requires the L3 container to write its current task state (dehydrate) to `workspace-state.json` when it receives SIGTERM. The `JarvisState.update_task()` method acquires `LOCK_EX` via `fcntl.flock()`. If the L3 container was in the middle of an `update_task()` call when SIGTERM arrived (e.g., writing a progress update), the lock is already held by the same process. A re-entrant call to `update_task()` from the signal handler attempts to acquire `LOCK_EX` on the same file descriptor held by the outer call — on Linux, `fcntl.flock()` is NOT re-entrant for the same process/thread. The result is a deadlock: the signal handler waits for a lock held by itself, the outer call never completes because the signal handler is blocking, and Docker's grace period expires with SIGKILL.

Additionally, `fcntl.flock()` in Python uses blocking I/O. Python signal handlers (registered via `signal.signal()`) are called between bytecode instructions but cannot interrupt a blocking I/O syscall already in progress. If the process is blocked on `flock()` waiting for another process's lock when SIGTERM arrives, the signal is deferred until the flock call returns — which may never happen if the lock holder also received SIGTERM and is itself deadlocked.

**Why it happens:**
Signal handler re-entrancy is a non-obvious constraint. The `JarvisState` class was designed for sequential use (call update_task, call read_state, etc.) and has no re-entrancy guard. Developers writing SIGTERM handlers typically call the same state update functions used in normal execution, without realising that the signal may interrupt an in-progress state write.

**How to avoid:**
- Use a **flag + main-loop check pattern** instead of performing I/O directly in the signal handler: the signal handler sets a module-level `_shutdown_requested = True` flag only. The main execution loop checks this flag at safe checkpoints (between LLM calls, after file writes) and performs dehydration at those points.
- Alternative for asyncio: use `loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(graceful_shutdown()))` — this schedules the shutdown coroutine in the event loop rather than running it synchronously in the signal handler context, avoiding re-entrancy.
- Add a `is_shutdown_requested()` check at the top of `update_task()` — if shutdown is in progress, skip the write and log a warning rather than blocking.
- Design the dehydration payload to be written to a **separate file** (`soul-<task_id>.shutdown.json`) that does NOT require the main state lock, avoiding any lock contention during shutdown.

**Warning signs:**
- Container hangs for exactly the Docker grace period (10s) after SIGTERM and then exits via SIGKILL
- Structured logs show the SIGTERM handler was entered but no subsequent log entries appear (deadlock)
- `workspace-state.json` is truncated or zero-length after a forced shutdown (interrupted mid-write)
- `ps aux` inside a hung container shows the Python process in `D` state (uninterruptible sleep on a syscall)

**Phase to address:** SIGTERM/Graceful Shutdown phase — design the dehydration-safe state write before implementing the signal handler; never call `update_task()` directly from signal handler context

---

### Pitfall 3: Recovery Loop Re-Spawns a Task Whose State Is Irrecoverably Stale

**What goes wrong:**
The automated recovery loop reads `workspace-state.json` to find tasks in `in_progress` state after a restart and re-queues them. However, `in_progress` in the state file does not distinguish between three very different situations:
1. **Container was mid-task, made no git commits** — safe to re-spawn from scratch
2. **Container committed partial work to the staging branch** — re-spawning creates a second set of commits on `l3/task-{task_id}`, which may conflict with or duplicate the first set
3. **Container completed the task but died before marking it `completed`** — re-spawning wastes a full L3 slot re-doing completed work, and the second run's git diff will conflict with the first run's commits

The recovery loop cannot distinguish these three cases by reading state.json alone — all three look identical: `status: "in_progress"`, no `completed_at` timestamp.

**Why it happens:**
State file design in v1.0-v1.3 uses status as a simple enum. The `in_progress` state was sufficient when tasks were ephemeral and non-recoverable. Adding recovery without adding more state transitions creates an ambiguity that the recovery loop cannot resolve safely.

**How to avoid:**
- Add a `recovery_safe` boolean field to task state, defaulted to `false` and set to `true` only during SIGTERM dehydration when the container confirms no git commits have been made to the staging branch yet. Recovery loop only re-spawns tasks where `recovery_safe: true`.
- Before re-spawning, check whether the staging branch `l3/task-{task_id}` exists in git. If it does, it contains partial or complete work — do not blindly re-spawn; require human decision (mark as `needs_review` in state).
- Add a `dehydrated_at` timestamp field. Tasks without this field were killed mid-execution (SIGKILL path), not gracefully dehydrated — treat differently from tasks with a clean dehydration record.
- Set a maximum re-spawn count per task (default 1). After one recovery re-spawn, if the task fails again, mark it `failed_unrecoverable` and alert.

**Warning signs:**
- Staging branch `l3/task-T001` exists with commits AND state shows `in_progress` — recovery loop is about to re-spawn a task that has already done work
- A task appears twice in the git log (duplicate commit messages differing only by `(retry)` suffix)
- `merge_staging` fails with a conflict on a task that "should have been clean" — caused by two runs committing different implementations of the same file

**Phase to address:** Task Recovery (sub-phase within Graceful Shutdown) — define the recovery eligibility rules and state transitions before implementing the recovery loop; a loop without eligibility checks is more dangerous than no recovery at all

---

### Pitfall 4: Memory Health Monitor Triggers False Positives on Semantically Valid Duplicates

**What goes wrong:**
The memory health monitor must detect "stale" and "conflicting" memories. The naive implementation computes cosine similarity between all pairs of memory embeddings and flags pairs above a threshold (e.g., 0.95) as duplicates or conflicts. However, OpenClaw's memory store contains many legitimately similar entries: multiple L3 task outcomes for the same type of task (e.g., "refactored Python module to use dataclasses") have very similar embeddings but are not stale — they are distinct historical events. Flagging them as conflicts causes the operator to delete valid memory and degrades the agent's ability to pattern-match on recurring task types.

The opposite problem also exists: a memory entry that is genuinely stale ("never use asyncio.run() inside pool.py") may have a moderate similarity score to a newer contradicting entry ("asyncio.run() is now used in the CLI entrypoint for standalone spawning") but because they are about different contexts, the conflict detector does not flag them.

**Why it happens:**
Vector similarity is a proxy for semantic relatedness, not semantic contradiction. High similarity means the content is about the same topic — not that one entry is wrong and one is right. Contradiction detection requires semantic reasoning (i.e., an LLM comparing the two entries), not just embedding distance. Developers building health monitors rely on embedding distance because it is cheap and scalable, but the signal quality is wrong for the conflict detection use case.

**How to avoid:**
- Do NOT use cosine similarity alone for conflict detection. Use it only as a **pre-filter** to find candidate pairs, then use an LLM (via a quick structured prompt) to assess whether the candidates actually conflict.
- Define "stale" operationally, not semantically: a memory entry is stale if it has not appeared in the top-10 retrieve results for any task in the past N days (configurable, default 30). This recency-based staleness metric avoids the similarity problem entirely.
- Define "conflicting" as: two entries in the same category (`review_decision`, `task_outcome`) for the same task_id with different verdicts/outcomes. This is a simple structural check that does not require vector comparison.
- Expose the "flag for review" action, not "auto-delete". The health monitor should surface candidates for human review in the dashboard `/memory` page — not autonomously delete or modify entries.

**Warning signs:**
- Memory health monitor reports 40%+ of the memory store as "conflicting" on first run — this is almost certainly false positives from similarity threshold that is too low
- After health monitor runs, agent task success rate drops (deleted valid context entries)
- Operator reports "the monitor keeps flagging the same entries every run" — health monitor is not recording which entries have been reviewed and dismissed

**Phase to address:** Memory Health Monitoring phase — define staleness and conflict detection metrics before writing the detector; validate the detector against synthetic ground-truth data (known good/bad pairs) before running against the production memory store

---

### Pitfall 5: L1 Strategic Suggestions Modify SOUL Templates at Runtime — Prompt Injection Attack Surface

**What goes wrong:**
The L1 suggestion engine reads recurring task failure/success patterns from memU and generates SOUL template modifications to improve L3 agent behavior. If these suggestions are written directly to `agents/l3_specialist/agent/SOUL.md` (or a project's `soul-override.md`) without human review, an adversarial memory entry can cause L1 to suggest a SOUL modification that changes agent behavior in unintended ways.

Concrete threat: a prompt injection payload stored in a memory entry (e.g., via a malicious task description processed by L3) surfaces during L1's pattern analysis. L1 interprets it as a legitimate behavioral pattern and suggests adding a SOUL instruction such as "always commit changes to main branch directly without creating a staging branch". If auto-applied, this breaks the L2 review workflow — permanently and silently.

This is not a theoretical concern: Palo Alto Unit 42 research documents exactly this class of attack against agent memory systems, and a security research paper specifically targeting OpenClaw-style SOUL.md persistence was published in 2025.

**Why it happens:**
The L1 suggestion pipeline reads from memU (which contains content generated by AI agents and external task descriptions), processes it through an LLM, and produces output that modifies files that govern other agents' behavior. This is an indirect prompt injection path: untrusted content (task descriptions, L3 outputs) → memU storage → L1 retrieval → L1 LLM processing → SOUL file modification. Each step appears legitimate in isolation; the end-to-end injection path is only visible when viewing the full pipeline.

**How to avoid:**
- **Mandatory human approval gate**: L1 suggestions must NEVER be auto-applied. All suggestions are written to a `suggestions/` directory (e.g., `workspace/.openclaw/<project_id>/soul-suggestions/`) and displayed in the dashboard for human review. The operator explicitly approves each suggestion before it is applied.
- **Diff-based review**: present the suggestion as a git-style diff against the current SOUL file, not as free-form text. This makes the exact proposed change visible and auditable.
- **Structural validation**: before offering a suggestion for review, validate it against a SOUL schema. A valid suggestion must: (a) not remove existing safety constraints, (b) not add instructions that reference file paths or shell commands, (c) not exceed a maximum diff size (100 lines). Reject suggestions failing validation without presenting them to the operator.
- **Read-only SOUL during normal operation**: `SOUL.md` files should be writable only by the explicit "apply suggestion" code path, not by any agent-triggered code path. L3 containers mount SOUL as read-only (`"mode": "ro"` — already the case in v1.3 spawn.py).
- **Sanitize memory before L1 analysis**: when L1 retrieves memories for pattern analysis, strip any content that contains markdown headings (`#`), code fences (`` ` ``), or template variable patterns (`$`, `{{}}`), which are injection vectors.

**Warning signs:**
- A SOUL suggestion contains the phrase "always", "never", or "override" — these are high-risk behavioral absolutes that warrant extra scrutiny
- A suggestion proposes adding a new `$variable` placeholder — this could be an attempt to inject dynamic content at render time
- After applying a suggestion, agent task success rate drops or L2 rejection rate increases significantly
- A SOUL suggestion references a specific task ID or project name — legitimate behavioral patterns are general, not task-specific

**Phase to address:** L1 Strategic Suggestions phase — the human approval gate must be the first thing built; do not implement the suggestion generation pipeline until the approval + validation workflow is in place, or the feature is unsafe to test

---

### Pitfall 6: Delta Snapshot Reads Against a File Currently Being Written — Torn Snapshot

**What goes wrong:**
The delta snapshot system computes the diff between the staging branch and the default branch (`git diff main...HEAD`). The current `capture_semantic_snapshot()` runs a `subprocess.run(['git', 'diff', ...])` call. If an L3 container is still actively writing to the workspace while the snapshot is captured (e.g., finishing a file write between two git operations), the snapshot captures an inconsistent state: some files include the container's partial changes, others do not. The resulting diff is not a coherent semantic unit.

More specifically, the delta snapshot design for v1.4 tracks changes since the last snapshot (not since `main`). If the previous snapshot's hash is used as the base (`git diff <prev-snapshot-sha>...HEAD`), and a concurrent write happens between reading `<prev-snapshot-sha>` from the last snapshot file and executing the diff, the base may not reflect the true previous state, producing a delta that appears to contain changes that were already in the previous snapshot.

**Why it happens:**
`subprocess.run` calls to `git` are not transactional. The delta snapshot adds a new state dimension (tracking previous snapshot SHA) that the current single-snapshot-per-task design does not have. Developers implementing delta snapshots naturally reuse the existing `capture_semantic_snapshot()` function, adding only the base SHA parameter, without considering concurrent writes or the atomicity requirements of the diff operation.

**How to avoid:**
- Take the diff **after** the L3 container has exited (in `_attempt_task` after `container.wait()` returns), not while it is running. At this point, there are no concurrent writes — the container is stopped. The current v1.3 design already does this; ensure the delta snapshot design preserves this constraint.
- Store the previous snapshot's git commit SHA (not a file path or mtime) as the delta base. Git commit SHAs are immutable — there is no TOCTOU race between reading the SHA and using it for a diff.
- Use `git diff --stat <base-sha>..<head-sha>` with explicit immutable SHAs rather than relative refs like `HEAD~1`, which can change meaning between the stat call and the diff call.
- Acquire the `fcntl.LOCK_SH` on the state file before reading the previous snapshot SHA, and release it only after the diff command completes. This prevents a concurrent `update_task()` write from changing the state file mid-diff.

**Warning signs:**
- Two consecutive delta snapshots for the same task show overlapping changes (the same file modification appears in both the N and N+1 delta)
- A delta snapshot shows zero changes but the git staging branch has new commits — the diff base SHA is pointing at the wrong commit
- Snapshot files on disk are larger than full snapshots (delta is larger than the full diff from `main`) — this indicates the base SHA is too far back

**Phase to address:** Delta Snapshot phase — design the delta base tracking strategy (commit SHA, not mtime) before implementing the capture function; validate that delta N+1 = full snapshot N+1 - full snapshot N for a known test sequence before wiring into the pool

---

### Pitfall 7: asyncio.create_task() for Fire-and-Forget Memorization Is Lost on Event Loop Shutdown

**What goes wrong:**
`pool.py` uses `asyncio.create_task(self._memorize_snapshot_fire_and_forget(...))` to memorize task outcomes without blocking the pool slot release. This pattern works correctly during normal operation. However, when the pool is shutting down (e.g., receiving SIGTERM), the asyncio event loop may be cancelled before all fire-and-forget tasks complete. `asyncio.create_task()` tasks that are still pending when the event loop is cancelled are aborted — their coroutines receive `CancelledError` and halt mid-execution. The memorization call is silently lost with no record in state.json (because the memorize failure path only logs a warning, not updating state).

After a SIGTERM shutdown, the memory store is missing the outcomes of any tasks that completed in the final seconds before shutdown. The recovery loop does not know these tasks were completed — it re-spawns them (if they were flagged as `in_progress`), and they run again unnecessarily.

**Why it happens:**
`asyncio.create_task()` is designed for concurrent execution within a running event loop, not for deferred execution across event loop lifecycle boundaries. The pattern is correct for the "slot released immediately, memorize in background" use case but breaks at event loop termination. Standard asyncio shutdown documentation (`loop.run_until_complete()`, `asyncio.run()`) cancels all pending tasks, which is the desired behavior for most cleanup scenarios — but not for fire-and-forget work that must complete before process exit.

**How to avoid:**
- Track all fire-and-forget tasks in a module-level set: `_pending_memorize_tasks: set[asyncio.Task] = set()`. In the graceful shutdown handler, `await asyncio.gather(*_pending_memorize_tasks, return_exceptions=True)` with a timeout (5 seconds). This ensures pending memorizations complete if time permits before the event loop is cancelled.
- Use `task.add_done_callback(_pending_memorize_tasks.discard)` to automatically remove completed tasks from the tracking set, preventing unbounded growth.
- As a fallback, write a `pending_memorize: true` field to the state file when creating the fire-and-forget task, and clear it when the task completes. On startup, the memory system can re-try any entries with `pending_memorize: true` (though at v1.4 scale this is a MEDIUM priority, not critical).
- Set the shutdown SIGTERM grace period in Docker (`--stop-timeout`) to at least 15 seconds to allow pending memorization tasks to complete before SIGKILL.

**Warning signs:**
- After a graceful shutdown and restart, `list_active_tasks()` returns tasks that were definitely completed in the last run (because the task was running, pool completed it, but memorize task was cancelled before the fire-and-forget finished and the state update from within `_memorize_snapshot_fire_and_forget` was never persisted — note: in the current code, state IS updated in `_attempt_task` before the fire-and-forget, so this is about memory data loss rather than state data loss — clarify which risk is primary)
- Memory store shows gaps in coverage around restart events (tasks completed shortly before shutdown have no memory entries)
- Structured logs show `asyncio.CancelledError` on memorize tasks during shutdown

**Phase to address:** SIGTERM/Graceful Shutdown phase — implement the pending-task tracking set at the same time as the shutdown handler; these must be built together or the fire-and-forget guarantees are weakened during the exact scenario where they matter most

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Auto-apply L1 SOUL suggestions without human review | No approval bottleneck; fully autonomous | Prompt injection path: malicious memory → L1 analysis → SOUL modification → changed agent behavior. One bad suggestion can corrupt all future tasks | Never — human approval gate is non-negotiable for SOUL modifications |
| Re-spawn any `in_progress` task on recovery | Simple recovery loop, no state analysis required | Re-spawns tasks that already have partial git commits, causing conflicts and duplicated work | Never without checking staging branch existence and `recovery_safe` flag first |
| Implement SIGTERM handler using `signal.signal()` in an asyncio event loop | Familiar API, works in synchronous Python | Not asyncio-safe: signal handler runs in the main thread and can interrupt the event loop mid-operation, causing data races; use `loop.add_signal_handler()` instead | Never in asyncio contexts |
| Delta snapshot base = previous snapshot file mtime | No need to store SHA; mtime is automatically available | mtime changes on file system metadata updates that do not change content; delta base becomes incorrect on `touch` or rsync operations | Never — always use git commit SHA as delta base |
| Health monitor auto-deletes flagged memories | Reduces manual operator burden | Deletes valid memories that are semantically similar but historically distinct; degrades agent pattern-matching capability | Never — always flag for review, never auto-delete |
| Skip SIGTERM handling in the L3 container entrypoint | Simpler entrypoint code | Any `docker stop` during an L3 task causes SIGKILL, which leaves the state file in `in_progress` forever and the staging branch in a partial state | Never — the entrypoint must handle SIGTERM for the recovery system to work |

---

## Integration Gotchas

Common mistakes when connecting the new v1.4 features to existing subsystems.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SIGTERM handler → JarvisState.update_task() | Calling update_task() directly from signal handler — re-entrancy deadlock if a write is already in progress | Set a flag in the handler; check the flag at safe checkpoints in the execution loop; schedule dehydration as an asyncio task via loop.add_signal_handler() |
| Memory health monitor → pgvector | Running `SELECT` with cosine similarity `<->` over the full memory table at high frequency (e.g., every 5 minutes) | Cache the last health check result for 1 hour minimum; run health checks as a low-priority background job, not on every API request; use the recency-based staleness metric instead of pairwise similarity |
| L1 suggestion engine → memU retrieve | Retrieving all memories without a project scope for pattern analysis | Always scope to project_id; L1 analyzes patterns per-project, not globally (cross-project contamination risk) |
| Delta snapshot → state engine read (previous SHA) | Reading previous snapshot SHA from a cached JarvisState instance that may be stale | Read state fresh (with LOCK_SH) immediately before the git diff command; do not use write-through cache values for delta base decisions |
| Recovery loop → pool.py semaphore | Re-spawning recovered tasks without checking if the pool semaphore was properly released on shutdown | On startup, reset the semaphore to its configured max value — do not carry over the pre-shutdown semaphore state, which is only valid for the previous event loop instance |
| L1 suggestion dashboard → file write | Next.js API route writing directly to agents/l3_specialist/agent/SOUL.md | Route all SOUL writes through a dedicated Python API endpoint that validates the diff, logs the change, and requires an explicit confirmation token |
| Health monitor → memory delete action | Calling DELETE /memory/{id} from the monitor without checking if the memory is referenced by any pending task | Soft-delete pattern: mark entry with `deleted: true` in metadata but preserve the record; hard-delete only after 7-day retention window |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Memory health check with O(N²) pairwise similarity scan | Dashboard `/memory` health tab takes 30+ seconds to load; PostgreSQL CPU spikes to 100% | Use approximate nearest-neighbor search (HNSW index) with limit=10 for candidate finding, not full table scan; cache results for 1 hour | When memory store exceeds ~500 entries (pairwise scan hits 250K comparisons) |
| Delta snapshot accumulating unbounded chain of deltas | Snapshot diff files grow nonlinearly; diff computation time increases with chain length | Periodic "rebase" to full snapshot when chain length exceeds 10; store SHAs for only the last 10 deltas | When a single task accumulates more than ~10 delta snapshots |
| L1 pattern analysis running on every task completion | memU retrieve spikes after every L3 completion; L1 LLM calls queue up | Batch L1 analysis: run once per 24 hours or when triggered manually, not per-task | First concurrent run of 3 L3 tasks completing simultaneously (3x L1 LLM calls in parallel) |
| SIGTERM grace period too short for state dehydration | Docker kills containers mid-dehydration, leaving state file truncated | Set `--stop-timeout 30` in Docker run config; state dehydration must complete within this window | Any task with a large activity log that takes >10s to serialize and write under lock |
| Recovery loop running before state file is fully consistent | Recovery loop starts, reads stale in_progress tasks, re-spawns prematurely | Add a startup delay (5s) or a "state file version check" before the recovery loop runs | Any restart scenario where the state file was being written when the process was killed |

---

## Security Mistakes

Domain-specific security issues for v1.4 features.

| Mistake | Risk | Prevention |
|---------|------|------------|
| L1 auto-applies SOUL suggestions without human review | Prompt injection via memory: malicious task output → stored as memory → surfaced to L1 → SOUL modification that changes agent safety constraints | Mandatory human approval gate; SOUL files are write-protected at OS level during normal operation |
| SOUL suggestion diff displayed in dashboard without escaping | Stored XSS: a SOUL suggestion containing `<script>` tags renders in the dashboard and executes in the operator's browser | Render SOUL diff as plain text in a `<pre>` tag; escape HTML entities before display; use a markdown renderer with XSS sanitization |
| Memory health monitor exposes full memory content via dashboard API | Full memory dump API endpoint accessible without authentication returns all project memories including agent reasoning about security-sensitive tasks | Dashboard memory API must enforce project scoping and require the same auth as other API routes; never expose a "dump all memories" endpoint |
| L1 reads memories from all projects for pattern analysis | Cross-project memory leakage: L1 pattern analysis sees memories from other projects and generates suggestions that embed cross-project context | L1 analysis must be strictly project-scoped; query memU with `where.user_id = project_id` filter on every retrieve |
| Recovery loop re-spawns tasks with original task description | Task description may contain credentials or sensitive data from the original request; re-spawn logs them again in structured logging | Sanitize task description before logging; use task_id as the log identifier, not the full description |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **SIGTERM handling:** Docker stop returns within 10s AND exit code is 0 or 143 (not 137) — exit code 137 means SIGKILL, meaning graceful shutdown did not work
- [ ] **Dehydration safety:** After a SIGTERM shutdown, verify `workspace-state.json` shows the task in `dehydrated` or `interrupted` status (not stuck in `in_progress`) — read the state file directly with `cat` after the container exits
- [ ] **Recovery eligibility:** Check that the recovery loop only re-spawns tasks where `recovery_safe: true` — verify by manually setting a task to `in_progress` without the flag and confirming the loop skips it
- [ ] **Memory health monitor false positives:** Run the health monitor against a known-good memory store of 20 entries — it must return 0 conflicts (not falsely flagging all similar entries)
- [ ] **L1 suggestion gate:** Attempt to auto-apply a suggestion by calling the suggestion API directly (bypassing the dashboard) — the API must return 403 or require an explicit confirmation token
- [ ] **SOUL validation:** Submit a SOUL suggestion that removes an existing safety constraint — the validation step must reject it before presenting to the operator
- [ ] **Delta snapshot integrity:** Verify that delta N + delta N+1 applied to the base equals the full snapshot at N+1 — test with a known 2-commit sequence and compare diff outputs
- [ ] **Fire-and-forget task tracking:** Send SIGTERM while a memorize task is pending — verify the pending task completes (or is logged as incomplete) before the process exits

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SIGTERM never reaches Python (shell form entrypoint) | LOW | Change entrypoint to exec form in Dockerfile; rebuild L3 image; no data loss |
| State file stuck in `in_progress` after SIGKILL | LOW | Manually update state file: `python3 -c "import json; ..."` to set task status to `interrupted`; add `recovery_safe: false` to prevent recovery loop from re-spawning |
| Recovery loop re-spawned a task with existing staging branch | MEDIUM | `git branch -D l3/task-{id}` to delete the duplicate staging branch; review state to determine if either run's work is usable; manually trigger L2 review if commits exist |
| L1 auto-applied a bad SOUL suggestion | MEDIUM | `git diff` on `agents/l3_specialist/agent/SOUL.md` to see what changed; `git restore` to revert; if suggestion was auto-applied without git tracking, check `soul-suggestions/` directory for the original and manual diff comparison |
| Memory health monitor deleted valid entries | HIGH | memU PostgreSQL backup restore (if backups are configured); or partially reconstruct from state file activity logs which record task outcomes in plaintext |
| Delta snapshot chain corrupted (overlapping deltas) | LOW | Fall back to full snapshot for the affected task: run `git diff main...l3/task-{id} > {task_id}.diff` and replace the corrupted delta chain; reset the stored base SHA |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SIGTERM absorbed by shell entrypoint | SIGTERM/Graceful Shutdown — Docker entrypoint fix | `docker stop` produces exit code 143 (not 137) within 5s |
| Signal handler deadlocks on fcntl lock | SIGTERM/Graceful Shutdown — dehydration design | No hung processes after `docker stop`; state file shows clean terminal status |
| Recovery loop re-spawns partial-work tasks | Task Recovery — eligibility rules | Recovery loop integration test: task with staging branch is NOT re-spawned |
| Health monitor false positives on similar entries | Memory Health Monitoring — staleness metric design | Zero false positives on 20-entry ground-truth test set |
| L1 suggestions modify SOUL without approval | L1 Strategic Suggestions — approval gate | Direct API call to apply suggestion returns 403; dashboard approval flow required |
| Prompt injection via memory → SOUL | L1 Strategic Suggestions — SOUL validation | Injected test payload in memory does not appear in any generated suggestion |
| Delta snapshot torn during concurrent write | Delta Snapshot — timing constraint | Delta captured after container.wait() returns; SHA-based base tracking |
| Fire-and-forget tasks lost on event loop shutdown | SIGTERM/Graceful Shutdown — task tracking | Pending memorize tasks complete or are logged as skipped; not silently lost |

---

## Sources

- Direct codebase inspection: `orchestration/state_engine.py`, `skills/spawn_specialist/spawn.py`, `skills/spawn_specialist/pool.py`, `orchestration/snapshot.py`, `orchestration/memory_client.py`, `docker/l3-specialist/entrypoint.sh` — HIGH confidence
- Docker SIGTERM and PID 1 signal handling: [PID 1 Signal Handling in Docker — Peter Malmgren](https://petermalmgren.com/signal-handling-docker/), [How to Handle Docker Container Graceful Shutdown and Signal Handling — OneUptime](https://oneuptime.com/blog/post/2026-01-16-docker-graceful-shutdown-signals/view), [Why Your Dockerized Application Isn't Receiving Signals — Hynek](https://hynek.me/articles/docker-signals/), [Trapping Signals in Docker Containers — CloudBees](https://www.cloudbees.com/blog/trapping-signals-in-docker-containers) — HIGH confidence
- Python asyncio signal handling: [python-graceful-shutdown — GitHub](https://github.com/wbenny/python-graceful-shutdown), [Signal Handling in Python — johal.in](https://johal.in/signal-handling-in-python-custom-handlers-for-graceful-shutdowns/) — HIGH confidence
- fcntl flock behavior on process termination: [File Locking in Linux — gavv.net](https://gavv.net/articles/file-locks/), [fcntl(2) Linux manual page](https://man7.org/linux/man-pages/man2/fcntl.2.html) — HIGH confidence
- pgvector production monitoring and staleness: [pgvector for AI Memory in Production — Ivan Turkovic](https://www.ivanturkovic.com/2025/11/16/pgvector-for-ai-memory-in-production-applications/), [Optimizing Vector Search at Scale — Medium](https://medium.com/@dikhyantkrishnadalai/optimizing-vector-search-at-scale-lessons-from-pgvector-supabase-performance-tuning-ce4ada4ba2ed), [Performance Tips Using Postgres and pgvector — Crunchy Data](https://www.crunchydata.com/blog/pgvector-performance-for-developers) — MEDIUM confidence
- Agentic AI memory and SOUL injection security: [Indirect Prompt Injection Poisons AI Long-Term Memory — Palo Alto Unit 42](https://unit42.paloaltonetworks.com/indirect-prompt-injection-poisons-ai-longterm-memory/), [The OpenClaw Prompt Injection Problem — Penligent](https://www.penligent.ai/hackinglabs/the-openclaw-prompt-injection-problem-persistence-tool-hijack-and-the-security-boundary-that-doesnt-exist/), [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — HIGH confidence (external research specifically targets OpenClaw's architecture)
- AI agent configuration modification risks: [Agentic AI and Security — Martin Fowler](https://martinfowler.com/articles/agentic-ai-security.html), [Top 10 Agentic AI Security Threats — Lasso Security](https://www.lasso.security/blog/agentic-ai-security-threats-2025) — MEDIUM confidence
- Delta/incremental snapshot consistency: [Incremental Snapshots in Debezium](https://debezium.io/blog/2021/10/07/incremental-snapshots/), [Concurrency Control — Delta Lake](https://docs.delta.io/concurrency-control/) — MEDIUM confidence (different domain but same consistency principles apply)
- asyncio task lifecycle and event loop shutdown: [Python asyncio documentation — conceptual overview](https://docs.python.org/3/howto/a-conceptual-overview-of-asyncio.html), [Real Python asyncio walkthrough](https://realpython.com/async-io-python/) — HIGH confidence

---
*Pitfalls research for: OpenClaw v1.4 Operational Maturity — Graceful Shutdown, Memory Health, L1 Suggestions, Delta Snapshots*
*Researched: 2026-02-24*
