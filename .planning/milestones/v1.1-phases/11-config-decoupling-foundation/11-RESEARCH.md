# Phase 11: Config Decoupling Foundation - Research

**Researched:** 2026-02-23
**Domain:** Python path resolution, config module design, data migration, git branch detection
**Confidence:** HIGH — all findings based on direct codebase inspection; no external library APIs required

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Path convention**
- All per-project runtime state lives under `workspace/.openclaw/<project_id>/`
- State file: `workspace/.openclaw/<project_id>/workspace-state.json`
- Snapshots organized by task: `workspace/.openclaw/<project_id>/snapshots/<task_id>/`
- The existing PumplAI project uses project ID `pumplai`
- Project config/manifest lives separately at `projects/<id>/project.json` (top-level, not under .openclaw)

**Migration strategy**
- Migration is an explicit CLI command (not automatic on first run)
- Block migration if any tasks are in spawned/running state — print which tasks are blocking
- No --force flag; user must wait for tasks to complete
- Backup old state to a `.backup/` dir before moving files to new location
- Hard cutover after migration — old paths stop working immediately with clear error pointing to new location

**Config resolution API**
- New dedicated module: `orchestration/project_config.py` (separate from existing config.py)
- Active project resolution: check `OPENCLAW_PROJECT` env var first, fall back to `active_project` field in `openclaw.json`
- Agent IDs are mapped explicitly in `projects/<id>/project.json` agents field (not convention-based lookup)
- Invalid/unknown project IDs raise `ProjectNotFoundError` — no silent fallback to wrong paths

**Branch detection**
- Check `default_branch` field in project.json first
- Fall back to `git symbolic-ref refs/remotes/origin/HEAD` if not configured
- Detect fresh on every snapshot operation (no caching)

### Claude's Discretion
- Last-resort fallback behavior when neither config nor git heuristic can determine the default branch
- Internal structure of the backup directory during migration
- Exact error message wording for migration guards and path resolution errors
- How `project_config.py` internally loads and validates project.json

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-01 | Per-project state file at `workspace/.openclaw/<project_id>/workspace-state.json` | Path API in `project_config.py`; `spawn.py` and `pool.py` must call `get_state_path()` instead of hardcoding |
| CFG-02 | Per-project snapshot directory at `workspace/.openclaw/<project_id>/snapshots/` | `snapshot.py` `capture_semantic_snapshot` currently hardcodes `workspace / '.openclaw' / 'snapshots'`; needs `get_snapshot_dir(project_id)` |
| CFG-03 | `project_config.py` exposes `get_state_path(project_id)` and `get_snapshot_dir(project_id)` | Module already exists; two new functions must be added |
| CFG-06 | `snapshot.py` detects default branch dynamically instead of hardcoding `"main"` | Branch detection already partially implemented in `create_staging_branch`; `capture_semantic_snapshot` and `l2_review_diff` and `l2_merge_staging` still hardcode `"main"` |
| CFG-07 | Agent `config.json` hierarchy references resolve from project config, not hardcoded strings | `spawn.py` `load_l3_config` hardcodes `agents/l3_specialist/config.json` path; agent ID in `config.json` fields like `reports_to` and `spawned_by` are static strings |
</phase_requirements>

---

## Summary

Phase 11 is an internal refactoring of OpenClaw's Python orchestration layer. No new user-facing features are added. The entire change surface is: one new module enhancement (`project_config.py`), three files updated to call the new path APIs (`spawn.py`, `pool.py`, `snapshot.py`), a migration CLI script, and a path-awareness fix throughout `snapshot.py`.

The codebase is clean Python 3 with no external dependencies beyond the standard library and `docker>=7.1.0`. No new packages are required. The `project_config.py` module already exists with the correct structure; it needs two new functions added. The hardcoded path `workspace/.openclaw/workspace-state.json` appears in three locations: `config.py` (default constant), `spawn.py` (line 177), and `pool.py` (line 50). The hardcoded path `workspace/.openclaw/snapshots` appears in `snapshot.py` (line 209) and `init.py` (lines 73, 112). All of these must route through `project_config.py`.

