# Phase 37: Category Field End-to-End Fix - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The `category` field flows end-to-end from memorize callers through MemoryClient, MemorizeRequest, and memu-py storage, so `_format_memory_context()` primary routing path fires and category metadata appears on retrieved items. Closes 3 integration gaps and 2 partial flows from v1.3 audit. No new capabilities — this fixes existing plumbing.

</domain>

<decisions>
## Implementation Decisions

### Category value semantics
- Controlled set of known values, not free-form strings
- Initial set: `review_decision`, `task_outcome`
- Defined as a `Literal` type or `Enum` in `MemorizeRequest` (co-located with the Pydantic model)
- Unknown category values are rejected by Pydantic validation — strict contract, catches bugs early

### Backwards compatibility
- Existing memories (stored without `category`) return `category=None` on retrieval — Claude decides exact defaulting approach
- The formatter's existing `agent_type` fallback routing remains as-is for memories without a category — zero breakage for old memories
- Existing callers that should use category (e.g. review_skill) are updated in this phase to start passing it — this is the "end-to-end" promise
- memu-py storage changes: Claude investigates during research and handles accordingly

### Validation and error handling
- `category` is optional on `MemorizeRequest` — defaults to `None` when omitted, backwards compatible
- Narrow fix: just add the `category` field to `MemorizeRequest`, don't change the extra fields policy or audit other fields
- Integration test required: memorize with category → retrieve → assert category present and routing works
- When memu-py API returns a memory without `category` (older data), client defaults to `None` gracefully — no error, no disruption

### Formatter routing logic
- Hard-coded dict mapping: `{"review_decision": "Past Review Outcomes", "task_outcome": "Task Outcomes"}`
- Category determines the section, `agent_type` determines ordering or sub-grouping within that section
- Category-grouped output ordering: review decisions → task outcomes → uncategorized/fallback
- Within each group, keep chronological order

### Claude's Discretion
- memu-py storage model investigation and any needed schema changes
- Exact defaulting approach for `category=None` on old memories
- How agent_type sub-grouping works within category sections (ordering, indentation, etc.)

</decisions>

<specifics>
## Specific Ideas

- Category routing is the primary path; agent_type fallback only fires when category is None/missing
- The section heading "Past Review Outcomes" already exists in the formatter — category routing should use it directly instead of reaching it via the agent_type fallback
- "Task Outcomes" is the new section heading for `task_outcome` category

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 37-category-field-e2e-fix*
*Context gathered: 2026-02-24*
