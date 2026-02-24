# Project Research Summary

**Project:** OpenClaw v1.3 — Agent Memory Integration
**Domain:** AI Swarm Orchestration / Persistent Agent Memory (memU)
**Researched:** 2026-02-24
**Confidence:** HIGH

## Executive Summary

OpenClaw v1.3 adds persistent memory to an existing 3-tier agent orchestration system (L1 → L2 → L3) that currently operates statelessly across restarts. The established approach for this domain is a standalone memory service with a vector database backend, accessed via HTTP from all tiers. The specific framework is `memu-py 1.4.0` (memU), deployed as a Docker container (`nevamindai/memu-server:latest`) backed by PostgreSQL+pgvector, with `httpx` as the unified HTTP client for both synchronous (L3 entrypoint) and asynchronous (L2 orchestration) call sites. No existing code is rewritten — the integration is additive across 5 surgically modified files and 6 new files. No new frontend dependencies are required.

The recommended build order is a strict 6-phase dependency chain dictated by the architecture: memU service infrastructure first, scoping conventions second, L3 write path third, L2/pre-spawn read path fourth, L2 review memorization fifth, and the dashboard panel last. The critical learning loop — L3 completes task, outcome is memorized, next L3 receives relevant context — spans Phases 1 through 4 and must be established as a unit. The dashboard panel (Phase 6) is intentionally deferred because it provides no validation signal until real memory records exist.

The dominant risk profile is infrastructure-first: 5 of 7 critical pitfalls manifest in Phase 1 before any application code is written. The Python 3.13 version mismatch (L3 containers run Python 3.11 via Debian APT, while memU requires 3.13+), Docker networking localhost misroute, pgvector extension init ordering, HNSW index schema design, and Temporal dependency evaluation must all be resolved and verified in Phase 1. The secondary structural risk is memory scoping: a single PostgreSQL database with filter-based isolation silently leaks cross-project memories if any retrieve call omits the `project_id` filter. The `MemoryClient` wrapper class with mandatory scoping parameters is the structural solution — it makes incorrect calls impossible rather than merely discouraged.

---

## Key Findings

### Recommended Stack

The v1.3 stack adds 5 new packages on top of the unchanged v1.2 baseline (Python 3 stdlib orchestration, Docker SDK, Next.js 14, SWR, Recharts, Tailwind). No new frontend libraries are needed — the existing SWR, Zod, and react-toastify cover all dashboard memory panel needs.

**Core technologies:**
- `nevamindai/memu-server:latest`: Pre-built Docker image for the memU REST API server — eliminates building a custom FastAPI wrapper; maintained by the memU team; exposes `/memorize`, `/retrieve`, `/categories` endpoints
- `pgvector/pgvector:pg16` (or pg17-bookworm): PostgreSQL with pgvector extension pre-installed — official image avoids manual extension compilation; pg17-bookworm matches L3 container Debian base
- `python:3.13-slim-bookworm`: Base image for any custom memU wrapper (if needed) — required because memU needs Python 3.13+ and Debian bookworm APT ships only Python 3.11
- `httpx==0.28.1`: HTTP client for L2 orchestration (async) and L3 entrypoint (sync) — single library covers both concurrency models; avoids the requests/aiohttp split

**Supporting:**
- `memu-py==1.4.0` with `[postgres]` extra: Python SDK used inside the memU service container; requires Python >=3.13; NOT imported in L3 containers or host orchestration — those use HTTP only
- `asyncpg==0.31.0`: Pulled transitively by `memu-py[postgres]`; do not install separately
- `python-dotenv`: Loads secrets in the memU container; keep connection strings out of the image

**Note on approach conflict:** STACK.md proposes building a custom FastAPI wrapper around `memu-py`. ARCHITECTURE.md uses the pre-built `nevamindai/memu-server:latest` Docker image. The pre-built image is strongly preferred — it eliminates a custom service build, is maintained upstream, and has been validated against the memU SDK. Only fall back to a custom wrapper if the pre-built image requires Temporal and Temporal cannot be disabled.

