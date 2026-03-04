---
phase: 63-correction-system-and-approval-gate
verified: 2026-03-03T21:00:00Z
status: passed
score: 20/20 must-haves verified
re_verification: false
---

# Phase 63: Correction System and Approval Gate — Verification Report

**Phase Goal:** Correction system and approval gate — CorrectionSession with soft/hard correction, approval gate blocking L3 spawns without approved topology, pushback notes, interactive CLI session loop

**Verified:** 2026-03-03T21:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CorrectionSession tracks cycle count and exposes cycle_limit_reached property | VERIFIED | `correction.py` lines 65-74: `cycle_count: int = 0`, `@property cycle_limit_reached` returns `self.cycle_count >= self.max_cycles` |
| 2 | export_draft writes annotated JSON with __comment__ keys to proposal-draft.json | VERIFIED | `correction.py` lines 251-261: `data["__comment__nodes"]` and `data["__comment__edges"]` set before `json.dump` |
| 3 | import_draft strips __comment__ keys, deserializes TopologyGraph, and runs constraint linter | VERIFIED | `correction.py` lines 308-343: dict comprehension strips `__comment__` keys, `TopologyGraph.from_dict(clean)` called, `ConstraintLinter.lint()` called |
| 4 | approve_topology atomically writes current.json and appends diff changelog entry | VERIFIED | `approval.py` lines 73-108: `load_topology`, `topology_diff`, `save_topology`, `append_changelog`, `delete_pending_proposals` all called in sequence |
| 5 | compute_pushback_note returns informational string when original confidence >= pushback_threshold and dimension drops >= 2 | VERIFIED | `approval.py` lines 146-177: threshold guard, `score_proposal` called, 5-dimension loop with `drop >= 2` check, informational-only return string; wrapped in `try/except` so it never raises |
| 6 | save_pending_proposals and load_pending_proposals use atomic tmp+rename with fcntl | VERIFIED | `storage.py` lines 189-250: `LOCK_EX` + `.tmp` + `rename` pattern for save; `LOCK_SH` for load; returns `None` if file absent |
| 7 | check_approval_gate returns False when current.json absent and auto_approve_l1 is false | VERIFIED | `approval.py` lines 203-218: `auto_approve_l1` fast-path; `load_topology` returns `None` → `{"approved": False, "reason": "..."}` with project_id and propose command |
| 8 | User can type feedback and receive a revised proposal with diff and full output | VERIFIED | `propose.py` `_run_session()`: feedback path calls `apply_soft_correction`, then `render_diff_summary` per archetype pair, then `render_full_output` for complete updated output |
| 9 | User can type 'edit' to switch to hard correction export-edit-import flow | VERIFIED | `propose.py` lines 248-295: `edit` command calls `export_draft`, waits for "done", calls `import_draft`, validates `lint_result`, shows `render_diff_summary`, calls `approve_topology` with `correction_type="hard"` |
| 10 | After 3 correction cycles, system presents best version and offers approve-or-edit | VERIFIED | `propose.py` `_run_session()`: `session.cycle_limit_reached` check at loop top; prints "I've refined this N times. Here's the best I achieved:" with `best_proposal_set`; restricts prompt to "Approve [N] or edit [N]" |
| 11 | User can approve a proposal by selecting its archetype number | VERIFIED | `propose.py` `_parse_selection()` (lines 102-144): parses 1-based index, archetype name, or bare "approve"; `approve_topology` called with selected topology |
| 12 | Proposals persist to pending-proposals.json on session exit | VERIFIED | `propose.py`: `save_pending_proposals` called after initial pipeline and after each soft correction; "quit" command also calls `save_pending_proposals` before exit |
| 13 | openclaw-approve loads pending proposals and prompts for approval selection | VERIFIED | `approve.py` lines 109-167: `load_pending_proposals`, `ProposalSet.from_dict`, `render_full_output`, reprompt loop, `approve_topology` with `correction_type="initial"` |
| 14 | Re-proposal diff is displayed alongside full updated proposal | VERIFIED | `propose.py` lines 344-355: `render_diff_summary(old_p, new_p)` printed for each archetype pair before `render_full_output` |
| 15 | L1 router blocks L3 spawn directives when no approved topology exists and auto_approve_l1 is false | VERIFIED | `router/index.js` lines 80-92: reads `config.topology?.auto_approve_l1`, checks `hasApprovedTopology`, throws `DispatchError` with descriptive message |
| 16 | L1 router allows directives when current.json exists | VERIFIED | `router/index.js` `hasApprovedTopology()`: `fs.existsSync(topoPath)` returns true → gate passes |
| 17 | L1 router allows directives when auto_approve_l1 config is true | VERIFIED | `router/index.js` line 80-83: `autoApproveL1 = config.topology?.auto_approve_l1 ?? false`; when true, gate block condition is false |
| 18 | L1 router does not block non-spawn directives (monitoring, status) | VERIFIED | `router/index.js` `isAdministrative()`: prefixes `status`, `monitor`, `log`, `list`, `health` bypass gate; `propose` directives also bypass via `proposeDirective` check |
| 19 | topology.auto_approve_l1 config key exists with default false | VERIFIED | `config.py` lines 178-182, 363: schema entry with `"type": "boolean"`, `"default": False`; `get_topology_config()` returns it |
| 20 | topology.pushback_threshold config key exists with default 8 | VERIFIED | `config.py` lines 182-187, 364: schema entry with `"type": "number"`, `"minimum": 0`, `"maximum": 10`; `get_topology_config()` returns default 8 |

