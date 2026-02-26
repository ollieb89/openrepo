# Architecture Research

**Domain:** AI Swarm Orchestration — v1.5 Config Consolidation Integration
**Researched:** 2026-02-25
**Confidence:** HIGH — based on direct codebase analysis of all integration points

---

## Context: What This Document Covers

This document is scoped exclusively to v1.5 feature integration. It describes how config
consolidation (CONF-01..07), Docker health checks (REL-09), cosine threshold calibration
(QUAL-07), and adaptive monitor polling (OBS-05) fit into the existing architecture.

For each feature: what to create new, what to modify surgically, and what to leave untouched.

### Existing Components (Reference Baseline)

| Component | File | Current Role |
|-----------|------|-------------|
| JarvisState | `packages/orchestration/src/openclaw/state_engine.py` | Cross-container state sync |
| project_config.py | `packages/orchestration/src/openclaw/project_config.py` | Path resolution, pool config loading |
| config.py | `packages/orchestration/src/openclaw/config.py` | Runtime constants (LOCK_TIMEOUT, POLL_INTERVAL, etc.) |
| config_validator.py | `packages/orchestration/src/openclaw/config_validator.py` | project.json + agent hierarchy validation |
| monitor.py | `packages/orchestration/src/openclaw/cli/monitor.py` | CLI monitor with fixed 1s poll interval |
| spawn.py | `skills/spawn/spawn.py` | L3 container spawning |
| pool.py | `skills/spawn/pool.py` | Per-project pool management |
| Dockerfile | `docker/l3-specialist/Dockerfile` | L3 container image — no HEALTHCHECK |
| entrypoint.sh | `docker/l3-specialist/entrypoint.sh` | L3 task execution with SIGTERM trap |
| openclaw.json | `config/openclaw.json` | App-level config: agents, gateway, memory, active_project |
| project.json | `projects/<id>/project.json` | Per-project: workspace, tech_stack, l3_overrides |

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENCLAW HOST (Ubuntu 24.04)                         │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Config Layer (v1.5 focus)                                             │  │
│  │                                                                         │  │
│  │  openclaw.json ──► openclaw_config.py (NEW: schema + migration)       │  │
│  │       │            └── validate_on_startup() — fail-fast              │  │
│  │       │                                                                │  │
│  │  project.json ──► project_config.py (MODIFY: use path_resolver)      │  │
│  │       │            └── validate_on_startup()                           │  │
│  │       │                                                                │  │
│  │  constants.py (NEW) ──► replaces config.py (DEPRECATE)               │  │
│  │       │            └── single source for LOCK_TIMEOUT, POLL_INTERVAL  │  │
│  │       │                                                                │  │
│  │  path_resolver.py (NEW) ──► authoritative workspace path resolution   │  │
│  │                 └── used by: spawn.py, pool.py, project_config.py,    │  │
│  │                              state_engine.py, monitor.py              │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Orchestration Layer                                                    │  │
│  │  pool.py ──► spawn.py                                                  │  │
│  │    │         └── L3 containers with HEALTHCHECK (REL-09)              │  │
│  │    │                                                                    │  │
│  │  monitor.py (MODIFY: adaptive polling — OBS-05)                        │  │
│  │    └── idle: 5s interval, active: 0.5s interval                       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  L3 Containers (openclaw-{project}-l3-{task})                          │  │
│  │  Dockerfile HEALTHCHECK: curl -f /health || exit 1                    │  │
│  │  entrypoint.sh: writes health sentinel file on startup                │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Memory + Dashboard (unchanged by v1.5)                                │  │
│  │  memU :18791 │ occc Next.js :6987                                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Integration Analysis

### Feature 1: Config Consolidation (CONF-01..07)

**Problem being solved:**

The existing codebase has config fragmentation:
- `config.py` holds runtime constants (POLL_INTERVAL, LOCK_TIMEOUT, CACHE_TTL_SECONDS, ACTIVITY_LOG_MAX_ENTRIES)
- `project_config.py` holds pool config defaults (`_POOL_CONFIG_DEFAULTS`) — duplicated in `pool.py` (`_POOL_DEFAULTS`)
- `project_config.py:_find_project_root()` resolves the root via env var + file traversal, but `monitor.py:_discover_projects()` uses a different resolution: `Path(__file__).parent.parent` (resolves relative to monitor.py file location, not OPENCLAW_ROOT)
- Workspace paths: `project_config.py:get_state_path()` returns `<root>/workspace/.openclaw/<project_id>/workspace-state.json`, but `data/workspace/` is where runtime data actually lives (noted as known limitation in PROJECT.md)
- `openclaw.json` schema: no formal JSON Schema, validation is only for `agents.list` hierarchy
- `project.json` validation: requires `workspace` + `tech_stack` but does not validate `workspace` is an existing path
- Constants are scattered: `MEMORY_CONTEXT_BUDGET = 2000` hardcoded in `spawn.py`, `_RETRIEVE_TIMEOUT` hardcoded in `spawn.py`, pool defaults duplicated in `project_config.py` and `pool.py`

