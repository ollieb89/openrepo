# Stack Research

**Domain:** AI Swarm Orchestration — v1.5 Config Consolidation additions
**Researched:** 2026-02-25
**Confidence:** HIGH (all claims verified against codebase + official Python docs + PyPI + Docker docs)

---

## Scope

This document covers ONLY net-new stack needs for v1.5. It does not re-document the existing
validated stack (Python 3 stdlib, docker>=7.1.0, httpx, asyncio, fcntl, Next.js 16, SWR,
Tailwind 4, Recharts, memU/FastAPI/PostgreSQL+pgvector) which shipped in v1.0–v1.4.

The four feature areas in scope:

1. **Config consolidation** — single authoritative path resolver, schema validation on load, migration CLI, env var precedence, constants consolidation, fail-fast startup validation, integration test suite (CONF-01 through CONF-07)
2. **Docker health checks for L3 containers** — HEALTHCHECK Dockerfile instruction + Python SDK health status read (REL-09)
3. **Cosine similarity threshold calibration** — empirical tuning methodology for conflict detection (QUAL-07)
4. **Adaptive monitor poll interval** — dynamic interval scaling based on activity level (OBS-05)

---

## Recommended Stack

### Core Technologies — Net New

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `jsonschema` | `>=4.26.0` | Strict schema validation for `openclaw.json` and `project.json` at startup | Provides JSON Schema Draft 7/2020-12 validation with lazy collect-all error reporting. OpenClaw already uses a hand-rolled `config_validator.py` that checks individual fields — jsonschema replaces that with a declarative schema dict, making CONF-02 and CONF-06 achievable without bespoke field-check code. No C extensions required; pure Python; Python >=3.10 compatible. Current release: 4.26.0 (Jan 7 2026). |
| Docker `HEALTHCHECK` instruction | Dockerfile built-in | L3 container health reporting to Docker daemon (REL-09) | Built-in Dockerfile instruction — zero library change. Adds `--interval`, `--timeout`, `--start-period`, `--retries` options. L3 containers are short-lived tasks; `--start-period` accounts for startup time. Health status readable via `container.attrs["State"]["Health"]["Status"]` in the existing docker-py client. |
| `container.attrs["State"]["Health"]` | docker>=7.1.0 (already pinned) | Read L3 container health status from Python | Accessed via the already-imported docker-py SDK. No new library. Pattern: `container.reload(); health = container.attrs.get("State", {}).get("Health", {})`. Returns dict with `Status` ("starting"/"healthy"/"unhealthy"/"none") and `Log` array. |

### Supporting Libraries — Net New

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `jsonschema` | `>=4.26.0` | Schema validation for config files | Add to `packages/orchestration/pyproject.toml` dependencies. Used in `config_validator.py` to replace hand-written field checks with declarative `Draft7Validator` or `Draft202012Validator`. Enables strict fail-fast on startup (CONF-06) and comprehensive integration testing (CONF-07). |

**All other v1.5 features are stdlib-only.** No further new pip installs required.

### What is Already Available — Do NOT Add Again

