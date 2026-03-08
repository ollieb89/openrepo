# Phase 81: Alert & Metrics Accuracy - Research

**Researched:** 2026-03-08
**Domain:** Python dataclass field injection, metrics parameter threading, event type alignment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**GAP-03: project_id injection approach**
- Add `project_id: Optional[str] = None` field to `AutonomyEvent` base dataclass
- Field appears in `to_dict()` output automatically — bridge `_bridge_handler` picks it up via `envelope.get("project_id", "")` — no bridge changes needed
- All call sites in `hooks.py` supply `project_id` from spawn args (confirmed: project_id flows in at hook call time)
- TypeScript side unchanged — `useAlerts.ts` filter `event.project_id === projectId` is already correct; once Python emits real project_id the filter works naturally

**GAP-04: metrics max_concurrent fix**
- Add `project_id: str` parameter to `collect_metrics_from_state()`
- Call `get_pool_config(project_id)` to read per-project `l3_overrides.max_concurrent`
- Only one call site: `write_python_metrics_snapshot()` already has `project_id` — thread it through
- Default fallback: `get_pool_config()` returns `DEFAULT_POOL_MAX_CONCURRENT` (3) for projects without override — correct behavior, no special handling needed
- Scope: `pool.max_concurrent` only — autonomy counters (`active_contexts`, `escalations_24h`) remain hardcoded 0, separate concern

**Test coverage**
- Python unit tests for both fixes:
  - `AutonomyEvent.to_dict()` includes `project_id` when supplied
  - `collect_metrics_from_state(project_id)` returns `max_concurrent` from project config, not hardcoded 3
- Update existing autonomy event test fixtures to pass `project_id` (retrofit for completeness, not just leave as None)
- No TS tests needed (useAlerts filter unchanged)
- No integration or E2E browser tests — unit coverage is sufficient for these bug fixes

**Plan structure**
- Single plan: `81-01-PLAN.md` covering both GAP-03 and GAP-04
- Rationale: small, no interdependency, cleaner to verify together

### Claude's Discretion

None declared.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
Creating new capabilities (e.g., real autonomy counters, E2E browser tests) is out of scope.
</user_constraints>

---

## Summary

Phase 81 closes two integration gaps (GAP-03 and GAP-04) identified in the v2.1 milestone audit. Both are targeted, surgical bug fixes with no new features. GAP-03 fixes `AutonomyEventBus` emitting `project_id='unknown'`, which causes the `useLiveEvents.ts` SSE handler to silently drop autonomy events because its project filter rejects unknown project IDs. GAP-04 fixes `collect_metrics_from_state()` hardcoding `max_concurrent: 3` rather than reading the per-project `l3_overrides.max_concurrent` value.

The fixes are independent. GAP-03 is a one-field addition to `AutonomyEvent` plus threading `project_id` through all hooks.py emit call sites. GAP-04 is a one-parameter addition to `collect_metrics_from_state()` with one threading change in its single call site. Both fixes have clear, existing infrastructure to build on: `get_pool_config()` already handles per-project config reads with safe defaults, and `AutonomyEvent` already uses dataclasses whose fields flow into `to_dict()`.

There is one important event-type alignment detail the planner must be aware of: `AutonomyEscalationTriggered` emits `event_type="autonomy.escalation_triggered"` but the bridge's `EventType` enum only registers `"autonomy.escalation"`. The CONTEXT.md decision states the fix is purely project_id injection, and the success criterion mentions `autonomy.escalation` and `autonomy.state_changed` events specifically. The planner should note that `autonomy.state_changed` IS registered in the bridge, so once project_id is injected those state_changed events will pass the filter. For escalation alerts specifically, `hooks.py` already emits `AutonomyEscalationTriggered` — but its `event_type` string `"autonomy.escalation_triggered"` is not subscribed by the bridge. This means the escalation alert path requires an additional emit of a `"autonomy.escalation"` typed event alongside the escalation_triggered event, OR renaming the event_type in the emit call. See the Critical Finding section below.

**Primary recommendation:** Fix GAP-03 by adding `project_id: Optional[str] = None` to `AutonomyEvent`, thread real project_id through all hooks.py emit call sites, and ensure escalation events reach the bridge with the correct `"autonomy.escalation"` event_type. Fix GAP-04 by adding `project_id: str` to `collect_metrics_from_state()` and threading it from `write_python_metrics_snapshot()`.

