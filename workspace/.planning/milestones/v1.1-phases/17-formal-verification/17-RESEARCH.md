# Phase 17: Formal Verification - Research

**Researched:** 2026-02-23
**Domain:** Evidence-based requirement verification — creating VERIFICATION.md documents for Phases 11 and 12 using concrete code evidence (file:line references) after Phase 16 integration fixes
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-01 | Per-project state file at `workspace/.openclaw/<project_id>/workspace-state.json` | `get_state_path(project_id)` returns `workspace/.openclaw/pumplai/workspace-state.json` — path pattern confirmed. `JarvisState._ensure_state_file()` creates parent dirs on first use. Code satisfies requirement; file not present until first container run (expected). |
| CFG-02 | Per-project snapshot directory at `workspace/.openclaw/<project_id>/snapshots/` | `capture_semantic_snapshot()` at `snapshot.py:171` and `cleanup_old_snapshots()` at `snapshot.py:461` both require `project_id: str` (no default) and call `get_snapshot_dir(project_id)` at lines 195 and 473. |
| CFG-03 | `project_config.py` exposes `get_state_path(project_id)` and `get_snapshot_dir(project_id)` | Both functions exist in `orchestration/project_config.py` at lines 100 and 123. Both return per-project paths with `project_id` in the path. Both raise `ProjectNotFoundError` for unknown IDs. |
| CFG-04 | SOUL.md default template with `$project_name` and `$tech_stack_*` substitution points | `agents/_templates/soul-default.md:4` contains `- **Project:** $project_name`. Lines 10-12 contain `$tech_stack_frontend`, `$tech_stack_backend`, `$tech_stack_infra`. All 5 variables render correctly via `string.Template.safe_substitute()`. |
| CFG-05 | Projects can override SOUL.md with a custom file in `projects/<id>/SOUL.md` | `soul_renderer.py:145` checks `projects/<project_id>/soul-override.md`. Override sections replace default sections (not appended). Confirmed working: `projects/pumplai/soul-override.md` overrides HIERARCHY and BEHAVIORAL PROTOCOLS sections. |
| CFG-06 | `snapshot.py` detects default branch dynamically instead of hardcoding `"main"` | `create_staging_branch()` at `snapshot.py:129` calls `_detect_default_branch(workspace)`. No `symbolic-ref` in its body. All 5 git functions (`create_staging_branch`, `l2_review_diff`, `l2_merge_staging`, `l2_reject_staging`, plus `capture_semantic_snapshot`) call `_detect_default_branch`. |
| CFG-07 | Agent `config.json` hierarchy references resolve from project config, not hardcoded strings | `spawn.py:load_l3_config()` at line 47 calls `get_agent_mapping(project_id)` and resolves `l3_agent_id = agent_map.get("l3_executor", "l3_specialist")`. Config path built from resolved `l3_agent_id` at line 55. |

</phase_requirements>

---

## Summary

Phase 17 is a **documentation-only phase** — no code changes required. All 7 CFG requirements were implemented by Phases 11 and 12, with the 3 wiring bugs fixed by Phase 16. The v1.1-MILESTONE-AUDIT.md identified these phases as "Unverified" (plans executed, SUMMARYs exist, but no VERIFICATION.md). Phase 17 closes those verification gaps by writing VERIFICATION.md files with concrete code evidence (file:line references).

The Phase 16 VERIFICATION.md (which already exists at `.planning/phases/16-integration-fixes/16-VERIFICATION.md`) provides the exact format to follow. It demonstrates the expected structure: observable truths table with VERIFIED/FAIL status + evidence, required artifacts, key link verification, requirements coverage, and an anti-patterns section.

All 7 CFG requirements have been verified to be satisfied by the current codebase through direct code inspection and running existing verification scripts (`verify_phase16.py` exits 0 with all 4 checks passing, `verify_soul_golden.py` exits 0 with all checks passing). The task is to document this evidence formally, not to implement anything new.

