# Phase 14: Project CLI - Research

**Researched:** 2026-02-23
**Domain:** Python CLI development, project scaffolding, argparse subcommands, Docker container detection
**Confidence:** HIGH

## Summary

Phase 14 adds `openclaw project init|list|switch|remove` as a new Python CLI module that wraps the existing orchestration layer. The codebase already provides all the infrastructure needed: `project_config.py` manages project manifests, `soul_renderer.py` writes SOUL.md, and the `projects/` directory structure is established with two real projects (`pumplai`, `geriai`). This phase is a pure CLI surface layer — no new orchestration logic is required.

The existing Python CLI pattern is well-established in `orchestration/monitor.py`: `argparse` with `add_subparsers()`, `Colors` class for ANSI output, and `if __name__ == '__main__': sys.exit(main())`. The new `orchestration/project_cli.py` module should follow the exact same pattern so operators can run it as `python3 orchestration/project_cli.py project <subcommand>` consistently with existing tooling.

The `switch` guard requires detecting running L3 Docker containers per-project. This is already solved: containers are labeled with `openclaw.project=<id>` (confirmed in `spawn.py:204`). A single `client.containers.list(filters={"label": f"openclaw.project={project_id}"})` call is sufficient — no new Docker patterns needed.

**Primary recommendation:** Implement as a single `orchestration/project_cli.py` module following the `monitor.py` argparse pattern. Reuse all existing path APIs. The only net-new logic is interactive prompts for `init`, a table renderer for `list`, and the Docker label filter for the `switch` guard.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Init experience**
- Interactive fallback: if `--id` or `--name` are missing, prompt interactively; flags override prompts
- On ID collision: prompt "Project X exists. Overwrite? [y/N]" in interactive mode; error and exit in non-interactive mode
- Default workspace path: `workspace/<project-id>/` inside the openclaw root directory
- Auto-activate: newly created project becomes the active project immediately

**Safety & edge cases**
- `switch` guard: block if any L3 Docker containers are currently running for the active project (check running containers, not task status)
- `remove` confirmation: always prompt "Remove project X and all its files? [y/N]"; `--force` flag skips confirmation
- `remove` scope: only deletes the project registration (`projects/<id>/` directory with project.json, SOUL.md); workspace directory (`workspace/<id>/`) is preserved
- Corrupt/missing project.json: `list` and `switch` skip broken projects with a warning line (e.g., "(corrupt)"), don't crash or block other projects

### Claude's Discretion
- Output formatting for `list` (table style, colors, column widths)
- Template system implementation details (directory structure, preset contents)
- Error message wording and exit codes
- How interactive prompts are implemented (readline, rich, etc.)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | `openclaw project init` creates `projects/<id>/project.json` from prompts or flags | Existing `project_config.py` has `load_project_config()` + `_find_project_root()`; `soul_renderer.write_soul()` handles SOUL.md output — both ready to call at init time |
| CLI-02 | `openclaw project list` shows all projects with ID, name, workspace, active marker | `monitor.py._discover_projects()` already enumerates `projects/` directory skipping `_`-prefixed entries — reuse this pattern; `get_active_project_id()` provides the active marker; table rendering is Claude's discretion |
| CLI-03 | `openclaw project switch <id>` updates `active_project` in `openclaw.json` | `openclaw.json` is plain JSON; `project_config.py._find_project_root()` locates it; atomic JSON write via read-modify-write; Docker label filter `openclaw.project=<id>` confirms no running containers before allowing switch |
| CLI-04 | `openclaw project remove <id>` deletes project directory with guard against removing active project | `shutil.rmtree(projects/<id>/)` with pre-check against `get_active_project_id()`; workspace directory is preserved by design |
| CLI-05 | `openclaw project init --template fullstack|backend|ml-pipeline` scaffolds from preset templates | Template JSON files in `projects/_templates/`; `init` reads chosen template and merges with explicit flags; template filenames must not match `_discover_projects()` exclusion (already handles `_`-prefixed dirs) |
| CLI-06 | Template presets stored in `projects/_templates/` with sensible defaults per stack type | Three JSON files: `fullstack.json`, `backend.json`, `ml-pipeline.json` — each pre-populates `tech_stack.*` and optionally `l3_overrides` |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib | CLI argument parsing, subcommand dispatch | Already used in `monitor.py`, `soul_renderer.py`, `init.py`, `spawn.py` — project-wide standard |
| `json` | stdlib | Read/write `openclaw.json` and `project.json` | Already used project-wide |
| `pathlib.Path` | stdlib | File system operations | Project-wide standard; all existing modules use `Path` not `os.path` |
| `shutil` | stdlib | `shutil.rmtree()` for directory deletion | Standard for recursive directory removal |
| `docker` | >=7.1.0 (installed) | Detect running L3 containers via label filter | Already a project dependency in `spawn.py`; confirmed importable |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sys` | stdlib | `sys.exit()`, `sys.stderr`, `sys.stdin.isatty()` | TTY detection for non-interactive mode guard |
| `os` | stdlib | `os.environ.get("OPENCLAW_PROJECT")` | Env var checks already in `project_config.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `argparse` | `click` | click is not installed; argparse is stdlib and project standard — do not deviate |
| Manual `input()` calls | `readline` / `rich.prompt` | `input()` is sufficient; rich is not installed; readline only adds history (nice-to-have, not needed) |
| `shutil.rmtree` | `subprocess rm -rf` | `shutil.rmtree` is the correct Python stdlib approach |

