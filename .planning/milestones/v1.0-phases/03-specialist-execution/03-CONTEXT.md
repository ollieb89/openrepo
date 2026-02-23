# Phase 3: Specialist Execution - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy isolated L3 specialist containers and implement Jarvis Protocol state synchronization. L3 specialists are dynamically spawned by L2 (PumplAI_PM) to execute tasks with physical container isolation. State changes flow up through `state.json` for hierarchy-wide visibility. Semantic snapshots capture workspace changes as git diffs.

Requirements: HIE-03, HIE-04, COM-03, COM-04

</domain>

<decisions>
## Implementation Decisions

### Specialist roster
- Single generic L3 specialist type (not Frontend/Backend split) — specialize later
- Runtime-agnostic: L3 containers support Claude Code CLI, Codex CLI, or Gemini CLI
- L2 delegates with task description + skill hint — L3 uses the hint but can adapt
- Full workspace mount (read/write access to entire project directory)
- On-demand GPU flag — L2 specifies whether a task needs GPU passthrough; only flagged containers get it
- Registered skill model — L3 has a defined skill registry; L2 picks from available skills
- Initial skills: Code + Test (write/edit code and run tests — the core development loop)

### Spawning & lifecycle
- L2 (PumplAI_PM) is the exclusive spawn authority — only L2 creates L3 containers
- Up to 3 concurrent L3 containers
- Auto-retry once on failure — if still fails after retry, report to L2 with context

### State visibility
- Full activity log in state.json — everything the L3 does is captured, not just status + result
- CLI/log output for human operator in Phase 3 — a CLI command or log tail to watch L3 activity in real-time (full dashboard deferred to Phase 4)

### Workspace persistence
- Semantic snapshots are git diffs of workspace changes
- L3 works on a staging branch — L2 reviews and merges into main workspace
- Staging branch model provides a natural review gate before changes land

### Claude's Discretion
- Container lifecycle model (ephemeral vs persistent) — trade-offs to evaluate
- State propagation mechanism (polling vs push events)
- L1 visibility into L3 state (through L2 aggregation vs direct read)
- Timeout strategy for L3 tasks
- Snapshot timing (on task completion vs on each commit)
- Snapshot retention policy
- CLI runtime selection mechanism (how L2 or config determines which CLI to use)

</decisions>

<specifics>
## Specific Ideas

- The swarm should feel like a team of developers working in parallel on branches, with a project manager (L2) reviewing and merging their work
- CLI runtime flexibility (Claude/Codex/Gemini) is important — the system should not be locked to a single AI provider
- Human operator wants real-time visibility into L3 activity even before the Phase 4 dashboard exists

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-specialist-execution*
*Context gathered: 2026-02-17*
