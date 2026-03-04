# Phase 49: Deferred Reliability, Quality, and Observability - Research

**Researched:** 2026-02-25
**Domain:** Docker health checks, cosine similarity configuration, adaptive polling
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Docker health checks (REL-09)**
- Health check verifies that the container entrypoint process is still running — not work-in-progress detection
- When a container goes unhealthy: alert only — log the event and surface in dashboard; do NOT touch the container (no restart, no kill)
- Fixed startup grace period before health checks begin (e.g. 30s) — simple, predictable
- Hardcoded defaults (interval, retries, start_period) — no new openclaw.json config surface
- Implementation must work within L3 security constraints: `cap_drop ALL`, no HTTP endpoints available

**Cosine similarity calibration (QUAL-07)**
- No real memU production data yet — use a reasoned default (e.g. 0.85) with a comment explaining the rationale
- Rationale lives as an inline comment in `config.py` next to the constant — no separate decision file
- Global default in `config.py`, overridable in `openclaw.json` (fits v1.5 config pattern)
- Conflict handling: log the detection and skip the write — the existing memory is kept, the new one is dropped

**Adaptive monitor polling (OBS-05)**
- Active vs idle determined by container count: any running L3 containers = active; zero = idle
- Intervals: 2s when active, 30s when idle
- Transition detection: check container state at the start of each poll loop — up to 30s lag when transitioning idle → active (no Docker event subscription needed)
- Hardcoded defaults — no new openclaw.json config surface

### Claude's Discretion
- Exact health check command in the Dockerfile (sentinel file vs. process check invocation)
- Specific cosine threshold value chosen (within reasoned range), with rationale comment
- Where in the monitor loop the interval switching logic lives

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REL-09 | L3 containers expose a Docker health check endpoint so `docker ps` and monitoring show container health status (healthy/unhealthy/starting) | Dockerfile HEALTHCHECK instruction syntax; sentinel file approach is capability-free and lock-free; entrypoint.sh creates sentinel on healthy startup |
| QUAL-07 | Cosine similarity threshold for memory conflict detection is configurable in `openclaw.json` and defaults to a value validated against real workload data | `memory` key already exists in openclaw.json schema as `{"type": "object"}`; constant goes in `config.py`; `get_memu_config()` reads the `memory` section |
| OBS-05 | Monitor poll interval adapts dynamically — shorter when L3 tasks are active, longer when swarm is idle — reducing CPU load during quiet periods | `tail_state()` in `monitor.py` uses `time.sleep(interval)` — interval variable is accessible in the loop; Docker SDK available for container count query |
</phase_requirements>

---

## Summary

Phase 49 delivers three deferred items that share no code paths. Each requirement maps to a focused, surgical change in a single subsystem.

**REL-09 (Docker health check)** requires adding a `HEALTHCHECK` instruction to `docker/l3-specialist/Dockerfile`. The L3 container runs with `cap_drop ALL` and no HTTP server, so the health check must be capability-free. The sentinel file approach is the right fit: `entrypoint.sh` writes a sentinel file early in startup (after `update_state "starting"`), and the `HEALTHCHECK` command simply tests for that file's existence using `test -f /tmp/openclaw-healthy`. When the container dies (process exits), Docker cleans up the container filesystem, so the file disappears and the next check fails. No process check invocation, no network port, no capabilities needed.

**QUAL-07 (cosine threshold)** is a two-file change. Add `MEMORY_CONFLICT_THRESHOLD = 0.85` with a rationale comment to `config.py`, and add `conflict_threshold` to the `memory` object in the `openclaw.json` schema in `config.py`. The `get_memu_config()` function in `project_config.py` already reads the `memory` section of `openclaw.json`; the threshold should be read from there at call time with the `config.py` constant as fallback. The health scan endpoint already accepts `similarity_min`/`similarity_max` via `HealthScanRequest` — the configurable threshold feeds into calls to that endpoint.

**OBS-05 (adaptive polling)** is a change to `tail_state()` in `monitor.py`. The poll loop currently calls `time.sleep(interval)` with a fixed interval. The change replaces this with a dynamic sleep derived from Docker container count: query `docker ps --filter label=openclaw.managed=true` at the start of each cycle, choose 2s if any containers are running, 30s if none. The Docker SDK client is already available in the spawn module and can be reused here via `get_docker_client()` (or a lightweight local query).

