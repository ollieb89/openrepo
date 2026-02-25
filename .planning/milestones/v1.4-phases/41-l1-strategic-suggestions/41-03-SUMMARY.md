---
phase: 41-l1-strategic-suggestions
plan: 03
subsystem: ui
tags: [next.js, react, swr, tailwind, suggestions, dashboard]

# Dependency graph
requires:
  - phase: 41-02
    provides: "Suggestions API routes (GET/POST /api/suggestions, POST /api/suggestions/[id]/action)"

provides:
  - "Suggestions dashboard page at /suggestions with SuggestionsPanel"
  - "SuggestionCard with expand/accept/reject flows and inline confirmation"
  - "DismissedTab lightweight archive list"
  - "Sidebar Suggestions nav item with red pending count badge"
  - "Shared TypeScript interfaces: Suggestion, SuggestionsData, EvidenceExample"

affects:
  - 41-l1-strategic-suggestions
  - future-phases-using-suggestions

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useSWR hook inline in panel component (same pattern as useMemory)"
    - "Accept-as-is approval flow with inline confirmation (no diff editing)"
    - "Sidebar badge via localStorage projectId read to avoid ProjectContext dependency"

key-files:
  created:
    - workspace/occc/src/lib/types/suggestions.ts
    - workspace/occc/src/app/suggestions/page.tsx
    - workspace/occc/src/components/suggestions/SuggestionsPanel.tsx
    - workspace/occc/src/components/suggestions/SuggestionCard.tsx
    - workspace/occc/src/components/suggestions/DismissedTab.tsx
  modified:
    - workspace/occc/src/components/layout/Sidebar.tsx

key-decisions:
  - "SuggestionCard renders accepted state as a green confirmation card (card stays visible as confirmation, not removed)"
  - "Sidebar reads projectId from localStorage directly (not ProjectContext) to avoid circular dependency in layout"
  - "DismissedTab shows plain text list — no expand/accept/reject, lightweight audit record only"

patterns-established:
  - "Suggestion approval UI: collapsed card (description + evidence count) expands to show diff + evidence examples"
  - "Reject flow: first click shows optional text field, Dismiss sends, Cancel aborts"

requirements-completed:
  - ADV-05

# Metrics
duration: 4min
completed: 2026-02-24
---

# Phase 41 Plan 03: Suggestions Dashboard UI Summary

**Next.js Suggestions dashboard with SWR-backed SuggestionCard accept/reject flows, DismissedTab archive, and Sidebar pending count badge**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-24T17:02:54Z
- **Completed:** 2026-02-24T17:06:14Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Suggestions dashboard page at `/suggestions` surfacing pending SOUL suggestion cards ordered by evidence_count descending
- Per-card accept/reject flows: accept sends to API and shows inline "Applied to soul-override.md" confirmation; reject reveals optional text field with Dismiss/Cancel buttons
- Sidebar red badge overlay on Suggestions nav icon showing pending count, polling every 30s
- Empty state showing last_run timestamp and "No patterns met the threshold" when no pending suggestions exist

## Task Commits

1. **Task 1: Types, page, and SuggestionsPanel (+ SuggestionCard, DismissedTab)** - `e8e5c98` (feat)
2. **Task 2: Sidebar badge** - `b99f5f5` (feat)

## Files Created/Modified

- `workspace/occc/src/lib/types/suggestions.ts` - Shared TypeScript interfaces: Suggestion, SuggestionsData, EvidenceExample
- `workspace/occc/src/app/suggestions/page.tsx` - Page wrapper using useProject() context
- `workspace/occc/src/components/suggestions/SuggestionsPanel.tsx` - Tab host with useSuggestions SWR hook, run-analysis button, pending/dismissed tabs, empty state
- `workspace/occc/src/components/suggestions/SuggestionCard.tsx` - Individual card with expand/accept/reject flows and inline confirmation
- `workspace/occc/src/components/suggestions/DismissedTab.tsx` - Lightweight dismissed suggestions archive list
- `workspace/occc/src/components/layout/Sidebar.tsx` - Added Suggestions nav item with red pending count badge (30s polling)

## Decisions Made

- SuggestionCard accepted state: card stays visible as a green confirmation banner ("Applied to soul-override.md") rather than disappearing — gives operator clear visual feedback before SWR cache updates
- Sidebar reads projectId from localStorage directly (not ProjectContext) to avoid React context dependency in layout component, consistent with plan spec
- DismissedTab is plain text list only — no expand, no accept/reject — satisfying CONTEXT.md "accessible but not prominent" requirement

## Deviations from Plan

None - plan executed exactly as written. SuggestionCard and DismissedTab were created in Task 1 (alongside the Panel) rather than Task 2 since they are imported by SuggestionsPanel and needed for the TypeScript build check. Task 2 then focused on Sidebar only.

Note: A pre-existing TypeScript parse error exists in `workspace/occc/src/components/sync/SummaryStream.tsx` (unterminated string literal from commit b091531). This is out of scope — existed before this plan and was not caused by these changes.

## Issues Encountered

None.

## Next Phase Readiness

Phase 41 Plans 01-03 are all complete. The full L1 Strategic Suggestions feature is implemented:
- Plan 01: suggest.py pattern engine
- Plan 02: API routes with approval gate
- Plan 03: Dashboard UI with accept/reject flows and Sidebar badge

Phase 42 (Delta Snapshots) is next.

---
*Phase: 41-l1-strategic-suggestions*
*Completed: 2026-02-24*
