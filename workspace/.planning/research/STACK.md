# Stack Research

**Domain:** AI Swarm Orchestration — Multi-Project Framework (v1.1 additions)
**Researched:** 2026-02-23
**Confidence:** HIGH

> **Scope note:** This document covers ONLY stack additions/changes required for the v1.1
> "Project Agnostic" milestone. The v1.0 baseline (Python 3, Docker SDK, Next.js 16,
> SWR, Tailwind 4, Bun) is validated and unchanged. Do not re-architect what works.

---

## Recommended Stack

### New Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `argparse` (stdlib) | Python 3.14 builtin | Project CLI subcommands (`init/switch/list/remove`) | Already used in `spawn.py` CLI harness. Zero new dependency. Subcommand groups via `add_subparsers()`. Sufficient for 4 commands with no interactive TUI needed. |
| `string.Template` (stdlib) | Python 3.14 builtin | SOUL/IDENTITY templating engine | Built-in, no install, safe `$VAR` syntax appropriate for markdown templates. Supports `safe_substitute()` which leaves unknown placeholders intact — critical for SOUL.md files that contain `$` in shell examples. |
| `json` (stdlib) | Python 3.14 builtin | Per-project state file management | Already used throughout orchestration layer. State files are `workspace-state.json` — same format, just namespaced per project under `workspace/.openclaw/<project_id>/`. |
| `pathlib.Path` (stdlib) | Python 3.14 builtin | Project directory scaffolding | Already used in `project_config.py`. `Path.mkdir(parents=True, exist_ok=True)` handles `projects/<id>/` tree creation atomically. |

### Supporting Libraries (New Additions)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None required | — | — | All new Python capabilities are stdlib. See rationale below. |

**Frontend additions for dashboard project switcher:**

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Already present: `swr` | 2.4.0 | Poll new `/api/projects` endpoint | Use existing SWR pattern from swarm status — no new library needed |
| Already present: `zod` | 4.3.6 | Validate project switcher API responses | Extend existing Zod schemas in occc — no new library needed |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `python3 -m pytest` (existing) | Test CLI subcommands | Test via `subprocess` invoking the CLI script directly — no new test framework |
| `bun test` (existing) | Frontend project switcher tests | Use existing occc test setup |

---

## Installation

```bash
# No new Python dependencies — all stdlib
# Python 3.14.3 is already installed on host

# No new npm/bun packages required for occc
# All frontend additions use already-installed swr + zod
```

---

## Feature-by-Feature Rationale

### 1. Project CLI: `openclaw project init/switch/list/remove`

**Implementation:** New Python script `orchestration/project_cli.py` using `argparse.ArgumentParser` with `add_subparsers()`.

**Why `argparse` not Click/Typer:**
- The existing `spawn.py` CLI already uses `argparse` — consistency beats marginal DX improvement
- Click/Typer would add ~500KB dependency for 4 subcommands
- No interactive prompts needed (non-interactive `init` reads from flags or a template)
- `argparse` subparsers handle `project init --template fullstack --name myapp` cleanly

**Subcommand structure:**
```
orchestration/project_cli.py
  project init   --name <id> --template <fullstack|backend|ml-pipeline> --workspace <path>
  project switch --name <id>
  project list
  project remove --name <id> [--force]
```

**Integration point:** `init` writes `projects/<id>/project.json` and scaffolds `agents/<l2_id>/agent/` from templates. `switch` updates `openclaw.json#active_project`. `list` reads `projects/*/project.json`. `remove` deletes `projects/<id>/` directory after confirmation.

---

### 2. SOUL Templating Engine

**Implementation:** `string.Template` from Python stdlib.

**Why `string.Template` not Jinja2:**
- Jinja2 is not installed on this host (verified: `python3 -c "import jinja2"` fails)
- Adding Jinja2 for markdown file templating is over-engineering — SOUL/IDENTITY files are simple key substitution (`$project_name`, `$l2_agent_id`, `$workspace_path`, `$tech_stack`)
- `string.Template.safe_substitute()` is essential: SOUL.md files contain shell command examples with `$VARIABLE` syntax that must pass through unchanged when not in the substitution map
- Jinja2's `{{ }}` syntax would require escaping every shell variable in template files — a maintenance burden
- If templating needs grow beyond simple substitution (loops, conditionals), revisit Jinja2 at that point

**Template storage:** `projects/templates/<template_name>/` containing `project.json.tmpl`, `SOUL.md.tmpl`, `IDENTITY.md.tmpl`. Templates use `$project_name`, `$project_id`, `$workspace_path`, `$tech_stack_summary` as substitution points.

