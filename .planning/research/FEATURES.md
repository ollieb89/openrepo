# Feature Research

**Domain:** AI swarm orchestration — v1.4 Operational Maturity
**Researched:** 2026-02-24
**Confidence:** HIGH (codebase analysis + verified patterns from official sources)

---

## Context: What This Milestone Adds

v1.3 shipped full agent memory (memU, bidirectional pipeline, SOUL injection, dashboard). The system
now learns across tasks. v1.4 hardens the system for production autonomy by addressing four gaps:

1. **Graceful shutdown** — L3 containers currently have no SIGTERM handler; killed containers leave
   tasks stuck in `in_progress` forever
2. **Memory health** — accumulated memories can go stale, conflict, or contain hallucinated facts;
   no current mechanism to detect or correct this
3. **L1 SOUL suggestions** — pattern extraction from failures is stored in memU but never surfaces
   as actionable SOUL improvements; humans must manually review and edit
4. **Delta snapshots** — every pre-spawn retrieval does a full memU query even when nothing new has
   been memorized since the last spawn

All four features build directly on the v1.3 infrastructure. None require new external services.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that production-grade container orchestration must provide. Missing them makes the system
feel unfinished for anything beyond demos.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| SIGTERM handler in L3 entrypoint | Any production container process must handle graceful shutdown — Docker sends SIGTERM before SIGKILL, default grace is 10s. Unhandled SIGTERM = SIGKILL after 10s, state permanently `in_progress` | LOW | `entrypoint.sh` has `set -euo pipefail` but no `trap` — 5-line bash addition to write `interrupted` status to Jarvis state before exit |
| Interrupted task recovery scan | On pool/L2 restart, tasks stuck in `in_progress` or `starting` beyond their skill timeout must be resolved (mark `failed` or auto-retry). Without this, dead tasks block pool slots and confuse the dashboard | MEDIUM | Pool startup hook: scan JarvisState for stale in-flight tasks using `updated_at` + skill timeout threshold |
| Memory health visibility | Dashboard should surface whether memory service is reachable and whether the memory store has quality issues. Silent failure is confusing and erodes trust | LOW | `MemoryClient.health()` already exists — dashboard badge is a straightforward extension of the existing `/memory` page |
| Per-project stale memory flagging | Operators need to know which memories are old and possibly outdated, not just that the store is healthy | MEDIUM | Age-based scoring against a configurable `health_stale_days` threshold; surface flagged memories in dashboard |

### Differentiators (Competitive Advantage)

Features that distinguish OpenClaw's approach to self-improving agent orchestration.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Automated memory conflict detection | Identifies memories that contradict each other using pgvector similarity — prevents mutually inconsistent context from being injected into future L3 tasks | MEDIUM | Pairwise cosine similarity query on all project memories; flag pairs with similarity 0.75-0.91 and opposing verdicts. pgvector already installed and indexed |
| Manual memory override UI | Operator can edit the content of a suspicious memory entry to correct it rather than deleting and re-memorizing — maintains audit trail | MEDIUM | Extends existing `/memory` page; requires new `PUT /memories/:id` endpoint in the memory service router |
| L1 SOUL suggestion engine | L1 (ClawdiaPrime) analyzes clustered rejection patterns in memU and generates concrete, reviewable additions to the L3 SOUL template — closes the loop from task failure to behavioral change | HIGH | Three new components: (1) pattern extractor queries memU for rejection clusters, (2) suggestion formatter produces diff-style SOUL amendments, (3) L2 acceptance flow writes accepted suggestions to `soul-override.md` |
| Delta memory retrieval | Track `last_memory_retrieval_at` cursor per project in state.json metadata; pre-spawn retrieval fetches only memories newer than that timestamp instead of re-querying the full store on every spawn | MEDIUM | Small state schema addition + `since` filter parameter on memU `/retrieve`. Delivers measurable latency reduction for projects with high task frequency |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-apply L1 SOUL suggestions without L2 approval | Seems like full autonomy, reduces operator burden | SOUL changes govern all future L3 tasks — incorrect suggestions silently degrade quality across the project with no rollback without version history | L1 generates suggestions as reviewable diffs; L2 confirms before writing to `soul-override.md`. The existing SOUL mechanism already supports this flow |
| Time-based automatic memory garbage collection | "Clean up stale memories" sounds like good hygiene | Recency bias — old memories about project conventions (coding style, branch naming rules) remain valid indefinitely. Time-based purge deletes institutional knowledge | Flag suspicious memories (conflict score + age) for manual review; never auto-delete by time alone. Operators choose what to remove |
| Real-time conflict alerts on every memory write | Immediate notification when conflicting memories are detected | Scanning full store on every memorize call is expensive; false positives on similar-but-valid memories create alert fatigue | Batch health scan triggered on demand or by memory count threshold; surface in dashboard as a badge count, not a live alert |
| Cross-project memory health aggregation | Single view across all projects | Breaks per-project isolation (core security design); creates cross-contamination risk | Per-project health view is correct; a summary report can be added later as an explicit opt-in |
| Snapshot file compression / binary format | Reduce disk usage | `.diff` files are already small and human-readable for L2 review — compression destroys debuggability for marginal gain | `cleanup_old_snapshots()` with configurable `max_snapshots` is sufficient; add per-project configurable retention limit |
| Full re-retrieval on every spawn regardless of cursor | Simpler code path, always fresh | For a project with 200+ memories and 10 tasks/day, this is 2,000 full semantic searches/day for no new information. Latency compounds at pool saturation | Delta retrieval with cursor; first spawn of session does full fetch, subsequent spawns fetch only new memories |

