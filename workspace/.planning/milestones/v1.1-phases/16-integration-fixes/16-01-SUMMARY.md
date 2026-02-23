---
phase: 16-integration-fixes
plan: "01"
subsystem: orchestration
tags: [snapshot, soul-renderer, config, cleanup, cfw-02, cfg-04, cfg-06]
dependency_graph:
  requires: [11-01, 12-01]
  provides: [fully-wired project_id threading, clean config.py, $project_name in soul template]
  affects: [orchestration/snapshot.py, orchestration/config.py, orchestration/monitor.py, orchestration/soul_renderer.py, agents/_templates/soul-default.md]
tech_stack:
  added: []
  patterns: [explicit project_id threading, function delegation over inline duplication]
key_files:
  created: []
  modified:
    - orchestration/snapshot.py
    - orchestration/config.py
    - orchestration/monitor.py
    - orchestration/soul_renderer.py
    - orchestration/__init__.py
    - agents/_templates/soul-default.md
    - scripts/verify_phase5_integration.py
decisions:
  - project_id is required with no default in snapshot functions — callers must pass explicitly (TypeError on omission)
  - project_id documented as intentionally reserved for soul-override.md; not consumed in soul-default.md
  - get_state_path removed from monitor.py imports (was imported but never used)
metrics:
  duration: "~3 min"
  completed: "2026-02-23"
  tasks_completed: 3
  files_modified: 7
---

# Phase 16 Plan 01: Integration Wiring Fixes Summary

Complete the cross-phase integration wiring left incomplete by Phases 11 and 12: project_id threading through snapshot functions, branch detection delegation, $project_name in soul template, and deprecated constant removal.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Thread project_id through snapshot functions and delegate branch detection | af9ae82 | orchestration/snapshot.py, scripts/verify_phase5_integration.py |
| 2 | Add $project_name consumption to soul-default.md and audit build_variables() | 26c3bb2 | agents/_templates/soul-default.md, orchestration/soul_renderer.py |
| 3 | Remove deprecated constants and clean up unused imports | e429a2c | orchestration/config.py, orchestration/monitor.py, orchestration/__init__.py |

## What Was Built

**CFG-02:** `capture_semantic_snapshot()` and `cleanup_old_snapshots()` now require an explicit `project_id: str` parameter with no default. The parameter is passed through to `get_snapshot_dir(project_id)` to resolve the per-project snapshot directory. No global default fallback exists — callers that omit it get a `TypeError` immediately.

**CFG-06:** `create_staging_branch()` no longer contains an inline branch detection block (`symbolic-ref` + fallback checks). Replaced with a single delegation: `default_branch = _detect_default_branch(workspace)`. The helper `_detect_default_branch()` was already correct and was being duplicated unnecessarily.

**CFG-04:** `agents/_templates/soul-default.md` HIERARCHY section now includes `- **Project:** $project_name`. `build_variables()` in `soul_renderer.py` now has inline comments documenting all 8 variable usages — `project_id` is explicitly noted as reserved for override files only.

**Deprecated constant removal:** `STATE_FILE` and `SNAPSHOT_DIR` deleted from `config.py`. Unused `import os` and `from pathlib import Path` removed. Only `LOCK_TIMEOUT`, `LOCK_RETRY_ATTEMPTS`, and `POLL_INTERVAL` remain. References purged from `monitor.py` and `orchestration/__init__.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing cleanup] Remove STATE_FILE/SNAPSHOT_DIR from orchestration/__init__.py**
- **Found during:** Task 3
- **Issue:** `__init__.py` re-exported `STATE_FILE` and `SNAPSHOT_DIR` from config — would fail after config cleanup
- **Fix:** Removed both from the import and `__all__` in `__init__.py`
- **Files modified:** orchestration/__init__.py
- **Commit:** e429a2c

**2. [Rule 2 - Unused import] Remove unused get_state_path from monitor.py**
- **Found during:** Task 3 import audit
- **Issue:** `get_state_path` was imported in both branches of the try/except in `monitor.py` but never referenced in the module body
- **Fix:** Removed from both import branches
- **Files modified:** orchestration/monitor.py
- **Commit:** e429a2c

**3. [Rule 2 - Unused import] Remove unused Set from monitor.py and json from soul_renderer.py**
- **Found during:** Task 3 import audit
- **Issue:** `Set` (typing) imported but unused in monitor.py; `json` imported but unused in soul_renderer.py
- **Fix:** Removed both unused imports
- **Files modified:** orchestration/monitor.py, orchestration/soul_renderer.py
- **Commit:** e429a2c

**4. [Rule 1 - Bug] Update verify_phase5_integration.py call site for new required project_id param**
- **Found during:** Task 1 (grep for callers)
- **Issue:** `scripts/verify_phase5_integration.py` line 363 called `capture_semantic_snapshot(task_id, str(workspace_path))` without `project_id` — would break at runtime with TypeError
- **Fix:** Added `verify_project_id = "default"` and passed it as third argument; updated expected_snapshot path to match per-project layout
- **Files modified:** scripts/verify_phase5_integration.py
- **Commit:** af9ae82

## Verification Results

All 4 plan verification checks pass:
- CFG-02: `capture_semantic_snapshot` has required `project_id` parameter — PASS
- CFG-06: `create_staging_branch` delegates to `_detect_default_branch` — PASS
- CFG-04: `soul-default.md` contains `$project_name` — PASS
- Constant cleanup: `STATE_FILE` absent from config — PASS

## Self-Check: PASSED