**Installation:** No new dependencies required — all libraries are stdlib or already present.

---

## Architecture Patterns

### Recommended Project Structure

```
orchestration/
├── project_cli.py       # NEW: `openclaw project` subcommand group
├── project_config.py    # existing: path resolution, manifest loading
├── soul_renderer.py     # existing: SOUL.md generation
├── monitor.py           # existing: reference pattern for argparse CLI
└── init.py              # existing: workspace init, find_project_root

projects/
├── _templates/          # NEW: template presets (CLI-06)
│   ├── fullstack.json
│   ├── backend.json
│   └── ml-pipeline.json
├── pumplai/
│   └── project.json
└── geriai/
    └── project.json
```

### Pattern 1: argparse subcommand dispatch (from monitor.py)

**What:** Top-level `project` group with four subparsers: `init`, `list`, `switch`, `remove`
**When to use:** Consistent with existing CLI modules in this codebase

```python
# Source: orchestration/monitor.py (project-verified pattern)
parser = argparse.ArgumentParser(description='OpenClaw Project Manager')
subparsers = parser.add_subparsers(dest='command', help='Command to run')

init_parser = subparsers.add_parser('init', help='Create a new project')
init_parser.add_argument('--id', dest='project_id', type=str)
init_parser.add_argument('--name', type=str)
init_parser.add_argument('--template', type=str, choices=['fullstack', 'backend', 'ml-pipeline'])
init_parser.add_argument('--force', action='store_true')

list_parser = subparsers.add_parser('list', help='List all projects')

switch_parser = subparsers.add_parser('switch', help='Switch active project')
switch_parser.add_argument('project_id', type=str)

remove_parser = subparsers.add_parser('remove', help='Remove a project')
remove_parser.add_argument('project_id', type=str)
remove_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
```

### Pattern 2: Active container detection via Docker label filter

**What:** Query Docker daemon for running containers labeled with the project ID before allowing `switch`
**When to use:** `switch` guard implementation (locked decision: check running containers, not task status)

```python
# Source: spawn.py:204 (confirmed label name), docker SDK docs
import docker

def _has_running_l3_containers(project_id: str) -> bool:
    """Return True if any L3 containers for this project are currently running."""
    try:
        client = docker.from_env()
        containers = client.containers.list(
            filters={"label": f"openclaw.project={project_id}"}
        )
        return len(containers) > 0
    except Exception:
        # If Docker is unreachable, err on the side of caution: allow switch
        return False
```

**Verified:** `docker.from_env()` + `containers.list(filters={"label": ...})` confirmed working in this environment (returned empty list for pumplai, Docker reachable).

### Pattern 3: Atomic openclaw.json update for `switch`

**What:** Read-modify-write pattern for updating `active_project` in `openclaw.json`
**When to use:** `switch` subcommand

```python
# Source: project_config.py pattern + standard JSON r/w
def _set_active_project(project_id: str) -> None:
    root = _find_project_root()
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    config["active_project"] = project_id
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')  # trailing newline convention
```

**Note:** The openclaw.json config validator warns about `active_project` being an "unrecognized key" (seen in CLI output), but the key is already present in the file and consumed by `project_config.py`. Do not remove or rename it.

### Pattern 4: Project enumeration (from monitor.py._discover_projects)

**What:** Enumerate `projects/` directory, skipping entries whose names start with `_`
**When to use:** `list` subcommand, `init` ID collision check