---

## Standard Stack

### Core (already in use — no new dependencies)

| Component | Location | Purpose |
|-----------|----------|---------|
| `AutonomyEvent` dataclass | `autonomy/events.py:30` | Base class; field added here propagates to all 8 subclasses |
| `AutonomyEventBus.emit()` | `autonomy/events.py:296` | Calls `event_bus.emit(envelope)` with `event.to_dict()` as envelope |
| `hooks.py` emit call sites | `autonomy/hooks.py` | 6+ call sites; all have `task_id` available, `project_id` must be threaded in |
| `collect_metrics_from_state()` | `metrics.py:29` | Pure function; receives pre-loaded state dict, returns metrics dict |
| `write_python_metrics_snapshot()` | `metrics.py:79` | Only call site of `collect_metrics_from_state()`; already holds `project_id` |
| `get_pool_config(project_id)` | `project_config.py:171` | Reads `l3_overrides.max_concurrent` with validation and default fallback |
| `DEFAULT_POOL_MAX_CONCURRENT` | `config.py:30` | Equals `3`; used by `get_pool_config()` as default when not overridden |

### Testing Infrastructure

| Tool | Command | Scope |
|------|---------|-------|
| pytest + uv | `uv run pytest packages/orchestration/tests/ -v` | All Python tests |
| vitest | `cd packages/dashboard && npm run test` | TS unit tests (not needed for this phase) |
| Target test files | `tests/test_python_metrics_snapshot.py`, `tests/autonomy/test_integration.py` | Existing tests to extend |

---

## Architecture Patterns

### GAP-03: AutonomyEvent project_id Injection

**Pattern: dataclass field with Optional default**

`AutonomyEvent` uses Python dataclasses. Adding a field with `field(default=None)` to the base class:
- Propagates to all 8 subclasses automatically (no subclass changes required)
- Appears in `to_dict()` output because the method explicitly builds the dict from named fields
- `AutonomyEventBus.emit()` calls `event.to_dict()` and passes the result as the envelope to `event_bus.emit()`
- The bridge's `_bridge_handler` calls `envelope.get("project_id", "")` — already present and correct

**Important dataclass field ordering rule:** In Python dataclasses, fields with defaults must come after fields without defaults. `AutonomyEvent` currently has `task_id: str` (no default) and `timestamp: float = field(default_factory=time.time)` (has default). The new `project_id: Optional[str] = None` field must be placed after `task_id` and alongside or after `timestamp`. Recommended position: after `timestamp`, before `event_type`.

**to_dict() scope:** The current `to_dict()` method explicitly constructs a dict with named keys:
```python
def to_dict(self) -> Dict[str, Any]:
    return {
        "event_type": self.event_type,
        "task_id": self.task_id,
        "timestamp": self.timestamp,
        "payload": self.to_payload(),
    }
```
Adding `project_id` to `to_dict()` requires a one-line addition — the field does NOT auto-appear from `asdict()` because `to_dict()` is manually constructed.

**hooks.py call site pattern:** All hooks currently emit like:
```python
AutonomyEventBus.emit(AutonomyStateChanged(
    task_id=task_id,
    old_state="",
    new_state=AutonomyState.PLANNING.value,
    reason="Task spawned, entering planning phase",
))
```
After the fix, all emit calls gain `project_id=project_id`. The `project_id` parameter must be threaded into the hook function signatures that don't currently receive it. `on_task_spawn(task_id, task_spec)` — project_id comes from `task_spec`. `on_container_healthy(task_id)`, `on_task_complete(task_id, result)`, `on_task_failed(task_id, error)` — these do not currently receive project_id; the decision says "project_id flows in at hook call time from spawn args". The planner must decide how to thread it: either add `project_id` parameter to each hook function, or store it in `_context_store` when the context is created in `on_task_spawn`.

**Recommended approach:** Store `project_id` on the `AutonomyContext` (or in a parallel `_project_id_store: Dict[str, str]` keyed by task_id) during `on_task_spawn`, then look it up in subsequent hooks. This avoids changing the signature of `on_container_healthy`, `on_task_complete`, `on_task_failed`.