**Primary recommendation:** Write two VERIFICATION.md files matching the Phase 16 format exactly. Phase 11's VERIFICATION.md covers CFG-01, CFG-02, CFG-03, CFG-06, CFG-07. Phase 12's VERIFICATION.md covers CFG-04, CFG-05. Use concrete file:line references — all evidence already located.

---

## Standard Stack

### Core

| Component | Location | Purpose | Why Used |
|-----------|----------|---------|----------|
| `orchestration/project_config.py` | Lines 100-143 | CFG-01, CFG-02, CFG-03 evidence | Source of `get_state_path()` and `get_snapshot_dir()` implementations |
| `orchestration/snapshot.py` | Lines 20-500 | CFG-02, CFG-06 evidence | Contains `_detect_default_branch()`, `create_staging_branch()`, `capture_semantic_snapshot()`, `cleanup_old_snapshots()` |
| `orchestration/soul_renderer.py` | Lines 81-159 | CFG-04, CFG-05 evidence | `build_variables()`, `render_soul()`, override detection logic |
| `agents/_templates/soul-default.md` | Lines 1-18 | CFG-04 evidence | Default template with `$project_name` and `$tech_stack_*` substitution points |
| `projects/pumplai/soul-override.md` | Entire file | CFG-05 evidence | Concrete override file that proves override mechanism works |
| `skills/spawn_specialist/spawn.py` | Lines 47-55 | CFG-07 evidence | `load_l3_config()` with `get_agent_mapping()` call |
| `.planning/phases/16-integration-fixes/16-VERIFICATION.md` | Entire file | Format template | Canonical example of VERIFICATION.md structure for this project |

### Supporting

| Component | Purpose | When to Reference |
|-----------|---------|------------------|
| `scripts/verify_phase16.py` | Already verifies CFG-02, CFG-04, CFG-06 | Cross-reference: these checks PASS as evidence |
| `scripts/verify_soul_golden.py` | Already verifies CFG-04, CFG-05 rendering | Cross-reference: these checks PASS as evidence |
| `orchestration/state_engine.py:72` | `_ensure_state_file()` creates dirs | CFG-01 "file doesn't exist yet" explanation |

---

## Architecture Patterns

### VERIFICATION.md Format (from Phase 16 example)

```markdown
---
phase: <phase-slug>
verified: <ISO timestamp>
status: passed
score: N/N must-haves verified
re_verification: null
gaps: []
human_verification: []
---

# Phase N: <Name> Verification Report

**Phase Goal:** <one-line goal>
**Verified:** <timestamp>
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | <truth statement> | VERIFIED | <file:line + what the code says> |

**Score:** N/N truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|

### Anti-Patterns Found

(table or "No anti-patterns found")

### Human Verification Required

(list or "None")
```

### What Constitutes Evidence (HIGH confidence)

Based on Phase 16 VERIFICATION.md pattern:
- **For function signatures:** State the exact signature with `project_id: str` (no default) or `Optional[str] = None`
- **For behavior:** State the specific line number where the behavior is implemented
- **For rendered output:** Reference the verification script check that confirms it
- **For file existence:** State the file path and whether it exists on disk

### Anti-Patterns to Avoid for VERIFICATION.md

- **Listing what the PLAN says** instead of what the CODE actually does — verification must cite actual code, not intentions
- **Omitting line numbers** — Phase 16 VERIFICATION.md always includes `:line_N` references
- **Marking as VERIFIED without running the check** — the existing scripts (`verify_phase16.py`, `verify_soul_golden.py`) have already confirmed the evidence is correct; cite those as supporting evidence
- **Conflating "code API exists" with "requirement fully satisfied"** — CFG-01 requires the path PATTERN, not that a specific file exists on disk yet

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| New verification script | New `scripts/verify_phase11.py` or `verify_phase12.py` | Existing `verify_phase16.py` already covers CFG-02, CFG-04, CFG-06 | Phase 17 adds DOCUMENTATION, not new scripts |
| Runtime checks | Execute code to confirm behavior | Cite `inspect.signature()` and `inspect.getsource()` pattern from existing verify scripts | Deterministic, already proved correct |

