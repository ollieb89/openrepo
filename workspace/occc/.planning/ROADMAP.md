# Roadmap: Nexus-Sync v1.1

- **[v1.4 (SHIPPED)](./milestones/v1.4-ROADMAP.md)**: Privacy-first context bridge with Slack/GitHub/Linear integration and natural language catch-up.

---

## Phase 6: Global Context Graph

**Goal:** Map relationships between decisions and work items across different silos and projects.

**Mapped requirements:** REAS-03, REAS-04, REAS-05

**Success criteria:**
- Bidirectional "edges" between disparate records are stored in a centralized SQLite table.
- Users can query the system to find transitive dependencies (e.g., "Find all issues affected by this Slack decision").
- Catch Me Up retrieval applies a relevance boost to records linked via the graph.

**Plans:** 3 plans
- [x] 06-01-PLAN.md — Graph Schema & Edge Persistence
- [x] 06-02-PLAN.md — Recursive Dependency Queries
- [x] 06-03-PLAN.md — Graph-Aware Catch Me Up Ranking

---

## Phase 7: Risk Drift Intelligence

**Goal:** Proactively identify contradictions between natural language decisions and structured ticket metadata.

**Mapped requirements:** REAS-06, REAS-07, REAS-08

**Success criteria:**
- LLM audits Slack decisions against GitHub/Linear issue states (dates, owners, priorities).
- Mismatches are flagged with explicit confidence scores and "Contradiction Reason" metadata.
- False positive rate is minimized through high-confidence thresholds.

**Plans:** 3 plans
- [ ] 07-01-PLAN.md — Decision-to-Tracker Audit Pipeline
- [ ] 07-02-PLAN.md — Contradiction Scoring & Confidence Gating
- [ ] 07-03-PLAN.md — Risk Synthesis Prompting

---

## Phase 8: Ingestion Expansion (Discord/Teams)

**Goal:** Broaden the project brain's data pool with Teams and Discord connectivity.

**Mapped requirements:** INTG-05, INTG-06, INTG-07

**Success criteria:**
- Microsoft Teams channel messages ingested via Microsoft Graph Delta Queries.
- Discord server messages ingested via Gateway (real-time) and REST (historical) hybrid.
- New source data is vectorized and available for Catch Me Up queries.

**Plans:** 3 plans
- [ ] 08-01-PLAN.md — Microsoft Teams Delta Ingestion
- [ ] 08-02-PLAN.md — Discord Gateway & REST Adapter
- [ ] 08-03-PLAN.md — Multi-Source Vector Ingestion

---

## Phase 9: Health & Visualization

**Goal:** Provide high-level oversight of project risks and contradictions.

**Mapped requirements:** UI-04, UI-05, UI-06

**Success criteria:**
- "Project Health" tab displays impact/likelihood heatmap of detected risks.
- Risks are injected as actionable alerts within the Catch Me Up timeline.
- Users can "Pin" insights to convert ephemeral alerts into permanent project markers.

**Plans:** 2 plans
- [ ] 09-01-PLAN.md — Health Dashboard Heatmap
- [ ] 09-02-PLAN.md — Integrated Risk UI & Insight Pinning

---
*Last updated: 2026-02-24 for v1.1 Milestone*
