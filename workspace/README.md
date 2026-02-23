# OpenClaw

AI Swarm Orchestration implementing the **Grand Architect Protocol** — a 3-tier hierarchical architecture where AI agents delegate, execute, and synchronize work through Docker containers and git-based workflows.

## Architecture

```
L1: ClawdiaPrime          Strategic Orchestrator
 └─ L2: Project Manager   Tactical Delegation & Review
     └─ L3: Specialists   Ephemeral Docker Containers
```

**L1 (Strategic)** receives high-level objectives and breaks them into tactical directives, routed to L2 via the `router_skill`.

**L2 (Tactical)** decomposes directives into atomic tasks, spawns L3 containers, reviews their output (git diffs), and merges or rejects work.

**L3 (Execution)** runs inside isolated Docker containers with security constraints (`no-new-privileges`, `cap_drop ALL`, 4GB mem, 1 CPU). Each container operates on a `l3/task-{id}` staging branch. Supports multiple AI runtimes: Claude Code, Codex, and Gemini CLI.

### State Synchronization (Jarvis Protocol)

Cross-container state is managed through `workspace/.openclaw/<project>/workspace-state.json` using `fcntl.flock()` — exclusive locks for writes, shared locks for reads. This is the single source of truth for task status.

### Git Workflow

L3 work is isolated on staging branches. L2 reviews diffs via semantic snapshots (git diffs + metadata), then merges with `--no-ff` or rejects. Snapshots are saved to `workspace/.openclaw/snapshots/`.

## Project Structure

```
agents/                  Agent identities (IDENTITY.md, SOUL.md, config.json)
  clawdia_prime/         L1 strategic orchestrator
  pumplai_pm/            L2 project manager
  l3_specialist/         L3 container agent template
orchestration/           Jarvis Protocol core
  state_engine.py        Cross-container state management with file locking
  snapshot.py            Semantic diff capture and review
  monitor.py             CLI for real-time L3 activity monitoring
  soul_renderer.py       SOUL template rendering per project
  project_cli.py         Multi-project management CLI
  project_config.py      Project configuration resolution
skills/                  Executable capabilities
  router_skill/          L1 → L2 directive dispatch (Node.js)
  spawn_specialist/      L2 → L3 container spawning (Python)
    spawn.py             Docker container lifecycle
    pool.py              Concurrency management (asyncio semaphore)
  review_skill/          L2 diff review
docker/l3-specialist/    L3 container image
  Dockerfile             Debian slim + git/python3/curl/jq, non-root user
  entrypoint.sh          Branch creation, runtime execution, state updates
workspace/               Project workspace (mounted into containers)
  occc/                  Monitoring dashboard (Next.js, port 6987)
projects/                Per-project configuration overrides
sandbox/                 Container registry
```

## Getting Started

### Prerequisites

- Docker
- Python 3
- Node.js (for router_skill)
- [Bun](https://bun.sh) (for the dashboard)

### Build the L3 Container Image

```bash
docker build -t openclaw-l3-specialist:latest docker/l3-specialist/
```

### Spawn a Specialist

```bash
python3 skills/spawn_specialist/spawn.py <task_id> <code|test> "<description>" \
  --workspace /path/to/workspace
```

### Multi-Project Management

```bash
python3 orchestration/project_cli.py init --id myproject --name "My Project"
python3 orchestration/project_cli.py list
python3 orchestration/project_cli.py switch myproject
python3 orchestration/project_cli.py remove myproject [--force]
```

### Monitor L3 Activity

```bash
python3 orchestration/monitor.py tail       # Stream activity in real-time
python3 orchestration/monitor.py status     # One-shot status of all tasks
python3 orchestration/monitor.py task <id>  # Full activity log for a task
```

### Run the Dashboard

```bash
cd workspace/occc
bun install
bun run dev    # http://localhost:6987
```

Or via Docker:

```bash
docker build -t openclaw-dashboard workspace/occc/
# Exposed on port 18795 → container 6987
```

## Configuration

| File | Purpose |
|------|---------|
| `openclaw.json` | Root config: agents, gateway (port 18789), channels, sandbox modes |
| `agents/l3_specialist/config.json` | L3 runtimes, skill registry (code: 600s, test: 300s), max 3 concurrent |
| `orchestration/config.py` | State file path, lock timeout (5s), poll interval (1s), snapshot directory |
| `projects/<id>/project.json` | Per-project overrides and SOUL template variables |

## L3 Container Security

Specialists run with strict isolation:

- Non-root user (UID 1000)
- `--security-opt no-new-privileges`
- `--cap-drop ALL`
- 4GB memory limit, 1 CPU
- Workspace mounted read-write, orchestration mounted read-only
- Max 3 concurrent containers (per-project semaphore)
- Retry once on failure, then report

## Milestones

- **v1.0** — Grand Architect Protocol Foundation (10 phases, shipped 2026-02-23)
- **v1.1** — Project Agnostic multi-project support (8 phases, shipped 2026-02-23)

## License

Proprietary. All rights reserved.