---

## Common Pitfalls

### Pitfall 1: CFG-01 "File Doesn't Exist" Confusion

**What goes wrong:** The per-project state file `workspace/.openclaw/pumplai/workspace-state.json` does NOT exist on disk (no L3 containers have run against the per-project path). A verifier might mark CFG-01 as FAIL because the file is absent.

**Why it happens:** CFG-01 requires the path CONVENTION be correct, not that the file be pre-populated. The legacy path `workspace/.openclaw/workspace-state.json` exists (from v1.0). The per-project path will be created on first container run by `JarvisState._ensure_state_file()` at `state_engine.py:75` which calls `self.state_file.parent.mkdir(parents=True, exist_ok=True)`.

**How to avoid:** Verify that `get_state_path('pumplai')` returns `workspace/.openclaw/pumplai/workspace-state.json` and that `spawn.py` injects the correct path as `OPENCLAW_STATE_FILE` env var at line 177. This is the behavioral evidence. File pre-existence is not the requirement.

**Warning signs:** If VERIFICATION.md says "file not found at expected path" — that's a false negative.

### Pitfall 2: CFG-02 — Phase 16 Already Fixed This

**What goes wrong:** The v1.1 audit noted CFG-02 had a wiring bug (`get_snapshot_dir()` called without project_id). Phase 16 fixed this. The VERIFICATION.md for Phase 11 must note that CFG-02 was partially implemented in Phase 11 and completed in Phase 16.

**Why it happens:** Phase 11 created the API; Phase 16 fixed the call sites. Both phases contribute to CFG-02 satisfaction.

**How to avoid:** In Phase 11's VERIFICATION.md, mark CFG-02 as VERIFIED and cite both the Phase 11 API creation AND Phase 16 fix. The requirements traceability in REQUIREMENTS.md already maps CFG-02 to "Phase 11, 16".

### Pitfall 3: CFG-04 — Phase 12 Created API, Phase 16 Fixed Template

**What goes wrong:** Similar to CFG-02, CFG-04 was partially implemented in Phase 12 (template created, but `$project_name` missing from body). Phase 16 fixed the template. Phase 12's VERIFICATION.md should cover CFG-04 as complete, noting Phase 16 completed the fix.

**How to avoid:** Cite `soul-default.md:4` (`- **Project:** $project_name`) as the evidence. The current codebase has this line; it was added in Phase 16.

### Pitfall 4: CFG-05 Override Path Convention

**What goes wrong:** The UAT tester during Phase 12 checked wrong paths (`agents/pumplai_pm/agent/soul-override.md` instead of `projects/pumplai/soul-override.md`). A verifier writing VERIFICATION.md might repeat this mistake.

**How to avoid:** Override path is `projects/<id>/soul-override.md`, not inside the agents directory. Evidence: `soul_renderer.py:145` — `override_path = root / "projects" / project_id / "soul-override.md"`.

### Pitfall 5: Phase 11 UAT vs Phase 16 Integration Fixes

**What goes wrong:** Phase 11's UAT.md shows 9/9 tests passing, BUT the v1.1 audit found 3 integration bugs that Phase 16 had to fix. The verifier might be confused about which phase "owns" the requirement.

**How to avoid:** VERIFICATION.md should reflect the CURRENT state of the code (post-Phase-16), not the state at the time Phase 11 completed. The requirements are satisfied NOW because Phase 11 built the foundation and Phase 16 completed the wiring. Both phases contribute.

---

## Code Examples

### CFG-01: State File Path Convention

