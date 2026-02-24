# Stack Research

**Domain:** AI Swarm Orchestration — v1.4 Operational Maturity additions
**Researched:** 2026-02-24
**Confidence:** HIGH (all claims verified against existing codebase + official Python docs + PyPI)

---

## Scope

This document covers ONLY net-new stack needs for v1.4. It does not re-document the existing
validated stack (Python 3 stdlib, docker>=7.1.0, httpx, asyncio, fcntl, Next.js 16, SWR,
Tailwind 4, Recharts, memU/FastAPI/PostgreSQL+pgvector) which is already shipped.

The four feature areas in scope:

1. **SIGTERM graceful shutdown** — signal handling + task dehydration/rehydration + recovery loops
2. **Memory health monitoring** — drift/conflict/stale detection with dashboard override UI
3. **L1 SOUL suggestion engine** — task pattern analysis producing proactive SOUL recommendations
4. **Delta memory snapshots** — reduced I/O via incremental state diffs

---

## Recommended Stack

### Core Technologies — Net New

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python `signal` (stdlib) | built-in | SIGTERM handler registration in pool.py | Already available everywhere Python runs. `loop.add_signal_handler(signal.SIGTERM, cb)` integrates directly with the asyncio event loop that pool.py already runs. No import overhead. Standard Docker PID 1 shutdown pattern. |
| `asyncio.CancelledError` catch (stdlib) | built-in | Task cleanup hook during graceful drain | Pool.py already uses asyncio. The correct dehydration point is the `except asyncio.CancelledError` block in a semaphore-holding coroutine — at that point the task ID, skill hint, and workspace path are all in scope for JarvisState write. |
| Exec-form Docker entrypoint | Dockerfile | PID 1 signal delivery to Python | The current `docker/l3-specialist/entrypoint.sh` uses shell form. Shell PID 1 does NOT forward SIGTERM to child Python processes. Fix: use `exec python -u ...` at the end of entrypoint.sh or switch to exec-form `CMD ["python", "-u", ...]`. Not a library change — a one-line Dockerfile/entrypoint change. |
| Python `collections.Counter` (stdlib) | built-in | Task pattern frequency analysis for L1 SOUL suggestions | Counts recurring keywords from task descriptions, failure patterns, skill type distributions. Already imported in similar fashion to `re` in spawn.py. Sufficient for all plausible OpenClaw task corpus sizes (tens to hundreds of tasks per project — not millions). |
| Python `statistics` (stdlib) | built-in | Success rate and latency statistics for SOUL suggestions | `statistics.mean()`, `statistics.stdev()`, `statistics.median()` for task duration and failure rate signals. Zero new dep. Requires Python >=3.4 (already satisfied). |
| Python `re` (stdlib) | built-in | Keyword extraction from task descriptions | Already used in spawn.py (`_PROJECT_ID_PATTERN`). Extend with `re.findall(r'\w+', desc.lower())` for pattern tokenization. No new import needed in files that already import it. |

### Supporting Libraries — Net New

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `deepdiff` | `>=8.6.1` | Structured JSON delta generation for snapshot diff/patch | Use if delta snapshots need to support full rehydration (reconstructing old state from stored patches). `Delta` objects serialize to flat dicts. No mandatory numpy dep for core diff/delta. Released September 2025 — actively maintained. |

**Note on deepdiff vs pure Python:** For state files that are shallow JSON dicts (<10KB, flat task objects), a custom `_compute_task_delta(old, new)` using dict comprehension is viable with zero new deps. Deepdiff is only needed if delta reversal (rehydrating old state from patches) becomes a requirement. Start with pure Python, add deepdiff if complexity grows.

### What is Already Available — Do NOT Add Again

| Capability | Where It Lives | v1.4 Use |
|------------|---------------|---------|
| Cosine similarity for duplicate/conflict detection | `memU postgres repo: _cosine()` and `vector_search_items()` with pgvector `<=>` operator | Similarity queries go through the existing `/retrieve` REST endpoint with project scoping. No orchestration-side vector math needed. |
| Memory list + delete API | `/memories` GET and `/memories/{id}` DELETE (already deployed in `docker/memory/memory_service/`) | Memory health monitor pages through all memories via this endpoint. Dashboard already calls these routes. |
| HTTP client for memU | `httpx` (already a dep in spawn.py and memory_client.py) | Memory health monitoring calls `/memories?user_id=` using the existing sync/async httpx patterns. |
| JarvisState write primitives | `orchestration/state_engine.py` | Task dehydration serializes into the existing task `metadata` dict. `update_task(task_id, "dehydrated", ...)` is sufficient. No schema change needed. |
| Fire-and-forget background work | `asyncio.create_task()` already used in pool.py | Recovery loop on pool startup and periodic health check polling use the same pattern. |
| Structured JSON logging | `orchestration/logging.py` `get_logger()` factory | All new modules use existing logger factory — no new logging dep. |
| `dataclasses` (stdlib) | built-in | `SuggestionReport` data container for L1 SOUL suggestions | Already available. |

