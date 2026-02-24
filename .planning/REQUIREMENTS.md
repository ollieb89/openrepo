# Requirements: OpenClaw

**Defined:** 2026-02-24
**Core Value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## v1.2 Requirements

Requirements for Orchestration Hardening milestone. Each maps to roadmap phases.

### Reliability

- [x] **REL-01**: State engine creates backup before every write, restoring from backup on JSON corruption instead of reinitializing empty
- [x] **REL-02**: Project config validates schema on load (project.json required fields, type checking), failing fast with actionable error messages
- [x] **REL-03**: openclaw.json validates agent hierarchy on load (valid reports_to references, level constraints)

### Performance

- [x] **PERF-01**: Docker client connections are reused across spawns via a shared client instance per pool
- [x] **PERF-02**: State engine caches state in memory, only reading from disk on cache miss or external modification
- [x] **PERF-03**: State engine uses write-through caching so that task updates immediately populate the in-memory cache, eliminating redundant disk re-reads after writes
- [x] **PERF-04**: Monitor and dashboard polling use cached state reads (shared locks) without competing with spawn writes

### Observability

- [x] **OBS-01**: All orchestration components use Python logging with structured JSON formatter and configurable log levels
- [x] **OBS-02**: Task lifecycle metrics are tracked: spawn-to-complete duration, lock wait times, retry counts per task
- [ ] **OBS-03**: Pool utilization is tracked: active/queued/completed container counts per project, semaphore saturation
- [x] **OBS-04**: Activity log entries are rotated when exceeding configurable threshold, with old entries archived

### Pool Config

- [ ] **POOL-01**: Per-project concurrency limits configurable via project.json l3_overrides
- [ ] **POOL-02**: Projects can run in isolated pool mode (dedicated containers) vs shared mode (default)
- [ ] **POOL-03**: Queue overflow policy configurable per project (reject, wait, priority)

### Dashboard

- [ ] **DSH-09**: Agent hierarchy view filters by selected project, showing only relevant L2/L3 agents
- [ ] **DSH-10**: Usage metrics panel shows task completion times, pool utilization, and container lifecycle stats

## Future Requirements

Deferred to v1.3+. Tracked but not in current roadmap.

### Reliability (deferred)

- **REL-04**: Graceful shutdown with signal handlers to clean up containers, release locks, flush logs
- **REL-05**: Task recovery on L2 crash (orphaned container cleanup, state file repair)
- **REL-06**: Entrypoint fails properly when CLI runtime missing (not dry-run exit 0)
- **REL-07**: Git commit failures in entrypoint are caught and reported to state

### Performance (deferred)

- **PERF-05**: Entrypoint batches state updates into single Python process instead of 5+ spawns
- **PERF-06**: Snapshot system caches default branch detection across calls
- **PERF-07**: Reduce subprocess count in snapshot.py merge/review workflows

### Observability (deferred)

- **OBS-05**: Adaptive monitor polling intervals per project based on activity frequency

## Out of Scope

| Feature | Reason |
|---------|--------|
| GitPython library adoption | Adds dependency; subprocess reduction sufficient for now |
| Prometheus/OpenTelemetry export | Overkill for single-host system; internal metrics sufficient |
| Multi-host pool distribution | Single-host architecture decision (v1.0) |
| Docker health checks | Requires image rebuild; defer to container hardening milestone |
| Real-time WebSocket metrics | SSE + polling hybrid works (v1.0 decision) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REL-01 | Phase 20 | Complete |
| REL-02 | Phase 20 | Complete |
| REL-03 | Phase 20 | Complete |
| PERF-01 | Phase 21 | Complete |
| PERF-02 | Phase 21 | Complete |
| PERF-03 | Phase 21 | Complete |
| PERF-04 | Phase 21 | Complete |
| OBS-01 | Phase 19 | Complete |
| OBS-02 | Phase 22 | Complete |
| OBS-03 | Phase 22 | Pending |
| OBS-04 | Phase 22 | Complete |
| POOL-01 | Phase 23 | Pending |
| POOL-02 | Phase 23 | Pending |
| POOL-03 | Phase 23 | Pending |
| DSH-09 | Phase 24 | Pending |
| DSH-10 | Phase 24 | Pending |
| PERF-04 (integration) | Phase 25 | Pending |

**Coverage:**
- v1.2 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after Phase 21 Plan 03 gap closure (PERF-03 wording aligned)*
