# Project: OpenClaw (Grand Architect Protocol)

## What This Is

OpenClaw is an AI Swarm Orchestration system implementing the Grand Architect Protocol — a 3-tier hierarchical architecture where AI agents delegate, execute, and synchronize work through Docker containers and git-based workflows. The occc dashboard provides real-time visibility into swarm operations with per-project metrics.

## Core Value

Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## Tech Stack

- **Core:** OpenClaw CLI, Bun, Docker 29.1.5
- **Orchestration:** Python 3 (state engine, snapshots, spawn, monitoring, project_config, config_validator, logging), memU (memu-py)
- **Memory:** memU 1.4.0 (Python 3.13+, PostgreSQL+pgvector)
- **Frontend:** Next.js 16 (App Router), Tailwind 4, SWR, Zod, Recharts
- **Container:** Debian bookworm-slim L3 images, Nvidia Container Toolkit
- **OS:** Ubuntu 24.04 LTS

## Current Milestone: Planning next (v1.7 or v2.0)

**Previous:** v1.6 Agent Autonomy — shipped 2026-02-26

## Current State

**Shipped:** v1.6 Agent Autonomy (2026-02-26)
**LOC:** ~25K Python, ~30K TypeScript/TSX (packages/ only)
**Tests:** 268/268 passing

Architecture operational:
- L1 (ClawdiaPrime) → L2 (PumplAI_PM) → L3 (Ephemeral Specialists) delegation chain
- Jarvis Protocol state synchronization with file locking, backup-on-write, and corruption recovery
- Semantic snapshot system with git staging branches
- occc mission control dashboard with SSE real-time streaming, project switching, and metrics visualization
- Docker isolation with `no-new-privileges`, `cap_drop ALL`, memory/CPU limits
- Unified config layer with schema validation, env-var precedence, and migration CLI
- Notion Kanban Sync (v1.5/v2.0 extension) for real-time project visibility

Agent autonomy (v1.6):
- 4-state autonomy framework (PLANNING → EXECUTING → BLOCKED/COMPLETE/ESCALATING) with confidence scoring
- Self-directed task decomposition via LLM planning phase; spawn injects AUTONOMY_ENABLED
- Confidence-based escalation (0.6 threshold) with indefinite pause loop until L2 resumes
- Context-aware tool selection with intent analysis and prompt injection
- Progress self-monitoring: heuristic deviation detection, LLM-driven course correction, dynamic step splicing
- Dashboard autonomy UI: state badges, confidence indicator, escalation alerts, EscalationsPage, Resume/Fail APIs
- E2E autonomy tests (16 tests): happy path, retry path, escalation path, multi-step

Multi-project framework (v1.1):
- Per-project state/snapshot path resolution via `project_config.py`
- SOUL template engine with default + per-project override mechanism
- Namespaced container naming and per-project pool isolation (PoolRegistry)
- `openclaw project` CLI with init/list/switch/remove and template presets
- Dashboard project selector with project-scoped API routes and SSE streams

Orchestration hardening (v1.2):
- Structured JSON logging across all orchestration components via `get_logger()` factory
- State engine reliability: backup-on-write, .bak recovery, config schema validation on load
- State engine performance: mtime-based in-memory caching, write-through updates, Docker client pooling
- Task lifecycle observability: spawn-to-complete timestamps, lock wait tracking, activity log rotation
- Per-project pool config: configurable concurrency limits, shared/isolated modes, overflow policies (reject/wait/priority)
- Dashboard metrics: Recharts visualization (task charts, pool gauges), agent hierarchy with status dots

Agent memory (v1.3):
- Standalone memU service (memu-py + PostgreSQL+pgvector) in Docker with REST API
- Per-project + per-agent memory scoping enforced by MemoryClient wrapper
- L3 auto-memorization of task outcomes via fire-and-forget (non-blocking)
- L2 review decision memorization with category metadata
- Pre-spawn context retrieval injected into SOUL template (2,000-char budget cap, graceful degradation)
- L3 in-execution memory queries via HTTP; category-routed memory formatting (CATEGORY_SECTION_MAP)
- Dashboard /memory page with project-scoped browsing, semantic search, bulk delete, metadata display

