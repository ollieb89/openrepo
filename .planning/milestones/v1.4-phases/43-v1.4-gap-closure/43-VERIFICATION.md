---
phase: 43-v1.4-gap-closure
verified: 2026-02-25T00:35:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 43: v1.4 Gap Closure Verification Report

**Phase Goal:** Close three wiring gaps from the v1.4 milestone audit — broken dashboard subprocess paths for suggest.py and soul_renderer.py, and register_shutdown_handler() never called from spawn_task().
**Verified:** 2026-02-25T00:35:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/suggestions invokes suggest.py at the correct path (no ENOENT) and populates soul-suggestions.json | VERIFIED | `route.ts` line 53: `path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py')`. ORCHESTRATION_ROOT resolves to `packages/orchestration/src/openclaw`. Target script confirmed present at `/home/ollie/.openclaw/packages/orchestration/src/openclaw/cli/suggest.py`. Old broken path `'orchestration/suggest.py'` absent from all files under `packages/dashboard/src/app/api/suggestions/`. |
| 2 | Accepting a suggestion appends to soul-override.md AND re-renders SOUL.md without silent failure | VERIFIED | `action/route.ts` line 57: `path.join(ORCHESTRATION_ROOT, 'soul_renderer.py')`. Target script confirmed present at `/home/ollie/.openclaw/packages/orchestration/src/openclaw/soul_renderer.py`. rerenderSoul() try/catch preserved (failure logged, accept request continues per Phase 41 plan decision). Append to soul-override.md occurs before rerender call. |
| 3 | When spawn_task() creates a pool and receives SIGTERM, drain_pending_memorize_tasks() is invoked before loop stops | VERIFIED | `pool.py` lines 1103-1108: guard checks `_shutdown_handler_registered`, calls `register_shutdown_handler(loop, pool)` after `run_recovery_scan()` using `asyncio.get_running_loop()`. `register_shutdown_handler()` wires SIGTERM via `loop.add_signal_handler()` which invokes drain. `test_spawn_task_wires_shutdown_handler` passes (7/7 pool shutdown tests pass). |
| 4 | register_shutdown_handler() cannot be called twice even if spawn_task() is invoked more than once (idempotency guard) | VERIFIED | Module-level flag `_shutdown_handler_registered = False` at `pool.py` line 41. `register_shutdown_handler()` sets `global _shutdown_handler_registered = True` as first statement (lines 1030-1031). `spawn_task()` wraps call in `if not _shutdown_handler_registered:` guard. `patch.object(pool_module, "_shutdown_handler_registered", False)` in test confirms attribute is accessible and patchable. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/dashboard/src/app/api/suggestions/route.ts` | ORCHESTRATION_ROOT constant + corrected suggest.py path + startup WARN check | VERIFIED | Line 9: `ORCHESTRATION_ROOT = path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw')`. Line 11-13: `existsSync` startup warn for `cli/suggest.py`. Line 53: `orchestrationPath = path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py')`. |
| `packages/dashboard/src/app/api/suggestions/[id]/action/route.ts` | ORCHESTRATION_ROOT constant + corrected soul_renderer.py path | VERIFIED | Line 9: same ORCHESTRATION_ROOT constant. Line 11-13: `existsSync` startup warn for `soul_renderer.py`. Line 57: `path.join(ORCHESTRATION_ROOT, 'soul_renderer.py')` inside `rerenderSoul()`. |
| `skills/spawn/pool.py` | Module-level _shutdown_handler_registered flag + register_shutdown_handler() call in spawn_task() | VERIFIED | Line 41: `_shutdown_handler_registered = False`. Lines 1030-1031: flag set to True inside `register_shutdown_handler()`. Lines 1103-1108: conditional call in `spawn_task()` with `asyncio.get_running_loop()` and debug log. |
| `packages/orchestration/tests/test_pool_shutdown.py` | Regression test asserting spawn_task() calls register_shutdown_handler() | VERIFIED | `test_spawn_task_wires_shutdown_handler` present at line 151. Patches `_shutdown_handler_registered = False`, mocks pool and config, asserts `mock_register.assert_called_once()`. Test passes. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `packages/dashboard/src/app/api/suggestions/route.ts` | `packages/orchestration/src/openclaw/cli/suggest.py` | `execFileAsync('python3', [path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py')])` | WIRED | Pattern `ORCHESTRATION_ROOT.*cli.*suggest\.py` confirmed at line 53. execFileAsync call is awaited with result read back (line 56-59). Target file exists on disk. |
| `packages/dashboard/src/app/api/suggestions/[id]/action/route.ts` | `packages/orchestration/src/openclaw/soul_renderer.py` | `execFileAsync('python3', [path.join(ORCHESTRATION_ROOT, 'soul_renderer.py')])` | WIRED | Pattern `ORCHESTRATION_ROOT.*soul_renderer\.py` confirmed at line 57. Wrapped in `rerenderSoul()` which is awaited in the accept branch (line 145). Target file exists on disk. |
| `skills/spawn/pool.py:spawn_task` | `skills/spawn/pool.py:register_shutdown_handler` | Direct call inside spawn_task() after pool creation, guarded by _shutdown_handler_registered | WIRED | Pattern `register_shutdown_handler\(loop, pool\)` confirmed at line 1107. Guard `if not _shutdown_handler_registered:` at line 1105. `asyncio.get_running_loop()` used (not deprecated `get_event_loop()`). |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ADV-01 | 43-01-PLAN.md | Pattern extraction engine queries memU for rejection clusters and identifies recurring failure patterns via frequency counting (threshold: ≥3 similar rejections within lookback window) | SATISFIED | suggest.py exists at the correct path and is now reachable via POST /api/suggestions. 11 tests in test_suggest.py and 8 in test_suggest_api.py pass (148 total). REQUIREMENTS.md marks ADV-01 as [x] Complete, Phase 43. |
| ADV-02 | 43-01-PLAN.md | Suggestion generator produces concrete diff-style SOUL amendments with pattern description, evidence count, and exact text to add to soul-override.md | SATISFIED | suggest.py reachable via corrected subprocess path. Implementation substantive (tested in test_suggest.py). REQUIREMENTS.md marks ADV-02 [x] Complete, Phase 43. |
| ADV-03 | 43-01-PLAN.md | Pending suggestions stored in workspace/.openclaw/<project_id>/soul-suggestions.json | SATISFIED | route.ts reads/writes `suggestionsPath(projectId)` = `workspace/.openclaw/<project>/soul-suggestions.json`. Implementation wired and tested. REQUIREMENTS.md marks ADV-03 [x] Complete, Phase 43. |
| ADV-04 | 43-01-PLAN.md | L2 acceptance flow reads pending suggestions and accepts (appends to soul-override.md, re-renders SOUL) or rejects (memorizes rejection reason) | SATISFIED | action/route.ts accept branch appends to soul-override.md then calls rerenderSoul() via corrected path. Reject branch updates status. REQUIREMENTS.md marks ADV-04 [x] Complete, Phase 43. |
| REL-08 | 43-01-PLAN.md | Pending fire-and-forget asyncio memorization tasks are drained (gathered) on pool shutdown instead of silently lost | SATISFIED | register_shutdown_handler() now called from spawn_task() (wired). Idempotency guard prevents double-registration. 7/7 pool shutdown tests pass including new regression test. REQUIREMENTS.md marks REL-08 [x] Complete, Phase 43. |

All 5 requirement IDs from PLAN frontmatter are accounted for. No orphaned requirements found for Phase 43.

### Anti-Patterns Found

None. No TODO/FIXME/PLACEHOLDER/stub patterns detected in any of the four modified files.

### Human Verification Required

#### 1. POST /api/suggestions end-to-end

**Test:** Start the dashboard dev server, navigate to the Suggestions panel for an active project, and click the Run Analysis button.
**Expected:** HTTP 200, suggest.py executes, soul-suggestions.json is populated or updated, results display in UI without a subprocess ENOENT error in dashboard server logs.
**Why human:** Dashboard must be running with a live project and memU service to exercise the full subprocess invocation path.

#### 2. Accept suggestion end-to-end

**Test:** With suggestions populated, accept one through the dashboard UI.
**Expected:** soul-override.md is appended, SOUL.md is re-rendered (check mtime or diff), dashboard shows the suggestion as accepted, no error in server logs for the soul_renderer.py subprocess.
**Why human:** Requires a live project workspace with both soul-override.md and SOUL.md present, plus a running memU service.

#### 3. SIGTERM drain under load

**Test:** Spawn a task via the production runtime that triggers spawn_task(), then send SIGTERM to the process while an in-flight memorize coroutine is pending.
**Expected:** Drain log message appears, pending memorize task completes before loop stops, no silent discard.
**Why human:** Requires a live Docker environment with a running L3 container to create real in-flight memorize tasks.

### Gaps Summary

No gaps found. All four observable truths are verified. All five requirement IDs (ADV-01, ADV-02, ADV-03, ADV-04, REL-08) are satisfied. The full test suite (148/148) passes including the new regression test `test_spawn_task_wires_shutdown_handler`.

---

_Verified: 2026-02-25T00:35:00Z_
_Verifier: Claude (gsd-verifier)_
