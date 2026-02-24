# Phase 28: L3 Auto-Memorization - Research

**Researched:** 2026-02-24
**Domain:** asyncio fire-and-forget, Python pool lifecycle hooks, config injection
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**What gets memorized**
- Store the full semantic snapshot as-is (git diff + metadata) as the memory content
- Include the full git diff — no truncation or summarization
- No size limit per memory item; let memU handle chunking/embedding
- Use existing snapshot metadata only (task_id, agent, timestamp, files changed) — no additional fields needed

**Trigger timing & lifecycle**
- Memorize on successful L3 task completion only — failures, timeouts, and rejections are not memorized
- Fire memorization after the snapshot is created but before the pool slot is released
- Fire-and-forget via `asyncio.create_task` with an exception handler that logs a warning on failure — no retry, no blocking

**MEMU env var injection**
- MEMU_API_URL value sourced from `openclaw.json` config (new field)
- Always inject the env var into L3 containers regardless of memU availability — no health check at spawn time
- The actual memorization call happens in the orchestration layer (Python), not inside the L3 container
- L3 gets the env var to prepare for Phase 31 (in-execution queries), not for this phase's memorization flow

**Memory attribution**
- Use the L3 specialist's agent ID (e.g. "l3_specialist") as the agent_id in MemoryClient
- Tag each memory with task_type (code/test) and file paths touched
- Use category prefix "l3_outcome" to distinguish from future memory types (Phase 30 will use "l2_review")

### Claude's Discretion
- HTTP timeout for the fire-and-forget memorization call
- Additional MEMU env vars beyond MEMU_API_URL (if needed for clean implementation)
- Memory title/summary generation approach (auto-generate from snapshot or use task description)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-01 | L3 task outcomes (semantic snapshots) are auto-memorized after successful container exit via fire-and-forget pattern | asyncio.create_task pattern; MemoryClient.memorize() already sentinel-safe; pool._attempt_task() is the exact call site |
| MEM-03 | Memorization failure is non-blocking — L3 task lifecycle and L2 review flow continue uninterrupted if memory service is unavailable | MemoryClient.memorize() already returns None on any exception — sentinel degradation already implemented; fire-and-forget wrapping ensures the `result` dict is returned before memorize completes |
| MEM-04 | MEMU_API_URL environment variable is injected into L3 containers at spawn time | spawn_l3_specialist() environment dict in spawn.py; new field in openclaw.json; get_memu_config() helper pattern mirrors existing get_pool_config() |
</phase_requirements>

---

## Summary

Phase 28 wires the existing MemoryClient (Phase 27) into two places in the existing spawn/pool infrastructure: the L3 container environment (for MEM-04, forward-compat with Phase 31) and the pool's `_attempt_task()` success path (for MEM-01 and MEM-03).

The fire-and-forget pattern uses `asyncio.create_task()`, which schedules the memorization coroutine on the running event loop without awaiting it. The pool slot is released in the `finally:` block of `spawn_and_monitor()` — the memorization task is launched *before* the function returns, meaning the slot is released while memorization is still in flight. This is the exact behavior required: pool slot freed before memU pipeline completes.

The scope of changes is deliberately narrow: one new field in `openclaw.json`, one new config reader in `project_config.py`, three lines added to `spawn.py` (env injection), and one async helper function + `create_task` call in `pool.py`'s `_attempt_task()` on the success branch. No new files are strictly required — all changes are additive to existing modules.

**Primary recommendation:** Add `_memorize_snapshot_fire_and_forget()` as a private async coroutine in `pool.py`, called via `asyncio.create_task()` immediately after `jarvis.update_task(status="completed")` in `_attempt_task()`. This keeps the memorization co-located with the task lifecycle event that triggers it and leverages the already-running asyncio event loop.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio.create_task | stdlib (3.7+) | Fire-and-forget coroutine scheduling | Already used in pool.py (log streaming); no new dep |
| MemoryClient | Phase 27 | memU REST API wrapper with scoping | Already exists; memorize() already sentinel-safe |
| httpx.AsyncClient | 0.27+ | HTTP transport inside MemoryClient | Already installed; used by MemoryClient |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| orchestration.snapshot | existing | Read saved .diff file content for memorization | Used to load snapshot content from disk after capture_semantic_snapshot() |
| orchestration.project_config | existing | Read MEMU_API_URL from openclaw.json | Pattern established by get_pool_config(); new get_memu_config() follows same pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.create_task | asyncio.ensure_future | create_task is preferred in Python 3.7+; ensure_future is deprecated for coroutines |
| asyncio.create_task | threading.Thread | Thread adds overhead; asyncio is already the runtime for pool.py |
| asyncio.create_task | Background task queue | Overkill; no retry requirement; fire-and-forget is the stated pattern |