Operational maturity (v1.4):
- SIGTERM graceful shutdown for L3 containers — bash trap writes `interrupted` to Jarvis state (exit 143)
- Fire-and-forget memorize drain — asyncio tasks tracked + drained (30s gather) via `loop.add_signal_handler`
- Pool startup recovery scan — detects orphaned tasks, applies configurable `mark_failed`/`auto_retry`/`manual` policy
- Memory health monitoring — staleness + cosine-conflict detection; dashboard badges, conflict panel, edit/archive actions
- L1 strategic SOUL suggestions — keyword-frequency clustering → diff-style amendments with mandatory approval gate
- Delta-cursor memory retrieval — `created_after` filter on memU `/retrieve`, cursor in `workspace-state.json`, `max_snapshots` pruning

Known limitations:
- Gateway startup is manual (runtime dependency)
- COM-04 snapshot capture cannot be E2E tested when workspace is a git submodule
- CLI routing replaces lane queue REST API (accepted spec deviation)
- `workspace/` path divergence: runtime state at `data/workspace/.openclaw/` vs code-resolved `OPENCLAW_ROOT/workspace/.openclaw/` — pre-existing, candidate for v1.5 config unification
- Human verification pending for live Docker/browser tests (SIGTERM E2E, memory health UI, suggestions UI)

## Requirements

### Validated

- ✓ SET-01: Ubuntu host + Docker + Nvidia — v1.0
- ✓ SET-02: openclaw.json gateway + lane queue config — v1.0
- ✓ SET-03: Gateway on port 18789 — v1.0
- ✓ HIE-01: ClawdiaPrime L1 strategic orchestrator — v1.0
- ✓ HIE-02: PumplAI_PM L2 tactical layer — v1.0
- ✓ HIE-03: L3 specialist containers spawn — v1.0
- ✓ HIE-04: Physical Docker isolation — v1.0
- ✓ COM-01: Hub-and-spoke via Gateway — v1.0
- ✓ COM-02: Lane Queues / CLI routing — v1.0 (spec deviation accepted)
- ✓ AUTO-01: L3 agents perform self-directed task breakdown and planning — v1.6
- ✓ AUTO-02: agents self-escalate based on confidence thresholds — v1.6
- ✓ AUTO-03: Context-aware tool selection based on task intent — v1.6
- ✓ AUTO-04: Progress self-monitoring and course correction logic — v1.6
- ✓ AUTO-05: Autonomous handoff to L2 when blocked or complete — v1.6 (partial: design doc deferred)
- ✓ COM-03: Jarvis Protocol state.json sync — v1.0
- ✓ COM-04: Semantic snapshotting — v1.0
- ✓ DSH-01: occc dashboard (Next.js 16) — v1.0
- ✓ DSH-02: Real-time SSE monitoring — v1.0
- ✓ DSH-03: Live log feeds from containers — v1.0
- ✓ DSH-04: Global metrics visualization — v1.0
- ✓ SEC-01: Permission-based access isolation — v1.0
- ✓ SEC-02: Automated log redaction — v1.0
- ✓ CFG-01 through CFG-07: Config decoupling (per-project paths, SOUL templating, dynamic branch detection) — v1.1
- ✓ MPR-01 through MPR-06: Multi-project runtime (container labels, namespaced naming, project-scoped pool/monitor) — v1.1
- ✓ CLI-01 through CLI-06: Project CLI (init/list/switch/remove with template presets) — v1.1
- ✓ DSH-05 through DSH-08: Dashboard project switcher (selector, scoped API/SSE, filtered views) — v1.1
- ✓ REL-01 through REL-03: State backup/recovery, project config validation, agent hierarchy validation — v1.2
- ✓ PERF-01 through PERF-04: Docker client pooling, state caching, write-through cache, cached monitor reads — v1.2
- ✓ OBS-01 through OBS-04: Structured logging, task lifecycle metrics, pool utilization, activity log rotation — v1.2
- ✓ POOL-01 through POOL-03: Per-project concurrency limits, shared/isolated modes, overflow policies — v1.2
- ✓ DSH-09 through DSH-10: Agent hierarchy filtering, usage metrics panel — v1.2
- ✓ INFRA-01 through INFRA-05: memU Docker service, PostgreSQL+pgvector, Docker Compose, REST API, health check — v1.3
- ✓ SCOPE-01 through SCOPE-03: Per-project scoping, per-agent scoping, MemoryClient enforcement — v1.3
- ✓ MEM-01 through MEM-04: L3 auto-memorization, L2 review memorization, non-blocking failure, MEMU_API_URL injection — v1.3
- ✓ RET-01 through RET-05: Pre-spawn retrieval, SOUL injection, budget cap, graceful degradation, in-execution queries — v1.3
- ✓ DSH-11 through DSH-14: Memory page, semantic search, delete action, metadata display — v1.3
- ✓ REL-04 through REL-08: SIGTERM graceful shutdown, pool recovery scan, configurable recovery policy, memorize drain — v1.4
- ✓ QUAL-01 through QUAL-06: Memory health scan (staleness + conflict detection), PUT update endpoint, dashboard badges + conflict panel + settings — v1.4
- ✓ ADV-01 through ADV-06: Pattern extraction engine, SOUL diff amendments, pending suggestions store, accept/reject pipeline with approval gate, dashboard suggestions UI — v1.4
- ✓ PERF-05 through PERF-08: Memory cursors in state.json, cursor-aware pre-spawn retrieval, `created_after` filter on memU, `max_snapshots` pruning — v1.4
- ✓ CONF-01 through CONF-07: Config consolidation (path resolver, schema validation, migration CLI, env precedence, integration tests) — v1.5
- ✓ REL-09, QUAL-07, OBS-05: Docker health checks, calibrated threshold, adaptive polling — v1.5
- ✓ NOTION-01 through NOTION-11: Notion Kanban Sync (lifecycle events, idempotent capture, reconcile) — v1.5

