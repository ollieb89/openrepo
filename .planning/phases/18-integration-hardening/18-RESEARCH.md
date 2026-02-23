# Phase 18: Integration Hardening - Research

**Researched:** 2026-02-23
**Domain:** Python package exports, bash environment variable propagation, Python module initialization hooks, JSON data correction
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Soul auto-generation trigger:**
- Auto-generate SOUL.md during `initialize_workspace()` for new projects
- Also expose a CLI command (`openclaw soul generate <project>`) for manual regeneration
- `initialize_workspace()` skips if SOUL.md already exists — never overwrites
- CLI regenerate command requires `--force` flag to overwrite existing SOUL.md; default behavior is skip with warning

**Package export surface:**
- Define full `__all__` in `orchestration/__init__.py` — not just the 3 missing symbols, but the complete public API
- `__all__` includes strictly public symbols only — symbols intended for external consumers (L3 containers, CLI, dashboard)
- Internal cross-module imports must use direct submodule imports (e.g. `from orchestration.config import X`), not the package root
- Add a brief docstring to `__init__.py` documenting what the orchestration package provides

### Claude's Discretion

- Logging verbosity for write_soul() (generated/skipped/error messages)
- Exact wording of CLI --force warning messages
- Branch detection implementation details (entrypoint.sh changes)
- geriai project.json fix approach (straightforward data correction)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-03 | `project_config.py` exposes `get_state_path(project_id)` and `get_snapshot_dir(project_id)` | Both functions exist in `project_config.py`; `ProjectNotFoundError` also exists there. All three are absent from `__init__.py __all__`. Simple import + `__all__` extension. |
| CFG-04 | SOUL.md default template with `$project_name` and `$tech_stack_*` substitution points | `soul_renderer.py` `write_soul()` exists and works. `initialize_workspace()` in `init.py` does not call it. Wire call site with skip-if-exists guard. |
| CFG-05 | Projects can override SOUL.md with a custom file in `projects/<id>/SOUL.md` | Override mechanism is correct in `soul_renderer.py` (reads `projects/<id>/soul-override.md`). The gap is the runtime trigger, same as CFG-04. |
| CFG-06 | `snapshot.py` detects default branch dynamically instead of hardcoding `"main"` | `_detect_default_branch()` exists and works on the L2 side. Gap is that `entrypoint.sh:39` still hardcodes `main` as the base for `git checkout -b`. Fix: pass `DEFAULT_BRANCH` env var from `spawn_l3_specialist()`, consume it in the entrypoint. |
| MPR-03 | `pool.py` resolves state file path per-project via `get_state_path()` | The code path is correct. The gap is that `geriai/project.json` has `"id": "pumplai"` (copy-paste error), which means `get_state_path("geriai")` would produce a path keyed on the wrong project. Correct the JSON data. |

</phase_requirements>

## Summary

Phase 18 addresses exactly 4 wiring defects found in the v1.1 milestone audit. All 4 are mechanical fixes to already-correct implementations — no new logic needs to be designed. The audit confirmed that the core implementations (branch detection, SOUL renderer, state path resolution) work correctly; what is missing is either an env-var thread that did not reach the container boundary, a missing function in `__all__`, a missing call site, or a bad JSON value.

The fixes decompose into two categories: (1) **data flow gaps** — entrypoint branch detection and soul_renderer trigger, both requiring additions to existing functions; and (2) **declaration gaps** — `__init__.py` exports and geriai JSON, both requiring edits to existing files with no behavioral change. Because all underlying logic is correct and already tested, the risk profile is low. The highest-risk fix is the soul auto-generation trigger in `initialize_workspace()` because it adds a side effect to a function that currently only creates directories; the skip-if-exists guard is the key correctness mechanism.

The CLI command `openclaw soul generate <project>` is a new addition with no prior scaffolding. It should follow the existing `monitor.py` / `spawn.py` argparse pattern — standalone script with `if __name__ == '__main__'` and `argparse.ArgumentParser`.

**Primary recommendation:** Execute the 4 fixes as 4 independent tasks. None depends on the others. Tasks can be planned in parallel waves.

## Standard Stack

### Core