**Integration point:** `orchestration/project_cli.py init` calls a new `orchestration/soul_templater.py` module that loads templates, performs substitution, and writes output files.

---

### 3. Per-Project State File Management

**Implementation:** Extend `orchestration/config.py` and `orchestration/project_config.py` — no new libraries.

**Current state:** `workspace/.openclaw/workspace-state.json` is a single global file. `config.py` already supports `OPENCLAW_STATE_FILE` env var override.

**New pattern:** State files become `workspace/.openclaw/<project_id>/state.json`. Snapshot dir becomes `workspace/.openclaw/<project_id>/snapshots/`.

**Integration:** `orchestration/config.py` gets a `get_state_file(project_id)` function that constructs the per-project path. `JarvisState` in `state_engine.py` already accepts a `state_file` path argument — the change is in how that path is resolved, not in the state engine itself.

**Pool isolation:** `pool.py` `L3ContainerPool` needs a `project_id` parameter. When `isolation_mode == "isolated"` (opt-in per project via `project.json#l3_overrides.pool_isolation: "isolated"`), the pool semaphore is per-project (stored in a dict keyed by project_id). Default `shared` mode keeps the existing global semaphore — backward compatible.

---

### 4. Configurable L3 Pool Isolation

**Implementation:** Extend `pool.py` with a module-level `_project_semaphores: Dict[str, asyncio.Semaphore]` dict.

**No new libraries.** `asyncio.Semaphore` is already used. The extension is:

```python
# pool.py addition
_project_semaphores: Dict[str, asyncio.Semaphore] = {}

def get_project_semaphore(project_id: str, max_concurrent: int) -> asyncio.Semaphore:
    if project_id not in _project_semaphores:
        _project_semaphores[project_id] = asyncio.Semaphore(max_concurrent)
    return _project_semaphores[project_id]
```

**Integration:** `project.json` gets `l3_overrides.pool_isolation: "shared" | "isolated"` and `l3_overrides.max_concurrent: 3`. `spawn.py`'s `load_l3_config()` already reads `l3_overrides` — extend it to pass these values through to pool initialization.

**Container labels:** Add `openclaw.project` label to spawned containers (e.g., `"openclaw.project": "pumplai"`) for dashboard filtering. This requires a one-line addition to `spawn.py`'s `labels` dict.

---

### 5. Dashboard Project Switcher

**Implementation:** New API route `workspace/occc/src/app/api/projects/route.ts` + project selector component.

**No new npm packages.** The occc dashboard already has:
- `swr` for polling — reuse for `/api/projects` endpoint
- `zod` for schema validation — extend for project list response
- `lucide-react` for icons — use existing icons (FolderOpen, RefreshCw)
- Tailwind 4 for styling — use existing utility classes

**API route reads** `openclaw.json#active_project` and enumerates `projects/*/project.json` via `fs.readdir` (Node.js stdlib in Next.js API routes). Returns `{ active: string, projects: ProjectManifest[] }`.

**Switch action:** `POST /api/projects/switch` with `{ project_id: string }` body. Writes updated `active_project` to `openclaw.json`. Uses Next.js API route with `fs.writeFile` — no new database or queue.

**UI placement:** Dropdown selector in the existing occc nav/header. Filter tasks displayed by `openclaw.project` container label (already exposed via Dockerode in the swarm API route).

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `argparse` for project CLI | `click` or `typer` | If interactive prompts (password input, multi-select) are required. Currently no such requirement. |
| `string.Template` for SOUL templating | `Jinja2` | If templates need loops, conditionals, or inheritance. Revisit if template complexity grows. |
| Stdlib `pathlib` + `json` for state management | SQLite (via `sqlite3` stdlib) | If state queries become relational (joins across projects). Current flat JSON is sufficient for N < 50 projects. |
| Per-project state files in `.openclaw/<project_id>/` | Single state file with project key prefix | Per-file approach avoids lock contention between projects. Simpler to archive/delete a project. |
| `asyncio.Semaphore` dict for pool isolation | Separate pool process per project | Dict approach reuses existing pool infrastructure. Separate processes would complicate the asyncio event loop. |
| Next.js API route for project switcher | Python FastAPI endpoint | occc already serves the dashboard — no second server needed. `fs` module handles config file reads in the same process. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Jinja2 | Not installed, overkill for simple key substitution in markdown files | `string.Template.safe_substitute()` |
| Click / Typer | Adds dependency for 4 subcommands already expressible in argparse | `argparse` with `add_subparsers()` |
| SQLite for project state | Over-engineering — flat JSON files with file locking already proven in v1.0 | `json` + `fcntl.flock` (existing Jarvis Protocol) |
| A new REST server for project management | Creates another service to manage and keep running | Next.js API routes in the existing occc process |
| Global state dict in `openclaw.json` for per-project container pools | Couples orchestration state to config file, causes write contention | Module-level `_project_semaphores` dict in `pool.py` (in-memory, per process) |
| Docker network namespacing for pool isolation | Physical network isolation at L3 level is already provided by `cap_drop ALL` + `no-new-privileges` | `asyncio.Semaphore` per project (logical isolation of concurrency slots) |

