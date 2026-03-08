# Project: OpenClaw Agent Orchestration

## What This Is

A cognitive infrastructure layer for autonomous multi-agent systems. OpenClaw manages not just agent execution, but the organizational structure of agent swarms — proposing, scoring, and evolving the topology of how agents collaborate. Built on a battle-tested 3-tier hierarchy (v1.0-v1.6) with Docker isolation, memory, autonomy, and observability. v2.0 added pre-execution structural intelligence: the system designs its own orchestration before executing it. v2.1 activated the real-time event pipeline: live L3 output streams to the dashboard, all directives route through the gateway API, and the unified metrics endpoint consolidates cross-layer observability.

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
- ✓ Tech debt cleared — v2.1 (test failures fixed, TopologyProposal consolidated, hardcoded paths removed)
- ✓ Live event bridge — v2.1 (Unix socket server auto-starts, all 17 event types flow to dashboard SSE)
- ✓ Gateway-only dispatch — v2.1 (execFileSync fallback removed, bootstrap mode for setup CLI)
- ✓ Unified AgentRegistry — v2.1 (auto-discovery, drift detection, per-agent config as source of truth)
- ✓ Terminal streaming dashboard — v2.1 (live L3 output panel, auto-scroll, click-to-open task stream)
- ✓ Pipeline timeline & unified metrics — v2.1 (/api/metrics consolidates Python + dashboard; PipelineStrip shows L1→L2→L3)
- ✓ INTG-01 live E2E verified — v2.1 (Playwright-confirmed: dispatch → task board → live stream → metrics → event order)

### Active

*(Planning next milestone — see /gsd:new-milestone)*

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

- 82 phases shipped across 9 milestones (v1.0-v2.1)
- ~88,500 LOC across Python + TypeScript
- Infrastructure: Gateway (HTTP API), Docker L3 containers, memU memory, autonomy framework, topology engine, event bridge (Unix socket), dashboard (Next.js)
- The system proposes its own orchestration structure, learns from corrections, and now streams live agent output to operators in real-time
- Target users: AI-native product teams, internal platform teams, multi-agent researchers
- All v2.1 tech debt resolved: single TopologyProposal class, no hardcoded paths, all tests passing
- Event bridge is the operational dependency: dashboard SSE requires Python orchestration process to be running

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
| Dual TopologyProposal classes | Separate proposer vs presentation concerns; bridged by conversion shim | ✓ Resolved — consolidated in v2.1 Phase 68 |
| Dataclasses over Pydantic | Consistent with AgentSpec pattern in existing codebase | ✓ Good — lightweight, no dependency added |
| Gateway-only dispatch | Remove execFileSync fallback; all L1→L2 directives through HTTP API | ✓ Good — clean dispatch boundary, gateway is required runtime dep |
| event_bus.emit() as single publish path | Wrap all event emissions through bus; bridge handler forwards to socket | ✓ Good — no double-emission, bridge failure is non-fatal warning |
| In-memory event ring buffer | Shared module-level ring (100 events per task) for SSE reconnect replay | ✓ Good — sufficient for v2.1; defer disk persistence to v2.2 |
| Per-agent config.json as source of truth | AgentRegistry merges per-agent files into openclaw.json at startup with drift warnings | ✓ Good — eliminates manual openclaw.json sync |
| project_id on AutonomyEvent | Optional[str] field threads project context through hooks._task_project_map | ✓ Good — GAP-03 closed; alerts now project-scoped |

---
*Last updated: 2026-03-08 after v2.1 milestone*
