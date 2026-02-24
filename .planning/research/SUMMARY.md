# Project Research Summary

**Project:** OpenClaw v1.4 Operational Maturity
**Domain:** AI Swarm Orchestration — production hardening of an existing Docker-based agent system
**Researched:** 2026-02-24
**Confidence:** HIGH

## Executive Summary

OpenClaw v1.4 is not a greenfield build — it is a hardening milestone applied to a shipped, working system. The four feature areas (graceful shutdown with task recovery, memory health monitoring, L1 SOUL suggestion engine, and delta memory snapshots) all build directly on v1.3 infrastructure. Research confirms that zero new external dependencies are required for three of the four features; the only optional addition is `deepdiff>=8.6.1` for delta snapshot rehydration, and only if complex patch reversal becomes a requirement. The recommended approach is to use stdlib-only implementations (signal, asyncio, collections, statistics, re) and maintain the zero-dep principle that has governed the orchestration layer throughout v1.0–v1.3.

The most critical finding is the SIGTERM signal delivery problem: the current `docker/l3-specialist/entrypoint.sh` uses shell form, meaning SIGTERM from `docker stop` is absorbed by bash (PID 1) and never forwarded to the Python/Claude process inside the container. This is the single most important fix — all graceful shutdown and state dehydration logic is unreachable until this one-line `exec` change is made in the entrypoint. The second critical finding is that SIGTERM signal handlers must not call `JarvisState.update_task()` directly due to `fcntl.flock()` re-entrancy on Linux; the correct pattern is a flag + asyncio-scheduled coroutine via `loop.add_signal_handler()`.

The highest-risk feature is the L1 SOUL suggestion engine. Research from Palo Alto Unit 42 and a paper specifically targeting OpenClaw's architecture documents a viable indirect prompt injection path: malicious task output stored in memU surfaces during L1 pattern analysis, and if suggestions are auto-applied, it modifies SOUL templates governing all future L3 behavior. The mandatory mitigation is a human approval gate — suggestions must only be written to a pending `soul-suggestions.json` file and never applied without explicit operator confirmation. Build the approval gate before the suggestion generation pipeline, not after.

## Key Findings

### Recommended Stack

The v1.4 stack is almost entirely the existing stack. Features 1, 2, and 3 require only Python stdlib additions (signal, asyncio, collections, statistics, re) to the existing orchestration layer. Feature 4 (delta snapshots) is implementable with a pure Python dict-comparison function and zero new imports. The only new dependency consideration is `deepdiff>=8.6.1` — recommended only if delta reversal (reconstructing old state from patch chains) becomes a requirement. The current state file structure (shallow JSON dicts, <10KB) does not need it.

**Core technologies (net new for v1.4):**
- `signal` + `asyncio.add_signal_handler` (stdlib): SIGTERM handling in pool.py — asyncio-safe; never use `signal.signal()` in an async context
- `collections.Counter` + `statistics` (stdlib): task pattern frequency analysis for L1 suggestion engine — sufficient at current task corpus size (tens to hundreds per project)
- `exec` form in `entrypoint.sh`: one-line change that makes Python the PID 1 process inside L3 containers, enabling SIGTERM delivery — zero library change
- `deepdiff>=8.6.1` (optional, defer): structured delta generation if rehydration semantics needed; start with pure Python Approach A
- Existing `httpx` + `/memories` REST API: memory health monitoring uses already-deployed memU endpoints with no new HTTP client

### Expected Features

**Must have (table stakes for "Operational Maturity" to be true):**
- SIGTERM handler + task dehydration — any production container process must handle graceful shutdown; unhandled SIGTERM leaves tasks permanently stuck in `in_progress` and blocks pool slots
- Interrupted task recovery loop — pool restart without manual intervention; scans JarvisState for orphaned tasks on startup with configurable recovery policy (mark_failed / auto_retry / manual)
- Memory health scan (Python module) — batch staleness and conflict detection via pgvector similarity and structural checks; returns scored flag list for the dashboard
- Memory health dashboard UI — extends existing `/memory` page with health badges, flagged items, and manual override (edit + dismiss); requires new `PUT /memories/:id` endpoint in the memory service