**Integration points:**

```
CONF-01: Single authoritative workspace path resolver
  New: packages/orchestration/src/openclaw/path_resolver.py
  Modified: project_config.py (call path_resolver instead of building paths inline)
  Modified: monitor.py:_discover_projects() (call path_resolver instead of Path(__file__)...)
  Modified: state_engine.py (if any paths are built inline — currently takes path as argument, OK)
  Modified: spawn.py (verify it uses get_state_path() consistently — currently does via project_config)

CONF-02: openclaw.json schema cleanup + documented validation
  Modified: config_validator.py (add validate_openclaw_config() function)
  Modified: project_config.py:load_and_validate_openclaw_config() (call new validator)
  New: config/openclaw.schema.json (JSON Schema for documentation + external tools)
  No change to openclaw.json itself — schema must accept the current structure

CONF-03: Migration CLI
  New: packages/orchestration/src/openclaw/cli/migrate_config.py (already exists at migrate_state.py — check)
  Expose as: openclaw-migrate entry point in pyproject.toml

CONF-04: Env var precedence documented + enforced
  Modified: project_config.py (audit all os.environ.get() calls, document precedence order)
  Env vars in use: OPENCLAW_ROOT, OPENCLAW_PROJECT, OPENCLAW_LOG_LEVEL, OPENCLAW_ACTIVITY_LOG_MAX
  No code structure change needed — precedence is already implemented, needs documentation + test

CONF-05: Constants consolidated
  New: packages/orchestration/src/openclaw/constants.py
    — moves all values from config.py
    — adds MEMORY_CONTEXT_BUDGET (from spawn.py)
    — resolves _POOL_CONFIG_DEFAULTS duplication (project_config.py vs pool.py)
  Modified: config.py → thin re-export shim (backward compat, add deprecation comment)
  Modified: spawn.py (import MEMORY_CONTEXT_BUDGET from constants)
  Modified: pool.py (import _POOL_DEFAULTS from constants)

CONF-06: Strict fail-fast startup validation
  Modified: project_config.py:load_project_config() — already calls validate_project_config()
  Modified: project_config.py:load_and_validate_openclaw_config() — call new validate_openclaw_config()
  New behavior: both raise ConfigValidationError on missing required fields (already true for project.json)
  New: validate_openclaw_config() validates: source_directories is list, gateway.port is int, memory.memu_api_url is string

CONF-07: Config integration test suite
  New: packages/orchestration/tests/test_config_integration.py
    — tests path resolver with various OPENCLAW_ROOT values
    — tests validate_openclaw_config() against valid + invalid fixtures
    — tests validate_project_config() edge cases
    — tests env var precedence: OPENCLAW_PROJECT > active_project
    — tests migration CLI with synthetic old-format config
```

**Key architectural decision for CONF-01 — path resolver:**

The core path divergence is `<root>/workspace/` in code vs `data/workspace/` at runtime.
Resolution: `path_resolver.py` must read the actual data directory from config, not assume a
hardcoded `workspace/` subdirectory. The `OPENCLAW_ROOT` env var (or `_find_project_root()`)
gives the repo root; the state/snapshot files should live under a configurable `data_dir`
(default: `<root>/workspace/`).

```python
# path_resolver.py
def get_state_file(project_id: str) -> Path:
    """Single authoritative path for workspace-state.json."""
    root = _get_openclaw_root()
    data_dir = _get_data_dir(root)  # reads from config or defaults to root/workspace
    return data_dir / ".openclaw" / project_id / "workspace-state.json"

def _get_data_dir(root: Path) -> Path:
    """Reads openclaw.json data_dir field, falls back to root/workspace."""
    # This resolves the runtime data vs code-resolved path divergence
    cfg = _load_openclaw_config_cached(root)
    return Path(cfg.get("data_dir", str(root / "workspace")))
```