### Expected Features

Feature research is scoped to v1.3 additions only. The baseline (orchestration, Docker pool, SOUL rendering, semantic snapshots, occc dashboard) is stable and untouched.

**Must have — P1 (table stakes for the learning loop):**
- Standalone memU service with PostgreSQL+pgvector — prerequisite for all other memory features; in-process store is not viable in a multi-container architecture
- Internal REST API for memory operations — bridges Python orchestration and Next.js dashboard to memU without requiring Python imports in TypeScript or version conflicts in L3
- Per-agent + per-project memory scoping — must be established before any data enters the store; post-hoc scoping requires retroactive data cleanup
- L3 auto-memorization of task outcomes — the core write path; uses existing semantic snapshots as the memorize payload; fire-and-forget to avoid blocking pool slots
- L2 memorization of review decisions — stores merge/reject decisions with reasoning; enables the review quality loop
- Pre-spawn context retrieval + SOUL template injection — the core read path; RAG mode only (milliseconds); retrieved context injected as `$memory_context` into SOUL template with a hard 5-item / 2,000-character budget
- Dashboard memory panel (browse + search, read-only) — operator visibility into what the swarm has learned; project-scoped; delete is allowed, edit is not

**Should have — P3 (add after P1 validated, triggered by observed behavior):**
- L2 rejection feedback loop — structured rejection tagging with "past mistakes" injected into SOUL; deferred until pre-spawn context is validated as insufficient alone
- L3 in-execution memory queries — mid-task HTTP retrieval from within the container; deferred until agents demonstrably repeat solved problems despite pre-spawn injection

**Defer to v2+:**
- Cross-project pattern sharing (global/ namespace) — only valuable with 5+ projects and substantial memory volume
- Memory TTL / forgetting policies — premature optimization; insufficient volume to justify
- Memory-driven L1 strategy suggestions — unvalidated value proposition

**Anti-features (avoid building):**
- Real-time memorization during L3 execution — produces incoherent partial-state records; the semantic snapshot at task completion is the correct memorization point
- Shared memory pool across projects — confidentiality boundary violation; per-project scoping is non-negotiable
- LLM-mode retrieval for pre-spawn context — seconds of latency per spawn, unacceptable with 3 concurrent L3 workers; reserve LLM mode for dashboard search where human latency is acceptable
- Dashboard edit (in-place mutation of stored memories) — use delete + re-memorize a correction instead; in-place edits corrupt retrieval integrity

### Architecture Approach

The architecture adds a shared Docker bridge network (`openclaw-net`) and two new containers (memu-server on port 8765, PostgreSQL internal on port 5432) that integrate with the existing 3-tier hierarchy through precisely scoped injection points. The key asymmetry is the dual-URL pattern: L2 orchestration (host Python) calls `http://localhost:8765`; L3 containers call `http://memu-server:8765` via Docker DNS on `openclaw-net`. These are different URLs for the same service and the distinction is mandatory.

**Major components:**

1. `docker/memory/docker-compose.yml` — brings up `memu-postgres` and `memu-server` on `openclaw-net`; named volume for persistent pgvector storage; `openclaw-net` is an external network created once during setup

2. `orchestration/memory_client.py` — thin `MemoryClient` wrapper (sync httpx) initialized with `project_id`; makes it structurally impossible to call memU without scoping; used by L2 orchestration; health check method for service availability detection

3. `skills/spawn_specialist/spawn.py` (modified) — adds pre-spawn `retrieve()` call (3s timeout, graceful degradation to empty string on failure); injects `MEMU_SERVICE_URL=http://memu-server:8765`, `MEMU_AGENT_ID`, `MEMU_PROJECT_ID`, `MEMU_ENABLED` env vars; adds L3 containers to `openclaw-net`

4. `orchestration/soul_renderer.py` (modified) — adds `extra_vars` parameter to `build_variables()`; `$memory_context` substitution with `safe_substitute()` defaulting to empty string; empty context renders harmlessly as blank section