---

## Stack Patterns by Variant

**If project template is `fullstack`:**
- Scaffold `SOUL.md` with Next.js + FastAPI tech stack block
- Set `l3_overrides.runtimes: ["claude-code", "codex"]` in project.json
- Default workspace to `~/Development/Projects/<project_id>`

**If project template is `backend`:**
- Scaffold `SOUL.md` with Python-only tech stack block
- Set `l3_overrides.runtimes: ["claude-code"]`
- Omit frontend stack references from IDENTITY.md

**If project template is `ml-pipeline`:**
- Scaffold `SOUL.md` with Python + GPU references
- Set `l3_overrides.requires_gpu: true`, `mem_limit: "8g"`
- Set `l3_overrides.pool_isolation: "isolated"` by default (GPU contention risk)

**If `pool_isolation: "isolated"` (opt-in):**
- Use `get_project_semaphore(project_id, max_concurrent)` instead of global semaphore
- Container labels include `openclaw.project: <id>` for dashboard filtering
- State file path: `workspace/.openclaw/<project_id>/state.json`

**If `pool_isolation: "shared"` (default):**
- Keep existing global `asyncio.Semaphore(3)` — zero change to `pool.py` behavior
- State file path: `workspace/.openclaw/<project_id>/state.json` (still per-project, isolation is about pool slots not state)

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.14.3 (host) | `string.Template` stdlib | `safe_substitute()` behavior unchanged since Python 3.0. No version concern. |
| Python 3.14.3 (host) | `argparse` stdlib | `add_subparsers(required=True)` available since Python 3.7. No version concern. |
| Next.js 16.1.6 | Node.js `fs/promises` API routes | `fs.readdir` with `{ withFileTypes: true }` works in Node.js 18+ (bundled with Next.js 16). |
| `swr` 2.4.0 | New `/api/projects` endpoint | SWR 2.x `useSWR` with mutation (`useSWRMutation`) handles the switch POST. No upgrade needed. |
| `zod` 4.3.6 | Project manifest schema | Zod 4 schema for `ProjectManifest` — extend existing schemas, no breaking changes. |
| `docker` Python SDK 7.1.0 | New `openclaw.project` label | Labels are a plain dict — backward compatible. Existing containers without the label still listed. |

---

## Sources

- Python 3.14.3 stdlib verification — `python3 -c "import string, argparse, json, pathlib; print('ok')"` run locally (HIGH confidence)
- Jinja2 absence confirmed — `python3 -c "import jinja2"` fails on host (HIGH confidence, verified 2026-02-23)
- `string.Template.safe_substitute()` docs — [https://docs.python.org/3/library/string.html#string.Template](https://docs.python.org/3/library/string.html#string.Template) (HIGH confidence)
- Existing `spawn.py` `labels` dict — read from `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` lines 153-160 (HIGH confidence, source code)
- Existing `pool.py` semaphore pattern — read from `/home/ollie/.openclaw/skills/spawn_specialist/pool.py` lines 44-45 (HIGH confidence, source code)
- Existing `project_config.py` resolver — read from `/home/ollie/.openclaw/orchestration/project_config.py` (HIGH confidence, source code)
- occc `package.json` — confirmed `swr@2.4.0`, `zod@4.3.6`, `next@16.1.6` already present (HIGH confidence)
- `argparse` subparsers pattern — [https://docs.python.org/3/library/argparse.html#sub-commands](https://docs.python.org/3/library/argparse.html#sub-commands) (HIGH confidence)

---

*Stack research for: OpenClaw v1.1 — Project Agnostic multi-project framework additions*
*Researched: 2026-02-23*
*Previous baseline (v1.0): See STACK.md git history — Python 3, Docker SDK, Next.js 16, SWR, Tailwind 4*
