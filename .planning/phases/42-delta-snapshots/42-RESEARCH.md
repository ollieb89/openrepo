# Phase 42: Delta Snapshots - Research

**Researched:** 2026-02-24
**Domain:** Cursor-based memory retrieval, snapshot pruning, state.json metadata, FastAPI filter extension
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Cursor scope and location**
- Cursor is per-project — one timestamp shared across all agents in the same project
- Stored under `metadata.memory_cursors` in `workspace-state.json` (nested in existing metadata block, not top-level)
- Cursor is updated after a successful fetch — never before. Failed or incomplete fetches leave the cursor unchanged so the next spawn retries the same time window

**Cursor error handling**
- If the cursor value is malformed or unparseable: log a warning and fall back to a full fetch
- Corrupt cursor does not abort the spawn — graceful degradation, worst case is one extra full fetch before the cursor is repaired

**Snapshot pruning configuration**
- `max_snapshots` is opt-in only — no default value. Pruning is inactive unless explicitly set in `project.json:l3_overrides.max_snapshots`
- Existing projects retain current (unlimited) behaviour without any change

**Pruning trigger**
- Prune check runs after each L2 review, when a new snapshot is written to disk
- No separate startup job — check-and-prune happens inline during the review commit path

**Prune ordering and atomicity**
- Delete oldest snapshots first (by filename/timestamp), keeping the newest N files
- If a prune partially fails (some `.diff` files can't be deleted): log the error, leave remaining intact — best-effort housekeeping, do not block the review flow
- Temporary limit breach is acceptable if filesystem permissions fail

### Claude's Discretion
- Exact key name within `metadata.memory_cursors` (e.g., flat string vs nested object if we ever need per-retrieval metadata)
- SHA-based vs timestamp-based cursor identity (requirement specifies ISO timestamp; implementation detail is Claude's)
- How to list snapshot files for oldest-first ordering (mtime vs filename sort)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERF-05 | Per-project `memory_cursors` tracked in state.json metadata with ISO timestamp of last successful retrieval | JarvisState metadata block exists at `state["metadata"]`; cursor key `memory_cursors` stores `{project_id: iso_str}`; JarvisState write methods handle atomic lock |
| PERF-06 | Pre-spawn retrieval fetches only memories newer than cursor; falls back to full fetch on any error | `_retrieve_memories_sync` in spawn.py is the only retrieval call site; add `created_after` param to payload when cursor is valid; cursor read/write needs new `get_memory_cursor` / `update_memory_cursor` helpers on JarvisState |
| PERF-07 | New `created_after` filter parameter on memU `/retrieve` endpoint supports cursor-based queries | Custom FastAPI router in `docker/memory/memory_service/routers/retrieve.py`; `RetrieveRequest` in `models.py`; filter must be applied in-process to items returned by `memu.retrieve()` since memu-py doesn't expose a `created_after` param natively |
| PERF-08 | Configurable `max_snapshots` per project with automatic pruning of oldest snapshots beyond the limit | `cleanup_old_snapshots()` already exists in `orchestration/snapshot.py` but is never called automatically; wire it into `capture_semantic_snapshot()` after writing the new snapshot; read `max_snapshots` from `project.json:l3_overrides.max_snapshots` |
</phase_requirements>

---

## Summary

Phase 42 implements two independent backend optimisations: (1) cursor-based memory retrieval that skips already-seen memories on each L3 pre-spawn, and (2) automatic bounding of per-project snapshot history via a configurable `max_snapshots` limit.

The cursor mechanism is entirely within the existing Python stack: `JarvisState` (which owns `workspace-state.json`), `spawn.py` (the only retrieval call site), and the custom FastAPI memory service router. No new Python packages are required. The cursor is an ISO 8601 timestamp stored under `state["metadata"]["memory_cursors"][project_id]`, read before each `_retrieve_memories_sync` call, and written back after a successful fetch. The memU `/retrieve` endpoint is extended with an optional `created_after` query field; the filter is applied at the FastAPI layer since memu-py's `retrieve()` method does not expose a native timestamp filter.

The snapshot pruning wires `cleanup_old_snapshots()` — which already exists in `snapshot.py` but is never called automatically — into `capture_semantic_snapshot()`. After writing each new snapshot to disk, the function reads `max_snapshots` from `l3_overrides` and prunes if the limit is set. This is a zero-risk path: if `max_snapshots` is absent the function is not called; partial deletion failures are logged and do not block the review flow.

**Primary recommendation:** Implement cursor logic in three focused edits (JarvisState helpers, spawn.py retrieval path, FastAPI retrieve router) and snapshot pruning as one inline call in `capture_semantic_snapshot`. All four changes are independently testable without Docker.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python stdlib `datetime` | 3.x built-in | ISO 8601 timestamp generation and parsing | No extra deps; `datetime.utcnow().isoformat() + "Z"` is the project's established ISO pattern |
| `fcntl.flock` via JarvisState | existing | Atomic read-modify-write of `workspace-state.json` | All state mutations already go through JarvisState; cursor writes must use the same locking |
| FastAPI `pydantic BaseModel` | existing | `RetrieveRequest` extension with `created_after: Optional[str]` | Pattern matches all existing request models in `docker/memory/memory_service/models.py` |
| `pathlib.Path.glob` + `sorted()` | stdlib | Snapshot file enumeration for oldest-first pruning | `cleanup_old_snapshots()` already uses this exact pattern (sort by `st_mtime`) |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `httpx.Client` sync (existing) | already imported in spawn.py | Passes `created_after` in the `/retrieve` payload | Already used by `_retrieve_memories_sync`; no new client needed |
| `orchestration/project_config.py:get_pool_config` pattern | existing | Read `max_snapshots` from `l3_overrides` with safe default | Match the validation pattern used for `max_concurrent`, `queue_timeout_s` |

### No New Dependencies

No new packages. All changes are pure additions within the existing stdlib + httpx + pydantic stack.

---

## Architecture Patterns

### Recommended File Layout for Changes

```
orchestration/
└── state_engine.py          # +get_memory_cursor(), +update_memory_cursor()

skills/spawn_specialist/
└── spawn.py                 # modify _retrieve_memories_sync() and spawn_l3_specialist()

docker/memory/memory_service/
├── models.py                # add Optional[str] created_after to RetrieveRequest
└── routers/
    └── retrieve.py          # pass created_after to retrieve; post-filter results

orchestration/
└── snapshot.py              # wire cleanup_old_snapshots() into capture_semantic_snapshot()
```

### Pattern 1: Cursor Read/Write on JarvisState

**What:** Two new methods on `JarvisState` manage the per-project cursor without exposing raw state dict manipulation to callers.

**When to use:** Any time spawn.py needs to read or persist the memory retrieval cursor.

```python
# In orchestration/state_engine.py

def get_memory_cursor(self, project_id: str) -> Optional[str]:
    """Return the ISO timestamp cursor for project_id, or None if not set.

    Returns None (not raises) on any read error — callers fall back to full fetch.
    """
    try:
        state = self.read_state()
        cursors = state.get("metadata", {}).get("memory_cursors", {})
        value = cursors.get(project_id)
        if not isinstance(value, str) or not value:
            return None
        # Validate parseable as ISO datetime
        from datetime import datetime
        datetime.fromisoformat(value.rstrip("Z"))
        return value
    except Exception as exc:
        logger.warning(
            "Failed to read memory cursor — will do full fetch",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return None


def update_memory_cursor(self, project_id: str, iso_timestamp: str) -> None:
    """Persist the ISO timestamp cursor for project_id under metadata.memory_cursors.

    Uses LOCK_EX read-modify-write. Logs and swallows exceptions — cursor write
    failure must never abort the spawn flow.
    """
    try:
        for attempt in range(self.lock_retry_attempts):
            try:
                with self.state_file.open("r+") as f:
                    self._acquire_lock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        state = self._read_state_locked(f)
                        if "metadata" not in state:
                            state["metadata"] = {}
                        if "memory_cursors" not in state["metadata"]:
                            state["metadata"]["memory_cursors"] = {}
                        state["metadata"]["memory_cursors"][project_id] = iso_timestamp
                        self._write_state_locked(f, state)
                        logger.debug(
                            "Memory cursor updated",
                            extra={"project_id": project_id, "cursor": iso_timestamp},
                        )
                        return
                    finally:
                        self._release_lock(f.fileno())
            except TimeoutError:
                if attempt == self.lock_retry_attempts - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))
    except Exception as exc:
        logger.warning(
            "Failed to persist memory cursor — cursor lost for this spawn",
            extra={"project_id": project_id, "error": str(exc)},
        )
```

### Pattern 2: Cursor-Aware Retrieval in spawn.py

**What:** `_retrieve_memories_sync` gains an optional `created_after` parameter. `spawn_l3_specialist` reads the cursor from state before calling it, and updates the cursor after a successful non-empty fetch.

**When to use:** Every pre-spawn memory retrieval call.

```python
# In skills/spawn_specialist/spawn.py

def _retrieve_memories_sync(
    base_url: str,
    project_id: str,
    query: str,
    created_after: Optional[str] = None,   # NEW
) -> list:
    """Retrieve memories from memU.

    Args:
        created_after: Optional ISO timestamp. When set, sent in the payload
                       so the router returns only newer items. Pass None for
                       a full fetch (first spawn or cursor fallback).
    """
    if not base_url or not project_id:
        return []
    payload = {
        "queries": [{"role": "user", "content": query}],
        "where": {"user_id": project_id},
    }
    if created_after:
        payload["created_after"] = created_after   # NEW
    try:
        with httpx.Client(base_url=base_url, timeout=_RETRIEVE_TIMEOUT) as client:
            response = client.post("/retrieve", json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data[:_RETRIEVE_LIMIT]
            if isinstance(data, dict) and "items" in data:
                return data["items"][:_RETRIEVE_LIMIT]
            return []
    except Exception as exc:
        logger.warning(
            "Pre-spawn memory retrieval failed (non-blocking)",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return []


# Inside spawn_l3_specialist(), just before the existing retrieval block:

# --- Cursor-based memory retrieval ---
state_file = get_state_path(project_id)
jarvis = JarvisState(state_file)
cursor = jarvis.get_memory_cursor(project_id)   # None on first spawn or corrupt

query = f"{task_description} skill:{skill_hint}"
memories = _retrieve_memories_sync(memu_url, project_id, query, created_after=cursor)

# Update cursor after successful fetch (even if empty list returned)
from datetime import datetime, timezone
new_cursor = datetime.now(timezone.utc).isoformat()
jarvis.update_memory_cursor(project_id, new_cursor)

memory_context = _format_memory_context(memories)
```

**Important:** The cursor is updated even when the fetch returns an empty list. An empty result means "nothing new since cursor" which is correct — the cursor timestamp should advance so the next spawn doesn't re-scan the same window. Only on exception (network error etc.) does `_retrieve_memories_sync` return `[]` and the cursor should NOT be updated (the exception path in the function already swallows and returns `[]`, so the cursor update after the call will still run — see Pitfall 1 below for the mitigation).

### Pattern 3: FastAPI Router Extension for `created_after`

**What:** `RetrieveRequest` gets an optional `created_after: Optional[str]` field. The retrieve router passes it to a post-filter on the memu result.

**Why post-filter:** The upstream `memu.retrieve()` method signature does not expose a `created_after` parameter. The filter must be applied at the FastAPI layer to returned items. Memory items returned by memu have a `created_at` field (ISO string or Unix float — verify during implementation).

```python
# In docker/memory/memory_service/models.py

class RetrieveRequest(BaseModel):
    queries: list[dict[str, Any]]
    where: dict[str, Any] | None = None
    created_after: Optional[str] = None  # ISO timestamp cursor — NEW


# In docker/memory/memory_service/routers/retrieve.py

@router.post("/retrieve")
async def retrieve(payload: RetrieveRequest, request: Request):
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(status_code=503, content={"detail": "Memory service not initialized"})

    try:
        result = await memu.retrieve(
            queries=payload.queries,
            where=payload.where,
        )

        # Apply cursor filter if provided
        if payload.created_after and isinstance(result, list):
            result = _filter_after(result, payload.created_after)
        elif payload.created_after and isinstance(result, dict) and "items" in result:
            result["items"] = _filter_after(result["items"], payload.created_after)

        return result
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Retrieval error: {str(e)}"})


def _filter_after(items: list, created_after: str) -> list:
    """Return only items whose created_at is strictly after `created_after`.

    Tolerates missing or unparseable created_at — those items pass through
    (conservative: better to return a stale item than lose a new one).
    """
    try:
        from datetime import datetime
        cutoff = datetime.fromisoformat(created_after.rstrip("Z"))
    except (ValueError, AttributeError):
        logger.warning(f"Unparseable created_after value: {created_after!r} — skipping filter")
        return items

    filtered = []
    for item in items:
        ts = item.get("created_at")
        if ts is None:
            filtered.append(item)  # pass through — conservative
            continue
        try:
            if isinstance(ts, (int, float)):
                item_dt = datetime.utcfromtimestamp(ts)
            else:
                item_dt = datetime.fromisoformat(str(ts).rstrip("Z"))
            if item_dt > cutoff:
                filtered.append(item)
        except (ValueError, TypeError, OSError):
            filtered.append(item)  # pass through — conservative
    return filtered
```

### Pattern 4: Auto-Prune in capture_semantic_snapshot

**What:** After writing the snapshot file, read `max_snapshots` from project config and call the existing `cleanup_old_snapshots()`.

**When to use:** Every time `capture_semantic_snapshot` writes a new `.diff` file.

```python
# At the end of capture_semantic_snapshot(), after snapshot_path.write_text(...):

# Auto-prune if max_snapshots is configured for this project (PERF-08)
try:
    project_cfg = load_project_config(project_id)
    max_snapshots = project_cfg.get("l3_overrides", {}).get("max_snapshots")
    if max_snapshots is not None:
        prune_result = cleanup_old_snapshots(
            workspace_path=workspace_path,
            project_id=project_id,
            max_snapshots=int(max_snapshots),
        )
        if prune_result["deleted_count"] > 0:
            logger.info(
                "Snapshot pruning complete",
                extra={
                    "project_id": project_id,
                    "deleted": prune_result["deleted_count"],
                    "remaining": prune_result["remaining_count"],
                },
            )
except Exception as exc:
    # Pruning failure must never block capture — log and continue
    logger.warning(
        "Snapshot pruning failed (non-blocking)",
        extra={"project_id": project_id, "error": str(exc)},
    )
```

### Anti-Patterns to Avoid

- **Updating cursor before fetch:** If the fetch then fails, the cursor skips the gap. Always update after successful return.
- **Raising on cursor write failure:** Cursor loss means next spawn does a full fetch — acceptable. Do not abort the spawn.
- **Adding `max_snapshots` to global l3 config defaults:** Per CONTEXT.md, it is opt-in only. Do not add a default in `_POOL_CONFIG_DEFAULTS` or `get_pool_config()`.
- **Sorting snapshots by filename lexicographically:** Filenames are task IDs (non-sequential). Use `st_mtime` (already done in existing `cleanup_old_snapshots`).
- **Filtering in `_retrieve_memories_sync` before returning:** The filter lives in the router because that is the natural boundary. spawn.py should not re-filter; it trusts the API.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Snapshot oldest-first ordering | Custom sort logic | Existing `cleanup_old_snapshots()` in snapshot.py | Already tested, uses `st_mtime` sort — just needs wiring |
| Atomic state write for cursor | Direct file write | `JarvisState.update_memory_cursor()` using existing `_write_state_locked` path | All state writes must go through fcntl locking |
| ISO timestamp generation | Custom formatting | `datetime.now(timezone.utc).isoformat()` | Standard Python; avoids TZ confusion |
| Cursor timestamp parsing | Regex | `datetime.fromisoformat()` (Python 3.7+) | Handles ISO 8601 with/without Z suffix after `.rstrip("Z")` |

---

## Common Pitfalls

### Pitfall 1: Cursor Updated Even on memU Network Failure

**What goes wrong:** `_retrieve_memories_sync` swallows exceptions and returns `[]`. The caller cannot distinguish "empty because nothing new" from "empty because network error". If cursor is always updated after the call, a network failure at spawn time advances the cursor, permanently skipping memories created during the outage window.

**How to avoid:** Change `_retrieve_memories_sync` to return a sentinel or use a flag. Simplest fix: return a distinct object (e.g., a dataclass `RetrieveResult(items: list, ok: bool)`). Update cursor only when `ok=True`. The existing tests will need updating for the new return type.

**Alternative (simpler):** Use an explicit exception or a bool out-parameter. Given the project's "graceful degradation always" philosophy, the recommended approach is:

```python
# Return a (list, bool) tuple where bool indicates success
def _retrieve_memories_sync(...) -> tuple[list, bool]:
    ...
    except Exception:
        return [], False   # failed — do not advance cursor

# Caller:
memories, fetch_ok = _retrieve_memories_sync(...)
if fetch_ok:
    jarvis.update_memory_cursor(project_id, new_cursor)
```

This is the approach to use. It preserves all existing graceful degradation while adding cursor accuracy.

### Pitfall 2: `created_at` Field Shape Unknown at Filter Time

**What goes wrong:** The `created_at` field in memU memory items may be a Unix float timestamp, an ISO string, or absent — depending on the database backend (inmemory, sqlite, postgres each store it differently).

**How to avoid:** The `_filter_after` helper in the router must handle all three cases: float (unix epoch), string (ISO), and None (pass through). The conservative pass-through-on-error approach documented in Pattern 3 is correct. During Wave 0 testing, inspect actual item shapes from the inmemory backend to verify.

**Warning sign:** If `created_after` is set but retrieve always returns the full list — the `created_at` field is None or absent in your backend. Add a log line to `_filter_after` to surface this.

### Pitfall 3: JarvisState Cache Stale After Cursor Write

**What goes wrong:** `JarvisState` has an mtime-based write-through cache. After `update_memory_cursor()` writes, the cache is updated by `_write_state_locked`. A subsequent `get_memory_cursor()` in the same JarvisState instance will read from cache correctly. But if a separate JarvisState instance is created elsewhere in the same process before the mtime updates on disk, it may read stale state.

**How to avoid:** In spawn.py, always use the same `jarvis` instance for both `get_memory_cursor()` and `update_memory_cursor()` within a single spawn call. Do not create multiple JarvisState instances for the same state file in the same function.

### Pitfall 4: Pruning Fires Before New Snapshot Is Fully Written

**What goes wrong:** If `cleanup_old_snapshots` is called before `snapshot_path.write_text()` completes and the new file isn't counted yet, it might keep N-1 snapshots instead of N after the prune.

**How to avoid:** `capture_semantic_snapshot` already writes the file with `snapshot_path.write_text(snapshot_content)` before pruning is invoked. The ordering in Pattern 4 is write-first, prune-second. Do not reorder.

### Pitfall 5: max_snapshots Validation Missing

**What goes wrong:** `project.json:l3_overrides.max_snapshots` is set to a string ("10") or negative int (-1) by mistake. `cleanup_old_snapshots` would receive an unexpected value.

**How to avoid:** After reading from project config, validate: `isinstance(max_snapshots, int) and max_snapshots > 0`. If invalid, log a warning and skip pruning (do not raise). Mirror the pattern used in `get_pool_config()`.

---

## Code Examples

### Reading and Writing memory_cursors in workspace-state.json

State file after cursor write (verified structure from state_engine.py):

```json
{
  "version": "1.0.0",
  "protocol": "jarvis",
  "tasks": { ... },
  "metadata": {
    "created_at": 1708800000.0,
    "last_updated": 1708800123.4,
    "memory_cursors": {
      "pumplai": "2026-02-24T10:30:00.123456+00:00"
    }
  }
}
```

The `metadata` block is guaranteed to exist by `_write_state_locked` which adds it if absent. `memory_cursors` is a sub-dict added by the new helper.

### ISO Timestamp Generation (stdlib only)

```python
from datetime import datetime, timezone

# Generate cursor after successful fetch
new_cursor = datetime.now(timezone.utc).isoformat()
# → "2026-02-24T10:30:00.123456+00:00"

# Parse cursor for comparison
cutoff = datetime.fromisoformat(new_cursor)
# Python 3.11+ handles "+00:00"; older versions need .rstrip("Z") for "Z"-suffix variants
```

### project.json l3_overrides Pattern

```json
{
  "l3_overrides": {
    "max_snapshots": 50,
    "max_concurrent": 3,
    "recovery_policy": "auto_retry"
  }
}
```

`max_snapshots` is a new key at the same level as existing keys — no schema migration required.

### cleanup_old_snapshots (existing, already correct)

```python
# From orchestration/snapshot.py (line 606) — confirmed behavior:
def cleanup_old_snapshots(workspace_path: str, project_id: str, max_snapshots: int = 100):
    snapshots_dir = get_snapshot_dir(project_id)
    snapshots = sorted(
        snapshots_dir.glob('*.diff'),
        key=lambda p: p.stat().st_mtime   # oldest first
    )
    # Deletes [:total - max_snapshots] oldest files
    # Returns {'deleted_count': N, 'remaining_count': M}
```

This function already handles: missing directory (returns 0/0), partial deletion (each file unlinked independently), and correct ordering. It does NOT need modification — only wiring.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full memory fetch on every spawn | Cursor-based delta fetch | Phase 42 | Fewer items fetched on repeat spawns; SOUL context stays focused on recent learnings |
| Unlimited snapshot directory growth | Bounded by max_snapshots | Phase 42 | Disk usage bounded for long-running projects |
| cleanup_old_snapshots() callable but never auto-invoked | Auto-invoked after each snapshot write | Phase 42 | Previously existed as dead code |

---

## Open Questions

1. **`created_at` field shape in memU inmemory backend**
   - What we know: Memory items from memu have metadata fields; `created_at` is likely present
   - What's unclear: Whether it's a Unix float or ISO string in the inmemory backend vs postgres
   - Recommendation: During Wave 0, add a quick probe: call `memu.list_memory_items()` and inspect a sample item's `created_at` field type. If None, the filter degrades gracefully (pass-through).

2. **Cursor update on empty-but-successful fetch**
   - What we know: Per CONTEXT.md, cursor is updated "after a successful fetch"
   - What's unclear: If fetch succeeds but returns 0 items (nothing new), should cursor advance?
   - Recommendation: YES — advance the cursor. An empty response confirms the window was scanned; advancing prevents re-scanning the same old window on next spawn.

3. **Thread safety of cursor read/write vs concurrent spawns**
   - What we know: Multiple L3 spawns can happen concurrently (pool.py uses asyncio semaphore but spawns may overlap at the JarvisState level)
   - What's unclear: If two spawns race to read the cursor simultaneously, both get the same cursor and both send identical `created_after`. Then both update the cursor. This is safe — identical cursor means identical window, no memories are missed.
   - Recommendation: No additional locking needed. The per-spawn cursor read and the post-fetch cursor write are already atomic via LOCK_EX in `update_memory_cursor`. Racing reads getting the same value is fine.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (stdlib, no pytest.ini asyncio mode needed for these tests) |
| Config file | `/home/ollie/.openclaw/tests/pytest.ini` (asyncio_mode = auto) |
| Quick run command | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py -x -q` |
| Full suite command | `python3 -m pytest /home/ollie/.openclaw/tests/ -x -q` |
| Estimated runtime | ~5 seconds (all tests are unit/mock-based, no Docker, no network) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-05 | `get_memory_cursor()` returns None when key absent; returns ISO string when set | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_get_memory_cursor_absent -x` | ❌ Wave 0 gap |
| PERF-05 | `update_memory_cursor()` writes under `metadata.memory_cursors[project_id]` | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_update_memory_cursor_writes -x` | ❌ Wave 0 gap |
| PERF-05 | Corrupt cursor value returns None (graceful) | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_get_memory_cursor_corrupt -x` | ❌ Wave 0 gap |
| PERF-06 | `_retrieve_memories_sync` sends `created_after` in payload when provided | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_retrieve_sends_created_after -x` | ❌ Wave 0 gap |
| PERF-06 | Cursor not updated when fetch returns ok=False (network error) | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_cursor_not_updated_on_fetch_failure -x` | ❌ Wave 0 gap |
| PERF-06 | Cursor updated after successful fetch (even empty list) | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_cursor_updated_after_success -x` | ❌ Wave 0 gap |
| PERF-07 | `_filter_after` returns only items newer than cutoff | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_filter_after_timestamp -x` | ❌ Wave 0 gap |
| PERF-07 | `_filter_after` passes through items with None/missing created_at | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_filter_after_missing_created_at -x` | ❌ Wave 0 gap |
| PERF-07 | `_filter_after` handles unix float and ISO string created_at | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_filter_after_unix_float -x` | ❌ Wave 0 gap |
| PERF-07 | Unparseable `created_after` skips filter (returns all items) | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_filter_after_bad_cursor_passthrough -x` | ❌ Wave 0 gap |
| PERF-08 | `capture_semantic_snapshot` calls `cleanup_old_snapshots` when `max_snapshots` set | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_prune_called_when_configured -x` | ❌ Wave 0 gap |
| PERF-08 | No pruning when `max_snapshots` absent from l3_overrides | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_prune_not_called_when_unconfigured -x` | ❌ Wave 0 gap |
| PERF-08 | Prune failure is logged but does not raise | unit | `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py::test_prune_failure_nonfatal -x` | ❌ Wave 0 gap |

### Nyquist Sampling Rate

- **Minimum sample interval:** After every committed task → run: `python3 -m pytest /home/ollie/.openclaw/tests/test_delta_snapshots.py -x -q`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green (`python3 -m pytest /home/ollie/.openclaw/tests/ -x -q`) before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~5 seconds

### Wave 0 Gaps (must be created before implementation)

- [ ] `/home/ollie/.openclaw/tests/test_delta_snapshots.py` — covers PERF-05, PERF-06, PERF-07, PERF-08 (13 test functions listed above)

Existing test infrastructure covers the framework (pytest.ini exists, stdlib-only mocking pattern established in test_spawn_memory.py and test_health_scan.py). Only the new test file is missing.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase read — `orchestration/state_engine.py`: JarvisState metadata block structure, `_write_state_locked` adds `metadata` key, LOCK_EX write pattern, write-through cache behavior
- Direct codebase read — `skills/spawn_specialist/spawn.py`: `_retrieve_memories_sync` signature, payload shape, call site in `spawn_l3_specialist`
- Direct codebase read — `docker/memory/memory_service/routers/retrieve.py`: FastAPI endpoint structure, how memu.retrieve() is called
- Direct codebase read — `docker/memory/memory_service/models.py`: `RetrieveRequest` Pydantic model
- Direct codebase read — `orchestration/snapshot.py:cleanup_old_snapshots`: existing implementation, mtime sort, return dict shape, `capture_semantic_snapshot` write path
- Direct codebase read — `orchestration/project_config.py:get_pool_config`: validation pattern for `l3_overrides` keys

### Secondary (MEDIUM confidence)

- Python stdlib docs (training data, stable): `datetime.fromisoformat()` available Python 3.7+; `datetime.now(timezone.utc).isoformat()` produces `+00:00` suffix

### Tertiary (LOW confidence)

- `created_at` field shape in memu inmemory items: inferred from CRUD list endpoint patterns — not directly verified. Must be confirmed during Wave 0.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are existing, confirmed by direct source read
- Architecture: HIGH — patterns derived from existing code in the same files being modified
- Pitfalls: HIGH — derived from reading actual code paths (cursor update timing, `_write_state_locked` behavior, filter-on-None)
- `created_at` field shape: LOW — not directly verified; confirmed conservative pass-through handles all cases

**Research date:** 2026-02-24
**Valid until:** 2026-04-24 (stable internal codebase — no external API churn)
