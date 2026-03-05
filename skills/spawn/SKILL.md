---
name: spawn
description: L3 Specialist Container Spawning Module for isolated Docker containers with GPU passthrough and state synchronization.
metadata:
  openclaw:
    emoji: "🐳"
    category: "orchestration-core"
---

# SKILL: L3 Specialist Container Spawning

## Overview
Implements the spawn skill for L2 to spawn isolated L3 containers with Docker Python SDK. Handles security isolation, GPU passthrough, and state synchronization. Project-aware — resolves project identity at spawn time.

## Tools
- `spawn_l3`: Create and manage isolated L3 specialist containers
- `pool_status`: Check container pool status and resource utilization
- `cleanup`: Remove stopped containers and clean up resources

## Usage
```bash
# Spawn a new L3 specialist
openclaw exec pumplai_pm "spawn_l3 --task-id task-001 --specialist python-dev --workspace /path/to/project"

# Check pool status
openclaw exec pumplai_pm "pool_status"

# Cleanup old containers
openclaw exec pumplai_pm "cleanup --older-than 24h"
```

## Features
- **Security Isolation**: Each L3 specialist runs in isolated Docker container
- **GPU Passthrough**: Support for CUDA GPU acceleration when available
- **State Synchronization**: Automatic workspace state mounting and synchronization
- **Memory Integration**: Pre-fetches memories and injects into L3 SOUL context
- **Project Awareness**: Resolves project identity and workspace paths automatically

## Implementation
The skill uses the existing `spawn.py` module which provides:
- Docker container lifecycle management
- Volume mounting for workspace and state
- Memory context injection via memU integration
- Resource monitoring and cleanup

## Dependencies
- Docker Python SDK
- openclaw state engine
- memU memory service
- Project configuration system
