# Phase 13: Multi-Project Runtime - Research

**Researched:** 2026-02-23
**Domain:** Docker container namespacing, per-project pool management, multi-state-file monitoring
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Container naming convention: `openclaw-<project>-l3-<task_id>`
- Enforce max length on project IDs (e.g. 20 chars) to keep `docker ps` output readable
- Single Docker label: `openclaw.project=<project_id>` — no additional metadata labels needed
- Default monitor behavior (no `--project` flag): show ALL projects with a project column in output
- Always include the project column in table/tail output regardless of how many projects exist — consistent format for scripts
- `monitor.py task <id>`: search all projects for the task ID; if same ID found in multiple projects, list matches and prompt user to specify `--project`
- Color-code entries by project in `monitor.py tail` stream for visual distinction
- If `active_project` is switched while L3 containers are running: warn about in-flight containers from the previous project, but allow the switch. Running containers finish in their original project context (pinned via env var).
- spawn must hard-fail if it cannot resolve a valid project ID — no container without project context. Exit with clear error message.
- Per-project pool limit: each project gets its own 3-container semaphore (not a shared global pool)
- Pool registry pattern: a `PoolRegistry` class manages per-project `L3ContainerPool` instances, creating on first spawn
- Per-project limit is 3 containers each
- The existing PumplAI project should work identically after this phase — backward compatibility with single-project setups is essential
- Monitor color-coding per project should be visually distinct in standard terminals (not just 256-color)

### Claude's Discretion

- Whether to add `openclaw.task.type=code|test` label for convenience filtering — Claude decides based on implementation utility
- Whether to validate project IDs at init time (alphanumeric + hyphens only) or sanitize at spawn time — Claude picks the safest approach
- Whether to add a global ceiling on total containers across all projects (e.g. max 9) in addition to per-project limits — Claude determines if worth the complexity
- Whether container cleanup on shutdown/timeout covers all openclaw containers or only the active project's — Claude picks the safest approach for multi-project
- Claude determines the safest resolution pattern for `OPENCLAW_PROJECT` across spawn, pool, state engine, and entrypoint.sh — env-var-first for containers at minimum
- Whether `entrypoint.sh` should independently verify `OPENCLAW_PROJECT` is set (defense in depth) or trust spawn — Claude decides

### Deferred Ideas (OUT OF SCOPE)

- Per-project pool isolation mode (`l3_pool: "shared"|"isolated"` in project.json) — tracked as POOL-01/02/03 for v1.2
- Per-project Docker networks — explicitly out of scope per REQUIREMENTS.md
</user_constraints>

---

## Summary

Phase 13 wires project identity through the three components that constitute the L3 container lifecycle: `spawn.py` (spawning), `pool.py` (concurrency management), and `monitor.py` (observation). The current codebase already has `OPENCLAW_PROJECT` env-var-first resolution in `project_config.py::get_active_project_id()` and a per-project `get_state_path()` — Phase 13 is about propagating those through to container names, Docker labels, pool isolation, and monitor output.

The changes are surgical: each of the three files gets a focused extension (project ID threading, not architectural rewrites). The most complex addition is `PoolRegistry` in `pool.py` — a new class that owns per-project `L3ContainerPool` instances indexed by project ID. The monitor changes are UI-layer: widening the output table, reading state files across all known projects, and adding ANSI color cycling per project. `entrypoint.sh` needs a single guard line. No new dependencies are required.