### GAP-03 Critical Finding: Event Type Mismatch for Escalation Alerts

The success criterion says `autonomy.escalation` events must appear in the dashboard. This requires understanding the event type routing:

| Python event class | `event_type` string emitted | Registered in bridge? | Passes useAlerts filter? |
|---|---|---|---|
| `AutonomyStateChanged` | `"autonomy.state_changed"` | YES (`EventType.AUTONOMY_STATE_CHANGED`) | NO (not in ALERT_EVENT_TYPES) |
| `AutonomyEscalationTriggered` | `"autonomy.escalation_triggered"` | NO — not in EventType enum | N/A — never reaches TS |
| (no current class) | `"autonomy.escalation"` | YES (`EventType.AUTONOMY_ESCALATION`) | YES — in ALERT_EVENT_TYPES |

The `useAlerts.ts` `ALERT_EVENT_TYPES` list contains `'autonomy.escalation'`. The bridge's `EventType` enum has `AUTONOMY_ESCALATION = "autonomy.escalation"`. However, `AutonomyEscalationTriggered.event_type` is `"autonomy.escalation_triggered"` — a string that is NOT registered in the bridge's subscription loop (`for et in EventType: _event_bus.subscribe(et.value, _bridge_handler)`).

**Consequence:** Even after fixing project_id, `AutonomyEscalationTriggered` events will still be dropped by the bridge because the event_bus has no subscriber registered for `"autonomy.escalation_triggered"`.

