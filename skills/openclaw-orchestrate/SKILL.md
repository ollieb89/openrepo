---
name: openclaw-orchestrate
description: Multi-tier agent orchestration in OpenClaw's L1→L2→L3 hierarchy. Use when routing directives from L1 (ClawdiaPrime) to L2 (Project Manager), delegating tasks from L2 to L3 specialists, building or modifying the router skill, coordinating parallel agent runs, or debugging delegation failures. Triggers for: "dispatch a task", "delegate to L3", "orchestration", "route a directive", "L1/L2/L3 workflow", "tier hierarchy", "agent coordination", "parallel agents", "openclaw router".
metadata:
  openclaw:
    emoji: "🏗️"
    category: "orchestration"
---

# OpenClaw Multi-Tier Orchestration

## Tier Overview

```
L1: ClawdiaPrime (Strategic Orchestrator)
 └─ L2: Project Manager (Tactical — per-project)
     └─ L3: Ephemeral Specialists (Isolated Docker Containers)
```

## L1 → L2 Directive Routing

L1 dispatches via `skills/router/index.js` using the CLI:
```bash
openclaw agent --agent {targetAgentId} --message "{directive}"
```

**Key rules:**
- `execFileSync` with argument arrays — **no shell string concatenation** (prevents injection)
- Target agent IDs come from `openclaw.json` `agents.list[].id`
- L1 issues strategic directives; L2 receives and breaks them into tasks

See [references/routing-patterns.md](references/routing-patterns.md) for directive templates and agent-id resolution.

## L2 → L3 Task Delegation

L2 calls `skills/spawn/spawn.py` to launch L3 containers:

```python
await spawn_l3_specialist(
    task_id=task_id,
    task_description=task_description,
    project_id=project_id,
    agent_type="L3_CODE",   # L3_CODE | L3_TEST | L3_REVIEW
    workspace_path=workspace_path
)
```

**Pool limits:** max 3 concurrent L3 containers per project (per-project semaphore via `PoolRegistry`).

See [references/l3-lifecycle.md](references/l3-lifecycle.md) for the full spawn/run/review/merge flow.

## Parallel Agent Coordination

Run multiple independent tasks concurrently:
```bash
# Fan-out: dispatch N tasks in parallel
openclaw agent --agent pm_agent --message "Task A: implement feature X"
openclaw agent --agent pm_agent --message "Task B: write tests for Y"
openclaw agent --agent pm_agent --message "Task C: document Z"
```

**Coordination patterns:**
- Fan-out then fan-in: dispatch parallel L3s, wait for all, aggregate results
- Sequential with handoff: task N output becomes task N+1 context
- Conditional: L2 reviews L3 output before deciding next step

See [references/coordination-patterns.md](references/coordination-patterns.md).

## State Flow

Tasks transition: `pending` → `in_progress` → `completed|failed|rejected`

Terminal states trigger memory extraction. The Jarvis Protocol (`state_engine.py`) uses `fcntl.flock()` for cross-container state safety.

## Debugging Orchestration

1. Check `agents/main/sessions/` for the current session JSONL
2. Verify `projects/<project_id>/project.json` has correct `workspace` and `agent_mappings`
3. Confirm pool availability: max 3 concurrent L3 per project
4. Check `data/<project_id>/workspace-state.json` for stale lock files

See [references/debug-checklist.md](references/debug-checklist.md) for systematic diagnosis steps.
