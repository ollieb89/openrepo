# Phase 20: Reliability Hardening - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Prevent silent data loss from JSON corruption in workspace-state.json and catch misconfigured projects/agents at load time with clear, actionable errors. No new features — this hardens existing state management and config loading paths.

</domain>

<decisions>
## Implementation Decisions

### Validation strictness
- Validate configs at startup only — no runtime/hot-reload validation needed
- project.json required fields: `workspace` and `tech_stack` (everything else can have sensible defaults)
- openclaw.json `reports_to` chain validation: Claude decides severity-based strictness (fail-fast vs warn)
- Claude decides whether to fail on first validation error or collect all errors per file type

### State backup & recovery
- Single `.bak` file strategy: `workspace-state.json.bak`
- Backup created **before every write** — copy current to .bak, then write new content
- If write is interrupted, .bak always has the last known-good state
- No backup rotation or timestamping — one copy is sufficient

### Recovery behavior
- On corruption detection: auto-recover from .bak and log a warning
- Warning format: one-liner with cause, e.g. `WARNING: workspace-state.json was corrupt (invalid JSON). Restored from backup.`
- Claude decides what counts as "corrupt" (invalid JSON only vs schema violations too)

### Error messaging style
- Human-friendly messages with fix hints, e.g. `project.json: missing required field "workspace". Add a workspace path pointing to your project directory.`
- Always include file path + field name to pinpoint the problem
- Recovery warnings are one-liners with cause — no verbose diffs
- Claude decides whether to use ANSI color (TTY detection) or plain text

### Claude's Discretion
- Fail-first vs collect-all validation strategy (per file type)
- reports_to chain validation strictness level
- Corruption detection threshold (JSON parse failure only, or also schema violations)
- Terminal color/formatting approach

</decisions>

<specifics>
## Specific Ideas

- Error messages should feel like helpful compiler errors — tell you what's wrong AND how to fix it
- Recovery should be invisible to the user except for the warning line — no prompts, no pauses
- Every state write path must go through backup — no exceptions, no shortcuts

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-reliability-hardening*
*Context gathered: 2026-02-24*