| Component | Version/Location | Purpose | Why Standard |
|-----------|-----------------|---------|--------------|
| Python `string.Template.safe_substitute` | stdlib | Variable substitution in SOUL templates | Already in use; project decision (avoids Jinja2 dependency) |
| `argparse` | stdlib | CLI argument parsing | Existing pattern in monitor.py, spawn.py |
| `fcntl.flock` | stdlib | Cross-container state file locking | Existing Jarvis Protocol pattern |
| bash `${VAR:-default}` | bash 3+ | Default env var expansion in entrypoint | POSIX compatible, minimal change to existing script |

### No New Dependencies

This phase introduces zero new Python packages or shell tools. All fixes use stdlib or in-repo patterns.

## Architecture Patterns

### Pattern 1: Env Var Threading Through Container Boundary

**What:** The L2 Python spawner builds an `environment` dict that is passed as Docker container env vars. The entrypoint.sh reads those vars.

**Current state (broken):**
```python
# spawn.py: environment dict (line ~170)
"environment": {
    "TASK_ID": task_id,
    "SKILL_HINT": skill_hint,
    "STAGING_BRANCH": staging_branch,
    "CLI_RUNTIME": cli_runtime,
    "TASK_DESCRIPTION": task_description,
    "OPENCLAW_PROJECT": project_id,
    "OPENCLAW_STATE_FILE": f"/workspace/.openclaw/{project_id}/workspace-state.json",
},
```

```bash
# entrypoint.sh line 39 (hardcoded):
git checkout -b "${STAGING_BRANCH}" main 2>/dev/null || git checkout -b "${STAGING_BRANCH}"
```

**Required fix — two coordinated changes:**

In `spawn.py`, add `DEFAULT_BRANCH` to the environment dict. The value comes from `_detect_default_branch()` in `snapshot.py`. The spawner already imports from `orchestration.snapshot` (via `orchestration/__init__.py`) so the function is accessible.

```python
# In spawn.py, inside spawn_l3_specialist():
# After computing staging_branch, before container_config:
from orchestration.snapshot import _detect_default_branch
workspace = Path(workspace_path)
default_branch = _detect_default_branch(workspace, project_id)

# Then add to environment dict:
"DEFAULT_BRANCH": default_branch,
```

In `entrypoint.sh`, change line 39:
```bash
# Before:
git checkout -b "${STAGING_BRANCH}" main 2>/dev/null || git checkout -b "${STAGING_BRANCH}"

# After:
git checkout -b "${STAGING_BRANCH}" "${DEFAULT_BRANCH:-main}" 2>/dev/null || git checkout -b "${STAGING_BRANCH}"
```

Note: `_detect_default_branch` is a private function (leading underscore). The CONTEXT.md marks branch detection implementation as Claude's Discretion. Two options:
1. Import the private function directly (simple, no API change needed)
2. Make it public by removing the underscore prefix (better long-term, but changes API)

Given this is "strictly wiring fixes" scope, importing the private function directly is lower risk. The function is in the same package.

### Pattern 2: Initialize-Once with Skip-If-Exists Guard

**What:** `initialize_workspace()` is an idempotent setup function. Adding soul generation must preserve that idempotency.

**Current structure of `initialize_workspace()` (init.py):**
```python
def initialize_workspace(project_root=None) -> Dict[str, Any]:
    # 1. resolve project_root
    # 2. get snapshots_dir = get_snapshot_dir()   ← uses active project
    # 3. mkdir state dir
    # 4. mkdir snapshots dir
    # 5. return result dict
```

**Gap:** `get_snapshot_dir()` and `get_state_path()` called without `project_id` — they resolve from `OPENCLAW_PROJECT` env var or `active_project` in openclaw.json. `write_soul()` will need the same `project_id`.

**Required additions:**
1. Add `project_id: Optional[str] = None` parameter to `initialize_workspace()` (or derive it internally from `get_active_project_id()`)
2. After creating directories, call `write_soul(project_id)` with skip-if-exists logic
3. The skip-if-exists check: determine the output path that `write_soul()` would use, check if it exists, skip if so

**Skip logic — two implementation options:**
- Option A: Pre-compute output path before calling `write_soul()`, check existence, skip
- Option B: Add `skip_if_exists: bool = True` parameter to `write_soul()` itself

Option B is cleaner since `write_soul()` already derives the output path internally. The CONTEXT.md states "`initialize_workspace()` skips if SOUL.md already exists", so the skip behavior lives in the `initialize_workspace()` call, but whether it's implemented inside `write_soul()` or as a pre-check in `initialize_workspace()` is Claude's Discretion.

