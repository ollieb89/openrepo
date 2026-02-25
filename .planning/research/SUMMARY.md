# Project Research Summary

**Project:** OpenClaw v1.5 Config Consolidation
**Domain:** AI Swarm Orchestration — configuration hardening and operational polish
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

OpenClaw v1.5 is a technical debt clearance milestone, not a feature milestone. Four milestones of organic growth left the system with three independent path resolution strategies, constants scattered across four modules, config schema that is only partially validated at startup, and three deferred operational items (Docker health checks, cosine threshold calibration, adaptive polling). Research confirms all of this is fixable without new external services and with only one net-new dependency (`jsonschema>=4.26.0`). The recommended approach is a strict build order: consolidate the foundations first (path resolver, constants), then add schema validation and migration tooling, then implement the deferred operational features. The integration test suite ships last to verify the whole config layer end-to-end.

The primary risk in this milestone is the path resolver consolidation. A known divergence exists between where code expects state files and where runtime writes them (`data/workspace/` vs `OPENCLAW_ROOT/workspace/`). Implementing the resolver without a data migration step first will silently discard live state files and reset all delta-sync cursors across all nine registered projects. The mitigation is explicit and non-negotiable: build and validate the migration CLI before touching the path resolver code. Two secondary risks deserve attention: strict startup validation must not block the pool's orphan recovery scan (two-pass startup sequence required), and adaptive polling must define activity as task-status-map diff rather than mtime change (mtime thrashes from activity log rotation every 100 entries).

The deferred operational items (REL-09, QUAL-07, OBS-05) are self-contained and can be implemented in any order once the constants foundation is in place. Docker health checks require a capability-free, lock-free sentinel file approach (not HTTP) because L3 containers have no HTTP server and run with `cap_drop ALL`. Cosine threshold calibration must use real memory exports from a live memU instance — synthetic calibration data does not reflect the actual embedding distribution of structured task-description strings.

## Key Findings

### Recommended Stack

The v1.5 stack is almost entirely the existing stack. The sole net-new dependency is `jsonschema>=4.26.0`, which replaces the existing hand-rolled field-by-field config validator with declarative `Draft7Validator` schema checks. This is the right call at v1.5 scope: the current `config_validator.py` was appropriate when validating two fields, but CONF-02 adds 8+ schema constraints making declarative validation the lower-maintenance choice. All other v1.5 features are stdlib-only: `time.monotonic()` for adaptive polling, Dockerfile `HEALTHCHECK` instruction for REL-09, and pure Python precision/recall math for QUAL-07 calibration.

**Core technologies:**
- `jsonschema>=4.26.0`: Config validation — replaces hand-rolled `config_validator.py` field checks with `Draft7Validator`; pure Python, no C extensions, Python >=3.10 compatible
- `docker>=7.1.0` (existing): Container health status — `container.attrs["State"]["Health"]["Status"]` added via `container.reload()` in existing pool.py client; no version change needed
- `time.monotonic()` (stdlib): Adaptive polling — immune to system clock adjustments; already used in state_engine.py context
- `test -f /tmp/openclaw-healthy` (bash builtin): Docker HEALTHCHECK — capability-free, lock-free, no tool dependencies; appropriate for task-runner containers with no HTTP endpoint
- `argparse` (stdlib): Migration CLI — consistent with all existing CLI modules; do not introduce `click`

**What NOT to use:** `pydantic` (refactors all dict-access callers), `numpy` in orchestration package (15MB+ dep; calibration runs in memory service container where numpy is already present), HTTP `HEALTHCHECK` with `curl` (L3 containers have no port), `APScheduler` (5-line stdlib backoff loop is sufficient).

### Expected Features

The v1.5 feature set divides cleanly into two groups: seven config consolidation items that are the core deliverable, and three deferred v1.4 items that fit naturally here.

**Must have (table stakes — the "Config Consolidation" label requires all seven):**
- CONF-01: Single authoritative path resolver (`get_project_root()` in `project_config.py`; all callers updated) — three divergent strategies currently exist; `spawn.py` line 433 uses a hardcoded depth traversal that breaks on package relocation
- CONF-02: `openclaw.json` schema validation — `gateway`, `memory`, `source_directories`, `channels` fields currently have no validation; bad values propagate silently to runtime errors
- CONF-03: Migration CLI (`openclaw-migrate --dry-run`) — operators need a non-destructive upgrade path; without it, every config schema change is a manual edit risk
- CONF-04: Env var precedence documented and enforced — `OPENCLAW_STATE_FILE` is read in `entrypoint.sh` but ignored by Python; this discrepancy must be resolved, not just documented
- CONF-05: Constants consolidated into `config.py` — pool defaults duplicated in `project_config.py` and `pool.py`; cosine thresholds hardcoded in `scan_engine.py`; `MEMORY_CONTEXT_BUDGET` hardcoded in `spawn.py`
- CONF-06: Strict fail-fast startup validation — both `openclaw.json` and `project.json`; two-pass sequence (parse-permissive before recovery scan, strict before accepting new spawns)
- CONF-07: Config integration test suite — path resolver agreement, validation error messages, env var override semantics, migration CLI idempotency

