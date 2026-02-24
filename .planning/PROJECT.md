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

## Current Milestone: v1.3 Agent Memory

**Goal:** Integrate memU memory framework as a standalone service so agents learn across sessions — L3 outcomes and L2 decisions are memorized, and relevant context is retrieved before task execution.

**Target features:**
- Standalone memU service in Docker with PostgreSQL+pgvector backend
- Internal REST API for memory operations (memorize, retrieve, CRUD)
- Per-agent + per-project memory scoping
- L3 auto-memorization of task outcomes (git diff + conversation)
- L2 memorization of review decisions (merge/reject + reasoning)
- Pre-spawn context retrieval and SOUL template injection
- L3 in-execution memory queries for task-specific lookups
- Dashboard memory panel (categories, items, search)

## Current State

**Shipped:** v1.2 Orchestration Hardening (2026-02-24)
**LOC:** ~22,800 (Python + TypeScript)

Architecture operational:
- L1 (ClawdiaPrime) → L2 (PumplAI_PM) → L3 (Ephemeral Specialists) delegation chain
- Jarvis Protocol state synchronization with file locking, backup-on-write, and corruption recovery
- Semantic snapshot system with git staging branches
- occc mission control dashboard with SSE real-time streaming, project switching, and metrics visualization
- Docker isolation with `no-new-privileges`, `cap_drop ALL`, memory/CPU limits

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
- Monitor cache fix: JarvisState reuse across poll cycles for cache hit performance

Known limitations:
- Gateway startup is manual (runtime dependency)
- COM-04 snapshot capture cannot be E2E tested when workspace is a git submodule
- CLI routing replaces lane queue REST API (accepted spec deviation)

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

### Active

- [ ] Standalone memU memory service (Docker + PostgreSQL+pgvector)
- [ ] Internal REST API for memory operations
- [ ] Per-agent + per-project memory scoping
- [ ] L3 auto-memorization of task outcomes
- [ ] L2 memorization of review decisions
- [ ] Pre-spawn context retrieval and SOUL injection
- [ ] L3 in-execution memory queries
- [ ] Dashboard memory panel

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
- Docker health checks — defer to container hardening milestone

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
| memU as self-hosted library in standalone Docker service | — Pending | v1.3 |
| PostgreSQL+pgvector for memory storage | — Pending | v1.3 |
| Per-agent + per-project memory scoping | — Pending | v1.3 |
| L2 proxy + L3 direct access (both paths) | — Pending | v1.3 |

## Primary Docs

- docs/SWARM_PLAN.md
- workspace/occc/README.md
- .planning/MILESTONES.md
- DEV_WF_FINDINGS.md

---
*Last updated: 2026-02-24 after v1.3 milestone started*
