# Architecture Research

**Domain:** AI Swarm Orchestration — v1.4 Operational Maturity Integration
**Researched:** 2026-02-24
**Confidence:** HIGH — based on direct codebase analysis of all integration points

---

## Context: What Already Exists (v1.3)

This document is scoped exclusively to v1.4 feature integration. It describes how graceful
shutdown, memory health monitoring, L1 strategic suggestions, and delta-based snapshots
fit into the existing architecture — what to create new, what to modify surgically, and
what to leave untouched.

### Existing Components (Do Not Rewrite)

| Component | File | v1.4 Status |
|-----------|------|-------------|
| JarvisState | `orchestration/state_engine.py` | Modify: add `interrupted_tasks` tracking + `dehydrate_task()` method |
| L3ContainerPool | `skills/spawn_specialist/pool.py` | Modify: add SIGTERM handler + interrupted task recovery loop |
| spawn_l3_specialist | `skills/spawn_specialist/spawn.py` | Modify: pass shutdown context to pool; inject `SHUTDOWN_SIGNAL_FILE` env var |
| entrypoint.sh | `docker/l3-specialist/entrypoint.sh` | Modify: trap SIGTERM for graceful container-side cleanup |
| MemoryClient | `orchestration/memory_client.py` | Modify: add `list_all()` + `delete()` + `update()` for health monitor |
| snapshot.py | `orchestration/snapshot.py` | Modify: `capture_semantic_snapshot()` returns delta relative to last-memorized commit |
| soul_renderer.py | `orchestration/soul_renderer.py` | Unchanged — L1 suggestion output writes to per-project soul-override.md |
| monitor.py | `orchestration/monitor.py` | Unchanged — CLI monitor reads state only; health + suggestions go to dashboard |
| occc dashboard | `workspace/occc/src/` | Modify: add memory health panel to `/memory` page; add suggestion panel to `/settings` page |

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENCLAW HOST (Ubuntu 24.04)                         │
│                                                                               │
│  ┌──────────────────┐    ┌──────────────────────────────────────────────┐   │
│  │  L1 ClawdiaPrime │    │  Orchestration Layer (Python)                 │   │
│  │  (L1 agent)      │    │                                               │   │
│  │                  │    │  pool.py ←──── SIGTERM handler                │   │
│  │  receives SOUL   │    │    │   dehydrate → state_engine.py            │   │
│  │  suggestions     │    │    │   recovery loop on restart               │   │
│  │  (suggestion_    │    │    │                                           │   │
│  │   engine.py)     │    │  suggestion_engine.py (NEW)                   │   │
│  └────────┬─────────┘    │    │   reads JarvisState patterns             │   │
│           │ CLI call     │    │   reads MemoryClient histories           │   │
│  ┌────────▼─────────┐    │    │   produces SOUL diff proposals           │   │
│  │  L2 PumplAI_PM   │    │                                               │   │
│  │  (L2 agent)      │    │  memory_health.py (NEW)                       │   │
│  └────────┬─────────┘    │    │   polls memU periodically                │   │
│           │ spawn        │    │   detects stale/conflicting items        │   │
│  ┌────────▼─────────┐    │    │   writes health report to state dir      │   │
│  │  pool.py         │    │                                               │   │
│  │  PoolRegistry    │    │  snapshot.py (MODIFIED)                       │   │
│  └────────┬─────────┘    │    │   delta-only diff vs last-memorized      │   │
│           │              │    │   hash stored in state_engine            │   │
│  ┌────────▼─────────────────────────────────────────────────────────┐   │   │
│  │  L3 Containers (openclaw-{project}-l3-{task_id})                 │   │   │
│  │  entrypoint.sh: trap SIGTERM → git stash + update_state         │   │   │
│  └─────────────────────────────────────────────────────────────────┘   │   │
│                                                                           │   │
│  ┌────────────────────────────────────────────────────────────────────┐  │   │
│  │  occc Next.js :6987                                                │  │   │
│  │  /memory page: memory health panel (stale/conflict badges)        │  │   │
│  │  /settings page: L1 suggestion panel (review/apply proposals)     │  │   │
│  └────────────────────────────────────────────────────────────────────┘  │   │
│                                                                            │   │
│  ┌────────────────────────────────────────────────────────────────────┐  │   │
│  │  memU Service (Docker: openclaw-net)                               │  │   │
│  │  memU-server :8765 ←──── health checks from memory_health.py      │  │   │
│  │  PostgreSQL+pgvector                                               │  │   │
│  └────────────────────────────────────────────────────────────────────┘  │   │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Integration Analysis