```python
# Source: orchestration/monitor.py:_discover_projects (verified)
def _list_projects(root: Path) -> list[dict]:
    """Return list of project dicts with id, name, workspace, status."""
    projects_dir = root / "projects"
    results = []
    if not projects_dir.exists():
        return results
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        manifest_path = entry / "project.json"
        try:
            with open(manifest_path) as f:
                cfg = json.load(f)
            results.append({"id": entry.name, "config": cfg, "corrupt": False})
        except Exception:
            results.append({"id": entry.name, "config": None, "corrupt": True})
    return results
```

### Pattern 5: Template loading for `init --template`

**What:** Load a JSON template from `projects/_templates/<template>.json`, merge with explicit flags
**When to use:** `init --template fullstack|backend|ml-pipeline`

```python
# Template files contain partial project.json structure
# Explicit flags (--id, --name, workspace) always override template values
def _load_template(template_name: str, root: Path) -> dict:
    template_path = root / "projects" / "_templates" / f"{template_name}.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    with open(template_path) as f:
        return json.load(f)
```

### Pattern 6: Non-interactive mode detection

**What:** Use `sys.stdin.isatty()` to detect piped/scripted context; fail fast on missing required fields
**When to use:** `init` command — interactive fallback only when running in a real terminal

```python
def _is_interactive() -> bool:
    return sys.stdin.isatty()

# In init handler:
if not project_id:
    if _is_interactive():
        project_id = input("Project ID: ").strip()
    else:
        print("Error: --id is required in non-interactive mode", file=sys.stderr)
        sys.exit(1)
```

### Pattern 7: `init` auto-activation — write project.json first, then update openclaw.json

**What:** Write `projects/<id>/project.json` first; on success, render SOUL.md; on success, set `active_project`
**When to use:** `init` subcommand — ensures partial failures leave a clean state

### Anti-Patterns to Avoid

- **Do not import `docker` at module level unconditionally:** If Docker SDK import fails (e.g., missing from env), the entire `project_cli.py` becomes unimportable. Use a try/except import at function call site or lazy import.
- **Do not write openclaw.json with `json.dumps` without indent:** The existing file uses `indent=2` formatting — preserve it to avoid noisy diffs.
- **Do not enumerate `projects/` without the `_` prefix guard:** `projects/_templates/` must be invisible to `list` and `switch` — the leading underscore exclusion is the established convention (from `_discover_projects`).
- **Do not delete workspace directory on `remove`:** Locked decision — only `projects/<id>/` is deleted; `workspace/<id>/` is preserved.
- **Do not hardcode the openclaw root path:** Always use `_find_project_root()` from `project_config.py`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container status detection | Custom Docker API call or task state parsing | `docker.containers.list(filters={"label": ...})` | Label filter is O(1), accurate, and already proven — task state can be stale |
| Project directory enumeration | Custom file walker | Pattern from `monitor.py._discover_projects()` | Already handles `_` prefix exclusion and error cases |
| SOUL.md generation | String concatenation | `soul_renderer.write_soul(project_id, skip_if_exists=True)` | Full template + override merge already implemented |
| Project root resolution | `os.getcwd()` or hardcoded path | `_find_project_root()` from `project_config.py` | Handles `OPENCLAW_ROOT` env var and walk-up logic |
| Project ID validation | Ad-hoc regex | `_validate_project_id()` from `spawn.py` (or copy the pattern) | Established rule: `^[a-zA-Z0-9-]{1,20}$` |

**Key insight:** This phase has nearly zero net-new business logic. Every non-trivial operation has an existing implementation to call or copy. The value is in assembling the surface, not rebuilding internals.

---

## Common Pitfalls

### Pitfall 1: L2 agent ID validation not performed at `init` time
**What goes wrong:** User creates a project with `agents.l2_pm` set to an ID that doesn't exist in `openclaw.json:agents.list` — silent failure when L2 tries to run.
**Why it happens:** The init command writes project.json without cross-referencing openclaw.json agent registry.
**How to avoid:** After writing project.json, check that `config["agents"]["l2_pm"]` exists in `openclaw.json:agents.list[*].id`. Print a warning (not error) if missing, since the agent list might be added later. This was flagged in STATE.md Blockers.
**Warning signs:** `load_l3_config()` in spawn.py silently falls back to `l3_specialist` if agent map is missing — same silent failure risk for l2_pm.

### Pitfall 2: openclaw.json write races with gateway process
**What goes wrong:** Gateway process reads openclaw.json while `switch` is writing it — partial JSON corrupts the gateway config.
**Why it happens:** No file locking on openclaw.json writes in the codebase.
**How to avoid:** Write to a `.tmp` file first, then `Path.rename()` (atomic on Linux). The `state_engine.py` uses `fcntl.flock()` for workspace state but openclaw.json has no such protection. For a CLI tool running interactively, a simple write is likely acceptable — but document the risk. The existing monitor.py and project_config.py write directly without locking; be consistent.
**Warning signs:** Gateway config errors after a `switch` in a live session.