**Primary recommendation:** Thread `project_id` as an explicit parameter from the outermost `spawn_task()` caller down through every layer; never rely on ambient state reads mid-flight. Validate the project ID string at spawn entry before any Docker or state operations.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MPR-01 | `spawn.py` adds `openclaw.project` label to all L3 containers | Docker SDK `labels` dict already used in `spawn_l3_specialist()` — add one key |
| MPR-02 | Container names prefixed with project ID: `openclaw-<project>-l3-<task_id>` | Line 110 of `spawn.py` sets `container_name` — replace with namespaced pattern |
| MPR-03 | `pool.py` resolves state file path per-project via `get_state_path()` | `L3ContainerPool.__init__` calls `get_state_path()` once at construction — must accept `project_id` and store it; `JarvisState` calls in `_attempt_task` must use per-project state file |
| MPR-04 | `monitor.py` accepts `--project` flag to filter output by project | New `argparse` flag; three display functions must accept optional project filter and discover all state files for all-projects mode |
| MPR-05 | `spawn.py` injects `OPENCLAW_PROJECT` env var into L3 containers | `environment` dict in `container_config` — add key |
| MPR-06 | `active_project` resolution is env-var-first to prevent mid-execution mutation | Already implemented in `project_config.py::get_active_project_id()` — Phase 13 must ensure `spawn.py` captures project ID once at spawn time and passes it explicitly, not re-reads ambient config at retry or pool-state-update time |
</phase_requirements>

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `docker` Python SDK | >=7.1.0 (already installed) | Container lifecycle, labels, filters | Already the project dependency; `labels` dict param is the correct API |
| `asyncio.Semaphore` | stdlib | Per-project concurrency limiting | Already used in `L3ContainerPool`; `PoolRegistry` creates one semaphore per project ID |
| `argparse` subparsers | stdlib | `--project` flag on monitor | Already used in `monitor.py` and `spawn.py` CLI sections — consistent pattern |
| `re` module | stdlib | Project ID validation (alphanumeric + hyphens) | Standard; no external deps needed |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| ANSI escape codes (already in `Colors` class) | N/A | Per-project color in tail output | Extend existing `Colors` class with a project-color rotation |
| `glob` / `pathlib.Path.glob()` | stdlib | Discover all project state files for all-projects monitor mode | `workspace/.openclaw/*/workspace-state.json` glob finds all project state files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pathlib.glob` for state file discovery | Enumerate `projects/` directory | `projects/` directory is the correct source of truth — glob on state files may miss projects that haven't spawned a task yet; enumerating `projects/` sub-directories is safer for all-projects mode |
| Per-project color via index in a list | Hash-based color | List rotation is predictable and consistent across runs; hash could theoretically collide on small color sets |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Change Structure

The three modified files plus entrypoint:

```
skills/spawn_specialist/
├── spawn.py          # +project_id param, +label, +env var, +name prefix, +validation
├── pool.py           # +PoolRegistry class, +project_id threading through all methods
orchestration/
├── monitor.py        # +--project flag, +project column, +multi-state-file discovery
docker/l3-specialist/
├── entrypoint.sh     # +OPENCLAW_PROJECT guard (defense in depth)
```

### Pattern 1: project_id threading — capture-once, pass-everywhere

**What:** At the top of `spawn_l3_specialist()`, resolve and validate project_id once. Pass it as an explicit argument to every downstream call (`get_state_path(project_id)`, `get_workspace_path(project_id)`, etc.). Never call `get_active_project_id()` inside the retry path or pool update path.

**Why:** `active_project` in `openclaw.json` could change between spawn and retry. The container must complete in the project context it was born in (MPR-06). Env-var pinning on the container handles isolation at the process boundary; Python-side code must handle isolation at the call boundary.

**Implementation:**

```python
# At the top of spawn_l3_specialist()
def spawn_l3_specialist(
    task_id: str,
    skill_hint: str,
    task_description: str,
    workspace_path: str,
    requires_gpu: bool = False,
    cli_runtime: str = "claude-code",
    project_id: Optional[str] = None,  # NEW param
) -> Any:
    # Resolve once — hard fail if unresolvable
    if project_id is None:
        project_id = get_active_project_id()

    # Validate project ID format
    _validate_project_id(project_id)

    # All downstream calls receive project_id explicitly
    state_file = get_state_path(project_id)
    ...
```

### Pattern 2: Project ID validation function

**What:** A single `_validate_project_id(project_id: str)` function at module level in `spawn.py` that enforces:
1. Non-empty string
2. Length <= 20 characters
3. Characters: `[a-zA-Z0-9-]` only (alphanumeric + hyphens)

**Why:** Container names are derived from project IDs. Invalid characters in Docker container names cause API errors. Catching this early gives a clear error message rather than a cryptic Docker exception. Validation at spawn time (not init time) is correct because spawn is the enforced entry point.

```python
import re