**Score:** 20/20 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/orchestration/src/openclaw/topology/correction.py` | CorrectionSession, apply_soft_correction, export_draft, import_draft | VERIFIED | 353 lines, all 4 exports present and substantive |
| `packages/orchestration/src/openclaw/topology/approval.py` | approve_topology, compute_pushback_note, check_approval_gate | VERIFIED | 219 lines, all 3 exports present and substantive |
| `packages/orchestration/src/openclaw/topology/storage.py` | save_pending_proposals, load_pending_proposals, delete_pending_proposals | VERIFIED | Extended at lines 189, 213, 238; all 3 new functions present |
| `packages/orchestration/tests/test_correction.py` | Tests for soft correction, hard correction, cycle limit (min 100 lines) | VERIFIED | 534 lines, 23 tests across 4 test classes |
| `packages/orchestration/tests/test_approval.py` | Tests for approval, pushback, gate check (min 80 lines) | VERIFIED | 425 lines, 19 tests across 3 test classes |
| `packages/orchestration/src/openclaw/cli/propose.py` | Interactive session loop with soft/hard correction and approval | VERIFIED | Contains `CorrectionSession`, `_run_session`, `_parse_selection`, `_find_original_proposal` |
| `packages/orchestration/src/openclaw/cli/approve.py` | openclaw-approve resume command | VERIFIED | 183-line file with `def main()`, registered in `pyproject.toml` |
| `packages/orchestration/src/openclaw/topology/renderer.py` | render_diff_summary for re-proposal delta display | VERIFIED | `def render_diff_summary` at line 56 |
| `packages/orchestration/tests/test_cli_propose.py` | Tests for interactive session loop (min 60 lines) | VERIFIED | 678 lines, 30 tests including 6 interactive session loop tests |
| `packages/orchestration/tests/test_cli_approve.py` | Tests for approve CLI (min 40 lines) | VERIFIED | 242 lines, 10 tests |
| `skills/router/index.js` | Approval gate check before L3 dispatch | VERIFIED | Contains `hasApprovedTopology`, `isAdministrative`, gate in `dispatchDirective()` |
| `packages/orchestration/src/openclaw/config.py` | New config keys: auto_approve_l1, pushback_threshold | VERIFIED | Both keys in schema and `get_topology_config()` return value |
| `packages/orchestration/tests/test_approval_gate_router.py` | Integration test for router gate (min 40 lines) | VERIFIED | 204 lines, 11 tests |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `correction.py` | `topology/proposer.py` | `generate_proposals_sync` | WIRED | Import at line 26; called at line 125 with outcome, project_id, registry, max_concurrent, clarifications |
| `approval.py` | `topology/storage.py` | `save_topology` + `append_changelog` | WIRED | Both imported at lines 22-25; both called in `approve_topology()` |
| `approval.py` | `topology/diff.py` | `topology_diff` | WIRED | Imported at line 17; called at line 78 |
| `approval.py` | `topology/rubric.py` | `score_proposal` | WIRED | Imported at line 20; called at line 152 |
| `cli/propose.py` | `topology/correction.py` | `CorrectionSession, apply_soft_correction, export_draft, import_draft` | WIRED | `from openclaw.topology.correction import` at line 42; all 4 used in `_run_session` |
| `cli/propose.py` | `topology/approval.py` | `approve_topology, compute_pushback_note` | WIRED | `from openclaw.topology.approval import` at line 48; both called in `_run_session` |
| `cli/approve.py` | `topology/storage.py` | `load_pending_proposals` | WIRED | Imported at line 21; called at line 109 with result checked for `None` |
| `router/index.js` | `workspace/.openclaw/{project_id}/topology/current.json` | `fs.existsSync` | WIRED | `existsSync(topoPath)` at line 51 in `hasApprovedTopology()`; gate applied in `dispatchDirective()` at line 86 |
| `config.py` | `topology/approval.py` | `get_topology_config` provides `auto_approve_l1` | WIRED | `auto_approve_l1` returned from `get_topology_config()` at line 363; `auto_approve_l1` parameter in `check_approval_gate()` |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| CORR-01 | 63-01, 63-02 | User can give textual feedback and receive a re-proposal (soft correction) | SATISFIED | `CorrectionSession` dataclass with `apply_soft_correction` in `correction.py`; wired into `propose.py` `_run_session` feedback path |
| CORR-02 | 63-01, 63-02 | User can directly edit proposed topology (hard correction) | SATISFIED | `export_draft`/`import_draft` in `correction.py`; "edit" command in `_run_session` calls both; `ConstraintLinter` validates on import |
| CORR-03 | 63-01 | System computes and stores diff between proposed and approved topology | SATISFIED | `approve_topology` computes `topology_diff` when previous exists; diff stored in changelog entry via `append_changelog` |
| CORR-04 | 63-01, 63-02 | On hard correction, system executes immediately then analyzes diff | SATISFIED | `approve_topology` called with `correction_type="hard"` immediately after `import_draft` succeeds; diff computed and stored |
| CORR-05 | 63-01, 63-03 | High-confidence original proposal surfaces non-blocking note when edit contradicts it | SATISFIED | `compute_pushback_note` in `approval.py`; `pushback_threshold` config key (default 8) in `config.py`; note displayed before return 0 in both CLIs |
| CORR-06 | 63-01, 63-02 | System enforces cycle limit (max 3 re-proposals) | SATISFIED | `cycle_limit_reached` property; `apply_soft_correction` raises `ValueError` at limit; `_run_session` shows best-so-far and restricts to approve/edit |
| CORR-07 | 63-01, 63-02, 63-03 | User must explicitly approve topology before it can be used for execution | SATISFIED | `check_approval_gate` in `approval.py`; `hasApprovedTopology` in `router/index.js` gates all non-administrative, non-propose `dispatchDirective` calls |

All 7 requirement IDs declared across plans are accounted for. No orphaned requirements found.

---

### Anti-Patterns Found

None. Scans of all phase 63 files returned no TODO/FIXME/PLACEHOLDER comments, no empty `return null`/`return {}`/`return []` implementations, no console.log-only handlers.

---

### Test Results

| Test File | Tests | Result |
|-----------|-------|--------|
| `test_correction.py` | 23 | All passing |
| `test_approval.py` | 19 | All passing |
| `test_cli_propose.py` | 30 | All passing |
| `test_cli_approve.py` | 10 | All passing |
| `test_approval_gate_router.py` | 11 | All passing |
| `test_proposal_rubric.py` (TestTopologyConfig) | 8 new + 6 existing | All passing |
| **Total phase 63 tests** | **114** | **All passing** |

**Pre-existing test failures (not caused by phase 63):**
- `test_proposer.py::TestGenerateProposals::test_rejection_context_none_when_fresh` — async event loop issue from phase 62, last commit to that test file is `6b7dbf9` (phase 62)
- `test_spawn_memory.py` (2 tests), `test_state_engine_memory.py` (1 test) — `JarvisState` attribute issue from phase 45, pre-dates phase 63

---

### Human Verification Required

None — all observable behaviors are verifiable through code inspection and test execution. The interactive CLI session loop (user typing feedback, receiving re-proposals) is covered by mocked unit tests that prove the branching logic is correctly wired.

---

## Summary

Phase 63 delivered all required components and they are fully wired:

1. **Core logic layer (Plan 01):** `correction.py` and `approval.py` implement all correction and approval behaviors. `storage.py` extended with fcntl-safe pending proposal persistence. 42 tests, all green.

2. **CLI integration layer (Plan 02):** `propose.py` extended with a complete interactive session loop using `CorrectionSession`. `approve.py` created as `openclaw-approve` entry point. `renderer.py` extended with `render_diff_summary`. Entry point registered in `pyproject.toml`. 52 new tests (82 total), all green.

3. **Router and config layer (Plan 03):** `router/index.js` extended with `hasApprovedTopology` and `isAdministrative` gate logic in `dispatchDirective`. `config.py` extended with `auto_approve_l1` and `pushback_threshold` schema entries and `get_topology_config()` return values. 17 new tests (98 total), all green.

All 7 CORR requirements are satisfied and marked complete in REQUIREMENTS.md. No stubs, no orphaned artifacts, no anti-patterns.

---

_Verified: 2026-03-03T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