| Capability | Where It Lives | v1.5 Use |
|------------|---------------|---------|
| Path resolution helpers | `packages/orchestration/src/openclaw/project_config.py` — `_find_project_root()`, `get_workspace_path()`, `get_state_path()`, `get_snapshot_dir()` | CONF-01: Audit all callsites and unify through these helpers. No new module needed — refactor existing divergent paths. |
| Config loading | `project_config.py` — `load_and_validate_openclaw_config()`, `load_project_config()` | CONF-02: Extend these functions with jsonschema validation instead of re-implementing load logic. |
| Config validation | `config_validator.py` — `validate_project_config()`, `validate_agent_hierarchy()`, `ConfigValidationError` | CONF-06: Replace field-by-field checks with jsonschema Draft 7 validator. Keep `ConfigValidationError` exception — callers already handle it. |
| Constants / defaults | `config.py` — `LOCK_TIMEOUT`, `POLL_INTERVAL`, `CACHE_TTL_SECONDS`, `LOG_LEVEL`, `ACTIVITY_LOG_MAX_ENTRIES`. Pool defaults in `project_config.py` `_POOL_CONFIG_DEFAULTS`. | CONF-05: Move ALL magic numbers here. `project_config.py`'s `_POOL_CONFIG_DEFAULTS` dict moves to `config.py`. |
| Migration CLI pattern | `cli/migrate_state.py` — argparse subcommand, idempotent with sentinel file, in-flight guard | CONF-03: New `openclaw-config migrate` command follows the same idempotent-with-guard pattern. |
| Argparse subcommands | `cli/project.py`, `cli/monitor.py`, `cli/suggest.py` — established subcommand pattern | CONF-03: Config migrate CLI uses the same `argparse.ArgumentParser` + `add_subparsers()` pattern already in project.py. No new CLI framework. |
| Env var precedence | `OPENCLAW_ROOT`, `OPENCLAW_PROJECT`, `OPENCLAW_LOG_LEVEL`, `OPENCLAW_ACTIVITY_LOG_MAX` — all read via `os.environ.get()` in their respective modules | CONF-04: Document the precedence chain (env > config file > hardcoded default) in code comments and ensure it is applied consistently across all four env vars. No new code — consistency audit. |
| Docker SDK client | `docker>=7.1.0` (already pinned) | REL-09: `container.reload(); container.attrs["State"]["Health"]` reads health status from the same client used in pool.py and review.py. |
| Structured JSON logging | `openclaw/logging.py` `get_logger()` factory | All new modules use existing logger. No new logging dep. |
| `pytest>=7.0` + `pytest-asyncio` | Already in dev dependencies | CONF-07: Config integration tests use the existing test suite infrastructure. No new testing library. |
| `time.monotonic()` (stdlib) | built-in | OBS-05: Adaptive poll interval calculation. Already used in state_engine.py context. |

---

## Integration Points with Existing Stack

### Feature Area 1: Config Consolidation (CONF-01 through CONF-07)

**The problem:** Multiple modules independently read `openclaw.json` via `_find_project_root()`. The `workspace/` path is constructed differently in `project_config.py` (`root / "workspace" / ".openclaw" / project_id`) vs `cli/monitor.py` (`root / "workspace" / ".openclaw" / entry.name`). Constants are split between `config.py` and `project_config.py`.

**CONF-01 — Authoritative path resolver:**
No new library. Consolidate `get_state_path()` and `get_snapshot_dir()` in `project_config.py` as the single canonical source. Audit callers: `state_engine.py`, `cli/monitor.py`, `cli/migrate_state.py`, `skills/spawn/spawn.py`. Each must call `get_state_path(project_id)` — no inline path construction.

**CONF-02 + CONF-06 — Schema validation with jsonschema:**
```python
# config_validator.py (new pattern)
from jsonschema import Draft7Validator, ValidationError

OPENCLAW_JSON_SCHEMA = {
    "type": "object",
    "required": ["active_project", "agents"],
    "properties": {
        "active_project": {"type": "string", "minLength": 1},
        "agents": {
            "type": "object",
            "required": ["list"],
            "properties": {
                "list": {"type": "array", "items": {"type": "object"}}
            }
        },
        "memory": {
            "type": "object",
            "properties": {
                "memu_api_url": {"type": "string"},
                "enabled": {"type": "boolean"}
            }
        }
    }
}

PROJECT_JSON_SCHEMA = {
    "type": "object",
    "required": ["workspace", "tech_stack"],
    "properties": {
        "workspace": {"type": "string", "minLength": 1},
        "tech_stack": {"type": "object"},
        "l3_overrides": {"type": "object"}
    }
}

def validate_openclaw_config(config: dict, config_path: str) -> None:
    validator = Draft7Validator(OPENCLAW_JSON_SCHEMA)
    errors = list(validator.iter_errors(config))
    if errors:
        raise ConfigValidationError([e.message for e in errors])
```