_PROJECT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]{1,20}$')

def _validate_project_id(project_id: str) -> None:
    if not _PROJECT_ID_PATTERN.match(project_id):
        raise ValueError(
            f"Invalid project ID '{project_id}': must be 1-20 chars, "
            "alphanumeric and hyphens only."
        )
```

### Pattern 3: PoolRegistry — per-project L3ContainerPool instances

**What:** A `PoolRegistry` class in `pool.py` that holds a `Dict[str, L3ContainerPool]` and creates/returns a pool per project ID. `L3ContainerPool.__init__` gains a `project_id` parameter; `_attempt_task` uses `JarvisState(get_state_path(self.project_id))` not the single stored `self.state_file`.

```python
class PoolRegistry:
    """Manages per-project L3ContainerPool instances."""

    def __init__(self, max_per_project: int = 3):
        self._pools: Dict[str, L3ContainerPool] = {}
        self._max_per_project = max_per_project

    def get_pool(self, project_id: str) -> "L3ContainerPool":
        if project_id not in self._pools:
            self._pools[project_id] = L3ContainerPool(
                project_id=project_id,
                max_concurrent=self._max_per_project,
            )
        return self._pools[project_id]
```

The updated `spawn_task()` convenience function accepts `project_id` and routes through `PoolRegistry`:

```python
async def spawn_task(
    task_id: str,
    skill_hint: str,
    task_description: str,
    workspace_path: Optional[str] = None,
    requires_gpu: bool = False,
    cli_runtime: str = "claude-code",
    project_id: Optional[str] = None,   # NEW
) -> Dict[str, Any]:
    if project_id is None:
        project_id = get_active_project_id()
    ...
    registry = PoolRegistry(max_per_project=3)
    pool = registry.get_pool(project_id)
    return await pool.spawn_and_monitor(...)