The migration's most important constraint is the in-flight task guard. The current state file at `workspace/.openclaw/workspace-state.json` contains three tasks, two with status `pending` and one with status `in_progress`. The migration command must read this file, check for non-terminal statuses, and refuse to proceed if any are found. After migration, the old path must produce a clear error rather than silently creating a new empty state file.

**Primary recommendation:** Add `get_state_path(project_id)` and `get_snapshot_dir(project_id)` to the existing `project_config.py`, update all four call sites, fix the three hardcoded-`"main"` references in `snapshot.py`, then write the migration script that copies `workspace/.openclaw/workspace-state.json` to `workspace/.openclaw/pumplai/workspace-state.json`.

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python standard library: `pathlib.Path` | stdlib | All path construction | Already used throughout; `Path` object composition is idiomatic |
| Python standard library: `shutil` | stdlib | File copy/move during migration | `shutil.copy2` preserves metadata; `shutil.move` for atomic rename |
| Python standard library: `json` | stdlib | Read/write state files | Already used throughout |
| Python standard library: `argparse` | stdlib | Migration CLI | Already used in `monitor.py`, `spawn.py` — consistent pattern |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `os.environ.get()` | stdlib | `OPENCLAW_PROJECT` env var resolution | Already pattern in `project_config.py` |
| `fcntl.flock()` | stdlib | Lock state file during migration read | Already used in `JarvisState`; migration should use `JarvisState.read_state()` to check for in-flight tasks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `shutil.copy2` + manual rename | `shutil.move` | `copy2` safer for migration (backup first, then verify, then delete old); `move` is atomic but no safety net |
| Re-implementing file lock in migration | Calling `JarvisState.read_state()` | Always prefer existing `JarvisState` API — it already handles lock retry logic |

---

## Architecture Patterns

### Recommended File Layout After Phase 11

```
workspace/
└── .openclaw/
    ├── pumplai/
    │   ├── workspace-state.json     # CFG-01: was workspace/.openclaw/workspace-state.json
    │   └── snapshots/               # CFG-02: was workspace/.openclaw/snapshots/
    │       └── <task_id>/           # per-task snapshot directory
    └── .backup/                     # migration backup (internal structure: Claude's discretion)
        └── workspace-state.json.bak

orchestration/
├── config.py           # unchanged: LOCK_TIMEOUT, POLL_INTERVAL (STATE_FILE/SNAPSHOT_DIR constants removed or deprecated)
├── project_config.py   # extended: get_state_path(), get_snapshot_dir() added
├── snapshot.py         # updated: remove hardcoded "main" in all 3 functions; use get_snapshot_dir()
├── state_engine.py     # unchanged: JarvisState still accepts a path argument — callers supply it
├── monitor.py          # updated: default --state-file computed from project_config.get_state_path()
└── init.py             # updated: initialize per-project dirs, not global dirs
```

### Pattern 1: Path API in project_config.py

**What:** Two pure functions that take a `project_id` (or default to active project) and return a `Path`.
**When to use:** Every time orchestration code needs the state file or snapshot directory.

```python
# orchestration/project_config.py

class ProjectNotFoundError(Exception):
    """Raised when project manifest does not exist for a given project_id."""
    pass


def get_state_path(project_id: Optional[str] = None) -> Path:
    """
    Return the per-project state file path.

    Path: <project_root>/workspace/.openclaw/<project_id>/workspace-state.json

    Raises:
        ProjectNotFoundError: If project_id has no manifest in projects/<id>/project.json
        ValueError: If no active project is configured and project_id is None
    """
    if project_id is None:
        project_id = get_active_project_id()

    # Validate project exists
    root = _find_project_root()
    manifest_path = root / "projects" / project_id / "project.json"
    if not manifest_path.exists():
        raise ProjectNotFoundError(
            f"Project '{project_id}' not found. No manifest at {manifest_path}"
        )

    return root / "workspace" / ".openclaw" / project_id / "workspace-state.json"


def get_snapshot_dir(project_id: Optional[str] = None) -> Path:
    """
    Return the per-project snapshot directory path.

    Path: <project_root>/workspace/.openclaw/<project_id>/snapshots/

    Raises:
        ProjectNotFoundError: If project_id has no manifest in projects/<id>/project.json
        ValueError: If no active project is configured and project_id is None
    """
    if project_id is None:
        project_id = get_active_project_id()

    root = _find_project_root()
    manifest_path = root / "projects" / project_id / "project.json"
    if not manifest_path.exists():
        raise ProjectNotFoundError(
            f"Project '{project_id}' not found. No manifest at {manifest_path}"
        )

    return root / "workspace" / ".openclaw" / project_id / "snapshots"
```

