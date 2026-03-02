---
name: coordinate_parallel
description: Coordinates execution across multiple domain PMs for cross-domain directives. Manages parallel dispatch, monitors progress, validates integration, and aggregates results.
metadata:
  openclaw:
    emoji: "🔄"
    category: "orchestration"
    agent_scope: ["main"]
---

# SKILL: Parallel PM Coordinator

## Purpose
Enable the Meta-PM Coordinator to handle directives that span multiple domains by:
1. Decomposing work into domain-specific subtasks
2. Dispatching to multiple PMs in parallel
3. Monitoring progress and detecting blockers
4. Validating integration compatibility
5. Aggregating results into unified output

## When to Use

Use this skill when `route_directive` returns `RouteType.COORDINATE`:
- Directives mentioning both frontend and backend
- Full-stack features requiring multiple domains
- Cross-project dependencies

## Usage

### Python API
```python
from agents.main.skills.coordinate_parallel import ParallelCoordinator

coordinator = ParallelCoordinator(config, swarm_query)

# Execute multi-PM coordination
result = await coordinator.execute(
    directive="Build auth system with Next.js frontend and FastAPI backend",
    pm_list=["pumplai_pm", "backend_pm"],
    integration_contract={
        "outputs": {
            "pumplai_pm": "Login UI components, auth hooks",
            "backend_pm": "JWT endpoints, user model"
        },
        "interface": "API contract: POST /api/auth/login returns {token, user}"
    }
)
```

## Coordination Flow

```
1. DECOMPOSE
   Split directive into PM-specific subtasks

2. DEFINE CONTRACT
   Specify integration requirements between PM outputs

3. DISPATCH PARALLEL
   Send subtasks to all PMs simultaneously

4. MONITOR
   Poll swarm state for each PM's progress
   Detect blockers and stalls

5. VALIDATE
   Check outputs against integration contract

6. AGGREGATE
   Merge valid outputs into unified result
   Report conflicts if found

7. REPORT
   Return aggregated result or escalation request
```

## Dependencies

- `swarm_query` — Monitor PM progress
- `route_directive` — Decompose directives
- `spawn` — Fallback for coordination tasks