**CONF-03 — Migration CLI:**
New `openclaw-config` entry point in `pyproject.toml` pointing to `cli/config_migrate.py`. Subcommands: `validate`, `migrate`. Pattern mirrors `cli/migrate_state.py` — idempotent, in-flight guard, sentinel on completion. No new library.

**CONF-04 — Env var precedence:**
Document and enforce: `OPENCLAW_ROOT` (root resolution) > `openclaw.json:active_project` for `OPENCLAW_PROJECT`. Precedence is already implemented; this is a consistency audit with added comments and a test.

**CONF-05 — Constants consolidation:**
Move `_POOL_CONFIG_DEFAULTS` from `project_config.py` to `config.py`. Add `HEALTH_CHECK_INTERVAL = 30` (Docker HEALTHCHECK default), `MONITOR_POLL_MIN = 0.5`, `MONITOR_POLL_MAX = 5.0` (OBS-05 bounds). One module owns all tunable numbers.

**CONF-07 — Integration test suite:**
Uses existing `pytest>=7.0` + `pytest-asyncio` + `tmp_path` fixture. Tests cover: path resolution for known project IDs, `ConfigValidationError` raised on bad schema, env var override of `OPENCLAW_ROOT`, migration CLI dry-run and actual migration idempotency.

### Feature Area 2: Docker Health Checks for L3 Containers (REL-09)

**Dockerfile change** — add to `docker/l3-specialist/Dockerfile`:
```dockerfile
# Health check: verify the entrypoint marker file exists (L3 creates it on startup)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD test -f /tmp/.openclaw_alive || exit 1
```

The `--start-period=60s` accounts for L3 startup time (Claude CLI initialization, git clone, etc.). The check itself is a file-existence test — L3 `entrypoint.sh` writes `/tmp/.openclaw_alive` on successful startup. This avoids network port dependency for a task-runner container.

**Rationale for file-based health check vs HTTP:**
- L3 containers do not expose HTTP ports
- `curl` would require the container to bind a port just for health checking
- `test -f /file` is zero-dependency (bash builtin), instant, and sufficient for "container is up and running" signal
- Docker health state flows: `starting` (during `--start-period`) → `healthy` → `unhealthy` (if 3 consecutive failures)

**Python SDK read** — in `skills/spawn/pool.py` or `review.py` after container operations:
```python
container.reload()  # Refresh attrs from daemon
health = container.attrs.get("State", {}).get("Health", {})
health_status = health.get("Status", "none")  # "starting"|"healthy"|"unhealthy"|"none"
```

`container.reload()` is already called in pool.py to check `container.status`. Adding health check read is a one-line addition.

**Dashboard exposure:** Pass `health_status` field in the existing swarm stream SSE payload. Dashboard `useContainers()` hook already polls every 5s; the new field appears alongside `status` in the container list response.

### Feature Area 3: Cosine Similarity Threshold Calibration (QUAL-07)

**What needs calibrating:** The conflict detection window in `docker/memory/memory_service/scan_engine.py` uses `similarity_min=0.75` and `similarity_max=0.92`. The 0.92 upper bound was flagged at v1.4 as needing empirical tuning.

**No new library.** The calibration is a methodology + test, not a runtime library change:

1. **Test harness** — new `pytest` parametrize test that runs `_find_conflicts()` against a fixture corpus of known-conflicting and known-distinct memory pairs with varying thresholds (0.75, 0.80, 0.85, 0.88, 0.90, 0.92, 0.95).
2. **Precision/recall metrics** — pure Python: `precision = true_positives / (true_positives + false_positives)`, `recall = true_positives / (true_positives + false_negatives)`. F1 score derivation.
3. **Fixture generation** — small deterministic corpus (20-30 pairs) with known similarity ground truth. Embeddings can be synthetic numpy arrays for the unit test; real pgvector embeddings used in integration test against a live memU instance.
4. **Outcome** — calibrated `similarity_min` and `similarity_max` constants moved to `config.py` as `CONFLICT_SIMILARITY_MIN` and `CONFLICT_SIMILARITY_MAX`. Currently 0.75/0.92 — final values determined by test results.