5. `docker/l3-specialist/entrypoint.sh` (modified) — fire-and-forget `curl POST /memorize` after task completion; does not wait for memorize pipeline to complete; exits after receiving HTTP 200/202 and logging the returned task_id

6. `workspace/occc/src/app/memory/` — new dashboard page; SWR hooks (`useMemory.ts`) polling `/api/memory` routes (30s interval — memory changes slowly); API routes proxy to `http://localhost:8765` with project scoping enforced server-side

**Data flows (in build dependency order):**
- L3 completes task → entrypoint.sh fires POST to `/memorize` (fire-and-forget) → memU pipeline extracts facts and stores
- L2 reviews diff → `memory_client.memorize()` stores decision with merge/reject reasoning (fire-and-forget)
- spawn.py calls `memory_client.retrieve()` (RAG mode, limit=5) → context formatted to ≤2,000 chars → injected into `soul_renderer` as `extra_vars` → L3 container starts with enriched SOUL

### Critical Pitfalls

1. **Python 3.11 in L3 containers vs memU's Python 3.13 requirement** — L3 containers must never import `memu-py` directly. All L3 memory calls go through HTTP REST (curl or `urllib.request`) to the memU-server container. The memU-server container must be based on `python:3.13-slim-bookworm` or the pre-built `nevamindai/memu-server` image, not `debian:bookworm-slim + apt-get install python3`. Verify with `python3 --version` inside the container; `debian:bookworm-slim` returns 3.11.

2. **pgvector extension init ordering failure** — Place `CREATE EXTENSION IF NOT EXISTS vector` in a shell script (`00_init.sh`) in `/docker-entrypoint-initdb.d/`, not a SQL file. SQL files execute in alphabetical order, which can run schema migrations before extension creation. Validate every cold start by deleting the postgres volume and checking `pg_extension` table before any integration code is written.

3. **L3 container localhost resolves to container loopback, not host** — Inject `MEMU_SERVICE_URL=http://memu-server:8765` at spawn time via env var. L3 containers must be added to `openclaw-net` in the spawn.py `docker run` call. Validate with `docker exec` from a running L3 container — host-side success does not prove in-container success.

4. **Synchronous memorize call blocks L3 container exit and holds pool slot** — Always fire-and-forget the memorize POST from L3 entrypoint. memU's memorize pipeline takes 5-15 seconds (LLM extraction + embed + store). Blocking with 3 concurrent L3 completions creates thundering-herd against the single-worker memU server and starvation for the next queued task.

5. **SOUL context explosion from unbounded memory retrieval** — Enforce a hard limit of 5 memory items and 2,000 characters maximum for the `$memory_context` block. Summarize memories as brief plain prose, not raw transcripts. Validate SOUL.md rendered byte count stays under 8KB (v1.2 baseline is ~3KB).

6. **Missing project_id filter on retrieve leaks cross-project memory** — The `MemoryClient` wrapper must be initialized with `project_id` and bake it into every call as a mandatory parameter. Write a two-project isolation test before any retrieval code ships: project B retrieve must return zero results from project A's records. Treat cross-project leakage as a security failure, not a correctness issue.

7. **Temporal service dependency for memU async pipeline** — The pre-built `memu-server` image may require a running Temporal instance (gRPC + PostgreSQL + UI server). For 3 concurrent L3 workers, asyncio background tasks are sufficient and eliminate 3-service overhead. Determine this in Phase 1 by pulling the image and inspecting its startup requirements. If Temporal is required, add a healthcheck that verifies Temporal gRPC before marking memU service ready.

---

## Implications for Roadmap

The build order is deterministic and non-negotiable. Infrastructure must precede client code; scoping must precede data writes; data writes must precede retrieval validation; retrieval must precede SOUL injection; the dashboard is last. The critical constraint is that each phase's verification gate must pass before the next phase begins — the fire-and-forget pattern and project scoping enforcement are not refinements, they are prerequisites.