**Should have (deferred from v1.4, high value-to-cost ratio):**
- REL-09: Docker health checks for L3 containers — file-based sentinel (`touch /tmp/openclaw-healthy`), `--start-period=15s`, capability-free; surfaces in dashboard container list
- QUAL-07: Cosine similarity threshold calibration — `openclaw-health calibrate-thresholds` CLI; outputs recommendations from real memU export; operator decides, system does not auto-adjust
- OBS-05: Adaptive monitor poll interval — 0.5s when active tasks detected, 1.0s in cooldown window (10s after last activity), 5.0s when truly idle; activity signal is task-status-map diff, not mtime

**Defer (v2+):**
- Config versioning / changelog (track which schema version each config file was last migrated to)
- Multi-environment config files (`openclaw.prod.json`) — `${ENV_VAR}` placeholder pattern is the correct existing mechanism
- Auto-hot-reload of `openclaw.json` — startup-time dependencies legitimately require restart
- Automatic cosine threshold learning — no labeled "true conflict" corpus exists yet

### Architecture Approach

v1.5 makes targeted surgical changes to the existing architecture. Two new modules are created as foundations (`constants.py` for all consolidated constants, `path_resolver.py` as the single authoritative path resolver), and `config.py` becomes a backward-compatible re-export shim from `constants.py`. Five existing modules receive additive or import-change modifications. Core components (`state_engine.py`, `snapshot.py`, `memory_client.py`, `soul_renderer.py`) are explicitly untouched. The dashboard receives one additive change: a health status badge on the container list component using `container.attrs["State"]["Health"]["Status"]` already available via the Docker SDK.

**Major components:**
1. `constants.py` (new) — canonical location for all tunable constants; must have zero import-time I/O; config.py re-exports from here for backward compat
2. `path_resolver.py` (new) — single authoritative resolver for `workspace-state.json`, snapshot dirs, soul files; reads optional `data_dir` from `openclaw.json` to resolve the existing `workspace/` vs `data/workspace/` divergence
3. `config_validator.py` (extended) — `validate_openclaw_config()` added alongside existing `validate_project_config()`; two-pass startup: parse-permissive before pool recovery, strict before spawn acceptance
4. `migrate_config.py` (new) — `openclaw-migrate` CLI; acquires `fcntl.LOCK_SH` on source state files; includes container pre-flight check; dry-run mode required
5. `test_config_integration.py` (new) — end-to-end tests for path resolution, validation, env var precedence, migration idempotency; builds last, verifies everything above

### Critical Pitfalls

1. **Path resolver consolidation discards live state files** — the known `workspace/` vs `data/workspace/` divergence means changing the resolver without a data migration step silently returns an empty new path for every project, resetting all task history and delta-sync cursors. Prevention: build and validate the migration CLI (CONF-03) before writing any path resolver code (CONF-01); add a hard failure in `get_state_path()` when the old path exists but the new path does not.

2. **Migration CLI corrupts state during active L3 spawns** — `shutil.copy2()` is not fcntl-aware; copying a state file being written by an active container produces truncated or stale JSON at the destination. Prevention: migration CLI must acquire `fcntl.LOCK_SH` before reading source files; add a container pre-flight check that aborts if any `openclaw-*-l3-*` containers are running; validate destination JSON before declaring success.

3. **Strict startup validation blocks orphan recovery scan** — if `ConfigValidationError` is raised before the pool recovery scan runs, orphaned tasks accumulate indefinitely and may be re-spawned on the next valid start. Prevention: two-pass startup sequence — parse-permissive first (only JSON parse failures abort), recovery scan second, strict schema validation third (blocks new spawn acceptance only).

4. **Adaptive polling thrashes on activity log rotation** — `workspace-state.json` mtime changes on every activity log rotation (every 100 entries), keeping the monitor in 0.5s fast-poll mode permanently if mtime is used as the activity signal. Prevention: activity detection must compare the task-status-map between polls, not mtime change alone.

