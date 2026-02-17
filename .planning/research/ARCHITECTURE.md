# Architecture Patterns

**Domain:** Hierarchical AI Swarms
**Researched:** 2026-02-17

## Recommended Architecture

The system follows the **Grand Architect Protocol**, a strictly separated three-tier hierarchy utilizing a hub-and-spoke communication model.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Tier 1: ClawdiaPrime** | Strategy & Routing. Identifies project context. Zero code. | User (Telegram), Tier 2 Agents. |
| **Tier 2: Project PMs** | Domain architects. Planning, standards, and QA gating. | Tier 1, Tier 3 Specialists. |
| **Tier 3: Specialists** | Implementation. Writing code, running tests, ML training. | Tier 2, Project Workspace. |
| **OpenClaw Gateway** | Central message bus and node registry. | All Agents. |
| **occc Dashboard** | Monitoring and visualization. Read-only view of state. | Shared `state.json`. |

### Data Flow

1. **Instruction Flow:** User (Telegram) → Tier 1 (Routes) → Tier 2 (Plans) → Tier 3 (Builds).
2. **State Flow:** Tier 3 (Updates status) → Shared `state.json` ← Dashboard (Polls every 2s).
3. **Workspace Flow:** Specialists mounted to specific project subdirs (e.g., `/workspace/pumplai`).

## Patterns to Follow

### Pattern 1: Tiered Isolation
**What:** Physical separation of agent environments using Docker.
**When:** Always. Specialists must not share toolchains.
**Example:**
```yaml
# docker-compose.claw.yml
services:
  worker_ml:
    volumes:
      - ./workspace/ml-infra:/root/workspace
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, capabilities: [gpu]}]
```

### Pattern 2: Semantic Snapshotting
**What:** Using the Accessibility Tree instead of raw screenshots for UI verification.
**When:** UI testing in Tier 3 Frontend workers.
**Rationale:** High precision for LLMs, lower token cost, zero hallucination of DOM elements.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Flattened Routing
**What:** L1 agents talking directly to L3 workers without PM mediation.
**Why bad:** Loss of architectural coherence; L1 cannot handle file-level complexity across multiple repos.
**Instead:** Always route through a Domain PM who maintains the project "Source of Truth" (e.g., `pumplai.md`).

## Scalability Considerations

| Concern | At 5 agents | At 50 agents | At 500 agents |
|---------|--------------|--------------|-------------|
| **Memory** | Shared `state.json` | Redis Cluster | Distributed Key-Value Store |
| **Compute** | Single Host (Ubuntu) | Docker Swarm / K8s | Multi-region Kubernetes |
| **Routing** | Simple Skill | Vector-based Context router | Federated Routing Network |

## Sources

- `/home/ollie/.openclaw/docs/SWARM_PLAN.md`
- `/home/ollie/.openclaw/docs/plans/2026-02-17-grand-architect-protocol-design.md`
