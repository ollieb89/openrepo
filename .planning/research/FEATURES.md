# Feature Research

**Domain:** AI swarm orchestration — v1.5 Config Consolidation
**Researched:** 2026-02-25
**Confidence:** HIGH (codebase analysis + verified patterns from official sources)

---

## Context: What This Milestone Adds

v1.4 shipped Operational Maturity (graceful shutdown, memory health monitoring, L1 SOUL suggestions,
delta snapshots). The system is behaviorally robust but carries config debt from four milestones of
organic growth:

1. **Path divergence** — three different root resolution strategies exist across the codebase: `project_config.py::_find_project_root()`, `spawn.py::Path(__file__).parent.parent.parent`, and `init.py::find_project_root()` (walk-up). These agree currently but can diverge silently if the package is installed somewhere unexpected.

2. **Schema not enforced at startup** — `openclaw.json` is loaded and partially validated (agent hierarchy), but many fields (gateway config, memory config, channels) have no validation at all. Bad values are silently ignored until they cause a runtime error deep in the call stack.

3. **Scattered constants** — `POLL_INTERVAL`, `LOCK_TIMEOUT`, `CACHE_TTL_SECONDS` live in `config.py`; pool defaults live in `project_config.py` (`_POOL_CONFIG_DEFAULTS`); cosine similarity thresholds live in `scan_engine.py` hardcoded; staleness thresholds live in the dashboard API handler. No single authoritative location.

4. **Three deferred items** (REL-09, QUAL-07, OBS-05) — Docker health checks, calibrated cosine threshold, and adaptive monitor polling were deferred from v1.4. They fit naturally here.

None of the four feature areas require new external services. All build on existing infrastructure.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that a production config layer must provide. Missing them = config bugs are impossible to
diagnose and easy to introduce silently.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single authoritative path resolver | All components must agree on where `workspace/`, `projects/`, `agents/` live. Divergent resolvers mean "it works on my machine" bugs that are invisible in tests | MEDIUM | Expose one `get_project_root()` function from `project_config.py`; update all callers. `spawn.py` line 433 uses `Path(__file__).parent.parent.parent` independently — this is the primary divergence point |
| Strict fail-fast startup validation for `openclaw.json` | Users expect bad config to produce a clear error message on startup, not a silent misbehavior 30 minutes later | MEDIUM | Extend `config_validator.py::validate_agent_hierarchy()` to also validate gateway port, memory.memu_api_url format, channels fields. Raise `ConfigValidationError` with actionable messages |
| Strict fail-fast startup validation for `project.json` | Same expectation — missing `workspace` or malformed `tech_stack` should fail immediately with an actionable message | LOW | `validate_project_config()` already catches `workspace` and `tech_stack`. Extend to validate `l3_overrides` required types (currently advisory warnings, promote to errors for unknown keys) |
| Constants consolidated into one module | Operators and developers should not need to hunt across three files to find timeout or threshold values | LOW | Move all defaults into `config.py`. Pool defaults from `project_config.py`, cosine thresholds from `scan_engine.py`, dashboard staleness defaults from API handler. Single import path for all tunable values |
| Env var precedence documented and enforced | `OPENCLAW_ROOT`, `OPENCLAW_PROJECT`, `OPENCLAW_LOG_LEVEL`, `OPENCLAW_ACTIVITY_LOG_MAX` have different scopes; undefined precedence order causes confusion when debugging | LOW | Document in `config.py` docstring. Enforce: env vars > config file values > coded defaults, consistently. Currently `OPENCLAW_ROOT` is checked in `_find_project_root()` but not all helpers respect it |
| Migration CLI for existing configs | Users with existing `openclaw.json` files need a non-destructive upgrade path when schema changes | MEDIUM | `openclaw-migrate --dry-run` reads existing config, reports what would change, writes new version. Not a database migration — just JSON schema normalization. Backed by the existing argparse CLI pattern |
| Config integration test suite | Regressions in path resolution and validation are silent — no test coverage verifies the resolver agrees across all call sites | MEDIUM | Tests for: path resolver agreement, validation error messages, env var override semantics, migration CLI idempotency |