### Pitfall 3: Docker SDK import failure at module load time
**What goes wrong:** `import docker` at top of `project_cli.py` fails in environments where the Docker SDK is not installed, making the entire module unusable even for `list` and `init` which don't need Docker.
**Why it happens:** Only `switch` needs Docker for the running-container guard.
**How to avoid:** Lazy-import docker inside `_has_running_l3_containers()` or wrap in try/except and degrade gracefully (print warning, allow switch). Verified: `docker` is importable in the current environment.

### Pitfall 4: `list` crashing on corrupt project.json
**What goes wrong:** A project directory has a malformed `project.json` (empty, invalid JSON, missing fields) — `list` raises an exception and exits without showing any projects.
**Why it happens:** `load_project_config()` raises on malformed JSON.
**How to avoid:** Per locked decision: catch exceptions per-entry in the enumeration loop, append a `(corrupt)` row to the table, continue. Do not propagate exceptions from individual project reads.

### Pitfall 5: `init` with duplicate ID in non-interactive mode
**What goes wrong:** `init --id existing-project` in a script silently overwrites project.json.
**Why it happens:** No ID collision check.
**How to avoid:** Per locked decision — in non-interactive mode (`not sys.stdin.isatty()`): error and exit. In interactive mode: prompt "Project X exists. Overwrite? [y/N]".

### Pitfall 6: SOUL.md write path derived incorrectly
**What goes wrong:** `write_soul()` derives the SOUL.md output path from `project_config["agents"]["l2_pm"]` — if the l2_pm agent ID doesn't match a real agent directory, parent `mkdir` succeeds but the agent directory is phantom.
**Why it happens:** `write_soul()` creates parent dirs with `mkdir(parents=True, exist_ok=True)`.
**How to avoid:** After `write_soul()` succeeds, print the path so the operator can see where it was written. Not a correctness issue but aids debuggability.

---

## Code Examples

### project.json schema (from existing projects)
```json
{
  "id": "myproject",
  "name": "My Project",
  "agent_display_name": "MyProject_PM",
  "workspace": "/home/ollie/.openclaw/workspace/myproject",
  "tech_stack": {
    "frontend": "",
    "backend": "",
    "infra": ""
  },
  "agents": {
    "l2_pm": "myproject_pm",
    "l3_executor": "l3_specialist"
  },
  "l3_overrides": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"]
  }
}
```
**Source:** `projects/pumplai/project.json` and `projects/geriai/project.json` — verified.

### Template file schema (new, for projects/_templates/)
```json
{
  "_template": "fullstack",
  "tech_stack": {
    "frontend": "Next.js, React, Tailwind CSS",
    "backend": "Python, FastAPI",
    "infra": "Docker, PostgreSQL"
  },
  "l3_overrides": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"]
  }
}
```

### Template file schema for backend preset
```json
{
  "_template": "backend",
  "tech_stack": {
    "frontend": "",
    "backend": "Python, FastAPI",
    "infra": "Docker, PostgreSQL"
  },
  "l3_overrides": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"]
  }
}
```

### Template file schema for ml-pipeline preset
```json
{
  "_template": "ml-pipeline",
  "tech_stack": {
    "frontend": "",
    "backend": "Python, PyTorch, FastAPI",
    "infra": "Docker, NVIDIA GPU, MLflow"
  },
  "l3_overrides": {
    "mem_limit": "8g",
    "cpu_quota": 200000,
    "runtimes": ["claude-code", "codex", "gemini-cli"]
  }
}
```

### Default project.json for init (no template)
```python
# Source: existing project.json files + project_config.py defaults
def _build_default_project_json(project_id: str, name: str, workspace: str) -> dict:
    return {
        "id": project_id,
        "name": name,
        "agent_display_name": f"{name.replace(' ', '')}_PM",
        "workspace": workspace,
        "tech_stack": {
            "frontend": "",
            "backend": "",
            "infra": ""
        },
        "agents": {
            "l2_pm": f"{project_id}_pm",
            "l3_executor": "l3_specialist"
        },
        "l3_overrides": {
            "mem_limit": "4g",
            "cpu_quota": 100000,
            "runtimes": ["claude-code", "codex", "gemini-cli"]
        }
    }
```