This means:
- `openclaw.json` gets an optional `data_dir` field (CONF-02 schema cleanup adds this)
- All path-building code in `project_config.py` delegates to `path_resolver.py`
- `monitor.py:_discover_projects()` uses `path_resolver.get_state_file(project_id)` instead of `Path(__file__).parent.parent / "workspace"...`

---

### Feature 2: Docker Health Checks (REL-09)

**Problem being solved:**

L3 containers have no HEALTHCHECK in the Dockerfile. Docker reports them as healthy by
default (no health status). Pool.py cannot distinguish "container started but CLI not ready"
from "container fully initialized." Dashboard container list has no health indicators.

**Integration points:**

```
Dockerfile:
  Add HEALTHCHECK instruction pointing to a sentinel file written by entrypoint.sh
  Strategy: file-based (not HTTP) because L3 containers have no HTTP server

  HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD test -f /tmp/openclaw-healthy || exit 1

entrypoint.sh:
  Write sentinel file after successful startup checks (after staging branch creation,
  before task execution):
    touch /tmp/openclaw-healthy

  Remove sentinel on SIGTERM handler (signals unhealthy to Docker):
    rm -f /tmp/openclaw-healthy

spawn.py (optional):
  After container.run() returns container object, optionally poll container.health
  for container readiness before marking as started in JarvisState. This is low-priority —
  current behavior (immediate status update) is acceptable.

Dashboard:
  The occc containers endpoint already returns container data from docker.containers.list().
  Docker SDK container.attrs['State']['Health']['Status'] gives: 'healthy', 'unhealthy',
  'starting', or absent (no healthcheck). Add health status to the API response and render
  it as a badge in the container list component.
```

**Minimal viable approach (recommended):**

Phase this feature:
1. Dockerfile + entrypoint.sh changes only — gives Docker daemon health visibility
2. Dashboard health badge — surface it in the container list

Skipping spawn.py readiness-wait: The current spawn flow updates JarvisState immediately
after `container.run()` returns. Waiting for health=healthy before updating state adds
latency and complexity (needs a polling loop with timeout). Not worth it — the SIGTERM
behavior and state engine already handle failure recovery.

**Modified files:**
- `docker/l3-specialist/Dockerfile` — add `HEALTHCHECK` instruction
- `docker/l3-specialist/entrypoint.sh` — `touch /tmp/openclaw-healthy` after staging branch setup
- `packages/dashboard/src/app/api/swarm/` — return `healthStatus` field in container response
- `packages/dashboard/src/components/` — add health badge to container row

**New files:** None required.

---

### Feature 3: Cosine Similarity Threshold Calibration (QUAL-07)

**Problem being solved:**

The v1.4 memory conflict detection uses a hardcoded cosine similarity threshold of 0.92
(noted in PROJECT.md as "Revisit — threshold needs empirical tuning under real workload").
At 0.92, true duplicates (exact rewrites) are caught but near-conflicts (contradictory
advice phrased differently) may be missed. At too low a threshold (e.g., 0.7), unrelated
memories with similar domain vocabulary generate false positives.

**Integration points:**

The threshold is currently hardcoded in `orchestration/memory_health.py` (new in v1.4).
Calibration means making it configurable + providing tooling to tune it empirically.

```
constants.py (NEW via CONF-05):
  MEMORY_CONFLICT_SIMILARITY_THRESHOLD = 0.92  # current default
  MEMORY_STALENESS_DAYS = 30                   # current default

openclaw.json (CONF-02 schema addition):
  "memory": {
    "memu_api_url": "http://localhost:18791",
    "conflict_threshold": 0.92,   # optional, defaults to constant
    "staleness_days": 30          # optional, defaults to constant
  }

project_config.py (new helper):
  def get_memory_health_config() -> Dict[str, Any]:
      """Read conflict_threshold and staleness_days from openclaw.json memory section."""
      # reads memory{} stanza, falls back to constants.py values

memory_health.py (MODIFY):
  Accept threshold as parameter (not hardcoded):
    def run_checks(project_id, conflict_threshold=None, staleness_days=None):
        cfg = get_memory_health_config()
        threshold = conflict_threshold or cfg["conflict_threshold"]
        ...

Calibration tooling (CONF-07 test suite can include):
  New: packages/orchestration/tests/fixtures/memory_calibration/
    — synthetic memory items with known conflict/non-conflict pairs
    — test that default threshold correctly classifies them
    — provides a basis for empirical tuning against real memU data
```