### Differentiators (Competitive Advantage)

Features that improve operator trust and system reliability beyond baseline config hygiene.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Docker health checks for L3 containers | L2 and the dashboard can distinguish "container running but stuck" from "container healthy and making progress". Without HEALTHCHECK, `docker inspect` only reports if the process is alive, not if it's doing useful work | MEDIUM | Add `HEALTHCHECK` to `docker/l3-specialist/Dockerfile`. Script checks for Jarvis state file existence and last `updated_at` recency. Reports unhealthy if state has not been written in >60s. Surfaces in `docker ps` output and dashboard container list |
| Adaptive monitor poll interval | Monitor CPU usage drops to near zero during idle periods (no active L3 tasks); responsive during active periods without fixed 1s overhead across all projects | MEDIUM | Replace fixed `time.sleep(interval)` in `tail_state()` with exponential backoff: 0.5s when activity seen → step up to 5s when quiescent → back to 0.5s on any new activity. State: `consecutive_quiet_cycles` counter per project. Max interval configurable |
| Cosine similarity threshold calibration | 0.92 (near-duplicate) and 0.75 (conflict) thresholds were chosen heuristically without empirical tuning. Miscalibrated thresholds produce false positive conflict alerts (noisy) or miss real conflicts (silent quality degradation) | LOW-MEDIUM | Add a `calibrate-thresholds` sub-command to `openclaw-memory` or new `openclaw-health` CLI. Samples existing memory store, computes similarity distribution, recommends thresholds at configurable percentiles. No automatic adjustment — outputs recommended values for operator review |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-hot-reload `openclaw.json` without restart | "Config changes should take effect immediately" | `openclaw.json` contains agent hierarchy, gateway settings, and memory API URL — these are startup-time dependencies. Hot-reloading mid-run risks inconsistent state between components that have already used the old values | Pool config (`project.json l3_overrides`) already supports hot-reload via `get_pool_config()` per-call. That is the right scope. `openclaw.json` changes legitimately require restart |
| Pydantic for config validation | Type-safe, generates errors automatically | Adds an external dependency to a package that currently has no external Python deps. The existing `validate_project_config()` pattern with explicit error collection is equivalent for JSON config validation | Keep `config_validator.py` with the existing collect-all strategy. Add more validations to the existing function, not a new dependency |
| CWD-based project auto-detection | "It should just know which project I'm in" | Conflicts with scripts calling `openclaw` from arbitrary directories (cron jobs, L3 containers, CI). Accepted and locked as out of scope in PROJECT.md | `OPENCLAW_PROJECT` env var + `active_project` in `openclaw.json` is the correct mechanism. Document clearly |
| Environment-specific config files (`openclaw.prod.json`) | "Different configs for dev/prod" | Adds implicit loading order complexity; conflicts with the current explicit model | Use `${ENV_VAR}` placeholders for environment-specific values (already supported in `openclaw.json`). Document the pattern |
| Config inheritance / extends | "Base config with project-level overrides" | Two levels of override already exist (`openclaw.json` + `project.json`). A third level adds complexity without clear value for a single-host system | Per-project `l3_overrides` in `project.json` is the correct extension point. Document what belongs where |
| Automatic threshold adjustment based on scan results | "System should learn the right thresholds from data" | Thresholds affect what gets flagged — auto-adjustment creates a feedback loop where the system can drift away from useful detection without operator visibility | Calibration tool outputs recommendations; operator decides. Log the thresholds in use on every health scan run so changes are auditable |

---

## Feature Dependencies

