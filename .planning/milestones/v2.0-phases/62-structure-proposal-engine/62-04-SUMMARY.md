---
phase: 62-structure-proposal-engine
plan: 04
subsystem: topology
tags: [llm-client, httpx, async, jsonschema, proposal-generation, changelog-context, topology]

# Dependency graph
requires:
  - phase: 62-structure-proposal-engine
    plan: 01
    provides: "TopologyGraph, TopologyNode, TopologyEdge, EdgeType data models; load_changelog storage"
  - phase: 62-structure-proposal-engine
    plan: 02
    provides: "ArchetypeClassifier for downstream validation (not used directly in this plan)"

provides:
  - "topology/llm_client.py: async call_llm() for Anthropic and Gemini providers via httpx"
  - "topology/llm_client.py: strip_markdown_fences() strips ```json fences from LLM responses"
  - "topology/proposer.py: TopologyProposal dataclass with archetype, graph, justification, delegation, coordination, risk fields"
  - "topology/proposer.py: PROPOSAL_JSON_SCHEMA for validating lean/balanced/robust LLM output"
  - "topology/proposer.py: ask_clarifications() - hybrid TTY or non-interactive defaults"
  - "topology/proposer.py: _load_rejection_context() - changelog-based rejection context with graceful degradation"
  - "topology/proposer.py: generate_proposals() async pipeline with fence stripping, schema validation, retry blocklist"
  - "topology/proposer.py: build_proposals() raw dict -> list[TopologyProposal] with EdgeType mapping"
  - "topology/proposer.py: generate_proposals_sync() synchronous wrapper via asyncio.run()"
  - "tests/test_proposer.py: 31 tests covering all pipeline behaviors with mocked LLM"

affects:
  - 62-05 (renderer uses generate_proposals + build_proposals to present proposals to user)
  - 62-03 (linter/rubric will validate TopologyProposal objects produced by build_proposals)
  - 63-correction-tracking (generate_proposals retry support enables correction-driven re-proposal)

# Tech tracking
tech-stack:
  added:
    - httpx (async HTTP client for LLM API calls)
    - jsonschema (JSON Schema validation of LLM output)
  patterns:
    - "Async LLM client: call_llm() dispatches to provider-specific impl based on OPENCLAW_LLM_PROVIDER env"
    - "Markdown fence stripping: regex strip before json.loads() — pitfall prevention pattern"
    - "Changelog context injection: rejected patterns surfaced to LLM to avoid repeating failures"
    - "Retry blocklist: rejected_roles parameter adds explicit DO NOT USE block to system prompt"
    - "Hybrid input: ask_clarifications(interactive) uses isatty() branch for TTY vs piped stdin"
    - "Schema-validated LLM output: jsonschema.validate() before returning to caller"

key-files:
  created:
    - packages/orchestration/src/openclaw/topology/llm_client.py
    - packages/orchestration/src/openclaw/topology/proposer.py
    - packages/orchestration/tests/test_proposer.py
  modified: []

key-decisions:
  - "TopologyProposal defined in proposer.py (not proposal_models.py) since plan 03 not yet executed and plan 04 does not depend on it"
  - "LLM client raises on HTTP errors and missing API keys — caller (orchestrator) handles retries, not the client itself"
  - "Rejected roles injected as explicit DO NOT USE block for retry scenarios — additive to changelog context"
  - "Non-interactive mode returns defaults silently (no stdout) — interactive mode prompts via stdin"
  - "jsonschema.validate() called synchronously after JSON parse — no async schema validation needed"

patterns-established:
  - "LLM pattern: call_llm(system_prompt, user_message) -> strip_markdown_fences() -> json.loads() -> jsonschema.validate()"
  - "Proposal pipeline: outcome + registry + changelog -> system prompt -> LLM -> parse -> build_proposals()"
  - "Graceful degradation: _load_rejection_context() catches all exceptions, returns None on any failure"

requirements-completed: [PROP-01, PROP-04]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 62 Plan 04: LLM Proposal Generation Pipeline Summary

**Async LLM client (Anthropic/Gemini via httpx) and proposal generation pipeline that transforms outcome descriptions into 3 topology proposals (Lean/Balanced/Robust) with changelog context injection, markdown fence stripping, and retry blocklist support**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T20:21:04Z
- **Completed:** 2026-03-03T20:24:07Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `llm_client.py`: minimal provider-configurable async LLM client via httpx — Anthropic and Gemini both working; `strip_markdown_fences()` utility for JSON extraction
- `proposer.py`: full proposal generation pipeline — system prompt construction with roles/constraints/rejection context, async LLM call, fence strip, schema validation, and raw dict to TopologyProposal list conversion
- 31 tests passing with mocked LLM calls — covers build_proposals, ask_clarifications, rejection context loading, generate_proposals, JSON schema validation, and sync wrapper

## Task Commits

Each task was committed atomically:

1. **Task 1: LLM client** - `91eef81` (feat)
2. **RED tests** - `6b7dbf9` (test)
3. **Task 2: Proposer pipeline** - `5252e69` (feat)

## Files Created/Modified

- `packages/orchestration/src/openclaw/topology/llm_client.py` - async call_llm() for Anthropic/Gemini, strip_markdown_fences()
- `packages/orchestration/src/openclaw/topology/proposer.py` - TopologyProposal, PROPOSAL_JSON_SCHEMA, PROPOSAL_SYSTEM_PROMPT, ask_clarifications, _load_rejection_context, generate_proposals, build_proposals, generate_proposals_sync
- `packages/orchestration/tests/test_proposer.py` - 31 tests with mocked LLM covering all pipeline behaviors

## Decisions Made

- **TopologyProposal defined in proposer.py**: Plan 03 (which creates `proposal_models.py`) has not been executed yet and plan 04 does not declare it as a dependency. Defining TopologyProposal directly in proposer.py avoids an unsatisfied import and keeps this plan self-contained.
- **LLM client raises, does not retry**: HTTP errors and missing API keys raise immediately — the orchestrator layer decides retry strategy, not the client. Keeps the client minimal per plan spec.
- **Rejected roles are additive**: The `rejected_roles` parameter adds an explicit "DO NOT use these roles" block on top of changelog context — both can coexist in a retry scenario.

## Deviations from Plan

None - plan executed exactly as written.

The one deviation judgment call (where to define TopologyProposal) was resolved by following the dependency graph strictly: plan 04 depends on 62-01 and 62-02, not 62-03. TopologyProposal is a local concern of this pipeline.

## Issues Encountered

None.

## User Setup Required

To use the LLM proposal generation pipeline, configure one of:
- `ANTHROPIC_API_KEY` or `ANTHROPIC_TOKEN` (default provider: Anthropic)
- `GEMINI_API_KEY` + `OPENCLAW_LLM_PROVIDER=gemini` (for Gemini)

Optional overrides:
- `OPENCLAW_LLM_MODEL`: Override model name (defaults: `claude-sonnet-4-20250514` / `gemini-2.5-flash`)
- `OPENCLAW_LLM_PROVIDER`: `anthropic` (default) or `gemini`

## Next Phase Readiness

- `generate_proposals_sync()` ready for CLI entry point integration (plan 05 renderer)
- `build_proposals()` ready for plan 03 linter/rubric validation pipeline
- `TopologyProposal` dataclass fields match what plan 03's `proposal_models.py` will need to be compatible with
- All 31 tests passing — no regressions in topology package

---
*Phase: 62-structure-proposal-engine*
*Completed: 2026-03-03*