5. **Docker HEALTHCHECK contends with fcntl lock during SIGTERM drain** — a health check that reads `workspace-state.json` would block on `fcntl.LOCK_EX` held by the SIGTERM handler's `update_task()` call. Prevention: health check must be read-only and lock-free; use `test -f /tmp/openclaw-healthy` sentinel file written by `entrypoint.sh` on startup and removed on SIGTERM.

6. **Constants consolidation introduces import-time I/O** — moving constants from literal values to computed-from-config values at module import time breaks any test that imports orchestration modules without a valid `openclaw.json`. Prevention: `constants.py` must be provably importable with no `OPENCLAW_ROOT` set; validate with a CI smoke test.

7. **Cosine threshold calibration on synthetic data produces wrong threshold** — OpenClaw memories cluster at 0.75–0.92 cosine similarity even when semantically distinct (shared structural patterns). Prevention: calibrate against real memU export of at least 50 memories from an active project; never calibrate against random vectors or manually crafted sentences.

## Implications for Roadmap

Based on research, the architecture's dependency graph mandates a strict 6-phase build order. Foundation phases must precede feature phases; migration tooling must precede the resolver change it enables.

### Phase 1: Constants and Path Resolver Foundations (CONF-01 partial, CONF-05)

**Rationale:** Everything else imports from `constants.py` or calls `path_resolver.py`. Building these first eliminates the need for partial rework in every subsequent phase. This is also the lowest-risk phase: moving literal values between modules and creating a new module that delegates to an existing private function.

**Delivers:** `constants.py` with all consolidated constants (pool defaults, memory budget, cosine thresholds, poll intervals); `path_resolver.py` as a public wrapper around `_find_project_root()`; `config.py` becomes a thin re-export shim; `spawn.py` and `pool.py` imports updated; `monitor.py` `_discover_projects()` uses path resolver instead of `Path(__file__).parent.parent`.

**Addresses:** CONF-01, CONF-05

**Avoids:** Pitfall 7 (import-time I/O) — constants are literal values; CI smoke test gates the phase.

---

### Phase 2: Schema Validation and Env Var Audit (CONF-02, CONF-04, CONF-06)

**Rationale:** Depends on `constants.py` for threshold defaults. Defines "what valid looks like" before the migration CLI references it. Env var audit must be done before documentation is written — the `OPENCLAW_STATE_FILE` inconsistency (read in `entrypoint.sh`, ignored in Python) must be resolved here alongside the path consolidation from Phase 1.

**Delivers:** `validate_openclaw_config()` in `config_validator.py` covering gateway, memory, source_directories; `openclaw.schema.json` as formal documentation; two-pass startup sequence (parse-permissive before recovery scan, strict before spawn); env var precedence documented with `OPENCLAW_STATE_FILE` disposition explicitly decided; optional `data_dir` and `memory.conflict_threshold` added to `openclaw.json`.

**Addresses:** CONF-02, CONF-04, CONF-06

**Avoids:** Pitfall 3 (strict validation blocking recovery scan); Pitfall 8 (env var documentation contradictions).

---

### Phase 3: Cosine Similarity Threshold Calibration (QUAL-07)

**Rationale:** Depends on `constants.py` (CONF-05) for `MEMORY_CONFLICT_SIMILARITY_THRESHOLD` and on the `openclaw.json` memory stanza extensions from Phase 2 to support `conflict_threshold` override. Self-contained change to `memory_health.py` (parameterize threshold) plus new `cli/health.py`.

**Delivers:** `memory_health.py` accepts `conflict_threshold` as a parameter; `get_memory_health_config()` helper in `project_config.py`; `openclaw-health calibrate-thresholds --project <id>` CLI that exports real memory embeddings, computes pairwise similarities, and outputs a precision/recall tradeoff table.

**Addresses:** QUAL-07

**Avoids:** Pitfall 6 (synthetic calibration data) — CLI designed for real memU exports; production threshold requires operator action against live data.

---

### Phase 4: Docker Health Checks for L3 Containers (REL-09)

**Rationale:** Self-contained Dockerfile and entrypoint.sh changes. Isolated from all other v1.5 phases once `constants.py` provides the health check timeout values. Building fourth allows prior phases to stabilize before adding the container rebuild cost.

**Delivers:** `HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 CMD test -f /tmp/openclaw-healthy` in Dockerfile; `touch /tmp/openclaw-healthy` after staging branch setup in `entrypoint.sh`; `rm -f` in SIGTERM handler; `healthStatus` field in dashboard container API response; health badge in container list component.

**Addresses:** REL-09

**Avoids:** Pitfall 5 (HEALTHCHECK contending with fcntl lock) — sentinel file approach is lock-free; documented as observability-only (not for Docker Compose `service_healthy` dependency chaining).

---

