---
name: swarm_query
description: Read-only cross-project state aggregation for L1 visibility. Enables ClawdiaPrime to query project status, detect bottlenecks, and monitor swarm health without modifying state.
metadata:
  openclaw:
    emoji: "👁️"
    category: "orchestration"
    agent_scope: ["clawdia_prime"]
---

# SKILL: Swarm Query

## Purpose
Provide ClawdiaPrime (L1) with read-only visibility into the entire swarm's operational state across all managed projects.

## Capabilities

### Queries

1. **get_swarm_overview()** - Aggregate status across all projects
   - Total active/queued/completed/failed tasks
   - Project health scores
   - Bottleneck detection

2. **get_project_status(project_id)** - Detailed single project view
   - Active task count and list
   - Recent activity timeline
   - L3 container status

3. **find_stalled_tasks(threshold_minutes)** - Detect stuck work
   - Tasks with no activity for N minutes
   - Potential recovery candidates

4. **get_health_score(project_id)** - Compute project health (0.0-1.0)
   - 1.0 = healthy, 0.0 = critical
   - Based on load, backlog, failures, staleness

## Safety

- **Read-only**: Uses `LOCK_SH` (shared lock) — never blocks L2/L3 writes
- **Cache**: 5-second TTL prevents state file thrashing
- **Graceful degradation**: Returns partial results if projects are unreachable

## Usage

### Python API
```python
from agents.clawdia_prime.skills.swarm_query import SwarmQuery

query = SwarmQuery()
overview = query.get_swarm_overview()
print(f"Total active: {overview.total_active}")
print(f"Bottlenecks: {overview.bottleneck_projects}")
```

### CLI
```bash
python -m agents.clawdia_prime.skills.swarm_query overview
python -m agents.clawdia_prime.skills.swarm_query status --project main
python -m agents.clawdia_prime.skills.swarm_query stalled --threshold 30
```

### Natural Language
When ClawdiaPrime receives queries like:
- "What's the status of all projects?"
- "Which projects need attention?"
- "Show me stalled tasks"

...the skill aggregates and formats the response.

## Dependencies

- `openclaw.state_engine:JarvisState` - for state file reading
- `openclaw.config:get_state_path` - for project state path resolution
- `openclaw.project_config:get_project_config` - for project registry