### Active

(None — v1.6 complete; next milestone TBD)

### Out of Scope

- Multi-host swarm — single-host only
- Persistent L3 agents — ephemeral containers by design
- REST lane queue API — CLI routing accepted as equivalent
- LLM-generated SOULs at init time — non-determinism in CLI init operations
- Per-project Docker networks — no inter-container networking needed
- CWD-based project auto-detection — conflicts with scripts calling openclaw from arbitrary directories
- Cross-project agent sharing — conflicts with 1:1 L2-to-project assumption
- GitPython library adoption — subprocess reduction sufficient for now
- Prometheus/OpenTelemetry export — overkill for single-host system
- Docker health checks — moved to v1.5 (REL-09 now active)

## Key Decisions

| Decision | Outcome | Version |
|----------|---------|---------|
| 3-tier hierarchy (L1/L2/L3) | ✓ Good — clean separation of concerns | v1.0 |
| Docker physical isolation | ✓ Good — security hardening works | v1.0 |
| Migrated Snap Docker → Native Docker | ✓ Good — resolved `no-new-privileges` blocker | v1.0 |
| CLI routing replaces lane queues | ✓ Good — simpler, same functional result | v1.0 |
| Jarvis Protocol (file locking) | ✓ Good — reliable cross-container sync | v1.0 |
| Next.js 16 + SWR for dashboard | ✓ Good — SSE + polling hybrid works | v1.0 |
| Git staging branches for L3 work | ✓ Good — clean isolation with L2 review | v1.0 |
| Project context layer (project.json manifests) | ✓ Good — clean per-project path resolution | v1.1 |
| SOUL templating via string.Template.safe_substitute | ✓ Good — no Jinja2 dependency, sufficient for variable substitution | v1.1 |
| Per-project pool isolation via PoolRegistry | ✓ Good — independent semaphores per project | v1.1 |
| argparse subparsers for project CLI | ✓ Good — consistent with existing spawn/monitor pattern | v1.1 |
| OPENCLAW_PROJECT env var priority over config | ✓ Good — prevents mid-execution mutation | v1.1 |
| SOUL auto-generation in initialize_workspace() | ✓ Good — skip-if-exists default, --force for explicit overwrite | v1.1 |
| Python stdlib logging only (no external deps) | ✓ Good — JSON to stderr, component field, configurable levels | v1.2 |
| Post-write backup (not pre-write) for state engine | ✓ Good — .bak always contains last valid state | v1.2 |
| mtime-based cache invalidation with TTL safety net | ✓ Good — zero contention on cache hits, deep copy prevents mutation | v1.2 |
| Docker client singleton with ping-on-reuse | ✓ Good — transparent daemon restart recovery | v1.2 |
| Config-driven pool with hot-reload on every get_pool() | ✓ Good — no restart needed for config changes | v1.2 |
| PoolOverflowError for all overflow scenarios | ✓ Good — single exception type, clear error messages | v1.2 |
| Shared semaphore lazy-created on first shared-mode call | ✓ Good — no wasted resources for isolated-only projects | v1.2 |
| JarvisState instance dict local to tail_state() | ✓ Good — implicit teardown on exit, no module-level cache | v1.2 |
| memU as self-hosted library in standalone Docker service | ✓ Good — avoids unknown Temporal dependency | v1.3 |
| PostgreSQL+pgvector for memory storage | ✓ Good — PG17 native vector performance, persistent volume | v1.3 |
| Per-agent + per-project memory scoping via MemoryClient | ✓ Good — structurally impossible to skip scoping | v1.3 |
| Fire-and-forget memorization via asyncio.create_task | ✓ Good — non-blocking, pool slot released immediately | v1.3 |
| Sync httpx for pre-spawn retrieval (not asyncio) | ✓ Good — avoids RuntimeError in async context | v1.3 |
| CATEGORY_SECTION_MAP for memory routing | ✓ Good — explicit three-bucket output, clean routing | v1.3 |
| 2,000-char SOUL memory budget (hardcoded) | ✓ Good — simple, prevents template bloat | v1.3 |
| `loop.add_signal_handler` for SIGTERM drain | ✓ Good — avoids fcntl deadlock risk with asyncio loop | v1.4 |
| Idempotency guard on `register_shutdown_handler()` | ✓ Good — safe to call from multiple code paths | v1.4 |
| Cosine similarity for conflict detection (0.85) | ✓ Good — Sitting at related-duplicate boundary per benchmarks | v1.5 |
| Keyword-frequency clustering for SOUL suggestions | ✓ Good — low false-positive rate; adaptive threshold for small sets | v1.5 |
| SHA-based commit cursor for delta snapshot retrieval | ✓ Good — ISO timestamp cursor in state.json | v1.4 |
| Approval gate validates SOUL diff before write | ✓ Good — prevents structural injection and safety-constraint removal | v1.4 |
| Path resolver requires explicit project_id | ✓ Good — no project-id fallback avoids path leakage | v1.5 |
| validation returns (fatal, warnings) tuple | ✓ Good — testable UI without affecting terminal stdout/stderr logic | v1.5 |
| additionalProperties violations as warnings | ✓ Good — unknown fields are forward-compatible | v1.5 |
| Event bus daemon handlers with ImportError guard | ✓ Good — fire-and-forget events never block state mutation | v1.5 |
| Field ownership check for Notion sync (`_should_write_status`) | ✓ Good — prevents OpenClaw from overwriting user-owned fields | v1.5 |
| 4 states vs 3 or 5 for autonomy | ✓ Good — distinct initialization, retry visibility, proper cleanup | v1.6 |
| 0.6 escalation threshold default | ✓ Good — balances caution and throughput | v1.6 |
| 1 retry default for L3 containers | ✓ Good — catches ~70% of transient issues, doesn't block pool | v1.6 |
| Fire-and-forget events | ✓ Good — never block task execution on event handling | v1.6 |

## Primary Docs

- docs/SWARM_PLAN.md
- workspace/occc/README.md
- .planning/MILESTONES.md
- DEV_WF_FINDINGS.md

---
*Last updated: 2026-02-26 after v1.6 milestone*
