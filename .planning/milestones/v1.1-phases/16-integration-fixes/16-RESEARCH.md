# Phase 16: Phase 11/12 Integration Fixes - Research

**Researched:** 2026-02-23
**Domain:** Python orchestration layer wiring — snapshot threading, soul template variables, git branch detection, deprecated constant cleanup
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fix scope:**
- Fix the 3 identified bugs plus clean up immediate neighbors in the same functions
- For CFG-02 (snapshot project_id): Thread project_id explicitly through function signatures of `capture_semantic_snapshot()` and `cleanup_old_snapshots()` — not just `get_snapshot_dir()`
- For CFG-04 (soul template): Add $project_name to soul-default.md template body AND audit all variables declared in `build_variables()` to ensure every one is consumed by the template
- For CFG-06 (staging branch): Replace duplicate inline branch detection in `create_staging_branch()` with a call to existing `_detect_default_branch()` helper. Do NOT enhance the helper — just use it
- Update ALL callers of changed functions in this phase (entrypoint.sh, spawn.py, etc.) — don't leave broken call sites for Phase 17 to catch

**Backward compatibility:**
- Break cleanly — project_id is a required parameter everywhere, no optional fallback to ambient config
- Any caller without project_id fails immediately with a clear error
- This is internal code with known call sites, so breaking is safe and prevents silent bugs
- Consistent policy across all affected functions: get_snapshot_dir(), capture_semantic_snapshot(), cleanup_old_snapshots()

