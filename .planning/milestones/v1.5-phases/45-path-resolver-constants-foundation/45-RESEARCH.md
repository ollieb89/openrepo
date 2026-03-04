# Phase 45: Path Resolver + Constants Foundation - Research

**Researched:** 2026-02-25
**Domain:** Python internal refactoring — path resolution and constants centralization
**Confidence:** HIGH (pure codebase investigation, no external library research needed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Path resolver API design:**
- Functions live in `config.py` (not a new module)
- `get_state_path(project_id)` and `get_snapshot_dir(project_id)` require explicit project_id — no implicit active-project fallback
- Workspace is always derived from project config (project.json) — no optional workspace parameter
- Resolver checks `OPENCLAW_ROOT` env var first, falls back to default `~/.openclaw` — aligns Python with Docker entrypoint.sh
- Resolver checks `OPENCLAW_STATE_FILE` env var first, then derives from `OPENCLAW_ROOT` + project — aligns Python with container usage
- Context-aware: detects container environment (e.g., `/.dockerenv` or `OPENCLAW_ROOT=/openclaw`) and adjusts base path accordingly

**Constants organization:**
- Constants are defaults that get overridden at runtime — `config.py` has `DEFAULT_POOL_MAX = 3`, code reads `openclaw.json` and falls back to `config.py` default
- `MEMORY_CONTEXT_BUDGET` (currently hardcoded 2000 in spawn.py) moves to `config.py` in this phase

**Migration strategy:**
- Hard swap, no deprecation — all 3 divergent resolvers replaced with the new one
- Batch all call site changes and test at end (not module-by-module)
- Both `pool.py` AND `project_config.py` import pool defaults from `config.py` — eliminates `_POOL_CONFIG_DEFAULTS` duplication entirely

**Container path alignment:**
- spawn.py calls `get_state_path(project_id)` and injects the resolved path as `OPENCLAW_STATE_FILE` env var into L3 containers — containers read it directly instead of resolving themselves

### Claude's Discretion

- Constants grouping style: flat module-level vars vs grouped dataclasses — pick what fits the volume of constants
- Naming convention: establish consistent scheme (e.g., subsystem-prefixed SCREAMING_SNAKE)
- Whether `_POOL_CONFIG_DEFAULTS` dict stays as a dict or breaks into individual constants — based on how it's consumed
- Path validation behavior: compute-only vs validate-and-raise — based on what callers need

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-01 | Operator can rely on a single path resolver function for workspace state — `get_state_path()` and `get_snapshot_dir()` return paths that match where L3 containers actually write | Confirmed: path divergence is real and precisely mapped. See Architecture Patterns for the canonical resolution algorithm. |
| CONF-05 | All shared constants and defaults (pool config, lock timeouts, cache TTL, log levels, memory budget cap) live in `config.py` — no duplicated magic values across modules | Confirmed: exact set of duplicated values identified across pool.py, project_config.py, and spawn.py. See Architecture Patterns for migration map. |

</phase_requirements>

---

## Summary

Phase 45 is a pure internal refactoring with no new user-facing capabilities. Its value is correctness: the existing codebase has a latent path divergence bug and duplicate constant definitions that create maintenance risk and can cause runtime failures if `OPENCLAW_ROOT` is not set.

The path divergence is confirmed by codebase investigation. Three callers currently resolve the project root independently: `spawn.py` uses `Path(__file__).parent.parent.parent` (resolves to `~/.openclaw` — correct), `project_config.py` uses `Path(__file__).parent.parent` (resolves to `packages/orchestration/src` — wrong without env var), and `monitor.py` uses `Path(__file__).parent.parent` (resolves to `packages/orchestration/src/openclaw` — wrong without env var). The system works in production only because `OPENCLAW_ROOT` env var is set at runtime, which masks the bug in `project_config.py` and `monitor.py`. Without that env var (e.g., tests, direct CLI invocations) the wrong root is silently used.

The constant duplication is equally concrete: `_POOL_CONFIG_DEFAULTS` dict is defined identically in both `project_config.py` and `pool.py`; `MEMORY_CONTEXT_BUDGET = 2000` is hardcoded in `spawn.py` with a comment; `config.py` already has `LOCK_TIMEOUT`, `POLL_INTERVAL`, `CACHE_TTL_SECONDS`, `LOG_LEVEL`, and `ACTIVITY_LOG_MAX_ENTRIES` — but is missing pool defaults and the memory budget cap.

**Primary recommendation:** Move `get_state_path()` and `get_snapshot_dir()` from `project_config.py` into `config.py` with a single authoritative `_find_project_root()` implementation, and add the pool defaults + `MEMORY_CONTEXT_BUDGET` to `config.py`. Then update all call sites to import from `config.py`. The existing `config.py` already establishes the right pattern — this phase extends it.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib.Path` | stdlib | Path manipulation and resolution | Already used throughout; no new dependencies |
| `os.environ` | stdlib | Env var reads for `OPENCLAW_ROOT`, `OPENCLAW_STATE_FILE` | Already used in `config.py` and `project_config.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | — | — | No new dependencies required |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flat constants in `config.py` | `dataclasses` / `NamedTuple` | Dataclasses add import overhead and pattern change for minimal benefit given ~10 constants total |
| Hard-coded pool dict in config.py | Individual `DEFAULT_POOL_MAX = 3` etc. | Depends on how `pool.py` and `project_config.py` consume it — see Architecture Patterns |

**Installation:** No new packages. Zero new dependencies.

---

## Architecture Patterns

### Recommended Project Structure

No directory changes. All changes are within:

```
packages/orchestration/src/openclaw/
├── config.py          # THE change: add path resolver functions + new constants
├── project_config.py  # Remove get_state_path, get_snapshot_dir, _POOL_CONFIG_DEFAULTS,
│                      # _find_project_root; keep all other public API intact
└── cli/
    └── monitor.py     # Update _discover_projects() to use config.get_state_path() loop

skills/spawn/
├── spawn.py           # Remove hardcoded project_root; use config.get_state_path()
└── pool.py            # Remove _POOL_DEFAULTS; import from openclaw.config
```

### Pattern 1: Authoritative Root Resolver

**What:** Single `_find_project_root()` in `config.py` that is the only path-traversal logic in the codebase.

**When to use:** Called only from other functions in `config.py` — never imported by callers directly.

**Implementation:**

```python
# packages/orchestration/src/openclaw/config.py
import os
from pathlib import Path
from typing import Optional

def _find_project_root() -> Path:
    """Single authoritative project root resolver.

    Resolution order:
    1. OPENCLAW_ROOT env var (explicit override — production and Docker use this)
    2. Default ~/.openclaw

    Never traverses __file__ — avoids install-location brittleness.
    """
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        return Path(env_root)
    return Path.home() / ".openclaw"
```

**Why `Path.home() / ".openclaw"` not `Path(__file__).parent.parent`:**
- `Path(__file__)` resolves relative to where the package is installed. After `uv pip install -e .`, `config.py` is at `packages/orchestration/src/openclaw/config.py`, so `parent.parent` = `packages/orchestration/src` — wrong.
- `Path.home() / ".openclaw"` is always `~/.openclaw` regardless of install location, matching the documented default in CLAUDE.md and Makefile.

### Pattern 2: Path Resolver Functions in config.py

**What:** `get_state_path(project_id)` and `get_snapshot_dir(project_id)` move from `project_config.py` to `config.py`. They are the only exported path-resolution API.

**Current location:** `project_config.py` lines 291–334
**Target location:** `config.py`

**Key decisions from CONTEXT.md:**
- `project_id` is required — no fallback to active project. Callers must pass it explicitly.
- `OPENCLAW_STATE_FILE` env var is checked first (aligns with entrypoint.sh which sets it for containers).
- For `get_state_path()`: if `OPENCLAW_STATE_FILE` is set, return `Path(os.environ["OPENCLAW_STATE_FILE"])` directly.

```python
# packages/orchestration/src/openclaw/config.py

def get_state_path(project_id: str) -> Path:
    """Return the per-project state file path.

    Resolution order:
    1. OPENCLAW_STATE_FILE env var (container-injected path — use as-is)
    2. Derived: <project_root>/workspace/.openclaw/<project_id>/workspace-state.json

    Args:
        project_id: Required. No implicit active-project fallback.
    """
    env_state = os.environ.get("OPENCLAW_STATE_FILE")
    if env_state:
        return Path(env_state)
    root = _find_project_root()
    return root / "workspace" / ".openclaw" / project_id / "workspace-state.json"


def get_snapshot_dir(project_id: str) -> Path:
    """Return the per-project snapshot directory path.

    Path: <project_root>/workspace/.openclaw/<project_id>/snapshots/

    Args:
        project_id: Required. No implicit active-project fallback.
    """
    root = _find_project_root()
    return root / "workspace" / ".openclaw" / project_id / "snapshots"
```

**Note on validation:** The current `project_config.py` versions check that `project.json` exists before returning the path. The CONTEXT.md decision is "compute-only vs validate-and-raise — based on what callers need." Given that:
- `spawn.py` calls `get_state_path()` after already loading project config (project is validated upstream)
- `pool.py` calls it similarly
- `monitor.py` doesn't validate project existence before computing paths

The recommendation is: **compute-only** (no existence check in `config.py`). Keep `ProjectNotFoundError` in `project_config.py` for `load_project_config()` — that's where project existence is authoritatively checked.

### Pattern 3: Constants Centralization

**What moves to `config.py`:**

Currently in `config.py` (already correct):
```python
LOCK_TIMEOUT = 5          # seconds
LOCK_RETRY_ATTEMPTS = 3
POLL_INTERVAL = 1.0       # seconds
CACHE_TTL_SECONDS = 5.0
LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()
ACTIVITY_LOG_MAX_ENTRIES = int(os.environ.get("OPENCLAW_ACTIVITY_LOG_MAX", "100"))
```

**To add to `config.py`:**

```python
# Pool defaults (remove from project_config.py and pool.py)
DEFAULT_POOL_MAX_CONCURRENT = 3
DEFAULT_POOL_MODE = "shared"
DEFAULT_POOL_OVERFLOW_POLICY = "wait"
DEFAULT_POOL_QUEUE_TIMEOUT_S = 300
DEFAULT_POOL_RECOVERY_POLICY = "mark_failed"

# Memory injection (move from spawn.py)
MEMORY_CONTEXT_BUDGET = 2000  # Hard cap in characters for injected memory section
```

**Constants grouping recommendation (Claude's Discretion):** Flat module-level vars over grouped dataclasses. The volume (~12 constants total) does not justify the pattern complexity of dataclasses. Subsystem-prefixed `SCREAMING_SNAKE` naming (`DEFAULT_POOL_*`) provides grouping without structure overhead.

**Pool defaults — dict vs individual vars (Claude's Discretion):** Break into individual constants. Rationale: `pool.py` currently uses `_POOL_DEFAULTS["overflow_policy"]` etc., and `project_config.py` uses `_POOL_CONFIG_DEFAULTS.copy()`. Both can be converted to reference individual `config.DEFAULT_POOL_*` constants without behavioral change, and individual constants are grep-able per the success criterion.

### Pattern 4: Call Site Migration

**spawn.py changes:**

| Current | After |
|---------|-------|
| `project_root = Path(__file__).parent.parent.parent` (line 433) | Remove; use `get_project_root()` from config or inline `_find_project_root()` |
| `config_path = Path(__file__).parent.parent.parent / "agents" / ...` (line 131) | Use `_find_project_root() / "agents" / ...` |
| `MEMORY_CONTEXT_BUDGET = 2000` (line 42) | Remove; import from `openclaw.config` |
| `"OPENCLAW_STATE_FILE": f"/workspace/.openclaw/{project_id}/workspace-state.json"` (line 467) | Replace with `str(get_state_path(project_id))` converted to container path, OR keep as-is since it's container-internal (see Pitfall 2) |
| `str(project_root / "workspace" / ".openclaw")` (line 455, volume mount) | Use `str(_find_project_root() / "workspace" / ".openclaw")` |

**Note on spawn.py OPENCLAW_STATE_FILE injection:** spawn.py currently hardcodes `/workspace/.openclaw/{project_id}/workspace-state.json` as the container-side path (line 467). This is intentionally the **container-internal** path (mounted at `/workspace/.openclaw`). The CONTEXT.md decision says "spawn.py calls `get_state_path(project_id)` and injects the resolved path as `OPENCLAW_STATE_FILE`." But `get_state_path()` returns the **host** path. There is a translation needed: host path `→` container path.

The container mount is: `str(project_root / "workspace" / ".openclaw"): {"bind": "/workspace/.openclaw"}`. So the host path `~/.openclaw/workspace/.openclaw/{id}/workspace-state.json` maps to container path `/workspace/.openclaw/{id}/workspace-state.json`.

**Recommendation:** Keep the OPENCLAW_STATE_FILE injection as a computed transformation rather than calling get_state_path() here, since get_state_path() returns the host path and the container needs the container path. Document this as a known asymmetry.

**project_config.py changes:**

| What | Action |
|------|--------|
| `get_state_path()` | Remove — callers now import from `openclaw.config` |
| `get_snapshot_dir()` | Remove — callers now import from `openclaw.config` |
| `_find_project_root()` | Remove — callers now use `openclaw.config._find_project_root()` |
| `_POOL_CONFIG_DEFAULTS` dict | Remove — `get_pool_config()` references `config.DEFAULT_POOL_*` constants |
| `load_and_validate_openclaw_config()` | Keep — still calls `_find_project_root()` but now imports it from config |

**pool.py changes:**

| What | Action |
|------|--------|
| `_POOL_DEFAULTS` dict | Remove — replace all references with `config.DEFAULT_POOL_*` |
| `from openclaw.project_config import get_state_path, ...` | `get_state_path` now imported from `openclaw.config` |

**monitor.py changes:**

| What | Action |
|------|--------|
| `root = Path(__file__).parent.parent` (line 65) | Replace with `from openclaw.config import _find_project_root; root = _find_project_root()` |
| `state_file = root / "workspace" / ".openclaw" / entry.name / "workspace-state.json"` | Replace with `get_state_path(entry.name)` from config |

**snapshot.py changes:**

| What | Action |
|------|--------|
| `from .project_config import load_project_config, get_snapshot_dir` | Change `get_snapshot_dir` import to `from .config import get_snapshot_dir` |

**state_engine.py:** No changes needed. It already imports from `.config` correctly.

### Pattern 5: Export Pattern from project_config.py

**Important:** `spawn.py` currently imports `get_state_path` from `project_config`:
```python
from openclaw.project_config import (
    get_active_project_id,
    load_project_config,
    get_workspace_path,
    get_agent_mapping,
    get_state_path,          # <- moves to config
    get_memu_config,
)
```

After the move, `spawn.py` imports `get_state_path` from `openclaw.config`. No re-export shim needed — CONTEXT.md says hard swap with no deprecation.

### Anti-Patterns to Avoid

- **`Path(__file__)` for root discovery:** Resolves to install location, not project root. Never use `Path(__file__).parent.parent.parent` to find project root.
- **Implicit active-project fallback in path functions:** CONTEXT.md locks `get_state_path(project_id)` as required arg. No `Optional[str] = None` default.
- **Re-exporting removed functions from project_config.py:** Hard swap means callers update their imports. No compatibility shims.
- **Checking `OPENCLAW_STATE_FILE` in `get_snapshot_dir()`:** Only `get_state_path()` respects `OPENCLAW_STATE_FILE` — snapshot dir has no equivalent env var, always derived from root.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path resolution | Custom traversal or registry | `OPENCLAW_ROOT` env var + `Path.home()` fallback | Already proven in production; matches entrypoint.sh |
| Constants registry | Plugin system / config class | Module-level vars in config.py | Zero complexity, already the project pattern |

**Key insight:** This phase is eliminating hand-rolled solutions, not adding them. The duplication itself is the anti-pattern being removed.

---

## Common Pitfalls

### Pitfall 1: The `project_config._find_project_root()` Bug is Real

**What goes wrong:** Without `OPENCLAW_ROOT` set, `project_config._find_project_root()` returns `packages/orchestration/src` (not the project root). `get_state_path()` currently lives in `project_config.py` and calls `_find_project_root()`, so it returns `packages/orchestration/src/workspace/.openclaw/<id>/workspace-state.json` — a path that does not exist on disk.

**Why it doesn't crash in production:** `OPENCLAW_ROOT=~/.openclaw` is set in the shell environment before running any openclaw commands (required by Makefile — `make dashboard` errors if not set).

**How to avoid:** New `_find_project_root()` in `config.py` must use `Path.home() / ".openclaw"` as fallback, NOT `Path(__file__).parent.*`. Verify with a unit test that checks the fallback without env var set.

**Warning signs:** Tests that pass with env var set but fail without it. Test suite should include a test that temporarily unsets `OPENCLAW_ROOT` and calls `get_state_path("testproject")` — should return `~/.openclaw/workspace/.openclaw/testproject/workspace-state.json`.

### Pitfall 2: Container Path vs Host Path in spawn.py

**What goes wrong:** `get_state_path(project_id)` returns the **host** path (`~/.openclaw/workspace/.openclaw/<id>/workspace-state.json`). The container needs the **container-internal** path (`/workspace/.openclaw/<id>/workspace-state.json`). If spawn.py naively injects `get_state_path(project_id)` as `OPENCLAW_STATE_FILE` without translation, the container gets a host path it cannot reach.

**Why it happens:** The mount creates an alias: host `~/workspace/.openclaw` → container `/workspace/.openclaw`. The mapping is implicit in the volumes dict.

**How to avoid:** In spawn.py, compute the container-side state path separately from the host-side path. The container path can be derived from `get_state_path(project_id)` by replacing the host prefix with `/workspace/.openclaw`. OR keep the current hardcoded container path `f"/workspace/.openclaw/{project_id}/workspace-state.json"` and separately use `get_state_path(project_id)` for host-side operations (creating JarvisState, writing soul files).

**Recommendation:** Introduce a helper or inline comment that makes the host↔container path mapping explicit. Both paths come from the same logical directory, just accessed via different mount points.

### Pitfall 3: test_spawn_memory.py Imports MEMORY_CONTEXT_BUDGET from spawn

**What goes wrong:** `test_spawn_memory.py` line 25 imports `MEMORY_CONTEXT_BUDGET` directly from `spawn`:
```python
from spawn import (
    ...
    MEMORY_CONTEXT_BUDGET,
    ...
)
```

After moving `MEMORY_CONTEXT_BUDGET` to `config.py`, this import will break unless spawn.py re-exports it or the test is updated.

**How to avoid:** In spawn.py, after importing from config, add a module-level alias:
```python
from openclaw.config import MEMORY_CONTEXT_BUDGET  # noqa: F401 — re-exported for test compatibility
```
OR update `test_spawn_memory.py` to import from `openclaw.config` directly. Given the "hard swap" migration strategy, updating the test is cleaner.

### Pitfall 4: pool.py Imports project_config Functions That Will Move

**What goes wrong:** pool.py line 36:
```python
from openclaw.project_config import get_active_project_id, get_workspace_path, get_state_path, get_pool_config, get_memu_config, get_snapshot_dir
```

After `get_state_path` and `get_snapshot_dir` move to `config.py`, this import breaks.

**How to avoid:** Update pool.py's import to split across two modules:
```python
from openclaw.config import get_state_path, get_snapshot_dir, DEFAULT_POOL_MAX_CONCURRENT, ...
from openclaw.project_config import get_active_project_id, get_workspace_path, get_pool_config, get_memu_config
```

### Pitfall 5: monitor.py _discover_projects() Is Not a Public API

**What goes wrong:** `_discover_projects()` in monitor.py is an internal function — not imported by other modules. But it currently builds state file paths inline using its own `root = Path(__file__).parent.parent`. After this phase, it must use `config.get_state_path()` per-project.

**How to avoid:** Replace the inline path construction in `_discover_projects()`:
```python
# Before:
state_file = root / "workspace" / ".openclaw" / entry.name / "workspace-state.json"

# After:
from openclaw.config import get_state_path, _find_project_root
state_file = get_state_path(entry.name)
root = _find_project_root()   # still needed for projects_dir enumeration
```

### Pitfall 6: Constants Naming Collision

**What goes wrong:** `pool.py` has `_POOL_DEFAULTS` and `project_config.py` has `_POOL_CONFIG_DEFAULTS` — different names for the same thing. If both are replaced with `config.DEFAULT_POOL_*` constants, any tests that patch `pool._POOL_DEFAULTS` will break.

**How to avoid:** Search for any test patches of `_POOL_DEFAULTS` or `_POOL_CONFIG_DEFAULTS` before removing them. Currently no such patches found in the test suite (verified by grep).

---

## Code Examples

Verified from codebase inspection:

### Current config.py (complete — shows what already exists)

```python
# packages/orchestration/src/openclaw/config.py (current)
import os

LOCK_TIMEOUT = 5
LOCK_RETRY_ATTEMPTS = 3
POLL_INTERVAL = 1.0
CACHE_TTL_SECONDS = 5.0
LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()
ACTIVITY_LOG_MAX_ENTRIES = int(os.environ.get("OPENCLAW_ACTIVITY_LOG_MAX", "100"))
```

### Target config.py additions

```python
# New additions for Phase 45
from pathlib import Path
from typing import Optional

def _find_project_root() -> Path:
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        return Path(env_root)
    return Path.home() / ".openclaw"

def get_state_path(project_id: str) -> Path:
    env_state = os.environ.get("OPENCLAW_STATE_FILE")
    if env_state:
        return Path(env_state)
    root = _find_project_root()
    return root / "workspace" / ".openclaw" / project_id / "workspace-state.json"

def get_snapshot_dir(project_id: str) -> Path:
    root = _find_project_root()
    return root / "workspace" / ".openclaw" / project_id / "snapshots"

# Pool defaults
DEFAULT_POOL_MAX_CONCURRENT = 3
DEFAULT_POOL_MODE = "shared"
DEFAULT_POOL_OVERFLOW_POLICY = "wait"
DEFAULT_POOL_QUEUE_TIMEOUT_S = 300
DEFAULT_POOL_RECOVERY_POLICY = "mark_failed"

# Memory injection
MEMORY_CONTEXT_BUDGET = 2000  # Hard cap in chars for injected memory section
```

### project_config.py get_pool_config() after migration

```python
# project_config.py — get_pool_config() updated to use config constants
from .config import (
    DEFAULT_POOL_MAX_CONCURRENT,
    DEFAULT_POOL_MODE,
    DEFAULT_POOL_OVERFLOW_POLICY,
    DEFAULT_POOL_QUEUE_TIMEOUT_S,
    DEFAULT_POOL_RECOVERY_POLICY,
)

# Replace _POOL_CONFIG_DEFAULTS dict with references to config constants:
def get_pool_config(project_id: Optional[str] = None) -> Dict[str, Any]:
    defaults = {
        "max_concurrent": DEFAULT_POOL_MAX_CONCURRENT,
        "pool_mode": DEFAULT_POOL_MODE,
        "overflow_policy": DEFAULT_POOL_OVERFLOW_POLICY,
        "queue_timeout_s": DEFAULT_POOL_QUEUE_TIMEOUT_S,
        "recovery_policy": DEFAULT_POOL_RECOVERY_POLICY,
    }
    # ... rest of function unchanged
```

### pool.py after migration

```python
# pool.py — remove _POOL_DEFAULTS, import from config
from openclaw.config import (
    DEFAULT_POOL_MAX_CONCURRENT,
    DEFAULT_POOL_MODE,
    DEFAULT_POOL_OVERFLOW_POLICY,
    DEFAULT_POOL_QUEUE_TIMEOUT_S,
    DEFAULT_POOL_RECOVERY_POLICY,
    get_state_path,
    get_snapshot_dir,
)
# Remove: _POOL_DEFAULTS dict (lines 43-49)
# Replace: _POOL_DEFAULTS["overflow_policy"] → DEFAULT_POOL_OVERFLOW_POLICY
# Replace: _POOL_DEFAULTS["queue_timeout_s"] → DEFAULT_POOL_QUEUE_TIMEOUT_S
# etc.
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded paths in each module | Centralized `_find_project_root()` | Phase 45 | Eliminates root-drift bug |
| Duplicate constant dicts | Single source in `config.py` | Phase 45 | Grep for any constant hits only config.py |

**Deprecated/outdated after this phase:**
- `project_config._find_project_root()`: superseded by `config._find_project_root()`
- `project_config.get_state_path()`: superseded by `config.get_state_path()`
- `project_config.get_snapshot_dir()`: superseded by `config.get_snapshot_dir()`
- `project_config._POOL_CONFIG_DEFAULTS`: superseded by `config.DEFAULT_POOL_*`
- `pool._POOL_DEFAULTS`: superseded by `config.DEFAULT_POOL_*`
- `spawn.MEMORY_CONTEXT_BUDGET`: superseded by `config.MEMORY_CONTEXT_BUDGET`

---

## Open Questions

1. **Container path translation in spawn.py**
   - What we know: `get_state_path()` returns host path; container needs `/workspace/.openclaw/...` path
   - What's unclear: CONTEXT.md says "spawn.py calls `get_state_path(project_id)` and injects the resolved path as `OPENCLAW_STATE_FILE`" — but this would inject the host path into the container, not the container-internal path
   - Recommendation: Interpret as "spawn.py uses `get_state_path()` for host-side JarvisState creation only; keep the hardcoded container-side `OPENCLAW_STATE_FILE` injection as-is, since it's a mount alias not a real path call." Document the intentional asymmetry in a comment.

2. **Whether `_find_project_root()` should be exported (public) or internal (prefixed `_`)**
   - What we know: monitor.py needs it for `projects_dir` enumeration (enumerates the projects/ directory)
   - What's unclear: Should `_find_project_root` be a public API or remain internal with monitor using `get_state_path()` for the path parts?
   - Recommendation: Export it as a public function `get_project_root()` since monitor.py legitimately needs the root for directory enumeration, not just path construction. Then monitor.py uses `get_project_root()` for `projects_dir` and `get_state_path(entry.name)` for state files.

---

## Validation Architecture

`nyquist_validation` not set in `.planning/config.json` — skipping this section.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — all findings verified by reading actual source files
  - `~/.openclaw/packages/orchestration/src/openclaw/config.py` — current constants
  - `~/.openclaw/packages/orchestration/src/openclaw/project_config.py` — divergent resolver + duplicated pool defaults
  - `~/.openclaw/skills/spawn/spawn.py` — divergent resolver (lines 131, 433) + MEMORY_CONTEXT_BUDGET
  - `~/.openclaw/packages/orchestration/src/openclaw/cli/monitor.py` — divergent resolver (line 65)
  - `~/.openclaw/docker/l3-specialist/entrypoint.sh` — container-side OPENCLAW_STATE_FILE usage
  - `~/.openclaw/packages/orchestration/tests/test_spawn_memory.py` — import of MEMORY_CONTEXT_BUDGET (line 25)
  - `~/.openclaw/packages/orchestration/tests/conftest.py` — test infrastructure
- Runtime verification via `python3 -c` path resolution checks

### Secondary (MEDIUM confidence)
- None needed — phase is internal refactoring with no external library dependencies

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; Python stdlib only
- Architecture: HIGH — paths verified by runtime Python evaluation; divergence confirmed
- Pitfalls: HIGH — discovered by direct code inspection; import dependencies verified

**Research date:** 2026-02-25
**Valid until:** Indefinite — codebase-derived findings don't expire until code changes