**Recommended implementation for `write_soul()` (adds optional skip behavior):**
```python
def write_soul(project_id: str, output_path: Optional[Path] = None, skip_if_exists: bool = False) -> Optional[Path]:
    config = load_project_config(project_id)
    if output_path is None:
        agents = config.get("agents", {})
        l2_pm_id = agents.get("l2_pm", project_id)
        output_path = _find_project_root() / "agents" / l2_pm_id / "agent" / "SOUL.md"

    if skip_if_exists and output_path.exists():
        print(f"[soul] SOUL.md already exists, skipping: {output_path}")
        return None  # or return output_path — both are valid

    content = render_soul(project_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    return output_path
```

**Call in `initialize_workspace()`:**
```python
try:
    from .soul_renderer import write_soul
    written = write_soul(project_id, skip_if_exists=True)
    if written:
        print(f"[init] Generated SOUL.md: {written}")
    else:
        print(f"[init] SOUL.md already exists, skipped")
except Exception as e:
    print(f"[init] WARNING: SOUL.md generation failed: {e}")
    # Non-fatal — workspace directories are already created
```

The try/except is important: `write_soul()` can fail (e.g., missing template, project not found) and must not break directory creation which already succeeded.

### Pattern 3: `__all__` Extension

**What:** `orchestration/__init__.py` currently exports symbols from `state_engine`, `config`, `init`, `project_config`, and `snapshot`. The 3 missing symbols are in `project_config` but not in either the import block or `__all__`.

**Current import block (project_config section):**
```python
from .project_config import (
    load_project_config,
    get_workspace_path,
    get_tech_stack,
    get_agent_mapping,
    get_active_project_id,
)
```

`get_state_path`, `get_snapshot_dir`, and `ProjectNotFoundError` are present in `project_config.py` but not imported in `__init__.py`.

**Required change — two coordinated edits:**

1. Extend the import:
```python
from .project_config import (
    load_project_config,
    get_workspace_path,
    get_tech_stack,
    get_agent_mapping,
    get_active_project_id,
    get_state_path,
    get_snapshot_dir,
    ProjectNotFoundError,
)
```

2. Add to `__all__`:
```python
'get_state_path', 'get_snapshot_dir', 'ProjectNotFoundError',
```

The CONTEXT.md decision requires the **complete public API** in `__all__`, not just the 3 missing symbols. Review current exports against what is genuinely public-facing. Also add `soul_renderer` exports per the audit's tech_debt note: "soul_renderer not re-exported from orchestration/__init__.py".

The docstring addition is also required per the locked decision. A concise module docstring:
```python
"""
OpenClaw Orchestration Package

Public API for the Jarvis Protocol state engine, project configuration,
git snapshot workflow, SOUL renderer, and workspace initialization.

External consumers (L3 containers, CLI tools, dashboard) should import
from this package root. Internal cross-module code should use direct
submodule imports (e.g., `from orchestration.config import X`).
"""
```

### Pattern 4: JSON Data Correction

**What:** `projects/geriai/project.json` was copied from `projects/pumplai/project.json` and the `id` field (and other pumplai-specific values) were never updated.

**Current (broken):**
```json
{
  "id": "pumplai",
  "name": "PumplAI",
  "agent_display_name": "PumplAI_PM",
  "workspace": "/home/ollie/Development/Projects/pumplai",
  ...
}
```

**Required:** Geriai-specific values for every field. The CONTEXT.md marks the approach as Claude's Discretion ("straightforward data correction"). Since there is no documented source of truth for geriai's actual configuration, a reasonable set of values based on the existing pumplai template structure:

```json
{
  "id": "geriai",
  "name": "GerIAI",
  "agent_display_name": "GerIAI_PM",
  "workspace": "/home/ollie/Development/Projects/geriai",
  "tech_stack": {
    "frontend": "",
    "backend": "",
    "infra": ""
  },
  "agents": {
    "l2_pm": "geriai_pm",
    "l3_executor": "l3_specialist"
  },
  "l3_overrides": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"]
  }
}
```

The critical correctness requirement is `"id": "geriai"` — this is what `get_state_path("geriai")` validates against. The workspace and agent values should be plausible geriai-specific values. If actual values are unknown, use geriai-appropriate placeholder paths.

### Pattern 5: CLI Command for Manual Soul Regeneration