### Phase 5: Adaptive Monitor Poll Interval (OBS-05)

**Rationale:** Depends on `constants.py` (CONF-05) for `POLL_INTERVAL_ACTIVE`, `POLL_INTERVAL_IDLE`, `POLL_BACKOFF_FACTOR`. Change is entirely self-contained within `monitor.py:tail_state()`. Building fifth avoids conflating the path resolver changes in Phase 1 (which also modifies `monitor.py`) with the adaptive logic.

**Delivers:** `_compute_adaptive_interval()` helper in `monitor.py` using task-status-map diff as activity signal; 0.5s fast-poll when active tasks detected, 1.0s cooldown for 10s after last activity, 5.0s idle; `--interval` CLI arg becomes the floor override; CPU usage during sustained idle drops ~70% vs fixed 1.0s polling.

**Addresses:** OBS-05

**Avoids:** Pitfall 4 (adaptive polling thrashes on log rotation) — activity signal is status-map comparison, not mtime; max idle interval capped at 5s.

---

### Phase 6: Migration CLI and Integration Test Suite (CONF-03, CONF-07)

**Rationale:** Migration CLI must reference the final schema (Phase 2) and the canonical path (Phase 1). Integration tests verify the entire config layer end-to-end and can only pass once all prior phases are complete.

**Delivers:** `migrate_config.py` (`openclaw-migrate` CLI) with dry-run mode, `fcntl.LOCK_SH` acquisition, container pre-flight check, destination JSON validation, and backup creation; `test_config_integration.py` covering path resolver agreement across all 9 registered projects, `ConfigValidationError` on bad schemas, env var override semantics, migration idempotency; CI smoke test for import-time I/O safety.

**Addresses:** CONF-03, CONF-07

**Avoids:** Pitfall 1 (path resolver discards state files) — migration CLI is the prevention mechanism; Pitfall 2 (migration corrupts state) — `fcntl.LOCK_SH` and container pre-flight check are the deliverables.

---

### Phase Ordering Rationale

- Phases 1 and 2 are non-negotiable prerequisites: every subsequent phase either imports from `constants.py` or references the canonical schema shape.
- Phase 6 (migration CLI) must be designed in Phase 1 (to understand the path divergence) but fully implemented in Phase 6 (after the final schema is known). The PITFALLS research is explicit: "CONF-03 must be built and validated before CONF-01 is implemented" — Phase 6 delivers the CLI that validates the Phase 1 resolver change is safe to deploy.
- Phases 3, 4, 5 are independent once foundations are in place and can be reordered or parallelized.
- Integration tests (CONF-07) ship in Phase 6 to validate the complete system rather than serving as aspirational specs.

### Research Flags

Phases needing attention during implementation (not additional external research):

- **Phase 1:** Verify `python3 -c "from openclaw.config import LOCK_TIMEOUT"` with no `OPENCLAW_ROOT` before the phase is complete. Confirm actual runtime data path by inspecting `ls /home/ollie/.openclaw/` to resolve the `workspace/` vs `data/workspace/` question before writing `path_resolver.py`.
- **Phase 2:** `OPENCLAW_STATE_FILE` disposition requires a design decision during implementation (promote to Python or mark container-internal). No external research needed — architectural judgment call.
- **Phase 3:** Calibration tool must be run against a live memU instance with real project memories before committing the updated `MEMORY_CONFLICT_SIMILARITY_THRESHOLD` constant. Operator action, not a code question.
- **Phase 4:** Verify health check command accessibility under UID 1000 with `cap_drop ALL` during integration testing: `docker exec --user 1000 <container> test -f /tmp/openclaw-healthy`.
- **Phase 6:** Migration CLI must be smoke-tested against the actual `data/workspace/` divergence on the live `.openclaw` instance before being declared production-ready.

Phases with well-documented standard patterns (no additional research needed):
- **Phase 5 (adaptive polling):** Exponential backoff is a well-established pattern; activity signal definition is a straightforward implementation detail.
- **Phase 4 (Docker HEALTHCHECK):** File-based sentinel pattern is verified from official Docker documentation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All stack decisions verified against codebase, PyPI, and official docs. One new dependency (`jsonschema>=4.26.0`) is unambiguous. `numpy` exclusion from orchestration confirmed as correct. |
| Features | HIGH | All 10 features (CONF-01..07, REL-09, QUAL-07, OBS-05) verified against codebase and requirement IDs in PROJECT.md. Feature dependencies mapped from actual import analysis. Anti-features explicitly confirmed (hot-reload, pydantic, CWD auto-detection). |
| Architecture | HIGH | All integration points verified via direct code inspection. File structure delta, build order, and component boundaries derived from actual module analysis. `state_engine.py`, `snapshot.py`, `memory_client.py`, `soul_renderer.py` confirmed untouched. |
| Pitfalls | HIGH (code-derived), MEDIUM (operational) | Code-derived pitfalls (path divergence, import-time I/O, fcntl contention) are HIGH — verified from codebase. Operational pitfalls (cosine threshold distribution, Docker HEALTHCHECK signal interaction) are MEDIUM — well-sourced but require empirical confirmation. |