### Phase 1: memU Infrastructure Setup

**Rationale:** Root dependency for every other phase. Nothing can be built or tested without a running memU service and verified pgvector database. Five of 7 critical pitfalls manifest here and must be resolved before moving on.
**Delivers:** `docker/memory/docker-compose.yml` with memu-server + memu-postgres; `docker network create openclaw-net`; L3 containers added to `openclaw-net` in spawn.py; `openclaw.json` gains `memory_service` config block (enabled: false initially); cold-start test passes (delete volume, restart, verify pgvector extension present); memorize and retrieve calls succeed from the host
**Addresses:** Standalone memU service (Docker + PostgreSQL+pgvector)
**Resolves pitfalls:** Python 3.13 base image, pgvector init ordering, Docker networking strategy, HNSW schema (mutable/immutable split), Temporal evaluation
**Research flag:** Needs Phase 1 investigation — pull `nevamindai/memu-server:latest` and determine whether Temporal is required. This is the single highest-uncertainty decision in the milestone.

### Phase 2: Memory Client + Scoping Convention

**Rationale:** Scoping must be established before any data enters the store. A scoping error at this stage requires retroactive data cleanup. The `MemoryClient` wrapper with mandatory project_id makes incorrect calls structurally impossible.
**Delivers:** `orchestration/memory_client.py` with `MemoryClient(base_url, project_id)` interface; `memory_client.health()` used by L2 startup; `openclaw.json:memory_service.enabled` flag; two-project isolation test passing (project B returns zero results from project A)
**Addresses:** Per-agent + per-project memory scoping; Internal REST API (client side)
**Resolves pitfalls:** Missing project_id filter; cross-project memory leakage
**Research flag:** Standard patterns — httpx sync API and wrapper class design are well-documented.

### Phase 3: L3 Auto-Memorization

**Rationale:** The write path of the learning loop. Must produce real memory records before retrieval can be validated end-to-end. Establishes the fire-and-forget pattern before any concurrent-completion scenarios arise.
**Delivers:** `entrypoint.sh` fires memorize POST on task completion (fire-and-forget; exit after HTTP 200/202 received); `MEMU_*` env vars injected by spawn.py into every L3 container; real memory items visible in memu-server categories after a test task completes
**Addresses:** L3 auto-memorization of task outcomes
**Uses:** curl (bash entrypoint) or `python3 -c "import urllib..."` (no httpx needed in L3); existing semantic snapshots as memorize payload
**Resolves pitfalls:** Fire-and-forget timing, pool slot release after task completion, concurrent memorize thundering-herd

### Phase 4: Pre-Spawn Retrieval + SOUL Injection

**Rationale:** The read path. Depends on Phase 3 having produced real memory records. The `soul_renderer.py` extension is surgical and additive (backward-compatible via default empty string). Retrieval budget constraints must be designed before wiring up.
**Delivers:** `spawn.py` calls `memory_client.retrieve()` before container creation (RAG mode, limit=5, 3s timeout, graceful degradation to empty string); `soul_renderer.py` gains `extra_vars` param; `agents/_templates/soul-default.md` gains `## Memory Context` + `$memory_context` section; end-to-end verification: spawned task SOUL contains retrieved context from Phase 3 memories
**Addresses:** Pre-spawn context retrieval; SOUL template injection
**Resolves pitfalls:** SOUL context size explosion (limit=5, 2,000 char hard cap, summarized prose format)
**Research flag:** Standard patterns — `string.Template.safe_substitute()` extension is the existing pattern in soul_renderer.py.

### Phase 5: L2 Review Decision Memorization

