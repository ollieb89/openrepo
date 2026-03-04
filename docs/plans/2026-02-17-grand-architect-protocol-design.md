# Grand Architect Protocol Design

**Date:** 2026-02-17
**Status:** Validated
**Context:** Unified architectural redesign for OpenClaw Swarm, integrating the "Federated Swarm" vision with "Rewrite" technical constraints.

## 1. Executive Summary
The "Grand Architect" protocol is a strictly separated, three-tiered swarm topology designed for an Ubuntu 24.04 LTS host. It eliminates cognitive load ("brain fog") by isolating concerns between project management and technical execution. The architecture is optimized for high-performance SaaS (PumplAI), ML Infrastructure (ml-local), Healthcare (GeriApp), and Security (ShDebug).

## 2. Tiered Command Structure
*   **Level 1: Head of Development (Clawdia Prime)**
    *   **Role:** The "Brain" and global state maintainer.
    *   **Network:** Host network for orchestration.
    *   **Responsibility:** Translating business requirements into project tasks.
*   **Level 2: Project Managers (Federated PMs)**
    *   **Role:** Domain-specific orchestrators.
    *   **Project Focus:** PumplAI, ml-local, GeriApp, ShDebug.
    *   **Responsibility:** Managing the lifecycle of their respective stacks and mediating between Level 1 and Level 3.
*   **Level 3: Specialist Workers (The Hands)**
    *   **Role:** Execution agents in Docker sandboxes (`non-main`).
    *   **Specialties:** `nuxt_pm` (Vue 3/Nuxt 4/Bun), `python_worker` (CUDA 12.8/Inference), `security_auditor` (WCAG AA/Security).

## 3. Technical Configuration
### Environment & Runtime
*   **Host OS:** Ubuntu 24.04 LTS.
*   **Runtime:** Node.js 22.x (LTS) enforced globally.
*   **Package Manager:** Bun (default for frontend/scaffolding).
*   **Workspace:** Unified `$HOME/Development` mapped via Docker volumes.

### Master Configuration (`openclaw.json`)
```json
{
  "networks": {
    "primary": {
      "gateway": "http://localhost:18789",
      "mode": "host"
    },
    "sandbox": {
      "mode": "docker",
      "image": "openclaw/worker-node22-cuda12.8:latest",
      "volumes": ["$HOME/Development:/app/workspace"]
    }
  },
  "agents": {
    "ClawdiaPrime": {
      "role": "Level 1: Head of Dev",
      "network": "primary",
      "capabilities": ["exec", "fs", "agentToAgent"],
      "memory": "semantic-snapshot"
    },
    "ML_ProjectManager": {
      "role": "Level 2: ML Orchestrator",
      "network": "sandbox",
      "parent": "ClawdiaPrime",
      "capabilities": ["agentToAgent", "fs"]
    },
    "PythonWorker": {
      "role": "Level 3: CUDA Specialist",
      "network": "sandbox",
      "parent": "ML_ProjectManager",
      "capabilities": ["exec", "canvas"],
      "resources": { "gpu": "all" }
    }
  }
}
```

## 4. Communication & Data Flow
*   **Hub and Spoke:** Communication flows through Level 2 PMs to prevent "State Drift" and cross-contamination of dependencies.
*   **Context Propagation:** Serialization of context into `task_packet.json` for all delegated tasks.
*   **Semantic Snapshots:** Periodic snapshots of workspace subdirectories (e.g., `ml-local`) to allow rapid state verification without full tree traversal.

## 5. Security & Isolation
*   **Hardened Sandboxes:** Level 3 workers use `sandbox: "non-main"` with restricted `allowlist` (exec, browser, fs, canvas, agentToAgent).
*   **Workspace Constraints:** Execution limited to `/app/workspace` subdirectories; no access to host SSH keys or sensitive env vars.
*   **Command Sanitization:** Regex filtering for all `exec` calls in high-risk specialists (e.g., `python_worker`).