**Should have (competitive differentiators):**
- Delta memory retrieval — `last_memory_retrieval_at` cursor in state.json + `created_after` filter on memU `/retrieve`; measurable latency reduction at high task frequency
- L1 SOUL suggestion engine — pattern extraction from JarvisState task history + memU rejection clusters; generates reviewable SOUL amendments; closes the failure-to-behavior-change loop

**Defer (v2+):**
- Cross-project memory health aggregation — breaks per-project isolation; add as explicit opt-in when multi-project workflows mature
- SOUL versioning / automatic rollback — would require git-tracking `soul-override.md`; exceeds v1.4 scope
- TTL / forgetting policies — memory volume not yet high enough to warrant automatic expiry

### Architecture Approach

v1.4 is additive: two new Python modules (`orchestration/memory_health.py`, `orchestration/suggestion_engine.py`), four new Next.js API routes, and surgical modifications to `pool.py`, `entrypoint.sh`, `state_engine.py`, `snapshot.py`, and `memory_client.py`. Nothing is rewritten. The existing JarvisState primitives (`update_task`, `set_task_metric`, `list_all_tasks`), `MemoryClient` (`health`, `retrieve`), and `soul_renderer.py` are all reused without interface changes. Two new architectural patterns are introduced: on-demand health check with 5-minute server-side cache (avoids background polling complexity), and suggestion-as-file (`soul-suggestions.json` in the project state directory, consistent with the existing `workspace-state.json` pattern).

**Major components:**
1. `orchestration/memory_health.py` (NEW) — connectivity, staleness, conflict, volume, and orphan checks against memU; writes `memory-health.json` to project state dir
2. `orchestration/suggestion_engine.py` (NEW) — reads JarvisState task outcomes + memU rejection memories; produces `SuggestionItem` proposals; writes `soul-suggestions.json`
3. `skills/spawn_specialist/pool.py` (MODIFIED) — SIGTERM handler via `loop.add_signal_handler`; dehydration drain; startup recovery loop; delta snapshot path in `_memorize_snapshot_fire_and_forget`; pending-task tracking set for clean shutdown
4. `docker/l3-specialist/entrypoint.sh` (MODIFIED) — `trap cleanup SIGTERM` + `exec`-form final command so Python/Claude process is PID 1 and receives signals
5. `workspace/occc` dashboard (MODIFIED) — health banner on `/memory` page; SOUL suggestions panel on `/settings` page; new `/api/memory/health` and `/api/suggestions` routes

### Critical Pitfalls

1. **SIGTERM absorbed by shell-form entrypoint** — Fix: add `exec` before the final CLI runtime call in `entrypoint.sh` so Python/Claude becomes PID 1. Verify with `docker stop` producing exit code 143, not 137 (SIGKILL). Must be done before any dehydration logic is written — all dehydration code is unreachable without this fix.

2. **Signal handler deadlocks on `fcntl.flock()`** — Fix: SIGTERM handler must only set a module-level flag (`_shutdown_requested = True`). Schedule actual dehydration as `asyncio.create_task(graceful_shutdown())` via `loop.add_signal_handler()`. Never call `update_task()` directly from signal handler context — re-entrancy causes deadlock on Linux.

3. **Recovery loop re-spawns tasks with existing git commits** — Fix: check whether staging branch `l3/task-{task_id}` exists before re-spawning. Only recover tasks flagged `recovery_safe: true` (set during clean SIGTERM dehydration). Tasks killed by SIGKILL (no `recovery_safe` flag) require manual decision or are marked `failed`.

4. **Memory health monitor false positives from semantic similarity** — Fix: use cosine similarity only as a pre-filter for candidate conflict pairs, not as a final verdict. Define staleness operationally (not retrieved in top-10 results for N days), not by age alone. Define conflicts structurally (same task_id, different verdict in `review_decision` memories). Never auto-delete — always flag for human review.

