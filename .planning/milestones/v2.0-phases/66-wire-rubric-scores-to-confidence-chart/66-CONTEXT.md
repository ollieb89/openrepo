# Phase 66: Wire Rubric Scores to Confidence Chart - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Pipe rubric scores from the approval workflow into changelog entries so the ConfidenceChart renders real data. The plumbing gap: `approve_topology()` has no rubric_scores parameter, CLI callers don't pass scores, and changelog entries never contain `annotations.rubric_scores`. The frontend (ConfidenceChart) and TypeScript types are already wired to consume this data.

</domain>

<decisions>
## Implementation Decisions

### Score scope per changelog entry
- Include rubric scores for ALL 3 archetypes (lean/balanced/robust) in each changelog entry — not just the approved one
- CLI callers extract a pre-built `{archetype: RubricScore}` dict from the ProposalSet and pass it to `approve_topology()` — keeps approve_topology decoupled from ProposalSet
- Omit archetypes that have no rubric_score (don't include zeros) — ConfidenceChart already handles sparse data gracefully

### Hard correction scoring
- Auto re-score edited topologies using `score_proposal()` before writing to changelog — ensures the chart always has data points after corrections
- Score the edited graph under all 3 archetypes — shows how the edit shifted confidence across all archetypes, more useful chart data
- Claude's discretion on whether to store weights alongside scores in the changelog entry (reproducibility vs simplicity tradeoff)

### Backfill / migration
- No migration needed — graceful empty state already handled by ConfidenceChart ("No rubric score data available yet")
- New approvals will naturally start populating data points
- No backfill command required

### Claude's Discretion
- Exact parameter name and type for rubric_scores on approve_topology()
- Whether to store scoring weights in changelog entries for reproducibility
- How to handle edge cases (e.g., score_proposal failure during hard correction — likely skip gracefully)
- Test structure and coverage approach

</decisions>

<specifics>
## Specific Ideas

No specific requirements — the wiring pattern is clear from the existing code contracts.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `approve_topology()` (topology/approval.py): Already writes annotations dict — extend with rubric_scores key
- `score_proposal()` (topology/rubric.py): Scores a TopologyGraph against weights — already used in propose.py for initial scoring
- `TopologyProposal.rubric_score` (topology/proposal_models.py): Each proposal carries its score — available at approval time
- `RubricScore.to_dict()` (topology/proposal_models.py): Serialization already exists
- `ConfidenceChart` + `transformChangelogToChartData()` (dashboard): Already reads `annotations.rubric_scores` and renders chart data
- `ChangelogAnnotations.rubric_scores` TypeScript type: Already defined as `Record<string, RubricScore>`

### Established Patterns
- approve_topology uses optional keyword args (pushback_note pattern) — rubric_scores follows the same pattern
- Annotations dict built incrementally in approve_topology (pushback_note, approved_archetype) — rubric_scores is another key
- CLI callers (propose.py, approve.py) already call approve_topology with positional project_id, graph, correction_type, pushback

### Integration Points
- `approve_topology()` signature: add optional `rubric_scores: Optional[dict] = None` parameter
- `propose.py` lines 242-247 and 316-321: pass rubric scores from ProposalSet at approval time
- `approve.py` line 167-172: pass rubric scores from loaded pending proposals at approval time
- Hard correction path in propose.py: call score_proposal() on edited graph, build scores dict, pass to approve_topology
- Tests: test_approval.py, test_cli_approve.py, test_cli_propose.py — extend with rubric_scores assertions

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 66-wire-rubric-scores-to-confidence-chart*
*Context gathered: 2026-03-04*
