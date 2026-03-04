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

## Memory Architecture

Two memory systems coexist; both use the memU framework:

| System | Purpose | Storage | Port/Path |
|--------|---------|---------|-----------|
| **memory-memu extension** | OpenClaw agent auto-capture/recall (before_agent_start, agent_end) | SQLite at `OPENCLAW_ROOT/memory/memu.sqlite` | In-process (memu_wrapper.py) |
| **memU REST API** | L3 SOUL injection, orchestration memorization | Postgres (Docker) | `http://localhost:18791` |

**Flow (L3 SOUL injection):** Agent action → `spawn.py` pre-fetches via `memory_client.retrieve()` → memU REST `/retrieve` → Postgres + embeddings → formatted context injected into L3 SOUL (2000 char cap).

**Flow (memory-memu extension):** Agent conversation → `before_agent_start` calls memu_wrapper search → SQLite retrieval → `prependContext` injected. On `agent_end`: messages → memu_wrapper store → LLM judgment → SQLite + embeddings.

**Config:**
- `openclaw.json` → `plugins.entries.memory-memu.config` (geminiApiKey, anthropicToken, memuDbPath, etc.)
- `openclaw.json` → `memory.memu_api_url` (REST API URL for spawn/orchestration; default `http://localhost:18791`)

**Health check:** `make memory-health` probes the memU REST API. Override via `MEMU_API_URL` env.

### Detailed Memory Architecture (Phase 3 Consolidation)

#### Storage & Configuration

**SQLite Database (Per-Agent Memory)**
- **Path**: `$OPENCLAW_ROOT/memory/memu.sqlite` (default: `~/.openclaw/memory/memu.sqlite`)
- **Configurable via**: 
  - Environment: `MEMU_DB_PATH` (takes precedence)
  - openclaw.json: `plugins.entries.memory-memu.config.memuDbPath` (optional; if unset, uses default)
  - Python wrapper: `extensions/memory-memu/memu_wrapper.py` derives the path dynamically
- **Portability**: No hardcoded absolute paths; all paths derive from `$OPENCLAW_ROOT` or environment variables

**REST API Configuration**
- **Base URL**: `http://localhost:18791` (default; override via `MEMU_API_URL` env)
- **Configured in**: `openclaw.json` → `memory.memu_api_url`
- **Used by**: `spawn.py` for L3 pre-spawn memory retrieval, `orchestration/state_engine.py` for agent calls

**Plugin Configuration**
- **Location**: `extensions/memory-memu/openclaw.plugin.json` (schema + defaults)
- **Runtime config**: `openclaw.json` → `plugins.entries.memory-memu.config`
- **Keys**:
  - `anthropicToken`, `geminiApiKey`: LLM & embedding credentials
  - `memuDbPath`: (optional) SQLite DB override
  - `llmProvider`, `embedProvider`: "anthropic", "openai", "gemini" (with per-provider defaults)
  - `autoCapture`, `autoRecall`: Enable/disable auto-memory flows
  - `captureDetail`: "low" | "medium" | "high" — controls what info is stored
  - `recallTopK`: How many memories to inject during recall (default 3)

#### Data Flow: Agent Memory Injection

**High-level**: Agent action → Retrieve memories → Filter & format → Inject into SOUL context

1. **Pre-spawn** (`spawn.py`):
   - L2 spawns an L3 task
   - Calls `memory_client.retrieve(agent_id, query, top_k=5)`
   - Memory client hits REST API `/retrieve` (memU service on :18791)
   - memU queries Postgres + embeddings, returns ranked memories
   - Memories are formatted as markdown and injected into L3's `SOUL.md` context
   - Budget cap: 2000 chars max per memory section (graceful truncation on overflow)

2. **During agent conversation** (`memory-memu extension`):
   - Agent sends message
   - `before_agent_start` hook calls memu_wrapper to search SQLite
   - Relevant memories are retrieved and prepended to the conversation context
   - Agent processes message with memory context available
   - On `agent_end`: memu_wrapper stores conversation → LLM judges importance → SQLite + embeddings updated

#### Environment Variables & Overrides

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `OPENCLAW_ROOT` | Base dir for all openclaw data | `~/.openclaw` | `/data/openclaw` |
| `MEMU_DB_PATH` | SQLite DB file path | `$OPENCLAW_ROOT/memory/memu.sqlite` | `/tmp/test.db` |
| `MEMU_API_URL` | REST API endpoint | `http://localhost:18791` | `http://memservice:18791` |
| `MEMU_PATH` | Local memU source path (for development) | (none) | `./packages/memory` |
| `ANTHROPIC_TOKEN` | Anthropic API credentials | (from config) | `sk-ant-...` |
| `GEMINI_API_KEY` | Gemini API credentials | (from config) | `AIza...` |
| `LLM_PROVIDER` | LLM backend | `anthropic` | `openai` \| `gemini` |
| `EMBED_PROVIDER` | Embedding backend | (per-provider) | `openai` \| `gemini` |

#### Validation & Health Checks

1. **SQLite connectivity**: `make memory-health` (curls the REST API; can be overridden with `MEMU_API_URL`)
2. **Portability audit** (during development):
   - Confirm no hardcoded `/home/`, `/root/`, or `/tmp/` paths in config
   - Check `memu_wrapper.py` uses `os.path.join()` and respects env vars
   - Verify all paths in `openclaw.plugin.json` descriptions reference env vars or relative paths
3. **L3 injection verification**: Spawn a test L3, inspect `/run/openclaw/soul.md`, confirm Memory section is present with expected content

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
make memory-up                  # Start memU service (Docker, port 18791)
make memory-health               # Check memU service health
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
- Dashboard uses `OPENCLAW_ROOT` env var (defaults to `~/.openclaw`)
- L3 containers run as non-root (UID 1000) with volumes: workspace → `/workspace`, openclaw → `/openclaw` (read-only)
- Per-project state is namespaced: containers (`openclaw-{project}-l3-{task}`), state files, snapshots, pool semaphores
- SOUL templates use `string.Template.safe_substitute()` with `$variable` placeholders

## Current Status

v1.0-v1.3 shipped. v1.4 (Operational Maturity) in progress — phases 39-42. See `.planning/ROADMAP.md` for details.
