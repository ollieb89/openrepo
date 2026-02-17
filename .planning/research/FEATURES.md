# Feature Landscape

**Domain:** AI Swarm Orchestration / Monitoring
**Researched:** 2026-02-17

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Task Routing | Users need high-level intents routed to specific projects. | Medium | Handled by Tier 1 (ClawdiaPrime). |
| Real-time Status | Monitoring agent activity (Idle/Working/Planning). | Low | Polled via Dashboard (occc). |
| Project Isolation | Ensuring code for Project A doesn't bleed into Project B. | High | Physical enforcement via Docker volumes. |
| Log Aggregation | Centralized view of agent reasoning and errors. | Medium | Stored in `logs/` and surfaced in Dashboard. |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 3-Tier Hierarchy | Eliminates "Brain Fog" by filtering context at each level. | High | Strategic (L1) -> Tactical (L2) -> Execution (L3). |
| Semantic Snapshots | UI verification without heavy token cost of screenshots. | Medium | Uses Accessibility Tree data for verification. |
| GPU Arbitration | Serializes ML tasks to prevent VRAM OOM. | High | Managed by PM-ML (Infrastructure Commander). |
| Telegram Uplink | Ubiquitous control plane for the swarm via mobile messaging. | Low | Integrated via OpenClaw Channels. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-Project Writers | Agents writing to multiple projects creates cross-repo pollution. | Strict project-scoped write permissions. |
| L1 Implementation | Head agent writing code increases risk of strategic hallucination. | L1 Routes ONLY; L3 Builds. |
| Synchronous Block | Waiting for long-running ML jobs blocks the entire swarm. | Use Lane Queues for parallel execution. |

## Feature Dependencies

```
Docker Isolation → Project-Scoped Volumes → Tier 3 Specialist Deployment
User Intent → Tier 1 Routing → Tier 2 Planning → Tier 3 Execution
Jarvis Protocol (state.json) → occc Dashboard Monitoring
```

## MVP Recommendation

Prioritize:
1. **Tier 1 Routing Logic:** Foundation of the swarm orchestration.
2. **Docker Isolation:** Secure physical substrate for agents.
3. **Dashboard Matrix View:** Essential for human oversight of the complex hierarchy.

Defer: **GPU Load Balancing:** Manual serialization via PM-ML is sufficient for initial pilot.

## Sources

- `/home/ollie/.openclaw/docs/SWARM_PLAN.md`
- `/home/ollie/.openclaw/workspace/occc/src/app/page.tsx`