---

## Feature Dependencies

```
[SIGTERM handler in entrypoint.sh]
    └──enables──> [Task dehydration: write "interrupted" to Jarvis state]
                      └──enables──> [Recovery loop distinguishes "interrupted" from "in_progress"]

[Interrupted task recovery loop]
    └──independent of──> [SIGTERM handler] (handles SIGKILL, host reboot, pool crash regardless)
    └──requires──> [JarvisState.list_all_tasks() + task updated_at timestamps] (both already exist)

[Delta memory retrieval]
    └──requires──> [last_memory_retrieval_at cursor in state.json metadata]
    └──requires──> [since= filter on memU /retrieve] (new endpoint parameter)
    └──independent of──> [Memory health monitoring]

[Memory health scan]
    └──requires──> [memU /memories?user_id= list endpoint] (already exists in memory service)
    └──requires──> [pgvector similarity query] (already installed and indexed)
    └──enables──> [Memory health dashboard UI with conflict/staleness badges]
    └──enables──> [Manual memory override UI]
    └──enables (feeds data to)──> [L1 SOUL suggestion engine]

[Manual memory override UI]
    └──requires──> [PUT /memories/:id endpoint] (new endpoint in memory_service)
    └──requires──> [Memory health scan] (identifies which memories to surface)

[L1 SOUL suggestion engine]
    └──requires──> [Memory health scan patterns] (rejection clusters come from memU)
    └──requires──> [soul-override.md per project] (already exists — L2 writes here)
    └──requires──> [New soul_suggestion directive type] (new L1→L2 message type)
    └──requires──> [L2 suggestion acceptance flow] (L2 side of the directive)
```

### Dependency Notes

- **SIGTERM handler is a 5-line bash change** — lowest cost, highest safety value. The `trap` handler calls `update_state "interrupted"` which already exists. Builds on nothing new.

- **Recovery loop is independent of SIGTERM handler** — even without SIGTERM handling, the recovery loop resolves tasks orphaned by SIGKILL, host reboot, or pool process death. Both are needed; neither depends on the other.

- **Delta retrieval requires a small memU router change** — `docker/memory/memory_service/routers/retrieve.py` needs a `created_after` filter parameter. The existing `where` dict in the POST body is the natural place to add it. This is internal to the memory service and does not affect the external API contract.

- **Memory health scan is prerequisite for L1 suggestions** — the suggestion engine clusters rejection patterns from memU data; health scan provides the query interface and scoring infrastructure it reuses. Build health scan first, L1 suggestions second.

- **L1 suggestions are the highest-complexity feature** — they span four components (soul_suggester.py, directive type, L2 acceptance flow, dashboard surface). Build last; the other three features are independently valuable without it.

---

## MVP Definition

### Launch With (v1.4 core — must ship for "Operational Maturity" to be true)

- [ ] SIGTERM handler + task dehydration — `trap` in `entrypoint.sh`, `update_state "interrupted"` before exit. Addresses deferred REL-04/REL-05.
- [ ] Interrupted task recovery loop — scan on pool startup (or explicit trigger), mark stale in-flight tasks `failed`, log with task details. Addresses REL-06/REL-07.
- [ ] Memory health scan (Python module) — batch scan for staleness + conflict flags, returns scored list of suspicious entries. No UI yet, just the scan logic.
- [ ] Memory health dashboard UI — extend `/memory` page with health badges, staleness indicators, conflict pair display, manual override (edit + dismiss flag). Requires `PUT /memories/:id` endpoint.
- [ ] Delta memory retrieval — `last_memory_retrieval_at` cursor in state.json; `since` filter on memU retrieve; spawn.py passes cursor and updates it after successful injection. Addresses deferred PERF-05/PERF-06.

