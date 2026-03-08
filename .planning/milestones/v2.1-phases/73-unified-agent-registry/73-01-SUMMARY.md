---
phase: 73-unified-agent-registry
plan: "01"
subsystem: agent-registry
tags:
  - agent-registry
  - drift-detection
  - defaults-inheritance
  - orphan-handling
  - tdd
dependency_graph:
  requires:
    - packages/orchestration/src/openclaw/agent_registry.py (existing)
    - packages/orchestration/src/openclaw/config.py (existing)
  provides:
    - AgentRegistry.all_agents()
    - AgentRegistry._detect_drift()
    - AgentRegistry._detect_orphans()
    - AgentRegistry._apply_defaults()
    - AgentSpec.source field
    - AgentSpec.sandbox field
    - get_agent_registry() in config.py
  affects:
    - Any code importing AgentRegistry (new fields available, behavior unchanged)
    - Startup code calling ensure_gateway() (can now chain with get_agent_registry())
tech_stack:
  added: []
  patterns:
    - TDD (Red-Green cycle with caplog propagation fix)
    - Drift detection via dual-source comparison
    - Defaults inheritance with explicit-set tracking
key_files:
  created:
    - packages/orchestration/tests/test_agent_registry.py
  modified:
    - packages/orchestration/src/openclaw/agent_registry.py
    - packages/orchestration/src/openclaw/config.py
decisions:
  - "Logger propagate=False in get_logger() requires test fixture to re-enable propagation for caplog capture"
  - "Explicit max_concurrent tracking via _explicit_max_concurrent set — only apply default when the dataclass default (3) is still in place AND not explicitly set"
  - "agent_registry.py imports only stdlib — no circular import possible with config.py"
  - "Orphan detection happens in _detect_orphans() after both loads complete, so source='openclaw_json' is the reliable orphan indicator"
metrics:
  duration: "3 minutes"
  completed: "2026-03-04"
  tasks_completed: 2
  files_modified: 3
  tests_added: 21
  tests_total: 742
requirements_satisfied:
  - AREG-01
  - AREG-02
  - AREG-03
---

# Phase 73 Plan 01: Unified Agent Registry Summary

**One-liner:** Enhanced AgentRegistry with drift detection (name/level/reports_to mismatch warnings), defaults inheritance (maxConcurrent + model.primary), orphan detection, and get_agent_registry() startup wiring.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 (RED) | TDD failing tests for AgentRegistry enhancements | d0c33fa | tests/test_agent_registry.py |
| 1 (GREEN) | Enhance AgentRegistry — drift, defaults, orphans, all_agents() | 5cc6009 | agent_registry.py, test_agent_registry.py |
| 2 | Wire AgentRegistry into startup via get_agent_registry() | 11dcfcb | config.py |

## What Was Built

### AgentSpec additions

- `source: str = "unknown"` — tracks config origin: `"openclaw_json"`, `"agents_dir"`, or `"both"`
- `sandbox: Optional[dict] = None` — receives defaults inheritance from `agents.defaults.sandbox`

### AgentRegistry new methods

**`all_agents() -> List[AgentSpec]`** — returns all registered specs sorted by level ascending then id alphabetically. Used by CLI for listing.

**`_detect_drift(spec)`** — called after per-agent config.json is merged. Compares `name`, `level`, `reports_to` against the openclaw.json baseline stored in `_openclaw_json_data`. Emits WARNING per conflicting field with agent id, field name, both values, and `openclaw agent sync` remediation hint.

**`_detect_orphans()`** — called after both load phases complete. Any agent with `source="openclaw_json"` has no per-agent directory and emits WARNING with `openclaw agent init {id}` scaffold hint.

**`_apply_defaults()`** — called last. Reads `agents.defaults` from openclaw.json and applies:
- `defaults.maxConcurrent` → `spec.max_concurrent` (only if not explicitly set by per-agent config)
- `defaults.model.primary` → `spec.model` (only if `spec.model is None`)
- `defaults.sandbox` → `spec.sandbox` (only if `spec.sandbox is None`)

### config.py addition

**`get_agent_registry()`** — canonical factory function. Returns `AgentRegistry(get_project_root())`. Non-fatal if no openclaw.json. Independent of `ensure_gateway()` — callers chain them as needed.

### Behavior changes in `_load_agents_directory()`

- Directories without `agents/{id}/agent/config.json` are now **skipped entirely** (previously would create a bare spec). This enforces the rule: a directory without config.json is not auto-registered.
- Underscore-prefixed directories (e.g., `_templates`) are silently skipped (unchanged behavior, now explicitly tested).
- Warns when `config.json` has an `id` field that differs from the directory name.

## Test Coverage

21 new tests covering:
- Orphan detection (2 tests)
- Drift on name, level, reports_to (4 tests including no-drift case)
- Defaults inheritance for maxConcurrent and model (4 tests)
- Directory without config.json not registered (1 test)
- `_templates` silently skipped (1 test)
- id mismatch in config.json (1 test)
- `all_agents()` return and sorting (3 tests)
- Source field tracking (3 tests)
- Edge cases: no openclaw.json, agents-dir-only (2 tests)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Logger propagate=False prevented caplog capture**
- **Found during:** Task 1 (GREEN phase, first run showed 6 failures)
- **Issue:** `get_logger()` sets `logger.propagate = False` to prevent duplicate JSON output. pytest's `caplog` fixture works via the standard propagation chain, so it could not capture warnings from the structured logger.
- **Fix:** Added `autouse=True` pytest fixture `enable_registry_log_propagation` that temporarily enables propagation (`logger.propagate = True`) on the `openclaw.agent_registry` logger during each test and restores it after.
- **Files modified:** `packages/orchestration/tests/test_agent_registry.py`
- **Commit:** 5cc6009

## Verification Results

```
uv run pytest packages/orchestration/tests/test_agent_registry.py -v
→ 21 passed in 0.20s

uv run pytest packages/orchestration/tests/ -x -q
→ 742 passed in 7.56s (0 failures, 0 regressions)

from openclaw.config import get_agent_registry
get_agent_registry()  # with real repo root
→ AgentRegistry (clawdia_prime registered, drift warnings emitted for real mismatches)
```

## Real-World Validation

Running `get_agent_registry()` on the actual repo discovered:
- `clawdia_prime`: name drift (`"Head of Development"` vs `"ClawdiaPrime - Head of Development"`)
- `pumplai_pm`: name drift (`"PumpLAI Project Manager"` vs `"PumplAI_PM - Domain Project Manager"`)
- `main` agent: name, level, and reports_to drift

These are genuine configuration divergences that the new registry correctly identifies. The `openclaw agent sync` remediation hint guides the operator to resolve them.

## Self-Check: PASSED

Files created/modified:
- FOUND: /home/ob/Development/Tools/openrepo/packages/orchestration/tests/test_agent_registry.py
- FOUND: /home/ob/Development/Tools/openrepo/packages/orchestration/src/openclaw/agent_registry.py
- FOUND: /home/ob/Development/Tools/openrepo/packages/orchestration/src/openclaw/config.py

Commits:
- d0c33fa — test(73-01): add failing tests
- 5cc6009 — feat(73-01): enhance AgentRegistry
- 11dcfcb — feat(73-01): add get_agent_registry()
