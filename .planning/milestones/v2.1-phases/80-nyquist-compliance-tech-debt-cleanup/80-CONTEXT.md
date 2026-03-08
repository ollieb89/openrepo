# Phase 80: Nyquist Compliance + Tech Debt Cleanup - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Retroactively create VALIDATION.md files for 7 completed phases (69, 70, 71, 72, 73, 76, 77), remove one dead function from metrics.py, and verify/close the socket path label criterion. No new features. No changes to phases 74 or 75.

</domain>

<decisions>
## Implementation Decisions

### Retroactive VALIDATION.md format
- Use simplified attestation style: YAML frontmatter + brief evidence summary per success criterion
- No task map, no wave 0 gates, no pending status rows — the phase is already done
- Include a one-line retroactive note in each file: "Retroactive: phase complete prior to Nyquist adoption."
- Set `nyquist_compliant: true` in frontmatter for all 7 files
- Evidence sources (use all three where available):
  1. SUMMARY.md outcomes (test results, task outcomes from execution)
  2. VERIFICATION.md pass/fail verdicts (phases 69–73 have VERIFICATION.md)
  3. Success criteria from ROADMAP.md (restate each criterion and mark met)

### Phase 74/75 scope exclusion
- Leave 74-VALIDATION.md and 75-VALIDATION.md as-is (nyquist_compliant: false)
- Phase 80 scope is strictly phases 69, 70, 71, 72, 73, 76, 77

### Socket path label (criterion 3)
- Verify-and-close: confirm `environment/page.tsx` label matches `route.ts` computed path
- Current code already shows `~/.openclaw/run/events.sock` — matches route.ts
- No code change expected; document as already correct and mark criterion satisfied
- Do NOT add OPENCLAW_EVENTS_SOCK support to the display label — cosmetic only

### Dead code removal
- Remove `collect_metrics()` function and its comment block from `metrics.py` — strictly scoped, nothing else
- Also delete root-level `test_metrics.py` (outside the package test suite, only caller of the dead function)
- No opportunistic cleanup of other code in metrics.py

### Claude's Discretion
- Exact structure/sections within each attestation VALIDATION.md body
- Order in which the 7 VALIDATION.md files are written

</decisions>

<specifics>
## Specific Ideas

- Each retroactive VALIDATION.md should be self-contained: a reader should be able to see what the phase delivered, what the success criteria were, and where the evidence lives — without opening other files

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `74-VALIDATION.md` and `75-VALIDATION.md`: reference for frontmatter schema and structure (adapt to simplified attestation style)
- `79-VALIDATION.md`: another reference showing varied validation types

### Established Patterns
- VALIDATION.md frontmatter keys: `phase`, `slug`, `status`, `nyquist_compliant`, `wave_0_complete`, `created`
- For retroactive files: `wave_0_complete` can be omitted or set `true` (wave 0 concept doesn't apply)

### Integration Points
- `packages/orchestration/src/openclaw/metrics.py`: remove `collect_metrics()` function (lines ~153–end of function) and its comment block
- `test_metrics.py` at repo root: delete entirely
- `environment/page.tsx` line 122: verify label, no code change expected

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 80-nyquist-compliance-tech-debt-cleanup*
*Context gathered: 2026-03-08*