### Feature 1: Graceful Shutdown with Task Recovery

**Integration points:**

The SIGTERM originates at the host process level (pool.py runs inside the L2 agent process).
L3 containers are separate Docker processes that also need SIGTERM awareness.

**Two-path shutdown:**

```
Host SIGTERM received
    ↓
pool.py SIGTERM handler fires
    ├── Dehydrate in-flight tasks → state_engine.py: update status "interrupted"
    ├── Send SIGTERM to each active Docker container
    └── Wait up to 30s for containers to exit gracefully

L3 Container receives SIGTERM (from Docker stop or host relay)
    ↓
entrypoint.sh trap handler fires
    ├── git stash current changes (preserves partial work)
    ├── update_state "interrupted" via Python call
    └── exit 0 (clean exit — pool.py sees exit code 0 but status=interrupted)
```

**Recovery on restart:**

```
pool.py (or PoolRegistry) initialized
    ↓
read JarvisState.list_tasks_by_status("interrupted")
    ↓
for each interrupted task:
    - re-spawn with original task_description + skill_hint from state
    - set retry_count = 0 (fresh attempt)
    - log "recovered task {task_id} from interrupted state"
```

**State engine changes required:**

`state_engine.py` needs `interrupted` as a valid task status (currently not in the
terminal states set). The existing `update_task()` method handles it without code changes —
only the caller logic needs to understand the new status. However, `list_active_tasks()`
filters out `completed` and `failed` — `interrupted` should NOT be in terminal states so it
appears in active task lists for recovery.

**New method needed:** `list_tasks_by_status(status: str) -> List[str]` for recovery loop
to find exactly the interrupted tasks. Alternatively, `list_all_tasks()` already exists and
the recovery loop can filter by status client-side.

**Modified files:**
- `skills/spawn_specialist/pool.py` — SIGTERM handler, dehydration, recovery loop
- `docker/l3-specialist/entrypoint.sh` — `trap cleanup SIGTERM` before task execution
- `orchestration/state_engine.py` — `interrupted` status awareness (minor: add to docstring / status constants)

**New files:** None required. The recovery loop lives entirely in pool.py.

---

### Feature 2: Memory Health Monitoring

**Integration points:**

The health monitor is a periodic background service that reads memU inventory and applies
heuristics to detect problems. It is NOT in the hot path (spawn/monitor/review).

**Architecture decision: standalone module, not embedded in MemoryClient**

`orchestration/memory_health.py` (new) — runs either as a background thread started by
pool.py on init, or as a cron-style invocation from an occc API route. The simpler option
is an on-demand API route: dashboard calls `/api/memory/health` which runs the health check
synchronously and caches the result server-side for 5 minutes.

**Health checks:**

```
memory_health.py:

1. Connectivity check
   GET /health → memU initialized?

2. Stale memory detection
   GET all items for project → filter items older than staleness_threshold_days
   (staleness = item created_at far in the past + low retrieval score)

3. Conflict detection
   Semantic similarity scan: retrieve items with high cosine similarity but
   contradictory content (e.g., "always use X" vs "never use X")
   Strategy: group items by category → compare top-N pairs → flag similarity > 0.92

4. Volume check
   Count items per project → warn if > volume_warn_threshold (default: 500)

5. Orphaned items check
   Items scoped to project_ids that no longer exist in projects/ directory
```

**Health report storage:**

Write to `workspace/.openclaw/{project_id}/memory-health.json`:
```json
{
  "generated_at": 1234567890.0,
  "project_id": "pumplai",
  "status": "warning",
  "checks": {
    "connectivity": {"ok": true},
    "stale_items": {"count": 12, "ids": [...]},
    "conflicts": {"pairs": [{"id_a": "...", "id_b": "...", "similarity": 0.94}]},
    "volume": {"total": 347, "warn_at": 500}
  }
}
```

**Dashboard integration:**

