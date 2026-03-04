---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Structural Intelligence
status: executing
stopped_at: Completed 01-protocol-foundations-02-PLAN.md
last_updated: "2026-03-04T12:58:29.056Z"
last_activity: 2026-03-04 — Phase 01 Plan 01 complete (native ACP WebSocket endpoint, ServerAcpTranslator, E2E tests)
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 13
  completed_plans: 13
  percent: 5
---

# Project State: OpenClaw Agent Orchestration

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** The system designs and refactors its own orchestration
**Current focus:** Phase 01: Protocol Foundations — ACP native WebSocket endpoint

## Current Position

Phase: 01-protocol-foundations
Plan: 1 of ? in current phase
Status: Executing
Last activity: 2026-03-04 — Phase 01 Plan 01 complete (native ACP WebSocket endpoint, ServerAcpTranslator, E2E tests)

Progress: [█░░░░░░░░░] 5% (phase 01 — 1/? plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed (v2.0): 1
- Average duration: 15min
- Total execution time: 15min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 62-01 | 1 | 15min | 15min |

*Updated after each plan completion*
| Phase 62 P02 | 4 | 2 tasks | 5 files |
| Phase 62 P04 | 3min | 2 tasks | 3 files |
| Phase 62-03 P03 | 5 | 2 tasks | 7 files |
| Phase 62 P05 | 5 | 3 tasks | 10 files |
| Phase 63 P01 | 4min | 1 tasks | 5 files |
| Phase 63 P03 | 5min | 2 tasks | 4 files |
| Phase 63 P02 | 6min | 2 tasks | 6 files |
| Phase 64-structural-memory P01 | 3min | 1 tasks | 4 files |
| Phase 64-structural-memory P02 | 5min | 2 tasks | 5 files |
| Phase 65-topology-observability P01 | 3min | 3 tasks | 12 files |
| Phase 65-topology-observability P02 | 5min | 2 tasks | 9 files |
| Phase 65-topology-observability PP03 | 4min | 2 tasks | 6 files |
| Phase 65-topology-observability P03 | 30min | 3 tasks | 6 files |
| Phase 01-protocol-foundations P01 | 15min | 3 tasks | 6 files |
| Phase 01-protocol-foundations P02 | 3min | 2 tasks | 6 files |

## Accumulated Context

### Decisions

- [v2.0 init]: Multi-proposal default — always return all 3 archetypes (Lean/Balanced/Robust); single-best recommendation abandoned
- [v2.0 init]: Execute-then-analyze on hard correction — user authority respected, async diff analysis non-blocking
- [v2.0 init]: Topology confidence and autonomy confidence are separate config keys — `topology.proposal_confidence_warning_threshold` vs `autonomy.confidence_threshold`
- [v2.0 init]: Topology data stored in separate `topology/` directory — never in workspace-state.json, never flock-contended with L3
- [v2.0 init]: Structural memory uses `category="structural_topology"` exclusion to prevent L3 SOUL context contamination
- [v2.0 init]: Preference profiling uses 14-day decay half-life and 20% epsilon-greedy exploration — built before first correction influences proposals
- [62-01]: Used @dataclass (not Pydantic) for topology models consistent with AgentSpec pattern
- [62-01]: EdgeType serializes as string value (e.g. "delegation") not enum name for human-readable JSON
- [62-01]: Topology directory separate from workspace-state.json to avoid fcntl contention with L3 containers
- [Phase 62]: Edges matched by endpoint pair (from_role, to_role) — different edge_type is a modification not add+remove
- [Phase 62]: Robust requires review_gate AND (escalation OR multi-coord-paths) — single review gate = balanced
- [Phase 62]: Balanced is explicit catch-all fallback archetype — classification is always exhaustive
- [Phase 62]: TopologyProposal defined in proposer.py (not proposal_models.py) since plan 03 not yet executed and plan 04 does not depend on it
- [Phase 62]: LLM client raises on HTTP errors and missing API keys — caller handles retries, not the client
- [Phase 62-03]: Rubric warning logic warns on ANY review gate loss (not just total loss) — partial safety reduction is significant
- [Phase 62-03]: preference_fit always returns 5 pre-Phase 64 (neutral baseline; Phase 64 adds adaptive preference scoring)
- [Phase 62-03]: Removal cost model for auto-constrain: +10 per review_gate edge, +1 per coordination edge — reviewers are expensive to remove
- [Phase 62]: proposer.TopologyProposal (.graph) converted to proposal_models.TopologyProposal (.topology) in CLI via _to_pm_proposals() helper
- [Phase 62]: score_proposal() standalone function added to rubric.py as wrapper around RubricScorer class
- [Phase 63-01]: CorrectionSession uses @dataclass consistent with AgentSpec/TopologyGraph patterns
- [Phase 63-01]: apply_soft_correction raises ValueError before LLM call when cycle limit reached (no wasted API call)
- [Phase 63-01]: compute_pushback_note never raises — catches all exceptions and returns empty string for safety
- [Phase 63]: Propose directives bypass the approval gate — they create topology, not consume it
- [Phase 63]: Gate condition requires projectId presence — absent active_project silently passes gate to avoid breaking bare installs
- [Phase 63]: render_diff_summary placed in renderer.py not propose.py — renderer is the presentation layer
- [Phase 63]: _parse_selection supports bare 'approve' (no number) — selects first proposal as default
- [Phase 63]: approve.py duplicates _parse_selection without command prefix — simpler than cross-CLI import
- [Phase 64-structural-memory]: Affinity normalization uses fractional deviation from equal-share mapped to [0,10] — equal corrections returns [5,5,5]
- [Phase 64-structural-memory]: explore param passed by caller (not drawn internally) — enforces session-level epsilon-greedy
- [Phase 64-structural-memory]: Dual-layer isolation: Layer 1 pre-filter uses metadata.category fallback to match both storage formats
- [Phase 64-structural-memory]: explore flag drawn once per session at call site in propose.py — not per-archetype
- [Phase 64-structural-memory]: ArchetypeClassifier enrichment and MemoryProfiler recompute are both non-blocking in approval.py
- [Phase 65-01]: Topology nav uses Network icon from lucide-react; SWR 30s refresh (topology changes on corrections not continuously); API routes return null/[] for missing files (valid pre-proposal state)
- [Phase 65-02]: NodeProps<Node<Data>> not NodeProps<Data> — @xyflow/react v12 generic requires the full Node type as the type parameter
- [Phase 65-02]: TopologyNodeData/TopologyEdgeData exported from topology-utils.ts to avoid circular imports; edge diff key uses 'from_role->to_role' string format
- [Phase 65-topology-observability]: Time-travel v1: shows diff highlights on current topology (not full historical reconstruction) — clearly indicated by amber banner; full reconstruction deferred
- [Phase 65-topology-observability]: Time-travel v1 simplification approved: diff highlights on current topology (not full historical reconstruction) — amber banner indicates selected correction; explicitly reviewed and accepted at checkpoint
- [Phase 01-01]: ACP endpoint uses separate acpWss instance — clean routing via ACP_WS_PATH="/v1/acp" constant in attachGatewayUpgradeHandler
- [Phase 01-01]: context.broadcast patched in-place (not replaced) — existing Gateway WS clients unaffected; ACP translators intercept broadcast events via wrap
- [Phase 01-01]: E2E tests named *.e2e.test.ts in test/e2e/ — matches vitest.e2e.config.ts include pattern
- [Phase 01-02]: workspaceDir in _meta overrides params.cwd — meta takes precedence for workspace isolation
- [Phase 01-02]: authProfileId stored on AcpSession and forwarded to chat.send — parse once on session create, use throughout session lifetime

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-04T12:54:39.898Z
Stopped at: Completed 01-protocol-foundations-02-PLAN.md
Resume file: None