```
[Single authoritative path resolver]
    └──required by──> [Config integration tests] (tests need consistent paths to assert against)
    └──required by──> [Startup validation] (validator needs to know where to find configs)
    └──enables──> [Migration CLI] (migration needs to find existing configs reliably)

[Constants consolidation]
    └──required by──> [Adaptive polling] (min/max interval lives in config.py)
    └──required by──> [Cosine calibration] (thresholds live in config.py, calibration tool reads + recommends)
    └──required by──> [Docker health checks] (health check timeout threshold in config.py)

[openclaw.json strict startup validation]
    └──independent of──> [project.json strict startup validation]
    └──feeds──> [Config integration tests]
    └──depends on──> [Single authoritative path resolver] (validation needs to find openclaw.json reliably)

[Migration CLI]
    └──depends on──> [Single authoritative path resolver]
    └──depends on──> [openclaw.json strict startup validation] (validates the migrated output)
    └──independent of──> [Docker health checks, adaptive polling, cosine calibration]

[Docker health checks]
    └──depends on──> [Constants consolidation] (timeout values from config.py)
    └──independent of──> [all other v1.5 features]

[Adaptive monitor polling]
    └──depends on──> [Constants consolidation] (min_poll, max_poll, backoff_factor in config.py)
    └──independent of──> [Docker health checks, cosine calibration]

[Cosine similarity threshold calibration]
    └──depends on──> [Constants consolidation] (current thresholds read from config.py)
    └──independent of──> [Docker health checks, adaptive polling]

[Config integration test suite]
    └──depends on──> [Single authoritative path resolver] (prerequisite for meaningful path tests)
    └──depends on──> [Constants consolidation] (tests verify defaults match expected values)
    └──should cover──> [Migration CLI] (migration idempotency test)
```

### Dependency Notes

- **Path resolver is the foundation** — all other config features assume there is one correct root. Build CONF-01 first. The fix is small: expose `_find_project_root()` as public API, remove the independent `Path(__file__).parent.parent.parent` calculation in `spawn.py` line 433, and update `init.py::find_project_root()` to call the canonical function instead of walking up independently.

- **Constants consolidation is the second foundation** — adaptive polling, Docker health check thresholds, and cosine calibration all need somewhere to read from. Move everything to `config.py` before building those features.

- **Startup validation and migration CLI are sequenced** — validate first (defines what valid looks like), migrate second (produces valid configs). Running them in the wrong order means the migration target is undefined.

- **Docker health checks, adaptive polling, and cosine calibration are independent** — once foundations are in place, these three can be built in any order or in parallel.

- **Config integration tests should be written last** — they verify the correctness of everything above. Writing them first as specs is useful but they cannot pass until the other features are in place.

---

## MVP Definition

### Launch With (v1.5 core — must ship for "Config Consolidation" to be true)

- [ ] CONF-01: Single authoritative path resolver — `get_project_root()` in `project_config.py`, all callers updated
- [ ] CONF-02: `openclaw.json` schema cleanup + documented fields
- [ ] CONF-03: Migration CLI (`openclaw-migrate`) — reads existing config, reports changes, writes new version
- [ ] CONF-04: Env var precedence documented and enforced consistently in `config.py`
- [ ] CONF-05: Constants/defaults consolidated into `config.py` — no duplicated magic values across modules
- [ ] CONF-06: Strict fail-fast startup validation for both config files
- [ ] CONF-07: Config integration test suite covering path resolution, validation, migration idempotency

### Add After Validation (v1.5 extension — deferred items)

- [ ] REL-09: Docker health checks for L3 containers
- [ ] QUAL-07: Cosine similarity threshold calibration tool
- [ ] OBS-05: Adaptive monitor poll interval

### Future Consideration (v2+)