**Deprecated constant removal:**
- Delete STATE_FILE and SNAPSHOT_DIR constants from config.py entirely — no stubs, no error messages, just gone
- Remove the unused STATE_FILE import from monitor.py
- Audit ALL orchestration/*.py files for unused imports and clean them up while we're in there
- Audit soul_renderer.py build_variables() for any other unused/dead code beyond the $project_name fix

**Validation approach:**
- Write a verification script at `scripts/verify_phase16.py` covering all 3 fixes
- Script checks: snapshot path threading, staging branch detection delegation, and template variable consumption
- CI-friendly: exit 0 on all pass, exit 1 on any failure, print results to stdout
- Follows existing pattern (scripts/verify_soul_golden.py already exists)

### Claude's Discretion
- Exact error messages when project_id is missing
- How to structure the verification script internally (class vs functions)
- Whether to use subprocess or direct import for template rendering verification

### Deferred Ideas (OUT OF SCOPE)
- Enhancing `_detect_default_branch()` to also check project.json default_branch field — could be a future improvement but out of scope for this fix phase
- Full automated test suite for orchestration layer — separate initiative
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-02 | Per-project snapshot directory at `workspace/.openclaw/<project_id>/snapshots/` | `get_snapshot_dir(project_id)` exists in project_config.py and is correct; `capture_semantic_snapshot()` and `cleanup_old_snapshots()` simply need `project_id` threaded through their signatures and passed to it |
| CFG-04 | SOUL.md default template with `$project_name` and `$tech_stack_*` substitution points | `build_variables()` already declares `project_name`; soul-default.md body uses `$workspace`, `$tech_stack_*` variables but is missing `$project_name` consumption — template file needs to reference it |
| CFG-06 | `snapshot.py` detects default branch dynamically instead of hardcoding `"main"` | `_detect_default_branch()` already exists in snapshot.py with full 5-step detection; `create_staging_branch()` has a duplicate 40-line inline detection block that ignores project.json — needs to be replaced with a single call to the helper |
</phase_requirements>

---

## Summary

Phase 16 is a surgical wiring fix phase with no new capabilities. All three problems were introduced by incomplete cross-module integration during Phases 11 and 12: functions in `snapshot.py` were built that call `get_snapshot_dir()` without threading `project_id` (CFG-02), `create_staging_branch()` duplicated branch detection logic rather than delegating to the existing helper (CFG-06), and the soul template body never consumed the `$project_name` variable that `build_variables()` already emits (CFG-04). Each fix is mechanically simple — the correct implementations already exist, they just aren't wired up.

The deprecated `STATE_FILE` and `SNAPSHOT_DIR` constants in `config.py` are a cleanup problem: they were marked for removal in Phase 11 (the deprecation comment says "Will be removed in Phase 13") but survived. `monitor.py` imports `STATE_FILE` from them though that import is never used at runtime. The constant removal and import cleanup are straightforward deletions with no behavioral impact.

The verification script at `scripts/verify_phase16.py` will follow the structure of the existing `scripts/verify_soul_golden.py` — a pure Python script with individual `verify_*()` functions that print PASS/FAIL per check and return a boolean, assembled by a `main()` that exits 0 on all pass, 1 on any failure.

**Primary recommendation:** Fix the three wiring bugs as pure function-signature changes with no logic rewrite, delete the deprecated constants, and use direct import (not subprocess) in the verification script for deterministic output.

---

## Standard Stack

### Core

| Module | Location | Purpose | Why Used |
|--------|----------|---------|----------|
| `snapshot.py` | `orchestration/snapshot.py` | Git staging branch workflow, snapshot capture | Already implements all operations; only signatures need updating |
| `soul_renderer.py` | `orchestration/soul_renderer.py` | SOUL.md template rendering via `string.Template` | Phase 12 implementation; `build_variables()` is the variable source |
| `project_config.py` | `orchestration/project_config.py` | `get_snapshot_dir(project_id)` canonical resolver | Correct implementation exists; just not called with explicit project_id |
| `config.py` | `orchestration/config.py` | Lock/poll constants; holds deprecated STATE_FILE/SNAPSHOT_DIR | Only `LOCK_TIMEOUT`, `LOCK_RETRY_ATTEMPTS`, `POLL_INTERVAL` remain after cleanup |
| `monitor.py` | `orchestration/monitor.py` | CLI monitoring tool | Imports deprecated `STATE_FILE` — remove import, `POLL_INTERVAL` stays |

### Supporting

| Module | Location | Purpose | When to Use |
|--------|----------|---------|-------------|
| `string.Template.safe_substitute()` | Python stdlib | Template variable substitution | Phase 12 decision — already in use; `safe_substitute` leaves unresolved `$var` intact rather than raising |
| `scripts/verify_soul_golden.py` | `scripts/verify_soul_golden.py` | Verification script pattern | Template for `verify_phase16.py` — same structure, same PASS/FAIL pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct import in verify script | subprocess call | Direct import is faster, more reliable, and gives structured return values; subprocess would require parsing stdout |
| Breaking callers cleanly | Optional fallback to ambient config | Locked decision: break cleanly — optional fallback masks bugs |

---

## Architecture Patterns

### Recommended Project Structure (no new files except verify script)

```
orchestration/
├── config.py              # Remove STATE_FILE, SNAPSHOT_DIR — keep LOCK_TIMEOUT, POLL_INTERVAL
├── monitor.py             # Remove `STATE_FILE` from import; audit all unused imports
├── snapshot.py            # Thread project_id through capture_semantic_snapshot(), cleanup_old_snapshots(); replace duplicate block in create_staging_branch()
├── soul_renderer.py       # No code changes; see template below
└── project_config.py      # No changes — get_snapshot_dir(project_id) is already correct

agents/_templates/
└── soul-default.md        # Add $project_name consumption to template body

scripts/
├── verify_soul_golden.py  # Existing — template/pattern reference
└── verify_phase16.py      # NEW: phase 16 verification script
```

### Pattern 1: Explicit project_id Threading (for CFG-02)

**What:** Add `project_id: str` as a required positional parameter to `capture_semantic_snapshot()` and `cleanup_old_snapshots()`, pass it through to `get_snapshot_dir(project_id)`.

**Current broken state in `snapshot.py`:**
```python
# capture_semantic_snapshot (line 196) — no project_id param
def capture_semantic_snapshot(task_id: str, workspace_path: str) -> Tuple[Path, Dict[str, Any]]:
    ...
    snapshots_dir = get_snapshot_dir()  # resolves via ambient config — BROKEN for multi-project

# cleanup_old_snapshots (line 485) — no project_id param
def cleanup_old_snapshots(workspace_path: str, max_snapshots: int = 100) -> Dict[str, Any]:
    ...
    snapshots_dir = get_snapshot_dir()  # same problem
```

**Fixed state — signature change + explicit pass-through:**
```python
def capture_semantic_snapshot(
    task_id: str,
    workspace_path: str,
    project_id: str,           # ADDED — required, no default
) -> Tuple[Path, Dict[str, Any]]:
    ...
    snapshots_dir = get_snapshot_dir(project_id)  # explicit threading

def cleanup_old_snapshots(
    workspace_path: str,
    project_id: str,           # ADDED — required, no default
    max_snapshots: int = 100,
) -> Dict[str, Any]:
    ...
    snapshots_dir = get_snapshot_dir(project_id)  # explicit threading
```

**Caller impact:** Search all callers — `entrypoint.sh` does not call these Python functions directly (it uses a helper that calls `update_state`). The Python-layer callers are currently internal to snapshot.py and any callers in tests or pool.py. Check `pool.py` and any other orchestration modules that call these functions.

### Pattern 2: Delegate to `_detect_default_branch()` (for CFG-06)

**What:** Replace the 40-line duplicate inline detection block in `create_staging_branch()` with a single call to the existing helper.

**Current broken state in `snapshot.py` (lines 129-154):**
```python
# Detect default branch (main or master)
default_branch = "main"
try:
    branch_result = subprocess.run(
        ['git', '-C', str(workspace), 'symbolic-ref', 'refs/remotes/origin/HEAD'],
        ...
    )
    if branch_result.returncode == 0 and branch_result.stdout.strip():
        default_branch = branch_result.stdout.strip().split('/')[-1]
    else:
        # Fallback: check if main exists, else use master
        main_check = subprocess.run(...)
        if main_check.returncode != 0:
            master_check = subprocess.run(...)
            if master_check.returncode == 0:
                default_branch = "master"
except Exception:
    pass  # Use default "main"
```

**Fixed state — replace entire block with one line:**
```python
default_branch = _detect_default_branch(workspace)
```

**Critical note:** `_detect_default_branch()` accepts an optional `project_id` parameter (step 1 of its resolution order checks `project.json default_branch`). The locked decision says "Do NOT enhance the helper" — but we can still pass `project_id` to it if we have it available in `create_staging_branch()`. The current signature of `create_staging_branch()` does not take `project_id`. The decision says to use the helper as-is, so the call becomes `_detect_default_branch(workspace)` with no project_id unless the caller already has one available. This is correct for now.

### Pattern 3: Template Variable Consumption (for CFG-04)

**What:** Add `$project_name` to the `soul-default.md` template body so the variable that `build_variables()` already emits is actually consumed.

**Current `build_variables()` output (all 8 variables):**
```python
return {
    "project_name": ...,       # DECLARED but never used in soul-default.md body
    "project_id": ...,         # used? check
    "agent_name": ...,         # used in title line: "# Soul: $agent_name ($tier)"
    "tier": ...,               # used in title line
    "tech_stack_frontend": ..., # used in CORE GOVERNANCE section
    "tech_stack_backend": ...,  # used in CORE GOVERNANCE section
    "tech_stack_infra": ...,    # used in CORE GOVERNANCE section
    "workspace": ...,           # used in HIERARCHY section
}
```

**Current soul-default.md body (full file — 18 lines):**
```
## HIERARCHY
- **Superior:** Reports to the L1 Strategic Orchestrator. All major project decisions must align with L1 strategic plans.
- **Subordinates:** Supervises L3 Worker containers.
- **Scope:** Primary authority over the `$workspace` workspace.

## CORE GOVERNANCE
1. **TACTICAL TRANSLATION:** Receive L1 goals and break them down into multi-step worker tasks.
2. **STRICT TECH STACK:**
   - **Frontend:** $tech_stack_frontend.
   - **Backend:** $tech_stack_backend.
   - **Infrastructure:** $tech_stack_infra.
3. **QUALITY GATE:** Review and verify all L3 output before reporting completion to L1.

## BEHAVIORAL PROTOCOLS
- **Resourceful Execution:** Use available tools to explore the workspace and validate implementations.
- **Contextual Integrity:** Ensure all changes are documented in the project's local memory or `MEMORY.md`.
- **Escalation:** If a task violates strategic vision or hits a major architectural blocker, escalate to L1.
```

**Variables verified consumed/not-consumed:**
- `$workspace` — consumed (HIERARCHY section) ✓
- `$tech_stack_frontend`, `$tech_stack_backend`, `$tech_stack_infra` — consumed (CORE GOVERNANCE) ✓
- `$agent_name`, `$tier` — consumed in title line (not in template body, but in `render_soul()` directly) ✓
- `$project_name` — NOT consumed anywhere in body or title ✗
- `$project_id` — NOT consumed anywhere ✗ (check if this is intentional)

**Decision says:** Add `$project_name` to the template body. Also audit all variables — the audit needs to determine whether `$project_id` is also expected to appear, or intentionally left as a silent variable (available for override files but not in the default).

**Where to add `$project_name`:** Planner's discretion, but the natural home is HIERARCHY (the scope line: "Primary authority over the `$workspace` workspace for project `$project_name`") or as a dedicated identity line, e.g. `- **Project:** $project_name`.

### Pattern 4: Deprecated Constant Removal

**What:** Delete `STATE_FILE` and `SNAPSHOT_DIR` from `config.py`; remove `STATE_FILE` from `monitor.py` import.

**Current `config.py` (full file — 24 lines):**
```python
import os
from pathlib import Path

# DEPRECATED: Use orchestration.project_config.get_state_path() instead.
STATE_FILE = Path(os.environ.get(
    'OPENCLAW_STATE_FILE',
    'workspace/.openclaw/workspace-state.json',
))

# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds

# DEPRECATED: Use orchestration.project_config.get_snapshot_dir() instead.
SNAPSHOT_DIR = Path(os.environ.get(
    'OPENCLAW_SNAPSHOT_DIR',
    'workspace/.openclaw/snapshots/',
))
```

**After deletion:** Only `LOCK_TIMEOUT`, `LOCK_RETRY_ATTEMPTS`, and `POLL_INTERVAL` remain. The `import os` and `from pathlib import Path` at the top will also no longer be needed — remove them.

**`monitor.py` import line to fix (lines 22-30):**
```python
# Current:
from .config import STATE_FILE, POLL_INTERVAL

# After:
from .config import POLL_INTERVAL
```
`POLL_INTERVAL` is actually used at line 567 (`default=POLL_INTERVAL`), so it stays. `STATE_FILE` is imported but never used at runtime (grep confirms no call site in the module body), so remove it.

### Pattern 5: Verification Script (follows verify_soul_golden.py)

**Structure to follow:**
```python
#!/usr/bin/env python3
"""Phase 16 verification: snapshot threading, staging branch detection, template variables."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_snapshot_project_id_threading() -> bool:
    """Verify capture_semantic_snapshot() and cleanup_old_snapshots() require explicit project_id."""
    import inspect
    from orchestration.snapshot import capture_semantic_snapshot, cleanup_old_snapshots

    # Check signatures: project_id must be a required parameter (no default)
    ...

def verify_staging_branch_delegates_to_detect() -> bool:
    """Verify create_staging_branch() calls _detect_default_branch() instead of inline detection."""
    import inspect
    from orchestration import snapshot as snap_module
    import ast

    # Read source, verify no duplicate subprocess.run for symbolic-ref inside create_staging_branch
    ...

def verify_template_variable_consumption() -> bool:
    """Verify $project_name appears in soul-default.md body and renders correctly."""
    import string
    from orchestration.soul_renderer import build_variables
    from orchestration.project_config import _find_project_root

    root = _find_project_root()
    template_path = root / "agents" / "_templates" / "soul-default.md"
    template_body = template_path.read_text()

    # All variables from build_variables() must appear in template or title
    ...

def verify_deprecated_constants_removed() -> bool:
    """Verify STATE_FILE and SNAPSHOT_DIR are gone from config.py."""
    from orchestration import config

    checks = [
        (not hasattr(config, 'STATE_FILE'), "STATE_FILE not in config"),
        (not hasattr(config, 'SNAPSHOT_DIR'), "SNAPSHOT_DIR not in config"),
    ]
    ...

def main() -> int:
    results = [
        ("snapshot project_id threading", verify_snapshot_project_id_threading()),
        ("staging branch detection delegation", verify_staging_branch_delegates_to_detect()),
        ("template variable consumption", verify_template_variable_consumption()),
        ("deprecated constants removed", verify_deprecated_constants_removed()),
    ]
    passed = all(ok for _, ok in results)
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
```

**Verification approach per check:**
- **Snapshot threading:** Use `inspect.signature()` to check that `project_id` is a required parameter with no default in both functions. Confidence: HIGH — deterministic.
- **Staging branch delegation:** Source-level check via `inspect.getsource(create_staging_branch)` — verify `_detect_default_branch` is called and `symbolic-ref` does not appear inline. Confidence: HIGH.
- **Template variable consumption:** Read soul-default.md, substitute with known variables, assert `$project_name` is not in output and a known value is present. Confidence: HIGH.
- **Deprecated constants:** `hasattr(config, 'STATE_FILE')` and `hasattr(config, 'SNAPSHOT_DIR')`. Confidence: HIGH.

### Anti-Patterns to Avoid

- **Adding optional `project_id=None` fallback:** The locked decision explicitly rejects this. Functions must require project_id or fail immediately.
- **Using subprocess in the verify script:** Direct import is cleaner and faster. `verify_soul_golden.py` uses direct import; follow that pattern.
- **Deleting `POLL_INTERVAL` from config.py:** Only the deprecated constants go. `LOCK_TIMEOUT`, `LOCK_RETRY_ATTEMPTS`, and `POLL_INTERVAL` are actively used.
- **Changing `_detect_default_branch()` logic:** Out of scope. Call it as-is.
- **Leaving any call site of `capture_semantic_snapshot()` or `cleanup_old_snapshots()` that does not pass `project_id`:** The fix is only complete when all callers are updated.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Branch detection logic | Another implementation | Existing `_detect_default_branch()` | Already handles 5 cases including project.json, symbolic-ref, local main/master, fallback |
| Snapshot path resolution | New path logic | `get_snapshot_dir(project_id)` in project_config.py | Already implements the per-project convention; just not called with explicit ID |
| Template engine | Custom string replacement | `string.Template.safe_substitute()` (already in use) | Phase 12 decision; no change |
| Verification framework | pytest/unittest suite | Simple functions with PASS/FAIL prints (verify_soul_golden.py pattern) | Consistent with existing scripts; CI-friendly; no dependencies |

---

## Common Pitfalls

### Pitfall 1: Incomplete Caller Audit for CFG-02
**What goes wrong:** `capture_semantic_snapshot()` and `cleanup_old_snapshots()` signatures are updated, but a call site is missed — the code still compiles (Python won't error until runtime), and the bug resurfaces under multi-project load.
**Why it happens:** Call sites may exist in pool.py, tests, or future Phase 17 code that hasn't been reviewed.
**How to avoid:** Before modifying signatures, grep all `.py` files for `capture_semantic_snapshot` and `cleanup_old_snapshots` to enumerate every call site.
**Warning signs:** After the fix, `uv run python -c "from orchestration.snapshot import capture_semantic_snapshot; import inspect; print(inspect.signature(capture_semantic_snapshot))"` should show `project_id` without a default.

### Pitfall 2: Orphaned `import os` / `from pathlib import Path` in config.py
**What goes wrong:** Deleting STATE_FILE and SNAPSHOT_DIR leaves `import os` and `from pathlib import Path` at the top of config.py with no purpose, creating noise.
**Why it happens:** Mechanical deletion of constants without reviewing imports.
**How to avoid:** After deleting the constants, verify that no remaining lines in config.py reference `os` or `Path`. If not, remove those imports too.
**Warning signs:** Linting tools would flag these as unused imports.

### Pitfall 3: monitor.py Still References STATE_FILE After Import Removal
**What goes wrong:** `STATE_FILE` appears in the import but the locked decision says to remove it. If it also appeared as a default argument somewhere in the file (it doesn't, but worth confirming), removing the import alone would cause a NameError.
**Why it happens:** Automatic assumption that import removal = done.
**How to avoid:** After removing from import, grep monitor.py for `STATE_FILE` to confirm zero remaining references.
**Warning signs:** `NameError: name 'STATE_FILE' is not defined` at runtime.

### Pitfall 4: soul-default.md Title Line vs. Body Confusion
**What goes wrong:** The title `# Soul: $agent_name ($tier)` is rendered inside `render_soul()` directly (not from the template file), and `soul-default.md` contains only `##` sections. Adding `$project_name` to the wrong location (e.g., as a `# ` header in the template) would break `parse_sections()` which skips title lines.
**Why it happens:** Template file has no title line — it starts with `## HIERARCHY`. The title is assembled in code.
**How to avoid:** Add `$project_name` inside a `##` section body, not as a standalone line before the first `##`.

### Pitfall 5: `$project_id` in build_variables() — Silent Unused Variable
**What goes wrong:** The audit of `build_variables()` may reveal `$project_id` is also unconsumed. If it's intentionally available for override files only, this is fine (safe_substitute leaves it as-is). But if it should appear in the default template, the fix is incomplete.
**Why it happens:** The decision says "audit all variables" — `$project_id` needs a determination.
**How to avoid:** During the audit step, explicitly decide: is `$project_id` expected in soul-default.md or is it intentionally reserved for override files? Document the decision. If it belongs in the template, add it alongside `$project_name`.

---

## Code Examples

### Exact lines to change in snapshot.py (CFG-02)

**capture_semantic_snapshot — before (line 196):**
```python
def capture_semantic_snapshot(task_id: str, workspace_path: str) -> Tuple[Path, Dict[str, Any]]:
```

**After:**
```python
def capture_semantic_snapshot(task_id: str, workspace_path: str, project_id: str) -> Tuple[Path, Dict[str, Any]]:
```

**Inside the function — before (line 260):**
```python
snapshots_dir = get_snapshot_dir()
```

**After:**
```python
snapshots_dir = get_snapshot_dir(project_id)
```

**cleanup_old_snapshots — before (line 485):**
```python
def cleanup_old_snapshots(workspace_path: str, max_snapshots: int = 100) -> Dict[str, Any]:
```

**After (project_id before the defaulted param):**
```python
def cleanup_old_snapshots(workspace_path: str, project_id: str, max_snapshots: int = 100) -> Dict[str, Any]:
```

**Inside the function — before (line 496):**
```python
snapshots_dir = get_snapshot_dir()
```

**After:**
```python
snapshots_dir = get_snapshot_dir(project_id)
```

### Exact block to replace in create_staging_branch (CFG-06)

**Before (lines 129-154) — 26-line inline duplicate block:**
```python
    # Detect default branch (main or master)
    default_branch = "main"
    try:
        branch_result = subprocess.run(
            ['git', '-C', str(workspace), 'symbolic-ref', 'refs/remotes/origin/HEAD'],
            capture_output=True,
            text=True
        )
        if branch_result.returncode == 0 and branch_result.stdout.strip():
            # Extract branch name from refs/remotes/origin/HEAD -> refs/remotes/origin/main
            default_branch = branch_result.stdout.strip().split('/')[-1]
        else:
            # Fallback: check if main exists, else use master
            main_check = subprocess.run(
                ['git', '-C', str(workspace), 'rev-parse', '--verify', 'main'],
                capture_output=True
            )
            if main_check.returncode != 0:
                master_check = subprocess.run(
                    ['git', '-C', str(workspace), 'rev-parse', '--verify', 'master'],
                    capture_output=True
                )
                if master_check.returncode == 0:
                    default_branch = "master"
    except Exception:
        pass  # Use default "main"
```

**After — single line:**
```python
    default_branch = _detect_default_branch(workspace)
```

### Exact template addition in soul-default.md (CFG-04)

**Current HIERARCHY section:**
```markdown
## HIERARCHY
- **Superior:** Reports to the L1 Strategic Orchestrator. All major project decisions must align with L1 strategic plans.
- **Subordinates:** Supervises L3 Worker containers.
- **Scope:** Primary authority over the `$workspace` workspace.
```

**After adding $project_name (one natural addition to the Scope line or as a new bullet — planner's discretion):**
```markdown
## HIERARCHY
- **Superior:** Reports to the L1 Strategic Orchestrator. All major project decisions must align with L1 strategic plans.
- **Subordinates:** Supervises L3 Worker containers.
- **Project:** $project_name
- **Scope:** Primary authority over the `$workspace` workspace.
```

### config.py after cleanup

```python
# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds
```

All `import os`, `from pathlib import Path`, and both deprecated constant blocks are removed.

### monitor.py import fix

**Before (lines 22-24 / 28-30):**
```python
from .config import STATE_FILE, POLL_INTERVAL
# and direct execution variant:
from orchestration.config import STATE_FILE, POLL_INTERVAL
```

**After:**
```python
from .config import POLL_INTERVAL
# and direct execution variant:
from orchestration.config import POLL_INTERVAL
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single global STATE_FILE in config.py | Per-project path via `get_state_path(project_id)` | Phase 11 | Enables multi-project isolation |
| Single global SNAPSHOT_DIR in config.py | Per-project path via `get_snapshot_dir(project_id)` | Phase 11 (API created) | Phase 16 finishes wiring this in |
| Hardcoded `"main"` default branch | `_detect_default_branch()` with 5-step resolution | Phase 11 (`_detect_default_branch` created) | Phase 16 finishes wiring create_staging_branch to use it |
| `string.Template` with unknown coverage | All declared variables consumed by template body | Phase 12 (partial) | Phase 16 completes coverage with `$project_name` |

**Deprecated/outdated:**
- `STATE_FILE` in config.py: Marked deprecated in Phase 11 ("Will be removed in Phase 13"). Phase 16 actually removes it.
- `SNAPSHOT_DIR` in config.py: Same story — marked deprecated, Phase 16 removes it.

---

## Open Questions

1. **Is `$project_id` also expected to appear in soul-default.md?**
   - What we know: `build_variables()` declares `project_id`, it does not appear in the default template body or title, and the decision says to audit all variables.
   - What's unclear: Is this intentional (available for override files but not default template) or an oversight?
   - Recommendation: During implementation, decide explicitly. If the answer is "intentional — override files may use it," document that decision. If the answer is "oversight," add it alongside `$project_name`.

2. **Are there any callers of `capture_semantic_snapshot()` or `cleanup_old_snapshots()` outside of the main orchestration files?**
   - What we know: Based on code inspection, these functions are currently called nowhere — `snapshot.py` defines them but no other `.py` file in `orchestration/` or `skills/` currently imports them. `entrypoint.sh` does not call them directly.
   - What's unclear: Whether tests or future phases depend on the old signature.
   - Recommendation: Grep before modifying. If no call sites exist, the signature change is risk-free. If call sites do exist, update all of them.

3. **Does `entrypoint.sh` need changes?**
   - What we know: `entrypoint.sh` does not call `capture_semantic_snapshot()` or `cleanup_old_snapshots()` — it uses a bash `update_state` helper that calls `JarvisState.update_task()` directly. The staging branch creation in `entrypoint.sh` is done in bash (lines 35-41), not via `create_staging_branch()`.
   - What's unclear: Whether `entrypoint.sh`'s inline bash branch detection also has the hardcoding bug (line 39: `git checkout -b "${STAGING_BRANCH}" main`).
   - Recommendation: Audit entrypoint.sh line 39 as part of CFG-06 fix. If it hardcodes `main`, that's a parallel bug — but the decision says to update all callers of changed functions. Since `entrypoint.sh` doesn't call `create_staging_branch()`, it's technically out of scope. Flag it as a known issue for Phase 17 if not addressed.

---

## Sources

### Primary (HIGH confidence)

Direct code inspection of the OpenClaw repository — all findings are based on reading the actual source files:

- `~/.openclaw/orchestration/snapshot.py` — full read, lines 20-523
- `~/.openclaw/orchestration/soul_renderer.py` — full read, `build_variables()` at line 82
- `~/.openclaw/orchestration/config.py` — full read (24 lines)
- `~/.openclaw/orchestration/monitor.py` — full read, import at lines 22-30
- `~/.openclaw/orchestration/project_config.py` — full read, `get_snapshot_dir()` at line 123
- `~/.openclaw/agents/_templates/soul-default.md` — full read (18 lines)
- `~/.openclaw/scripts/verify_soul_golden.py` — full read (verification pattern)
- `~/.openclaw/.planning/v1.1-MILESTONE-AUDIT.md` — integration issues enumerated
- `~/.openclaw/.planning/phases/16-integration-fixes/16-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)

- Python `string.Template` documentation: `safe_substitute()` behavior (leaves unresolved `$var` intact, no exception) — confirmed by existing usage in `soul_renderer.py` line 137 and `verify_soul_golden.py` line 68.
- Python `inspect.signature()` for verification approach — standard library, no version concerns.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are existing code in the repo, no new libraries
- Architecture: HIGH — changes are purely mechanical wiring (signature additions, block replacement, constant deletion)
- Pitfalls: HIGH — identified from direct code reading and locked decision constraints
- Verification approach: HIGH — modeled directly on existing `verify_soul_golden.py`

**Research date:** 2026-02-23
**Valid until:** Indefinite — no external dependencies; all findings are based on the current codebase state
