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

(None — next milestone not yet defined. Use `/gsd:new-milestone` to begin.)

### Out of Scope

- Mid-flight adaptation — requires topology-as-data to be stable first; v2.1+
- Auto-scaling — dependent on structural scoring being proven; v2.1+
- Self-refactoring execution graphs — research-grade complexity; v2.1+
- Dynamic role spawning — needs runtime topology mutation; v2.1+
- Consumer-facing UI — audience is AI-native product teams, platform teams, researchers
- Protocol standardization (ACP) — deferred until structural intelligence is proven internally

## Context

- 67 phases shipped across 8 milestones (v1.0-v2.0)
- ~365K LOC across Python + TypeScript
- Existing infrastructure: Gateway, Docker containers, memU memory, autonomy framework, topology engine, dashboard
- The system now proposes its own orchestration structure before execution, learning from human corrections
- Target users: AI-native product teams, internal platform teams, multi-agent researchers

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
*Last updated: 2026-03-04 after v2.0 milestone*
