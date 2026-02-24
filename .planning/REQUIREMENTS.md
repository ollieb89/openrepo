# Requirements: OpenClaw v1.4 Operational Maturity

**Defined:** 2026-02-24
**Core Value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## v1.4 Requirements

Requirements for v1.4 Operational Maturity. Each maps to roadmap phases.

### Reliability (Graceful Sentinel)

- [ ] **REL-04**: L3 entrypoint uses exec form so Python process is PID 1 and receives SIGTERM directly from Docker
- [ ] **REL-05**: L3 container handles SIGTERM via bash trap, writes `interrupted` status to Jarvis state before exit
- [ ] **REL-06**: Pool scans for orphaned tasks (in_progress/interrupted/starting beyond skill timeout) on startup and applies configurable recovery policy (mark_failed / auto_retry / manual)
- [ ] **REL-07**: Recovery policy is configurable per-project via `l3_overrides.recovery_policy` in project.json
- [ ] **REL-08**: Pending fire-and-forget asyncio memorization tasks are drained (gathered) on pool shutdown instead of silently lost

### Quality (Memory Health Monitor)

- [ ] **QUAL-01**: Batch health scan detects stale memories older than configurable threshold (default 30 days) that haven't been retrieved recently
- [ ] **QUAL-02**: Batch health scan detects conflicting memories via pgvector cosine similarity range query (same topic, different verdict)
- [ ] **QUAL-03**: Health scan returns scored list of flagged memories with flag type, similarity score, and recommendation
- [ ] **QUAL-04**: New `PUT /memories/:id` endpoint in memory service allows updating memory content
- [ ] **QUAL-05**: Dashboard /memory page displays health badges on flagged memories with staleness and conflict indicators
- [ ] **QUAL-06**: Dashboard side panel shows conflict details (both memories, similarity score) with actions: edit, delete, dismiss flag

### Advanced (L1 Strategic Suggestions)

- [ ] **ADV-01**: Pattern extraction engine queries memU for rejection clusters and identifies recurring failure patterns via frequency counting (threshold: ≥3 similar rejections within lookback window)
- [ ] **ADV-02**: Suggestion generator produces concrete diff-style SOUL amendments with pattern description, evidence count, and exact text to add to soul-override.md
- [ ] **ADV-03**: Pending suggestions stored in `workspace/.openclaw/<project_id>/soul-suggestions.json`
- [ ] **ADV-04**: L2 acceptance flow reads pending suggestions and accepts (appends to soul-override.md, re-renders SOUL) or rejects (memorizes rejection reason)
- [ ] **ADV-05**: Dashboard surfaces pending SOUL suggestions with accept/reject actions for operator review
- [ ] **ADV-06**: Auto-apply of suggestions without human approval is structurally prevented (mandatory approval gate)

### Performance (Delta Snapshots)

- [ ] **PERF-05**: Per-project `memory_cursors` tracked in state.json metadata with ISO timestamp of last successful retrieval
- [ ] **PERF-06**: Pre-spawn retrieval fetches only memories newer than cursor; falls back to full fetch on any error
- [ ] **PERF-07**: New `created_after` filter parameter on memU `/retrieve` endpoint supports cursor-based queries
- [ ] **PERF-08**: Configurable `max_snapshots` per project with automatic pruning of oldest snapshots beyond the limit

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
| REL-04 | Phase 39 | Pending |
| REL-05 | Phase 39 | Pending |
| REL-06 | Phase 39 | Pending |
| REL-07 | Phase 39 | Pending |
| REL-08 | Phase 39 | Pending |
| QUAL-01 | Phase 40 | Pending |
| QUAL-02 | Phase 40 | Pending |
| QUAL-03 | Phase 40 | Pending |
| QUAL-04 | Phase 40 | Pending |
| QUAL-05 | Phase 40 | Pending |
| QUAL-06 | Phase 40 | Pending |
| ADV-01 | Phase 41 | Pending |
| ADV-02 | Phase 41 | Pending |
| ADV-03 | Phase 41 | Pending |
| ADV-04 | Phase 41 | Pending |
| ADV-05 | Phase 41 | Pending |
| ADV-06 | Phase 41 | Pending |
| PERF-05 | Phase 42 | Pending |
| PERF-06 | Phase 42 | Pending |
| PERF-07 | Phase 42 | Pending |
| PERF-08 | Phase 42 | Pending |

**Coverage:**
- v1.4 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 — traceability confirmed after roadmap creation*