**Calibration workflow (operational, not code):**

1. Run memory_health.py with threshold 0.85 against real memU data → count flagged pairs
2. Manual inspection of flagged pairs → calculate precision (true conflicts / flagged)
3. Repeat with 0.88, 0.92, 0.95 → pick threshold where precision > 80%
4. Update `openclaw.json memory.conflict_threshold` to calibrated value
5. Update constant default to match empirical finding

This is an operational concern, not a pure code concern. The code change is: make threshold
configurable. The calibration itself happens at runtime.

**Modified files:**
- `packages/orchestration/src/openclaw/constants.py` (new, as part of CONF-05)
- `packages/orchestration/src/openclaw/project_config.py` — add `get_memory_health_config()`
- `packages/orchestration/src/openclaw/memory_health.py` — accept threshold as parameter
- `config/openclaw.json` — add optional `conflict_threshold` + `staleness_days` to memory stanza

**New files:** `packages/orchestration/tests/fixtures/memory_calibration/` (test fixtures)

---

### Feature 4: Adaptive Monitor Polling (OBS-05)

**Problem being solved:**

`monitor.py:tail_state()` polls at a fixed 1-second interval (from `config.POLL_INTERVAL`).
When the swarm is idle (no active tasks), this wastes CPU and generates noisy debug logs.
When the swarm is busy, 1 second may feel slow for real-time visibility.

**Integration points:**

The adaptive logic belongs entirely within `tail_state()` in `monitor.py`. No other
components need to change.

```
monitor.py:tail_state() — MODIFY:

Current: fixed time.sleep(interval)

New: adaptive interval based on detected activity

def _compute_adaptive_interval(
    last_seen_active: Optional[float],    # timestamp of last observed in_progress/starting task
    current_active_count: int,            # tasks currently in active statuses
    base_interval: float,                 # from constants.POLL_INTERVAL (1.0s)
    fast_interval: float,                 # from constants.POLL_INTERVAL_ACTIVE (0.5s)
    idle_interval: float,                 # from constants.POLL_INTERVAL_IDLE (5.0s)
    cooldown_seconds: float = 10.0,       # stay fast for N seconds after last active task
) -> float:
    if current_active_count > 0:
        return fast_interval
    if last_seen_active and (time.time() - last_seen_active) < cooldown_seconds:
        return base_interval   # cooldown: just finished, stay at normal speed
    return idle_interval       # truly idle

constants.py (NEW):
  POLL_INTERVAL = 1.0           # base (current behavior)
  POLL_INTERVAL_ACTIVE = 0.5    # fast mode: active tasks detected
  POLL_INTERVAL_IDLE = 5.0      # idle mode: no tasks for > cooldown_seconds

config.py (MODIFY: re-export from constants, add new names):
  from .constants import POLL_INTERVAL, POLL_INTERVAL_ACTIVE, POLL_INTERVAL_IDLE
```

**State tracking needed in tail_state():**

```python
# Within the while True loop:
total_active = sum(
    1 for proj_id, _ in projects
    for task in js_instances.get(proj_id, ...)
    if task.get("status") in ACTIVE_STATUSES
)
if total_active > 0:
    last_seen_active = time.time()

interval = _compute_adaptive_interval(last_seen_active, total_active, ...)
time.sleep(interval)
```

This is self-contained — no changes to JarvisState, spawn.py, or pool.py.

**Modified files:**
- `packages/orchestration/src/openclaw/constants.py` (new, as part of CONF-05)
- `packages/orchestration/src/openclaw/cli/monitor.py` — adaptive interval logic in `tail_state()`
- `packages/orchestration/src/openclaw/config.py` — re-export new constants (backward compat)

**New files:** None.

---

## Component Boundaries

### New Components (create from scratch)

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `path_resolver.py` | Single authoritative resolver for all runtime data paths (state files, snapshot dirs, health reports, soul files) | `packages/orchestration/src/openclaw/path_resolver.py` |
| `constants.py` | All module-level constants consolidated: timeouts, intervals, memory budget, pool defaults, threshold defaults | `packages/orchestration/src/openclaw/constants.py` |
| `openclaw.schema.json` | JSON Schema for openclaw.json — documents required fields, optional fields, types | `config/openclaw.schema.json` |
| `test_config_integration.py` | Integration tests: path resolution, validation, env var precedence, migration | `packages/orchestration/tests/test_config_integration.py` |
| `migrate_config.py` | CLI subcommand: detect old config shape, produce upgraded version with new optional fields | `packages/orchestration/src/openclaw/cli/migrate_config.py` |