### Add After Validation (v1.4 extension)

- [ ] L1 SOUL suggestion engine — pattern extraction, suggestion format, L2 acceptance flow. Build after health scan proves the rejection pattern data is reliable. Addresses deferred ADV-01.

### Future Consideration (v2+)

- [ ] Cross-project health aggregation — defer until multi-project operator workflows are more common.
- [ ] SOUL versioning / automatic rollback — would require git-tracking `soul-override.md`; useful but exceeds v1.4 scope.
- [ ] TTL / forgetting policies — memory volume not yet high enough to need automatic expiry.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SIGTERM handler + dehydration | HIGH — prevents stuck tasks, mandatory for production | LOW — 5-line bash trap | P1 |
| Interrupted task recovery loop | HIGH — handles pool restart without manual intervention | MEDIUM — startup scan in pool.py | P1 |
| Memory health scan (Python) | HIGH — prevents quality degradation from stale/conflicting memories | MEDIUM — pgvector similarity query + age scoring | P1 |
| Memory health dashboard UI | MEDIUM — operator visibility and correction workflow | MEDIUM — extends `/memory` page + new PUT endpoint | P1 |
| Delta memory retrieval | MEDIUM — latency reduction at scale, correctness at high task frequency | MEDIUM — cursor in state.json + memU filter | P2 |
| L1 SOUL suggestion engine | HIGH long-term — self-improving agents without manual intervention | HIGH — multi-component, new directive type | P2 |

**Priority key:**
- P1: Must have for v1.4 to honestly be called "Operational Maturity"
- P2: Should have — defines the milestone's differentiating value
- P3: Nice to have, future consideration

---

## Detailed Feature Behavior: Expected Patterns

### 1. Graceful Container Shutdown with Task State Dehydration/Rehydration

**Standard pattern (verified):** Docker sends SIGTERM to PID 1. Process has `stop_grace_period`
(default 10s) to clean up before SIGKILL. `entrypoint.sh` is PID 1 in L3 containers.

**Dehydration — what happens on SIGTERM:**

```bash
# Add to entrypoint.sh before the CLI runtime call:
_handle_signal() {
  update_state "interrupted" "SIGTERM received — container shutting down gracefully"
  # Kill the CLI runtime subprocess if it's running
  if [[ -n "${CLI_PID:-}" ]]; then
    kill -TERM "$CLI_PID" 2>/dev/null || true
  fi
  exit 143  # 128 + 15 (SIGTERM)
}
trap '_handle_signal' SIGTERM SIGINT

# Run CLI runtime in background to capture its PID:
"${CLI_RUNTIME}" "${SOUL_ARGS[@]}" --task "${TASK_DESCRIPTION}" &
CLI_PID=$!
wait "$CLI_PID"
EXIT_CODE=$?
```

**State after dehydration:**
```json
{
  "status": "interrupted",
  "activity_log": [
    { "timestamp": 1708776000, "status": "interrupted", "entry": "SIGTERM received — container shutting down gracefully" }
  ],
  "updated_at": 1708776000
}
```

**Rehydration (recovery loop) — what happens on pool restart:**

`pool.py` calls `scan_interrupted_tasks(project_id)` on startup:
1. Read all tasks via `JarvisState.list_all_tasks()`
2. For each task with `status in ("interrupted", "in_progress", "starting")`:
   - Check `updated_at` — if older than `skill_timeout` seconds, task is orphaned
   - Apply recovery policy from `project.json l3_overrides.recovery_policy`:
     - `"mark_failed"` (default — safe): call `update_task(task_id, "failed", "Recovered: task orphaned")`
     - `"auto_retry"`: call `spawn_and_monitor()` with original task params from metadata
     - `"manual"`: emit a structured warning log; leave for operator
3. Log scan results at INFO level

**Implementation touch points:**
- `docker/l3-specialist/entrypoint.sh` — add trap handler
- `skills/spawn_specialist/pool.py` — add `scan_interrupted_tasks()` + call in `PoolRegistry.get_pool()` or as explicit `pool.recover_orphans()` method
- `projects/<id>/project.json l3_overrides` — add optional `recovery_policy` field

**Confidence:** HIGH — bash trap semantics are stable and well-documented; JarvisState write path is unchanged.

---

### 2. Memory Health Monitoring

**Problem:** memU accumulates memories across all L3 task outcomes and L2 review decisions. After
weeks of operation, some entries become stale (project switched from library X to Y), contradictory
(two task outcomes contradict each other on the same pattern), or orphaned (reference a task ID that
no longer exists in state.json). These degrade the quality of future SOUL injections.

