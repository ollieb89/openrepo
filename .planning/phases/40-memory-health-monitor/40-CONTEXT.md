# Phase 40: Memory Health Monitor - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can detect and resolve stale and conflicting memories through a health scan engine and dashboard review UI. Includes a batch scan (manual + scheduled), health badges on the existing /memory page, a dedicated health tab, a conflict resolution side panel, a PUT endpoint for updates, and a settings panel for threshold tuning.

</domain>

<decisions>
## Implementation Decisions

### Health scan trigger & results
- Manual "Run Health Scan" button on /memory page AND a scheduled background scan at a fixed interval (e.g. hourly)
- Results appear in two places: inline badges on the main memory list AND a dedicated Health tab for focused triage
- Each flagged memory gets a recommended action (archive, merge, review, etc.) — operator can follow or ignore
- Health tab shows a summary bar at the top with colored count chips (e.g. "3 stale - 2 conflicts")

### Badge & flag presentation
- Colored pill/tag badges next to memory titles — orange for stale, red for conflict
- Flagged memories stay in their normal list position; a filter toggle shows only flagged items
- Health tab in navigation shows a count badge (red/orange number) when unresolved flags exist

### Conflict resolution panel
- Side panel with side-by-side layout showing both conflicting memories with differences highlighted
- Three actions: edit, delete, dismiss flag
- After resolving, auto-advance to the next flagged memory for efficient triage
- Edit is inline in the panel — content becomes editable, save button replaces action buttons
- Dismissed flags are hidden until the next scan; if the conflict still exists, it re-flags

### Staleness & threshold tuning
- A memory is stale if it's old AND hasn't been retrieved recently (age + retrieval frequency)
- Stale memory actions: archive (soft-delete, recoverable) or dismiss (keep, re-scan later)
- Settings panel (gear icon on health tab) with all config in one place: scan interval, age threshold, retrieval window, similarity threshold
- Operators can adjust all thresholds from the dashboard

### Claude's Discretion
- Default threshold values (age, retrieval window, similarity score)
- Exact diff highlighting approach for conflict panel
- Animation/transition for auto-advance between flags
- Summary bar visual design and color palette

</decisions>

<specifics>
## Specific Ideas

- Conflict panel should feel like a diff view — side-by-side with highlighted differences, familiar to developers
- Triage flow should be efficient: auto-advance keeps operators in flow state without manual navigation
- Settings panel is a single consolidated place — not scattered across multiple locations

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 40-memory-health-monitor*
*Context gathered: 2026-02-24*
