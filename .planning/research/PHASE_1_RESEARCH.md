# Phase 1: Environment Substrate - Research

**Researched:** 2026-02-17
**Domain:** Infrastructure, Containerization, OpenClaw Gateway
**Confidence:** HIGH

## Summary

This research establishes the foundation for Phase 1: Environment Substrate. The OpenClaw project requires a tiered swarm architecture (Grand Architect Protocol) running on Ubuntu 24.04. The core components involve Docker isolation, Nvidia GPU support, and a central Gateway for agent communication.

**Primary recommendation:** Use OpenClaw's native agent isolation features paired with Docker volume mappings to enforce strict workspace boundaries for L2 and L3 agents.

## User Constraints (from CONTEXT.md)

*No CONTEXT.md was provided; research based on PROJECT.md and REQUIREMENTS.md.*

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SET-01 | Establish Ubuntu 24.04 host environment with Docker and Nvidia Container Toolkit. | Standard setup verified for 24.04 (LTS). |
| SET-02 | Configure OpenClaw root openclaw.json with gateway and lane queue settings. | `gateway` and `agents.defaults` sections identified. |
| SET-03 | Initialize OpenClaw Gateway on port 18789. | `openclaw gateway` command flags verified. |
| SEC-01 | Enforce permission-based access (e.g., PumplAI_PM restricted to /app/project). | Agent-specific `workspace` mapping and Docker isolation. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Docker | 27+ | Containerization | Industry standard for process isolation. |
| Nvidia Container Toolkit | Latest | GPU Passthrough | Required for AI acceleration on Nvidia hardware. |
| OpenClaw CLI | 2026.2.15 | Swarm Orchestration | Core system for agent management. |

## Architecture Patterns

### OpenClaw Gateway Configuration
The `openclaw.json` file controls the Gateway's behavior. The "lane queue" system in OpenClaw ensures that each session or agent operates in an isolated execution "lane" to prevent race conditions.

**Recommended `openclaw.json` snippet:**
```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "REPLACE_WITH_SECURE_TOKEN"
    }
  },
  "agents": {
    "defaults": {
      "maxConcurrent": 4,
      "subagents": {
        "maxConcurrent": 8
      }
    }
  }
}
```

### Permission-Based Access (SEC-01)
To restrict PumplAI_PM to `/app/project`, we use Docker volume mapping.
1. Define the agent in `openclaw.json`.
2. Map the host's project directory to the container's `/app/project`.
3. Set the `workspace` property in OpenClaw to `/app/project`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GPU Isolation | Custom CUDA scripts | Nvidia Container Toolkit | Official support for GPU slicing and passthrough. |
| Task Queuing | Custom Redis queue | OpenClaw Lane Queues | Built-in concurrency control and session affinity. |

## Common Pitfalls

### Pitfall 1: Port Collision
**What goes wrong:** Gateway fails to start because port 18789 is occupied.
**How to avoid:** Use `openclaw gateway --force` to kill existing listeners during development.

### Pitfall 2: Nvidia Driver Mismatch
**What goes wrong:** Docker containers cannot see the GPU despite the toolkit being installed.
**How to avoid:** Ensure the host Nvidia driver version matches the minimum requirements of the `nvidia-container-toolkit`. Use `nvidia-smi` on both host and container for verification.

## Code Examples

### Verification of Host Setup (SET-01)
```bash
# Check Docker
docker --version
docker run --rm hello-world

# Check Nvidia Toolkit
nvidia-smi
docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Gateway Initialization (SET-03)
```bash
# Start the gateway in the background
openclaw gateway run --port 18789 --auth token --token <your-token>
```

## Sources

### Primary (HIGH confidence)
- Local `openclaw.json` inspection.
- `openclaw --help` CLI documentation.
- Project `REQUIREMENTS.md`.

## Metadata
**Research date:** 2026-02-17
**Valid until:** 2026-03-17