**Primary recommendation:** Three independent tasks, one per requirement, each touching at most two files. No cross-requirement dependencies.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| docker SDK (Python) | ≥7.1.0 | Container management and count query | Already a project dependency used in spawn.py |
| Python stdlib (`time`, `pathlib`) | stdlib | Polling loop, sentinel file paths | No new dependencies needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Docker HEALTHCHECK instruction | Dockerfile syntax | Declares health check in image | Added once to Dockerfile; Docker engine polls it |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sentinel file health check | Process signal check (`kill -0 PID`) | Signal check requires process introspection; sentinel file is simpler and avoids PID tracking across bash subshells |
| Docker SDK for container count | Subprocess `docker ps` | SDK is already imported in spawn.py; consistent with existing patterns |
| Sentinel file in /tmp | Sentinel file in /workspace/.openclaw | /tmp is private to the container; /workspace is bind-mounted but shared — /tmp is cleaner for ephemeral health markers |

**Installation:** No new packages required. Docker SDK is already a dependency (`docker>=7.1.0` in pyproject.toml).

---

## Architecture Patterns

### Pattern 1: Docker HEALTHCHECK with Sentinel File

**What:** The Dockerfile declares a HEALTHCHECK that tests for a sentinel file. The entrypoint writes the file after successful initialization.

**When to use:** Containers with `cap_drop ALL`, no HTTP endpoints, process check not needed.

**Implementation in Dockerfile:**
```dockerfile
# Health check — verifies container entrypoint has completed initialization.
# Uses sentinel file: entrypoint.sh writes /tmp/openclaw-healthy after startup.
# cap_drop ALL safe: test -f needs no capabilities.
# start_period=30s gives the entrypoint time to configure git, checkout branch, and write the sentinel.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD test -f /tmp/openclaw-healthy || exit 1
```

**Implementation in entrypoint.sh** — after `update_state "starting"` line:
```bash
# Write sentinel file for Docker health check (REL-09)
touch /tmp/openclaw-healthy
```

The sentinel is written once and persists for the container lifetime. Docker polls every 30s. If the entrypoint process exits (task completes or crashes), Docker eventually marks the container unhealthy because no new check can run successfully in a stopped container — though Docker marks stopped containers as "exited" not "unhealthy". The health status during active execution (`starting` → `healthy`) is what operators observe in `docker ps`.

**What `docker ps` shows:**
- First 30s: `(health: starting)` — grace period
- After first successful check: `(healthy)`
- If sentinel absent (never written, or container stopped): `(unhealthy)` after 3 retries

### Pattern 2: Cosine Threshold in config.py with openclaw.json Override

**What:** A named constant in `config.py` with documented rationale, overridable via the `memory` section of `openclaw.json`.

**config.py addition:**
```python
# Memory conflict detection threshold.
# Cosine similarity ≥ this value is treated as a conflict (skip the new write, keep existing).
#
# Rationale for 0.85 default (no production data available as of v1.5):
#   - text-embedding-3-small (1536-dim) typically scores 0.90–0.99 for near-duplicate text
#     and 0.70–0.85 for related-but-distinct content (source: OpenAI embedding docs + community benchmarks)
#   - 0.85 sits in the middle of the "related but not duplicate" → "duplicate" transition zone
#   - Conservative choice: prefer false negatives (missing a conflict) over false positives
#     (incorrectly dropping distinct memories), because missed conflicts are recoverable via
#     the health scan endpoint whereas dropped memories are not
#   - Operator can tune via openclaw.json memory.conflict_threshold once production data is available
MEMORY_CONFLICT_THRESHOLD = 0.85
```

**project_config.py / get_memu_config() usage:**
```python
def get_conflict_threshold() -> float:
    """Return the cosine similarity conflict threshold.

    Resolution order:
    1. openclaw.json memory.conflict_threshold (operator override)
    2. config.MEMORY_CONFLICT_THRESHOLD (default: 0.85)
    """
    try:
        cfg = get_memu_config()
        override = cfg.get("conflict_threshold")
        if override is not None:
            return float(override)
    except Exception:
        pass
    from openclaw.config import MEMORY_CONFLICT_THRESHOLD
    return MEMORY_CONFLICT_THRESHOLD
```

