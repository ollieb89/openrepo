# Phase 36: Dashboard Memory Panel - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The occc dashboard gets a /memory page where the operator can browse project-scoped memory items, inspect individual items with metadata, run semantic search (via POST /retrieve), and delete items. The page is scoped to the currently selected project and updates when the project selector changes.

</domain>

<decisions>
## Implementation Decisions

### Memory item presentation
- Table rows layout with sortable columns: Type, Category, Agent, Created
- Click a row to expand inline (accordion-style) showing full content and extra metadata
- Expanded content capped at ~300 characters with a "show more" toggle to reveal the rest
- Content in expanded view shows the memory text plus any additional metadata not in columns

### Browse & navigation
- Filter bar above the table with dropdown selectors for Category, Agent source, and Type
- Default sort: newest first (most recently created at top)
- Compact stats bar above filters showing total count and per-agent breakdown (e.g., "42 items | l2_pm: 12 · l3_code: 22 · l3_test: 8")
- Classic pagination with page numbers at bottom, ~25 items per page
- Auto-reload silently when project changes in the project selector — consistent with existing dashboard pages

### Search experience
- Prominent full-width search bar at the top of the page, above the stats bar and filters
- Search triggered on Enter key press (not debounced as-you-type — semantic search is not instant)
- Search results replace the table contents with a "Showing results for 'query'" banner and a clear button to return to browsing
- Filters still apply during search (can narrow search results by category/agent/type)

### Delete workflow
- Delete button visible only in the expanded row view (not on every row)
- Confirmation dialog on click ("Are you sure?" popup)
- After successful deletion: row animates out, brief success toast, stats bar updates count
- Bulk delete supported: checkboxes on each row, "Delete selected" button appears when items are checked
- Bulk delete also uses confirmation dialog before executing

### Claude's Discretion
- Empty search results state design (friendly messaging with suggestions)
- Loading states and skeleton design
- Exact spacing, typography, color coding for agent/category badges
- Sort direction toggle UX
- Error state handling (API failures, timeout)
- Filter dropdown population (dynamic from available data vs static list)

</decisions>

<specifics>
## Specific Ideas

- Stats bar layout inspired by the mockup: `Memory | 42 items | l2_pm: 12 · l3_code: 22 · l3_test: 8`
- Page hierarchy top-to-bottom: Search bar → Stats bar → Filter dropdowns → Table → Pagination
- Follow existing occc dashboard patterns for project-scoping (SWR with `?project=` query param for cache separation)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 36-dashboard-memory-panel*
*Context gathered: 2026-02-24*
