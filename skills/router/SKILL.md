---
name: router
description: Enables L1 orchestrators to delegate tasks to L2 project managers via the OpenClaw Gateway.
metadata:
  openclaw:
    emoji: "🔀"
    category: "orchestration-core"
---
# SKILL: Hub-and-Spoke Router

## Tools
- `dispatch_directive`: Send a high-level instruction to a subordinate agent.

## Usage
```bash
openclaw exec clawdia_prime "dispatch_directive --targetId pumplai_pm --directive 'synchronize workspace status'"
```