**Resolution options (planner to decide, keeping "no bridge changes needed" constraint):**
1. In `hooks.py`, when emitting escalation, also emit a synthetic event with `event_type="autonomy.escalation"` directly via `event_bus.emit()` (bypassing `AutonomyEventBus` which would wrap it as `"autonomy.escalation_triggered"`). This matches how other direct event_bus emissions are done.
2. Change `AutonomyEscalationTriggered.event_type` field default to `"autonomy.escalation"` (renames the Python event type to match the bridge's registered string). This is a breaking change if anything subscribes to `"autonomy.escalation_triggered"`.

Option 1 is safer: `hooks.py` already imports `event_bus` via `AutonomyEventBus.emit()`. Adding a direct `event_bus.emit({"event_type": "autonomy.escalation", "project_id": project_id, "task_id": task_id, ...})` alongside the existing emit is minimally invasive and doesn't touch the event class definitions.

### GAP-04: collect_metrics_from_state() Parameter Threading

**Current signature:**
```python
def collect_metrics_from_state(state_dict: Dict[str, Any]) -> Dict[str, Any]:
```

**Target signature:**
```python
def collect_metrics_from_state(state_dict: Dict[str, Any], project_id: str = "") -> Dict[str, Any]:
```

**Body change:** Replace `"max_concurrent": 3` with:
```python
pool_config = get_pool_config(project_id) if project_id else {}
max_concurrent = pool_config.get("max_concurrent", DEFAULT_POOL_MAX_CONCURRENT)
```

**Import:** `get_pool_config` is already imported in `metrics.py` (line 10: `from .project_config import get_pool_config`). Confirmed by reading the file.

**Call site threading:** `write_python_metrics_snapshot()` already has `project_id: str` as its first parameter. Change its internal call from:
```python
python_metrics = collect_metrics_from_state(state_dict)
```
to:
```python
python_metrics = collect_metrics_from_state(state_dict, project_id)
```

**Lock safety preserved:** `get_pool_config()` reads `project.json` (not `workspace-state.json`), so calling it inside the path that originates from `_write_state_locked` is safe — it does not acquire `fcntl.flock()` on the workspace state file. This was confirmed by reviewing `get_pool_config()` which calls `load_project_config()` which reads `projects/<id>/project.json`.

### Anti-Patterns to Avoid

- **Do not call `get_pool_config()` on every metric read.** The function reads from disk. It is called only inside `write_python_metrics_snapshot()` which already has 750ms throttle protection.
- **Do not add `project_id` to `AutonomyEvent.to_dict()` without also adding it to the `__init__`-generated fields.** The dataclass field must be declared in the class body.
- **Do not change `hooks.py` function signatures without checking all callers in `spawn.py` and pool.py.** Verify that the actual callers (in `skills/spawn/spawn.py`) pass project_id consistently.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-project pool config with defaults | Custom config reader | `get_pool_config(project_id)` in `project_config.py:171` | Already handles validation, invalid values, missing project, default fallback — NEVER raises |
| Default max_concurrent value | Magic number `3` | `DEFAULT_POOL_MAX_CONCURRENT` from `config.py` | Single source of truth; `get_pool_config()` already uses it |
| Project_id lookup from task_id | New registry | Store on `AutonomyContext` or in parallel dict during `on_task_spawn` | Context store (`_context_store`) already keyed by task_id |

---

## Common Pitfalls

### Pitfall 1: to_dict() Requires Manual project_id Key

**What goes wrong:** Developer adds `project_id` to `AutonomyEvent` dataclass but expects it to auto-appear in `to_dict()`. It won't — `to_dict()` is manually constructed, not `asdict()`-based.

**How to avoid:** Explicitly add `"project_id": self.project_id` to the dict returned by `to_dict()` in `AutonomyEvent`.

**Verification:** `assert "project_id" in event.to_dict()` in the unit test.

### Pitfall 2: Bridge Doesn't Subscribe to autonomy.escalation_triggered

**What goes wrong:** After adding project_id to `AutonomyEscalationTriggered`, the event still never reaches the dashboard because the bridge only subscribes to `EventType` values, and `"autonomy.escalation_triggered"` is not one of them.

**How to avoid:** Emit a `"autonomy.escalation"` typed event in `hooks.py` when escalation occurs, via direct `event_bus.emit()` call. Do not rely solely on `AutonomyEventBus.emit(AutonomyEscalationTriggered(...))` for the alert path.

**Warning sign:** Dashboard shows no escalation alerts even after project_id fix is applied. Check bridge's subscription list matches the emitted event_type strings.

### Pitfall 3: Dataclass Field Ordering with Defaults

**What goes wrong:** Adding `project_id: Optional[str] = None` before `task_id: str` (no default) in `AutonomyEvent` raises `TypeError: non-default argument 'task_id' follows default argument` at import time.

**How to avoid:** Place `project_id: Optional[str] = None` after all non-default fields. In `AutonomyEvent`, after `timestamp` is correct placement.

### Pitfall 4: collect_metrics_from_state Callers Broken by New Parameter

**What goes wrong:** Adding `project_id` as required (non-default) parameter breaks existing test callers that pass only `state_dict`.

**How to avoid:** Use `project_id: str = ""` with a default empty string. Empty string triggers `DEFAULT_POOL_MAX_CONCURRENT` fallback in `get_pool_config()` (which handles missing project gracefully and logs a warning). Existing tests continue to work unmodified.

### Pitfall 5: Subclass from_dict() Methods Don't Pass project_id

**What goes wrong:** Each subclass `from_dict()` constructs `cls(task_id=..., timestamp=..., ...)` explicitly. If `project_id` is added to the base but subclass `from_dict()` methods don't pass it, deserialization loses it.

**How to avoid:** Update each subclass `from_dict()` to include `project_id=data.get("project_id")`. There are 8 subclasses (AutonomyStateChanged, AutonomyConfidenceUpdated, AutonomyEscalationTriggered, AutonomyRetryAttempted, AutonomyPlanGenerated, AutonomyProgressUpdated, AutonomyToolsSelected, AutonomyCourseCorrection). Round-trip serialization tests catch this.

---

## Code Examples

### GAP-03: AutonomyEvent base class field addition

```python
# Source: packages/orchestration/src/openclaw/autonomy/events.py (current structure)
@dataclass
class AutonomyEvent(ABC):
    task_id: str
    timestamp: float = field(default_factory=time.time)
    project_id: Optional[str] = None          # ADD THIS FIELD
    event_type: str = field(default="autonomy.base", init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "project_id": self.project_id,    # ADD THIS LINE
            "payload": self.to_payload(),
        }
```

### GAP-03: hooks.py emit call site pattern (after fix)

```python
# Source: packages/orchestration/src/openclaw/autonomy/hooks.py (after fix)
AutonomyEventBus.emit(AutonomyStateChanged(
    task_id=task_id,
    project_id=project_id,    # ADD project_id to all emit calls
    old_state="",
    new_state=AutonomyState.PLANNING.value,
    reason="Task spawned, entering planning phase",
))
```

### GAP-03: Escalation alert path (direct event_bus emit)

```python
# hooks.py on_task_failed — emit "autonomy.escalation" via event_bus directly
# so bridge (subscribed to EventType.AUTONOMY_ESCALATION) forwards it to dashboard
from openclaw import event_bus as _event_bus
_event_bus.emit({
    "event_type": "autonomy.escalation",
    "project_id": project_id,
    "task_id": task_id,
    "timestamp": time.time(),
    "payload": {"reason": error, "confidence": context.confidence_score},
})
```

### GAP-04: collect_metrics_from_state() after fix

```python
# Source: packages/orchestration/src/openclaw/metrics.py (after fix)
def collect_metrics_from_state(
    state_dict: Dict[str, Any],
    project_id: str = "",          # ADD PARAMETER
) -> Dict[str, Any]:
    ...
    pool_cfg = get_pool_config(project_id) if project_id else {}
    max_concurrent = pool_cfg.get("max_concurrent", DEFAULT_POOL_MAX_CONCURRENT)
    ...
    return {
        ...
        "pool": {
            "active_containers": in_progress,
            "max_concurrent": max_concurrent,   # WAS: hardcoded 3
        },
        ...
    }
```

### GAP-04: write_python_metrics_snapshot() threading (after fix)

```python
# Source: packages/orchestration/src/openclaw/metrics.py (after fix)
python_metrics = collect_metrics_from_state(state_dict, project_id)  # WAS: collect_metrics_from_state(state_dict)
```

---

## State of the Art

| Current (Broken) | Target (Fixed) | Impact |
|---|---|---|
| `AutonomyEvent.to_dict()` omits `project_id` | `to_dict()` includes `"project_id": self.project_id` | Events pass `useLiveEvents.ts` project filter |
| `hooks.py` emits with no project_id argument | All emit calls pass `project_id=project_id` | Events routed to correct per-project alert feed |
| `AutonomyEscalationTriggered` event_type not bridge-registered | Direct emit of `"autonomy.escalation"` typed event in hooks.py | Escalation appears in dashboard alert feed |
| `collect_metrics_from_state()` hardcodes `max_concurrent: 3` | Reads `get_pool_config(project_id)["max_concurrent"]` | `/api/metrics` returns correct per-project value |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (uv run) |
| Config file | `packages/orchestration/pyproject.toml` |
| Quick run command | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py packages/orchestration/tests/autonomy/ -x -q` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |

### Phase Requirements → Test Map

This phase closes GAP-03 and GAP-04. No formal requirement IDs are assigned (they are integration gap closures). The behavioral assertions are:

| Gap | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| GAP-03a | `AutonomyEvent.to_dict()` includes `project_id` when set | unit | `uv run pytest packages/orchestration/tests/autonomy/ -k "project_id" -x` | Wave 0 — new test |
| GAP-03b | `AutonomyStateChanged` emitted from `on_task_spawn` includes real project_id | unit | `uv run pytest packages/orchestration/tests/autonomy/test_integration.py -x` | Exists — extend |
| GAP-03c | Escalation path emits `"autonomy.escalation"` typed event | unit | `uv run pytest packages/orchestration/tests/autonomy/test_integration.py -k "escalat" -x` | Exists — extend |
| GAP-04a | `collect_metrics_from_state(state_dict, project_id)` returns project's `max_concurrent` | unit | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -x` | Exists — extend |
| GAP-04b | `collect_metrics_from_state(state_dict)` (no project_id) returns default 3 | unit | `uv run pytest packages/orchestration/tests/test_metrics_lifecycle.py -x` | Exists — extend |
| GAP-04c | `collect_metrics_from_state(state_dict, "proj-with-override")` returns override value | unit | `uv run pytest packages/orchestration/tests/test_metrics_lifecycle.py -k "override" -x` | Wave 0 — new test |

### Specific Test Strategies

**GAP-03: project_id in AutonomyEvent.to_dict()**

New unit test in `tests/autonomy/` (or extend `test_integration.py`):
```python
def test_to_dict_includes_project_id():
    event = AutonomyStateChanged(
        task_id="t1",
        project_id="my-project",
        old_state="planning",
        new_state="executing",
        reason="test",
    )
    d = event.to_dict()
    assert d["project_id"] == "my-project"

def test_to_dict_project_id_none_by_default():
    event = AutonomyStateChanged(task_id="t1", old_state="", new_state="planning", reason="")
    d = event.to_dict()
    assert d.get("project_id") is None  # or absent — either is acceptable
```

**GAP-03: hooks.py project_id threading**

Extend `tests/autonomy/test_integration.py` — mock `event_bus.emit` and assert envelopes contain real project_id:
```python
def test_on_task_spawn_emits_with_project_id(mock_event_bus, clear_hooks_store):
    with patch('openclaw.event_bus.emit') as mock_emit:
        mock_emit.side_effect = mock_event_bus.emit
        hooks.on_task_spawn("task-001", {"project_id": "proj-alpha", "max_retries": 1})
        emitted = mock_event_bus.get_events("autonomy.state_changed")
        assert emitted[0]["project_id"] == "proj-alpha"
```

**GAP-03: Escalation alert event type**

```python
def test_on_task_failed_emits_autonomy_escalation_event(mock_event_bus, clear_hooks_store):
    hooks.on_task_spawn("task-002", {"project_id": "proj-beta", "max_retries": 0})
    with patch('openclaw.event_bus.emit') as mock_emit:
        mock_emit.side_effect = mock_event_bus.emit
        hooks.on_task_failed("task-002", "out of memory")
    escalation_events = mock_event_bus.get_events("autonomy.escalation")
    assert len(escalation_events) >= 1
    assert escalation_events[0]["project_id"] == "proj-beta"
```

**GAP-04: max_concurrent from project config**

Extend `tests/test_python_metrics_snapshot.py` or `tests/test_metrics_lifecycle.py`:
```python
def test_collect_metrics_returns_project_max_concurrent(tmp_path, monkeypatch):
    # Write a project.json with l3_overrides.max_concurrent = 5
    projects_dir = tmp_path / "projects" / "testproj"
    projects_dir.mkdir(parents=True)
    (projects_dir / "project.json").write_text(
        json.dumps({"l3_overrides": {"max_concurrent": 5}})
    )
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
    state_dict = {"tasks": {}, "metadata": {}}
    metrics = collect_metrics_from_state(state_dict, "testproj")
    assert metrics["pool"]["max_concurrent"] == 5

def test_collect_metrics_default_when_no_project_id():
    state_dict = {"tasks": {}, "metadata": {}}
    metrics = collect_metrics_from_state(state_dict)
    assert metrics["pool"]["max_concurrent"] == 3  # DEFAULT_POOL_MAX_CONCURRENT
```

**Manual verification steps** (if bridge is running):
1. Trigger an autonomy state change via `hooks.on_task_spawn("task-x", {"project_id": "pumplai", "max_retries": 0})`
2. Open dashboard at `http://localhost:6987` with project `pumplai` selected
3. Confirm alert appears in the per-project alert feed
4. Call `GET /api/metrics?project=pumplai` and confirm `python.pool.max_concurrent` matches the value in `projects/pumplai/project.json` → `l3_overrides.max_concurrent`

### Sampling Rate

- **Per task commit:** `uv run pytest packages/orchestration/tests/autonomy/ packages/orchestration/tests/test_python_metrics_snapshot.py -x -q`
- **Per wave merge:** `uv run pytest packages/orchestration/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] New test: `AutonomyEvent.to_dict()` includes `project_id` key — extend `tests/autonomy/test_integration.py` or add to `tests/autonomy/test_state_machine.py`
- [ ] New test: `collect_metrics_from_state(state_dict, "project-with-override")` returns override `max_concurrent` — extend `tests/test_python_metrics_snapshot.py`
- [ ] Retrofit: existing `tests/autonomy/test_integration.py` fixtures — update `on_task_spawn` calls to pass `project_id` in `task_spec`

---

## Open Questions

1. **How does hooks.py receive project_id for mid-lifecycle hooks?**
   - What we know: `on_task_spawn(task_id, task_spec)` receives task_spec which contains project_id per CONTEXT.md. Subsequent hooks (`on_container_healthy`, `on_task_complete`, `on_task_failed`) receive only `task_id`.
   - What's unclear: The planner must decide whether to add `project_id` parameter to subsequent hook signatures, or store it in `_context_store`/a parallel dict during spawn.
   - Recommendation: Store it. Add `project_id: str = ""` to `AutonomyContext.project_id` (if the dataclass supports it) or maintain a `_task_project_map: Dict[str, str]` parallel dict in `hooks.py`. This avoids cascading signature changes in callers (`spawn.py`).

2. **Does spawned L3's task_spec reliably carry project_id?**
   - What we know: CONTEXT.md states "project_id flows in at hook call time from spawn args". The `_project_id_store` or `AutonomyContext` approach sidesteps this question for subsequent hook calls.
   - What's unclear: Whether `task_spec["project_id"]` is always present or sometimes absent.
   - Recommendation: Use `.get("project_id", "")` with empty-string default — graceful degradation; events with empty project_id become `project_id=""` in the envelope, which the bridge converts to `"unknown"` (existing behavior).

3. **Does `useAlerts.ts` filter out events with `project_id="unknown"`?**
   - What we know: `useLiveEvents.ts` line 83: `if (projectId && parsed.project_id && parsed.project_id !== projectId) return;` — if `parsed.project_id` is falsy (empty string or absent), the event passes the filter. If it's `"unknown"`, it only passes if the dashboard is viewing project `"unknown"`.
   - What's unclear: Whether bridge maps `""` to `"unknown"` (yes: `bridge.py:76` `project_id=envelope.get("project_id", "") or "unknown"`).
   - Recommendation: Ensure hooks.py always supplies the real project_id. The empty/unknown fallback should never be needed after the fix.

---

## Sources

### Primary (HIGH confidence)

All findings below are from direct code inspection of the repository.

- `packages/orchestration/src/openclaw/autonomy/events.py` — AutonomyEvent base class, to_dict() implementation, all 8 subclasses, AutonomyEventBus.emit()
- `packages/orchestration/src/openclaw/autonomy/hooks.py` — all emit call sites, _context_store structure, hook function signatures
- `packages/orchestration/src/openclaw/metrics.py` — collect_metrics_from_state() hardcoded 3, write_python_metrics_snapshot() signature and call site
- `packages/orchestration/src/openclaw/project_config.py:171` — get_pool_config() implementation, DEFAULT_POOL_MAX_CONCURRENT import, validation and default fallback
- `packages/orchestration/src/openclaw/config.py:30` — DEFAULT_POOL_MAX_CONCURRENT = 3
- `packages/orchestration/src/openclaw/events/bridge.py` — _envelope_to_event(), _EVENT_TYPE_MAP, ensure_event_bridge() subscription loop
- `packages/orchestration/src/openclaw/events/protocol.py` — EventType enum, AUTONOMY_ESCALATION = "autonomy.escalation", AUTONOMY_STATE_CHANGED = "autonomy.state_changed"
- `packages/orchestration/src/openclaw/event_bus.py` — emit() dispatches by event_type string to registered handlers
- `packages/dashboard/src/lib/hooks/useAlerts.ts` — ALERT_EVENT_TYPES = ['agent.error', 'autonomy.escalation', 'task.escalated', 'task.failed', 'pool.overflow']
- `packages/dashboard/src/lib/hooks/useLiveEvents.ts` — project filter: `if (projectId && parsed.project_id && parsed.project_id !== projectId) return`
- `packages/orchestration/tests/test_python_metrics_snapshot.py` — test patterns for metrics tests
- `packages/orchestration/tests/test_metrics_lifecycle.py` — existing lifecycle test patterns
- `packages/orchestration/tests/autonomy/test_integration.py` — existing autonomy integration test patterns with mock_event_bus

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components read directly from source
- Architecture: HIGH — both fix paths confirmed by reading actual code; no external dependencies
- Pitfalls: HIGH — event type mismatch confirmed by cross-referencing protocol.py EventType enum against AutonomyEscalationTriggered.event_type value
- Event routing gap: HIGH — bridge subscription loop and EventType enum both read directly; mismatch confirmed

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable internal code; no external library dependencies)