```python
# orchestration/project_config.py:100-120
def get_state_path(project_id: Optional[str] = None) -> Path:
    if project_id is None:
        project_id = get_active_project_id()
    root = _find_project_root()
    manifest_path = root / "projects" / project_id / "project.json"
    if not manifest_path.exists():
        raise ProjectNotFoundError(...)
    return root / "workspace" / ".openclaw" / project_id / "workspace-state.json"
    # Example: /home/ollie/.openclaw/workspace/.openclaw/pumplai/workspace-state.json

# orchestration/state_engine.py:72-75
def _ensure_state_file(self) -> None:
    """Creates parent directories and initializes empty state if needed."""
    self.state_file.parent.mkdir(parents=True, exist_ok=True)  # creates per-project dir
```

### CFG-02: Snapshot Project ID Threading

```python
# orchestration/snapshot.py:171 (required parameter, no default)
def capture_semantic_snapshot(task_id: str, workspace_path: str, project_id: str) -> ...:
    ...
    snapshots_dir = get_snapshot_dir(project_id)  # line 195 — explicit threading

# orchestration/snapshot.py:461 (required parameter, no default)
def cleanup_old_snapshots(workspace_path: str, project_id: str, max_snapshots: int = 100) -> ...:
    ...
    snapshots_dir = get_snapshot_dir(project_id)  # line 473 — explicit threading
```

### CFG-03: Path API in project_config.py

```python
# orchestration/project_config.py:100
def get_state_path(project_id: Optional[str] = None) -> Path:
    # Returns: workspace/.openclaw/<project_id>/workspace-state.json
    return root / "workspace" / ".openclaw" / project_id / "workspace-state.json"  # line 120

# orchestration/project_config.py:123
def get_snapshot_dir(project_id: Optional[str] = None) -> Path:
    # Returns: workspace/.openclaw/<project_id>/snapshots
    return root / "workspace" / ".openclaw" / project_id / "snapshots"  # line 143
```

### CFG-04: Template Variable Consumption

```
# agents/_templates/soul-default.md:1-18 (full file)
## HIERARCHY
- **Superior:** Reports to the L1 Strategic Orchestrator.
- **Subordinates:** Supervises L3 Worker containers.
- **Project:** $project_name           <- line 4
- **Scope:** Primary authority over the `$workspace` workspace.

## CORE GOVERNANCE
1. **TACTICAL TRANSLATION:** ...
2. **STRICT TECH STACK:**
   - **Frontend:** $tech_stack_frontend.   <- line 10
   - **Backend:** $tech_stack_backend.     <- line 11
   - **Infrastructure:** $tech_stack_infra. <- line 12
3. **QUALITY GATE:** ...

## BEHAVIORAL PROTOCOLS
...
```

### CFG-05: Override Detection and Application

```python
# orchestration/soul_renderer.py:145-149
override_path = root / "projects" / project_id / "soul-override.md"  # line 145
override_sections, override_order = {}, []
if override_path.exists():  # line 147
    override_text = string.Template(override_path.read_text()).safe_substitute(variables)
    override_sections, override_order = parse_sections(override_text)

# projects/pumplai/soul-override.md — exists on disk, overrides HIERARCHY and BEHAVIORAL PROTOCOLS
```

### CFG-06: Dynamic Branch Detection

```python
# orchestration/snapshot.py:74 + 129 — create_staging_branch
def create_staging_branch(task_id: str, workspace_path: str, stash_if_needed: bool = True) -> str:
    workspace = Path(workspace_path)
    ...
    default_branch = _detect_default_branch(workspace)  # line 129 — delegated, not inlined

# _detect_default_branch at snapshot.py:20 — 5-step resolution:
# 1. project.json default_branch field
# 2. git symbolic-ref refs/remotes/origin/HEAD
# 3. local main branch check
# 4. local master branch check
# 5. fallback to "main" with warning
```

### CFG-07: Agent Config Resolution from Project Manifest