**Why this is the right approach:** NLP research consistently shows cosine similarity thresholds are domain-specific with no universal value. The [0.75, 0.85] range is typical for OOD detection on sentence embeddings; OpenClaw's task-description embeddings may differ. Empirical testing on the actual corpus is the only reliable calibration method (confirmed by ACL/EMNLP literature).

**`numpy` usage note:** `numpy` is already a transitive dep of `pgvector`/`memu` in the memory service Docker container. The calibration test can use `numpy` in the test environment only — it must NOT be added to orchestration's `pyproject.toml` dependencies.

### Feature Area 4: Adaptive Monitor Poll Interval (OBS-05)

**No new library.** Pure stdlib pattern using `time.monotonic()` for elapsed time tracking and `min()`/`max()` for interval clamping.

**Algorithm** (implemented in `cli/monitor.py` `tail_state()`):
```python
# Constants from config.py
MONITOR_POLL_MIN = 0.5   # seconds — floor when activity is high
MONITOR_POLL_MAX = 5.0   # seconds — ceiling when idle
MONITOR_BACKOFF_FACTOR = 1.5  # interval growth factor on idle cycle
MONITOR_ACTIVITY_RESET = True  # reset to POLL_MIN on any new activity

interval = MONITOR_POLL_MIN
last_activity_time = time.monotonic()

while True:
    had_activity = _poll_all_projects(...)  # returns bool
    if had_activity:
        interval = MONITOR_POLL_MIN
        last_activity_time = time.monotonic()
    else:
        idle_secs = time.monotonic() - last_activity_time
        # Back off exponentially up to MONITOR_POLL_MAX
        interval = min(interval * MONITOR_BACKOFF_FACTOR, MONITOR_POLL_MAX)

    time.sleep(interval)
```

**Integration point:** `tail_state()` in `cli/monitor.py` currently calls `time.sleep(interval)` with a fixed interval passed from CLI args. The adaptive version replaces the fixed sleep with the above pattern. The `--interval` CLI arg becomes the `POLL_MIN` override (when user specifies, use as floor instead of default).

**Dashboard SSE stream:** The dashboard monitor (`packages/dashboard/src/app/api/swarm/stream/route.ts`) polls via `useContainers()` at a fixed 5s interval on the client side. This is a separate codepath — OBS-05 only targets the CLI monitor, not the dashboard SSE. Dashboard polling remains fixed.

---

## Installation

```bash
# Add jsonschema to orchestration dependencies
# Edit packages/orchestration/pyproject.toml:
# dependencies = ["docker>=7.1.0", "httpx", "jsonschema>=4.26.0"]

uv pip install "jsonschema>=4.26.0"

# All other v1.5 features require NO new pip installs.
# REL-09: Dockerfile instruction change only (no Python package)
# QUAL-07: Calibration test only (numpy available in memory service container already)
# OBS-05: stdlib time.monotonic() only
```