**Installation:** No new packages required — all dependencies already installed.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. Changes are additive to:
```
orchestration/
├── project_config.py   # + get_memu_config() helper
└── memory_client.py    # no changes

skills/spawn_specialist/
├── spawn.py            # + MEMU env vars in environment dict
└── pool.py             # + _memorize_snapshot_fire_and_forget() + create_task call

openclaw.json           # + "memory": {"memu_api_url": "http://..."} field
```

### Pattern 1: Fire-and-Forget with asyncio.create_task

**What:** Schedule a coroutine without awaiting it. The caller continues immediately. The coroutine runs concurrently on the same event loop.

**When to use:** Any time you need background work that must not block the main flow and where failures are tolerable (logged but not raised).

**Critical detail:** `create_task()` requires an active running event loop. In `_attempt_task()`, the event loop is always running (the function is itself `async`). This is safe.

**Critical detail:** Tasks created with `create_task()` that raise unhandled exceptions produce a "Task exception was never retrieved" warning in the console. The exception handler in the coroutine body (`except Exception: logger.warning(...)`) prevents this.

```python
# Source: Python 3 asyncio docs — asyncio.create_task()
async def _memorize_snapshot_fire_and_forget(
    self,
    task_id: str,
    snapshot_content: str,
    skill_hint: str,
) -> None:
    """Fire-and-forget: memorize snapshot. Exception logged, never raised."""
    memu_cfg = get_memu_config()
    if not memu_cfg.get("enabled", True):
        return
    base_url = memu_cfg.get("memu_api_url", "")
    if not base_url:
        logger.warning("MEMU_API_URL not configured — skipping memorization", extra={"task_id": task_id})
        return

    agent_type = AgentType.L3_CODE if skill_hint == "code" else AgentType.L3_TEST
    try:
        async with MemoryClient(base_url, self.project_id, agent_type) as client:
            await client.memorize(snapshot_content, category="l3_outcome")
        logger.info("Snapshot memorized", extra={"task_id": task_id})
    except Exception as exc:
        logger.warning("Snapshot memorization failed (non-blocking)", extra={"task_id": task_id, "error": str(exc)})


# Call site in _attempt_task() after jarvis.update_task(status="completed"):
asyncio.create_task(
    self._memorize_snapshot_fire_and_forget(task_id, snapshot_content, skill_hint)
)
```

### Pattern 2: Snapshot Content Loading

The semantic snapshot is already written to disk by `capture_semantic_snapshot()`. However, `capture_semantic_snapshot()` is called from the **L3 entrypoint inside the container** — not from the pool. The snapshot `.diff` file is written to `workspace/.openclaw/<project_id>/snapshots/<task_id>.diff` which is volume-mounted at `rw`.

**Key insight:** By the time `_attempt_task()` reaches the success path, the container has already exited and the snapshot file is on disk. The pool can read it directly from `get_snapshot_dir(project_id) / f"{task_id}.diff"`.

```python
from orchestration.project_config import get_snapshot_dir

snapshot_path = get_snapshot_dir(self.project_id) / f"{task_id}.diff"
if snapshot_path.exists():
    snapshot_content = snapshot_path.read_text()
else:
    snapshot_content = f"Task {task_id} completed (no snapshot available)"
```

### Pattern 3: MEMU Config in openclaw.json

Follow the established pattern of reading optional configuration from `openclaw.json`. The new field is a top-level `"memory"` object:

```json
{
  "memory": {
    "memu_api_url": "http://localhost:18791"
  }
}
```

The corresponding reader in `project_config.py` follows `get_pool_config()` exactly:

