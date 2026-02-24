# Requirements: Nexus-Sync v1.1 "Global Project Brain"

**Defined:** 2026-02-24
**Core Value:** A unified, intelligent project brain that identifies cross-project dependencies and proactive risk drift.

## Milestone Requirements

### 1. Multi-Source Expansion
- [ ] **INTG-05**: Microsoft Teams Connector — Ingest channel messages using Microsoft Graph Delta Queries.
- [ ] **INTG-06**: Discord Connector — Ingest server messages using a hybrid Gateway (real-time) and REST (historical) approach.
- [ ] **INTG-07**: Incremental indexing for new sources — Discord/Teams messages are vectorized and added to Catch Me Up index.

### 2. Global Context Graph
- [ ] **REAS-03**: Adjacency list schema — Persist bidirectional relationships (edges) between decisions, issues, and sources across project boundaries.
- [ ] **REAS-04**: Transitive dependency lookup — Implement recursive CTEs in SQLite to find "ripple effects" of a change across projects.
- [ ] **REAS-05**: Multi-Project Boost — Scoring engine boost (+0.3) for records in related projects, not just the active one.

### 3. Risk Drift Intelligence
- [ ] **REAS-06**: Decision-to-Tracker Comparison — LLM pipeline to audit Slack decisions against GitHub/Linear metadata (Dates, Status, Assignee).
- [ ] **REAS-07**: Contradiction Scoring — Detect and categorize risks (e.g., "Schedule Conflict", "Priority Mismatch", "Assignee Drift") with confidence levels.
- [ ] **REAS-08**: Actionable Insight Generation — Generate short summaries explaining *why* a contradiction was flagged.

### 4. Visibility & Health
- [ ] **UI-04**: "Project Health" Dashboard — High-level visualization of project risks using impact/likelihood heatmaps.
- [ ] **UI-05**: Integrated Catch Up Alerts — Inject risk drift insights directly into the "Catch Me Up" timeline.
- [ ] **UI-06**: Insight Pinning — Allow users to promote ephemeral risk insights to permanent "Project Alerts."

## Out of Scope
- **Write-back Automation**: Automatically updating Linear tickets based on Slack decisions (Deferred to v1.2+ for safety).
- **Voice/Meeting Transcription**: Teams/Discord voice support (Focus remains on text for v1.1).
- **Federated Graphs**: Syncing context graphs between different user machines (Remains local-first).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTG-05 | Phase 8: Ingestion Expansion | Pending |
| INTG-06 | Phase 8: Ingestion Expansion | Pending |
| INTG-07 | Phase 8: Ingestion Expansion | Pending |
| REAS-03 | Phase 6: Global Context Graph | Pending |
| REAS-04 | Phase 6: Global Context Graph | Pending |
| REAS-05 | Phase 6: Global Context Graph | Pending |
| REAS-06 | Phase 7: Risk Drift Intelligence | Pending |
| REAS-07 | Phase 7: Risk Drift Intelligence | Pending |
| REAS-08 | Phase 7: Risk Drift Intelligence | Pending |
| UI-04   | Phase 9: Health & Visualization | Pending |
| UI-05   | Phase 9: Health & Visualization | Pending |
| UI-06   | Phase 9: Health & Visualization | Pending |

---
*Next milestone pending: v1.1 "Global Project Brain"*
