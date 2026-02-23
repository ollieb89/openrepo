# Phase 16: Phase 11/12 Integration Fixes - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 3 cross-phase wiring issues identified by v1.1 milestone audit (CFG-02, CFG-04, CFG-06), remove deprecated constants, and clean up related dead code in the orchestration layer. No new capabilities — purely fixing existing code to work as designed.

</domain>

<decisions>
## Implementation Decisions

### Fix scope
- Fix the 3 identified bugs plus clean up immediate neighbors in the same functions
- For CFG-02 (snapshot project_id): Thread project_id explicitly through function signatures of `capture_semantic_snapshot()` and `cleanup_old_snapshots()` — not just `get_snapshot_dir()`
- For CFG-04 (soul template): Add $project_name to soul-default.md template body AND audit all variables declared in `build_variables()` to ensure every one is consumed by the template
- For CFG-06 (staging branch): Replace duplicate inline branch detection in `create_staging_branch()` with a call to existing `_detect_default_branch()` helper. Do NOT enhance the helper — just use it
- Update ALL callers of changed functions in this phase (entrypoint.sh, spawn.py, etc.) — don't leave broken call sites for Phase 17 to catch

### Backward compatibility
- Break cleanly — project_id is a required parameter everywhere, no optional fallback to ambient config
- Any caller without project_id fails immediately with a clear error
- This is internal code with known call sites, so breaking is safe and prevents silent bugs
- Consistent policy across all affected functions: get_snapshot_dir(), capture_semantic_snapshot(), cleanup_old_snapshots()

### Deprecated constant removal
- Delete STATE_FILE and SNAPSHOT_DIR constants from config.py entirely — no stubs, no error messages, just gone
- Remove the unused STATE_FILE import from monitor.py
- Audit ALL orchestration/*.py files for unused imports and clean them up while we're in there
- Audit soul_renderer.py build_variables() for any other unused/dead code beyond the $project_name fix

### Validation approach
- Write a verification script at `scripts/verify_phase16.py` covering all 3 fixes
- Script checks: snapshot path threading, staging branch detection delegation, and template variable consumption
- CI-friendly: exit 0 on all pass, exit 1 on any failure, print results to stdout
- Follows existing pattern (scripts/verify_soul_golden.py already exists)

### Claude's Discretion
- Exact error messages when project_id is missing
- How to structure the verification script internally (class vs functions)
- Whether to use subprocess or direct import for template rendering verification

</decisions>

<specifics>
## Specific Ideas

- Follow the existing `scripts/verify_soul_golden.py` pattern for the new verification script
- The break-cleanly approach mirrors how Phase 13 already resolved project_id explicitly via env-var-first pattern (MPR-06)

</specifics>

<deferred>
## Deferred Ideas

- Enhancing `_detect_default_branch()` to also check project.json default_branch field — could be a future improvement but out of scope for this fix phase
- Full automated test suite for orchestration layer — separate initiative

</deferred>

---

*Phase: 16-integration-fixes*
*Context gathered: 2026-02-23*