---

## Integration Points with Existing Stack

### Feature 1: SIGTERM Graceful Shutdown + Dehydration/Rehydration

**Integration:** `pool.py` (`L3ContainerPool.run_task()`) registers a handler via `loop.add_signal_handler(signal.SIGTERM, shutdown_handler)`. On signal: set a `_shutting_down` flag, stop accepting new tasks, drain the asyncio semaphore gracefully, write each in-flight task ID to JarvisState with status `"dehydrated"` and serialized context (workspace path, skill hint, task description). On startup: `L3ContainerPool.__init__()` scans JarvisState for tasks in `"dehydrated"` status and re-queues them.

**Files to modify:**
- `skills/spawn_specialist/pool.py` — add signal handler, dehydration drain, startup recovery scan
- `orchestration/state_engine.py` — add `"dehydrated"` to the non-terminal status set (it should NOT appear in `list_active_tasks()` exclusions — dehydrated tasks ARE to be recovered)
- `docker/l3-specialist/entrypoint.sh` — fix PID 1 signal forwarding with `exec`

**No new library imports.** `import signal` is stdlib. `asyncio` is already imported in pool.py.

### Feature 2: Memory Health Monitoring

**Integration:** New `orchestration/memory_health.py` module with three detection passes:

1. **Staleness**: `GET /memories?user_id={project_id}` — compare `updated_at` against configurable threshold (default: 30 days). Items not reinforced and older than threshold are flagged as stale.
2. **Near-duplicate**: For each memory, `POST /retrieve` with the item's own content as query. Items returned with cosine similarity >0.92 (via memU's pgvector `<=>`) are flagged as duplicates. The threshold is tunable via config.
3. **Conflict detection**: Two memories with near-identical embedding but opposite sentiment keywords (simple negation heuristic: one contains "failed", the other "succeeded" for the same task pattern) are flagged as conflicts.

**Dashboard:** New `/api/memory/health` Next.js route. New "Health" tab on the existing `/memory` page with flagged items, similarity scores, timestamps, and manual override buttons (delete / keep / merge label).

**No new Python deps.** All HTTP via existing `httpx.AsyncClient` through `MemoryClient`. Cosine scoring comes back in the `/retrieve` response payload (memU already includes scores).

### Feature 3: L1 SOUL Suggestion Engine

**Integration:** New `orchestration/pattern_analyzer.py`. Reads `JarvisState.list_all_tasks()` for all registered projects (via `project_config.py` project list). Extracts:
- `skill_hint` distribution (code vs test ratio)
- Top 20 keyword tokens from task descriptions via `Counter(re.findall(r'\w+', desc.lower()))`
- Success rate per skill type: `completed / (completed + failed)`
- Mean and p95 task duration from `spawn_requested_at` → `completed_at` metadata timestamps
- Recurring failure phrases (task description tokens that appear disproportionately in failed tasks)

Returns a `SuggestionReport` dataclass. CLI entry point: `openclaw suggest-soul --project {id}` added to `orchestration/project_cli.py`. L1 reads this via new `GET /api/suggestions?project=` dashboard route.

**No new library imports.** `collections`, `re`, `statistics`, `dataclasses` are all stdlib.

### Feature 4: Delta Memory Snapshots

**Integration:** Extends `orchestration/snapshot.py`. On each snapshot write, compute a delta between the last written snapshot and the current state. Store `{base_hash, patches, timestamp, project_id}` in the snapshot directory alongside full snapshots (one full snapshot per N deltas, configurable).

**Approach A — Zero dep (recommended for v1.4):**
```python
def _compute_task_delta(old_tasks: dict, new_tasks: dict) -> dict:
    added = {k: v for k, v in new_tasks.items() if k not in old_tasks}
    removed = list(old_tasks.keys() - new_tasks.keys())
    changed = {k: v for k, v in new_tasks.items()
               if k in old_tasks and old_tasks[k] != v}
    return {"added": added, "removed": removed, "changed": changed}
```