```

### Pattern 4: Multi-state-file monitor discovery

**What:** When `--project` is not specified, `monitor.py` discovers all project state files by globbing `workspace/.openclaw/*/workspace-state.json` or by enumerating `projects/` subdirectories via `project_config`. The project ID is inferred from the directory name.

**Why:** State files are per-project at `workspace/.openclaw/<project_id>/workspace-state.json`. The monitor must aggregate tasks from all files, tagging each with its source project ID.

```python
def _discover_state_files(project_filter: Optional[str] = None) -> List[Tuple[str, Path]]:
    """Return list of (project_id, state_file_path) pairs."""
    root = _find_project_root()
    projects_dir = root / "projects"
    results = []
    for project_dir in sorted(projects_dir.iterdir()):
        if project_dir.name.startswith("_"):  # skip _templates
            continue
        if project_filter and project_dir.name != project_filter:
            continue
        state_file = root / "workspace" / ".openclaw" / project_dir.name / "workspace-state.json"
        results.append((project_dir.name, state_file))
    return results
```

### Pattern 5: Project color rotation in monitor tail

**What:** A deterministic mapping from project ID to ANSI color. Use a small list of standard 8-color ANSI codes (always works in standard terminals, not 256-color dependent). Project IDs are assigned colors by insertion order in the project discovery list.

```python
# Standard 8-color ANSI — works in all terminals
PROJECT_COLORS = [
    '\033[92m',  # Green
    '\033[94m',  # Blue
    '\033[95m',  # Magenta
    '\033[96m',  # Cyan
    '\033[93m',  # Yellow
    '\033[91m',  # Red
]

def get_project_color(project_id: str, project_list: List[str]) -> str:
    idx = project_list.index(project_id) if project_id in project_list else 0
    return PROJECT_COLORS[idx % len(PROJECT_COLORS)]
```

### Anti-Patterns to Avoid

- **Re-reading `active_project` mid-flight:** `pool._attempt_task` currently calls `JarvisState(self.state_file)`. After Phase 13 `self.state_file` is gone — replaced with `self.project_id`. The `JarvisState` must be constructed with `get_state_path(self.project_id)` inside `_attempt_task`, not from a cached `self.state_file` value that could be stale.
- **Container name without project prefix collision:** The current `container_name = f"openclaw-l3-{task_id}"` will collide if two projects run tasks with the same `task_id`. The fix is `f"openclaw-{project_id}-l3-{task_id}"` — this is MPR-02.
- **Monitoring only the active project's state file:** `monitor.py` currently resolves one state file via `get_state_path()`. Without phase 13 changes, switching `active_project` makes the previous project's tasks invisible. The fix is multi-state-file discovery.
- **Skipping `_templates` directory in project enumeration:** `projects/_templates/` exists for Phase 14. Monitor and pool discovery must skip directories starting with `_`.
- **Global hard cap complexity without proportional value:** A global cap of 9 (3 × 3 projects) adds a second semaphore and cross-project contention logic. Given single-host operation and per-project limits already in place, this is unnecessary complexity. Recommendation: **skip the global cap**. If a user has 4 projects each capped at 3, the machine can handle 12 L3 containers — that is within the per-project intent.
- **Cleanup scope ambiguity:** On shutdown/timeout, cleanup should cover all `openclaw.managed=true` containers regardless of project. Scoping cleanup to only the active project would leave orphaned containers from other projects on crash. Recommendation: **cleanup all `openclaw.managed=true` containers**.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docker container filtering by project | Custom container list + Python filter loop | `docker.containers.list(filters={"label": "openclaw.project=pumplai"})` | Docker daemon does the filter server-side; confirmed working via live test |
| Project ID color assignment | Color hash function | Index into fixed list modulo list length | Deterministic, predictable, zero collision risk for 6 or fewer projects |
| State file discovery | Custom JSON registry of known state files | `pathlib.Path.iterdir()` on `projects/` directory | `projects/` directory is already the canonical project registry; no secondary registry needed |

**Key insight:** The Docker Python SDK `labels` parameter on `containers.run()` (and `containers.list()` filters) is the correct and complete API for container project tagging. There is no need to track container-to-project mappings in a separate data structure.

---

## Common Pitfalls

### Pitfall 1: State file path inside `_attempt_task` is stale after retry

**What goes wrong:** `L3ContainerPool.__init__` captures `self.state_file = get_state_path()` at construction time. The pool is re-used for the retry attempt. If `active_project` flipped between the first attempt and the retry (unlikely but possible), the retry writes to the wrong state file.

**Why it happens:** State file captured once at construction, not per-task. After Phase 13, `project_id` is a constructor param — `get_state_path(self.project_id)` inside `_attempt_task` is safe because `project_id` is immutable after construction.

**How to avoid:** In `_attempt_task`, construct `JarvisState(get_state_path(self.project_id))` locally, not from `self.state_file`. Remove `self.state_file` attribute entirely from `L3ContainerPool`.

### Pitfall 2: Container name length exceeding Docker's 64-character limit

**What goes wrong:** Docker container names have no hard API limit but `docker ps` truncates very long names. More importantly, the `container_name` is used as a lookup key (`client.containers.get(container_name)`) — the name must be valid.

**Why it happens:** `openclaw-<project>-l3-<task_id>`. If `project_id` is 20 chars and `task_id` is a UUID (36 chars), the name is `openclaw-` (9) + 20 + `-l3-` (4) + 36 = 69 chars. Docker allows names up to ~128 chars but display is cleaner under 64.

**How to avoid:** The 20-char project ID limit in the decisions already addresses this. With a max project ID of 20 chars and typical task IDs (e.g. `abc-001`, `task-20260223-001`), names stay under 50 chars. Document the recommendation: use short task IDs in practice.

### Pitfall 3: Monitor discovers `_templates` as a project

**What goes wrong:** `projects/_templates/` is created for Phase 14 (CLI-06). If monitor enumerates `projects/` subdirectories blindly, it will try to open `workspace/.openclaw/_templates/workspace-state.json`, find no file, and either error or silently produce an empty project column.

**Why it happens:** The templates directory lives alongside real project directories.

**How to avoid:** Skip any subdirectory whose name starts with `_` in the project discovery loop.

### Pitfall 4: `geriai` project exists without a state file yet

**What goes wrong:** `projects/geriai/` exists (confirmed in repo) but `workspace/.openclaw/geriai/workspace-state.json` may not exist if no tasks have been spawned for geriai. The monitor's all-projects mode must handle missing state files gracefully (not crash).

**Why it happens:** State files are created lazily by `JarvisState._ensure_state_file()` on first write, not at project creation.

**How to avoid:** In the monitor's discovery path, check `state_file.exists()` before attempting to read it. If missing, treat as a project with zero tasks (display project row with "No tasks" or simply skip the project in the task table).

### Pitfall 5: Backward compatibility — single-project callers

**What goes wrong:** The `spawn_task()` convenience function currently takes no `project_id` parameter. Code calling `spawn_task(task_id, "code", "description")` without a project ID would fail if the signature becomes required.

**Why it happens:** Phase 13 adds `project_id` to function signatures. Callers not updated would break.

**How to avoid:** Make `project_id: Optional[str] = None` with fallback to `get_active_project_id()`. This preserves backward compatibility: single-project setups with `active_project` set in `openclaw.json` continue to work without any call-site changes.

---

## Code Examples

Verified patterns from codebase and Docker SDK documentation:

### Adding the project label to container_config in spawn.py

```python
# Source: spawn.py lines 160-167 (existing labels block)
"labels": {
    "openclaw.managed": "true",
    "openclaw.level": str(l3_config.get("level", 3)),
    "openclaw.task_id": task_id,
    "openclaw.spawned_by": spawned_by,
    "openclaw.skill": skill_hint,
    "openclaw.tier": f"l{l3_config.get('level', 3)}",
    "openclaw.project": project_id,           # MPR-01: add this line
    # Optional (Claude's discretion): "openclaw.task.type": skill_hint  # MPR-01 convenience
},
```

Recommendation for `openclaw.task.type`: **add it**. It enables `docker ps --filter label=openclaw.task.type=code` for debugging without any runtime cost. One extra dict key.

### Container name with project prefix

```python
# Source: spawn.py line 110 (existing)
container_name = f"openclaw-l3-{task_id}"         # current
container_name = f"openclaw-{project_id}-l3-{task_id}"  # MPR-02: replacement
```

### OPENCLAW_PROJECT env var injection

```python
# Source: spawn.py lines 139-145 (existing environment block)
"environment": {
    "TASK_ID": task_id,
    "SKILL_HINT": skill_hint,
    "STAGING_BRANCH": staging_branch,
    "CLI_RUNTIME": cli_runtime,
    "TASK_DESCRIPTION": task_description,
    "OPENCLAW_PROJECT": project_id,            # MPR-05: add this line
    "OPENCLAW_STATE_FILE": f"/workspace/.openclaw/{project_id}/workspace-state.json",  # updated path
},
```

Note: The existing `OPENCLAW_STATE_FILE` value uses `get_state_path().parent.name` which resolves the active project at spawn time — fine for single project but should use the already-resolved `project_id` for clarity and correctness.

### entrypoint.sh defense-in-depth guard

```bash
# After the existing required-var checks, add:
: "${OPENCLAW_PROJECT:?OPENCLAW_PROJECT is required — container spawned without project context}"
```

Recommendation: **add the guard**. It is a single line, runs in <1ms, and provides an unambiguous failure message if a container is ever spawned without the env var (e.g. during manual testing or a future code regression). Defense in depth is worth the negligible cost here.

### Docker label filter (confirmed working — live tested)

```python
# Source: Docker Python SDK docs + live verified against running daemon
client.containers.list(filters={"label": "openclaw.project=pumplai"})
# Returns only containers with openclaw.project label set to "pumplai"
```

### Monitor --project argparse addition

```python
# Add to each subparser in monitor.py main():
for subparser in [tail_parser, status_parser, task_parser]:
    subparser.add_argument(
        '--project',
        type=str,
        default=None,
        help='Filter output by project ID (default: show all projects)',
    )
```

### Monitor table output with project column

```python
# Extend existing show_status() header line
print(f"{Colors.BOLD}{'PROJECT':<15} {'TASK ID':<20} {'STATUS':<15} {'SKILL':<10} {'CREATED':<20} {'LAST ACTIVITY'}{Colors.RESET}")
print("-" * 115)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single global state file | Per-project state file at `workspace/.openclaw/<project_id>/workspace-state.json` | Phase 11 | Phase 13 builds on this — `get_state_path(project_id)` already exists |
| Single global `L3ContainerPool` | Per-project pool via `PoolRegistry` | Phase 13 | Each project gets independent concurrency limits |
| Container named `openclaw-l3-<task_id>` | Named `openclaw-<project>-l3-<task_id>` | Phase 13 | Eliminates cross-project name collisions |

**Note on Phase 11 dependency:** `project_config.py::get_state_path(project_id)` and `get_active_project_id()` must be in place before Phase 13 can proceed. Phase 13 CONTEXT.md lists "Depends on Phase 11." Confirm Phase 11 is complete before execution.

---

## Open Questions

1. **Phase 11 completion status**
   - What we know: STATE.md shows Phase 11 is "ready to plan" as of 2026-02-23; `project_config.py` already contains `get_state_path(project_id)` which is the Phase 11 CFG-03 deliverable
   - What's unclear: Whether Phase 11 has been fully executed or if `project_config.py` changes were pre-landed
   - Recommendation: Verify `workspace/.openclaw/pumplai/workspace-state.json` exists and is the canonical state file path before beginning Phase 13 implementation. The planner should add a prerequisite check task.

2. **`spawn_l3_specialist` call sites outside known path**
   - What we know: Grep shows `spawn_task` / `spawn_l3_specialist` are used in `pool.py` and `spawn.py` only within the codebase (not counting planning docs and workspace copies)
   - What's unclear: The STATE.md concern "Catalogue all `spawn_task()` call sites before Phase 13 begins" was logged as a pre-work item
   - Recommendation: The planner's Wave 0 or first task should include a call-site audit. Based on the grep results, the live callers are only in `pool.py` — this is low risk but should be verified.

3. **geriai project state — is it a real second project or a stub?**
   - What we know: `projects/geriai/project.json` exists but its content is identical to `pumplai` (same workspace, same agent IDs). This appears to be a copy-paste stub created to test multi-project infrastructure.
   - What's unclear: Whether the monitor's all-projects mode needs to handle the case of two projects sharing the same workspace path
   - Recommendation: Treat `geriai` as a valid second project for testing. The shared workspace path is the user's testing setup. The monitor and pool operate on project IDs and state files, not workspace paths, so no special handling is needed.

---

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` — the key is absent. Treating as **false**. Validation Architecture section is **omitted** per researcher instructions.

However, the project testing pattern (from `scripts/verify_soul_golden.py` and `scripts/verify_phase3.py`) establishes a **verification script convention**: standalone Python scripts in `scripts/` that run assertions and print PASS/FAIL. Phase 13's planner should plan a `scripts/verify_phase13.py` script covering the 6 MPR requirements as the UAT gate.

---

## Sources

### Primary (HIGH confidence)
- Live codebase inspection: `skills/spawn_specialist/spawn.py` — current container_name, labels, environment dict patterns (lines 110, 139-167)
- Live codebase inspection: `skills/spawn_specialist/pool.py` — `L3ContainerPool` constructor, `_attempt_task` state file usage
- Live codebase inspection: `orchestration/monitor.py` — current argparse structure, display functions
- Live codebase inspection: `orchestration/project_config.py` — `get_active_project_id()`, `get_state_path()` already env-var-first
- Docker Python SDK (live verified): `docker.containers.list(filters={"label": "..."})` label filter confirmed working against running daemon
- Docker Python SDK `help(containers.run)`: `labels` accepts `dict` of name-value pairs — confirmed

### Secondary (MEDIUM confidence)
- `projects/geriai/project.json` inspection: second project confirmed in repo for multi-project testing
- `scripts/verify_soul_golden.py`: establishes project testing convention (standalone script, PASS/FAIL output)

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all required libraries already present in codebase, no new deps
- Architecture: HIGH — based on direct code reading of all files that Phase 13 modifies
- Pitfalls: HIGH — pitfalls derived from concrete code inspection (actual line numbers, actual data structures), not speculation

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (codebase is stable; Docker SDK API is stable)
