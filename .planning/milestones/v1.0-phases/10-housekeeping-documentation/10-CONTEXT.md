# Phase 10: Housekeeping & Documentation - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean up remaining tech debt from the v1.0 milestone audit — missing verification docs for Phases 5 and 8, an unused `redactWithReport()` export, a misconfigured `pumplai_pm` workspace path, and a missing `snapshot.py` export. No new capabilities; this is strictly cleanup and documentation.

</domain>

<decisions>
## Implementation Decisions

### redactWithReport() removal
- **Full removal** — delete the function, its types, any test stubs, and all imports referencing it. Clean slate.
- Claude traces the call graph; if nothing calls it at runtime, remove regardless of how many modules import it.
- Commit message references the audit item it closes (e.g. `fix(debt): remove unused redactWithReport (closes TD-XX)`)

### Retroactive verification docs (Phase 5 & 8)
- **Evidence from git** — pull evidence from commit history and existing code state (diffs, test results, code inspection). Pragmatic, not re-running live checks.
- **Same format** as other VERIFICATION.md files — no special 'retroactive' marker or lighter format
- **Best-effort inference** where criteria can't be fully evidenced — note confidence level where uncertain, don't mark as unverifiable
- **Separate commits** — one commit per phase's verification doc

### Path & export fixes
- **Audit all agent configs** — while fixing `pumplai_pm` workspace path, check all `agents/` config files for stale or incorrect path references
- **Audit all orchestration exports** — while adding `snapshot.py` to `orchestration/__init__.py` `__all__`, verify all modules in `orchestration/` are properly exported
- **Fix trivial findings** discovered during audits (simple path/export corrections). Log anything structural as new tech debt.
- **Group commits by type** — one commit for all path fixes, one commit for all export fixes

### Claude's Discretion
- Exact audit methodology for path and export scanning
- How to structure git evidence in verification docs (which commits to reference, how to present diffs)
- Whether to scan beyond `agents/` and `orchestration/` if patterns suggest broader issues
- Ordering of the work items within the phase

</decisions>

<specifics>
## Specific Ideas

- Commit messages should reference audit items they close for traceability back to the v1.0 milestone audit
- The convention of separate commits per logical fix (from Phase 9) carries forward here
- Verification docs should be indistinguishable from ones created at phase completion time — same quality bar

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-housekeeping-documentation*
*Context gathered: 2026-02-23*
