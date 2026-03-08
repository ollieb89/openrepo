# Phase 81: Alert & Metrics Accuracy - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Two targeted bug fixes closing GAP-03 and GAP-04 from the v2.1 milestone audit:
- **GAP-03**: `AutonomyEventBus` emits with `project_id='unknown'` — events silently dropped by `useAlerts.ts` filter — autonomy escalation alerts never appear in per-project dashboard feed
- **GAP-04**: `collect_metrics_from_state()` hardcodes `max_concurrent: 3` — metrics endpoint always returns 3 regardless of project's `l3_overrides.max_concurrent`

Creating new capabilities (e.g., real autonomy counters, E2E browser tests) is out of scope.

</domain>

<decisions>
## Implementation Decisions

### GAP-03: project_id injection approach
- Add `project_id: Optional[str] = None` field to `AutonomyEvent` base dataclass
- Field appears in `to_dict()` output automatically — bridge `_bridge_handler` picks it up via `envelope.get("project_id", "")` — no bridge changes needed
- All call sites in `hooks.py` supply `project_id` from spawn args (confirmed: project_id flows in at hook call time)
- TypeScript side unchanged — `useAlerts.ts` filter `event.project_id === projectId` is already correct; once Python emits real project_id the filter works naturally

### GAP-04: metrics max_concurrent fix
- Add `project_id: str` parameter to `collect_metrics_from_state()`
- Call `get_pool_config(project_id)` to read per-project `l3_overrides.max_concurrent`
- Only one call site: `write_python_metrics_snapshot()` already has `project_id` — thread it through
- Default fallback: `get_pool_config()` returns `DEFAULT_POOL_MAX_CONCURRENT` (3) for projects without override — correct behavior, no special handling needed
- Scope: `pool.max_concurrent` only — autonomy counters (`active_contexts`, `escalations_24h`) remain hardcoded 0, separate concern

### Test coverage
- Python unit tests for both fixes:
  - `AutonomyEvent.to_dict()` includes `project_id` when supplied
  - `collect_metrics_from_state(project_id)` returns `max_concurrent` from project config, not hardcoded 3
- Update existing autonomy event test fixtures to pass `project_id` (retrofit for completeness, not just leave as None)
- No TS tests needed (useAlerts filter unchanged)
- No integration or E2E browser tests — unit coverage is sufficient for these bug fixes

### Plan structure
- Single plan: `81-01-PLAN.md` covering both GAP-03 and GAP-04
- Rationale: small, no interdependency, cleaner to verify together

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_pool_config(project_id)` in `project_config.py:171` — already reads `l3_overrides.max_concurrent` with validation and default fallback; just needs to be called
- `AutonomyEvent` base dataclass in `autonomy/events.py` — adding a field here propagates to all 5 subclasses (`AutonomyStateChanged`, `AutonomyConfidenceUpdated`, `AutonomyEscalationTriggered`, `AutonomyRetryAttempted`, `AutonomyPlanCreated`)
- `hooks.py` — all emit call sites; `project_id` is available from spawn args at call time

### Established Patterns
- `AutonomyEvent` uses Python dataclasses with `field(default_factory=...)` for defaults — `Optional[str] = None` fits the existing pattern
- `collect_metrics_from_state()` is a pure function receiving state as parameter (no locking) — adding `project_id` param maintains the same pattern; `get_pool_config()` reads project JSON (not workspace-state), safe to call inside write lock
- Bridge `_bridge_handler` at `bridge.py:52` does `envelope.get("project_id", "")` — already handles missing project_id gracefully

### Integration Points
- `autonomy/events.py` -> `autonomy/hooks.py` -> `events/bridge.py` -> Unix socket -> dashboard SSE -> `useLiveEvents.ts` -> `useAlerts.ts`
- `metrics.py:collect_metrics_from_state()` <- `write_python_metrics_snapshot()` <- state engine `_write_state_locked`

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — these are direct bug fixes with clear target behavior defined by the success criteria in ROADMAP.md.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 81-alert-metrics-accuracy*
*Context gathered: 2026-03-08*