```python
# skills/spawn_specialist/spawn.py:47-55
def load_l3_config(project_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        agent_map = get_agent_mapping(project_id)           # line 50 — reads from project.json
        l3_agent_id = agent_map.get("l3_executor", "l3_specialist")  # line 51
    except (FileNotFoundError, ValueError):
        l3_agent_id = "l3_specialist"                       # line 53 — fallback
    config_path = Path(...) / "agents" / l3_agent_id / "config.json"  # line 55
    ...

# projects/pumplai/project.json agents section:
# { "l2_pm": "pumplai_pm", "l3_executor": "l3_specialist" }
```

---

## Detailed Evidence Matrix

This matrix maps each requirement to the exact evidence to include in VERIFICATION.md:

### Phase 11 VERIFICATION.md (CFG-01, CFG-02, CFG-03, CFG-06, CFG-07)

| Req | Observable Truth | File:Line | Verification Method |
|-----|-----------------|-----------|---------------------|
| CFG-01 | `get_state_path('pumplai')` returns `workspace/.openclaw/pumplai/workspace-state.json` | `project_config.py:120` | Run `get_state_path('pumplai')` and assert path contains `pumplai/workspace-state.json` |
| CFG-01 | `JarvisState._ensure_state_file()` creates per-project directory on first use | `state_engine.py:75` | Source check: `parent.mkdir(parents=True, exist_ok=True)` in `_ensure_state_file` |
| CFG-01 | `spawn.py` injects correct per-project path as `OPENCLAW_STATE_FILE` env var | `spawn.py:177` | `f"/workspace/.openclaw/{project_id}/workspace-state.json"` in inject dict |
| CFG-02 | `capture_semantic_snapshot()` requires `project_id: str` with no default | `snapshot.py:171` | `inspect.signature()` shows `project_id` with `default is inspect.Parameter.empty` — PASSES in `verify_phase16.py` |
| CFG-02 | `cleanup_old_snapshots()` requires `project_id: str` with no default | `snapshot.py:461` | Same inspect.signature check — PASSES in `verify_phase16.py` |
| CFG-02 | Both functions call `get_snapshot_dir(project_id)` explicitly | `snapshot.py:195, 473` | `inspect.getsource()` confirms — PASSES in `verify_phase16.py` |
| CFG-03 | `get_state_path(project_id)` exists in `project_config.py` | `project_config.py:100` | `hasattr(project_config, 'get_state_path')` is True |
| CFG-03 | `get_snapshot_dir(project_id)` exists in `project_config.py` | `project_config.py:123` | `hasattr(project_config, 'get_snapshot_dir')` is True |
| CFG-03 | Both raise `ProjectNotFoundError` for unknown project IDs | `project_config.py:116-118, 139-141` | `ProjectNotFoundError` class at line 95; raised when manifest not found |
| CFG-06 | `create_staging_branch()` delegates to `_detect_default_branch(workspace)` | `snapshot.py:129` | `_detect_default_branch` in `getsource(create_staging_branch)` — PASSES in `verify_phase16.py` |
| CFG-06 | No inline `symbolic-ref` in `create_staging_branch()` | `snapshot.py:74-185` | `symbolic-ref` NOT in `getsource(create_staging_branch)` — PASSES in `verify_phase16.py` |
| CFG-06 | All 5 git functions use `_detect_default_branch()` | `snapshot.py:129,192,284,333,417` | Source check confirms all 5 call sites |
| CFG-07 | `load_l3_config()` calls `get_agent_mapping(project_id)` | `spawn.py:50` | `get_agent_mapping` in `getsource(load_l3_config)` |
| CFG-07 | `l3_agent_id` resolved from `agents.l3_executor` in project manifest | `spawn.py:51` | `agent_map.get("l3_executor", "l3_specialist")` in source |
| CFG-07 | Config path built from resolved `l3_agent_id`, not hardcoded | `spawn.py:55` | `"agents" / l3_agent_id / "config.json"` — no string literal `"l3_specialist"` in path construction |

