# Project: OpenClaw Agent Orchestration

## What This Is

A cognitive infrastructure layer for autonomous multi-agent systems. OpenClaw manages not just agent execution, but the organizational structure of agent swarms — proposing, scoring, and evolving the topology of how agents collaborate. Built on a battle-tested 3-tier hierarchy (v1.0-v1.6) with Docker isolation, memory, autonomy, and observability. v2.0 added pre-execution structural intelligence: the system now designs its own orchestration before executing it.

## Core Value

The system designs and refactors its own orchestration — proposing multi-agent structures, learning from human corrections, and improving structural reasoning over time.

## Requirements

### Validated

- v1.0: 3-tier hierarchy (L1/L2/L3) with Docker isolation, Jarvis Protocol state engine, semantic snapshots, dashboard
- v1.1: Multi-project support, SOUL template engine, project CLI, dashboard project switcher
- v1.2: Structured logging, state reliability, mtime caching, task lifecycle observability, per-project pool config, metrics panel
- v1.3: memU memory service, bidirectional memory pipeline, SOUL injection, L3 in-execution queries, dashboard memory panel
- v1.4: Graceful shutdown, pool recovery, memory health monitoring, L1 SOUL suggestions, delta-cursor retrieval
- v1.5: Config consolidation, schema validation, migration CLI, env var precedence, Docker health checks, Notion sync
- v1.6: Autonomy framework, self-directed decomposition, confidence-based escalation, context-aware tools, progress self-monitoring
- ✓ Topology as data model — v2.0 (graph objects with JSON serialization, versioning, diffing, archetype classification)
- ✓ Structure proposal engine — v2.0 (LLM-powered multi-candidate proposals with 7-dimension rubric scoring, constraint linting)
- ✓ Dual correction system — v2.0 (soft feedback + hard direct edit with approval gate enforcement)
- ✓ Structural memory — v2.0 (decay-weighted preference profiling, epsilon-greedy exploration, LLM pattern extraction, L3 isolation)
- ✓ Topology observability — v2.0 (React Flow DAG, dual-panel comparison, correction timeline, confidence evolution chart)

### Active

## Current Milestone: v2.1 Programmatic Integration & Real-Time Streaming

**Goal:** Replace CLI-level coupling with programmatic APIs, activate existing event infrastructure, and deliver live L3 output streaming to the dashboard.

**Target features:**
- Tech debt resolution (test failures, TopologyProposal consolidation, hardcoded path removal)
- Event bridge activation (start Unix socket server, wire event bus, dashboard SSE verification)
- Gateway-only dispatch (remove execFileSync fallback, route all directives through gateway HTTP API)
- Unified Agent Registry (merge openclaw.json + per-agent configs, auto-discovery, resolve config drift)
- L3 output streaming (Docker logs → event bus → Unix socket → dashboard SSE, live terminal view)
- Cross-runtime observability (unified metrics endpoint, pipeline timeline view L1→L2→L3)
- SOUL injection verification (ensure dynamic variables populated at spawn time, add topology context)
- Docker base image sharing (shared base image, rebase L3 Dockerfile)
- Bootstrap mode (gateway-free startup flag for initial setup)
- Integration E2E verification

### Out of Scope

- Mid-flight topology adaptation — requires stable integration layer first; v2.2+
- Auto-scaling — dependent on structural scoring being proven; v2.2+
- Self-refactoring execution graphs — research-grade complexity; v2.2+
- Dynamic role spawning — needs runtime topology mutation; v2.2+
- Multi-agent coordination (handoff protocols, shared task queues, collaborative memory, conflict resolution) — planned for v2.2
- Consumer-facing UI — audience is AI-native product teams, platform teams, researchers
- Protocol standardization (ACP) — deferred until structural intelligence is proven internally
- Event persistence to disk/DB — in-memory buffer sufficient for v2.1; defer replay/compliance to v2.2
- Git submodule wiring — deprioritized per user feedback

## Context

- 67 phases shipped across 8 milestones (v1.0-v2.0)
- ~365K LOC across Python + TypeScript
- Existing infrastructure: Gateway, Docker containers, memU memory, autonomy framework, topology engine, dashboard
- The system now proposes its own orchestration structure before execution, learning from human corrections
- Target users: AI-native product teams, internal platform teams, multi-agent researchers
- Event infrastructure exists but isn't wired: Unix socket transport, 17 event types defined, dashboard SSE bridge — server never started
- Router already has fetch-to-gateway primary path with execFileSync fallback — v2.1 removes fallback
- Per-agent config.json files are richer than openclaw.json entries — registry consolidation needed
- Pre-existing test failures: async event loop issues in test_proposer.py, nested loop conflicts in test_state_engine_memory.py
- Dual TopologyProposal classes (proposer.py vs proposal_models.py) with incompatible field names (graph vs topology)
- Hardcoded ~/ and ~/ paths in 15+ files including active runtime configs

## Constraints

- **Tech stack**: Python (orchestration), TypeScript (Gateway/Dashboard) — extend, don't replace
- **Memory**: Must integrate with existing memU service for structural memory
- **Isolation**: Docker container model stays; topology proposals must be expressible as container configurations
- **Backwards compatibility**: v1.x agent configs, SOUL templates, and spawn mechanisms must still work

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Multi-proposal over single-best | Exposes reasoning surface, enables splice corrections, richer learning signal | ✓ Good — users compare archetypes effectively |
| Three fixed archetypes (Lean/Balanced/Robust) | Keeps proposals interpretable, avoids minor variations | ✓ Good — clear differentiation in practice |
| Common scoring rubric (7 dimensions) | Enables comparative confidence, structured observability, diffable preferences | ✓ Good — rubric scores flow to dashboard charts |
| Execute-then-analyze on direct edit | Respects user authority, non-blocking, learns asynchronously | ✓ Good — no latency on hard corrections |
| Pre-execution only (no mid-flight) | Scopes milestone cleanly; adaptation is v2.1+ | ✓ Good — clean boundary, deferred complexity |
| Topology data in separate files | Avoids fcntl contention with L3 workspace-state.json | ✓ Good — no lock conflicts observed |
| Dual TopologyProposal classes | Separate proposer vs presentation concerns; bridged by conversion shim | ⚠️ Revisit — tech debt, consolidate in future |
| Dataclasses over Pydantic | Consistent with AgentSpec pattern in existing codebase | ✓ Good — lightweight, no dependency added |

---
*Last updated: 2026-03-04 after v2.1 milestone initialization*
