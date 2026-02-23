# Phase 13: Multi-Project Runtime - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire project identity through the L3 container lifecycle — spawn, pool, and monitor become project-aware. Multiple projects can run L3 containers concurrently without name collisions, state file cross-contamination, or resource contention. This phase does NOT include CLI commands for project management (Phase 14) or dashboard changes (Phase 15).

</domain>

<decisions>
## Implementation Decisions

### Container naming & labels
- Enforce max length on project IDs (e.g. 20 chars) to keep `docker ps` output readable
- Container naming convention: `openclaw-<project>-l3-<task_id>`
- Single Docker label: `openclaw.project=<project_id>` — no additional metadata labels needed (workspace path, name live in project.json)

### Claude's Discretion: label extras
- Whether to add `openclaw.task.type=code|test` label for convenience filtering — Claude decides based on implementation utility

### Claude's Discretion: ID validation
- Whether to validate project IDs at init time (alphanumeric + hyphens only) or sanitize at spawn time — Claude picks the safest approach

### Monitor filtering
- Default behavior (no `--project` flag): show ALL projects with a project column in output
- Always include the project column in table/tail output, regardless of how many projects exist — consistent format for scripts
- `monitor.py task <id>`: search all projects for the task ID; if same ID found in multiple projects, list matches and prompt user to specify `--project`
- Color-code entries by project in `monitor.py tail` stream for visual distinction

### Mid-execution safety
- If `active_project` is switched while L3 containers are running: warn about in-flight containers from the previous project, but allow the switch. Running containers finish in their original project context (pinned via env var).
- spawn must hard-fail if it cannot resolve a valid project ID — no container without project context. Exit with clear error message.

### Claude's Discretion: env-var resolution chain
- Claude determines the safest resolution pattern for OPENCLAW_PROJECT across spawn, pool, state engine, and entrypoint.sh — env-var-first for containers at minimum

### Claude's Discretion: entrypoint verification
- Whether entrypoint.sh should independently verify OPENCLAW_PROJECT is set (defense in depth) or trust spawn — Claude decides

### Pool behavior
- Per-project pool limit: each project gets its own 3-container semaphore (not a shared global pool)
- Pool registry pattern: a PoolRegistry class manages per-project L3ContainerPool instances, creating on first spawn
- Per-project limit is 3 containers each

### Claude's Discretion: global hard cap
- Whether to add a global ceiling on total containers across all projects (e.g. max 9) in addition to per-project limits — Claude determines if worth the complexity

### Claude's Discretion: cleanup scope
- Whether container cleanup on shutdown/timeout covers all openclaw containers or only the active project's — Claude picks the safest approach for multi-project

</decisions>

<specifics>
## Specific Ideas

- The existing PumplAI project should work identically after this phase — backward compatibility with single-project setups is essential
- Monitor color-coding per project should be visually distinct in standard terminals (not just 256-color)

</specifics>

<deferred>
## Deferred Ideas

- Per-project pool isolation mode (`l3_pool: "shared"|"isolated"` in project.json) — tracked as POOL-01/02/03 for v1.2
- Per-project Docker networks — explicitly out of scope per REQUIREMENTS.md

</deferred>

---

*Phase: 13-multi-project-runtime*
*Context gathered: 2026-02-23*
