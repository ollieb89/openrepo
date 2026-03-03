---
phase: 63-correction-system-and-approval-gate
plan: 03
subsystem: topology
tags: [router, approval-gate, config, tdd, fcntl]
dependency_graph:
  requires:
    - packages/orchestration/src/openclaw/topology/approval.py
    - packages/orchestration/src/openclaw/topology/storage.py
    - skills/router/index.js
  provides:
    - skills/router/index.js (hasApprovedTopology gate)
    - packages/orchestration/src/openclaw/config.py (auto_approve_l1, pushback_threshold)
    - packages/orchestration/tests/test_approval_gate_router.py
  affects:
    - Phase 63 CLI plans (depend on topology config keys)
    - All L3 dispatch paths through the router
tech_stack:
  added:
    - hasApprovedTopology(projectId, workspaceRoot) in router/index.js
    - isAdministrative(directive) in router/index.js
    - auto_approve_l1 (boolean, default False) in OPENCLAW_JSON_SCHEMA and get_topology_config()
    - pushback_threshold (number 0-10, default 8) in OPENCLAW_JSON_SCHEMA and get_topology_config()
  patterns:
    - TDD (red-green): 6+11 tests written before implementation
    - fs.existsSync gate check for topology current.json presence
    - Administrative directive bypass to prevent gate from blocking monitoring
    - Propose directive bypass (propose creates topology, does not require it)
key_files:
  created:
    - packages/orchestration/tests/test_approval_gate_router.py
  modified:
    - skills/router/index.js
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/tests/test_proposal_rubric.py
decisions:
  - "Propose directives bypass the approval gate — they create topology, not consume it"
  - "Admin prefix list: status, monitor, log, list, health — operators must never be gated"
  - "Gate condition is projectId presence: if active_project absent, gate silently passes to avoid breaking bare installs"
  - "hasApprovedTopology and isAdministrative exported from router for testability"
  - "os module added to router (was missing) to resolve os.homedir() for workspaceRoot fallback"
metrics:
  duration: 5min
  completed_date: "2026-03-03"
  tasks_completed: 2
  files_created: 1
  files_modified: 3
  tests_added: 17
  tests_passing: 98
---

# Phase 63 Plan 03: Router Approval Gate and Config Extension Summary

**One-liner:** L1 router gates L3 spawns on topology approval via fs.existsSync(current.json), with admin/propose bypass and new auto_approve_l1 + pushback_threshold config keys.

## What Was Built

### skills/router/index.js (Extended)

Three additions:

- **`isAdministrative(directive)`** — Returns true if directive starts with any of: `status`, `monitor`, `log`, `list`, `health`. Administrative directives bypass the approval gate so operators can always diagnose system state even before topology approval.

- **`hasApprovedTopology(projectId, workspaceRoot)`** — Checks `workspace/.openclaw/<projectId>/topology/current.json` existence via `fs.existsSync()`. Returns true when `approve_topology()` (Python) has previously saved an approved topology. This is the exact file that `save_topology()` writes to.

- **Approval gate in `dispatchDirective()`** — Before any dispatch (gateway or CLI fallback), reads `config.topology?.auto_approve_l1`. If false, and directive is not a propose directive and not administrative, and `projectId` is set, and `hasApprovedTopology()` returns false — throws a `DispatchError` with message: `No approved topology for project '${projectId}'. Run 'openclaw-propose' to generate and approve a topology.`

### packages/orchestration/src/openclaw/config.py (Extended)

Two additions:

- **`OPENCLAW_JSON_SCHEMA`** — `topology.properties` extended with `auto_approve_l1` (boolean, default False) and `pushback_threshold` (number, minimum 0, maximum 10, default 8). `config_validator.py` validates these automatically via the existing schema-driven validation path — no changes needed to the validator itself.

- **`get_topology_config()`** — Extended return dict to include `auto_approve_l1` and `pushback_threshold` with correct defaults. These keys are now consumed by the router (reads `config.topology?.auto_approve_l1`) and by `compute_pushback_note()` (already used `pushback_threshold` argument).

## Tests

**test_proposal_rubric.py::TestTopologyConfig (6 new tests):**
- `test_auto_approve_l1_default_is_false`: get_topology_config() returns False default
- `test_pushback_threshold_default_is_8`: get_topology_config() returns 8 default
- `test_auto_approve_l1_in_schema`: boolean type in OPENCLAW_JSON_SCHEMA
- `test_pushback_threshold_in_schema`: number 0-10 in OPENCLAW_JSON_SCHEMA
- `test_schema_accepts_auto_approve_l1_true`: validator accepts new keys cleanly
- `test_topology_config_reflects_override`: user-configured values returned correctly

**test_approval_gate_router.py (11 new tests):**
- `TestApprovalGateBlocking` (4): blocks on no current.json, returns reason string, reason includes project_id, reason mentions openclaw-propose
- `TestApprovalGatePassing` (2): passes when save_topology has created current.json, passes with manually written current.json
- `TestApprovalGateAutoApprove` (2): auto_approve_l1=True bypasses gate, bypass works without current.json
- `TestApprovalGateConfigIntegration` (3): config keys accessible, types correct, config-driven bypass end-to-end

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing dependency] Added `os` module import to router/index.js**
- **Found during:** Task 2 implementation
- **Issue:** `os.homedir()` used for workspaceRoot fallback but `os` was not imported
- **Fix:** Added `const os = require('os');` alongside existing requires
- **Files modified:** skills/router/index.js
- **Commit:** fc12fca

## Requirements Coverage

| Requirement | Coverage |
|-------------|----------|
| CORR-05 | pushback_threshold config key added with default 8, get_topology_config() returns it |
| CORR-07 | hasApprovedTopology gate in router, check_approval_gate tested end-to-end |

## Self-Check: PASSED

- FOUND: skills/router/index.js contains `hasApprovedTopology` (line 47)
- FOUND: skills/router/index.js contains `existsSync` for current.json check (line 51)
- FOUND: packages/orchestration/src/openclaw/config.py contains `auto_approve_l1`
- FOUND: packages/orchestration/tests/test_approval_gate_router.py (204 lines > 40 min)
- FOUND commit: ce62c33 (RED topology config tests)
- FOUND commit: 59ea212 (feat config extension)
- FOUND commit: 9f3e22f (RED router gate tests)
- FOUND commit: fc12fca (feat router gate implementation)
- 98/98 relevant tests pass