- [ ] Config versioning / changelog — track which version of the schema each config file was last migrated to
- [ ] Multi-environment config support — properly scoped env var overlays with audit log
- [ ] Automatic threshold learning — only viable once enough calibration data exists across projects

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Single authoritative path resolver | HIGH — prevents silent divergence bugs | LOW — refactor, not new code | P1 |
| Constants consolidation | HIGH — prerequisite for other features, reduces DRY violations | LOW — move values, update imports | P1 |
| openclaw.json strict startup validation | HIGH — operator gets actionable error on bad config immediately | MEDIUM — extend existing validator | P1 |
| project.json strict startup validation extensions | MEDIUM — current coverage is already good for critical fields | LOW — promote warnings to errors for unknown keys | P1 |
| Env var precedence | MEDIUM — reduces debugging confusion | LOW — documentation + consistency audit | P1 |
| Migration CLI | HIGH — without it, operators have to hand-edit configs on upgrade | MEDIUM — argparse subcommand + JSON normalization | P1 |
| Config integration test suite | HIGH — prevents regressions in complex resolution logic | MEDIUM — test matrix across env vars, file states | P1 |
| Docker health checks | MEDIUM — improves container observability | MEDIUM — Dockerfile + health script | P2 |
| Adaptive monitor polling | LOW-MEDIUM — reduces idle CPU; not blocking | LOW — replace `time.sleep()` with backoff logic | P2 |
| Cosine similarity threshold calibration | MEDIUM — improves memory health scan accuracy | LOW — CLI tool + distribution analysis | P2 |

**Priority key:**
- P1: Must have for v1.5 to be called "Config Consolidation"
- P2: Should have — deferred v1.4 items, high value-to-cost ratio
- P3: Nice to have, future consideration

---

## Detailed Feature Behavior: Expected Patterns

### 1. Single Authoritative Path Resolver (CONF-01)

**Current problem (verified by codebase inspection):**

Three independent root resolution strategies currently coexist:

| Location | Strategy | Risk |
|----------|----------|------|
| `project_config.py::_find_project_root()` | `OPENCLAW_ROOT` env var, else walk up from `__file__` parent | Correct — canonical |
| `spawn.py` line 433 | `Path(__file__).parent.parent.parent` | Hardcoded depth — breaks if package structure changes |
| `init.py::find_project_root()` | Walk up looking for `openclaw.json` presence | Different walk-up strategy, no env var check |

**Expected resolution:**

```python
# project_config.py — promote _find_project_root() to public API
def get_project_root() -> Path:
    """
    Return the OpenClaw project root directory.

    Resolution order:
    1. OPENCLAW_ROOT env var (explicit override)
    2. Walk up from this file's location until openclaw.json is found
    3. FileNotFoundError if neither succeeds

    All components that need the project root MUST call this function.
    Do not use Path(__file__).parent.parent or custom walk-up logic.
    """
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        return Path(env_root)
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "openclaw.json").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError(
        "Cannot find openclaw.json. Set OPENCLAW_ROOT env var or run from within the project."
    )
```

**Callers to update:**
- `spawn.py` line 433: replace `Path(__file__).parent.parent.parent` with `from openclaw.project_config import get_project_root; project_root = get_project_root()`
- `init.py::find_project_root()`: replace body with `from .project_config import get_project_root; return get_project_root()`
- All other callers of `_find_project_root()` (internal) are already in `project_config.py` — no changes needed

**Confidence:** HIGH — refactor only, no behavior change.

---

### 2. Constants Consolidation (CONF-05)

**Current state (verified):**

| Constant | Current Location | Value |
|----------|-----------------|-------|
| `LOCK_TIMEOUT` | `config.py` | 5s |
| `LOCK_RETRY_ATTEMPTS` | `config.py` | 3 |
| `POLL_INTERVAL` | `config.py` | 1.0s |
| `CACHE_TTL_SECONDS` | `config.py` | 5.0s |
| `LOG_LEVEL` | `config.py` | from env |
| `ACTIVITY_LOG_MAX_ENTRIES` | `config.py` | from env, default 100 |
| Pool defaults (`max_concurrent`, `pool_mode`, etc.) | `project_config.py::_POOL_CONFIG_DEFAULTS` | Scattered dict |
| Cosine similarity thresholds | `scan_engine.py` (hardcoded in `_find_conflicts()` call sites) | 0.75 / 0.97 |
| Staleness thresholds | Dashboard API handler (unverified location) | age_threshold_days=30, retrieval_window_days=14 |
| Adaptive poll min/max | Does not exist yet | New in v1.5 |

