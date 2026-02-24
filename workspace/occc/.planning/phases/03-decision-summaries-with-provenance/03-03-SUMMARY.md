---
phase: 03-decision-summaries-with-provenance
plan: 03
subsystem: ui-dashboard
tags: [ui, decisions, human-in-the-loop, correction]
requires:
  - phase: 03-decision-summaries-with-provenance
    plan: 02
    provides: decision extraction engine
provides:
  - Chronological Decision Log UI with citation provenance
  - Human-in-the-loop correction (Hide, Re-summarize with Hints)
  - Dashboard integration for recent decisions
affects: [ui, api-routes, summarizer]
tech-stack:
  added: [lucide-react]
  patterns: [human-in-the-loop, provenance-first-ui]
key-files:
  created:
    - src/app/decisions/page.tsx
    - src/components/decisions/DecisionCard.tsx
    - src/app/api/decisions/[id]/route.ts
    - src/app/api/decisions/[id]/re-summarize/route.ts
    - src/components/common/ContextCard.tsx
    - src/lib/connectors/health-payload.ts
  modified:
    - src/app/page.tsx
    - src/app/api/decisions/route.ts
    - src/lib/sync/summarizer.ts
    - src/lib/types/decisions.ts
key-decisions:
  - "Added `connectorId` and `sourceId` to the `Decision` model to enable tracing back to raw material for re-summarization."
  - "Implemented 'Re-summarize with Hints' to allow users to guide the local LLM towards more accurate or focused outcomes."
  - "Decisions are surfaced on the main dashboard as 'Recent Decisions' cards to minimize tab-switching for common context checks."
requirements-completed: [SUMM-03]
duration: 60 min
completed: 2026-02-24
---

# Phase 03 Plan 03: Decision Log UI and Correction Loop Summary

**The user-facing surface for Phase 3 is now live, providing a transparent, verifiable, and editable log of project decisions.**

## Accomplishments
- **Interactive Decision Log:** Created a high-density feed at `/decisions` that displays outcomes, participants, and citations.
- **Correction Loop:** Implemented backend and frontend support for hiding garbage summaries and re-triggering extraction with user-provided hints.
- **Context Integration:** Surfaced the 3 most recent decisions on the main dashboard to provide immediate project situational awareness.
- **Build Stability:** Fixed several pre-existing type and lint errors that were blocking the build, ensuring the new components meet production standards.

## Decisions Made
- **Provenance-First UI:** Citation snippets are always visible and explicitly linked to Slack to maintain trust in AI-generated content.
- **Hints over Manual Edits:** Chose to implement 'Re-summarize with Hints' rather than direct manual editing of outcomes to preserve the link between the summary and the source text while still allowing user refinement.

## Phase Completion
- Phase 3 is now fully implemented.
- The system correctly ingests Slack threads, extracts privacy-safe decisions locally via Phi-3, and presents them for user review and catch-up.
- **Ready for Phase 4: Auto-Link Suggest/Review Loop.**
