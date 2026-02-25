---
phase: 40-memory-health-monitor
plan: 03
subsystem: ui
tags: [react, nextjs, tailwind, memory, health, conflict-resolution, diff, settings]

# Dependency graph
requires:
  - phase: 40-02
    provides: HealthTab with flag map, health-scan proxy, HealthFlag interface, MemoryPanel scaffolding

provides:
  - ConflictPanel component with LCS word-diff, side-by-side view, edit/delete/dismiss actions, auto-advance
  - SettingsPanel component with all 5 health thresholds (scan interval, age, retrieval, similarity range)
  - MemoryPanel integration of both panels with proper state management and API wiring
  - Archive action for stale flags in HealthTab

affects: [phase-41, phase-42]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - LCS word-diff algorithm (~50 lines) without external library — common/added/removed token arrays rendered with mark spans
    - Slide-in side panel with fixed+right positioning and backdrop overlay click-to-close
    - Inline conflict resolution flow: edit textarea / delete confirmation / dismiss — all call onAdvanceNext for sequential triage
    - HealthSettings type exported from SettingsPanel as single source of truth (imported by MemoryPanel)
    - Optional prop pattern for HealthTab extensions (onArchiveMemory?: optional) preserving backward compat

key-files:
  created:
    - workspace/occc/src/components/memory/ConflictPanel.tsx
    - workspace/occc/src/components/memory/SettingsPanel.tsx
  modified:
    - workspace/occc/src/components/memory/MemoryPanel.tsx
    - workspace/occc/src/components/memory/HealthTab.tsx

key-decisions:
  - "LCS word-diff splits on whitespace (\\s+ regex) preserving original spacing tokens — simple and faithful to original formatting"
  - "ConflictPanel renders both DiffView columns simultaneously — A shows removed/common, B shows added/common giving natural diff intuition"
  - "SettingsPanel is ephemeral session-only state (no backend persistence) per CONTEXT.md scope decision"
  - "HealthSettings type defined once in SettingsPanel.tsx, imported by MemoryPanel — avoids duplicate interface"
  - "onArchiveMemory is optional prop on HealthTab — archive calls PUT with {archived_at: ISO string} and dismisses flag client-side"
  - "handleAdvanceNext filters conflict flags only (not stale) for sequential conflict triage — stale flags have their own dismiss/archive path"

patterns-established:
  - "Slide-in side panel: fixed right-0 top-0 h-full max-w-2xl with backdrop div at z-40, panel at z-50"
  - "Inline delete confirmation: boolean confirmingDelete state within panel — no separate dialog component needed"
  - "Auto-advance pattern: onAdvanceNext callback provided by parent, child calls after any resolution action"

requirements-completed: [QUAL-06]

# Metrics
duration: 5min
completed: 2026-02-24
---

# Phase 40 Plan 03: Memory Health Monitor — Conflict Resolution UI Summary

**ConflictPanel with LCS word-diff highlighting and sequential resolution flow, plus SettingsPanel consolidating all 5 health thresholds in one place**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-24T17:45:01Z
- **Completed:** 2026-02-24T17:49:19Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- ConflictPanel: slide-in panel from right showing both conflicting memories side by side with LCS-based word-diff highlighting (green additions, red strikethrough removals), similarity score badge, and three resolution actions (edit/delete/dismiss)
- Edit mode: textarea replaces left column content with save/cancel, calls PUT /api/memory/[id] on save
- Delete mode: inline confirmation ("Delete Memory A?") then DELETE, both followed by onAdvanceNext auto-advance
- Auto-advance: after any resolution, MemoryPanel's handleAdvanceNext finds the next conflict flag in ordered list and opens it, or closes panel if none remain
- SettingsPanel: dropdown for scan interval (Off/15m/30m/1hr/2hr), number inputs for age threshold, retrieval window, similarity min/max with appropriate step values
- HealthTab: Archive button added for stale flags (calls PUT with archived_at ISO timestamp, then dismisses flag client-side)

## Task Commits

1. **Task 1: ConflictPanel with diff view and resolution actions** - `bfa2ae5` (feat)
2. **Task 2: SettingsPanel and MemoryPanel integration** - `494ac3e` (feat)

## Files Created/Modified

- `/home/ollie/.openclaw/workspace/occc/src/components/memory/ConflictPanel.tsx` - Slide-in conflict resolution panel with LCS word-diff, edit/delete/dismiss actions, auto-advance
- `/home/ollie/.openclaw/workspace/occc/src/components/memory/SettingsPanel.tsx` - Settings panel with 5 health threshold controls, exports HealthSettings interface
- `/home/ollie/.openclaw/workspace/occc/src/components/memory/MemoryPanel.tsx` - Integrated ConflictPanel and SettingsPanel with state management, real API handlers
- `/home/ollie/.openclaw/workspace/occc/src/components/memory/HealthTab.tsx` - Added optional onArchiveMemory prop, Archive button for stale flags

## Decisions Made

- LCS word-diff splits on `\s+` regex preserving spacing tokens for faithful rendering of original formatting
- ConflictPanel renders both columns from the same DiffView — Memory A shows common+removed, Memory B shows common+added for natural diff intuition
- SettingsPanel uses ephemeral session-only state — no backend persistence (per CONTEXT.md scope decision)
- HealthSettings type defined once in SettingsPanel.tsx and imported by MemoryPanel (single source of truth)
- onArchiveMemory is optional on HealthTab to preserve backward compatibility
- handleAdvanceNext only sequences through conflict flags — stale flags have dismiss/archive as independent actions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing TypeScript error in `SummaryStream.tsx` (unterminated string literal from embedded newline character) was present before this plan. Not caused by this plan's changes and not within scope to fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- QUAL-06 satisfied: conflict resolution UI complete with diff view, edit/delete/dismiss, auto-advance, and settings panel
- Phase 40 complete — all QUAL-01 through QUAL-06 requirements delivered across plans 01-03
- Phase 41 (L1 Strategic Suggestions) is next — approval gate should be built before suggestion pipeline per research flags

---
*Phase: 40-memory-health-monitor*
*Completed: 2026-02-24*