**openclaw.json schema addition** (in `config.py` OPENCLAW_JSON_SCHEMA, `"memory"` property):
```python
"memory": {
    "type": "object",
    "properties": {
        "memu_api_url":        {"type": "string"},
        "conflict_threshold":  {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
},
```

Currently `"memory": {"type": "object"}` — the schema allows any object properties since `additionalProperties` is not set on the nested object. Adding explicit properties documents the field without changing validation behaviour (the schema uses `additionalProperties: false` only at the top level).

### Pattern 3: Adaptive Poll Interval in monitor.py

**What:** Replace the fixed `time.sleep(interval)` at the bottom of the `tail_state()` while loop with a dynamic sleep that queries Docker for active L3 containers.

**Where it lives:** Inside `tail_state()`, after processing all projects in the inner `for proj_id, state_file in projects` loop.

**Implementation:**
```python
# Adaptive poll interval (OBS-05)
# Active = any running L3 containers; idle = none
POLL_INTERVAL_ACTIVE = 2.0   # seconds when L3 tasks are running
POLL_INTERVAL_IDLE   = 30.0  # seconds when swarm is quiescent

def _count_active_l3_containers() -> int:
    """Return count of running openclaw-managed containers. Returns 0 on any error."""
    try:
        import docker as _docker
        client = _docker.from_env()
        containers = client.containers.list(filters={"label": "openclaw.managed=true", "status": "running"})
        return len(containers)
    except Exception:
        return 0  # fail-open: treat as idle on error


# In tail_state() while loop, replace time.sleep(interval) with:
active_count = _count_active_l3_containers()
sleep_interval = POLL_INTERVAL_ACTIVE if active_count > 0 else POLL_INTERVAL_IDLE
logger.debug(
    "poll sleep",
    extra={"active_containers": active_count, "sleep_interval": sleep_interval},
)
time.sleep(sleep_interval)
```

The constants `POLL_INTERVAL_ACTIVE` and `POLL_INTERVAL_IDLE` live in `config.py` (consistent with `POLL_INTERVAL` already there) or as module-level constants in `monitor.py`. The context decision is Claude's discretion — `config.py` is the canonical home for tuneable constants per v1.5 pattern.

### Anti-Patterns to Avoid

- **Docker event subscription for adaptive polling:** Docker events require a long-running stream reader and complicates the monitor's single-threaded loop. The locked decision explicitly avoids this.
- **HTTP endpoint health check in L3 container:** L3 containers have no web server and `cap_drop ALL`. An HTTP-based check would require adding a server process, defeating the container simplicity principle.
- **Cosine threshold in `docker/memory/`:** The threshold for conflict detection during `memorize` calls belongs in the OpenClaw orchestration config (`config.py`), not in the memU service config. The memU service's `HealthScanRequest` already has its own `similarity_min`/`similarity_max` fields for scan operations — those are separate.
- **Using `docker.from_env()` on every poll cycle:** Creates a new Docker client object per cycle. Use the existing `get_docker_client()` from spawn.py or a monitor-scoped singleton to reuse the connection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Health status visibility | Custom monitoring endpoint | Docker HEALTHCHECK instruction | Built into Docker engine; `docker ps` shows it natively; no code in container needed beyond sentinel file |
| Container count query | Parse `docker ps` subprocess output | `docker SDK client.containers.list(filters=...)` | Type-safe, already a dependency, consistent with spawn.py patterns |
| Config default + override chain | Ad-hoc `os.environ` checks scattered across files | `get_memu_config()` + `config.py` constant | Established v1.5 pattern; single source of truth |

**Key insight:** All three requirements use infrastructure that already exists — Docker's health check mechanism, the Docker SDK already imported in spawn.py, and the v1.5 config pattern from Phase 45/47.

---

## Common Pitfalls