### Phase 12 VERIFICATION.md (CFG-04, CFG-05)

| Req | Observable Truth | File:Line | Verification Method |
|-----|-----------------|-----------|---------------------|
| CFG-04 | `$project_name` present in `soul-default.md` body | `soul-default.md:4` | `'$project_name' in template_text` — PASSES in `verify_phase16.py` |
| CFG-04 | `$tech_stack_frontend` present in template | `soul-default.md:10` | `'$tech_stack_frontend' in template_text` — PASSES in `verify_soul_golden.py` |
| CFG-04 | `$tech_stack_backend` present in template | `soul-default.md:11` | `'$tech_stack_backend' in template_text` |
| CFG-04 | `$tech_stack_infra` present in template | `soul-default.md:12` | `'$tech_stack_infra' in template_text` |
| CFG-04 | `string.Template.safe_substitute()` resolves all variables | `soul_renderer.py:141` | `verify_soul_golden.py` — "No unresolved variables" check PASSES |
| CFG-05 | Override detection: `soul_renderer.py` checks `projects/<id>/soul-override.md` | `soul_renderer.py:145` | `override_path = root / "projects" / project_id / "soul-override.md"` in source |
| CFG-05 | Override sections replace (not append) default sections | `soul_renderer.py:48-78` | `merge_sections()` function: `merged.update(override_sections)` — overrides win |
| CFG-05 | PumplAI override file exists and is applied | `projects/pumplai/soul-override.md` | File exists on disk; `render_soul('pumplai')` contains `ClawdiaPrime` (from override HIERARCHY) — PASSES in `verify_soul_golden.py` |
| CFG-05 | New project without override uses default template completely | `soul_renderer.py:146` | `override_sections, override_order = {}, []` as default; no-override path returns full default — "new-project-without-override" check PASSES in `verify_soul_golden.py` |

---

## Key Context: What Phase 17 Is NOT

Phase 17 does NOT:
- Implement any new code
- Run the migration script (`orchestration/migrate_state.py`) to move the legacy state file
- Fix any remaining bugs — Phase 16 fixed the last wiring bugs
- Update `REQUIREMENTS.md` checkboxes (this is done as part of writing VERIFICATION.md)
- Create new verification scripts — existing `verify_phase16.py` and `verify_soul_golden.py` are the verification infrastructure

Phase 17 IS:
- Two VERIFICATION.md files at:
  - `.planning/phases/11-config-decoupling-foundation/VERIFICATION.md`
  - `.planning/phases/12-soul-templating/VERIFICATION.md`
- Each with concrete file:line evidence for every requirement assigned to that phase
- Status: VERIFIED for all 7 CFG requirements (they are all satisfied in the current codebase)

---

## State of the Art

| Old State (at v1.1 audit) | Current State (post-Phase-16) | Fixed In | Impact |
|---------------------------|-------------------------------|----------|--------|
| CFG-02: `get_snapshot_dir()` called without `project_id` | `capture_semantic_snapshot(project_id: str)` required | Phase 16 | Multi-project snapshot isolation works |
| CFG-04: `$project_name` not in `soul-default.md` | `soul-default.md:4` has `- **Project:** $project_name` | Phase 16 | All template variables consumed |
| CFG-06: `create_staging_branch` has inline duplicate detection | Delegates to `_detect_default_branch(workspace)` at line 129 | Phase 16 | Branch detection is consistent, supports `project.json default_branch` |
| CFG-01, CFG-03, CFG-05, CFG-07: No VERIFICATION.md | Post-Phase-17: VERIFICATION.md with evidence | Phase 17 | Audit gap closed |

---

## Open Questions

