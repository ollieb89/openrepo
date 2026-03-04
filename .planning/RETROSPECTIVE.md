# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.6 — Agent Autonomy

**Shipped:** 2026-02-26
**Phases:** 7 (54-60) | **Plans:** 14 executed | **Timeline:** 2 days (2026-02-25 → 2026-02-26)

### What Was Built
- 4-state autonomy framework (PLANNING → EXECUTING → BLOCKED/ESCALATING → COMPLETE) with event bus integration and spawn hooks
- Self-directed task decomposition via LLM planning phase before L3 execution
- Confidence-based escalation with indefinite pause loop until L2 reviews and resumes
- Context-aware tool selection with intent analysis and prompt injection into L3 planning
- Progress self-monitoring with heuristic deviation detection and LLM-driven course correction
- Dashboard autonomy UI: state badges, confidence indicators, escalation alerts, Resume/Fail APIs
- 16 E2E autonomy tests covering happy path, retry, escalation, and multi-step scenarios

### What Worked
- Phase decomposition was well-scoped — each phase addressed one autonomy capability cleanly
- Event bus architecture (from v1.5) provided clean integration points for autonomy events
- Docker-based E2E testing infrastructure (mock LLM server) enabled deterministic autonomy testing
- Backward-compatible L3 entrypoint (AUTONOMY_ENABLED flag) avoided breaking existing workflows

### What Was Inefficient
- AUTO-05 (progress self-monitoring) partially satisfied — heuristic deviation detection works but LLM reflection quality depends heavily on prompt engineering
- Phase 54 had 4 plans for what could have been 2-3 (design doc + verification could merge with implementation)
- E2E test infrastructure (phase 59) required significant setup that could have been scaffolded earlier

### Patterns Established
- Autonomy state machine pattern: finite states with event-driven transitions
- Confidence scoring protocol: pluggable scorer interface with threshold-based and adaptive implementations
- L3 self-reporting via sentinel files: lightweight status communication without network dependency
- Mock LLM server pattern for deterministic testing of LLM-dependent features

### Key Lessons
1. Event bus architecture pays dividends — v1.5's event bus made autonomy integration straightforward
2. Confidence thresholds need tuning per-project — a single default won't work for all task types
3. E2E test infrastructure should be built alongside the first feature, not as a separate late phase

### Cost Observations
- Model mix: ~80% opus, ~20% sonnet
- Sessions: ~4-5
- Notable: Compact milestone — 14 plans across 7 phases in 2 days

---

## Milestone: v2.0 — Structural Intelligence

**Shipped:** 2026-03-04
**Phases:** 7 (61-67) | **Plans:** 17 executed | **Timeline:** 15 days (2026-02-17 → 2026-03-04)

### What Was Built
- Topology as data — swarm structures as explicit graph objects with JSON serialization, versioning, diffing, archetype classification
- Structure proposal engine — LLM-powered multi-candidate proposals with 7-dimension rubric scoring and constraint linting
- Dual correction system — soft re-proposal (cycle-limited) + hard direct edit (execute-then-analyze) with approval gate
- Structural memory — correction diffs, decay-weighted preference profiling, epsilon-greedy exploration, LLM pattern extraction
- Topology observability — React Flow DAG, dual-panel comparison, correction timeline, confidence evolution chart
- Gap closure phases (66-67) — rubric score wiring to ConfidenceChart, public API exports, broken import fixes

### What Worked
- Milestone audit caught 2 integration gaps (INT-01, INT-02) before shipping — resolved with focused gap closure phases
- Dataclass-based data model (consistent with AgentSpec pattern) kept topology code lightweight and testable
- TDD discipline across all phases — 457+ tests gave high confidence in correctness
- Clean phase dependencies — each phase built on the previous one's exports without circular imports
- Separate topology file storage avoided fcntl contention with existing workspace-state.json

### What Was Inefficient
- Dual TopologyProposal classes (proposer.py vs proposal_models.py) — conversion shim adds maintenance burden
- Phase 62 had 5 plans where the first 2 were actually Phase 61 prerequisites — planning could be tighter
- Phase 65 visual verification requires human browser inspection — 6 items still pending manual check
- TOBS-04 time-travel simplified to diff-highlights-on-current instead of full historical reconstruction
- Hardcoded OPENCLAW_ROOT fallback pattern perpetuated across new dashboard API routes

### Patterns Established
- Topology data isolation: dedicated `topology/` directory with own fcntl locks, never in workspace-state.json
- Multi-candidate proposal pattern: always generate all 3 archetypes for comparison
- Correction-as-training: every human edit feeds structural memory for future preference scoring
- Approval gate enforcement: no L3 spawn without explicit topology approval
- Rubric scoring pipeline: score → approve → annotate → dashboard — data flows through the full stack

### Key Lessons
1. Milestone audits before shipping catch real gaps — both INT-01 and INT-02 would have been tech debt without the audit
2. Gap closure phases (small, focused) are effective for resolving audit findings without scope creep
3. Structural memory isolation requires dual-layer defense (pre-filter + category exclusion) — single-layer is insufficient
4. React Flow v12 generics changed from v11 — `NodeProps<Node<Data>>` not `NodeProps<Data>` caused initial confusion

### Cost Observations
- Model mix: ~85% opus, ~15% sonnet
- Sessions: ~8-10
- Notable: 7 phases in 15 days including 2 gap closure phases added mid-milestone from audit findings

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 10 | 25 | Foundation — established 3-tier hierarchy |
| v1.1 | 8 | 17 | Multi-project — per-project namespacing |
| v1.2 | 7 | 14 | Hardening — structured logging, caching |
| v1.3 | 13 | 19 | Memory — memU integration, SOUL injection |
| v1.4 | 6 | 16 | Operations — graceful shutdown, health monitoring |
| v1.5 | 9 | 22 | Config — consolidation, schema validation, Notion sync |
| v1.6 | 7 | 14 | Autonomy — self-directed execution, escalation |
| v2.0 | 7 | 17 | Structural Intelligence — topology proposals, corrections, memory |

### Cumulative Quality

| Milestone | Tests | Key Verification |
|-----------|-------|-----------------|
| v1.0 | 16 req, 5 E2E | Full requirement + integration coverage |
| v1.1 | 23 req | Config decoupling verified |
| v1.2 | 16 req | Logging + reliability verified |
| v1.3 | 21 req | Memory pipeline E2E verified |
| v1.4 | 21 req, 148 tests | Full test suite |
| v1.5 | 21 req, 268 tests | Integration + schema tests |
| v1.6 | 10/11 req, 16 E2E | Autonomy lifecycle tests |
| v2.0 | 31/31 req, 457+ tests | Full topology stack verified + milestone audit |

### Top Lessons (Verified Across Milestones)

1. Event-driven architecture compounds value — each milestone leverages the event bus more deeply (v1.5 Notion sync, v1.6 autonomy events)
2. Per-project isolation is non-negotiable — every feature must be scoped by project ID (established v1.1, reinforced every milestone since)
3. Docker-based testing enables confidence — L3 container testing (v1.0) and E2E autonomy testing (v1.6) both critical for shipping reliably
4. Config consolidation before new features saves rework — v1.5's config cleanup made v1.6 autonomy config integration clean
5. Milestone audits before shipping catch integration gaps — v2.0 audit found 2 issues that were resolved before release
6. Gap closure phases (small, focused) resolve audit findings without scope creep — v2.0 added phases 66-67 mid-milestone
