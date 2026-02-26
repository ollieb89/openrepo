# Phase 41: L1 Strategic Suggestions - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

L1 can identify recurring failure patterns in task activity logs and produce reviewable SOUL amendments written only to `soul-suggestions.json`. An operator must explicitly accept or reject each suggestion before any soul-override.md file is modified. Pattern extraction, a suggestion review dashboard, and the approval gate are all in scope. Automatic/scheduled extraction, cross-project analysis, and SOUL version history are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Suggestion card design
- Primary card display: pattern description + evidence count (e.g. "Agents frequently ignore user-specified file paths (7 occurrences)")
- Expanded suggestion view uses a unified diff format showing exactly what would be appended/changed in soul-override.md
- Evidence shown: count + 2–3 example task excerpts (task ID + short rejection reason) — enough context without overwhelming
- Suggestions ordered by evidence count descending — highest-frequency patterns surface first

### Approval flow
- On accept: inline confirmation on the card ("Applied to soul-override.md") + updated SOUL content visible on the same page immediately
- On reject: optional text field appears (not required) — operator can dismiss with one click or add context; reason is memorized if provided
- Rejected suggestions move to a Dismissed tab/archive — not permanently deleted, visible if operator wants to review
- Accept-as-is only — no inline editing of the diff before accepting; operator edits soul-override.md directly if they want different wording

### Trigger & cadence
- Pattern extraction is on-demand: a "Run analysis" button on the Suggestions dashboard page
- Also triggerable via CLI: `python3 orchestration/suggest.py --project X` so L1 can initiate analysis programmatically
- New pending suggestions surface via a badge on the Suggestions nav item (count visible without navigating)
- If a run finds no patterns meeting the threshold: show a clear empty state — "Last run: [timestamp]. No patterns met the threshold." — confirms the engine ran

### Lookback window & thresholds
- Default lookback window: last 30 days of task history
- Configurable per project via `suggestion_lookback_days` in `l3_overrides` in project.json (consistent with pool config pattern)
- Pattern engine analyzes per-task activity log entries in workspace-state.json (already captured by Jarvis Protocol)
- Rejection suppression: if a pattern was rejected, do not re-surface it unless significantly more new evidence accumulates (target: ~2× the original threshold before re-suggesting)
- Minimum threshold for generating a suggestion: ≥3 similar rejections within the lookback window (fixed per requirements)

### Claude's Discretion
- Exact similarity algorithm for clustering similar failure patterns
- Specific wording of the pattern description generated from clusters
- How "similar rejections" are detected (embedding similarity, keyword frequency, or hybrid)
- Dismissed tab placement and visual treatment within the Suggestions page layout
- Exact threshold multiplier for re-surfacing rejected patterns (the "~2×" is a target, not a hard rule)

</decisions>

<specifics>
## Specific Ideas

- The "Run analysis" button should clearly show when the last analysis ran (timestamp), so operators know whether results are fresh
- The Dismissed archive should feel lightweight — not a prominent feature, just accessible if needed for audit

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 41-l1-strategic-suggestions*
*Context gathered: 2026-02-24*