```python
def get_memu_config() -> Dict[str, Any]:
    """Read memory service config from openclaw.json.

    Returns:
        Dict with 'memu_api_url' key. Returns empty dict on any error.
        Never raises — callers receive a usable (possibly empty) config.
    """
    defaults = {"memu_api_url": "", "enabled": True}
    try:
        root = _find_project_root()
        config_path = root / "openclaw.json"
        with open(config_path) as f:
            cfg = json.load(f)
        memory_cfg = cfg.get("memory", {})
        result = defaults.copy()
        if "memu_api_url" in memory_cfg:
            result["memu_api_url"] = memory_cfg["memu_api_url"]
        return result
    except Exception as exc:
        _logger.warning("Failed to read memu config — memorization disabled", extra={"error": str(exc)})
        return defaults
```

### Pattern 4: MEMU Env Var Injection in spawn.py

The `environment` dict in `spawn_l3_specialist()` already contains 8 env vars. Adding MEMU vars is a straight addition. Per decisions: always inject regardless of memU availability.

```python
# In spawn_l3_specialist() environment dict — add after existing vars:
"MEMU_API_URL": get_memu_config().get("memu_api_url", ""),
"MEMU_AGENT_ID": "l3_specialist",
"MEMU_PROJECT_ID": project_id,
"MEMU_ENABLED": "1",
```

Note: The CONTEXT.md decision says "MEMU_API_URL value sourced from openclaw.json config" — the `get_memu_config()` call at spawn time satisfies this. The additional vars (`MEMU_AGENT_ID`, `MEMU_PROJECT_ID`, `MEMU_ENABLED`) are Claude's discretion and provide clean Phase 31 forward-compat without extra work for the L3 runtime.

### Pattern 5: Exact Call Site in pool._attempt_task()

The only valid trigger point is after `jarvis.update_task(task_id, status="completed")` on the `result["status"] == "completed"` branch. The snapshot must be on disk (container has exited) and the task is confirmed successful before firing memorization.

```python
# EXISTING success path in _attempt_task():
if result["status"] == "completed":
    t0 = time.time()
    jarvis.update_task(
        task_id=task_id,
        status="completed",
        activity_entry=f"Task completed successfully (exit code: {result['exit_code']})",
    )
    lock_wait_total_ms += (time.time() - t0) * 1000

    # NEW: fire-and-forget memorization (non-blocking, runs after slot release)
    snapshot_path = get_snapshot_dir(self.project_id) / f"{task_id}.diff"
    snapshot_content = snapshot_path.read_text() if snapshot_path.exists() else f"Task {task_id} completed"
    asyncio.create_task(
        self._memorize_snapshot_fire_and_forget(task_id, snapshot_content, skill_hint)
    )
```

The `finally:` block with `self.semaphore.release()` is in `spawn_and_monitor()`, which calls `_attempt_task()`. The task is created inside `_attempt_task()`, then `_attempt_task()` returns the result dict, then `spawn_and_monitor()` runs `finally: self.semaphore.release()`. The memorization task is already scheduled on the event loop before the slot is released — the fire-and-forget timing requirement is naturally satisfied.

### Anti-Patterns to Avoid

- **Awaiting the memorization coroutine:** `await self._memorize_snapshot_fire_and_forget(...)` would block the pool slot until memU completes (minutes). Use `create_task`, never `await`.
- **Health-checking memU at spawn time:** Adds latency to every spawn; decided against. The sentinel degradation in MemoryClient handles unavailability silently.
- **Reading snapshot before container exits:** The pool can only call `snapshot_path.read_text()` after `container.wait()` returns. The existing code structure already guarantees this — `monitor_container()` is awaited before the success branch is reached.
- **Memorizing on retry attempts:** Only final successful outcome should be memorized. The `retry_count` field is available to filter if needed, but the natural placement (in the `status == "completed"` branch, after the final result is known) handles this correctly.
- **Passing snapshot_content to `_attempt_task` via parameters:** `_attempt_task` doesn't currently take `skill_hint` — but it does, it's already a parameter. The snapshot read happens inside `_attempt_task` after success — no interface changes needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP fire-and-forget | Custom thread pool, background queue | asyncio.create_task | Already in asyncio runtime; zero overhead |
| Non-blocking degradation | Try/except around await | MemoryClient sentinel pattern (already built) | memorize() already returns None on failure |
| Config reading | Parse openclaw.json inline | get_memu_config() helper (to be built, ~15 lines) | Follows established project_config.py pattern |

**Key insight:** The hard work is already done. Phase 27 built the MemoryClient with sentinel degradation. Phase 26 built the snapshot system. This phase is pure integration — wiring existing components at the right lifecycle point.

---

## Common Pitfalls

