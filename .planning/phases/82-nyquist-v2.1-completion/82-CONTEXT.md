# Phase 82: Nyquist v2.1 Completion - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Write or update VALIDATION.md for phases 74, 75, 78, 79, and 80 so that all v2.1 phases have `nyquist_compliant: true`. This is attestation work only — no production code changes. Closes the Nyquist gap identified in the v2.1 milestone audit.

</domain>

<decisions>
## Implementation Decisions

### Phase 75 manual items handling
- Attest `nyquist_compliant: true` with the 4 browser-only items documented as `accepted_deferrals`
- Framing: plan-approved deviations (per Phase 75 PLAN and audit), automated evidence (9/9 auto criteria passed) is sufficient for attestation
- The 4 items (pipeline timestamp accuracy to 1s, expand/collapse pipeline row, shift-click multi-expand, metrics page visual layout) are cosmetic/operational confirmation, not functional blockers
- Live browser confirmation is deferred to operational use — not a prerequisite for nyquist attestation

### Evidence standard for existing drafts (74, 75, 79)
- Existing VERIFICATION.md evidence + SUMMARY.md frontmatter is sufficient to flip `nyquist_compliant: false` → `true`
- No need to re-run tests before attesting — the evidence was already captured at phase completion
- Review each VALIDATION.md draft, confirm evidence links are accurate, then flip the flag

### Phases 78 and 80 (no VALIDATION.md yet)
- Use the retroactive attestation format established in Phase 80 (evidence tables from VERIFICATION.md)
- Phase 78: documentation phase — evidence is the VERIFICATION.md files it created for phases 74, 76, 77
- Phase 80: Nyquist cleanup phase — evidence is the VALIDATION.md files it created + dead code removed + socket label confirmed
- No test suite to run; attestation is based on documented deliverables from SUMMARY.md

### Claude's Discretion
- Exact frontmatter fields in each new VALIDATION.md (follow the existing draft format in 74/75/79)
- Whether to include a "Per-Task Verification Map" in 78 and 80 (documentation phases have no test commands — a deliverables table is more appropriate)
- Wording of accepted_deferrals entries for Phase 75

</decisions>

<specifics>
## Specific Ideas

- Phase 75 accepted_deferrals should reference the audit explicitly: "Plan-approved deviation per Phase 75 PLAN spec and v2.1-MILESTONE-AUDIT.md — automated evidence sufficient"
- The single plan (82-01-PLAN.md) should cover all 5 phases in one wave — they're independent attestation tasks

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.planning/phases/74-dashboard-streaming-ui/74-VALIDATION.md`: Draft template to follow for updating phases 74, 75, 79
- `.planning/phases/80-nyquist-compliance-tech-debt-cleanup/80-VERIFICATION.md` + `80-01-SUMMARY.md`: Evidence sources for Phase 80 attestation
- `.planning/phases/78-verification-documentation-closure/78-01-SUMMARY.md` + `78-02-SUMMARY.md`: Evidence sources for Phase 78 attestation

### Established Patterns
- Retroactive attestation format: frontmatter (`phase`, `slug`, `status: attested`, `nyquist_compliant: true`, `wave_0_complete`, `created`) + evidence table section
- For documentation phases (78, 80): replace "Per-Task Verification Map" with "Deliverables Attestation" table listing what was produced and confirming existence
- `accepted_deferrals` section used when attesting phases with known, documented deviations

### Integration Points
- VALIDATION.md files live in each phase directory: `.planning/phases/{N}-{slug}/{N}-VALIDATION.md`
- After all 5 are written/updated, the v2.1-MILESTONE-AUDIT.md `nyquist.compliant_phases` list should be updated to include 74, 75, 78, 79, 80

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 82-nyquist-v2.1-completion*
*Context gathered: 2026-03-08*