**Target state:**

```python
# config.py — authoritative location for ALL tunable constants

# --- Locking ---
LOCK_TIMEOUT = 5          # seconds; max wait for fcntl.LOCK_EX
LOCK_RETRY_ATTEMPTS = 3   # retries before raising TimeoutError

# --- Polling ---
POLL_INTERVAL = 1.0       # base polling interval (seconds)
POLL_INTERVAL_MIN = 0.5   # adaptive poll: fastest (seconds)
POLL_INTERVAL_MAX = 10.0  # adaptive poll: slowest when quiescent (seconds)
POLL_BACKOFF_FACTOR = 2.0 # multiply interval after each quiet cycle
POLL_QUIET_THRESHOLD = 3  # consecutive quiet cycles before backing off

# --- Cache ---
CACHE_TTL_SECONDS = 5.0   # max state cache age before forced re-read

# --- Logging ---
LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()
ACTIVITY_LOG_MAX_ENTRIES = int(os.environ.get("OPENCLAW_ACTIVITY_LOG_MAX", "100"))

# --- Pool defaults ---
POOL_MAX_CONCURRENT = 3
POOL_MODE_DEFAULT = "shared"
POOL_OVERFLOW_POLICY_DEFAULT = "wait"
POOL_QUEUE_TIMEOUT_S = 300
POOL_RECOVERY_POLICY_DEFAULT = "mark_failed"

# --- Memory health ---
MEMORY_STALENESS_AGE_DAYS = 30        # flag memories older than this
MEMORY_STALENESS_WINDOW_DAYS = 14     # unless retrieved within this window
MEMORY_CONFLICT_SIMILARITY_MIN = 0.75 # lower bound of conflict window
MEMORY_CONFLICT_SIMILARITY_MAX = 0.97 # upper bound (above = near-duplicate)
MEMORY_NEAR_DUPLICATE_THRESHOLD = 0.97

# --- Docker health check ---
HEALTH_CHECK_INTERVAL_S = 30          # how often Docker runs the health check
HEALTH_CHECK_TIMEOUT_S = 10           # health check script must complete within
HEALTH_CHECK_RETRIES = 3              # failures before marking unhealthy
HEALTH_CHECK_START_PERIOD_S = 60      # don't count failures during startup
HEALTH_CHECK_STALE_STATE_S = 90       # state not updated in this window = unhealthy
```

**Confidence:** HIGH — purely mechanical consolidation.

---

### 3. openclaw.json Startup Validation (CONF-02, CONF-06)

**Current state:** `validate_agent_hierarchy()` validates `agents.list` only. Everything else
(`gateway`, `memory`, `channels`, `source_directories`) is loaded and used without validation.

**Expected extended validation:**

```python
def validate_openclaw_config(config: dict, config_path: str) -> None:
    """
    Validate all top-level sections of openclaw.json at startup.
    Fail-fast: raises ConfigValidationError listing all problems at once.
    """
    errors = []

    # gateway.port: must be an integer in 1–65535
    gateway = config.get("gateway", {})
    if "port" in gateway:
        port = gateway["port"]
        if not isinstance(port, int) or not (1 <= port <= 65535):
            errors.append(
                f'openclaw.json: gateway.port must be an integer 1–65535, got {port!r}'
            )

    # memory.memu_api_url: must be a string starting with http:// or https://
    memory = config.get("memory", {})
    if "memu_api_url" in memory:
        url = memory["memu_api_url"]
        if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
            errors.append(
                f'openclaw.json: memory.memu_api_url must start with http:// or https://, got {url!r}'
            )

    # source_directories: must be a list of non-empty strings
    src_dirs = config.get("source_directories", [])
    if not isinstance(src_dirs, list):
        errors.append('openclaw.json: source_directories must be a list')
    else:
        for i, d in enumerate(src_dirs):
            if not isinstance(d, str) or not d.strip():
                errors.append(f'openclaw.json: source_directories[{i}] must be a non-empty string')

    # Delegate agent hierarchy to existing validator
    _validate_agent_hierarchy_section(config, config_path, errors)

    if errors:
        raise ConfigValidationError(errors)
```