### Pitfall 1: Task Exception Not Handled

**What goes wrong:** `asyncio.create_task()` runs the coroutine in the background. If an unhandled exception escapes the coroutine, Python logs "Task exception was never retrieved" to stderr — noisy but not fatal.

**Why it happens:** Unlike `await`, `create_task` does not propagate exceptions to the caller.

**How to avoid:** Wrap the entire body of `_memorize_snapshot_fire_and_forget` in `try/except Exception` and log a warning. MemoryClient.memorize() already catches all exceptions internally, so the outer catch is defensive belt-and-suspenders.

**Warning signs:** "Task exception was never retrieved" in logs.

### Pitfall 2: Snapshot File Not on Disk at Call Time

**What goes wrong:** `snapshot_path.read_text()` raises `FileNotFoundError` if called before the container's entrypoint writes the `.diff` file.

**Why it happens:** L3 containers call `capture_semantic_snapshot()` inside the container (the container itself runs this). If the container exits without writing the snapshot (e.g. task_description was empty, git had nothing to diff), the file won't exist.

**How to avoid:** Always check `snapshot_path.exists()` before reading. Fall back to a minimal content string (e.g. `f"Task {task_id} completed — no snapshot available"`). This allows memorization to still proceed with metadata even when the diff is empty.

**Warning signs:** `FileNotFoundError` on `snapshot_path.read_text()`.

### Pitfall 3: Event Loop Not Running When create_task is Called

**What goes wrong:** `asyncio.create_task()` raises `RuntimeError: no running event loop` if called outside an async context.

**Why it happens:** This would only happen if `_memorize_snapshot_fire_and_forget` were called from a sync context. In the current architecture, `_attempt_task()` is `async` and is always called from the asyncio event loop.

**How to avoid:** The call site is inside `async def _attempt_task()` — no issue. Document this as a constraint if `_attempt_task` is ever refactored to sync.

**Warning signs:** `RuntimeError: no running event loop` at task creation.

### Pitfall 4: snapshot content is the L3 container's diff, not the merged diff

**What goes wrong:** The snapshot captured by the L3 entrypoint is the diff on the `l3/task-{task_id}` staging branch. This is the correct content to memorize — it reflects what the L3 actually did. Confusion arises if someone assumes the merged diff should be memorized instead.

**Why it happens:** The pool's success path precedes L2 review and merge. The `.diff` file is written by the container before it exits.

**How to avoid:** Memorize the staging-branch snapshot. This is exactly what `capture_semantic_snapshot()` writes to disk.

### Pitfall 5: `get_memu_config()` import in spawn.py creates circular dependency

**What goes wrong:** `spawn.py` currently imports from `orchestration.*`. Adding `get_memu_config()` to `project_config.py` and importing it from `spawn.py` is safe — `project_config.py` has no imports from `spawn.py`.

**How to avoid:** Verify import chain before committing. `spawn.py` → `orchestration.project_config` → no circular deps.

---

## Code Examples

### Complete _memorize_snapshot_fire_and_forget implementation

```python
# Source: asyncio docs + MemoryClient Phase 27 patterns
async def _memorize_snapshot_fire_and_forget(
    self,
    task_id: str,
    snapshot_content: str,
    skill_hint: str,
) -> None:
    """
    Memorize L3 task snapshot in memU. Non-blocking fire-and-forget.

    Called via asyncio.create_task() — exceptions are caught and logged,
    never raised. Memorization failure is completely non-blocking.
    """
    from orchestration.project_config import get_memu_config
    from orchestration.memory_client import MemoryClient, AgentType

    memu_cfg = get_memu_config()
    base_url = memu_cfg.get("memu_api_url", "").strip()
    if not base_url:
        logger.debug(
            "MEMU_API_URL not configured — skipping memorization",
            extra={"task_id": task_id},
        )
        return

    agent_type = AgentType.L3_CODE if skill_hint == "code" else AgentType.L3_TEST
    try:
        async with MemoryClient(base_url, self.project_id, agent_type) as client:
            result = await client.memorize(snapshot_content, category="l3_outcome")
        if result is not None:
            logger.info(
                "Snapshot memorized",
                extra={"task_id": task_id, "project_id": self.project_id},
            )
        # If result is None, MemoryClient already logged a warning
    except Exception as exc:
        # Belt-and-suspenders: MemoryClient.memorize() should not raise,
        # but catch here to guarantee fire-and-forget semantics.
        logger.warning(
            "Snapshot memorization failed (non-blocking)",
            extra={"task_id": task_id, "error": str(exc)},
        )
```