**Rationale:** Can technically be built in parallel with Phase 4 (both depend on Phase 2 only), but validation benefits from Phase 3 patterns being stable. Closes the review quality loop. Requires locating the exact merge/reject decision call site in the codebase.
**Delivers:** L2 review flow calls `memory_client.memorize()` with structured merge/reject decision and reasoning; state file is updated before memorize call fires (decision not lost if memorize fails); decisions are retrievable as L2-attributed context in Phase 4 pre-spawn retrieval
**Addresses:** L2 memorization of review decisions
**Research flag:** Needs codebase investigation — locate the exact code path where L2 implements the merge/reject decision (may be in `snapshot.py`, an agent-side action, or an L2 orchestration hook). This determines the call site before Phase 5 planning is complete.

### Phase 6: Dashboard Memory Panel

**Rationale:** Last, because it provides no validation signal until real memory records exist from Phases 3 and 5. Uses established SWR + project-selector patterns from v1.1/v1.2 dashboard.
**Delivers:** `/api/memory?project={id}` Next.js route (GET categories + item counts, proxies to `http://localhost:8765/categories`); `/api/memory/search` route (POST semantic search, proxies to `/retrieve`); `workspace/occc/src/app/memory/page.tsx` with category sidebar, item table, semantic search bar (debounced), agent attribution column (L2 vs L3), delete action; `workspace/occc/src/lib/memory.ts` (`useMemory()` SWR hook, 30s poll interval)
**Addresses:** Dashboard memory panel (browse + search)
**Uses:** SWR 2.4.0, Zod 3.23.8 (response validation), react-toastify (error surfacing) — all already installed
**Research flag:** Standard patterns — identical SWR hook and API proxy pattern used in tasks, containers, and projects panels.

### Phase Ordering Rationale

- Phase 1 is mandatory first: 5 of 7 pitfalls are Phase 1 blockers; infrastructure cannot be added after integration code is written without risking mismatched assumptions
- Phase 2 must precede Phases 3, 4, and 5: scoping conventions must exist before any data enters the store
- Phase 3 must precede Phase 4: retrieval against an empty memory store cannot be validated end-to-end
- Phases 4 and 5 can be developed in parallel once Phase 2 is complete; neither depends on the other
- Phase 6 is correctly last: dashboard showing zero memories provides no validation; it needs real data from Phases 3 and 5

### Research Flags

**Needs deeper investigation during planning:**
- **Phase 1:** Pull `nevamindai/memu-server:latest` and inspect startup requirements. Determine whether Temporal is required. If yes, decide whether to include Temporal or build a custom asyncio-based wrapper. This decision gates the entire Phase 1 architecture.
- **Phase 1:** Confirm the correct pgvector image tag (`pg16` in ARCHITECTURE.md vs `pg17-bookworm` in STACK.md). Verify which version `memu-server` expects in its `DATABASE_URL`. Use the version the memu-server image was tested against.
- **Phase 5:** Inspect the existing codebase to locate where L2 makes merge/reject decisions. The call site for `memory_client.memorize()` depends on this. Check `orchestration/snapshot.py`, L2 agent session handling, and any `review.py` equivalent.

**Standard patterns — skip deep research during planning:**
- **Phase 2:** `MemoryClient` wrapper with httpx is textbook Python; no novel patterns
- **Phase 4:** `soul_renderer.py` extra_vars extension follows the existing `string.Template.safe_substitute()` pattern already in the codebase
- **Phase 6:** Dashboard SWR hook + API proxy follows identical pattern to `useTasks`, `useContainers`, and project-switcher hooks established in v1.1/v1.2

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified on PyPI and Docker Hub; Python 3.13 version constraint confirmed in memu-py source; httpx dual-mode coverage is well-justified |
| Features | HIGH | Feature dependency graph is unambiguous; P1/P2/P3 split derives from the existing architecture's natural injection points; anti-features are well-documented with production failure modes |
| Architecture | HIGH | Based on direct codebase inspection of all v1.2 modified files + memU-server repository; component boundaries, data flows, and env var injection points are precise |
| Pitfalls | HIGH | All 7 critical pitfalls derive from verified sources: pgvector GitHub issues, Docker networking docs, Python APT version behavior; recovery strategies and "looks done but isn't" checklist included |