1. **Should REQUIREMENTS.md checkboxes be updated as part of Phase 17?**
   - What we know: CFG-01 through CFG-07 are all marked `[ ]` in REQUIREMENTS.md despite being implemented. The phase goal says to create VERIFICATION.md files, not to update REQUIREMENTS.md.
   - What's unclear: Is updating REQUIREMENTS.md in scope?
   - Recommendation: Update REQUIREMENTS.md checkboxes as part of Phase 17 — they are demonstrably satisfied and the formal verification documents will prove it. This is the natural conclusion of the verification work.

2. **Should Phase 17 also cover Phase 16's contribution to CFG-02, CFG-04, CFG-06?**
   - What we know: Phase 11's VERIFICATION.md covers CFG-01, CFG-02, CFG-03, CFG-06, CFG-07. Phase 16 fixed the wiring bugs for CFG-02, CFG-04, CFG-06. Phase 16 already has its own VERIFICATION.md.
   - What's unclear: Whether Phase 11's VERIFICATION.md should acknowledge Phase 16's fixes.
   - Recommendation: Phase 11's VERIFICATION.md should note for CFG-02 and CFG-06 that "Phase 16 completed the call-site fixes." REQUIREMENTS.md traceability already maps these to "Phase 11, 16."

3. **CFG-01: State file doesn't exist on disk — mark as VERIFIED or PARTIAL?**
   - What we know: The state file will be created by `JarvisState._ensure_state_file()` on first use. The code is fully wired. No container run has yet created it at the per-project path.
   - What's unclear: Does "per-project state file at path X" mean the path pattern, or a live file?
   - Recommendation: Mark as VERIFIED. The requirement says the system uses per-project paths — the code proves this. A production deployment that has run containers would have the file. The absence of the file is an operational state, not a code gap.

---

## Sources

### Primary (HIGH confidence)

All findings from direct codebase inspection:

- `/home/ollie/.openclaw/orchestration/project_config.py` — `get_state_path()` at line 100, `get_snapshot_dir()` at line 123
- `/home/ollie/.openclaw/orchestration/snapshot.py` — `capture_semantic_snapshot()` at line 171, `cleanup_old_snapshots()` at line 461, `create_staging_branch()` at line 74, `_detect_default_branch()` at line 20
- `/home/ollie/.openclaw/orchestration/soul_renderer.py` — `build_variables()` at line 81, `render_soul()` at line 118, `merge_sections()` at line 48, override detection at line 145
- `/home/ollie/.openclaw/agents/_templates/soul-default.md` — `$project_name` at line 4, `$tech_stack_*` at lines 10-12
- `/home/ollie/.openclaw/projects/pumplai/soul-override.md` — override sections HIERARCHY and BEHAVIORAL PROTOCOLS
- `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` — `load_l3_config()` at line 47, `get_agent_mapping()` call at line 50
- `/home/ollie/.openclaw/orchestration/state_engine.py` — `_ensure_state_file()` at line 72
- `/home/ollie/.openclaw/scripts/verify_phase16.py` — all 4 checks PASS (run confirmed: exit 0)
- `/home/ollie/.openclaw/scripts/verify_soul_golden.py` — all checks PASS (run confirmed: exit 0)
- `/home/ollie/.openclaw/.planning/v1.1-MILESTONE-AUDIT.md` — verification gap identification
- `/home/ollie/.openclaw/.planning/phases/16-integration-fixes/16-VERIFICATION.md` — VERIFICATION.md format template
- `/home/ollie/.openclaw/.planning/REQUIREMENTS.md` — requirement definitions and traceability

---

## Metadata

**Confidence breakdown:**
- What to write (VERIFICATION.md format): HIGH — Phase 16 example is the canonical template
- Evidence for each requirement: HIGH — all 7 requirements verified by direct code inspection and running existing scripts
- Which files are needed: HIGH — exactly 2 VERIFICATION.md files, one for Phase 11, one for Phase 12
- Open questions: LOW concern — all are resolvable without ambiguity; recommendations given

**Research date:** 2026-02-23
**Valid until:** Indefinite — no external dependencies; all findings are from current codebase state