**Approach B — deepdiff (if rehydration needed):**
```python
from deepdiff import DeepDiff, Delta
delta = Delta(DeepDiff(old_state, new_state))
serialized = delta.to_flat_dicts()
```

Recommendation: Implement Approach A in v1.4 to maintain the zero-external-dep principle. Add a `SNAPSHOT_DELTA_MODE = True` config flag. Migrate to deepdiff if the delta format needs to be externally consumed or reversed.

---

## Installation

```bash
# For Feature 4, Approach B only (if pure Python delta is insufficient):
pip install "deepdiff>=8.6.1"

# All other v1.4 features require NO new pip installs.
# Features 1, 2, 3 are stdlib-only additions.
```

To verify no new dep is actually needed for Features 1-3:
```bash
# Confirm signal, asyncio, collections, statistics, re are stdlib
python3 -c "import signal, asyncio, collections, statistics, re; print('all stdlib')"
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| stdlib `signal.add_signal_handler` | `aioshutdown` PyPI package | Only if multiple complex shutdown hooks need ordered registration across many async components. OpenClaw's shutdown surface is small (one pool, one state file). Stdlib is sufficient and adds no dep. |
| deepdiff >=8.6.1 for delta snapshots | `jsonpatch==1.33` | Use jsonpatch if external consumers need RFC 6902 interoperability. jsonpatch only dep is `jsonpointer`. deepdiff is better for Python-internal reconstruction because Delta is self-describing. |
| Pure Python delta dict diff (Approach A) | deepdiff | Use deepdiff when task metadata grows deeply nested or when delta reversal is required. At v1.4 scope the state dict is shallow enough that custom diff is maintainable and simpler. |
| Existing `/retrieve` endpoint for similarity in health monitor | numpy cosine similarity in orchestration | Never add numpy to the orchestration layer. memU's pgvector already computes cosine distance efficiently at the DB tier for the dataset sizes involved. |
| `collections.Counter` + `statistics` for pattern analysis | scikit-learn (KMeans, DBSCAN) | Use ML clustering only when task corpus exceeds ~10,000 entries. At current scale (tens to hundreds of tasks per project), `Counter.most_common()` gives identical insight at zero cost. |
| `asyncio.Queue` for recovery task re-queuing | Redis / Celery / RQ | Introduces a broker dependency for a problem that can be solved with an in-memory queue populated from JarvisState on startup. Single-host system with no persistence requirement across broker restarts. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `numpy` in orchestration layer | Adds 15MB+ compiled dependency to what is otherwise a zero-dep Python package. Vector math for memory health is performed by pgvector inside the DB. | Existing `/retrieve` REST API via httpx |
| `scikit-learn` for task pattern analysis | Pulls in numpy + scipy + joblib. At OpenClaw's scale this is solving a frequency-count problem with machine learning. | `collections.Counter` + `statistics` stdlib |
| `celery` or `rq` for recovery queues | Introduces Redis/broker dependency. Recovery queue is an in-memory list of dehydrated task IDs read from JarvisState on pool startup. | `asyncio.Queue` + JarvisState read on startup |
| Shell-form Docker entrypoint (unchanged) | PID 1 is `/bin/bash`; SIGTERM goes to bash, not Python. Python pool never receives the signal. Graceful shutdown silently fails. | `exec python -u ...` at end of entrypoint.sh |
| `prometheus_client` or OpenTelemetry | Explicitly out of scope per PROJECT.md "Out of Scope" section. Single-host system. | Existing structured JSON logging via `get_logger()` |
| `pendulum` in orchestration layer | Already used inside memU but not in orchestration. The orchestration layer only needs `datetime.fromisoformat()` (stdlib, Python 3.11+) for timestamp parsing. | `datetime.fromisoformat()` (stdlib 3.11+) |
| `APScheduler` or similar for health monitor polling | Scheduler dependency for what is a `asyncio.get_event_loop().call_later(interval, fn)` call. | `asyncio.call_later()` or periodic background task with `asyncio.sleep()` loop |

---

## Stack Patterns by Variant

**If delta snapshot complexity stays low (state files <10KB, flat task dicts):**
- Use Approach A: custom `_compute_task_delta()` pure Python in snapshot.py
- Zero new dependencies
- Sufficient for task-level change tracking at current scale

**If delta snapshots need to support rehydration (reconstructing old state from patch chain):**
- Use Approach B: `deepdiff>=8.6.1`
- `Delta` objects are serializable to flat dicts via `to_flat_dicts()`
- Reversible: apply `delta` to `old_state` to reconstruct `new_state`
- Add to `requirements.txt` only when this need is confirmed

**If memory health monitoring needs to run on a schedule (not just on-demand):**
- Use `asyncio.sleep()` loop in a background task — consistent with pool.py's existing polling pattern
- Do NOT add APScheduler or Celery Beat

**If SIGTERM needs to coordinate across both `pool.py` and a future `monitor.py` daemon:**
- Register `signal.SIGTERM` handler in each process independently
- Each registers via `signal.signal()` (sync context) or `loop.add_signal_handler()` (async context)
- Pool and monitor are separate processes — no shared signal handler state

**If the L1 SOUL suggestion engine needs to generate prose recommendations:**
- Pattern analyzer produces structured data; L1 formats it as text via its own SOUL template
- Do NOT add an LLM API call inside pattern_analyzer.py — keep analysis deterministic and pure Python
- L1 agent interprets the `SuggestionReport` and writes SOUL edits

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `deepdiff>=8.6.1` | Python >=3.9 | Verified on PyPI, September 2025 release. numpy is NOT a mandatory dep — only needed for `[optimize]` extra. |
| `jsonpatch==1.33` | Python >=3.7 (works on 3.13+) | Stable since June 2023. Single dep: `jsonpointer`. No C extensions — pure Python. |
| `signal.add_signal_handler()` | Python 3.x, Unix/Linux only | Not available on Windows. OpenClaw targets Ubuntu 24.04 — fully compatible. Must be called from within a running asyncio event loop for async-safe callback. |
| stdlib `statistics` | Python >=3.4 | Available on all supported Python versions. `statistics.stdev()` requires >=2 values — guard with `len(durations) >= 2` check. |
| `datetime.fromisoformat()` | Python >=3.7 (full ISO 8601 on >=3.11) | For timestamp parsing in pattern_analyzer.py. Python 3.11+ handles timezone offsets properly. OpenClaw host is Python 3.14.3 — no issue. |

---

## Sources

- Python 3 official docs `asyncio-eventloop.html` — `loop.add_signal_handler()` usage, Unix-only constraint, integration with asyncio tasks (HIGH confidence)
- Python 3 official docs `signal.html` — `signal.SIGTERM`, `signal.signal()` (HIGH confidence)
- PyPI deepdiff 8.6.1 — verified latest version September 2025, Python >=3.9, numpy not mandatory for core (HIGH confidence, fetched 2026-02-24)
- PyPI jsonpatch 1.33 — verified latest stable, pure Python, single dep (HIGH confidence, fetched 2026-02-24)
- `/home/ollie/.openclaw/skills/spawn_specialist/pool.py` — confirmed asyncio event loop context, existing `asyncio.create_task()` patterns (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/orchestration/state_engine.py` — confirmed JarvisState write primitives, `update_task()` and `create_task()` signature for dehydration (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/orchestration/memory_client.py` — confirmed httpx AsyncClient pattern, existing `health()`, `memorize()`, `retrieve()` methods (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/docker/memory/memory_service/routers/memories.py` — confirmed `/memories` GET list and `/memories/{id}` DELETE endpoints exist in deployed service (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/docker/memory/memory_service/routers/health.py` — confirmed `/health` endpoint shape (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/workspace/memory/src/memu/database/postgres/repositories/memory_item_repo.py` — confirmed `vector_search_items()` with pgvector cosine distance `<=>`, pure-Python `_cosine()` fallback, similarity score returned in tuples (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/docker/l3-specialist/entrypoint.sh` — confirmed shell-form entrypoint (PID 1 issue exists, exec fix needed) (HIGH confidence, direct code inspection)
- WebSearch: Python SIGTERM Docker PID 1 patterns 2025/2026 — corroborated exec-form fix and dumb-init alternative (MEDIUM confidence)
- WebSearch: deepdiff delta serialization flat dicts (MEDIUM confidence, corroborated by PyPI docs)

---

*Stack research for: OpenClaw v1.4 Operational Maturity*
*Researched: 2026-02-24*
*Previous baseline (v1.0–v1.3): Python 3 stdlib + docker>=7.1.0 + httpx + asyncio + Next.js 16 + memU/FastAPI/PostgreSQL+pgvector — all unchanged*
