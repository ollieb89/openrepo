---
phase: 54-autonomy-framework
created: 2026-02-25
milestone: v1.6
---

# Phase 54: Autonomy Framework — Context

**Gathered:** 2026-02-25
**Status:** Ready for execution
**Plans:** 4 plans created

## Phase Boundary

Define the foundational architecture and interfaces for agent autonomy in OpenClaw. This phase establishes the decision-making framework that allows L3 agents to self-direct their work.

## Plans

| Plan | File | Goal |
|------|------|------|
| 54-01 | [54-01-PLAN.md](./54-01-PLAN.md) | Core interfaces and state machine |
| 54-02 | [54-02-PLAN.md](./54-02-PLAN.md) | Confidence scorer and config schema |
| 54-03 | [54-03-PLAN.md](./54-03-PLAN.md) | Integration hooks and event bus wiring |
| 54-04 | [54-04-PLAN.md](./54-04-PLAN.md) | Design doc and verification |

## Scope

**In scope:**
- Autonomy state machine design
- Confidence scoring interface
- Escalation threshold configuration
- Tool selection heuristics schema
- Progress tracking data model

**Out of scope:**
- Full implementation (later phases)
- Dashboard UI changes
- Memory system modifications

## Implementation Decisions

### State Machine Design
- **4-state model**: planning → executing → complete|escalating
- **Escalating is a state** that pauses work until L2 reviews (not just a transition)
- **Self-recovery allowed**: 1 automatic retry attempt from 'blocked' before escalating
- **Distributed ownership**: Each L3 self-reports state via sentinel file or state.json

### Integration Architecture
- **Integration approach**: Hook into existing spawn/execute flow at task creation
- **Persistence**: Store autonomy state in memU memory system for cross-restart recall
- **Dashboard communication**: Claude's discretion — use existing SSE patterns or polling
- **Pool/spawn interaction**: Emit events to existing event bus (decoupled)

### Claude's Discretion
- Dashboard communication mechanism (push vs pull)
- Specific sentinel file format for L3 self-reporting
- Event schema for autonomy-related events

## Specific Ideas

- State transitions should be observable in dashboard with clear visual indicators
- Escalation state should show reason/context to L2 for faster review
- Memory-based persistence enables "resume where I left off" even after container restart

## Deferred Ideas

- Adaptive confidence thresholds that learn from past escalations (future phase)
- Autonomous task breakdown into sub-tasks (new capability — separate phase)
- Cross-project autonomy coordination (future enhancement)

## Dependencies

- v1.5 milestone complete (phases 45-53)
- Config consolidation provides path/constant foundation
- Phase 52 suggestion system as baseline for confidence concepts

## Success Criteria

1. [ ] `autonomy/` package created with core interfaces
2. [ ] `AutonomyState` enum defined (planning, executing, blocked, complete, escalating)
3. [ ] `ConfidenceScorer` protocol established
4. [ ] Escalation threshold config schema added to `openclaw.json`
5. [ ] Design doc approved (stored in `.planning/research/`)

## Related Documents

- `.planning/v1.6-MILESTONE-AUDIT.md` — milestone tracking
- `.planning/ROADMAP.md` — autonomy requirements source
- `packages/orchestration/src/openclaw/config.py` — config schema location

---

*Phase: 54-autonomy-framework*
*Context gathered: 2026-02-25*
