# Project: OpenClaw (Grand Architect Protocol)

## What This Is

OpenClaw is an AI Swarm Orchestration system implementing the Grand Architect Protocol — a 3-tier hierarchical architecture where AI agents delegate, execute, and synchronize work through Docker containers and git-based workflows. The occc dashboard provides real-time visibility into swarm operations.

## Core Value

Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## Current Milestone: v1.2 Orchestration Hardening

**Goal:** Make the orchestration layer production-grade — fix silent failures, improve performance under concurrency, add structured observability, and complete per-project pool isolation with dashboard metrics.

**Target features:**
- Reliability hardening: state recovery, graceful shutdown, error classification, config validation
- Performance: Docker client pooling, state caching, batch updates, subprocess reduction
- Full observability: structured JSON logging, task lifecycle metrics, pool utilization, adaptive monitoring
- Per-project pool config: configurable concurrency limits, isolated/shared mode, queue overflow policy
- Dashboard: agent hierarchy filtering per project, usage metrics visualization

## Tech Stack

- **Core:** OpenClaw CLI, Bun, Docker 29.1.5
- **Orchestration:** Python 3 (state engine, snapshots, spawn, monitoring, project_config)
- **Frontend:** Next.js 16 (App Router), Tailwind 4, SWR, Zod
- **Container:** Debian bookworm-slim L3 images, Nvidia Container Toolkit
- **OS:** Ubuntu 24.04 LTS

## Current State

**Shipped:** v1.1 Project Agnostic (2026-02-23)
**LOC:** ~27,400 (Python + TypeScript + JavaScript)

Architecture operational:
- L1 (ClawdiaPrime) → L2 (PumplAI_PM) → L3 (Ephemeral Specialists) delegation chain
- Jarvis Protocol state synchronization with file locking
- Semantic snapshot system with git staging branches
- occc mission control dashboard with SSE real-time streaming and project switching
- Docker isolation with `no-new-privileges`, `cap_drop ALL`, memory/CPU limits

Multi-project framework (v1.1):
- Per-project state/snapshot path resolution via `project_config.py`
- SOUL template engine with default + per-project override mechanism
- Namespaced container naming and per-project pool isolation (PoolRegistry)
- `openclaw project` CLI with init/list/switch/remove and template presets
- Dashboard project selector with project-scoped API routes and SSE streams
- `OPENCLAW_PROJECT` env var takes priority over `active_project` in config

Known limitations:
- Gateway startup is manual (runtime dependency)
- COM-04 snapshot capture cannot be E2E tested when workspace is a git submodule
- CLI routing replaces lane queue REST API (accepted spec deviation)
- L3 pool isolation is shared by default; per-project isolated pools deferred to v1.2

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

### Active

(Defined in REQUIREMENTS.md for v1.2)

### Out of Scope

- Multi-host swarm — single-host only
- Persistent L3 agents — ephemeral containers by design
- REST lane queue API — CLI routing accepted as equivalent
- LLM-generated SOULs at init time — non-determinism in CLI init operations
- Per-project Docker networks — no inter-container networking needed
- CWD-based project auto-detection — conflicts with scripts calling openclaw from arbitrary directories
- Cross-project agent sharing — conflicts with 1:1 L2-to-project assumption

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

## Primary Docs

- docs/SWARM_PLAN.md
- workspace/occc/README.md
- .planning/MILESTONES.md
- DEV_WF_FINDINGS.md

---
*Last updated: 2026-02-24 after v1.2 milestone started*