**Overall confidence:** HIGH

### Gaps to Address

- **memu-server Temporal dependency:** Whether `nevamindai/memu-server:latest` requires a running Temporal instance is unconfirmed. STACK.md proposes a custom FastAPI wrapper (no Temporal); PITFALLS.md warns Temporal adds 3-service overhead. Pull the image in Phase 1 and inspect startup behavior before committing to either approach. This is the highest-uncertainty decision in the milestone.

- **Port convention conflict:** ARCHITECTURE.md uses port 8765; STACK.md uses 18791 (OpenClaw's 18xxx convention). Final port must be chosen before any integration code is written and documented consistently in `openclaw.json`. Recommendation: use 18791 if building a custom service wrapper; use whatever port the pre-built memu-server exposes if using the Docker image.

- **L2 review call site:** Phase 5 requires placing `memory_client.memorize()` at the merge/reject decision point in L2's execution flow. The current codebase may implement this as an agent-side action not in a Python file. Inspect before Phase 5 planning.

- **`memu-py` client vs raw httpx REST calls:** FEATURES.md documents the `MemuClient` Python class from `memu-py`; ARCHITECTURE.md designs a raw `httpx` client against the REST API. For `memory_client.py` in L2 orchestration, using `memu-py`'s `MemuClient` SDK (pointing at the self-hosted memu-server) may be cleaner and more resilient to API changes than a hand-rolled HTTP client. Evaluate during Phase 2 once the memu-server startup behavior is understood.

---

## Sources

### Primary (HIGH confidence)
- memu-py PyPI 1.4.0 — Python >=3.13 requirement, API methods (`memorize`, `retrieve`), postgres extra
- NevaMind-AI/memU GitHub README — MemUService API, PostgreSQL+pgvector setup, self-hosted mode
- NevaMind-AI/memU-server GitHub — pre-built Docker image, FastAPI wrapper, async pipeline architecture
- OpenClaw codebase (direct inspection) — `skills/spawn_specialist/spawn.py`, `orchestration/soul_renderer.py`, `docker/l3-specialist/entrypoint.sh`, `skills/spawn_specialist/pool.py`, `orchestration/snapshot.py`, `docker/l3-specialist/Dockerfile`
- FastAPI PyPI 0.132.0 — version confirmed, Python >=3.10, Pydantic v2
- httpx PyPI 0.28.1 — sync + async APIs, Python >=3.8
- asyncpg PyPI 0.31.0 — pulled by memu-py[postgres], Python 3.9-3.14 compatible
- docker-library/python slim-bookworm Dockerfile — Python 3.13 base image verified, latest patch 3.13.12
- pgvector GitHub issues #355, #512 — extension init ordering bug documented and confirmed
- pgvector GitHub issue #875 — HNSW update performance limitation confirmed
- Docker Docs: Host Network Driver — localhost resolution inside containers documented

### Secondary (MEDIUM confidence)
- Agent Zero Memory Dashboard (DeepWiki) — UI patterns for memory browse, search, category organization
- Anthropic: Effective Context Engineering for AI Agents — pre-task context injection, context budget patterns
- mem0.ai: AI Memory Security Best Practices — scoping, isolation, sanitization patterns
- Palo Alto Unit 42: Persistent Behaviors in Agents' Memory — prompt injection via retrieval threat model
- Crunchy Data: HNSW Indexes with Postgres and pgvector — mutable/immutable table split pattern
- pgvector Docker Hub tag list — pg16/pg17 bookworm variants

### Tertiary (LOW confidence — needs validation during implementation)
- Temporal alternatives for small projects — asyncio queue vs Temporal trade-offs; apply only if memu-server requires Temporal
- Amazon Bedrock AgentCore: Specify namespaces — multi-tenant memory namespace design patterns
- arXiv: Asynchronous LLM Function Calling (2412.07017) — fire-and-forget timing estimates

---
*Research completed: 2026-02-24*
*Ready for roadmap: yes*
