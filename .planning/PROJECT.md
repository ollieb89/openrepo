# Project: OpenClaw (Grand Architect Protocol)

## What This Is

OpenClaw is an AI Swarm Orchestration system implementing the Grand Architect Protocol — a 3-tier hierarchical architecture where AI agents delegate, execute, and synchronize work through Docker containers and git-based workflows. The occc dashboard provides real-time visibility into swarm operations.

## Core Value

Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## Tech Stack

- **Core:** OpenClaw CLI, Bun, Docker 29.1.5
- **Orchestration:** Python 3 (state engine, snapshots, spawn, monitoring)
- **Frontend:** Next.js 16 (App Router), Tailwind 4, SWR, Zod
- **Container:** Debian bookworm-slim L3 images, Nvidia Container Toolkit
- **OS:** Ubuntu 24.04 LTS

## Current State

**Shipped:** v1.0 Grand Architect Protocol Foundation (2026-02-23)
**LOC:** ~14,600 (Python + TypeScript + JavaScript)

Architecture operational:
- L1 (ClawdiaPrime) → L2 (PumplAI_PM) → L3 (Ephemeral Specialists) delegation chain
- Jarvis Protocol state synchronization with file locking
- Semantic snapshot system with git staging branches
- occc mission control dashboard with SSE real-time streaming
- Docker isolation with `no-new-privileges`, `cap_drop ALL`, memory/CPU limits

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

### Active

(None — awaiting next milestone definition)

### Out of Scope

- Multi-host swarm — single-host only for v1.0
- Persistent L3 agents — ephemeral containers by design
- REST lane queue API — CLI routing accepted as equivalent

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

## Primary Docs

- docs/SWARM_PLAN.md
- workspace/occc/README.md
- .planning/MILESTONES.md

---
*Last updated: 2026-02-23 after v1.0 milestone*
