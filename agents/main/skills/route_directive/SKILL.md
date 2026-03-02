---
name: route_directive
description: Analyzes incoming directives and intelligently routes them to appropriate domain PMs, generic L3 execution, or escalation. Uses content analysis and swarm state for optimal routing decisions.
metadata:
  openclaw:
    emoji: "🎯"
    category: "orchestration"
    agent_scope: ["main"]
---

# SKILL: Intelligent Directive Router

## Purpose
Analyze incoming directives from L1 and determine the optimal execution path:
- Route to domain-specific PM (pumplai_pm, etc.)
- Spawn generic L3 specialist (research, analysis, docs)
- Coordinate multi-PM execution for cross-domain work
- Escalate to L1 when unclear or contradictory

## Routing Logic

### Priority Order

1. **Explicit Project Mention**
   - Detect: "Update the pumplai login page"
   - Route: Direct to pumplai_pm

2. **Tech Stack Detection**
   - Detect: "Create a Next.js component", "FastAPI endpoint"
   - Route: Match stack to PM registry

3. **Generic Task Keywords**
   - Detect: "Research...", "Analyze...", "Document...", "Compare..."
   - Route: Spawn L3 directly

4. **Multi-Domain Indicators**
   - Detect: "Frontend and backend", "API and UI", "full-stack feature"
   - Route: Parallel coordination

5. **Ambiguous / No Match**
   - Route: Escalate to L1 with options

## Usage

### Python API
```python
from agents.main.skills.route_directive import DirectiveRouter, RouteDecision

router = DirectiveRouter(config, swarm_query)
decision = router.route("Implement a Next.js login page with FastAPI backend")

if decision.route_type == RouteType.TO_PM:
    print(f"Route to: {decision.target}")
elif decision.route_type == RouteType.SPAWN_L3:
    print(f"Spawn L3 with skill: {decision.target}")
```

### CLI
```bash
python -m agents.main.skills.route_directive "Implement user authentication"
# Output: {"route_type": "TO_PM", "target": "pumplai_pm", "confidence": 0.95}
```

## Dependencies

- `swarm_query` — For PM availability checking
- `project_registry` — From main agent config