Note: `migrate_state.py` already exists at `packages/orchestration/src/openclaw/cli/migrate_state.py` —
the config migration is a separate file scoped to `openclaw.json` and `project.json` format upgrades.

### Modified Components (surgical changes only)

| Component | What Changes | Risk |
|-----------|-------------|------|
| `config.py` | Becomes a thin re-export shim pointing to `constants.py` — backward compat preserved | LOW — additive deprecation only |
| `config_validator.py` | Add `validate_openclaw_config()` for openclaw.json fields (source_directories, gateway.port, memory stanza) | LOW — additive |
| `project_config.py` | Path-building calls delegate to `path_resolver.py`; add `get_memory_health_config()` | MEDIUM — path resolution is used everywhere; requires careful testing |
| `monitor.py` | Adaptive interval in `tail_state()`; use `path_resolver.get_state_file()` in `_discover_projects()` | LOW — self-contained logic change |
| `spawn.py` | Import `MEMORY_CONTEXT_BUDGET` from `constants.py` instead of inline | LOW — pure import change |
| `pool.py` | Import `_POOL_DEFAULTS` from `constants.py` instead of inline | LOW — pure import change |
| `memory_health.py` | Accept `conflict_threshold` as parameter; read from `get_memory_health_config()` | LOW — additive parameter |
| `docker/l3-specialist/Dockerfile` | Add `HEALTHCHECK` instruction | LOW — additive |
| `docker/l3-specialist/entrypoint.sh` | `touch /tmp/openclaw-healthy` after staging branch setup; `rm -f` in SIGTERM handler | LOW — minimal bash change |
| `config/openclaw.json` | Add optional `data_dir`, `memory.conflict_threshold`, `memory.staleness_days` fields | LOW — backward compatible additions |
| Dashboard containers component | Add `healthStatus` badge to container row | LOW — additive UI |

### Untouched Components

| Component | Why Untouched |
|-----------|---------------|
| `state_engine.py` | Takes path as constructor argument — not responsible for path resolution |
| `snapshot.py` | Path passed from caller — unaffected by path resolver refactor |
| `soul_renderer.py` | Already reads workspace from project config via correct path |
| `memory_client.py` | HTTP client only — no filesystem paths |
| `memory_health.py` (algorithm) | Logic unchanged — only threshold becomes configurable |
| `suggestion_engine.py` | Reads from JarvisState + memU — no path changes needed |
| Dashboard pages | `/memory`, `/settings` — only containers list gets health badge |

---

## Data Flows

### Flow 1: Config Load (CONF-01, CONF-06)

```
Process startup (spawn.py, pool.py, monitor.py)
    ↓
import project_config  →  load_and_validate_openclaw_config()
    ├── open config/openclaw.json
    ├── validate_openclaw_config() — fail-fast on missing required fields
    │   (source_directories: list, gateway.port: int, memory.memu_api_url: str)
    └── validate_agent_hierarchy() — existing
    ↓
get_active_project_id() → OPENCLAW_PROJECT env var (priority) OR active_project field
    ↓
load_project_config(project_id)
    ├── open projects/<id>/project.json
    ├── validate_project_config() — fail-fast (existing behavior)
    └── validate workspace path exists (new: CONF-06)
    ↓
path_resolver.get_state_file(project_id)
    ├── reads data_dir from openclaw.json (or defaults to <root>/workspace)
    └── returns authoritative Path for workspace-state.json
```

### Flow 2: Adaptive Monitor Poll (OBS-05)

```
monitor.py tail_state() starts
    ↓
POLL intervals loaded from constants.py (1.0s, 0.5s, 5.0s)
    ↓
while True:
    poll all projects → read JarvisState
    count active tasks across all projects
    if active > 0:
        last_seen_active = now
    ↓
    _compute_adaptive_interval(last_seen_active, active_count, ...)
    → active > 0: 0.5s
    → active == 0 and now - last_seen_active < 10s: 1.0s (cooldown)
    → active == 0 and cooldown expired: 5.0s
    ↓
    time.sleep(computed_interval)
```

### Flow 3: Docker Health Check (REL-09)