**What:** The CONTEXT.md locks in an `openclaw soul generate <project>` CLI command. This is a new addition. The existing CLI entry points follow the `if __name__ == '__main__'` + `argparse` pattern (see `monitor.py`, `spawn.py`).

**Implementation approach:** Add to `soul_renderer.py`'s existing `__main__` block, or create a dedicated `openclaw` CLI dispatcher. The current `soul_renderer.py` already has a `__main__` block with `--project` and `--write` flags. The simplest approach is to extend the existing `soul_renderer.py` CLI to recognize the `generate` subcommand style, or to document that `openclaw soul generate <project>` maps to `python3 orchestration/soul_renderer.py --project <project> --write`.

Since there is no top-level `openclaw` CLI dispatcher yet (Phase 14 would add it), the most practical approach for this phase is to verify `soul_renderer.py`'s existing `--write` mode works as the manual trigger, and document the command alias. A thin wrapper script `scripts/openclaw-soul-generate.sh` could proxy to the renderer if a more polished CLI UX is desired — but that depends on project preferences.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Default branch detection | Custom git parsing logic | Existing `_detect_default_branch()` in `snapshot.py` |
| Template variable substitution | Custom string replacement | Existing `string.Template.safe_substitute()` already in use |
| File existence check before write | Custom locking | Simple `output_path.exists()` check — no concurrent access expected at init time |

## Common Pitfalls

### Pitfall 1: Circular Import When Calling write_soul from init.py

**What goes wrong:** `init.py` imports from `project_config`. `soul_renderer.py` also imports from `project_config`. If `init.py` imports `soul_renderer` at module level, and `soul_renderer` imports something that triggers `init.py` to reload, you get a circular import error.

**Why it happens:** Python's import system caches modules, but circular imports within a package can cause `AttributeError: partially initialized module` if the import graph has a cycle.

**How to avoid:** Use a local (deferred) import inside `initialize_workspace()` function body, not at module level:
```python
def initialize_workspace(...):
    # ... directory creation ...
    try:
        from .soul_renderer import write_soul  # local import — avoids circular import risk
        ...
    except ImportError as e:
        print(f"WARNING: soul_renderer not available: {e}")
```

**Warning signs:** `ImportError: cannot import name 'write_soul' from partially initialized module 'orchestration.init'`

### Pitfall 2: `_detect_default_branch` Requires a Workspace Path

**What goes wrong:** Calling `_detect_default_branch(workspace, project_id)` from `spawn_l3_specialist()` requires a `Path` object for the workspace. The `workspace_path` parameter in `spawn_l3_specialist()` is a `str`. Forgetting the `Path()` cast causes `subprocess.run` to silently fail.

**How to avoid:**
```python
workspace = Path(workspace_path)
default_branch = _detect_default_branch(workspace, project_id)
```

**Warning signs:** Branch detection falls through to "main" fallback even when the repo has a non-main default branch.

### Pitfall 3: `__all__` Without Corresponding Import

**What goes wrong:** Adding a symbol to `__all__` without adding the corresponding `from .module import symbol` line causes `AttributeError` when `from orchestration import *` is used, and `ImportError` when `from orchestration import ProjectNotFoundError` is used.

**How to avoid:** Always update both the `from .module import (...)` block AND the `__all__` list together.

### Pitfall 4: geriai Workspace Path Must Be a Valid Directory for Pool Operations

**What goes wrong:** `get_state_path("geriai")` validates that `projects/geriai/project.json` exists but does NOT validate that the `workspace` field points to a real directory. Pool operations that call `get_workspace_path("geriai")` will return whatever is in the JSON, even if that directory doesn't exist on the host.

**How to avoid:** The JSON correction should use a path that either exists or is clearly marked as a placeholder. Adding a `"_note": "test project"` field (non-standard but harmless) signals intent. Alternatively, use `/tmp/geriai-workspace` as the workspace value for a test project.

### Pitfall 5: write_soul() Skip Logic Return Value Ambiguity

**What goes wrong:** If `write_soul()` returns `None` when skipping, callers that assume a `Path` return value will get `None` and may crash on subsequent `.name` access.

**How to avoid:** Return type annotation should be `Optional[Path]` and call sites must handle `None`. The `initialize_workspace()` return dict should not include the SOUL path if skipped — just include a `soul_written: bool` key.

## Code Examples

