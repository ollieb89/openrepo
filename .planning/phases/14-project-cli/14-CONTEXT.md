# Phase 14: Project CLI - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

CLI subcommands (`openclaw project init|list|switch|remove`) that let users manage projects without hand-editing JSON files. Template presets pre-populate sensible defaults for common stack types. The project management model (project.json schema, SOUL.md rendering) already exists from prior phases — this phase wraps it in a CLI interface.

</domain>

<decisions>
## Implementation Decisions

### Init experience
- Interactive fallback: if `--id` or `--name` are missing, prompt interactively; flags override prompts
- On ID collision: prompt "Project X exists. Overwrite? [y/N]" in interactive mode; error and exit in non-interactive mode
- Default workspace path: `workspace/<project-id>/` inside the openclaw root directory
- Auto-activate: newly created project becomes the active project immediately

### Safety & edge cases
- `switch` guard: block if any L3 Docker containers are currently running for the active project (check running containers, not task status)
- `remove` confirmation: always prompt "Remove project X and all its files? [y/N]"; `--force` flag skips confirmation
- `remove` scope: only deletes the project registration (`projects/<id>/` directory with project.json, SOUL.md); workspace directory (`workspace/<id>/`) is preserved
- Corrupt/missing project.json: `list` and `switch` skip broken projects with a warning line (e.g., "(corrupt)"), don't crash or block other projects

### Claude's Discretion
- Output formatting for `list` (table style, colors, column widths)
- Template system implementation details (directory structure, preset contents)
- Error message wording and exit codes
- How interactive prompts are implemented (readline, rich, etc.)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-project-cli*
*Context gathered: 2026-02-23*