**Startup hook:** `load_and_validate_openclaw_config()` in `project_config.py` calls
`validate_openclaw_config()` — this is already the entry point. Extend it, not a new call site.

**Confidence:** HIGH — extends existing pattern.

---

### 4. Migration CLI (CONF-03)

**Standard pattern for JSON config migration:**

The migration CLI is an `openclaw-migrate` entry point (new `cli/migrate.py`, registered in
`pyproject.toml`). It follows the standard collect-diff-apply pattern:

```bash
# Dry-run mode: show what would change
openclaw-migrate --dry-run

# Apply mode: write normalized config in-place (takes backup first)
openclaw-migrate

# Specific file
openclaw-migrate --config /path/to/openclaw.json
```

**Migration operations:**

| Operation | Condition | Action |
|-----------|-----------|--------|
| Normalize env var placeholders | Field values contain raw secrets | Warn user, do not modify (can't know the right var name) |
| Add missing `active_project: null` | Key absent | Insert with null value and comment |
| Normalize `source_directories` | Missing entirely | Insert empty list `[]` |
| Remove unknown top-level keys | Keys not in schema | Log removed key names; strip from output |
| Validate result | After normalization | Run `validate_openclaw_config()` on output; fail if still invalid |

**Output format:**

```
OpenClaw Config Migration
Reading: /home/ollie/.openclaw/openclaw.json

Changes:
  + Added missing field: source_directories = []
  ~ Removed unknown key: legacy_field

Backup written: /home/ollie/.openclaw/openclaw.json.bak.20260225T120000
Config updated: /home/ollie/.openclaw/openclaw.json

Validation: PASSED
```

**Confidence:** HIGH — argparse subcommand pattern is already established in the codebase.

---

### 5. Docker Health Checks for L3 Containers (REL-09)

**Standard Docker HEALTHCHECK pattern (verified from official docs):**

```dockerfile
# docker/l3-specialist/Dockerfile

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/entrypoint-health.sh"]
```

```bash
#!/bin/bash
# docker/l3-specialist/entrypoint-health.sh
# Exit 0 = healthy, non-zero = unhealthy

set -e

STATE_FILE="${OPENCLAW_STATE_FILE:-/workspace/.openclaw/${OPENCLAW_PROJECT}/workspace-state.json}"

# Rule 1: State file must exist (container has made progress)
if [[ ! -f "$STATE_FILE" ]]; then
    echo "UNHEALTHY: state file not found: $STATE_FILE" >&2
    exit 1
fi

# Rule 2: State file must have been written within HEALTH_CHECK_STALE_STATE_S seconds
STALE_THRESHOLD="${HEALTH_CHECK_STALE_STATE_S:-90}"
MTIME=$(stat -c %Y "$STATE_FILE" 2>/dev/null || echo 0)
NOW=$(date +%s)
AGE=$(( NOW - MTIME ))

if (( AGE > STALE_THRESHOLD )); then
    echo "UNHEALTHY: state file not updated for ${AGE}s (threshold: ${STALE_THRESHOLD}s)" >&2
    exit 1
fi

echo "HEALTHY: state updated ${AGE}s ago"
exit 0
```

**Parameter rationale:**
- `--start-period=60s`: L3 containers need time for Claude/Gemini to produce first output before state is written. 60s is conservative; task startup typically completes in 5-15s but model calls can be slow.
- `--interval=30s`: Frequent enough to detect stuck containers within a minute.
- `--timeout=10s`: Health script is a filesystem stat — should complete in milliseconds.
- `--retries=3`: Three consecutive failures (90s total) before declaring unhealthy, absorbs transient slow model calls.

**Dashboard integration:** The container list in occc already calls `docker inspect` for container
metadata. `Health.Status` is available in the inspect output (`healthy`, `unhealthy`, `starting`).
Add a health status badge to the container row in the existing `useContainers()` hook.

**Ephemeral container caveat:** L3 containers are short-lived (minutes to hours). Health check status
is primarily useful to detect containers that are stuck (model API timeout, file lock deadlock) rather
than for restart orchestration. The `unhealthy` status is informational — L2 is the appropriate
entity to decide whether to kill and restart a stuck container.

**Confidence:** MEDIUM — Docker HEALTHCHECK semantics are well-documented (HIGH). The health script
logic (state file recency) is appropriate for this workload (MEDIUM — assumes state file is written
frequently enough; tasks with no intermediate state writes will appear unhealthy even if running).

---

### 6. Adaptive Monitor Poll Interval (OBS-05)

**Current state:** `tail_state()` in `monitor.py` does `time.sleep(interval)` with a fixed 1.0s
interval. The `POLL_INTERVAL` constant is used as the default for `--interval` CLI argument.

**Expected behavior — exponential backoff on quiescence:**

```python
# Adaptive polling state per monitoring session (not per project)
_consecutive_quiet: int = 0  # cycles with no new activity

def _compute_next_interval(had_activity: bool, current_interval: float) -> float:
    """
    Compute next poll interval.
    - Activity seen: reset to POLL_INTERVAL_MIN
    - No activity: double up to POLL_INTERVAL_MAX
    """
    if had_activity:
        return POLL_INTERVAL_MIN
    return min(current_interval * POLL_BACKOFF_FACTOR, POLL_INTERVAL_MAX)
```

**Integration into `tail_state()` main loop:**

```python
current_interval = POLL_INTERVAL_MIN
while True:
    had_activity = False
    for proj_id, state_file in projects:
        # ... existing poll logic ...
        if new_entries or status_changed:
            had_activity = True
    current_interval = _compute_next_interval(had_activity, current_interval)
    time.sleep(current_interval)
```

**Behavior characteristics:**
- System with active L3 tasks: polls at 0.5s (same responsiveness as before, faster than current 1.0s)
- System idle for 3 cycles: 0.5s → 1.0s → 2.0s → 4.0s → capped at 10.0s
- Any new activity: immediately resets to 0.5s on next cycle
- CPU usage during sustained idle: ~18 polls/minute vs ~60/minute at fixed 1.0s — 70% reduction

**CLI flag behavior:** `--interval` becomes the base interval (default: `POLL_INTERVAL_MIN`). Users
who pass `--interval 5` get a 5s base with backoff to `POLL_INTERVAL_MAX`.

**Confidence:** HIGH — standard exponential backoff pattern; no external dependencies.

---

### 7. Cosine Similarity Threshold Calibration (QUAL-07)

**Current state:** `scan_engine.py::_find_conflicts()` uses `similarity_min=0.75` and
`similarity_max=0.97` hardcoded in call sites. The v1.4 key decisions table explicitly marked this as
"⚠️ Revisit — threshold needs empirical tuning under real workload."

**Research findings on cosine threshold values (MEDIUM confidence):**

No universal threshold exists. Values depend on embedding model, domain vocabulary density, and task.
Community patterns for text embeddings (OpenAI, sentence-transformers):
- Near-duplicate detection: 0.95–0.99 range is widely used
- Semantic similarity: 0.75–0.85 is the standard "related" range
- Conflict detection (similar topic, opposing content): this is a harder problem — similarity alone
  cannot distinguish "these say the same thing" from "these say opposite things about the same topic"

**What calibration means for OpenClaw:**

The `similarity_max=0.97` (near-duplicate ceiling) is likely too low — memories about the same task
from different angles can legitimately have similarity >0.92 without being conflicting. The
`similarity_min=0.75` (conflict floor) is a reasonable starting point.

**Calibration tool behavior:**

```bash
# Sample existing memory store and analyze similarity distribution
openclaw-health calibrate-thresholds --project pumplai

# Output:
Analyzing 142 memories for project: pumplai
Computing pairwise similarities...

Similarity distribution:
  Pairs with sim > 0.97: 8  (near-duplicate candidates)
  Pairs with sim 0.90-0.97: 23 (high similarity)
  Pairs with sim 0.75-0.90: 41 (moderate similarity — current conflict window)
  Pairs with sim < 0.75: 1,847 (dissimilar)

Recommendations:
  Near-duplicate threshold: 0.97 (current: 0.97) ✓ OK
  Conflict window min: 0.82 (current: 0.75) ↑ Consider raising to reduce false positives
  Conflict window max: 0.97 (current: 0.97) ✓ OK

Manual review recommended for: 8 near-duplicate pairs (see --verbose for details)
```

**Implementation:** New `cli/health.py` with `calibrate-thresholds` subcommand. Calls `MemoryClient`
to retrieve all memories for a project, computes pairwise cosine similarities using the same
`cosine_topk` function already in `scan_engine.py`, outputs distribution and recommendations.
Thresholds are in `config.py` and the calibration tool outputs suggested values — operator updates
`config.py` constants manually.

**Why not automatic adjustment:** The system does not have enough labeled examples of "true conflict"
vs "legitimately similar" to learn a threshold automatically. Manual review of a sample is required
to validate recommendations. Automatic adjustment creates an audit gap.

**Confidence:** MEDIUM — the calibration tool logic is straightforward (HIGH); the recommended
threshold values require empirical validation against real project memory data (MEDIUM).

---

## Existing Integration Points (v1.4 foundations v1.5 builds on)

| v1.4 Component | v1.5 Usage |
|----------------|------------|
| `project_config.py::_find_project_root()` | Promoted to public `get_project_root()`, becomes the canonical resolver |
| `config.py` | Extended with all constants migrated from other modules |
| `config_validator.py::validate_project_config()` | Extended with `openclaw.json` section validation |
| `config_validator.py::validate_agent_hierarchy()` | Unchanged — called by the new `validate_openclaw_config()` wrapper |
| `scan_engine.py::_find_conflicts()` | Thresholds read from `config.py` instead of hardcoded |
| `cli/monitor.py::tail_state()` | Adaptive interval replaces fixed `time.sleep(interval)` |
| `docker/l3-specialist/Dockerfile` | `HEALTHCHECK` instruction added |
| `MemoryClient.retrieve()` | Used by calibration tool to sample memories |
| `packages/orchestration/tests/` | Extended with config integration test suite |

---

## Sources

- Codebase analysis: `packages/orchestration/src/openclaw/config.py`, `project_config.py`, `config_validator.py`, `init.py`, `cli/monitor.py`, `skills/spawn/spawn.py`, `docker/l3-specialist/Dockerfile`, `docker/memory/memory_service/scan_engine.py`
- [Docker HEALTHCHECK documentation — official Dockerfile reference](https://docs.docker.com/reference/dockerfile/#healthcheck)
- [Docker Health Check Best Practices 2026 — OneUptime](https://oneuptime.com/blog/post/2026-01-30-docker-health-check-best-practices/view)
- [Cosine Similarity Thresholds — rule-of-thumb discussion (OpenAI forum)](https://community.openai.com/t/rule-of-thumb-cosine-similarity-thresholds/693670)
- [Adaptive Polling Mechanisms — emergentmind](https://www.emergentmind.com/topics/adaptive-polling)
- [Exponential backoff — Wikipedia](https://en.wikipedia.org/wiki/Exponential_backoff)
- PROJECT.md requirement IDs: CONF-01 through CONF-07, REL-09, QUAL-07, OBS-05

---

*Feature research for: OpenClaw v1.5 Config Consolidation*
*Researched: 2026-02-25*
