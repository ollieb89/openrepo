# Project: OpenClaw Agent Orchestration

## What This Is

A cognitive infrastructure layer for autonomous multi-agent systems. OpenClaw manages not just agent execution, but the organizational structure of agent swarms — proposing, scoring, and evolving the topology of how agents collaborate. Built on a battle-tested 3-tier hierarchy (v1.0-v1.6) with Docker isolation, memory, autonomy, and observability.

## Core Value

The system designs and refactors its own orchestration — proposing multi-agent structures, learning from human corrections, and improving structural reasoning over time.

## Current Milestone: v2.0 Structural Intelligence

**Goal:** OpenClaw proposes its own orchestration structure — pre-execution structural intelligence with inspectable reasoning and learning from corrections.

**Target features:**
- Topology as Data — swarm structures as explicit, serializable, versionable, diffable graph objects
- Structure Proposal Engine — multi-proposal (Lean/Balanced/Robust archetypes) with scored rubric and justification
- Dual Correction System — soft feedback (re-propose) + hard direct edit (execute, diff-analyze asynchronously)
- Structural Memory — topology diffs, correction rationales, pattern extraction, preference profiling
- Topology Observability — proposed/approved structures, correction history, structural diff timeline, confidence evolution

**Architectural decisions:**
- Multi-proposal by default (2-3 scored candidates, not single-best)
- Fixed archetypes: Lean (minimal roles, fast), Balanced (explicit coordination), Robust (specialized, safe)
- Common scoring rubric: complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence
- Correction as training: feedback updates heuristics, direct edits analyzed as diffs, both feed structural memory
- Post-edit behavior: execute immediately, analyze diff asynchronously, surface non-blocking notes when high-confidence original contradicts edit

**Explicitly NOT in scope (v2.1+):**
- Mid-flight topology adaptation
- Auto-scaling during execution
- Self-refactoring execution graphs
- Dynamic role spawning at runtime

## Requirements

### Validated

- v1.0: 3-tier hierarchy (L1/L2/L3) with Docker isolation, Jarvis Protocol state engine, semantic snapshots, dashboard
- v1.1: Multi-project support, SOUL template engine, project CLI, dashboard project switcher
- v1.2: Structured logging, state reliability, mtime caching, task lifecycle observability, per-project pool config, metrics panel
- v1.3: memU memory service, bidirectional memory pipeline, SOUL injection, L3 in-execution queries, dashboard memory panel
- v1.4: Graceful shutdown, pool recovery, memory health monitoring, L1 SOUL suggestions, delta-cursor retrieval
- v1.5: Config consolidation, schema validation, migration CLI, env var precedence, Docker health checks, Notion sync
- v1.6: Autonomy framework, self-directed decomposition, confidence-based escalation, context-aware tools, progress self-monitoring

### Active

- [ ] Topology as data model
- [ ] Structure proposal engine
- [ ] Dual correction system
- [ ] Structural memory
- [ ] Topology observability

### Out of Scope

- Mid-flight adaptation — requires topology-as-data to be stable first; v2.1+
- Auto-scaling — dependent on structural scoring being proven; v2.1+
- Self-refactoring execution graphs — research-grade complexity; v2.1+
- Dynamic role spawning — needs runtime topology mutation; v2.1+
- Consumer-facing UI — audience is AI-native product teams, platform teams, researchers
- Protocol standardization (ACP) — deferred until structural intelligence is proven internally

## Context

- 60 phases shipped across 6 milestones (v1.0-v1.6)
- ~340K LOC across Python + TypeScript
- Existing infrastructure: Gateway, Docker containers, memU memory, autonomy framework, dashboard
- The system currently executes structure designed by humans; this milestone makes it propose structure
- Target users: AI-native product teams, internal platform teams, multi-agent researchers

## Constraints

- **Tech stack**: Python (orchestration), TypeScript (Gateway/Dashboard) — extend, don't replace
- **Memory**: Must integrate with existing memU service for structural memory
- **Isolation**: Docker container model stays; topology proposals must be expressible as container configurations
- **Backwards compatibility**: v1.x agent configs, SOUL templates, and spawn mechanisms must still work

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Multi-proposal over single-best | Exposes reasoning surface, enables splice corrections, richer learning signal | -- Pending |
| Three fixed archetypes (Lean/Balanced/Robust) | Keeps proposals interpretable, avoids minor variations | -- Pending |
| Common scoring rubric (7 dimensions) | Enables comparative confidence, structured observability, diffable preferences | -- Pending |
| Execute-then-analyze on direct edit | Respects user authority, non-blocking, learns asynchronously | -- Pending |
| Pre-execution only (no mid-flight) | Scopes milestone cleanly; adaptation is v2.1+ | -- Pending |

---
*Last updated: 2026-03-03 after v2.0 milestone initialization*