```
spawn_l3_specialist() called
    ↓
container.run(...) → container started
    ↓
Docker daemon runs HEALTHCHECK every 10s:
    test -f /tmp/openclaw-healthy
    start-period: 15s (no checks while container initializes)
    retries: 3 before marking unhealthy
    ↓
entrypoint.sh executes:
    setup → git checkout staging branch → touch /tmp/openclaw-healthy → execute task
    (Health = starting → healthy after first successful check)
    ↓
SIGTERM received → rm -f /tmp/openclaw-healthy
    (Docker marks container as unhealthy if SIGTERM arrives before task completion)
    ↓
Dashboard:
    GET /api/swarm/containers → Docker SDK container.attrs['State']['Health']['Status']
    → render badge: healthy (green), starting (yellow), unhealthy (red), none (grey)
```

### Flow 4: Threshold-Configurable Conflict Detection (QUAL-07)

```
Dashboard loads /memory → GET /api/memory/health?project=pumplai
    ↓
API route calls memory_health.run_checks(project_id)
    ↓
memory_health.run_checks():
    cfg = get_memory_health_config(project_id)
    threshold = cfg["conflict_threshold"]  # from openclaw.json or constant default
    staleness_days = cfg["staleness_days"]
    ↓
    run conflict scan with threshold
    → pairs with cosine similarity > threshold flagged as conflicts
    ↓
return HealthReport with flagged pairs
```

---

## Build Order (Phase Dependencies)

Features are largely independent but share the constants.py and path_resolver.py foundations.
Build the foundation first to avoid repeated partial changes.

```
Phase 1: Constants + Path Resolver (CONF-05, CONF-01 foundation)
  WHY FIRST: Foundation that all other phases depend on.
              Resolve _POOL_DEFAULTS duplication, move MEMORY_CONTEXT_BUDGET,
              create path_resolver.py, update project_config.py to use it.
  Touches: constants.py (new), path_resolver.py (new), config.py (shim),
           project_config.py (delegate to path_resolver), spawn.py (import),
           pool.py (import), monitor.py (use path_resolver in _discover_projects)
  Test: existing 148 tests still pass

Phase 2: openclaw.json Schema + Validation (CONF-02, CONF-04, CONF-06)
  WHY SECOND: Depends on constants.py (threshold defaults); adds validation layer.
  Touches: config_validator.py (+validate_openclaw_config), project_config.py
           (+validate workspace path), openclaw.json (+data_dir, +memory.conflict_threshold),
           openclaw.schema.json (new)
  Test: validation tests against good/bad openclaw.json fixtures

Phase 3: Threshold Calibration (QUAL-07)
  WHY THIRD: Depends on constants.py (MEMORY_CONFLICT_SIMILARITY_THRESHOLD) and
              validate_openclaw_config() (new memory stanza fields from Phase 2).
  Touches: project_config.py (+get_memory_health_config), memory_health.py (parameterize threshold)
  Test: calibration fixture tests; verify behavior unchanged at default threshold

Phase 4: Docker Health Checks (REL-09)
  WHY FOURTH: Self-contained Dockerfile + entrypoint.sh change; no Python dependencies.
              Fourth to allow prior phases to stabilize before adding container rebuild cost.
  Touches: Dockerfile (+HEALTHCHECK), entrypoint.sh (+touch/rm sentinel), dashboard containers API
  Test: spawn container → wait 15s → verify Docker reports healthy

Phase 5: Adaptive Monitor Polling (OBS-05)
  WHY FIFTH: Depends on constants.py (new POLL_INTERVAL_ACTIVE, POLL_INTERVAL_IDLE from Phase 1).
  Touches: monitor.py (adaptive interval logic), constants.py (add new interval constants)
  Test: simulate 0 tasks → verify 5s sleep; simulate 1 active task → verify 0.5s sleep

Phase 6: Migration CLI + Integration Test Suite (CONF-03, CONF-07)
  WHY LAST: Tests verify the whole config layer end-to-end; migration CLI can reference
             final schema. No other phases depend on this.
  Touches: migrate_config.py (new), test_config_integration.py (new)
  Test: migrate synthetic old config → verify output matches new schema
```

---

## Architectural Patterns

### Pattern 1: Thin Re-Export Shim for Backward Compatibility

**What:** `config.py` becomes `from .constants import *` with deprecation comment.
All existing importers (`from openclaw.config import POLL_INTERVAL`) continue to work
without change. New code imports from `constants.py`.

