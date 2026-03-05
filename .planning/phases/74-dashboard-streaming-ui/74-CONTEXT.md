# Phase 74: Dashboard Streaming UI - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a terminal-style live output panel integrated with the task board. Users click any task card to open its L3 output stream in a side panel. This is a UI verification and polish phase — the infrastructure (SSE, LogViewer, TaskTerminalPanel, TaskBoard wiring) was largely built during Phase 71. Phase 74 verifies the full end-to-end experience works, fills UX gaps, and satisfies DASH-01/DASH-02/DASH-03 success criteria.

</domain>

<decisions>
## Implementation Decisions

### What already exists (verified from codebase)
- `LogViewer.tsx`: Full SSE-based terminal component connected to `/api/events`, filters by taskId, auto-scroll with pause-on-scroll-up, "↓ scroll to resume" indicator on scroll-up, 1000-line rolling buffer, exponential backoff reconnection
- `TaskTerminalPanel.tsx`: Right-side panel (`w-80`) wrapping LogViewer — task ID header, StatusBadge, close button, PipelineView stage indicator, completion banner ("syncing → stored" transition via supplementalLines from activity_log)
- `TaskBoard.tsx`: `selectedTaskId` state, `handleTaskClick`, renders `TaskTerminalPanel` alongside kanban columns
- Phase 71 delivers: TASK_OUTPUT events flowing from pool.py → event_bus → Unix socket → `/api/events` SSE

### Task card selected state
- **Gap confirmed:** `TaskCard` has no `selected` prop and no visual selected state — clicked card looks identical to unselected cards
- Planner should add `isSelected` prop to TaskCard with visual highlight (blue border ring or tinted background consistent with existing Tailwind dark/light patterns)
- No other TaskCard interaction needed beyond the existing click handler

### Panel layout
- Fixed `w-80` (320px) right-side panel — maintain as-is (matches existing design pattern)
- Claude's discretion on exact sizing if adjustment is needed for readability

### Completed/failed task access
- Existing behavior is correct: clicking any task opens the panel
  - In-progress tasks: live SSE stream via LogViewer
  - Completed/failed tasks: stored activity_log shown via supplementalLines (falls back gracefully)
- No change needed to this behavior

### Reconnection UX
- Carry Phase 71 decision: no missed-event replay on reconnect (in-memory only, fire-and-forget)
- Existing LogViewer error banner on disconnect is acceptable
- Claude's discretion on whether to make reconnect more subtle

### Auto-scroll behavior (DASH-03)
- DASH-03: "Scrolling back to bottom resumes auto-scroll **without clicking a button**"
- Existing LogViewer already implements this: scroll handler checks `atBottom` (within 20px threshold) and sets `autoScrollRef.current = true` — no button click required
- The "↓ scroll to resume" shown in the UI is an indicator, not a button — this satisfies DASH-03
- Verify this works correctly in end-to-end testing

### Claude's Discretion
- Exact visual style for task card selected state (blue ring, background tint, or combined)
- Whether to make SSE reconnect indicator more subtle
- Minor layout/spacing adjustments if needed for terminal readability

</decisions>

<specifics>
## Specific Ideas

No specific visual references provided. Follow existing dashboard dark/light theme patterns (Tailwind, gray-900 backgrounds for terminals, blue for interactive states).

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LogViewer.tsx` (`packages/dashboard/src/components/`): Production-ready terminal with SSE, auto-scroll, reconnect, 1000-line buffer — use as-is, no rebuild needed
- `TaskTerminalPanel.tsx` (`packages/dashboard/src/components/tasks/`): Side panel wrapper — use as-is, may need minor width/header tweaks
- `TaskBoard.tsx` (`packages/dashboard/src/components/tasks/`): Already wires click-to-select and renders TaskTerminalPanel — confirm correct behavior
- `TaskCard.tsx` (`packages/dashboard/src/components/tasks/`): Needs `isSelected` prop + selected visual state added
- `StatusBadge`, `Card` components: Existing UI primitives for consistent styling

### Established Patterns
- SSE events flow through `/api/events` — all components use `EventSource('/api/events')` with client-side filtering
- Auto-scroll pattern: `autoScrollRef` + scroll handler checks `scrollTop + clientHeight >= scrollHeight - 20` for bottom detection
- Dark/light theming via Tailwind dark: variants throughout (gray-800/gray-900 for dark terminal backgrounds)
- Phase 71 established: `TASK_OUTPUT` event type, `TaskOutputPayload` with `{line, stream}`, filtering by `task_id` in event envelope

### Integration Points
- `TaskBoard.tsx:handleTaskClick` → sets `selectedTaskId` → passes to `TaskTerminalPanel` → passes to `LogViewer` as `taskId`
- `LogViewer` → `EventSource('/api/events')` → filters `parsed.task_id === effectiveTaskId` for TASK_OUTPUT events
- `/api/events/route.ts` → Unix socket bridge → Python event bus → pool.py emit
- `TaskCard.tsx`: needs `isSelected: boolean` prop passed from TaskBoard (which has `selectedTaskId`)

</code_context>

<deferred>
## Deferred Ideas

- Resizable panel — out of scope for Phase 74, consider Phase 77 or backlog
- Fullscreen terminal mode — separate capability, backlog
- Search/filter within terminal output — separate capability, backlog

</deferred>

---

*Phase: 74-dashboard-streaming-ui*
*Context gathered: 2026-03-05*