### Fix 1: entrypoint.sh branch detection

```bash
# Required env var declaration (add near top of entrypoint.sh)
: "${DEFAULT_BRANCH:=main}"

# Line 39 replacement:
git checkout -b "${STAGING_BRANCH}" "${DEFAULT_BRANCH}" 2>/dev/null || git checkout -b "${STAGING_BRANCH}"
```

Note: Using `:=` (assign default if unset) rather than `:-` (substitute default) means the variable is set to "main" if not provided, which is cleaner for subsequent use.

### Fix 1 (spawn.py side):

```python
# Add after computing staging_branch, before building container_config:
from orchestration.snapshot import _detect_default_branch as _detect_branch
_default_branch = _detect_branch(Path(workspace_path), project_id)

# In environment dict:
"DEFAULT_BRANCH": _default_branch,
```

### Fix 2: __init__.py complete export surface

```python
"""
OpenClaw Orchestration Package

Public API for the Jarvis Protocol state engine, project configuration,
git snapshot workflow, SOUL renderer, and workspace initialization.

External consumers (L3 containers, CLI tools, dashboard) should import
from this package root. Internal cross-module code should use direct
submodule imports (e.g., `from orchestration.config import X`).
"""

from .state_engine import JarvisState
from .config import LOCK_TIMEOUT, POLL_INTERVAL
from .init import initialize_workspace, verify_workspace
from .project_config import (
    load_project_config,
    get_workspace_path,
    get_tech_stack,
    get_agent_mapping,
    get_active_project_id,
    get_state_path,
    get_snapshot_dir,
    ProjectNotFoundError,
)
from .snapshot import (
    create_staging_branch,
    capture_semantic_snapshot,
    l2_review_diff,
    l2_merge_staging,
    l2_reject_staging,
    cleanup_old_snapshots,
    GitOperationError,
)
from .soul_renderer import render_soul, write_soul

__all__ = [
    # State engine
    'JarvisState',
    # Config constants
    'LOCK_TIMEOUT', 'POLL_INTERVAL',
    # Workspace lifecycle
    'initialize_workspace', 'verify_workspace',
    # Project configuration
    'load_project_config', 'get_workspace_path', 'get_tech_stack',
    'get_agent_mapping', 'get_active_project_id',
    'get_state_path', 'get_snapshot_dir', 'ProjectNotFoundError',
    # Git snapshot workflow
    'create_staging_branch', 'capture_semantic_snapshot',
    'l2_review_diff', 'l2_merge_staging', 'l2_reject_staging',
    'cleanup_old_snapshots', 'GitOperationError',
    # SOUL renderer
    'render_soul', 'write_soul',
]
```

### Fix 3: initialize_workspace() with soul trigger

```python
def initialize_workspace(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Initialize workspace by creating required directories idempotently.
    Also generates SOUL.md for the active project if it does not yet exist.
    ...
    """
    if project_root is None:
        project_root = find_project_root()

    # Resolve project_id for soul generation
    try:
        from .project_config import get_active_project_id
        project_id = get_active_project_id()
    except (ImportError, ValueError):
        project_id = None

    snapshots_dir = get_snapshot_dir()
    get_state_path().parent.mkdir(parents=True, exist_ok=True)

    already_existed = snapshots_dir.exists()
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    created = not already_existed

    if created:
        print(f"{Colors.GREEN}✓{Colors.RESET} Created snapshots directory: {snapshots_dir}")
    else:
        print(f"{Colors.BLUE}ℹ{Colors.RESET} Snapshots directory already exists: {snapshots_dir}")

    # Generate SOUL.md for project if not yet written (skip-if-exists, non-fatal)
    soul_written = False
    if project_id is not None:
        try:
            from .soul_renderer import write_soul
            soul_path = write_soul(project_id, skip_if_exists=True)
            if soul_path is not None:
                print(f"{Colors.GREEN}✓{Colors.RESET} Generated SOUL.md: {soul_path}")
                soul_written = True
            else:
                print(f"{Colors.BLUE}ℹ{Colors.RESET} SOUL.md already exists, skipped")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} SOUL.md generation failed (non-fatal): {e}")

    return {
        'snapshots_dir': str(snapshots_dir),
        'created': created,
        'already_existed': already_existed,
        'soul_written': soul_written,
    }
```

### Fix 4: geriai/project.json