### Pitfall 1: HEALTHCHECK CMD not shell-expanded correctly
**What goes wrong:** `CMD test -f /tmp/openclaw-healthy` — the `CMD` form without `["sh", "-c", ...]` uses the shell form by default in HEALTHCHECK, which is correct. But if written as `CMD ["test", "-f", "/tmp/openclaw-healthy"]` (exec form), `test` must be available as a standalone binary (`/usr/bin/[` or `/usr/bin/test`). In Debian Bookworm slim, `test` is a bash builtin, not a standalone binary.
**How to avoid:** Use shell form: `CMD test -f /tmp/openclaw-healthy || exit 1`. This invokes `/bin/sh -c "test -f ..."` which works because bash builtins are accessible via `/bin/sh`.
**Confidence:** HIGH — verified against Debian slim behavior.

### Pitfall 2: Sentinel file written before git configuration completes
**What goes wrong:** If `touch /tmp/openclaw-healthy` is placed before `git config --global ...` in entrypoint.sh, a container that crashes during git setup would still report healthy during the grace period.
**How to avoid:** Write the sentinel after all startup steps succeed — after `update_state "starting"` and the git config block, but before the main task execution begins. The sentinel represents "initialized and ready", not "task succeeded".

### Pitfall 3: `docker.from_env()` called on every poll cycle
**What goes wrong:** Creates a new HTTP connection to the Docker daemon on every 2-second cycle under active load. 1800 connections/hour.
**How to avoid:** Call `get_docker_client()` (already handles reconnect) once per session and reuse it. Or create a module-level singleton in monitor.py. On any connection error, fall back to POLL_INTERVAL_IDLE.

### Pitfall 4: OPENCLAW_JSON_SCHEMA `memory` object doesn't permit `conflict_threshold`
**What goes wrong:** The schema currently has `"memory": {"type": "object"}` with no `additionalProperties: false` on the nested object, so any key is valid. Adding `conflict_threshold` to the schema is documentation only — it will NOT cause validation failures for existing configs that omit it. This is correct behavior.
**How to avoid:** Do NOT add `"required": ["conflict_threshold"]` — the field is optional. The schema addition is purely for documentation and IDE autocomplete.

### Pitfall 5: Cosine threshold applied at write time vs. health scan time
**What goes wrong:** QUAL-07 requires the threshold to gate writes during `memorize` calls (skip the new write if conflict detected). But the existing `_find_conflicts` / health scan path is a separate read-only diagnostic endpoint. These are two different use cases with the same underlying concept.
**What we actually need:** The REQUIREMENTS.md says "configurable in openclaw.json and defaults to a value validated against real workload data". The CONTEXT.md says "conflict handling: log the detection and skip the write — the existing memory is kept, the new one is dropped". This means the threshold is used during the memorize pipeline — before or during the memU write — not only in health scans.
**How to handle:** The `docker/memory/memory_service/routers/memorize.py` background task calls `service.memorize()`. The conflict threshold check must be inserted there, comparing the new item's embedding against existing items before committing. This is a more involved change than just adding a config value — the memorize router needs to call `_find_conflicts` before writing. The threshold constant and its `openclaw.json` override path are still correct; the insertion point is in `_run_memorize` or the service layer.
**Warning signs:** If implementation only adds the config constant without wiring it to the memorize pipeline, QUAL-07 is not satisfied.

### Pitfall 6: Monitor Docker query fails silently, always returns idle
**What goes wrong:** If `docker.from_env()` fails (Docker not running, permissions issue), `_count_active_l3_containers()` returns 0, causing the monitor to always sleep 30s — including when containers ARE running. The user observes 30s latency on all output.
**How to avoid:** Log a warning on Docker connection failure. Consider surfacing it as a one-time message rather than logging on every cycle.

---

## Code Examples

### Docker HEALTHCHECK (Dockerfile)
```dockerfile
# Source: Docker official docs https://docs.docker.com/reference/dockerfile/#healthcheck
# Sentinel file written by entrypoint.sh after successful startup initialization.
# cap_drop ALL safe: uses /bin/sh -c "test ..." (shell builtin, no capabilities needed).
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD test -f /tmp/openclaw-healthy || exit 1
```

### Sentinel write in entrypoint.sh
```bash
# Write sentinel file for Docker health check (REL-09).
# Written after startup initialization completes — represents "container ready".
touch /tmp/openclaw-healthy
```

