# Phase 30: L2 Review Decision Memorization - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

After L2 (PumplAI_PM) completes a review cycle — merge, reject, or merge conflict — the decision and reasoning are stored in memU so future L3 spawns receive context about past review outcomes for the project. Memorization is fire-and-forget and must not block the review cycle.

</domain>

<decisions>
## Implementation Decisions

### Memory content shape
- Full context bundle per decision: verdict (merge/reject/conflict), free-text reasoning, diff summary, task type (code/test), and original task description
- Reasoning is free-text from L2 (not structured fields) — works well with semantic retrieval
- Task type (skill_type from spawn) is included for filtering capability
- Metadata tags: task_id + verdict + skill_type

### Trigger timing
- Memorization fires AFTER the merge/reject/conflict resolution completes — decision must be final before storing
- Fire-and-forget pattern (consistent with Phase 28's L3 auto-memorization) — failure logged but does not block L2
- Merge conflicts that abort are also memorized as a distinct event type
- All decisions stored (no deduplication) — if a task is retried and reviewed again, both decisions persist for full narrative

### Rejection surfacing in future L3 SOULs
- Structured warning block format: `## Past Review Outcomes` with entries like `- Task X was rejected: [reason]`
- Both merges AND rejections surface in future L3 SOULs — merges provide positive signal, rejections provide warnings
- SOUL injection separates review memories from work context memories: distinct `## Past Work Context` (Phase 28) and `## Past Review Outcomes` (Phase 30) sections

### Category & tagging
- Review memories persist indefinitely — old rejections remain relevant for similar future work
- Metadata tags per memory item: task_id, verdict, skill_type

### Claude's Discretion
- Diff summary truncation/sizing approach
- memU category naming (single 'review_decision' vs split categories — align with Phase 28 patterns)
- Agent type naming (l2_pm vs l2_reviewer — align with existing conventions)
- Cap on how many review memories get injected into a single L3 SOUL

</decisions>

<specifics>
## Specific Ideas

- Merge conflicts should be stored as a distinct verdict type alongside merge/reject, so future L3s know "this area had merge conflicts before"
- The full retry narrative matters: "rejected first attempt, merged second" gives L3s useful context about what approaches work vs don't

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-l2-review-decision-memorization*
*Context gathered: 2026-02-24*