### Pattern 2: Call Site Updates — spawn.py and pool.py

**What:** Replace hardcoded state file paths with calls to `get_state_path()`.

```python
# skills/spawn_specialist/spawn.py  — line 177 currently:
# state_file = project_root / "workspace" / ".openclaw" / "workspace-state.json"
# Replace with:
from orchestration.project_config import get_state_path
state_file = get_state_path()  # uses OPENCLAW_PROJECT env var or active_project

# skills/spawn_specialist/pool.py  — __init__ line 50 currently:
# self.state_file = self.project_root / "workspace" / ".openclaw" / "workspace-state.json"
# Replace with:
from orchestration.project_config import get_state_path
self.state_file = get_state_path()
```

### Pattern 3: snapshot.py — Remove Hardcoded "main"

**What:** Three functions in `snapshot.py` hardcode `"main"` as the diff base. They must call a shared helper to detect the default branch from project.json or git.

**Current hardcoded locations in snapshot.py:**
1. `capture_semantic_snapshot` line 170: `'diff', 'main...HEAD'`
2. `capture_semantic_snapshot` line 180: `'diff', '--stat', 'main...HEAD'`
3. `l2_review_diff` line 263: `'diff', '--stat', f'main...{branch_name}'`
4. `l2_review_diff` line 272: `'diff', f'main...{branch_name}'`
5. `l2_merge_staging` line 309: `'checkout', 'main'`
6. `l2_merge_staging` line 319: `'merge', '--no-ff', branch_name, '-m', f'Merge L3 task {task_id} into main'`
7. `l2_reject_staging` line 393: `'checkout', 'main'`

Note: `create_staging_branch` already has branch detection logic (lines 79-104) but the result is local to that function. The detection logic needs to be extracted into a standalone helper so all functions can call it.

```python
# Extract existing detection from create_staging_branch into a module-level function:

def _detect_default_branch(workspace: Path, project_id: Optional[str] = None) -> str:
    """
    Detect the default branch for a workspace.

    Resolution order:
    1. project.json default_branch field
    2. git symbolic-ref refs/remotes/origin/HEAD
    3. Check if 'main' exists locally
    4. Check if 'master' exists locally
    5. Fallback: "main" (Claude's discretion — see Open Questions)

    Fresh detection on every call (no caching per locked decision).
    """
    # 1. Project config
    if project_id is not None:
        try:
            config = load_project_config(project_id)
            if "default_branch" in config:
                return config["default_branch"]
        except (FileNotFoundError, ValueError):
            pass

    # 2. Git symbolic-ref
    try:
        result = subprocess.run(
            ['git', '-C', str(workspace), 'symbolic-ref', 'refs/remotes/origin/HEAD'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('/')[-1]
    except Exception:
        pass

    # 3 & 4. Local branch existence
    for candidate in ('main', 'master'):
        result = subprocess.run(
            ['git', '-C', str(workspace), 'rev-parse', '--verify', candidate],
            capture_output=True
        )
        if result.returncode == 0:
            return candidate

    # 5. Last resort fallback
    return "main"
```

### Pattern 4: snapshot.py — Per-Project Snapshot Directory

**What:** `capture_semantic_snapshot` currently writes to `workspace / '.openclaw' / 'snapshots'`. It must use `get_snapshot_dir()`.

```python
# snapshot.py capture_semantic_snapshot — current line 209:
# snapshots_dir = workspace / '.openclaw' / 'snapshots'
# Replace with:
from .project_config import get_snapshot_dir
snapshots_dir = get_snapshot_dir()  # or pass project_id explicitly
snapshots_dir.mkdir(parents=True, exist_ok=True)
```