Extend `/memory` page with a health banner (red/yellow/green) reading from
`/api/memory/health?project={id}`. Health check is on-demand + cached — no background
polling needed from the dashboard. The "manual override" UI is a delete button on flagged
items (already possible via existing `/api/memory` DELETE route from v1.3, or a new route
if that wasn't built).

**Modified files:**
- `orchestration/memory_client.py` — add `list_all(project_id)` + `delete(item_id)` methods
- `workspace/occc/src/app/api/memory/health/route.ts` — new route, on-demand + cached
- `workspace/occc/src/app/memory/page.tsx` — extend with health banner + flagged items panel

**New files:**
- `orchestration/memory_health.py` — health check logic, reads via MemoryClient

---

### Feature 3: L1 Strategic SOUL Suggestions

**Integration points:**

L1 (ClawdiaPrime) receives suggestions for modifying L2/L3 SOUL templates based on observed
task failure/success patterns. This is an analytical pipeline — reads patterns, produces
proposed diffs, surfaces them to L1 via dashboard. L1 reviews and applies.

**Architecture decision: suggestion engine as standalone orchestration module**

The suggestion engine does NOT modify SOUL files automatically. It proposes changes that
L1 reviews in the dashboard and explicitly approves. This preserves the human-in-loop
principle for SOUL evolution.

```
suggestion_engine.py (new):

Input sources:
  1. JarvisState.list_all_tasks() → task outcomes (completed/failed/timeout/retry_count)
  2. MemoryClient.retrieve(query="task failures") → L2 review decisions
  3. Task metadata: skill_hint, description patterns, retry frequency

Analysis:
  1. Failure pattern detection
     - Tasks with retry_count > 0 grouped by skill_hint + description keyword
     - Common failure log substrings extracted from activity_log entries

  2. Success pattern extraction
     - Tasks completed on first attempt grouped by characteristics
     - Extract what made them succeed (description structure, skill_hint)

  3. Suggestion generation
     - If skill=code failure rate > 30%: suggest SOUL amendment adding known pitfall
     - If review decisions show recurring rejection reason: suggest L3 SOUL clarity change
     - Output: list of SuggestionItem(section, current_text, proposed_text, confidence, evidence)

Output:
  workspace/.openclaw/{project_id}/soul-suggestions.json
  (JSON list of suggestion items, each with section, proposed_change, evidence, applied=false)
```

**Apply flow:**

```
Dashboard /settings page → L1 reviews suggestion list
    ↓
L1 clicks "Apply" on a suggestion
    ↓
POST /api/suggestions/apply {project_id, suggestion_id}
    ↓
API route calls soul_renderer.py logic to write to soul-override.md
  (using existing parse_sections() + merge_sections() pattern)
    ↓
soul-override.md updated → next L3 spawn picks it up via existing render_soul()
```

**This reuses the existing SOUL override mechanism entirely.** `soul_renderer.py` already
supports per-project `soul-override.md` via `merge_sections()`. Suggestions simply propose
additions or replacements to sections in that file.

**Modified files:**
- `workspace/occc/src/app/settings/page.tsx` — extend with suggestions panel (or new `/decisions` page if settings is already complex)
- `workspace/occc/src/app/api/suggestions/` — new route directory

**New files:**
- `orchestration/suggestion_engine.py` — pattern analysis + suggestion generation
- `workspace/occc/src/app/api/suggestions/route.ts` — list suggestions
- `workspace/occc/src/app/api/suggestions/apply/route.ts` — apply suggestion to soul-override.md

---

### Feature 4: Delta-Based Memory Snapshots

**Integration points:**

Currently `pool.py` memorizes the full `.diff` file (entire diff from default branch to
HEAD) after task completion. For long-running tasks with many commits, this diff grows large
and contains content already memorized from prior tasks.

**Problem:** The current snapshot in `snapshot.py` produces a diff from `{default_branch}...HEAD`,
which is the cumulative diff since the L3 branch was created. Each L3 task starts fresh
from a new staging branch, so the diff is naturally task-scoped already. The actual issue
is that the diff content passed to memU is the full file snapshot (including metadata
header), not a delta of what changed since the last memorize call.

**True delta scenario:**

Within a single task, if `pool.py` calls memorize at multiple checkpoints (currently it
does not — it calls once at completion), a delta would avoid re-memorizing unchanged parts.
The simpler interpretation is: **delta = only the new commits since the last memorize**,
useful when a task does multiple git commits during execution.

**Architecture decision: track last-memorized commit hash in state_engine**

```
state_engine.py:
  task entry gains optional field: "last_memorized_commit": "<sha>"

snapshot.py — new function:
  capture_delta_snapshot(task_id, workspace_path, project_id, since_commit=None):
    if since_commit:
      diff = git diff {since_commit}...HEAD  # delta since last memorize
    else:
      diff = git diff {default_branch}...HEAD  # full diff (first memorize)
    save to {task_id}-delta-{sha[:8]}.diff

pool.py — modified memorize path:
  sha = git rev-parse HEAD (sync call)
  last_sha = jarvis.read_task(task_id).get("last_memorized_commit")
  content = capture_delta_snapshot(task_id, ..., since_commit=last_sha)
  await memorize(content)
  jarvis.set_task_metric(task_id, "last_memorized_commit", sha)
```

**Practical impact:** For typical short tasks (single git commit), delta = full diff (no
change in behavior). For long tasks with multiple commits, delta reduces memorize payload
size. The bookkeeping cost is one extra `git rev-parse HEAD` call and one state engine write.

**Modified files:**
- `orchestration/snapshot.py` — add `capture_delta_snapshot()` function
- `orchestration/state_engine.py` — `last_memorized_commit` field in task metadata (no API change needed — `set_task_metric()` handles arbitrary keys)
- `skills/spawn_specialist/pool.py` — `_memorize_snapshot_fire_and_forget()` uses delta path

**New files:** None required.

---

## Component Boundaries

### New Components (create from scratch)

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `memory_health.py` | Periodic health checks: connectivity, stale item detection, conflict detection, volume warnings | `orchestration/memory_health.py` |
| `suggestion_engine.py` | Pattern analysis from JarvisState + memU, produces SuggestionItem proposals for SOUL evolution | `orchestration/suggestion_engine.py` |
| Memory Health API route | On-demand health check endpoint, 5min server-side cache | `workspace/occc/src/app/api/memory/health/route.ts` |
| Suggestions API routes | List suggestions + apply-to-soul-override endpoint | `workspace/occc/src/app/api/suggestions/route.ts` + `apply/route.ts` |

### Modified Components (surgical changes only)

| Component | What Changes | Risk |
|-----------|-------------|------|
| `skills/spawn_specialist/pool.py` | SIGTERM handler registration; dehydration call; recovery loop on init; delta snapshot path in `_memorize_snapshot_fire_and_forget()` | MEDIUM — async signal handling in Python needs care |
| `docker/l3-specialist/entrypoint.sh` | Add `trap cleanup_handler SIGTERM` before task execution; `cleanup_handler` stashes + updates state | LOW — bash trap is well-understood |
| `orchestration/state_engine.py` | Add `interrupted` to status docstring; `list_tasks_by_status()` helper method | LOW — additive only |
| `orchestration/snapshot.py` | Add `capture_delta_snapshot()` alongside existing `capture_semantic_snapshot()` | LOW — new function, existing function unchanged |
| `orchestration/memory_client.py` | Add `list_all()` (paginated GET /memories) + `delete(item_id)` (DELETE /memories/{id}) methods | LOW — additive |
| `workspace/occc/src/app/memory/page.tsx` | Add health banner section reading from `/api/memory/health` | LOW — additive |
| `workspace/occc/src/app/settings/page.tsx` | Add SOUL suggestions panel (or `/decisions/page.tsx` if settings is overcrowded) | LOW — additive |

---

## Data Flows

### Flow 1: Graceful Shutdown

```
SIGTERM → host process (pool.py event loop)
    ↓
asyncio signal handler: set shutdown_event
    ↓
for each task_id in self.active_containers:
    container.kill(signal="SIGTERM")
    jarvis.update_task(task_id, "interrupted", "SIGTERM received, container signalled")
    ↓
wait up to 30s for containers.wait() to return
    ↓
remaining containers: force-remove
    ↓
process exits cleanly

L3 container receives SIGTERM:
    ↓
entrypoint.sh trap: git stash push -m "interrupted-{TASK_ID}"
    ↓
python update_state(TASK_ID, "interrupted", "SIGTERM received")
    ↓
exit 0

On next pool.py startup:
    ↓
jarvis.list_all_tasks() → filter status == "interrupted"
    ↓
for each interrupted task: re-submit to pool as new spawn
    (original task_description + skill_hint preserved in state metadata)
```

### Flow 2: Memory Health Check

```
Dashboard loads /memory page
    ↓
GET /api/memory/health?project=pumplai
    ↓
API route checks cache (< 5 min old): return cached if fresh
    ↓
Cache miss: call memory_health.run_checks(project_id)
    ├── memory_client.health() → connectivity status
    ├── memory_client.list_all(project_id) → all items
    │   ├── flag items with age > staleness_days
    │   └── run similarity scan on top-N items for conflicts
    └── count total items → volume warning
    ↓
Write health-report.json to .openclaw/{project_id}/
    ↓
Return HealthReport to API route → cache → return to dashboard
    ↓
Dashboard renders: green/yellow/red banner + flagged items list
User clicks delete on flagged item:
    ↓
DELETE /api/memory/{item_id}?project=pumplai
    ↓
memory_client.delete(item_id)
```

### Flow 3: L1 Strategic Suggestion

```
L1 or operator triggers suggestion analysis
    ↓
GET /api/suggestions/run?project=pumplai
    ↓
suggestion_engine.analyze(project_id):
    ├── read JarvisState.list_all_tasks() → task outcomes + retry counts
    ├── memory_client.retrieve("task failures patterns") → L2 decisions
    └── pattern analysis → List[SuggestionItem]
    ↓
Write soul-suggestions.json to .openclaw/{project_id}/
    ↓
GET /api/suggestions?project=pumplai → returns pending suggestions
    ↓
Dashboard /settings page renders suggestion list
    ↓
L1 reviews, clicks "Apply" on accepted suggestion
    ↓
POST /api/suggestions/apply {project_id, suggestion_id}
    ↓
API route: read soul-override.md (or empty if missing)
    parse_sections() + merge_sections() with new/modified section
    write updated soul-override.md
    mark suggestion as applied in soul-suggestions.json
    ↓
Next L3 spawn: render_soul() picks up updated soul-override.md automatically
```

### Flow 4: Delta Memory Snapshot

```
Task completes in pool.py _attempt_task()
    ↓
asyncio.create_task(_memorize_snapshot_fire_and_forget(...))
    ↓
Read last_memorized_commit from JarvisState task metadata
    ↓
snapshot.capture_delta_snapshot(task_id, workspace, project_id, since_commit)
    ├── if since_commit is None: full diff (first memorize, existing behavior)
    └── if since_commit set: git diff {since_commit}...HEAD (delta only)
    ↓
Build memorize payload with delta content (smaller if multi-commit task)
    ↓
MemoryClient.memorize(delta_content)
    ↓
On success: jarvis.set_task_metric(task_id, "last_memorized_commit", current_sha)
```

---

## Build Order (Phase Dependencies)

The four features are largely independent — they touch different parts of the system. This
ordering minimizes risk by building foundational changes before dependent features.

```
Phase 1: Graceful Shutdown — SIGTERM handling
  WHY FIRST: Foundational reliability; required before long-running production use.
  Touches: pool.py, entrypoint.sh, state_engine.py (minor)
  Test: send SIGTERM to pool process → verify interrupted state in state.json → verify recovery spawns on next start
  No dependencies on other v1.4 features.

Phase 2: Delta Snapshots — snapshot.py + pool.py memorize path
  WHY SECOND: Pure backend optimization; no dashboard needed; verifiable with existing tools.
  Touches: snapshot.py (new function), pool.py (memorize path), state_engine.py (last_memorized_commit metric)
  Test: spawn task with multiple commits → verify delta diff is smaller than full diff → verify memU item contains only new changes
  Depends on: nothing (but builds on Phase 1 pool.py changes — schedule after Phase 1 to avoid merge conflicts)

Phase 3: Memory Health Monitor
  WHY THIRD: Backend logic + API + minimal dashboard. Self-contained.
  Touches: memory_client.py (list_all, delete), memory_health.py (new), /api/memory/health route (new), /memory page (extend)
  Test: inject a stale item → health check flags it → dashboard shows yellow banner → delete removes it
  Depends on: existing memU service (v1.3 already shipped)

Phase 4: L1 Strategic Suggestions
  WHY LAST: Requires task history data (Phase 1 ensures clean history), benefits from
  delta snapshots (Phase 2 means cleaner memory items), and is the highest-complexity feature.
  Touches: suggestion_engine.py (new), /api/suggestions routes (new), /settings page (extend)
  Test: run several tasks with failures → generate suggestions → apply suggestion → verify soul-override.md updated
  Depends on: existing JarvisState task history, existing MemoryClient, existing soul_renderer.py
```

---

## Architectural Patterns

### Pattern 1: Async Signal Handling in pool.py

**What:** Register SIGTERM handler via `asyncio.get_event_loop().add_signal_handler()` to
set a `shutdown_event`. Spawn coroutine checks the event after each container exit.

**Why not `signal.signal()`:** The existing pool.py is fully asyncio — mixing sync signal
handlers with async code causes race conditions on Python <3.12. The asyncio API is safe.

**Example:**
```python
# pool.py __init__ or startup
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(_shutdown(loop)))

async def _shutdown(loop):
    logger.info("SIGTERM received — initiating graceful shutdown")
    for task_id, container in list(self.active_containers.items()):
        container.kill(signal="SIGTERM")
        jarvis.update_task(task_id, "interrupted", "SIGTERM received")
    # Give containers 30s to exit
    await asyncio.sleep(30)
    loop.stop()
```

**Trade-offs:** Simple and well-understood. Does not handle SIGKILL (unclean kill). Recovery
loop handles the gap — interrupted tasks are re-queued on next start.

### Pattern 2: On-Demand Health Check with Server-Side Cache

**What:** `/api/memory/health` route runs health checks on first call, caches result in
module-level variable with timestamp, returns cached result for 5 minutes.

**Why not background polling:** Background polling requires a persistent server process or
cron — adds operational complexity. On-demand is sufficient for health monitoring use case.
The dashboard only shows health when the user views the `/memory` page.

**Example:**
```typescript
// route.ts
let _healthCache: { report: HealthReport; ts: number } | null = null

export async function GET(req: Request) {
  const now = Date.now()
  if (_healthCache && now - _healthCache.ts < 5 * 60 * 1000) {
    return Response.json(_healthCache.report)
  }
  const report = await runHealthChecks(project)
  _healthCache = { report, ts: now }
  return Response.json(report)
}
```

### Pattern 3: Suggestion-as-File (not DB)

**What:** `soul-suggestions.json` lives in the project state directory alongside
`workspace-state.json`. Suggestions are immutable once generated — applying one marks it
`applied: true` rather than deleting it (audit trail).

**Why:** Consistent with the existing pattern of JSON files in `.openclaw/{project_id}/`.
No new storage dependency. Suggestions are project-scoped and few in number (< 50 expected).

### Pattern 4: Delta by Default, Full on First

**What:** `capture_delta_snapshot()` checks `last_memorized_commit`. If none, produces full
diff (matching existing behavior exactly). If set, produces `git diff {sha}...HEAD`.

**Why:** Zero behavioral change for existing single-commit tasks. Multi-commit tasks get the
optimization automatically. No configuration required.

---

## Anti-Patterns

### Anti-Pattern 1: Modifying SOUL Files Without L1 Review

**What people do:** `suggestion_engine.py` automatically writes to `soul-override.md` when
confidence is high.
**Why it's wrong:** SOUL mutations affect every subsequent task. Automated changes without
review can compound — one bad suggestion affects all future L3 spawns until manually reverted.
**Do this instead:** Always write to `soul-suggestions.json` with `applied: false`. L1 clicks
Apply in the dashboard. The Apply API route writes to `soul-override.md`. Audit trail preserved.

### Anti-Pattern 2: Blocking Pool Shutdown on Container Completion

**What people do:** SIGTERM handler waits indefinitely for all containers to complete their
current task before shutting down.
**Why it's wrong:** A task that hung before SIGTERM will hang the shutdown too. The pool
process becomes unkillable.
**Do this instead:** Dehydrate task state immediately on SIGTERM. Give containers 30s with
SIGTERM, then force-remove. Recovery loop handles the rest on restart.

### Anti-Pattern 3: Running Similarity Scan on All Memory Items

**What people do:** Conflict detection loads all memory items and runs pairwise cosine
similarity O(n²).
**Why it's wrong:** At 500 items, that is 125,000 comparisons — called every time the health
page loads.
**Do this instead:** Scope conflict scan to the most recent N items (default 50) within each
category. Use memU's existing `/retrieve` semantic search to find items similar to known
conflict seeds rather than exhaustive pairwise scan.

### Anti-Pattern 4: Re-memorizing Full Diff on Every Checkpoint

**What people do:** Call memorize multiple times during a task, each time with the full
`{default_branch}...HEAD` diff.
**Why it's wrong:** Each subsequent memorize includes all content from prior memorizations.
memU deduplicates by content hash but still pays the embedding cost for every call.
**Do this instead:** Delta snapshots — only the new commits since `last_memorized_commit`.
The state engine tracks the SHA so each memorize payload contains only net-new information.

---

## File Structure Delta (New Files Only)

```
orchestration/
├── memory_health.py          # NEW: stale/conflict/volume health checks
└── suggestion_engine.py      # NEW: pattern analysis, SuggestionItem generation

workspace/occc/src/app/
├── api/
│   ├── memory/
│   │   └── health/
│   │       └── route.ts      # NEW: on-demand health check endpoint
│   └── suggestions/
│       ├── route.ts           # NEW: GET list, POST generate
│       └── apply/
│           └── route.ts      # NEW: POST apply suggestion to soul-override.md
└── settings/                  # EXISTS: extend page.tsx with suggestions panel
    └── page.tsx               # MODIFY: add SuggestionsPanel component

workspace/occc/src/components/
├── memory/
│   └── HealthBanner.tsx       # NEW: green/yellow/red health status
└── suggestions/
    └── SuggestionsList.tsx    # NEW: suggestion review/apply UI
```

---

## Integration Points Summary

| Feature | New Files | Modified Files | Untouched |
|---------|-----------|----------------|-----------|
| Graceful Shutdown | none | `pool.py`, `entrypoint.sh`, `state_engine.py` (minor) | `spawn.py`, `snapshot.py`, `memory_client.py` |
| Delta Snapshots | none | `snapshot.py` (+function), `pool.py` (memorize path), `state_engine.py` (metric key) | `memory_client.py`, `entrypoint.sh`, dashboard |
| Memory Health | `memory_health.py`, `api/memory/health/route.ts`, `HealthBanner.tsx` | `memory_client.py` (+methods), `memory/page.tsx` | `pool.py`, `state_engine.py`, `snapshot.py` |
| L1 Suggestions | `suggestion_engine.py`, `api/suggestions/` routes, `SuggestionsList.tsx` | `settings/page.tsx` | `soul_renderer.py` (reused as-is), `memory_client.py`, `pool.py` |

---

## Scaling Considerations

This remains a single-host system. v1.4 scaling concerns:

| Concern | Current Scale | Notes |
|---------|---------------|-------|
| SIGTERM recovery storm | Restart after kill → all interrupted tasks re-queued simultaneously | Stagger recovery with `asyncio.sleep(0)` yield between spawns; pool semaphore already limits concurrency |
| Suggestion analysis cost | list_all_tasks() on large state files | JarvisState.list_all_tasks() reads full state.json — consider task count limit (e.g., last 500 tasks) for suggestion analysis |
| Health check latency | list_all() from memU at 500+ items | Server-side cache (5min) prevents hammering; scope scan to last 50 items per category |
| soul-suggestions.json growth | Accumulates applied suggestions | Add `max_suggestions` cap (e.g., 100); archive older applied suggestions |

---

## Sources

- OpenClaw codebase: `skills/spawn_specialist/pool.py`, `orchestration/state_engine.py`, `orchestration/snapshot.py`, `docker/l3-specialist/entrypoint.sh`, `orchestration/memory_client.py`, `orchestration/soul_renderer.py`
- PROJECT.md: v1.4 feature definitions + out-of-scope constraints
- Python asyncio signal docs: `loop.add_signal_handler()` for safe async SIGTERM handling

---

*Architecture research for: OpenClaw v1.4 Operational Maturity*
*Researched: 2026-02-24*