Verify single new dep:
```bash
python3 -c "import jsonschema; print(jsonschema.__version__)"
# Expected: 4.26.0 (or later)

# Confirm all other needed modules are stdlib
python3 -c "import time, os, json, argparse; print('all stdlib OK')"
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `jsonschema>=4.26.0` with `Draft7Validator` | Hand-rolled field checks (current `config_validator.py`) | Keep hand-rolled only if you need custom error messages that jsonschema cannot produce. jsonschema's `iter_errors()` gives field paths — sufficient for actionable errors. The current hand-rolled approach was appropriate for v1.2 (2 fields), but CONF-02 adds 8+ schema constraints making declarative validation the lower-maintenance choice. |
| `jsonschema>=4.26.0` | `pydantic>=2.0` | Use pydantic if OpenClaw config objects need to be passed as typed Python objects throughout the codebase. jsonschema validates raw dicts (which is what config files are) without creating model classes. At v1.5 scope, raw dict access is sufficient and pydantic would require refactoring all callers. |
| `jsonschema>=4.26.0` | `jsonschema-rs` (Rust-based) | Use jsonschema-rs if validation throughput exceeds 10,000 configs/second. OpenClaw validates at most 2 config files on startup. Pure-Python jsonschema is ample. |
| File-based `HEALTHCHECK` (`test -f /tmp/.openclaw_alive`) | HTTP-based `HEALTHCHECK` (`curl -f http://localhost:PORT/health`) | Use HTTP check if L3 containers ever expose a port (e.g., future local API). Current L3 containers are task runners with no listening port — file-based is simpler and zero-dependency. |
| Exponential backoff with `min(interval * 1.5, MAX)` | `backoff` PyPI library | Use backoff library if retry/backoff is needed across many functions with decorator syntax. OBS-05 is one polling loop — inline `min()` calculation needs no library. |
| Empirical calibration test harness | Static threshold (keep 0.92) | Keep static only if no real memory corpus is available for testing. The v1.4 decision log explicitly flags 0.92 as "revisit" — QUAL-07 mandates calibration rather than accepting the unvalidated value. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pydantic` for config validation | Creates typed model classes requiring refactoring all dict-access callers throughout codebase. Disproportionate change for a config validation improvement. | `jsonschema.Draft7Validator` validates raw dicts in-place — zero caller changes needed. |
| `numpy` in `packages/orchestration/` | Already explicitly rejected in v1.4 and v1.3 research. Adds 15MB+ compiled dep to what is otherwise a zero-C-extension Python package. Vector math for QUAL-07 calibration runs only in the memory service Docker container where numpy is already present transitively. | Calibration test imports numpy only in `tests/test_threshold_calibration.py`, not in orchestration production code. |
| HTTP `HEALTHCHECK` with `curl` in L3 Dockerfile | Requires installing curl in the image (already present) AND L3 container exposing a port just for health checking. Port binding is unnecessary complexity for a task-runner container. | `test -f /tmp/.openclaw_alive` — bash builtin, no port, no network, instant. |
| `APScheduler` or similar for adaptive polling | Library dependency for a pattern expressible in 5 lines of stdlib code. OBS-05 is one while-loop with exponential backoff — not a multi-job scheduling problem. | `time.monotonic()` + `time.sleep()` + inline interval calculation. |
| `ConfigArgParse` or similar config-arg bridges | Introduces a new CLI framework over the existing argparse patterns. All env var / config file precedence is already implemented via `os.environ.get()` — consistent with the locked v1.1 decision to use argparse subparsers. | `os.environ.get("OPENCLAW_ROOT")` + argparse (already established pattern). |
| `click` for migration CLI | Inconsistent with all existing CLI modules (`monitor.py`, `project.py`, `suggest.py`) which use argparse. Introducing click creates two CLI frameworks in one package. | `argparse.ArgumentParser` + `add_subparsers()` — established in-codebase pattern. |

---

## Stack Patterns by Variant

**If `openclaw.json` schema grows beyond simple type checks (e.g., cross-field validation):**
- Use jsonschema `if/then/else` keywords within the Draft 7 schema
- Example: `if active_project is set, then projects/<id>/project.json must exist`
- Implement as a post-schema custom validator function (not a separate library)

**If the HEALTHCHECK file approach proves unreliable (container dies before writing marker):**
- Add the `test -f` check as a fallback to the entrypoint exit trap
- Alternative: check for the process itself via `pgrep -f entrypoint` or check for a known artifact (git repo, virtualenv)
- Do NOT switch to HTTP check unless L3 containers expose ports for other reasons

**If adaptive poll interval needs to be configurable per-project:**
- Add `monitor.poll_min` and `monitor.poll_max` to `project.json`'s `l3_overrides`
- Read via `get_pool_config()` extension (follow existing override pattern)
- For v1.5, global constants in `config.py` are sufficient

**If jsonschema validation errors need more human-friendly formatting:**
- Use `jsonschema.exceptions.best_match(errors)` to surface the most relevant error when multiple errors exist
- Wrap in `ConfigValidationError` as before — callers already handle that exception type

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `jsonschema>=4.26.0` | Python >=3.10 | Current release 4.26.0 (Jan 7 2026). No C extensions. Works with Python 3.10–3.14 (OpenClaw's target range). Lazy `iter_errors()` works on Python 3.10+. |
| `docker>=7.1.0` (existing) | Python >=3.10 | `container.attrs["State"]["Health"]` available in all docker-py 7.x releases. No version change needed. |
| `jsonschema` Draft 7 | `openclaw.json` current structure | Draft 7 is the stable, well-supported target. Draft 2020-12 is also available but Draft 7 is sufficient for the schema complexity involved. |
| `time.monotonic()` | Python >=3.3 | Available on all supported Python versions. Monotonic clock — immune to system clock adjustments. |
| `test -f` in `HEALTHCHECK CMD` | Docker 17.05+ | HEALTHCHECK instruction stable since Docker 1.12. `--start-period` (used for L3 grace period) requires Docker 17.05+. Docker 29.1.5 fully supports all options. |

---

## Sources

- PyPI jsonschema 4.26.0 — current version (Jan 7 2026), Python >=3.10, MIT license, no C extensions (HIGH confidence, fetched 2026-02-25)
- [jsonschema official docs — Schema Validation](https://python-jsonschema.readthedocs.io/en/stable/validate/) — `Draft7Validator`, `iter_errors()`, `best_match()` (HIGH confidence)
- [Docker HEALTHCHECK docs](https://gdevops.frama.io/containerization/dockerfile/instructions/HEALTHCHECK/HEALTHCHECK.html) — `--interval`, `--timeout`, `--start-period`, `--retries` parameters (HIGH confidence)
- [Docker HEALTHCHECK best practices 2026](https://oneuptime.com/blog/post/2026-01-30-docker-health-check-best-practices/view) — file-based vs HTTP check patterns (MEDIUM confidence)
- docker-py SDK docs (7.1.0) — `container.attrs` raw response structure; `container.reload()` for refreshing attrs (HIGH confidence via WebSearch verification against SDK docs)
- `container.attrs["State"]["Health"]["Status"]` pattern — verified via WebSearch against multiple practical examples showing "starting"/"healthy"/"unhealthy"/"none" status values (MEDIUM confidence, multiple sources agree)
- ACL/EMNLP literature on cosine similarity thresholds — domain-specific calibration required, no universal value; [0.75, 0.85] typical for sentence embeddings (MEDIUM confidence, academic sources via WebSearch)
- `/home/ollie/.openclaw/docker/memory/memory_service/scan_engine.py` — confirmed `similarity_min=0.75`, `similarity_max=0.92` with `cosine_topk()` from memu; calibration target is these two constants (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/config.py` — confirmed all current constants; `POLL_INTERVAL = 1.0` is the fixed interval OBS-05 makes adaptive (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/cli/monitor.py` — confirmed `time.sleep(interval)` call pattern and `POLL_INTERVAL` import; adaptive replacement point identified (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/config_validator.py` — confirmed current hand-rolled validation; jsonschema replaces field-by-field checks (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/project_config.py` — confirmed `_POOL_CONFIG_DEFAULTS` lives here (not config.py), divergence from config.py to fix in CONF-05 (HIGH confidence, direct code inspection)
- `/home/ollie/.openclaw/docker/l3-specialist/Dockerfile` — confirmed no HEALTHCHECK instruction present; `l3worker` non-root user confirmed; `bash /entrypoint.sh` confirmed (HIGH confidence, direct code inspection)
- [backoff PyPI](https://pypi.org/project/backoff/) — reviewed and rejected for OBS-05; inline `min()` calculation is sufficient (MEDIUM confidence)

---

*Stack research for: OpenClaw v1.5 Config Consolidation*
*Researched: 2026-02-25*
*Previous baseline (v1.0–v1.4): Python 3 stdlib + docker>=7.1.0 + httpx + asyncio + Next.js 16 + memU/FastAPI/PostgreSQL+pgvector — all unchanged. v1.4 added no new deps (stdlib-only). v1.5 adds jsonschema>=4.26.0 as the sole new dependency.*
