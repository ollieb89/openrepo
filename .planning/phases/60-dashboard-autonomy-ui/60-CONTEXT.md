---
phase: 60
slug: dashboard-autonomy-ui
created: 2026-02-26
milestone: v1.6
---

# Phase 60: Dashboard Autonomy UI

**Goal**: Implement DSH-AUTO-01 and DSH-AUTO-02 (Dashboard autonomy state display and escalation notifications)

**Depends on**: Phase 54, 55, 56, 57, 58
**Requirements**: DSH-AUTO-01, DSH-AUTO-02

## Context

The autonomy framework emits rich events (`AutonomyStateChanged`, `AutonomyConfidenceUpdated`, `AutonomyEscalationTriggered`, `AutonomyToolsSelected`, `AutonomyCourseCorrection`) but the dashboard has no UI to display this information. Operators cannot see:

- Which tasks are in PLANNING vs EXECUTING vs BLOCKED
- Confidence scores for in-progress tasks
- Which tools an L3 agent has selected
- When escalations occur and why

## Success Criteria

- [ ] State badge component (planning/executing/blocked/complete/escalating)
- [ ] Confidence score visualization (progress bar + numeric)
- [ ] Selected tools display per task
- [ ] Real-time escalation alert banner
- [ ] Escalation context panel with reason and confidence
- [ ] Course correction history view

## Plans

- 60-01-PLAN.md — Autonomy State Dashboard Components
- 60-02-PLAN.md — Escalation Notifications & Real-time Alerts

## References

- v1.6 Milestone Audit: `.planning/v1.6-MILESTONE-AUDIT.md`
- Requirements DSH-AUTO-01/02: `.planning/REQUIREMENTS.md`
