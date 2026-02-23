# Phase 11: Config Decoupling Foundation - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Decouple all state/snapshot paths from hardcoded single-project constants. Establish per-project path resolution as the canonical pattern. Migrate the existing PumplAI system to the new structure without data loss. Dynamic branch detection for snapshot diffs. Agent config references resolve from project manifest instead of hardcoded strings.

</domain>

<decisions>
## Implementation Decisions

### Path convention
- All per-project runtime state lives under `workspace/.openclaw/<project_id>/`
- State file: `workspace/.openclaw/<project_id>/workspace-state.json`
- Snapshots organized by task: `workspace/.openclaw/<project_id>/snapshots/<task_id>/`
- The existing PumplAI project uses project ID `pumplai`
- Project config/manifest lives separately at `projects/<id>/project.json` (top-level, not under .openclaw)

### Migration strategy
- Migration is an explicit CLI command (not automatic on first run)
- Block migration if any tasks are in spawned/running state — print which tasks are blocking
- No --force flag; user must wait for tasks to complete
- Backup old state to a `.backup/` dir before moving files to new location
- Hard cutover after migration — old paths stop working immediately with clear error pointing to new location

### Config resolution API
- New dedicated module: `orchestration/project_config.py` (separate from existing config.py)
- Active project resolution: check `OPENCLAW_PROJECT` env var first, fall back to `active_project` field in `openclaw.json`
- Agent IDs are mapped explicitly in `projects/<id>/project.json` agents field (not convention-based lookup)
- Invalid/unknown project IDs raise `ProjectNotFoundError` — no silent fallback to wrong paths

### Branch detection
- Check `default_branch` field in project.json first
- Fall back to `git symbolic-ref refs/remotes/origin/HEAD` if not configured
- Detect fresh on every snapshot operation (no caching)

### Claude's Discretion
- Last-resort fallback behavior when neither config nor git heuristic can determine the default branch
- Internal structure of the backup directory during migration
- Exact error message wording for migration guards and path resolution errors
- How `project_config.py` internally loads and validates project.json

</decisions>

<specifics>
## Specific Ideas

- Two-tier separation: project definitions at `projects/<id>/` (config, manifest, soul overrides) vs runtime state at `workspace/.openclaw/<id>/` (state files, snapshots). Clean boundary between "what the project is" and "what the project is doing."
- Migration CLI should print a before/after summary showing old paths → new paths before executing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-config-decoupling-foundation*
*Context gathered: 2026-02-23*