### `list` table output format (Claude's discretion — recommendation)
```
ID              NAME            WORKSPACE                               ACTIVE
──────────────────────────────────────────────────────────────────────────────
pumplai         PumplAI         /home/ollie/Development/Projects/pum…  *
geriai          GerIAI          /home/ollie/Development/Projects/ger…
badproject      (corrupt)       —
```
Column widths: ID=15, NAME=15, WORKSPACE=40 (truncated), ACTIVE=6. Use the existing `Colors` class for ANSI.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON editing | `openclaw project init/switch` | Phase 14 (this phase) | Operators no longer need to know project.json schema |
| Fixed `pumplai` project only | Multi-project with `projects/` directory | Phase 11-13 (complete) | CLI builds on already-solid foundation |
| SOUL.md hand-authored | `soul_renderer.write_soul()` called at init | Phase 12 (complete) | Init can auto-generate SOUL.md — no extra steps |

**Deprecated/outdated:**
- Manual `cp projects/pumplai/project.json projects/<id>/project.json`: The error message in `project_config.py:72` still says to do this — Phase 14 makes it obsolete. The planner should note this message can be updated as a cleanup task.

---

## Open Questions

1. **Should `init` validate that `agents.l2_pm` exists in `openclaw.json:agents.list`?**
   - What we know: STATE.md explicitly flags this as a silent failure risk. `spawn.py` validates project ID format but not agent ID existence.
   - What's unclear: Whether a warning is sufficient or should be a hard error. The user might add the agent entry to `openclaw.json` separately.
   - Recommendation: Print a warning (yellow, non-fatal) if `agents.l2_pm` value not found in `openclaw.json:agents.list[*].id`. Do not block init — agent registration is a separate concern.

2. **Should `project_cli.py` be invokable as `python3 orchestration/project_cli.py project <subcommand>` or just `python3 orchestration/project_cli.py <subcommand>`?**
   - What we know: `monitor.py` uses `python3 orchestration/monitor.py tail` (subcommand is the first positional arg, no "project" prefix). The Node.js `openclaw` CLI would call the Python script directly.
   - What's unclear: The phase goal says `openclaw project init` — if this is the Node.js CLI dispatching to Python, the "project" prefix is handled by the Node.js layer. If this is purely standalone Python, include "project" as a top-level group.
   - Recommendation: Implement as `python3 orchestration/project_cli.py <init|list|switch|remove>` — the "project" grouping is implied by the module name. This mirrors how `monitor.py tail` works (no "monitor" prefix). Leave integration with the Node.js `openclaw` binary to a future phase or operator configuration.

3. **What is the `agent_display_name` convention for newly created projects?**
   - What we know: `pumplai` uses `"PumplAI_PM"`, `geriai` uses `"GerIAI_PM"`. The `soul_renderer.build_variables()` falls back to `agents.l2_pm` if `agent_display_name` is absent.
   - Recommendation: Default to `f"{name.replace(' ', '')}_PM"` — strips spaces from the project name and appends `_PM`. Operator can override via prompt or flag.

---

## Sources

### Primary (HIGH confidence)
- `/home/ollie/.openclaw/orchestration/monitor.py` — argparse subcommand pattern, Colors class, `_discover_projects()` implementation
- `/home/ollie/.openclaw/orchestration/project_config.py` — `_find_project_root()`, `get_active_project_id()`, `load_project_config()`, `get_state_path()`, project ID validation
- `/home/ollie/.openclaw/orchestration/soul_renderer.py` — `write_soul()`, `build_variables()`, skip_if_exists behavior
- `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` — container naming pattern (`openclaw-{project_id}-l3-{task_id}`), label `openclaw.project`, `_validate_project_id()`
- `/home/ollie/.openclaw/projects/pumplai/project.json` and `geriai/project.json` — canonical project.json schema
- `/home/ollie/.openclaw/openclaw.json` — `active_project` field structure confirmed, `agents.list` structure verified
- Live Docker test: `client.containers.list(filters={"label": "openclaw.project=pumplai"})` returned empty list — SDK works, filter syntax confirmed

### Secondary (MEDIUM confidence)
- `orchestration/init.py` — `find_project_root()`, SOUL auto-init pattern at workspace initialization
- `orchestration/__init__.py` — public API exports available to `project_cli.py`

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, all confirmed importable, project pattern verified
- Architecture: HIGH — based entirely on reading existing codebase modules
- Pitfalls: HIGH — derived from STATE.md explicit blockers and direct code inspection
- Template content: MEDIUM — sensible defaults from project knowledge, no external verification needed

**Research date:** 2026-02-23
**Valid until:** 2026-04-23 (stable domain — stdlib + existing codebase patterns do not expire)
