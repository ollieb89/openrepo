# Requirements: OpenClaw v1.5

**Defined:** 2026-02-25
**Core Value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## v1.5 Requirements

### Config Consolidation (CONF)

- [ ] **CONF-01**: Operator can rely on a single path resolver function for workspace state — `get_state_path()` and `get_snapshot_dir()` return paths that match where L3 containers actually write
- [ ] **CONF-02**: `openclaw.json` has a documented, validated schema for the OpenClaw runtime section; unknown fields are flagged at startup
- [ ] **CONF-03**: Operator can run `openclaw config migrate` to upgrade an existing `openclaw.json` to the current schema with a dry-run preview
- [ ] **CONF-04**: Env var precedence is explicitly documented in `openclaw.json` comments and enforced uniformly — `OPENCLAW_ROOT` → `OPENCLAW_PROJECT` → `OPENCLAW_LOG_LEVEL` → `OPENCLAW_ACTIVITY_LOG_MAX` resolution order is consistent across all callers
- [ ] **CONF-05**: All shared constants and defaults (pool config, lock timeouts, cache TTL, log levels, memory budget cap) live in `config.py` — no duplicated magic values across modules
- [ ] **CONF-06**: OpenClaw fails at startup with a clear, actionable error if `openclaw.json` or `project.json` contains missing required fields or invalid types
- [ ] **CONF-07**: Config integration tests cover path resolution (state/snapshot paths), env var precedence, fail-fast validation, and pool config fallback — and run with `uv run pytest`

### Reliability (REL)

- [ ] **REL-09**: L3 containers expose a Docker health check endpoint so `docker ps` and monitoring show container health status (healthy/unhealthy/starting)

### Quality (QUAL)

- [ ] **QUAL-07**: Cosine similarity threshold for memory conflict detection is configurable in `openclaw.json` and defaults to a value validated against real workload data (not the placeholder 0.92 from v1.4)

### Observability (OBS)

- [ ] **OBS-05**: Monitor poll interval adapts dynamically — shorter interval when L3 tasks are active, longer interval when swarm is idle — reducing CPU load during quiet periods

## v2 Requirements

### Advanced Memory

- **ADV-07**: Cross-project health aggregation — aggregate memory health across all projects in a single dashboard view
- **ADV-08**: SOUL version history — track accepted SOUL amendments over time with rollback capability
- **ADV-09**: Memory TTL / forgetting — memories expire after configurable time or access count

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-host swarm | Single-host only — out of scope by design |
| Persistent L3 agents | Ephemeral containers by design |
| Prometheus/OpenTelemetry export | Overkill for single-host system |
| Cross-project agent sharing | Conflicts with 1:1 L2-to-project assumption |
| CWD-based project auto-detection | Conflicts with scripts calling openclaw from arbitrary directories |
| GitPython library adoption | Subprocess reduction sufficient for now |
| LLM-generated SOULs at init time | Non-determinism in CLI init operations |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | — | Pending |
| CONF-02 | — | Pending |
| CONF-03 | — | Pending |
| CONF-04 | — | Pending |
| CONF-05 | — | Pending |
| CONF-06 | — | Pending |
| CONF-07 | — | Pending |
| REL-09  | — | Pending |
| QUAL-07 | — | Pending |
| OBS-05  | — | Pending |

**Coverage:**
- v1.5 requirements: 10 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 10 ⚠️

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after initial definition*