### openclaw.json memory field addition

```json
{
  "memory": {
    "memu_api_url": "http://localhost:18791"
  }
}
```

### Environment dict additions in spawn.py

```python
# In spawn_l3_specialist() environment dict (inside container_config):
"environment": {
    # ... existing vars ...
    "MEMU_API_URL": get_memu_config().get("memu_api_url", ""),
    "MEMU_AGENT_ID": "l3_specialist",
    "MEMU_PROJECT_ID": project_id,
    "MEMU_ENABLED": "1",
},
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| asyncio.ensure_future | asyncio.create_task | Python 3.7 (2018) | create_task is preferred for coroutines; ensure_future still works but deprecated for this use |
| Manual thread for background HTTP | asyncio.create_task | N/A for this project | Pool is already asyncio; no threading needed |

---

## Open Questions

1. **What HTTP timeout to use for the memorization call in `_memorize_snapshot_fire_and_forget`?**
   - What we know: MemoryClient already uses `TIMEOUT_MEMORIZE = httpx.Timeout(10.0, connect=2.0)` for embedding generation
   - What's unclear: The fire-and-forget coroutine uses MemoryClient directly, so it inherits the 10s timeout automatically — no separate timeout decision needed unless the planner wants a longer "background" timeout
   - Recommendation: Inherit the existing 10s TIMEOUT_MEMORIZE. This is already conservative enough for embedding. No separate override needed.

2. **Should additional MEMU env vars (MEMU_AGENT_ID, MEMU_PROJECT_ID, MEMU_ENABLED) be injected?**
   - What we know: Only MEMU_API_URL is required by CONTEXT.md; others are discretion
   - What's unclear: Phase 31 (in-execution queries) needs the agent to know its own identity inside the container
   - Recommendation: Inject all four (`MEMU_API_URL`, `MEMU_AGENT_ID`, `MEMU_PROJECT_ID`, `MEMU_ENABLED`). The container currently knows its `OPENCLAW_PROJECT` but not its agent identity or whether memory is available. Four vars is minimal forward-compat.

3. **Memory title/summary generation for the memorize() content field?**
   - What we know: MemoryClient.memorize() takes a `content` string and a `category` label. The current implementation uses `resource_url` as the content field in the memU payload (Phase 26/27 decision — memU expects resource_url for the content string).
   - What's unclear: Should a title prefix be prepended to help future retrieval? e.g. `f"Task {task_id} ({skill_hint}): {task_description}\n\n{snapshot_content}"`
   - Recommendation: Prepend a one-line header: `f"# L3 {skill_hint.upper()} task {task_id}\n\n{snapshot_content}"`. This ensures RAG retrieval can match on task type and ID without adding metadata fields to the payload.

---

## Sources

### Primary (HIGH confidence)

- Python 3 asyncio docs (stdlib) — asyncio.create_task(), task exception handling, running event loop requirements
- `/home/ollie/.openclaw/orchestration/memory_client.py` — MemoryClient API, AgentType enum, memorize() signature, sentinel patterns
- `/home/ollie/.openclaw/skills/spawn_specialist/pool.py` — _attempt_task() call site, success branch, spawn_and_monitor() finally block structure
- `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` — environment dict structure in spawn_l3_specialist()
- `/home/ollie/.openclaw/orchestration/snapshot.py` — capture_semantic_snapshot() return value, snapshot file path, get_snapshot_dir() usage
- `/home/ollie/.openclaw/orchestration/project_config.py` — get_pool_config() pattern to follow for get_memu_config()
- `/home/ollie/.openclaw/.planning/phases/27-memory-client-scoping/27-01-SUMMARY.md` — decisions, import patterns, next-phase guidance

### Secondary (MEDIUM confidence)

- Python 3.7 asyncio.create_task() deprecation of ensure_future — well-documented in Python changelog

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components already exist in the codebase; no new libraries
- Architecture: HIGH — call site verified by reading pool.py; insertion point is unambiguous
- Pitfalls: HIGH — derived from direct code analysis of the existing pool/spawn/snapshot code

**Research date:** 2026-02-24
**Valid until:** Stable — implementation targets existing, stable Python stdlib and internal modules