5. **L1 suggestions modify SOUL via indirect prompt injection** — Fix: mandatory human approval gate must be the first thing built in the L1 suggestion phase. Suggestions write to `soul-suggestions.json` only. The apply API route validates the diff (no safety constraint removal, no shell commands, max 100 lines) before writing to `soul-override.md`. SOUL files are read-only except via the explicit apply code path.

6. **Fire-and-forget memorize tasks lost on event loop shutdown** — Fix: track all `asyncio.create_task(_memorize_...)` calls in a module-level set. SIGTERM handler awaits `asyncio.gather(*_pending_memorize_tasks, return_exceptions=True)` with a 5-second timeout before the loop stops. Set `--stop-timeout 30` in `docker run` config to give the grace period enough room.

## Implications for Roadmap

Based on research, the four features decompose into a natural 4-phase build order. Features 1 and 2 are foundational reliability (ship first); features 3 and 4 are operational intelligence (ship after reliable baseline). Within each pair, the simpler backend-only feature precedes the one requiring dashboard components.

### Phase 1: Graceful Shutdown and Task Recovery

**Rationale:** This is the hard blocker. Without SIGTERM handling and a recovery loop, any deployment restart leaves tasks permanently in `in_progress`, blocking pool slots and corrupting dashboard state. It is also the foundation that makes subsequent phases safe — the memory health monitor and suggestion engine both read task history, which is only clean if shutdown is handled correctly. The entrypoint `exec` fix must come first, before the dehydration logic, because that logic is unreachable until signals are delivered correctly.
**Delivers:** SIGTERM-safe L3 containers; clean `interrupted` task status on shutdown; pool startup recovery scan with configurable `recovery_policy`; pending-memorize task tracking set for clean shutdown; `--stop-timeout 30` in docker run
**Addresses:** SIGTERM handler + dehydration (P1 must-have), interrupted task recovery loop (P1 must-have)
**Avoids:** Shell-form entrypoint signal absorption; fcntl deadlock in signal handler; fire-and-forget task loss on shutdown; recovery re-spawning tasks with existing git commits on the staging branch

### Phase 2: Delta Memory Snapshots

**Rationale:** Pure backend optimization with no dashboard dependency — simplest change to validate independently. Building this immediately after Phase 1 while pool.py changes are fresh avoids later merge conflicts (both phases touch `_memorize_snapshot_fire_and_forget`). The pure Python Approach A (`_compute_task_delta()` dict comprehension) is strongly recommended over deepdiff to maintain the zero-dep principle. Zero behavioral change for single-commit tasks; multi-commit tasks get the optimization automatically.
**Delivers:** `capture_delta_snapshot()` in snapshot.py; `last_memorized_commit` metric tracked in state engine; delta-only memorize payloads for multi-commit tasks; fallback to full diff when no prior commit tracked
**Uses:** stdlib only; existing `JarvisState.set_task_metric()`; existing `git diff` subprocess pattern
**Avoids:** Snapshot base using mtime instead of immutable SHA; concurrent write producing torn deltas (snapshot deferred until after `container.wait()` returns — already current behavior)

### Phase 3: Memory Health Monitoring

**Rationale:** Self-contained backend + API + minimal dashboard extension. Prerequisite for Phase 4 (L1 suggestions) because the suggestion engine clusters rejection patterns from the same memU data that health monitoring queries. Building health monitoring first validates the pgvector similarity query patterns and establishes `memory_health.py` infrastructure that `suggestion_engine.py` will reuse. The new `PUT /memories/:id` endpoint in the memory service must be implemented here.
**Delivers:** `orchestration/memory_health.py` with staleness / conflict / volume / orphan checks; `GET /api/memory/health` Next.js route with 5-minute server-side cache; health banner on `/memory` page; flagged items panel with delete / edit / dismiss actions; `PUT /memories/:id` in memory service
**Implements:** On-demand health check with server-side cache pattern; structural (not purely semantic) conflict detection
**Avoids:** O(N²) pairwise similarity scan (scope to top-50 per category); auto-deletion of flagged memories; cross-project memory exposure in health API routes

### Phase 4: L1 Strategic SOUL Suggestion Engine

