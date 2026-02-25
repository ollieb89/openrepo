# Requirements: OpenClaw v1.4 Operational Maturity

**Defined:** 2026-02-24
**Core Value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## v1.4 Requirements

Requirements for v1.4 Operational Maturity. Each maps to roadmap phases.

### Reliability (Graceful Sentinel)

- [x] **REL-04**: L3 entrypoint uses exec form so Python process is PID 1 and receives SIGTERM directly from Docker
- [x] **REL-05**: L3 container handles SIGTERM via bash trap, writes `interrupted` status to Jarvis state before exit
- [x] **REL-06**: Pool scans for orphaned tasks (in_progress/interrupted/starting beyond skill timeout) on startup and applies configurable recovery policy (mark_failed / auto_retry / manual)
- [x] **REL-07**: Recovery policy is configurable per-project via `l3_overrides.recovery_policy` in project.json
- [x] **REL-08**: Pending fire-and-forget asyncio memorization tasks are drained (gathered) on pool shutdown instead of silently lost

### Quality (Memory Health Monitor)

- [x] **QUAL-01**: Batch health scan detects stale memories older than configurable threshold (default 30 days) that haven't been retrieved recently
- [x] **QUAL-02**: Batch health scan detects conflicting memories via pgvector cosine similarity range query (same topic, different verdict)
- [x] **QUAL-03**: Health scan returns scored list of flagged memories with flag type, similarity score, and recommendation
- [x] **QUAL-04**: New `PUT /memories/:id` endpoint in memory service allows updating memory content
- [x] **QUAL-05**: Dashboard /memory page displays health badges on flagged memories with staleness and conflict indicators
- [x] **QUAL-06**: Dashboard side panel shows conflict details (both memories, similarity score) with actions: edit, delete, dismiss flag

### Advanced (L1 Strategic Suggestions)

- [x] **ADV-01**: Pattern extraction engine queries memU for rejection clusters and identifies recurring failure patterns via frequency counting (threshold: ≥3 similar rejections within lookback window)
- [x] **ADV-02**: Suggestion generator produces concrete diff-style SOUL amendments with pattern description, evidence count, and exact text to add to soul-override.md
- [x] **ADV-03**: Pending suggestions stored in `workspace/.openclaw/<project_id>/soul-suggestions.json`
- [x] **ADV-04**: L2 acceptance flow reads pending suggestions and accepts (appends to soul-override.md, re-renders SOUL) or rejects (memorizes rejection reason)
- [x] **ADV-05**: Dashboard surfaces pending SOUL suggestions with accept/reject actions for operator review
- [x] **ADV-06**: Auto-apply of suggestions without human approval is structurally prevented (mandatory approval gate)

### Performance (Delta Snapshots)

- [x] **PERF-05**: Per-project `memory_cursors` tracked in state.json metadata with ISO timestamp of last successful retrieval
- [x] **PERF-06**: Pre-spawn retrieval fetches only memories newer than cursor; falls back to full fetch on any error
- [x] **PERF-07**: New `created_after` filter parameter on memU `/retrieve` endpoint supports cursor-based queries
- [x] **PERF-08**: Configurable `max_snapshots` per project with automatic pruning of oldest snapshots beyond the limit

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Memory

- **ADV-07**: Cross-project memory health aggregation with opt-in per-project
- **ADV-08**: SOUL version history with automatic rollback on performance regression
- **ADV-09**: TTL-based memory expiry policies for high-volume projects

### Reliability

- **REL-09**: Docker health checks for L3 containers with configurable probe intervals

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-apply L1 suggestions without approval | Documented prompt injection vector — incorrect suggestions silently degrade all future L3 tasks |
| Time-based automatic memory garbage collection | Recency bias deletes valid institutional knowledge (coding style, conventions) |
| Real-time conflict alerts on every memory write | Full-store scan per write is expensive; batch scan is sufficient |
| Cross-project health aggregation | Breaks per-project isolation; defer to explicit opt-in design |
| Snapshot compression / binary format | .diff files are small and human-readable for L2 review; compression destroys debuggability |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REL-04 | Phase 39 | Complete |
| REL-05 | Phase 39 | Complete |
| REL-06 | Phase 39 | Complete |
| REL-07 | Phase 39 | Complete |
| REL-08 | Phase 43 | Complete |
| QUAL-01 | Phase 40 | Complete |
| QUAL-02 | Phase 40 | Complete |
| QUAL-03 | Phase 40 | Complete |
| QUAL-04 | Phase 40 | Complete |
| QUAL-05 | Phase 40 | Complete |
| QUAL-06 | Phase 40 | Complete |
| ADV-01 | Phase 43 | Complete |
| ADV-02 | Phase 43 | Complete |
| ADV-03 | Phase 43 | Complete |
| ADV-04 | Phase 43 | Complete |
| ADV-05 | Phase 41 | Complete |
| ADV-06 | Phase 41 | Complete |
| PERF-05 | Phase 42 | Complete |
| PERF-06 | Phase 42 | Complete |
| PERF-07 | Phase 42 | Complete |
| PERF-08 | Phase 42 | Complete |

**Coverage:**
- v1.4 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓
- Pending (gap closure): 5 (ADV-01, ADV-02, ADV-03, ADV-04, REL-08 → Phase 43)

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 — traceability confirmed after roadmap creation*
