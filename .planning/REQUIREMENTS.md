# Requirements: OpenClaw v1.6 (Agent Autonomy)

**Defined:** 2026-02-25  
**Updated:** 2026-02-26  
**Core Value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## v1.6 MVP Requirements

### Autonomy Core (AUTO)

- [ ] **AUTO-01**: L3 agents perform self-directed task breakdown and planning
  - Agent decomposes high-level tasks into executable sub-tasks
  - Sub-tasks tracked with individual autonomy contexts
  - Planning phase completes before execution begins

- [ ] **AUTO-02**: Agents self-escalate based on confidence thresholds
  - Confidence calculated from complexity, ambiguity, past success, time estimate
  - Escalation triggered when confidence < 0.6 (configurable)
  - Escalation event emitted with reason and context

- [ ] **AUTO-03**: Context-aware tool selection based on task intent
  - Tool registry with capability descriptions
  - Task-to-tool matching based on semantic similarity
  - Fallback to general execution when no match

- [ ] **AUTO-04**: Progress self-monitoring and course correction
  - State transitions tracked (PLANNING → EXECUTING → BLOCKED/COMPLETE)
  - Automatic retry from BLOCKED (1 retry max, configurable)
  - Course correction when stuck detected

- [ ] **AUTO-05**: Autonomous handoff to L2 when blocked or complete
  - Terminal states: COMPLETE, ESCALATING
  - L2 notified with full context on escalation
  - Clean handoff without data loss

### Test & Quality (TEST)

- [ ] **TEST-01**: Fix autonomy framework test failures
  - Correct event_bus patching in test_integration.py
  - All autonomy tests passing

- [ ] **TEST-02**: E2E tests for autonomy lifecycle
  - Happy path: PLANNING → EXECUTING → COMPLETE
  - Retry path: EXECUTING → BLOCKED → EXECUTING → COMPLETE
  - Escalation path: EXECUTING → BLOCKED → ESCALATING

### Dashboard (DSH)

- [ ] **DSH-AUTO-01**: Display autonomy state per task
  - State badge (planning/executing/blocked/complete/escalating)
  - Confidence score visualization

- [ ] **DSH-AUTO-02**: Escalation notifications
  - Real-time alert when escalation triggered
  - Context panel with escalation reason

### Integration (INT)

- [ ] **INT-01**: Wire autonomy hooks into spawn flow
  - on_task_spawn creates AutonomyContext
  - on_container_healthy transitions to EXECUTING
  - on_task_complete/on_task_failed handle terminal states

- [ ] **INT-02**: L3 container self-reporting
  - AutonomyClient in L3 containers reports state
  - Sentinel file backup when HTTP unavailable

## Out of Scope

- Persistent L3 agents (ephemeral by design)
- Multi-agent coordination confidence scoring
- ML-based AdaptiveScorer implementation
- Automatic task re-planning after external changes

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTO-01 | Phase 55 | Pending |
| AUTO-02 | Phase 54 | Implemented (tests pending) |
| AUTO-03 | Phase 56 | Pending |
| AUTO-04 | Phase 54 | Implemented (tests pending) |
| AUTO-05 | Phase 54 | Implemented (tests pending) |
| TEST-01 | Phase 55 | Pending |
| TEST-02 | Phase 56 | Pending |
| DSH-AUTO-01 | Phase 57 | Pending |
| DSH-AUTO-02 | Phase 57 | Pending |
| INT-01 | Phase 55 | Pending |
| INT-02 | Phase 55 | Pending |