**Rationale:** Highest complexity; spans four components; requires clean task history (Phase 1), cleaner memory payloads (Phase 2), and validated memU query patterns (Phase 3) to produce useful suggestions. Build the human approval gate and SOUL validation layer first — do not test suggestion generation until safety controls are in place, because test data is real task output that may contain injection payloads.
**Delivers:** `orchestration/suggestion_engine.py` with pattern extraction (task outcomes + memU rejection clusters); `soul-suggestions.json` pending file in project state dir; GET/POST suggestion API routes; SOUL suggestions review/apply panel in `/settings` page; diff-based suggestion display; structural validation on apply (no safety constraint removal, no shell commands, max 100 lines)
**Avoids:** Auto-applying suggestions without human approval; SOUL suggestion XSS in dashboard (render as `<pre>`, escape HTML); cross-project memory leakage in L1 analysis; SOUL modifications from unauthenticated API calls; LLM calls inside `suggestion_engine.py` (keep analysis deterministic and stdlib-only)

### Phase Ordering Rationale

- Phase 1 must come first: it is the only phase modifying `pool.py` and `entrypoint.sh` in ways all other phases depend on. Building Phases 2 and 3 while Phase 1's pool.py changes are in-flight creates merge conflicts and untestable states.
- Phase 2 groups immediately after Phase 1: both touch `_memorize_snapshot_fire_and_forget` in pool.py — doing them together while the context is fresh minimizes conflict risk.
- Phase 3 before Phase 4 is a hard dependency: the suggestion engine's rejection pattern queries reuse the `MemoryClient` query infrastructure and `memory_health.py` module built in Phase 3. Phase 3 also validates the pgvector similarity thresholds that Phase 4 relies on.
- Phase 4 is deferred to last because getting the safety controls wrong has irreversible consequences (SOUL mutation affects all future L3 tasks). Deferring it ensures the system has accumulated real task history before the first suggestion run and that the clean-history invariant from Phase 1 is established.

### Research Flags

Phases likely needing deeper research or careful specification during planning:
- **Phase 1 (Graceful Shutdown):** asyncio SIGTERM + fcntl interaction is subtle; the dehydration-safe write design should be prototyped in isolation before the full pool.py integration. The recovery eligibility rules (`recovery_safe` flag, staging branch check, `dehydrated_at` timestamp) need explicit specification before coding the recovery loop — a loop without eligibility checks is more dangerous than no recovery at all.
- **Phase 4 (L1 Suggestions):** The SOUL diff validation rules (what constitutes a safe vs unsafe suggestion) need explicit specification before building the validation layer. Cluster quality depends on memU embedding quality, which has not been tested at scale for this codebase — track cluster hit rate during early Phase 4 testing and add fallback to keyword frequency if clustering yields no clusters.

Phases with well-documented patterns (can skip research-phase):
- **Phase 2 (Delta Snapshots):** Git SHA-based delta tracking is a standard pattern; the implementation is mechanical once the pure Python approach decision is confirmed.
- **Phase 3 (Memory Health):** The on-demand API + server-side cache pattern is straightforward Next.js; the staleness and structural conflict detection heuristics are fully defined in the research with no open design decisions.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All net-new stack needs verified against PyPI, official Python docs, and direct codebase inspection. Zero new mandatory deps confirmed for Features 1–3. deepdiff 8.6.1 version confirmed on PyPI 2026-02-24. |
| Features | HIGH | Feature scope derived from direct codebase gap analysis of v1.3 deferred work (REL-04/05/06/07, PERF-05/06, ADV-01). Feature behavior patterns verified against Docker docs, Python asyncio docs, HaluMem paper, and SCOPE/multi-agent research. |
| Architecture | HIGH | All integration points verified against direct codebase inspection of pool.py, state_engine.py, snapshot.py, memory_client.py, entrypoint.sh, and memory service routers. No assumptions about undocumented APIs. |
| Pitfalls | HIGH | Critical pitfalls verified via direct code inspection (shell-form entrypoint confirmed present) + high-confidence external sources (Docker PID 1 docs, Python asyncio docs, fcntl Linux man page, Palo Alto Unit 42 research specifically targeting OpenClaw architecture). Similarity threshold values (0.75, 0.92) are MEDIUM — reasonable starting points needing empirical tuning. |