**Overall confidence: HIGH**

### Gaps to Address

- **`data/workspace/` vs `OPENCLAW_ROOT/workspace/` canonical path:** The exact resolution strategy for the `data_dir` field in `openclaw.json` must be confirmed against the actual runtime data location before Phase 1 code is written. Run `ls /home/ollie/.openclaw/` to determine where state files actually live.

- **`OPENCLAW_STATE_FILE` disposition:** Before Phase 2 documentation is written, decide whether this env var is promoted to Python-level support (requires `get_state_path()` update) or marked as container-internal only (requires `entrypoint.sh` rename or documentation caveat). Both paths are valid; the decision just needs to be explicit.

- **Cosine threshold production value:** QUAL-07 can be implemented fully in Phase 3, but the `MEMORY_CONFLICT_SIMILARITY_THRESHOLD` constant cannot be updated from its current value (0.92) until the calibration tool is run against real memU data. This is an operator action that may lag Phase 3 code completion.

- **`pool.py` `_POOL_DEFAULTS` vs `project_config.py` `_POOL_CONFIG_DEFAULTS` divergence check:** Both dicts exist and may have diverged. Verify their contents are identical before Phase 1 consolidation to confirm the merge is lossless: `grep -A10 "_POOL_DEFAULTS\|_POOL_CONFIG_DEFAULTS" packages/orchestration/src/openclaw/project_config.py skills/spawn/pool.py`.

## Sources

### Primary (HIGH confidence)
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/config.py` — confirmed all current constants and `POLL_INTERVAL = 1.0` as the fixed baseline
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/project_config.py` — confirmed `_find_project_root()` canonical strategy and `_POOL_CONFIG_DEFAULTS` location
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/config_validator.py` — confirmed current hand-rolled validation scope (agent hierarchy only)
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/cli/monitor.py` — confirmed fixed `time.sleep(interval)` and `POLL_INTERVAL` import
- `/home/ollie/.openclaw/skills/spawn/spawn.py` — confirmed hardcoded `Path(__file__).parent.parent.parent` at line 433
- `/home/ollie/.openclaw/docker/l3-specialist/Dockerfile` — confirmed no HEALTHCHECK, `l3worker` non-root user, `bash /entrypoint.sh` entrypoint
- `/home/ollie/.openclaw/docker/memory/memory_service/scan_engine.py` — confirmed `similarity_min=0.75`, `similarity_max=0.92` hardcoded
- PyPI jsonschema 4.26.0 — pure Python, no C extensions, MIT license, Python >=3.10 compatible (Jan 7 2026)
- [jsonschema official docs](https://python-jsonschema.readthedocs.io/en/stable/validate/) — `Draft7Validator`, `iter_errors()`, `best_match()`
- [Docker HEALTHCHECK docs](https://docs.docker.com/reference/dockerfile/#healthcheck) — `--interval`, `--timeout`, `--start-period`, `--retries`

### Secondary (MEDIUM confidence)
- docker-py SDK docs (7.1.0) — `container.attrs["State"]["Health"]["Status"]` values ("starting"/"healthy"/"unhealthy"/"none")
- [Docker HEALTHCHECK best practices 2026 — OneUptime](https://oneuptime.com/blog/post/2026-01-30-docker-health-check-best-practices/view) — file-based vs HTTP check patterns
- [Docker graceful shutdown and signal handling — OneUptime](https://oneuptime.com/blog/post/2026-01-16-docker-graceful-shutdown-signals/view) — HEALTHCHECK interaction with SIGTERM drain window
- [Cosine similarity thresholds — OpenAI community](https://community.openai.com/t/rule-of-thumb-cosine-similarity-thresholds/693670) — domain-specific calibration required, no universal value
- [Exponential backoff — Better Stack](https://betterstack.com/community/guides/monitoring/exponential-backoff/) — standard adaptive polling pattern
- ACL/EMNLP literature on cosine similarity thresholds — domain-specific calibration required; [0.75, 0.85] typical for sentence embeddings

### Tertiary (LOW confidence)
- Schema evolution patterns from migration literature — applied by analogy; OpenClaw config migration is simpler than database schema evolution and specific patterns need validation during implementation

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
