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

**L1 → L2 delegation**: `skills/router_skill/index.js` dispatches directives via `openclaw agent --agent {targetId} --message "{directive}"` CLI commands. Uses `execFileSync` with argument arrays (no shell interpretation) to prevent injection.

**L2 → L3 delegation**: `skills/spawn_specialist/spawn.py` spawns Docker containers with security isolation (`no-new-privileges`, `cap_drop ALL`, 4GB mem limit, 1 CPU). Max 3 concurrent L3 containers per project managed by `skills/spawn_specialist/pool.py` via asyncio semaphore (`PoolRegistry` gives per-project independent semaphores).

**State synchronization**: The **Jarvis Protocol** (`orchestration/state_engine.py`) uses `fcntl.flock()` for cross-container state management via `workspace/.openclaw/<project_id>/workspace-state.json`. Exclusive locks (LOCK_EX) for writes, shared locks (LOCK_SH) for reads. mtime-based cache avoids unnecessary disk I/O. Backup recovery from `.bak` on corruption.

**Git workflow**: L3 work is isolated on `l3/task-{task_id}` staging branches. L2 reviews diffs (`orchestration/snapshot.py`), then merges with `--no-ff` or rejects. Semantic snapshots saved to `workspace/.openclaw/<project_id>/snapshots/`.

**Agent memory** (v1.3, in progress): `orchestration/memory_client.py` wraps a memU REST API (`workspace/memory/`) with per-project, per-agent scoping. `spawn.py` retrieves memories pre-spawn and injects them into L3 SOUL context (2000 char budget cap, graceful degradation on failure).

## Key Directories

- `agents/` — Agent identities (IDENTITY.md, SOUL.md, config.json) per tier; `_templates/soul-default.md` for SOUL variable substitution
- `orchestration/` — Jarvis Protocol state engine, snapshot system, CLI monitor, project CLI, memory client, SOUL renderer, config
- `skills/` — `router_skill` (L1→L2, Node.js), `spawn_specialist` (L2→L3, Python), `review_skill` (L2 diff review), `gog/` (skill from ClawhHub)
- `docker/l3-specialist/` — Dockerfile and `entrypoint.sh` for ephemeral L3 containers
- `workspace/` — Runtime data: `.openclaw/` per-project state/snapshots, `occc/` Next.js dashboard, `memory/` memU service
- `projects/<id>/` — Per-project manifest (`project.json`), optional `soul-override.md`
- `.planning/` — Roadmap, phase plans, milestone archives, verification docs

## Commands

### Tests
```bash
python3 -m pytest tests/ -v                     # Run all tests
python3 -m pytest tests/test_spawn_memory.py -v  # Run specific test file
```

### Multi-Project Management
```bash
python3 orchestration/project_cli.py init --id myproject --name "My Project"
python3 orchestration/project_cli.py list
python3 orchestration/project_cli.py switch <project_id>
python3 orchestration/project_cli.py remove <project_id>
```

### L3 Monitor (CLI)
```bash
python3 orchestration/monitor.py tail                    # Stream all projects
python3 orchestration/monitor.py tail --project pumplai  # Single project
python3 orchestration/monitor.py status                  # One-shot status table
python3 orchestration/monitor.py task <id>               # Full activity log for a task
python3 orchestration/monitor.py pool                    # Pool utilization stats
```

### L3 Container Spawning
```bash
docker build -t openclaw-l3-specialist:latest docker/l3-specialist/

# Direct spawn (testing)
python3 skills/spawn_specialist/spawn.py <task_id> <code|test> "<description>" \
  --workspace /path/to/workspace --project myproject

# Pool-managed spawn (production — enforces concurrency limits + retry)
python3 skills/spawn_specialist/pool.py <task_id> <code|test> "<description>" \
  --workspace /path/to/workspace --project myproject
```

### SOUL Templating
```bash
python3 orchestration/soul_renderer.py --project myproject --write
```

### Dashboard (occc)
```bash
cd workspace/occc && bun install && bun run dev   # http://localhost:6987
```

## Configuration

- `openclaw.json` — Root config: agent list, gateway (port 18789), `source_directories`, `active_project`, Telegram integration, memU API URL. **Contains secrets** (bot token, gateway auth token).
- `projects/<id>/project.json` — Per-project: workspace path, tech stack, agent mappings, `l3_overrides` (mem_limit, cpu_quota, pool_mode, overflow_policy, max_concurrent, queue_timeout_s)
- `agents/l3_specialist/config.json` — L3 defaults: supported runtimes (claude-code, codex, gemini-cli), skill timeouts (code: 600s, test: 300s)
- `orchestration/config.py` — Runtime tuning constants (lock timeout, poll interval, cache TTL, activity log max). Overridable via `OPENCLAW_LOG_LEVEL` and `OPENCLAW_ACTIVITY_LOG_MAX` env vars.

## Development Notes

- Orchestration is Python 3 with dependencies: `docker>=7.1.0`, `httpx` (memory client + spawn memory retrieval)
- The router_skill is Node.js
- L3 containers run as non-root (UID 1000) with volumes: workspace → `/workspace`, orchestration → `/orchestration` (read-only)
- Per-project state is namespaced: containers (`openclaw-{project}-l3-{task}`), state files, snapshots, pool semaphores
- SOUL templates use `string.Template.safe_substitute()` with `$variable` placeholders; per-project overrides in `soul-override.md`
- Pool supports modes (`shared`/`isolated`), overflow policies (`wait`/`reject`/`priority`), configurable per-project in `l3_overrides`

## Current Status

v1.0 (Foundation), v1.1 (Project Agnostic), and v1.2 (Orchestration Hardening) are shipped. v1.3 (Agent Memory) is in progress — phases 26-32. See `.planning/ROADMAP.md` for details.
