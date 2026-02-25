# Phase 49: Deferred Reliability, Quality, and Observability - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Three items deferred from earlier milestones are delivered:
1. **REL-09** — Docker health checks for L3 containers (visible via `docker ps`)
2. **QUAL-07** — Calibrated cosine similarity threshold for memory conflict detection
3. **OBS-05** — Adaptive monitor polling (short interval when active, long when idle)

Creating new capabilities, adding new config fields beyond the cosine threshold, or changing container lifecycle policy are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Docker health checks (REL-09)
- Health check verifies that the container entrypoint process is still running — not work-in-progress detection
- When a container goes unhealthy: alert only — log the event and surface in dashboard; do NOT touch the container (no restart, no kill)
- Fixed startup grace period before health checks begin (e.g. 30s) — simple, predictable
- Hardcoded defaults (interval, retries, start_period) — no new openclaw.json config surface
- Implementation must work within L3 security constraints: `cap_drop ALL`, no HTTP endpoints available

### Cosine similarity calibration (QUAL-07)
- No real memU production data yet — use a reasoned default (e.g. 0.85) with a comment explaining the rationale
- Rationale lives as an inline comment in `config.py` next to the constant — no separate decision file
- Global default in `config.py`, overridable in `openclaw.json` (fits v1.5 config pattern)
- Conflict handling: log the detection and skip the write — the existing memory is kept, the new one is dropped

### Adaptive monitor polling (OBS-05)
- Active vs idle determined by container count: any running L3 containers = active; zero = idle
- Intervals: 2s when active, 30s when idle
- Transition detection: check container state at the start of each poll loop — up to 30s lag when transitioning idle → active (no Docker event subscription needed)
- Hardcoded defaults — no new openclaw.json config surface

### Claude's Discretion
- Exact health check command in the Dockerfile (sentinel file vs. process check invocation)
- Specific cosine threshold value chosen (within reasoned range), with rationale comment
- Where in the monitor loop the interval switching logic lives

</decisions>

<specifics>
## Specific Ideas

- MEMORY.md note: use task-status-map diff NOT mtime for change detection (mtime thrashes from .bak writes, cursor updates, log rotation) — this aligns with the "container count" approach chosen
- Health check must be capability-free (cap_drop ALL) and lock-free — sentinel file approach noted as viable alternative to process check

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 49-deferred-reliability-quality-and-observability*
*Context gathered: 2026-02-25*
