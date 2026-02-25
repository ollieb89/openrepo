---
name: openclaw-spawn-l3
description: L2→L3 container spawning in OpenClaw. Use when spawning Docker specialist containers, managing the per-project container pool, configuring L3 security isolation, injecting SOUL and memory context into containers, reviewing L3 diffs, merging or rejecting L3 work, or debugging container lifecycle issues. Triggers for: "spawn L3", "container pool", "L3 specialist", "Docker isolation", "SOUL injection", "task container", "cap_drop", "l3/task branch", "pool semaphore".
---

# L2 → L3 Container Spawning

## Quick Spawn

```python
from skills.spawn.spawn import spawn_l3_specialist

result = await spawn_l3_specialist(
    task_id="task-abc123",
    task_description="Implement the user authentication module",
    project_id="pumplai",
    agent_type="L3_CODE",       # L3_CODE | L3_TEST | L3_REVIEW
    workspace_path="/home/ollie/Development/Projects/pumplai"
)
```

## Security Profile

Every L3 container runs with:
- `--no-new-privileges`
- `--cap-drop ALL`
- 4 GB memory limit
- 1 CPU limit
- Non-root (UID 1000)
- Volumes: workspace → `/workspace`, openclaw → `/openclaw` (read-only)

## Pool Management

`PoolRegistry` in `skills/spawn/pool.py` provides per-project independent semaphores. **Max 3 concurrent L3 per project.**

```python
from skills.spawn.pool import PoolRegistry

registry = PoolRegistry(max_concurrent=3)
async with registry.acquire(project_id):
    # spawn runs here
```

When at capacity, new spawn calls wait (asyncio semaphore). Do not bypass — pool prevents resource exhaustion.

## SOUL & Memory Injection

Before spawn, `spawn.py`:
1. Retrieves memories from memU (`_retrieve_memories_sync`)
2. Formats memory context (`_format_memory_context`, 2000 char cap)
3. Reads `soul-default.md` + per-project `soul-override.md`
4. Builds augmented SOUL (`_build_augmented_soul`)
5. Writes to `<workspace>/.openclaw/<project_id>/soul-<task_id>.md`

L3 container reads `SOUL_FILE` and passes it as system prompt.

## Git Workflow

L3 work lands on staging branch `l3/task-{task_id}`. L2 reviews diffs, then:
- **Merge**: `git merge --no-ff l3/task-{task_id}`
- **Reject**: delete branch, update state to `rejected`

Use `openclaw.snapshot` to capture diffs for L2 review before merge decision.

## Container Naming

Containers are namespaced: `openclaw-{project_id}-l3-{task_id}`. Labels and env vars carry project/task context for monitoring.

See [references/container-config.md](references/container-config.md) for full Docker config, volume mounts, and env var list.
See [references/soul-template.md](references/soul-template.md) for SOUL injection details and `$variable` placeholder reference.