**When to use:** When consolidating constants from a module with many existing importers.

**Trade-offs:** Two-file indirection temporarily. Deprecation removed in a future cleanup.

```python
# config.py (after)
"""
Backward-compatible re-export. New code should import from openclaw.constants.
This module will be removed in a future version.
"""
from .constants import (  # noqa: F401
    LOCK_TIMEOUT,
    LOCK_RETRY_ATTEMPTS,
    POLL_INTERVAL,
    POLL_INTERVAL_ACTIVE,
    POLL_INTERVAL_IDLE,
    CACHE_TTL_SECONDS,
    LOG_LEVEL,
    ACTIVITY_LOG_MAX_ENTRIES,
    MEMORY_CONTEXT_BUDGET,
    MEMORY_CONFLICT_SIMILARITY_THRESHOLD,
    MEMORY_STALENESS_DAYS,
)
```

### Pattern 2: File-Based Docker HEALTHCHECK

**What:** Write a sentinel file `touch /tmp/openclaw-healthy` after successful L3 container
initialization. HEALTHCHECK uses `test -f` which requires no additional tools beyond core
utilities. Remove the sentinel on SIGTERM.

**When to use:** When containers have no HTTP endpoint to health-check against.

**Trade-offs:** Simpler than HTTP health endpoint. Does not validate that the CLI runtime
is still functioning mid-task — only that initialization succeeded. Acceptable for L3 ephemeral
containers where mid-task failure is handled by the state engine, not Docker.

```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD test -f /tmp/openclaw-healthy || exit 1
```

### Pattern 3: Configurable Thresholds with Constant Defaults

**What:** Algorithm thresholds (cosine similarity, staleness days) live in `constants.py`
as defaults. `openclaw.json` can override them via the `memory` stanza. Runtime code reads
from config first, falls back to constant.

**When to use:** When a threshold needs empirical tuning per deployment but has a reasonable
default.

**Trade-offs:** Adds a config read to the hot path (health checks). Mitigated by the existing
server-side cache on the health endpoint. Never raises — always returns a usable value.

### Pattern 4: Activity-Bounded Adaptive Polling

**What:** Monitor poll interval scales inversely with activity: fast when tasks are running,
slow when idle, with a cooldown period to stay responsive right after task completion.

**When to use:** Long-running polling loops where activity is bursty (quiet most of the time,
intense during task execution windows).

**Trade-offs:** Adds minor state tracking (last_seen_active timestamp) to the poll loop.
No external dependencies. The cooldown prevents flapping between fast/slow during rapid
task transitions.

---

## Anti-Patterns

### Anti-Pattern 1: Building Paths in Multiple Places

**What people do:** Each module computes `Path(__file__).parent.parent / "workspace"` inline.

**Why it's wrong:** The v1.5 root cause: `monitor.py` builds paths relative to its own file
location (`Path(__file__).parent.parent`), which points to the orchestration package root —
not `OPENCLAW_ROOT`. When `OPENCLAW_ROOT` is `/home/ollie/.openclaw` but monitor.py is at
`packages/orchestration/src/openclaw/cli/monitor.py`, the traversal resolves to
`packages/orchestration/src/openclaw/` — wrong.

**Do this instead:** All path construction goes through `path_resolver.py`. Single point of
change when data directory moves (which already happened between v1.0 and v1.4).

### Anti-Pattern 2: Duplicating Default Dictionaries Across Modules

**What people do:** `_POOL_CONFIG_DEFAULTS` defined in `project_config.py` and `_POOL_DEFAULTS`
defined in `pool.py` with the same values.

**Why it's wrong:** They diverge silently. A new key added to one is missed in the other.
The existing pool.py comment "also used by pool.py as fallback reference" acknowledges the
coupling but doesn't resolve it.

**Do this instead:** One canonical `POOL_CONFIG_DEFAULTS` dict in `constants.py`. Both
`project_config.py` and `pool.py` import from there.

### Anti-Pattern 3: Hardcoded HEALTHCHECK Start Period Too Short

**What people do:** HEALTHCHECK --start-period=5s on containers that take 15-20s to be ready.

**Why it's wrong:** Docker starts issuing health checks after start-period. If start-period
is shorter than container initialization, the first checks all fail, triggering unhealthy
state before the container is actually broken.

**Do this instead:** --start-period=15s for L3 containers. The CLI runtime (claude-code,
gemini-cli) may need several seconds to start. The staging branch checkout adds another 2-5s.
15s is conservative but safe.