```json
{
  "id": "geriai",
  "name": "GerIAI",
  "agent_display_name": "GerIAI_PM",
  "workspace": "/home/ollie/Development/Projects/geriai",
  "tech_stack": {
    "frontend": "",
    "backend": "",
    "infra": ""
  },
  "agents": {
    "l2_pm": "geriai_pm",
    "l3_executor": "l3_specialist"
  },
  "l3_overrides": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"]
  }
}
```

## Open Questions

1. **What are geriai's actual tech stack values?**
   - What we know: The `geriai/` directory exists as a test project. The project.json is a copy-paste of pumplai.
   - What's unclear: Whether geriai is a real project or a test fixture. If real, actual stack values are unknown.
   - Recommendation: Use empty strings for tech_stack fields (or omit the key). If geriai is only a test fixture, placeholder values are fine. The critical correctness requirement is `"id": "geriai"`.

2. **Should `_detect_default_branch` be promoted to public API?**
   - What we know: It is a private function (`_` prefix) currently used only within `snapshot.py`. The CONTEXT.md marks branch detection implementation as Claude's Discretion.
   - What's unclear: Whether spawner calling a private function is acceptable long-term, or whether the function should be surfaced in `__all__`.
   - Recommendation: Import it directly from the submodule in `spawn.py` (`from orchestration.snapshot import _detect_default_branch`). Add to `__all__` as `detect_default_branch` (public alias) is a Phase 18 discretion call.

3. **Does `openclaw soul generate` need a top-level dispatcher or is `soul_renderer.py --write` sufficient?**
   - What we know: Phase 14 will add a project CLI. No `openclaw` dispatcher exists yet.
   - What's unclear: User expectation for the CLI UX at Phase 18.
   - Recommendation: Wire `soul_renderer.py`'s existing `--write` mode as the manual trigger. Document it clearly. A thin alias script can be added if UX matters before Phase 14.

## Task Decomposition for Planner

The 4 gaps are independent and can be executed in any order. Suggested grouping:

**Wave 1 (all independent, can run in parallel if multiple agents):**
- Task A: Fix `entrypoint.sh` + add `DEFAULT_BRANCH` to `spawn.py` environment dict
- Task B: Add `get_state_path`, `get_snapshot_dir`, `ProjectNotFoundError`, and `soul_renderer` exports to `orchestration/__init__.py` + add module docstring
- Task C: Add `skip_if_exists` parameter to `write_soul()`, call `write_soul()` from `initialize_workspace()`, update `initialize_workspace()` return dict
- Task D: Correct `projects/geriai/project.json` with geriai-specific values

All 4 tasks touch different files with no shared write targets.

## Sources

### Primary (HIGH confidence)

- Direct source inspection: `/home/ollie/.openclaw/docker/l3-specialist/entrypoint.sh` — confirmed hardcoded `main` on line 39
- Direct source inspection: `/home/ollie/.openclaw/orchestration/__init__.py` — confirmed `get_state_path`, `get_snapshot_dir`, `ProjectNotFoundError` absent from imports and `__all__`
- Direct source inspection: `/home/ollie/.openclaw/orchestration/init.py` — confirmed `initialize_workspace()` does not call `write_soul()`
- Direct source inspection: `/home/ollie/.openclaw/projects/geriai/project.json` — confirmed `"id": "pumplai"` (copy-paste error)
- Direct source inspection: `/home/ollie/.openclaw/orchestration/soul_renderer.py` — confirmed `write_soul()` API, output path derivation logic
- Direct source inspection: `/home/ollie/.openclaw/orchestration/snapshot.py` — confirmed `_detect_default_branch()` signature and resolution order
- Direct source inspection: `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` — confirmed `environment` dict structure, confirmed `DEFAULT_BRANCH` is absent
- Audit document: `/home/ollie/.openclaw/.planning/v1.1-MILESTONE-AUDIT.md` — primary source for gap identification and fix specifications

### No External Research Required

This phase is entirely internal wiring of an existing codebase. All implementation patterns are derivable from source inspection. No library documentation, no external APIs, no new technology. Confidence is HIGH because all claims are directly verified against source files in the repository.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns from existing code
- Architecture: HIGH — all patterns derived from direct source inspection
- Pitfalls: HIGH — identified from code structure, not speculation

**Research date:** 2026-02-23
**Valid until:** Indefinite — internal codebase research, not dependent on external library versions
