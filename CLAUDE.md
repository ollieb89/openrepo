# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

OpenClaw is an AI Swarm Orchestration system implementing the **Grand Architect Protocol** — a 3-tier hierarchical architecture where AI agents delegate, execute, and synchronize work through Docker containers and git-based workflows.

## Architecture: 3-Tier Hierarchy

```
L1: ClawdiaPrime (Strategic Orchestrator)
 └─ L2: Project Manager (Tactical — per-project)
     └─ L3: Ephemeral Specialists (Isolated Docker Containers)
```

**L1 → L2 delegation**: `skills/router/index.js` dispatches directives via `openclaw agent --agent {targetId} --message "{directive}"` CLI commands. Uses `execFileSync` with argument arrays (no shell interpretation) to prevent injection.

**L2 → L3 delegation**: `skills/spawn/spawn.py` spawns Docker containers with security isolation (`no-new-privileges`, `cap_drop ALL`, 4GB mem limit, 1 CPU). Max 3 concurrent L3 containers per project managed by `skills/spawn/pool.py` via asyncio semaphore (`PoolRegistry` gives per-project independent semaphores).

**State synchronization**: The **Jarvis Protocol** (`packages/orchestration/src/openclaw/state_engine.py`) uses `fcntl.flock()` for cross-container state management via `<workspace>/.openclaw/<project_id>/workspace-state.json`. Exclusive locks (LOCK_EX) for writes, shared locks (LOCK_SH) for reads. mtime-based cache avoids unnecessary disk I/O. Backup recovery from `.bak` on corruption.

**Git workflow**: L3 work is isolated on `l3/task-{task_id}` staging branches. L2 reviews diffs (`openclaw.snapshot`), then merges with `--no-ff` or rejects.

**Agent memory** (v1.3): `openclaw.memory_client` wraps a memU REST API (`packages/memory/`) with per-project, per-agent scoping. `spawn.py` retrieves memories pre-spawn and injects them into L3 SOUL context (2000 char budget cap, graceful degradation on failure).

## Repository Structure

```
.openclaw/
├── pyproject.toml              # uv workspace root
├── Makefile                    # Unified dev commands
├── CLAUDE.md
├── config/
│   ├── openclaw.json           # App config (no secrets)
│   └── .env.example            # Secret placeholders
├── packages/
│   ├── orchestration/          # Python: core engine (openclaw package)
│   │   ├── pyproject.toml
│   │   ├── src/openclaw/       # State engine, snapshot, SOUL, config, memory
│   │   │   └── cli/            # monitor, project, suggest entry points
│   │   └── tests/
│   ├── dashboard/              # TypeScript: Next.js OCCC dashboard
│   │   ├── package.json
│   │   └── src/
│   └── memory/                 # Rust/Python: memU service
├── skills/                     # Skill implementations
│   ├── router/                 # Node.js — L1→L2 directive routing
│   ├── spawn/                  # Python — L2→L3 container spawning
│   ├── review/                 # Python — L2 diff review
│   └── .../                    # Hub-installed skills
├── agents/                     # Agent identities and configs
├── projects/                   # Per-project manifests
├── docker/                     # Dockerfiles
│   ├── l3-specialist/
│   └── memory/
├── data/                       # .gitignored runtime data
└── .planning/                  # Roadmap, phase plans
```

## Commands

### Development
```bash
make help                        # Show all available commands
make dev                         # Install orchestration in dev mode
make test                        # Run Python tests
make dashboard                   # Start dashboard dev server (port 6987)
make docker-l3                   # Build L3 container image
```

### Tests
```bash
uv run pytest packages/orchestration/tests/ -v        # All tests
uv run pytest packages/orchestration/tests/test_X.py   # Specific test
```

### Multi-Project Management
```bash
openclaw-project init --id myproject --name "My Project"
openclaw-project list
openclaw-project switch <project_id>
```

### L3 Monitor
```bash
openclaw-monitor tail                    # Stream all projects
openclaw-monitor tail --project pumplai  # Single project
openclaw-monitor status                  # One-shot status table
```

### Dashboard
```bash
make dashboard   # http://localhost:6987
```

## Configuration

- `config/openclaw.json` — App config: agent list, gateway (port 18789), `source_directories`, `active_project`. Secrets use `${ENV_VAR}` placeholders.
- `projects/<id>/project.json` — Per-project: workspace path, tech stack, agent mappings, `l3_overrides`
- `agents/l3_specialist/config.json` — L3 defaults: supported runtimes, skill timeouts
- `packages/orchestration/src/openclaw/config.py` — Runtime tuning constants. Overridable via `OPENCLAW_LOG_LEVEL` and `OPENCLAW_ACTIVITY_LOG_MAX` env vars.

## Development Notes

- Python package `openclaw` installed from `packages/orchestration/` — use `from openclaw.X import Y`
- Dashboard uses `OPENCLAW_ROOT` env var (defaults to `/home/ollie/.openclaw`)
- L3 containers run as non-root (UID 1000) with volumes: workspace → `/workspace`, openclaw → `/openclaw` (read-only)
- Per-project state is namespaced: containers (`openclaw-{project}-l3-{task}`), state files, snapshots, pool semaphores
- SOUL templates use `string.Template.safe_substitute()` with `$variable` placeholders

## Current Status

v1.0-v1.3 shipped. v1.4 (Operational Maturity) in progress — phases 39-42. See `.planning/ROADMAP.md` for details.
