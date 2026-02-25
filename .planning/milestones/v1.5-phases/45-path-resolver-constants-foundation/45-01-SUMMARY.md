---
phase: 45-path-resolver-constants-foundation
plan: 01
subsystem: orchestration/config
tags: [path-resolver, constants, config, foundation]
dependency_graph:
  requires: []
  provides: [get_project_root, get_state_path, get_snapshot_dir, DEFAULT_POOL_MAX_CONCURRENT, MEMORY_CONTEXT_BUDGET]
  affects: [pool.py, project_config.py, spawn.py, monitor.py]
tech_stack:
  added: []
  patterns: [env-var-first-resolution, compute-only-path-functions, screaming-snake-constants]
key_files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/config.py
decisions:
  - "get_state_path() and get_snapshot_dir() require project_id — no Optional default, no active-project fallback"
  - "OPENCLAW_STATE_FILE env var takes priority in get_state_path() to align with container entrypoint.sh behavior"
  - "_find_project_root() never uses Path(__file__).parent — that resolves to site-packages install location, not live project root"
metrics:
  duration: 46s
  completed: 2026-02-25
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 45 Plan 01: Path Resolver Functions and Consolidated Constants Summary

**One-liner:** Authoritative path resolver functions and pool/memory constants added to config.py as single source of truth, using OPENCLAW_ROOT env-var-first resolution and OPENCLAW_STATE_FILE container alignment.

## What Was Built

Added three path resolver functions and six constants to `packages/orchestration/src/openclaw/config.py`:

**Path Resolver Functions:**
- `_find_project_root() -> Path`: Internal helper. Checks `OPENCLAW_ROOT` env var first, falls back to `~/.openclaw`. Never uses `Path(__file__).parent`.
- `get_project_root() -> Path`: Public API wrapper around `_find_project_root()`. Used by monitor.py for project directory enumeration.
- `get_state_path(project_id: str) -> Path`: Checks `OPENCLAW_STATE_FILE` env var first (container entrypoint.sh alignment), then derives `<root>/workspace/.openclaw/<project_id>/workspace-state.json`. Compute-only.
- `get_snapshot_dir(project_id: str) -> Path`: Derives `<root>/workspace/.openclaw/<project_id>/snapshots`. No env var override. Compute-only.

**Consolidated Constants:**
- `DEFAULT_POOL_MAX_CONCURRENT = 3` (was duplicated in pool.py and project_config.py)
- `DEFAULT_POOL_MODE = "shared"`
- `DEFAULT_POOL_OVERFLOW_POLICY = "wait"`
- `DEFAULT_POOL_QUEUE_TIMEOUT_S = 300`
- `DEFAULT_POOL_RECOVERY_POLICY = "mark_failed"`
- `MEMORY_CONTEXT_BUDGET = 2000` (was hardcoded in spawn.py line 42)

## Verification

All three plan verification commands passed:
1. All new imports succeed
2. Path derivation assertion: `testproj` in path, `workspace-state.json` in path — OK
3. 151 existing tests pass (0 failures, 0 errors)

## Tasks

| # | Name | Commit | Status |
|---|------|--------|--------|
| 1 | Add path resolver functions to config.py | d1632be | Done |
| 2 | Add consolidated constants to config.py | d1632be | Done (same commit — same file, sequential edits) |

## Commits

| Hash | Description |
|------|-------------|
| d1632be | feat(45-01): add path resolver functions to config.py |

## Deviations from Plan

None — plan executed exactly as written. Both tasks edited the same file and were batched into a single write operation and commit, which is equivalent to two sequential commits on the same file.

## Decisions Made

1. **project_id required on path functions** — No `Optional[str]` default, no active-project fallback. Callers must know which project they're operating on. Prevents silent routing errors.
2. **OPENCLAW_STATE_FILE takes priority in get_state_path()** — Container entrypoint.sh sets this env var to point at the mounted workspace state file. Priority alignment prevents path mismatch between container and host code paths.
3. **_find_project_root() avoids Path(__file__).parent** — That resolves to the package install location inside site-packages, not the live OpenClaw project root. Documented in docstring.

## Self-Check: PASSED

- [x] `packages/orchestration/src/openclaw/config.py` exists and has all expected exports
- [x] Commit d1632be exists in git log
- [x] 151 tests pass
