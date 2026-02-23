# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

OpenClaw is an AI Swarm Orchestration system implementing the **Grand Architect Protocol** — a 3-tier hierarchical architecture where AI agents delegate, execute, and synchronize work through Docker containers and git-based workflows.

## Architecture: 3-Tier Hierarchy

```
L1: ClawdiaPrime (Strategic Orchestrator)
 └─ L2: PumplAI_PM (Tactical Project Manager)
     └─ L3: Ephemeral Specialists (Isolated Docker Containers)
```

**L1 → L2 delegation**: `skills/router_skill/index.js` dispatches directives via `openclaw agent --agent {targetId} --message "{directive}"` CLI commands.

**L2 → L3 delegation**: `skills/spawn_specialist/spawn.py` spawns Docker containers with security isolation (`no-new-privileges`, `cap_drop ALL`, 4GB mem limit, 1 CPU). Max 3 concurrent L3 containers managed by `skills/spawn_specialist/pool.py` via asyncio semaphore.

**State synchronization**: The **Jarvis Protocol** (`orchestration/state_engine.py`) uses `fcntl.flock()` for cross-container state management via `workspace/.openclaw/workspace-state.json`. Exclusive locks (LOCK_EX) for writes, shared locks (LOCK_SH) for reads.

**Git workflow**: L3 work is isolated on `l3/task-{task_id}` staging branches. L2 reviews diffs (`orchestration/snapshot.py`), then merges with `--no-ff` or rejects. Semantic snapshots (git diffs with metadata) are saved to `workspace/.openclaw/snapshots/`.

## Key Directories

- `agents/` — Agent identities (IDENTITY.md, SOUL.md, config.json) for each tier
- `orchestration/` — Jarvis Protocol state engine, snapshot system, CLI monitor, config
- `skills/` — Executable skills: `router_skill` (L1→L2, Node.js), `spawn_specialist` (L2→L3, Python)
- `docker/l3-specialist/` — Dockerfile and entrypoint for ephemeral L3 containers
- `workspace/` — Actual project workspace (includes `occc/` Next.js dashboard)
- `sandbox/` — Container registry (`containers.json`)
- `identity/` — Device authentication tokens
- `.planning/` — Roadmap, phase plans, and verification docs

## Commands

### L3 Monitor (CLI)
```bash
python3 orchestration/monitor.py tail          # Stream L3 activity in real-time
python3 orchestration/monitor.py status        # One-shot status of all tasks
python3 orchestration/monitor.py task <id>     # Full activity log for a task
```

### L3 Container Spawning
```bash
# Build L3 image (required before spawning)
docker build -t openclaw-l3-specialist:latest docker/l3-specialist/

# Spawn a specialist (test CLI)
python3 skills/spawn_specialist/spawn.py <task_id> <code|test> "<description>" --workspace /home/ollie/.openclaw/workspace
```

### Dashboard (occc)
```bash
cd workspace/occc
bun install
bun run dev        # Dev server on http://localhost:6987
```

### Docker Dashboard
```bash
docker build -t openclaw-dashboard workspace/occc/
# Exposed on port 18795 → container 6987
```

## Configuration

- `openclaw.json` — Root config: agent definitions, gateway (port 18789), sandbox modes, Telegram integration
- `agents/l3_specialist/config.json` — L3 container config: supported runtimes (claude-code, codex, gemini-cli), skill registry with timeouts (code: 600s, test: 300s), max 3 concurrent, retry once on failure
- `orchestration/config.py` — State file path, lock timeout (5s), poll interval (1s), snapshot directory

## Development Notes

- The orchestration layer is Python 3 with no external dependencies beyond `docker>=7.1.0` (for spawn_specialist)
- The router_skill is Node.js (uses `child_process.execSync` to call `openclaw` CLI)
- The L3 entrypoint (`docker/l3-specialist/entrypoint.sh`) handles git branch creation, CLI runtime execution, and state updates
- State file at `workspace/.openclaw/workspace-state.json` is the single source of truth for task status across containers
- L3 containers run as non-root user (UID 1000) with volumes: workspace → `/workspace`, orchestration → `/orchestration` (read-only)

## Current Status

Phases 1-3 complete (environment, orchestration, specialist execution). Phase 4 (monitoring dashboard) is planned. See `.planning/ROADMAP.md` for full progress.