**Detection heuristics (practical, no LLM required):**

| Flag | Condition | Query |
|------|-----------|-------|
| `possibly_stale` | `created_at` older than `health_stale_days` (configurable, default 30) | Filter by `user_id` + `created_at < threshold` |
| `possible_duplicate` | Cosine similarity > 0.92 to another memory in same project | pgvector `<=>` operator on embedding column |
| `possible_conflict` | Cosine similarity 0.75–0.91 AND different `category` verdict field | pgvector range query + category join |
| `orphaned` | `resource_url` references a `task_id` not in current state.json | Cross-reference scan, offline |

**Health scan output format:**
```python
{
  "project_id": "pumplai",
  "scanned_at": "2026-02-24T12:00:00Z",
  "total_memories": 142,
  "healthy": 128,
  "flags": [
    {
      "memory_id": "abc123",
      "flag": "possible_conflict",
      "conflicting_memory_id": "def456",
      "similarity_score": 0.83,
      "created_at": "2026-02-10T...",
      "recommendation": "Review both entries; keep the newer one if they contradict"
    }
  ]
}
```

**Dashboard UI behavior:**
- Flagged memories show a warning badge in the existing `/memory` browse list
- Clicking a flag opens a side panel showing: the memory content, the conflicting memory content (for conflict flags), similarity score, creation date
- Actions available: Delete one, Edit (update content), Dismiss flag (records a `flag_dismissed` reason)
- Edit action calls new `PUT /memories/:id` endpoint with `{ "resource_url": "<new_content>" }`

**New endpoint required:**
```
PUT /memories/:id
Body: { "resource_url": string }
Response: 200 OK | 404 Not Found | 422 Unprocessable
```

This goes in `docker/memory/memory_service/routers/memories.py` alongside the existing `DELETE` handler.

**Confidence:** MEDIUM — the pgvector similarity query is supported; specific thresholds (0.75, 0.92) are reasonable starting points backed by the HaluMem paper's findings on memory conflict detection but will need empirical tuning.

---

### 3. L1 Proactive SOUL Template Suggestions

**Problem:** L3 agents repeatedly make the same mistakes that get memorized as rejections but never
feed back into the SOUL that governs future L3 behavior. A human must manually review rejection
patterns and hand-edit `soul-override.md`.

**Expected behavior:**

1. `orchestration/soul_suggester.py` runs as an L1-triggered analysis:
   - Query memU for all `review_decision` memories with `verdict=reject` for the project
   - Cluster similar rejections by semantic embedding (cosine similarity > 0.80)
   - For each cluster with ≥3 members, identify the common failure pattern from the `reasoning` field
   - Generate a concrete SOUL amendment:
     ```
     ## Suggested SOUL Amendment
     PATTERN: L3 repeatedly forgets to run tests before committing (4 instances)
     EXAMPLE: "Rejected: code changed but no tests updated or run"
     SUGGESTED ADDITION to soul-override.md:
     > After completing code changes, always run the project test suite (e.g., `uv run pytest`)
     > before staging any commits. Untested commits will be rejected.
     ```

2. L1 sends suggestion as directive of new type `soul_suggestion` to L2:
   - Suggestion includes: pattern description, evidence count, exact text to add to SOUL
   - L2 receives directive, presents the suggestion (logs it, writes to a pending suggestions file)

3. L2 acceptance flow:
   - L2 reads pending suggestions from `workspace/.openclaw/<project_id>/soul-suggestions.json`
   - For each suggestion: `accept` (append to `soul-override.md` + re-render SOUL via `soul_renderer.py`) or `reject` (memorize the rejection with reason)

4. On next spawn after acceptance, the augmented SOUL is injected into new L3 containers.

**Threshold:** ≥3 similar rejections within `suggestion_lookback_days` (default 30). Below threshold, L1 accumulates but does not interrupt L2.

**Implementation components:**
- `orchestration/soul_suggester.py` — new file; pattern extraction + suggestion generation
- `orchestration/soul_renderer.py` — read `soul-suggestions.json` pending file (minor extension)
- `skills/router_skill/` or new trigger mechanism for L1 analysis
- `workspace/occc/src/app/settings/` or `/memory` dashboard — surface pending suggestions to operator

**Confidence:** MEDIUM — pattern extraction and clustering are well-understood; the cluster quality depends on memU embedding quality which is untested at this scale. The suggestion format and directive type are new design decisions.

---

### 4. Delta-Based Memory Snapshots

**Problem:** `_retrieve_memories_sync()` in `spawn.py` does a full semantic search against all
project memories on every L3 spawn, even when nothing new has been memorized since the last spawn.
For a project with 100+ memories and multiple tasks running per day, this is wasteful.

