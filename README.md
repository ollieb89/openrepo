# OpenClaw

AI Swarm Orchestration implementing the **Grand Architect Protocol** — a 3-tier hierarchical architecture where AI agents delegate, execute, and synchronize work through Docker containers and git-based workflows.

---

## Table of Contents

- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Multi-Project Management](#multi-project-management)
- [Spawning L3 Specialists](#spawning-l3-specialists)
- [Monitoring](#monitoring)
- [Dashboard](#dashboard)
- [Configuration Reference](#configuration-reference)
- [Security Model](#security-model)
- [Milestones](#milestones)
- [License](#license)

---

## Architecture

```
L1: ClawdiaPrime            Strategic Orchestrator
 └─ L2: Project Manager     Tactical Delegation & Review
     └─ L3: Specialists     Ephemeral Docker Containers
```

OpenClaw uses a **3-tier hierarchy** to decompose complex objectives into atomic, isolated work units:

| Tier | Role | Implementation |
|------|------|----------------|
| **L1 — Strategic** | Receives high-level objectives, breaks them into tactical directives | `agents/clawdia_prime/` — routes via `skills/router/index.js` |
| **L2 — Tactical** | Decomposes directives into atomic tasks, spawns L3 containers, reviews diffs, merges or rejects | `agents/pumplai_pm/` (per-project) — uses `skills/spawn/` |
| **L3 — Execution** | Runs inside isolated Docker containers on staging branches, executes code/test tasks | `docker/l3-specialist/` — ephemeral, security-constrained |

### Delegation Flow

```
L1 (ClawdiaPrime)
 │
 │  router skill dispatches directive via:
 │    openclaw agent --agent <l2_id> --message "<directive>"
 │
 ▼
L2 (Project Manager)
 │
 │  spawn skill creates Docker container:
 │    - Creates task in workspace-state.json
 │    - Runs container with security constraints
 │    - Monitors execution with timeout
 │    - Reviews git diff (semantic snapshot)
 │    - Merges (--no-ff) or rejects staging branch
 │
 ▼
L3 (Specialist Container)
     - Checks out staging branch: l3/task-{id}
     - Executes task via CLI runtime (Claude Code / Codex / Gemini CLI)
     - Commits changes on staging branch
     - Reports status back to workspace-state.json
```

---

## How It Works

### State Synchronization (Jarvis Protocol)

All cross-container state is managed through a single JSON file per project:

```
workspace/.openclaw/<project_id>/workspace-state.json
```

The **Jarvis Protocol** (`orchestration/state_engine.py`) uses `fcntl.flock()` for safe concurrent access:

- **Shared locks** (`LOCK_SH`) for reads — multiple containers can read simultaneously
- **Exclusive locks** (`LOCK_EX`) for writes — only one writer at a time
- **Lock timeout**: 5 seconds with 3 retry attempts and exponential backoff
- **mtime-based cache**: Reads are served from memory when the file hasn't changed, avoiding unnecessary disk I/O
- **Backup recovery**: If the state file is corrupt or empty, the engine auto-recovers from a `.bak` file
- **Activity log rotation**: Logs are trimmed at 100 entries per task to prevent unbounded growth

### Git Workflow

L3 work is isolated on **staging branches**:

1. L3 container creates branch `l3/task-{task_id}` from the project's default branch
2. L3 executes the task, stages changes, and commits on the staging branch
3. L2 captures a **semantic snapshot** — a git diff with metadata (files changed, insertions, deletions)
4. L2 reviews the diff and either:
   - **Merges** with `git merge --no-ff` into the default branch, then deletes the staging branch
   - **Rejects** by force-deleting the staging branch and marking the task as rejected

Snapshots are saved to `workspace/.openclaw/<project_id>/snapshots/{task_id}.diff`.

### Container Pool Management

L3 containers are managed by an **asyncio semaphore-based pool** (`skills/spawn/pool.py`):

- **Default concurrency**: 3 containers per project (configurable per-project)
- **Pool modes**:
  - `shared` (default) — all shared-mode projects share a global semaphore
  - `isolated` — each project gets its own dedicated semaphore
- **Overflow policies**:
  - `wait` (default) — queue and wait up to `queue_timeout_s` (300s)
  - `reject` — fail immediately if all slots are full
  - `priority` — priority queue where lower number = higher priority
- **Auto-retry**: Failed tasks are retried once automatically
- **Ephemeral lifecycle**: Containers are force-removed after completion

---

## Project Structure

```
openclaw.json                Root configuration (agents, gateway, channels, source_directories)
agents/                      Agent identities and configuration
  clawdia_prime/             L1 strategic orchestrator
  pumplai_pm/                L2 project manager (example)
  l3_specialist/             L3 container agent template
    config.json              Runtimes, skill registry, resource limits
  _templates/
    soul-default.md          SOUL template with variable substitution
orchestration/               Jarvis Protocol core
  state_engine.py            Cross-container state with file locking and caching
  snapshot.py                Semantic diff capture and git branch operations
  monitor.py                 CLI for real-time L3 activity monitoring
  soul_renderer.py           SOUL.md template rendering per project
  project_cli.py             Multi-project management CLI
  project_config.py          Project configuration resolution and validation
  config.py                  Tunable constants (lock timeout, poll interval, cache TTL)
  config_validator.py        Project and agent hierarchy validation
  logging.py                 Structured logging subsystem
skills/                      Executable capabilities
  router/                    L1 → L2 directive dispatch (Node.js)
    index.js                 Uses execFileSync for shell-injection-safe CLI calls
  spawn/                     L2 → L3 container spawning (Python)
    spawn.py                 Docker container lifecycle and security config
    pool.py                  Concurrency management (asyncio semaphore, PoolRegistry)
  review/                    L2 diff review
docker/l3-specialist/        L3 container image
  Dockerfile                 Debian slim + git/python3/curl/jq, non-root user
  entrypoint.sh              Branch creation, runtime execution, state updates
workspace/                   Project workspace and runtime data
  .openclaw/                 Per-project state and snapshots
    <project_id>/
      workspace-state.json   Single source of truth for task status
      snapshots/             Captured git diffs
  occc/                      Monitoring dashboard (Next.js, port 6987)
projects/                    Per-project configuration
  <project_id>/
    project.json             Project manifest (workspace, tech stack, agent mappings, L3 overrides)
    soul-override.md         Optional per-project SOUL section overrides
  _templates/                Project scaffolding templates
sandbox/                     Container registry (containers.json)
identity/                    Device authentication tokens
.planning/                   Roadmap, phase plans, and verification docs
```

---

## Prerequisites

- **Docker** — for L3 specialist containers
- **Python 3** — orchestration layer (no external deps except `docker>=7.1.0` for spawn)
- **Node.js** — for `router` skill (L1 → L2 dispatch)
- **[Bun](https://bun.sh)** — for the monitoring dashboard

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url> ~/.openclaw
cd ~/.openclaw
```

### 2. Build the L3 container image

```bash
docker build -t openclaw-l3-specialist:latest docker/l3-specialist/
```

### 3. Install Python dependencies (for spawn)

```bash
pip install docker>=7.1.0
```

### 4. Configure source directories

Edit `openclaw.json` to set where your project code lives:

```json
{
  "source_directories": [
    "/home/you/Development/Projects",
    "/home/you/Development/Tools"
  ]
}
```

These directories are used as default workspace roots when initializing new projects.

---

## Quick Start

### Initialize your first project

```bash
python3 orchestration/project_cli.py init --id myproject --name "My Project"
```

This will:
- Create `projects/myproject/project.json` with default configuration
- Generate a `SOUL.md` identity file for the L2 agent
- Set `myproject` as the active project
- Default workspace path to `<source_directories[0]>/myproject`

### Spawn a specialist to do work

```bash
python3 skills/spawn/spawn.py task-001 code "Implement the login page" \
  --workspace /path/to/myproject
```

### Monitor the work in real-time

```bash
python3 orchestration/monitor.py tail
```

### Check task status

```bash
python3 orchestration/monitor.py status
```

---

## Multi-Project Management

OpenClaw supports managing multiple projects simultaneously, each with isolated state, snapshots, and container pools.

### Initialize a project

```bash
python3 orchestration/project_cli.py init --id myproject --name "My Project"

# With a template preset:
python3 orchestration/project_cli.py init --id myproject --name "My Project" --template fullstack

# With a custom workspace path:
python3 orchestration/project_cli.py init --id myproject --name "My Project" \
  --workspace /custom/path/to/project
```

Available templates: `fullstack`, `backend`, `ml-pipeline`

### List all projects

```bash
python3 orchestration/project_cli.py list
```

Output:

```
ID              NAME            WORKSPACE                                ACTIVE
--------------------------------------------------------------------------------
pumplai         PumplAI         /home/ollie/Development/Projects/pumplai *
smartai         SmartAI         /home/ollie/Development/Projects/smartai
replyiq         ReplyIQ         /home/ollie/Development/Projects/replyiq
```

### Switch the active project

```bash
python3 orchestration/project_cli.py switch smartai
```

Switching is blocked if L3 containers are still running for the current active project.

### Remove a project

```bash
python3 orchestration/project_cli.py remove smartai          # Interactive confirmation
python3 orchestration/project_cli.py remove smartai --force   # Skip confirmation
```

Removes `projects/smartai/` but preserves the workspace directory.

### Project configuration

Each project has a `projects/<id>/project.json` manifest:

```json
{
  "id": "pumplai",
  "name": "PumplAI",
  "agent_display_name": "PumplAI_PM",
  "workspace": "/home/ollie/Development/Projects/pumplai",
  "tech_stack": {
    "frontend": "Next.js 16, React 19, Tailwind v4",
    "backend": "Python 3.12, FastAPI",
    "infra": "Docker-based isolation, PostgreSQL"
  },
  "agents": {
    "l2_pm": "pumplai_pm",
    "l3_executor": "l3_specialist"
  },
  "l3_overrides": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"],
    "max_concurrent": 3,
    "pool_mode": "shared",
    "overflow_policy": "wait",
    "queue_timeout_s": 300
  }
}
```

### SOUL templating

Each L2 agent receives a rendered `SOUL.md` identity file built from:

1. `agents/_templates/soul-default.md` — base template with `$variable` placeholders
2. `projects/<id>/soul-override.md` — optional per-project section overrides

Variables are substituted from the project config: `$project_name`, `$agent_name`, `$tech_stack_frontend`, etc. Re-render with:

```bash
python3 orchestration/soul_renderer.py --project myproject --write
```

---

## Spawning L3 Specialists

### Direct spawn (for testing)

```bash
python3 skills/spawn/spawn.py <task_id> <code|test> "<description>" \
  --workspace /path/to/workspace \
  --project myproject \
  --runtime claude-code \
  --gpu  # optional GPU passthrough
```

### Pool-managed spawn (production)

```bash
python3 skills/spawn/pool.py <task_id> <code|test> "<description>" \
  --workspace /path/to/workspace \
  --project myproject
```

The pool enforces concurrency limits, handles retry logic, and cleans up containers after completion.

### Supported CLI runtimes

| Runtime | Description |
|---------|-------------|
| `claude-code` | Claude Code CLI (default) |
| `codex` | OpenAI Codex CLI |
| `gemini-cli` | Google Gemini CLI |

The runtime is passed as `CLI_RUNTIME` environment variable to the container. The entrypoint invokes whichever runtime is available.

### Skill types

| Skill | Timeout | Description |
|-------|---------|-------------|
| `code` | 600s (10 min) | Write and edit source code |
| `test` | 300s (5 min) | Run test suites and report results |

---

## Monitoring

### CLI Monitor

The monitor provides real-time visibility into L3 activity across all projects.

#### Stream activity in real-time

```bash
python3 orchestration/monitor.py tail                    # All projects
python3 orchestration/monitor.py tail --project pumplai  # Single project
python3 orchestration/monitor.py tail --interval 2.0     # Custom poll interval
```

Output shows color-coded status transitions and activity entries:

```
OpenClaw L3 Monitor - Tailing Activity (all projects)
Polling interval: 1.0s
Press Ctrl+C to stop

[pumplai] [STATUS] task-001 pending → in_progress
[pumplai] [2026-02-24 14:30:01] [task-001] [in_progress] Created new staging branch: l3/task-task-001
[pumplai] [2026-02-24 14:30:05] [task-001] [in_progress] Executing task with claude-code...
[pumplai] [2026-02-24 14:35:12] [task-001] [completed] Task completed. Changed files: src/login.tsx,
```

#### One-shot status

```bash
python3 orchestration/monitor.py status                    # All projects
python3 orchestration/monitor.py status --project pumplai  # Single project
```

Shows a table with all tasks, their status, skill, timestamps, and last activity.

#### Task detail

```bash
python3 orchestration/monitor.py task task-001                    # Auto-discovers project
python3 orchestration/monitor.py task task-001 --project pumplai  # Explicit project
```

Shows the full activity log for a specific task.

#### Pool utilization

```bash
python3 orchestration/monitor.py pool                    # All projects
python3 orchestration/monitor.py pool --project pumplai  # Single project
```

Shows per-project pool stats: active slots, queued tasks, completed/failed counts, and saturation percentage (color-coded: green 0-33%, yellow 34-66%, red 67-100%).

### Legacy single-file mode

For backward compatibility, you can pass `--state-file` to target a specific state file:

```bash
python3 orchestration/monitor.py tail --state-file workspace/.openclaw/pumplai/workspace-state.json
```

---

## Dashboard

The **OCCC** (OpenClaw Control Center) is a Next.js monitoring dashboard running on port 6987.

### Pages

| Page | URL | Description |
|------|-----|-------------|
| Overview | `/` | System overview and status summary |
| Tasks | `/tasks` | Task list with status, activity, filtering |
| Containers | `/containers` | Live container status (polls every 5s) |
| Agents | `/agents` | Agent hierarchy and configuration |
| Metrics | `/metrics` | Pool utilization charts and performance data |

### Run locally

```bash
export OPENCLAW_ROOT=$HOME/.openclaw   # Required: dashboard inherits this for suggest.py path resolution
make dashboard                         # or: cd packages/dashboard && bun install && bun run dev
```

### Run via Docker

```bash
docker build -t openclaw-dashboard packages/dashboard/
# Exposed on host port 18795 → container port 6987
```

### Dashboard features

- **Project selector** — persists selection to `localStorage('occc-project')`, validates against server project list on mount
- **Dark mode** — toggle stored in `localStorage('occc-theme')`, synchronized to avoid flash
- **Real-time data** — SWR hooks with automatic polling (tasks: 3s, containers: 5s)
- **Per-project filtering** — all data views filter by selected project via `?project=` query params

---

## Configuration Reference

### openclaw.json (root config)

| Field | Description |
|-------|-------------|
| `active_project` | Currently active project ID |
| `source_directories` | Array of paths where user code lives (used for default workspace paths) |
| `agents.defaults.model.primary` | Default AI model for agents |
| `agents.defaults.maxConcurrent` | Max concurrent agent sessions |
| `agents.list[]` | Agent definitions (id, name, level, reports_to, project, sandbox) |
| `gateway.port` | Gateway port (default: 18789) |
| `channels.telegram` | Telegram bot integration config |

### projects/\<id\>/project.json (per-project)

| Field | Description |
|-------|-------------|
| `id` | Project identifier (alphanumeric + hyphens, 1-20 chars) |
| `name` | Human-readable project name |
| `agent_display_name` | Display name for the L2 agent |
| `workspace` | Absolute path to the project's codebase |
| `tech_stack` | `{frontend, backend, infra}` — injected into SOUL templates |
| `agents.l2_pm` | L2 project manager agent ID |
| `agents.l3_executor` | L3 specialist agent ID |
| `l3_overrides.mem_limit` | Container memory limit (default: `"4g"`) |
| `l3_overrides.cpu_quota` | Container CPU quota in microseconds (default: `100000` = 1 CPU) |
| `l3_overrides.runtimes` | Supported CLI runtimes |
| `l3_overrides.max_concurrent` | Max concurrent L3 containers for this project (default: 3) |
| `l3_overrides.pool_mode` | `"shared"` or `"isolated"` (default: `"shared"`) |
| `l3_overrides.overflow_policy` | `"wait"`, `"reject"`, or `"priority"` (default: `"wait"`) |
| `l3_overrides.queue_timeout_s` | Queue wait timeout in seconds (default: 300) |
| `default_branch` | Git default branch name (auto-detected if not set) |

### agents/l3_specialist/config.json

| Field | Description |
|-------|-------------|
| `container.image` | Docker image name (default: `openclaw-l3-specialist:latest`) |
| `container.lifecycle` | `"ephemeral"` — containers are removed after completion |
| `container.mem_limit` | Memory limit (overridable per-project) |
| `container.cpu_quota` | CPU quota in microseconds (overridable per-project) |
| `runtime.default` | Default CLI runtime (`claude-code`) |
| `runtime.supported` | List of supported runtimes |
| `skill_registry.code.timeout_seconds` | Code task timeout (600s) |
| `skill_registry.test.timeout_seconds` | Test task timeout (300s) |
| `max_concurrent` | Default max concurrent containers (3) |
| `retry_on_failure` | Auto-retry once on failure (`true`) |

### orchestration/config.py (runtime tuning)

| Constant | Default | Description |
|----------|---------|-------------|
| `LOCK_TIMEOUT` | 5s | Max wait for file lock acquisition |
| `LOCK_RETRY_ATTEMPTS` | 3 | Retries with exponential backoff on lock timeout |
| `POLL_INTERVAL` | 1.0s | Monitor polling interval |
| `CACHE_TTL_SECONDS` | 5.0s | Max cache age before forced re-read |
| `ACTIVITY_LOG_MAX_ENTRIES` | 100 | Trim threshold for per-task activity logs |

Environment variable overrides: `OPENCLAW_LOG_LEVEL` (default: INFO), `OPENCLAW_ACTIVITY_LOG_MAX`.

---

## Security Model

L3 specialist containers run with strict isolation:

| Constraint | Value |
|------------|-------|
| User | Non-root (matches host UID/GID) |
| Privileges | `--security-opt no-new-privileges` |
| Capabilities | `--cap-drop ALL` |
| Memory | 4GB limit (configurable per-project) |
| CPU | 1 CPU (100000 microsecond quota, configurable per-project) |
| Workspace mount | Read-write (project workspace only) |
| Orchestration mount | Read-only |
| Restart policy | None (L2 handles retries, not Docker) |
| Concurrency | Max 3 concurrent containers per project (configurable) |
| Retry | Once on failure, then report |
| Shell injection | Prevented — `router` skill uses `execFileSync` with argument arrays, no shell interpretation |

---

## Agent Autonomy Framework (v1.6)

The **Agent Autonomy Framework** enables L3 containers to self-direct their work with confidence-based decision making, automatically escalating to human oversight when confidence falls below threshold.

### Architecture

```
L3 Container
 │
 ├─ AutonomyClient ──→ Orchestrator HTTP API
 │                        │
 ├─ Sentinel Files ──→ /tmp/openclaw/autonomy/  (backup)
 │                        │
 └─ Confidence Loop    Autonomy Hooks
    (self-reporting)    │
                         ├─ State Machine (4 states)
                         ├─ Event Bus (decoupled)
                         └─ memU (persistence)
```

### States

| State | Description | Transition Trigger |
|-------|-------------|-------------------|
| **PLANNING** | Task initialized | `on_task_spawn()` |
| **EXECUTING** | Container healthy, work in progress | Container health check |
| **BLOCKED** | Hit obstacle, retry pending | Task failure |
| **COMPLETE** | Task finished successfully | Task completion |
| **ESCALATING** | Max retries exceeded, human needed | Retry exhaustion |

### Confidence Scoring

Tasks are scored 0.0-1.0 based on:
- **Complexity** (25%): Code keywords, length, multi-step indicators
- **Ambiguity** (30%): Uncertainty words vs clarity indicators
- **Past Success** (25%): Historical success rate (future: ML-based)
- **Time Estimate** (20%): Duration-based confidence

**Escalation Threshold**: 0.6 (configurable per-project)

### Usage

```python
from openclaw.autonomy import (
    on_task_spawn, on_container_healthy, on_task_complete,
    AutonomyState, AutonomyContext, AutonomyEventBus
)

# 1. Spawn creates PLANNING context
context = on_task_spawn("task-001", {"max_retries": 1})

# 2. Health check transitions to EXECUTING
on_container_healthy("task-001")

# 3. L3 container reports confidence
#    (inside container via AutonomyClient)
from openclaw.autonomy import AutonomyClient
client = AutonomyClient("task-001", "http://host.docker.internal:8080")
client.report_state_update("executing", confidence=0.85)

# 4. Task completion
on_task_complete("task-001", {"status": "success"})
```

### Configuration

```json
{
  "autonomy": {
    "enabled": true,
    "escalation_threshold": 0.6,
    "confidence_calculator": "threshold",
    "max_retries": 1,
    "blocked_timeout_minutes": 30
  }
}
```

### Events

| Event | Description |
|-------|-------------|
| `autonomy.state_changed` | State transition occurred |
| `autonomy.confidence_updated` | Confidence score changed (debounced) |
| `autonomy.escalation_triggered` | Human escalation requested |
| `autonomy.retry_attempted` | Retry from BLOCKED state |

---

## Milestones

| Version | Name | Phases | Shipped |
|---------|------|--------|---------|
| **v1.0** | Grand Architect Protocol Foundation | 10 phases, 25 plans | 2026-02-23 |
| **v1.1** | Project Agnostic (multi-project support) | 8 phases, 17 plans | 2026-02-23 |
| **v1.2** | Orchestration Hardening | 7 phases (logging, reliability, perf, observability, pool config, dashboard metrics) | 2026-02-24 |

See `.planning/ROADMAP.md` for full phase details.

---

## License

Proprietary. All rights reserved.
