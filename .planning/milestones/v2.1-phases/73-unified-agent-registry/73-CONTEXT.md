# Phase 73: Unified Agent Registry - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Agent configuration has one source of truth — per-agent config.json files — with auto-discovery at startup and drift warnings when central config diverges. Requirements: AREG-01 (single registry class), AREG-02 (auto-discovery), AREG-03 (drift detection).

</domain>

<decisions>
## Implementation Decisions

### Drift warning behavior
- Use Python logging at WARNING level — respects OPENCLAW_LOG_LEVEL, integrates with structured logging from Phase 68
- Warn on identity fields only: name, level, reports_to — fields that affect hierarchy and routing. Ignore extras like skill_registry, projects (only in per-agent)
- Warn with remediation hint: log mismatch AND suggest fix ("Run `openclaw agent sync` to update openclaw.json from per-agent configs"). Non-blocking — drift is informational, not fatal
- Orphan agents (in openclaw.json but not agents/ dir): warn with scaffold hint, register from openclaw.json data. Suggest "Run `openclaw agent init {id}` to create agents/{id}/agent/config.json". Backwards compatible

### Source of truth resolution
- Keep openclaw.json agents.list as a lightweight index (id, level, reports_to) for quick reference. Per-agent configs hold the full truth
- Per-agent config.json always wins on conflict — simple, predictable. Drift warning surfaces the mismatch
- agents.defaults section applies as fallback: model, sandbox, maxConcurrent from openclaw.json agents.defaults provide baseline values. Per-agent config overrides when specified
- Validate per-agent config.json with warnings: check required fields (id, level) exist, warn on unknown fields. Don't block — just surface issues

### Discovery conventions
- agents/{id}/agent/config.json must exist for auto-discovery — config.json = "this is an agent". Directories without it are ignored silently
- Underscore prefix directories are skipped (_templates, _fixtures) — already the convention in agent_registry.py
- Auto-discovery runs at startup + CLI refresh via `openclaw agent refresh` to rescan without restarting. Useful during development
- Agent ID derived from directory name. config.json id field must match or triggers drift warning. Filesystem-driven

### CLI output format
- `openclaw agent list` displays a table grouped by level: L1 first, then L2, then L3. Columns: ID, Name, Level, Reports To, Source
- Drift status shown inline via Status column: "✓" for clean, "⚠ drift" for mismatches, "new" for filesystem-only
- `--json` flag for programmatic use — consistent with Phase 72 CLI patterns
- Only `openclaw agent list` in this phase — matches AREG requirements exactly. Other subcommands (init, sync, inspect) are future work

### Claude's Discretion
- Table formatting library choice (tabulate, rich, plain formatting)
- Exact drift warning message wording
- Schema validation implementation (inline checks vs JSON Schema)
- How agent refresh integrates with existing CLI structure
- Internal registry caching strategy

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Success criteria are prescriptive:
1. Adding a new agent directory under agents/ with a config.json causes it to appear in the registry at next startup without editing openclaw.json
2. `openclaw agent list` shows agents discovered from the filesystem, not only those in openclaw.json
3. A mismatch between openclaw.json agents.list and agents/*/agent/config.json produces a startup warning that names the conflicting fields

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent_registry.py` (202 lines): AgentRegistry class + AgentSpec dataclass already exist. Merges both sources, per-agent wins. Missing: drift detection, CLI integration, startup wiring, defaults inheritance
- `config_validator.py`: Schema validation infrastructure — can be extended for per-agent config validation
- `config.py`: Runtime config loading, get_gateway_config() pattern to follow for get_agent_registry()

### Established Patterns
- Startup checks use ensure_gateway() pattern (Phase 72) — registry loading should follow similar pattern
- Python logging with OPENCLAW_LOG_LEVEL (Phase 68) — drift warnings use this
- CLI entry points in cli/ directory (monitor.py, project.py) — agent subcommand follows same structure
- Event bus for system events (Phase 70) — registry could optionally publish agent.discovered / agent.drift events

### Integration Points
- `packages/orchestration/src/openclaw/agent_registry.py`: Main file to enhance — add drift detection, defaults inheritance, validation
- CLI entry point: new `cli/agent.py` or extend existing CLI structure for `openclaw agent list`
- Startup path: wire registry loading into orchestration startup alongside ensure_gateway()
- `config/openclaw.json` agents section: read agents.list + agents.defaults

</code_context>

<deferred>
## Deferred Ideas

- `openclaw agent init {id}` — scaffold new agent directory with config.json template
- `openclaw agent sync` — write merged config back to openclaw.json
- `openclaw agent inspect {id}` — show full merged config for a single agent
- File watcher for live agent directory changes — too complex for this phase

</deferred>

---

*Phase: 73-unified-agent-registry*
*Context gathered: 2026-03-04*