### Pattern 5: Migration CLI

**What:** Standalone script `orchestration/migrate_state.py` that moves the legacy state file to the new per-project path.

```python
#!/usr/bin/env python3
"""
Migrate workspace state to per-project path convention.

Usage:
    python3 orchestration/migrate_state.py [--project pumplai]

This command is IDEMPOTENT — safe to run multiple times.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestration.state_engine import JarvisState
from orchestration.project_config import get_state_path, _find_project_root

IN_FLIGHT_STATUSES = {'spawned', 'running', 'in_progress', 'starting', 'testing'}

def main():
    parser = argparse.ArgumentParser(description="Migrate OpenClaw state to per-project paths")
    parser.add_argument("--project", default="pumplai", help="Project ID (default: pumplai)")
    args = parser.parse_args()

    project_root = _find_project_root()
    old_path = project_root / "workspace" / ".openclaw" / "workspace-state.json"
    new_path = get_state_path(args.project)

    # Check if already migrated
    if not old_path.exists():
        if new_path.exists():
            print(f"Already migrated. State file at: {new_path}")
            return 0
        else:
            print(f"No state file found at old path: {old_path}")
            print(f"Creating empty state at new path: {new_path}")
            # Create empty state at new location
            new_path.parent.mkdir(parents=True, exist_ok=True)
            JarvisState(new_path)._ensure_state_file()
            return 0

    # Read and inspect old state
    js = JarvisState(old_path)
    state = js.read_state()
    tasks = state.get("tasks", {})

    # Guard: check for in-flight tasks
    blocking_tasks = [
        tid for tid, tdata in tasks.items()
        if tdata.get("status") in IN_FLIGHT_STATUSES
    ]
    if blocking_tasks:
        print("ERROR: Cannot migrate while tasks are in-flight.")
        print("Blocking tasks:")
        for tid in blocking_tasks:
            status = tasks[tid].get("status", "unknown")
            print(f"  - {tid} ({status})")
        print("Wait for all tasks to complete or fail, then run migration again.")
        return 1

    # Print before/after summary
    print(f"Migration plan:")
    print(f"  Old state file: {old_path}")
    print(f"  New state file: {new_path}")
    if tasks:
        print(f"  Tasks to migrate: {len(tasks)}")
        for tid, tdata in tasks.items():
            print(f"    - {tid} ({tdata.get('status', 'unknown')})")
    else:
        print("  Tasks to migrate: 0 (empty state)")
    print()

    # Create backup
    backup_dir = project_root / "workspace" / ".openclaw" / ".backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / "workspace-state.json.bak"
    shutil.copy2(old_path, backup_path)
    print(f"Backed up to: {backup_path}")

    # Create new directory and copy state
    new_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old_path, new_path)
    print(f"Copied state to: {new_path}")

    # Verify copy integrity
    with open(new_path) as f:
        verify = json.load(f)
    assert len(verify.get("tasks", {})) == len(tasks), "Task count mismatch after copy"

    # Hard cutover: replace old file with sentinel
    sentinel = {
        "migrated": True,
        "new_path": str(new_path),
        "error": (
            f"This state file has been migrated to {new_path}. "
            "Update callers to use project_config.get_state_path()."
        )
    }
    with open(old_path, 'w') as f:
        json.dump(sentinel, f, indent=2)
    print(f"Old path sentineled: {old_path}")

    print()
    print("Migration complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Pattern 6: CFG-07 — Agent Config References from Project Manifest

**What:** `spawn.py` hardcodes `agents/l3_specialist/config.json` as the path to L3 config. The `config.json` itself hardcodes `"reports_to": "pumplai_pm"` and `"spawned_by": "pumplai_pm"`. The locked decision says agent IDs resolve from `projects/<id>/project.json` agents field.

**Current state in spawn.py `load_l3_config()`:**
```python
config_path = Path(__file__).parent.parent.parent / "agents" / "l3_specialist" / "config.json"
```

The agents field in `projects/pumplai/project.json` is already `{"l2_pm": "pumplai_pm", "l3_executor": "l3_specialist"}`. The `spawn.py` already reads `agent_map.get("l2_pm")` for `spawned_by` (lines 113-117), so partial implementation exists.

**What remains:** The L3 agent config path (`agents/l3_specialist/config.json`) should be resolved using `agents.l3_executor` from `project.json`, not a hardcoded string. This means `load_l3_config()` should:
1. Get `l3_executor` ID from `get_agent_mapping()` (already a function in `project_config.py`)
2. Build config path as `agents/<l3_executor_id>/config.json`

```python
def load_l3_config(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Load L3 specialist configuration from project-resolved agent path."""
    try:
        agent_map = get_agent_mapping(project_id)
        l3_agent_id = agent_map.get("l3_executor", "l3_specialist")
    except (FileNotFoundError, ValueError):
        l3_agent_id = "l3_specialist"

    config_path = Path(__file__).parent.parent.parent / "agents" / l3_agent_id / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    # Apply project-level L3 overrides if available (existing logic preserved)
    ...
```

### Anti-Patterns to Avoid

- **Modifying `config.py` to add project-scoped paths**: `config.py` is a module-level constant file; it cannot know the project at import time. All project-scoped paths belong in `project_config.py`.
- **Auto-migrating on first read of old path**: The locked decision is explicit CLI only. `JarvisState.__init__` must NOT silently migrate.
- **Caching default branch detection**: Locked decision says fresh detection on every snapshot operation. Do not add an `@lru_cache` or module-level variable.
- **Using `shutil.move` before backup**: Always `copy2` to backup first, verify, then sentinel the old path. `move` leaves no recovery option if something fails mid-migration.
- **Silent fallback when `ProjectNotFoundError`**: The locked decision says invalid project IDs raise `ProjectNotFoundError` — no silent fallback. Do not catch this exception in `get_state_path()` or `get_snapshot_dir()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File locking during migration | Custom lock mechanism | `JarvisState.read_state()` (calls `_acquire_lock` internally) | Already handles retry logic and timeouts |
| Task status inspection | Re-read JSON manually | `JarvisState.read_state()` then inspect `tasks` dict | Handles corrupt JSON gracefully |
| Directory creation | `os.makedirs` | `Path.mkdir(parents=True, exist_ok=True)` | Already used throughout codebase — stay consistent |
| JSON copy verification | Byte comparison | Load JSON and compare task count | Structural verification is more meaningful than byte equality |

---

## Common Pitfalls

### Pitfall 1: State File Sentinel Not Detected by JarvisState

**What goes wrong:** After migration, the old path contains a JSON sentinel. Any code that still uses the old path will call `JarvisState(old_path)`, which calls `_read_state_locked`. The sentinel JSON is valid JSON but has no `tasks` key and a top-level `error` key. `read_state()` returns it without error — the caller silently operates on empty state.

**Why it happens:** `JarvisState` is designed to handle any valid JSON (returns empty state on missing keys). It does not validate the schema beyond checking for a `tasks` key.

**How to avoid:** After migration, callers that still use the old hardcoded path must be updated. The sentinel approach alone is not sufficient for silent prevention — it is an audit trail, not a hard block. The real fix is ensuring ALL four call sites (config.py default, spawn.py line 177, pool.py line 50, entrypoint.sh line 11) are updated to use `get_state_path()`.

**Warning signs:** `monitor.py status` shows zero tasks after migration even though tasks exist.

### Pitfall 2: Docker Entrypoint Still Uses Hardcoded Path

**What goes wrong:** `docker/l3-specialist/entrypoint.sh` line 11 hardcodes `STATE_FILE="/workspace/.openclaw/workspace-state.json"`. After migration, L3 containers write status updates to the old (non-existent or sentinel) path.

**Why it happens:** The entrypoint runs inside Docker; it does not call `project_config.py`. It only has access to environment variables.

**How to avoid:** The spawner (`spawn.py`) must inject `STATE_FILE` as an environment variable into the container, computed from `get_state_path()`. The entrypoint already reads from environment variables — change `STATE_FILE` from a hardcoded string to `STATE_FILE="${OPENCLAW_STATE_FILE:-/workspace/.openclaw/workspace-state.json}"` (fallback for backward compat during transition).

**Warning signs:** L3 container activity logs are missing from the post-migration state file even though containers ran successfully.

### Pitfall 3: init.py Creates Old Directory Structure

**What goes wrong:** `orchestration/init.py` `initialize_workspace()` hardcodes `workspace/.openclaw/snapshots` (line 73) and `verify_workspace()` hardcodes `workspace/.openclaw` (line 112). After Phase 11, calling `init.py` would recreate the old paths.

**Why it happens:** `init.py` was written before per-project paths were planned.

**How to avoid:** Update `init.py` to accept a `project_id` argument and call `get_state_path()` / `get_snapshot_dir()` for path construction. The `verify_workspace` check should verify the per-project directory exists.

### Pitfall 4: Migration Run While tasks Are `"pending"`

**What goes wrong:** The state file currently has two tasks with status `"pending"` (not `"in_progress"`). If the migration guard only blocks on `"in_progress"`, it will proceed while pending tasks exist. Those pending tasks reference `container_name` metadata for containers that may still be planned.

**Why it happens:** "In-flight" is ambiguous — the locked decision says "spawned/running state." `"pending"` tasks may not have spawned containers yet, but they represent committed intent.

**How to avoid:** Define `IN_FLIGHT_STATUSES = {'spawned', 'running', 'in_progress', 'starting', 'testing'}`. Do NOT include `"pending"` in the block list — pending tasks have no live container and can be safely migrated. Only statuses that indicate a container is actively running should block migration.

### Pitfall 5: snapshot.py cleanup_old_snapshots Uses Old Path

**What goes wrong:** `cleanup_old_snapshots` in `snapshot.py` (line 443) hardcodes `workspace / '.openclaw' / 'snapshots'`. After the migration, this function would operate on an empty or non-existent directory.

**Why it happens:** It was overlooked — it is in the same file but not in the listed hardcoded locations.

**How to avoid:** Update `cleanup_old_snapshots` signature to accept an optional `project_id` and use `get_snapshot_dir(project_id)` for the snapshots directory.

---

## Code Examples

Verified patterns from direct codebase inspection:

### get_active_project_id() — Existing Pattern to Follow
```python
# orchestration/project_config.py — existing, already correct
def get_active_project_id() -> str:
    env_project = os.environ.get("OPENCLAW_PROJECT")
    if env_project:
        return env_project
    root = _find_project_root()
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    project_id = config.get("active_project")
    if not project_id:
        raise ValueError("No active project set. ...")
    return project_id
```

### Current Hardcoded Path Inventory (All Must Be Fixed)

| File | Line(s) | Hardcoded Value | Fix |
|------|---------|----------------|-----|
| `orchestration/config.py` | 6-8 | `workspace/.openclaw/workspace-state.json` | Deprecate or remove; downstream callers use `get_state_path()` |
| `orchestration/config.py` | 18-21 | `workspace/.openclaw/snapshots/` | Deprecate or remove; downstream callers use `get_snapshot_dir()` |
| `orchestration/init.py` | 73 | `workspace/.openclaw/snapshots` | Use `get_snapshot_dir(project_id)` |
| `orchestration/init.py` | 112 | `workspace/.openclaw` | Use `get_state_path(project_id).parent` |
| `orchestration/snapshot.py` | 170, 180 | `'main...HEAD'` | Use `_detect_default_branch(workspace)` |
| `orchestration/snapshot.py` | 263, 272 | `f'main...{branch_name}'` | Use `_detect_default_branch(workspace)` |
| `orchestration/snapshot.py` | 309 | `'checkout', 'main'` | Use `_detect_default_branch(workspace)` |
| `orchestration/snapshot.py` | 319 | `'Merge L3 task ... into main'` | Dynamic branch name in message |
| `orchestration/snapshot.py` | 393 | `'checkout', 'main'` | Use `_detect_default_branch(workspace)` |
| `orchestration/snapshot.py` | 209 | `workspace / '.openclaw' / 'snapshots'` | Use `get_snapshot_dir()` |
| `orchestration/snapshot.py` | 443 | `workspace / '.openclaw' / 'snapshots'` | Use `get_snapshot_dir()` |
| `skills/spawn_specialist/spawn.py` | 177 | `project_root / "workspace" / ".openclaw" / "workspace-state.json"` | Use `get_state_path()` |
| `skills/spawn_specialist/pool.py` | 50 | `project_root / "workspace" / ".openclaw" / "workspace-state.json"` | Use `get_state_path()` |
| `docker/l3-specialist/entrypoint.sh` | 11 | `"/workspace/.openclaw/workspace-state.json"` | Use env var injected by spawner |

### Current State of workspace-state.json (Live Data)
```json
{
  "version": 1,
  "tasks": {
    "phase6-hie03-test": { "status": "pending", ... },
    "phase6-hie04-test": { "status": "pending", ... },
    "phase6-com03-test": { "status": "in_progress", ... }
  }
}
```
**Migration implication:** `phase6-com03-test` has status `in_progress`. The migration guard WILL block until this task resolves. The user must either wait for it to complete/fail, or manually update its status before migration. This is real data that matters.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global constants in `config.py` | Per-project path resolution in `project_config.py` | Phase 11 | Enables multi-project operation; Phase 13 pool isolation depends on this |
| Hardcoded `"main"` in snapshot diffs | Dynamic branch detection | Phase 11 | Projects using `master` or custom default branches will generate valid diffs |
| Agent config path hardcoded in spawn.py | Resolved from project manifest `agents.l3_executor` | Phase 11 | Downstream projects can use any agent ID without forking spawn.py |

---

## Open Questions

1. **Last-resort branch fallback when detection fails completely**
   - What we know: The CONTEXT.md marks this as Claude's discretion
   - What's unclear: Should the fallback be `"main"`, or should it raise an error? A hard failure ensures no silent wrong-branch diffs. A fallback to `"main"` is more resilient but may silently produce wrong diffs for repos without a `main` branch.
   - Recommendation: Return `"main"` as the last-resort fallback (current behavior preserved from `create_staging_branch`). Log a warning so operators know detection fell back. This is consistent with current behavior and avoids breaking existing PumplAI operation. The warning makes it visible without being fatal.

2. **`config.py` STATE_FILE and SNAPSHOT_DIR constants after migration**
   - What we know: `monitor.py` uses `STATE_FILE` as the default CLI argument. After Phase 11, the default should come from `get_state_path()`.
   - What's unclear: Should these constants be removed from `config.py` or retained for backward compatibility?
   - Recommendation: Keep the constants in `config.py` but deprecate them by adding a comment. Remove them in Phase 13 when all consumers have been migrated. `monitor.py` default `--state-file` should compute from `get_state_path()` instead of importing `STATE_FILE`.

3. **`phase6-com03-test` in-progress task in current state file**
   - What we know: The actual live state file has one task with `"in_progress"` status. Migration will block on this.
   - What's unclear: Is this a stale artifact from earlier testing, or an actually running container?
   - Recommendation: The migration script should print the blocking task details clearly. The operator decides whether to wait or manually update the status. The migration script should NOT auto-resolve stale tasks.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of `~/.openclaw/orchestration/` — all Python modules read in full
- Direct inspection of `~/.openclaw/skills/spawn_specialist/spawn.py` and `pool.py`
- Direct inspection of `~/.openclaw/docker/l3-specialist/entrypoint.sh`
- Direct inspection of `~/.openclaw/workspace/.openclaw/workspace-state.json` — live state data
- Direct inspection of `~/.openclaw/projects/pumplai/project.json`
- Direct inspection of `~/.openclaw/openclaw.json`

### Secondary (MEDIUM confidence)
- None required — all findings are from direct code inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; pure Python stdlib
- Architecture: HIGH — all call sites found by grep; all patterns derived from existing code style
- Pitfalls: HIGH — identified from direct code inspection of all affected files
- Migration data: HIGH — live state file read directly

**Research date:** 2026-02-23
**Valid until:** This research is tied to the codebase state at research time. Valid until any of the inspected files change. No time-based expiry needed (no external dependencies).