**Overall confidence:** HIGH

### Gaps to Address

- **Similarity threshold tuning for conflict detection:** The 0.92 near-duplicate and 0.75–0.91 conflict range thresholds are starting points from the HaluMem paper. Plan a validation step during Phase 3: run the health monitor against a known ground-truth test set (known good and known bad pairs) before running against the production memory store.

- **L1 suggestion cluster quality at current data scale:** The suggestion engine requires ≥3 similar rejections per cluster to generate a proposal. At current project scale, the rejection corpus may be too small for meaningful clustering. Track cluster hit rate during early Phase 4 testing; adjust threshold or fall back to keyword frequency if clustering consistently yields no results.

- **`PUT /memories/:id` endpoint schema:** The memory service has GET and DELETE for memory items but no PUT/update. The exact schema for the update body (`resource_url` as content carrier vs a dedicated `content` field) should be confirmed against the existing `memory_item` model before Phase 3 implementation to avoid a later schema migration.

- **Docker `--stop-timeout` in pool.py:** The current L3 container run command uses skill timeout (600s for code, 300s for test). The SIGTERM-to-SIGKILL grace period (`docker stop --time`) is separate and defaults to 10 seconds. This must be explicitly set to at least 30 seconds in the `docker run` call within pool.py, or the entire graceful shutdown design is moot — all dehydration must complete within this window.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `orchestration/state_engine.py`, `skills/spawn_specialist/pool.py`, `skills/spawn_specialist/spawn.py`, `orchestration/snapshot.py`, `orchestration/memory_client.py`, `docker/l3-specialist/entrypoint.sh`, `docker/memory/memory_service/routers/memories.py`, `docker/memory/memory_service/routers/retrieve.py`, `workspace/memory/src/memu/database/postgres/repositories/memory_item_repo.py`
- Python 3 official docs: `asyncio-eventloop.html` (loop.add_signal_handler, Unix-only constraint), `signal.html` (SIGTERM, signal.signal)
- PyPI deepdiff 8.6.1 — verified latest version September 2025, Python >=3.9, numpy not mandatory for core
- Palo Alto Unit 42: "Indirect Prompt Injection Poisons AI Long-Term Memory" — directly relevant threat model
- Penligent: "The OpenClaw Prompt Injection Problem" — paper specifically targeting OpenClaw's SOUL.md persistence architecture
- OWASP LLM01:2025 Prompt Injection — standard threat classification
- Docker SIGTERM and PID 1 signal handling: Peter Malmgren, OneUptime, Hynek, CloudBees — consistent findings on shell-form vs exec-form
- Python asyncio signal docs: loop.add_signal_handler() for safe async SIGTERM handling
- fcntl(2) Linux manual page — LOCK_EX re-entrancy behavior on Linux

### Secondary (MEDIUM confidence)
- HaluMem: Evaluating Hallucinations in Memory Systems of Agents (arXiv 2025) — similarity thresholds for conflict detection
- SCOPE: Prompt Evolution for Enhancing Agent Effectiveness (arXiv 2025) — SOUL injection patterns
- Multi-Agent Design: Optimizing Agents with Better Prompts and Topologies (arXiv 2025) — agent behavioral improvement patterns
- Self-Evolving Agents — Autonomous Agent Retraining (OpenAI Cookbook 2025) — L1 suggestion engine patterns
- pgvector production patterns: Ivan Turkovic, Crunchy Data, Medium — similarity query performance and HNSW index usage
- Incremental snapshot consistency: Debezium, Delta Lake — SHA-based delta base tracking principles

### Tertiary (LOW confidence)
- WebSearch: Python SIGTERM Docker PID 1 patterns 2025/2026 — corroborates exec-form fix (covered more reliably by primary sources)
- WebSearch: deepdiff delta serialization flat dicts — corroborated by PyPI docs

---
*Research completed: 2026-02-24*
*Ready for roadmap: yes*
