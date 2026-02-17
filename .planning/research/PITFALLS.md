# Domain Pitfalls

**Domain:** AI Swarm Orchestration
**Researched:** 2026-02-17

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Cognitive Overload ("Brain Fog")
**What goes wrong:** A single agent manages multiple projects, leading to hallucinated dependencies and toolchain conflicts (e.g., trying to `npm install` in a Python environment).
**Why it happens:** Stale tokens in the context window from previous project tasks.
**Consequences:** High error rates, broken builds, developer frustration.
**Prevention:** Implement strict hierarchical isolation (Grand Architect Protocol).
**Detection:** Agent attempts to use tools irrelevant to the current file extension.

### Pitfall 2: VRAM Contention
**What goes wrong:** Multiple ML tasks or inference requests trigger Out-Of-Memory (OOM) errors.
**Why it happens:** Lack of resource arbitration for the GPU.
**Consequences:** Container crashes, lost training progress.
**Prevention:** Use an "Infrastructure Commander" (PM-ML) to serialize GPU-heavy tasks via Lane Queues.
**Detection:** `nvidia-smi` showing >95% VRAM usage followed by process termination.

## Moderate Pitfalls

### Pitfall 1: State Desync
**What goes wrong:** Dashboard shows agents are "Working" but they are actually "Idle" or "Error".
**Prevention:** Implement a standard "Heartbeat" hook that updates `state.json` on every tool execution.

### Pitfall 2: Permission Creep
**What goes wrong:** Tier 3 agents gaining write access to shared config directories.
**Prevention:** Use Read-Only (`:ro`) Docker mounts for all config files; only mount the project-specific workspace as Read-Write.

## Minor Pitfalls

### Pitfall 1: Log Noise
**What goes wrong:** "Live Feed" in Dashboard becomes unreadable due to excessive "Received message" logs.
**Prevention:** Filter logs by severity/source before writing to the shared feed.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Environment Setup | Incompatible Nvidia drivers on Ubuntu 24.04. | Use drivers 550+ and verify with `nvidia-container-cli info`. |
| Agent Definition | SOUL definitions too broad. | Enforce "Zero Code" for L1 and "No Implement" for L2. |
| Dashboard Deploy | Circular dependency on `state.json`. | Dashboard must be the last service to start and mounted RO. |

## Sources

- `/home/ollie/.openclaw/docs/plans/2026-02-17-grand-architect-protocol-design.md`
- `/home/ollie/.openclaw/workspace/occc/src/app/api/swarm/route.ts`
