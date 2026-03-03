# Phase 63: Correction System and Approval Gate - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can correct proposals through textual feedback (soft correction) or direct topology edits (hard correction), with the system enforcing an approval gate before any L3 execution. Every correction event produces a diff record for Phase 64 structural memory. Does NOT include structural memory/preference learning (Phase 64) or dashboard visualization (Phase 65).

</domain>

<decisions>
## Implementation Decisions

### Soft Correction Flow
- Same-session conversational loop: after proposals display, CLI stays interactive. User types feedback inline (e.g., "flatten the hierarchy", "add a review gate between coordinator and workers")
- Re-proposal scope is Claude's discretion: broad feedback regenerates all 3 archetypes, specific feedback targets only the relevant archetype(s)
- Re-proposals show diff (highlighted delta) AND full updated proposal below — user sees both the evolution and the complete picture
- 3-cycle limit (CORR-06): when hit, system presents the best version so far, explains what feedback asked for vs what the engine achieved, and offers to approve or directly edit. "Here's where I landed. Approve this or edit it yourself."
- Each re-proposal round goes through the same constraint linter pipeline as initial proposals

### Hard Correction UX
- Export-edit-import workflow: system exports the selected proposal to `topology/proposal-draft.json` in annotated JSON format (JSONC with field descriptions, role names as keys, readable edge types). User edits in their editor, then the system imports on approval
- Tiered validation on import: unknown agent roles block execution with error. Pool limit violations get non-blocking warnings. Matches the constraint linter's existing reject/auto-adjust split
- File lives in project-scoped topology directory: `workspace/.openclaw/{project_id}/topology/proposal-draft.json`
- Parser strips annotations on import and converts back to TopologyGraph via from_dict()

### Approval Gate
- Inline confirmation in the same session: after proposals display (or after correction), prompt user to approve by selecting the archetype name/number
- Proposals persist on session exit: saved to `topology/pending-proposals.json` so user can resume later with `openclaw approve` to pick up where they left off
- Approval writes directly to `current.json` and appends to `changelog.json` with the diff from previous version (if any). No intermediate staging step
- L1 directive approval is configurable per-project: `topology.auto_approve_l1` config key (default: false). Projects can opt into auto-approval for L1-generated proposals. Human-in-the-loop by default
- No L3 container spawn occurs until a topology version has been explicitly approved (CORR-07)

### High-Confidence Pushback
- Surfaces both inline AND persisted to changelog: user sees the note immediately after approval, and it's written to `changelog.json` as an annotation on the diff entry for Phase 64 structural memory
- Separate higher threshold: new config key `topology.pushback_threshold` (e.g., 8/10) distinct from `topology.proposal_confidence_warning_threshold`. Only pushes back when system was very confident
- Dimension-specific detail: note names the exact rubric dimensions that shifted and by how much (e.g., "Your edit reduced risk containment from 8/10 to 3/10 by removing the review gate")
- Latest-only inline display: only show the most recent pushback note in the session. All notes are persisted to changelog for historical review
- Note is always non-blocking — never prevents execution (CORR-05)

### Claude's Discretion
- Session state management implementation (in-memory vs file-based for the interactive loop)
- Exact annotated JSON format and comment style for proposal-draft.json
- Re-proposal prompt engineering (how feedback gets injected into the LLM prompt)
- Diff rendering format for re-proposal deltas
- Exact wording of cycle-limit and pushback messages
- Error handling for malformed edited JSON on import

</decisions>

<specifics>
## Specific Ideas

- The soft correction loop should feel conversational — like iterating with a collaborator, not submitting forms. User types natural language, engine responds with revised proposals
- Export-edit-import mirrors the familiar pattern of `kubectl edit` — export, edit in $EDITOR, reimport. Topology editing should feel like infrastructure management, not UI interaction
- Pushback notes should feel like a knowledgeable colleague saying "just so you know..." — informative, not confrontational. Dimension-specific so the user can evaluate the trade-off themselves
- The cycle limit message should acknowledge the feedback was heard, not dismiss it — "Here's the closest I could get to what you described" not "I can't do this"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TopologyProposal` dataclass (topology/proposer.py): Carries graph, justification, assumptions — re-proposal pipeline extends this
- `TopologyDiff` dataclass (topology/diff.py): Computes structural deltas — used for changelog entries after every correction
- `TopologyGraph.to_dict()/from_dict()` (topology/models.py): Serialization round-trip — basis for export-edit-import
- `LintResult` dataclass (topology/linter.py): Carries valid/adjusted flags and adjustment descriptions — reusable for tiered validation on hard corrections
- `TopologyStorage` (topology/storage.py): fcntl-locked read/write to current.json and changelog.json — approval writes use this directly
- `RubricScore` dataclass (topology/proposal_models.py): 7-dimension scoring with key_differentiators — pushback note reads these to identify shifted dimensions
- `renderer.py` (topology/renderer.py): ASCII DAG and comparative matrix rendering — re-proposal diff display extends these

### Established Patterns
- fcntl.flock for file operations (state_engine.py, topology/storage.py)
- Pydantic/dataclass models with to_dict/from_dict serialization
- Project-scoped files under `workspace/.openclaw/{project_id}/topology/`
- CLI commands follow `openclaw-{name}` pattern
- Config keys namespaced by feature: `topology.*`

### Integration Points
- `openclaw-propose` CLI entry point (from Phase 62): extend with interactive session loop, approval prompt, and `openclaw approve` resume command
- `topology/storage.py`: add pending-proposals.json and proposal-draft.json file operations
- `topology/changelog.json`: diff entries with annotation field ready for pushback notes and Phase 64 enrichment
- L1 routing via `skills/router/index.js`: needs approval gate check before execution dispatch
- Config: new keys `topology.auto_approve_l1` and `topology.pushback_threshold`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 63-correction-system-and-approval-gate*
*Context gathered: 2026-03-03*