**Expected behavior:**

**State schema addition** (backward-compatible — missing key = full fetch):
```json
{
  "metadata": {
    "created_at": ...,
    "last_updated": ...,
    "memory_cursors": {
      "pumplai": "2026-02-24T10:00:00Z"
    }
  }
}
```

**Pre-spawn retrieval flow with delta:**
1. Read `memory_cursors[project_id]` from state metadata (None if not set → full fetch)
2. If cursor exists, call `/retrieve` with `where: { user_id: project_id, created_after: cursor }`
3. If delta is non-empty, merge with cached context from last full fetch (up to 2,000-char budget)
4. If delta is empty, reuse last soul file if it exists, or use base SOUL without memory augmentation
5. After successful injection, update `memory_cursors[project_id]` = current ISO timestamp via `JarvisState.set_task_metric()`

**memU retrieve endpoint change** (`docker/memory/memory_service/routers/retrieve.py`):
```python
# Add to RetrieveRequest model:
created_after: Optional[str] = None  # ISO 8601 timestamp

# Add to WHERE clause construction:
if request.created_after:
    where["created_after"] = request.created_after
```

**Tradeoff:** First spawn of a session does a full fetch (cache cold). Subsequent spawns fetch only
new memories. For short sessions (1-2 tasks), gain is minimal. For pipelines (10+ tasks/day), gain
is proportional to task count. The primary value is reducing latency at the pool saturation boundary.

**Fallback behavior:** On any error reading the cursor or filtering by `since`, fall through to full
fetch. Delta is a performance optimization, not a correctness requirement.

**Confidence:** HIGH — cursor-based retrieval is a standard event-sourcing pattern; the memU filter
extension is small and the fallback path preserves correct behavior.

---

## Existing Integration Points (v1.3 foundations v1.4 builds on)

| v1.3 Component | v1.4 Usage |
|----------------|------------|
| `JarvisState.update_task()` | Dehydration writes `interrupted` status on SIGTERM |
| `JarvisState.list_all_tasks()` | Recovery loop reads all tasks to find orphans |
| `JarvisState.set_task_metric()` | Cursor `last_memory_retrieval_at` stored here |
| `MemoryClient.health()` | Dashboard health indicator badge |
| `MemoryClient.retrieve()` | Health scan conflict detection query |
| `_retrieve_memories_sync()` in spawn.py | Extended with `since` parameter for delta retrieval |
| `pool._attempt_task()` | Recovery loop's `auto_retry` policy calls this |
| `l2_reject_staging()` in snapshot.py | Rejection memories are the source for L1 suggestion patterns |
| `soul-override.md` per project | L1 suggestion acceptance writes here |
| `/memory` dashboard page | Extended with health flags, staleness badges, override UI |
| `docker/memory/memory_service/routers/memories.py` | New `PUT /memories/:id` handler added |
| `docker/memory/memory_service/routers/retrieve.py` | `created_after` filter added for delta |

---

## Sources

- [HaluMem: Evaluating Hallucinations in Memory Systems of Agents (arXiv 2025)](https://arxiv.org/pdf/2511.03506)
- [Memory in the Age of AI Agents (arXiv 2025)](https://arxiv.org/abs/2512.13564)
- [SCOPE: Prompt Evolution for Enhancing Agent Effectiveness (arXiv 2025)](https://arxiv.org/html/2512.15374v1)
- [Multi-Agent Design: Optimizing Agents with Better Prompts and Topologies (arXiv 2025)](https://arxiv.org/html/2502.02533v1)
- [Docker Container Graceful Shutdown Patterns (oneuptime 2026)](https://oneuptime.com/blog/post/2026-01-16-docker-graceful-shutdown-signals/view)
- [Orchestration Dehydration and Rehydration — BizTalk Pattern (Microsoft Learn)](https://learn.microsoft.com/en-us/biztalk/core/orchestration-dehydration-and-rehydration)
- [Self-Evolving Agents — Autonomous Agent Retraining (OpenAI Cookbook 2025)](https://developers.openai.com/cookbook/examples/partners/self_evolving_agents/autonomous_agent_retraining/)
- Codebase analysis: `docker/l3-specialist/entrypoint.sh`, `skills/spawn_specialist/pool.py`, `skills/spawn_specialist/spawn.py`, `orchestration/state_engine.py`, `orchestration/memory_client.py`, `orchestration/snapshot.py`, `docker/memory/memory_service/routers/`

---

*Feature research for: OpenClaw v1.4 Operational Maturity*
*Researched: 2026-02-24*