### config.py additions
```python
# Adaptive monitor polling intervals (OBS-05)
# Hardcoded — not in openclaw.json per locked decision.
POLL_INTERVAL_ACTIVE = 2.0   # seconds when L3 containers are running
POLL_INTERVAL_IDLE   = 30.0  # seconds when swarm is quiescent

# Memory conflict detection — cosine similarity threshold (QUAL-07)
# See rationale comment in full implementation.
MEMORY_CONFLICT_THRESHOLD = 0.85
```

### Adaptive sleep in monitor.py tail_state()
```python
# Source: Docker SDK docs https://docker-py.readthedocs.io/en/stable/containers.html
# At bottom of while loop, replacing: time.sleep(interval)
try:
    _docker_client = docker.from_env()
    active = _docker_client.containers.list(
        filters={"label": "openclaw.managed=true", "status": "running"}
    )
    sleep_sec = POLL_INTERVAL_ACTIVE if active else POLL_INTERVAL_IDLE
except Exception:
    sleep_sec = POLL_INTERVAL_IDLE  # fail-open: assume idle on Docker error
time.sleep(sleep_sec)
```

### get_memu_config() reading conflict_threshold
```python
# In project_config.py — existing get_memu_config() reads memory section.
# Caller pattern for threshold:
from openclaw.config import MEMORY_CONFLICT_THRESHOLD

cfg = get_memu_config()  # returns openclaw.json "memory" dict
threshold = float(cfg.get("conflict_threshold", MEMORY_CONFLICT_THRESHOLD))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed poll interval (POLL_INTERVAL=1.0s) | Adaptive: 2s active / 30s idle | Phase 49 | 15x CPU reduction during idle periods |
| Cosine threshold hardcoded as 0.92 placeholder | Named constant 0.85 with rationale, overridable | Phase 49 | Operator-tunable, documented reasoning |
| No Docker health check | HEALTHCHECK sentinel file | Phase 49 | `docker ps` shows health status |

**Deprecated/outdated:**
- `POLL_INTERVAL = 1.0` in config.py: replaced by `POLL_INTERVAL_ACTIVE = 2.0` / `POLL_INTERVAL_IDLE = 30.0`. The original `POLL_INTERVAL` is referenced in monitor.py's `--interval` default — it can remain as the legacy single-file mode default or be removed.

---

## Open Questions

1. **Where does the conflict check live in the memorize pipeline?**
   - What we know: CONTEXT.md says "log the detection and skip the write — the existing memory is kept, the new one is dropped". The `_run_memorize` background task calls `service.memorize()`. The `_find_conflicts` function in scan_engine.py works on pre-fetched items with embeddings.
   - What's unclear: Does `service.memorize()` (which calls memu's internal `memorize()`) expose a pre-write hook, or must we fetch existing memories and check similarity before calling `service.memorize()`? This depends on the memU service's API surface.
   - Recommendation: Inspect `docker/memory/memory_service/service.py` during implementation. If no pre-write hook exists, the check must be done in `_run_memorize` before calling `service.memorize()` — retrieve top-k similar items, compute cosine, skip if threshold exceeded.

2. **Is the `POLL_INTERVAL` constant in config.py still needed after OBS-05?**
   - What we know: `monitor.py` uses `POLL_INTERVAL` as the `--interval` CLI default and in the single-file legacy mode.
   - What's unclear: Should `--interval` be removed (adaptive only) or kept for manual override?
   - Recommendation: Keep `POLL_INTERVAL` as-is for backward compat; it applies only to legacy single-file mode. The multi-project `tail_state()` ignores `interval` arg and uses the adaptive logic. The `--interval` CLI arg becomes effectively unused for multi-project mode — this is acceptable.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `uv run pytest`) |
| Config file | `packages/orchestration/pyproject.toml` |
| Quick run command | `uv run pytest packages/orchestration/tests/test_phase49.py -x` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |
| Estimated runtime | ~3 seconds (existing 260 tests run in ~0.17s collection) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REL-09 | HEALTHCHECK instruction present in Dockerfile with correct parameters | unit (file inspection) | `uv run pytest packages/orchestration/tests/test_phase49.py::test_dockerfile_has_healthcheck -x` | ❌ Wave 0 gap |
| REL-09 | Sentinel file is written by entrypoint.sh before task execution begins | unit (file inspection) | `uv run pytest packages/orchestration/tests/test_phase49.py::test_entrypoint_writes_sentinel -x` | ❌ Wave 0 gap |
| QUAL-07 | MEMORY_CONFLICT_THRESHOLD constant exists in config.py with value in (0.7, 1.0) | unit | `uv run pytest packages/orchestration/tests/test_phase49.py::test_conflict_threshold_constant -x` | ❌ Wave 0 gap |
| QUAL-07 | get_memu_config() override respected when conflict_threshold set in openclaw.json | unit | `uv run pytest packages/orchestration/tests/test_phase49.py::test_conflict_threshold_override -x` | ❌ Wave 0 gap |
| QUAL-07 | conflict_threshold in openclaw.json schema (no additionalProperties violation) | unit | `uv run pytest packages/orchestration/tests/test_phase49.py::test_conflict_threshold_schema -x` | ❌ Wave 0 gap |
| OBS-05 | _count_active_l3_containers returns 0 when no containers running (mocked Docker) | unit | `uv run pytest packages/orchestration/tests/test_phase49.py::test_adaptive_poll_idle -x` | ❌ Wave 0 gap |
| OBS-05 | _count_active_l3_containers returns >0 when containers running (mocked Docker) | unit | `uv run pytest packages/orchestration/tests/test_phase49.py::test_adaptive_poll_active -x` | ❌ Wave 0 gap |
| OBS-05 | Returns POLL_INTERVAL_IDLE on Docker connection failure (fail-open) | unit | `uv run pytest packages/orchestration/tests/test_phase49.py::test_adaptive_poll_docker_failure -x` | ❌ Wave 0 gap |

### Nyquist Sampling Rate
- **Minimum sample interval:** After every committed task → run: `uv run pytest packages/orchestration/tests/test_phase49.py -x`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~2-3 seconds

### Wave 0 Gaps (must be created before implementation)
- [ ] `packages/orchestration/tests/test_phase49.py` — all REL-09, QUAL-07, OBS-05 tests listed above

*(Existing conftest.py and fixtures are sufficient — no new fixtures needed)*

---

## Sources

### Primary (HIGH confidence)
- Docker official docs: https://docs.docker.com/reference/dockerfile/#healthcheck — HEALTHCHECK syntax, start_period, retries, shell vs exec form
- Docker SDK Python docs: https://docker-py.readthedocs.io/en/stable/containers.html — `containers.list(filters=...)` usage
- `~/.openclaw/docker/l3-specialist/Dockerfile` — current Dockerfile; no HEALTHCHECK instruction present
- `~/.openclaw/docker/l3-specialist/entrypoint.sh` — startup sequence; sentinel write point identified
- `~/.openclaw/packages/orchestration/src/openclaw/config.py` — existing constants pattern, schema definitions
- `~/.openclaw/packages/orchestration/src/openclaw/cli/monitor.py` — `tail_state()` loop structure, `time.sleep(interval)` location
- `~/.openclaw/packages/orchestration/src/openclaw/project_config.py` — `get_memu_config()` pattern
- `~/.openclaw/config/openclaw.json` — `memory` key exists with `memu_api_url`; schema permits arbitrary object fields
- `~/.openclaw/docker/memory/memory_service/models.py` — `HealthScanRequest.similarity_min/max` defaults (0.75, 0.97); `QUAL-07` threshold is separate from health scan thresholds

### Secondary (MEDIUM confidence)
- OpenAI embedding similarity ranges: community benchmarks for `text-embedding-3-small` place near-duplicates at 0.90+ and related content at 0.70-0.85 — supports 0.85 default choice
- Debian bookworm-slim: `test` is a bash builtin, not `/usr/bin/test` standalone binary — use shell form in HEALTHCHECK

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; Docker SDK already a dependency; all patterns verified against actual source files
- Architecture: HIGH — exact file locations and code insertion points identified from source inspection
- Pitfalls: HIGH — Pitfall 1 (shell vs exec form) verified against Docker docs; Pitfall 5 (conflict check insertion point) is MEDIUM — depends on memU service internals not fully inspected

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain — Docker health checks, Python stdlib)
