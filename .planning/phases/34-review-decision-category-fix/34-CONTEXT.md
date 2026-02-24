# Phase 34: Review Decision Category Fix - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the memory routing so `_memorize_review_decision()` tags review decisions with `category: "review_decision"` in the memU payload, and `_format_memory_context()` routes items with that category to the "Past Review Outcomes" SOUL section instead of falling through to "Past Work Context". This is a correctness fix for an integration gap — no new capabilities.

</domain>

<decisions>
## Implementation Decisions

### Category field handling
- Use a plain string literal `"review_decision"` — no constants, no enums
- Add `"category": "review_decision"` as a new field alongside existing payload fields in `_memorize_review_decision()`
- Always send the category unconditionally — no feature flags, no version checks
- Scoped to review decisions only — other memorize functions are not modified in this phase

### Backward compatibility
- No migration of existing memories — old items stay as-is without a category field
- Items without a category field silently route to "Past Work Context" (default section)
- Items with an unrecognized category value also route to "Past Work Context" (safe fallback)
- Explicit test case required: verify items without category field route to default section

### Routing logic in formatter
- Keep existing SOUL section names: "Past Review Outcomes" and "Past Work Context"
- Skip empty items — don't render memories with no meaningful content regardless of category
- Both mocked unit test AND optional integration test (with pytest marker) for the round-trip

### Claude's Discretion
- Routing implementation approach (simple if/else vs dict-based mapping) — pick what fits the current `_format_memory_context()` structure
- Whether to emit a debug log for items without a category field — match existing logging patterns in the codebase

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The fix should be minimal and surgical, touching only `_memorize_review_decision()` in `snapshot.py` and `_format_memory_context()` in `spawn.py`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 34-review-decision-category-fix*
*Context gathered: 2026-02-24*