### Anti-Pattern 4: Adapting Poll Interval Based on Stale State

**What people do:** Compute poll interval based on state read in the previous iteration,
not the current one.

**Why it's wrong:** If the last poll missed an activity update (e.g., state file write
was in-flight), the adaptive logic uses outdated active count and may switch to slow
polling just as a new task starts.

**Do this instead:** Compute the active count from the current poll iteration's state read,
before computing the sleep interval. `last_seen_active` tracks when we last observed
activity — interval computed fresh each cycle.

---

## File Structure Delta

```
packages/orchestration/src/openclaw/
├── constants.py                    # NEW: all module-level constants consolidated
├── path_resolver.py                # NEW: single authoritative path resolver
├── config.py                       # MODIFY: thin re-export shim from constants.py
├── config_validator.py             # MODIFY: add validate_openclaw_config()
├── project_config.py               # MODIFY: use path_resolver; add get_memory_health_config()
├── memory_health.py                # MODIFY: parameterize threshold
├── cli/
│   ├── monitor.py                  # MODIFY: adaptive poll interval; path_resolver in _discover_projects
│   └── migrate_config.py           # NEW: openclaw.json + project.json migration CLI

config/
├── openclaw.json                   # MODIFY: add data_dir, memory.conflict_threshold, memory.staleness_days
└── openclaw.schema.json            # NEW: formal JSON Schema

docker/l3-specialist/
├── Dockerfile                      # MODIFY: add HEALTHCHECK instruction
└── entrypoint.sh                   # MODIFY: touch sentinel on startup, rm on SIGTERM

packages/orchestration/tests/
├── test_config_integration.py      # NEW: path resolution, validation, env var precedence tests
└── fixtures/
    └── memory_calibration/         # NEW: synthetic memory items for threshold calibration tests

packages/dashboard/src/
└── app/api/swarm/                  # MODIFY: include healthStatus in container response
```

---

## Integration Points Summary

| Feature | New Files | Modified Files | Untouched |
|---------|-----------|----------------|-----------|
| Config Consolidation (CONF-01..07) | `constants.py`, `path_resolver.py`, `openclaw.schema.json`, `migrate_config.py`, `test_config_integration.py` | `config.py`, `config_validator.py`, `project_config.py`, `spawn.py`, `pool.py`, `monitor.py`, `openclaw.json` | `state_engine.py`, `snapshot.py`, `memory_client.py`, `soul_renderer.py` |
| Docker Health Checks (REL-09) | none | `Dockerfile`, `entrypoint.sh`, dashboard containers API/component | `pool.py`, `spawn.py`, `state_engine.py` |
| Threshold Calibration (QUAL-07) | calibration test fixtures | `memory_health.py`, `project_config.py` (+helper), `constants.py` | `memory_client.py`, dashboard, `state_engine.py` |
| Adaptive Monitor Polling (OBS-05) | none | `monitor.py`, `constants.py` (+new interval constants), `config.py` (re-export) | everything else |

---

## Scaling Considerations

This remains a single-host system. v1.5 scaling concerns are operational, not architectural:

| Concern | Impact | Notes |
|---------|--------|-------|
| Constants consolidation | Zero runtime cost | Import-time only |
| Path resolver overhead | Single extra JSON read per process start | Cached after first call |
| Adaptive polling | Reduces CPU 5x during idle | No contention risk |
| Docker HEALTHCHECK | 10s interval, negligible overhead | One `test -f` per container per interval |
| Threshold config read | One extra JSON parse per health check call | Already cached by health endpoint |

---

## Sources

- OpenClaw codebase direct analysis: `config.py`, `config_validator.py`, `project_config.py`,
  `state_engine.py`, `cli/monitor.py`, `skills/spawn/spawn.py`, `skills/spawn/pool.py`,
  `docker/l3-specialist/Dockerfile`, `docker/l3-specialist/entrypoint.sh`, `config/openclaw.json`,
  `projects/pumplai/project.json`
- PROJECT.md: v1.5 requirements CONF-01..07, REL-09, QUAL-07, OBS-05 + known limitations
- Docker HEALTHCHECK docs: `test -f` file-based check, start-period semantics (HIGH confidence)
- Python asyncio adaptive sleep: standard pattern (HIGH confidence)

---

*Architecture research for: OpenClaw v1.5 Config Consolidation*
*Researched: 2026-02-25*
