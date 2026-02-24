# Roadmap: Nexus-Sync v1

**Source inputs:** `PROJECT.md`, `REQUIREMENTS.md`, `research/SUMMARY.md`
**Planning depth:** standard
**Roadmap horizon:** v1 only

## Phase 1: Local-First Core & Privacy Guardrails

**Goal:** Establish local processing defaults and enforce explicit controls for any remote path.

**Mapped requirements:** PRIV-01, PRIV-02, PRIV-03

**Success criteria:**
- Local processing is the default execution path for content processing and embeddings.
- Remote inference path is disabled by default and requires explicit user opt-in before use.
- Remote path uses encrypted transit for all requests.
- Stored data is constrained to minimum metadata required for retrieval/linking (no unnecessary raw retention).

## Phase 2: Source Connectivity & Incremental Sync

**Goal:** Deliver reliable Slack + project tracker connectivity with resumable sync and health visibility.

**Mapped requirements:** INTG-01, INTG-02, INTG-03, INTG-04, PERF-02

**Success criteria:**
- User can connect one Slack workspace and select channels for sync.
- User can connect one project tracker (GitHub Issues or Linear) and ingest issue metadata.
- Incremental sync processes only net-new/changed records after first import.
- Sync progress is visible and resumes correctly after interruption.
- Connector health statuses (connected, rate-limited, auth-expired) are visible in product UI/diagnostics.

## Phase 3: Decision Summaries with Provenance

**Goal:** Produce trustworthy thread decision summaries with references and user correction control.

**Mapped requirements:** SUMM-01, SUMM-02, SUMM-03

**Success criteria:**
- Key decisions from synced Slack threads are summarized and available in project context.
- Each summary includes source references (thread/channel links and timestamps).
- User can mark incorrect summaries and hide them from active project context.

**Plans:** 3 plans
- [x] 03-01-PLAN.md — Decision Storage Foundation & Data Models
- [x] 03-02-PLAN.md — Local Decision Extraction Engine
- [x] 03-03-PLAN.md — Decision Log UI and Correction Loop

**Phase 4: Auto-Link & Review Loop**

**Plans:** 4 plans
- [x] 04-01-PLAN.md — Vector Store Initialization
- [x] 04-02-PLAN.md — Issue Indexer
- [x] 04-03-PLAN.md — Relevance Engine
- [x] 04-04-PLAN.md — Link UI & Review Loop

## Phase 5: Catch Me Up Experience & Runtime Performance

**Goal:** Ship core catch-up workflow with timeline/citations and interactive responsiveness under background load.

**Mapped requirements:** CMEU-01, CMEU-02, CMEU-03, PERF-01, PERF-03

**Success criteria:**
- User can ask natural-language catch-up questions scoped to a feature/topic.
- Responses include a timeline of notable updates across Slack and the connected tracker.
- Responses include citation links to original sources for verifiability.
- Idle/background listening and sync remain low-overhead for desktop usage.
- Catch-up responses return quickly enough to support interactive workflows.

**Plans:** 3 plans
- [x] 05-01-PLAN.md — The Intent & Temporal Engine
- [x] 05-02-PLAN.md — Streaming RAG & Synthesis
- [ ] 05-03-PLAN.md — The "Catch Me Up" UI

## Requirement-to-Phase Index

| Requirement | Phase |
|-------------|-------|
| PRIV-01 | Phase 1 |
| PRIV-02 | Phase 1 |
| PRIV-03 | Phase 1 |
| INTG-01 | Phase 2 |
| INTG-02 | Phase 2 |
| INTG-03 | Phase 2 |
| INTG-04 | Phase 2 |
| PERF-02 | Phase 2 |
| SUMM-01 | Phase 3 |
| SUMM-02 | Phase 3 |
| SUMM-03 | Phase 3 |
| LINK-01 | Phase 4 |
| LINK-02 | Phase 4 |
| LINK-03 | Phase 4 |
| CMEU-01 | Phase 5 |
| CMEU-02 | Phase 5 |
| CMEU-03 | Phase 5 |
| PERF-01 | Phase 5 |
| PERF-03 | Phase 5 |

## Notes

- Scope intentionally excludes v2 and out-of-scope items from `REQUIREMENTS.md`.
- Each v1 requirement maps to exactly one phase.
- Sequence follows privacy-first foundation, then connectivity, then user-facing intelligence.
- Progress sync (2026-02-24): Phase 1 is complete (`01-01` through `01-04`).
- Progress sync (2026-02-24): Phase 2 is complete (`02-01` through `02-05`).
- Progress sync (2026-02-24): Phase 3 is complete (`03-01` through `03-03`).
- Progress sync (2026-02-24): Phase 4 is complete (`04-01` through `04-04`).
- Next execution target: Phase 5 Catch Me Up Experience & Runtime Performance.

---
*Last updated: 2026-02-24 after 05 planning*
