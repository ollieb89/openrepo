# Research Summary: Nexus-Sync v1.1 "Global Project Brain"

**Domain:** Multi-source project context and risk intelligence
**Researched:** 2025-10-24
**Overall confidence:** HIGH

## Executive Summary

The transition from a single-project context bridge (v1.0) to a "Global Project Brain" (v1.1) requires moving beyond simple ingestion to active intelligence. The core of this phase is the **Cross-Project Context Graph**, which maps relationships across different silos (e.g., a Slack decision in Project A affecting a GitHub issue in Project B). Research indicates that SQLite's **Recursive CTEs** are the most efficient way to handle these transitive dependencies locally, provided that depth limits and indexing are strictly enforced.

A critical differentiator in v1.1 is **Risk Drift Detection**. By comparing natural language decisions extracted from chat (Slack/Discord/Teams) with structured metadata in work trackers (GitHub/Linear), Nexus-Sync can identify contradictions in dates, priorities, and assignees. This is achieved through **Structured Prompt Chaining**, where LLMs are tasked with identifying semantic mismatches between two disparate data objects.

Ingestion expansion into **Discord and Microsoft Teams** leverages existing incremental sync patterns but introduces new challenges: Microsoft Teams provides robust **Delta Queries**, while Discord requires a hybrid of **Gateway (WebSocket) events** for real-time and **paginated REST** for historical backfills.

## Key Findings

**Stack:** SQLite with Recursive CTEs for graph traversal; Microsoft Graph Delta Queries for Teams; Structured LLM Prompting for contradiction detection.
**Architecture:** Adjacency list storage for the Context Graph; LLM-driven comparison pipeline for Risk Drift.
**Critical pitfall:** **Contradiction Alert Fatigue**—over-reporting minor discrepancies can lead to users ignoring the system. Mitigation involves high-confidence thresholds and "Actionable Insight" grouping.

## Implications for Roadmap

Suggested phase structure for v1.1:

1.  **Phase 1.1.a: Context Graph Foundation** - Implement recursive CTEs and adjacency list schema in SQLite to map cross-project links.
2.  **Phase 1.1.b: Risk Drift Intelligence** - Implement the LLM comparison pipeline between Slack and GitHub/Linear metadata.
3.  **Phase 1.1.c: Ingestion Expansion** - Build Teams (Delta Query) and Discord (Gateway + REST) connectors.
4.  **Phase 1.1.d: Health Dashboard** - Develop the visualization layer for surfacing high-risk linkages and contradictions.

**Phase ordering rationale:**
- The Graph Foundation is a prerequisite for mapping cross-project risks.
- Intelligence (Risk Drift) adds the most value and should be validated before the visualization layer is finalized.
- Expansion to Discord/Teams broadens the data pool for the Graph.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Recursive CTEs and Delta Queries are industry standards. |
| Features | MEDIUM | Risk Drift is technically feasible but requires prompt tuning for precision. |
| Architecture | HIGH | Adjacency lists are well-proven for SQLite graph storage. |
| Pitfalls | MEDIUM | Alert fatigue is a known UX risk; mitigation effectiveness needs testing. |

## Gaps to Address

- Performance benchmarking for recursive CTEs on graphs with >100k edges.
- Fine-tuning the "Abstain" threshold for LLM contradiction detection to minimize false positives.
- Handling Discord's eventual consistency in high-volume servers.
