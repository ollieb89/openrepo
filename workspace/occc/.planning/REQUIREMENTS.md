# Requirements: Nexus-Sync

**Defined:** 2026-02-24
**Core Value:** A user can ask one question and reliably understand what changed across communication and project systems for a feature.

## v1 Requirements

### Integrations

- [ ] **INTG-01**: User can connect a Slack workspace and sync selected channels.
- [ ] **INTG-02**: User can connect one project tracker (GitHub Issues or Linear) and sync issue metadata.
- [ ] **INTG-03**: User can run incremental sync so only new/changed items are processed after first import.
- [ ] **INTG-04**: User can view connector health (connected, rate-limited, auth-expired).

### Decision Summaries

- [ ] **SUMM-01**: User can view AI-generated summaries of key decisions from Slack threads.
- [ ] **SUMM-02**: Each summary includes source references (channel/thread links, message timestamps).
- [ ] **SUMM-03**: User can mark a summary as incorrect and hide it from project context.

### Auto-Linking

- [ ] **LINK-01**: System suggests links when a conversation likely relates to an existing issue.
- [ ] **LINK-02**: User can accept or reject each suggested link.
- [ ] **LINK-03**: Accepted links are visible from both sides (chat context and issue context).

### Catch Me Up

- [ ] **CMEU-01**: User can ask natural-language catch-up questions scoped to a feature/topic.
- [ ] **CMEU-02**: Responses include a timeline of notable updates across Slack and issue tracker.
- [ ] **CMEU-03**: Responses include citation links back to the original sources.

### Privacy & Local-First

- [x] **PRIV-01**: Raw content processing and embeddings run locally by default.
- [x] **PRIV-02**: Any remote inference path must use encrypted transit and explicit opt-in.
- [x] **PRIV-03**: System stores only minimum metadata required for retrieval and linking.

### Desktop Performance

- [ ] **PERF-01**: Background CPU usage remains low during idle listening/sync.
- [ ] **PERF-02**: Initial sync progress is visible and resumable after interruption.
- [ ] **PERF-03**: Query response time is fast enough for interactive catch-up workflows.

## v2 Requirements

### Additional Sources

- **SRC-01**: Add Discord connector with parity to Slack ingestion.
- **SRC-02**: Add email connector for decision extraction from threads.

### Advanced Reasoning

- **REAS-01**: Multi-project context graph and cross-project dependency insights.
- **REAS-02**: Proactive "risk drift" alerts for unresolved decision changes.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full chat client replacement UI | Nexus-Sync is middleware-first for MVP speed and focus |
| Notion/Jira support in v1 | Keep integration surface narrow until Slack + GitHub/Linear quality is proven |
| Autonomous write-back to issues/chats | High trust risk; require human confirmation in v1 |
| Training foundation models on customer data | Violates privacy-first product constraint |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTG-01 | Phase 2 | Pending |
| INTG-02 | Phase 2 | Pending |
| INTG-03 | Phase 2 | Pending |
| INTG-04 | Phase 2 | Pending |
| SUMM-01 | Phase 3 | Pending |
| SUMM-02 | Phase 3 | Pending |
| SUMM-03 | Phase 3 | Pending |
| LINK-01 | Phase 4 | Pending |
| LINK-02 | Phase 4 | Pending |
| LINK-03 | Phase 4 | Pending |
| CMEU-01 | Phase 5 | Pending |
| CMEU-02 | Phase 5 | Pending |
| CMEU-03 | Phase 5 | Pending |
| PRIV-01 | Phase 1 | Complete |
| PRIV-02 | Phase 1 | Complete |
| PRIV-03 | Phase 1 | Complete |
| PERF-01 | Phase 5 | Pending |
| PERF-02 | Phase 2 | Pending |
| PERF-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after Phase 1 completion*
