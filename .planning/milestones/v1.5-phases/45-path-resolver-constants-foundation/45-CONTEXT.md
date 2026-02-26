# Phase 45: Path Resolver + Constants Foundation - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Consolidate all divergent path resolvers into one authoritative function in `config.py`, and centralize all duplicated magic values (pool defaults, lock timeouts, cache TTL, log levels, memory budget cap) into `config.py` as the single source. No new capabilities — this is internal infrastructure cleanup.

</domain>

<decisions>
## Implementation Decisions

### Path resolver API design
- Functions live in `config.py` (not a new module)
- `get_state_path(project_id)` and `get_snapshot_dir(project_id)` require explicit project_id — no implicit active-project fallback
- Workspace is always derived from project config (project.json) — no optional workspace parameter
- Resolver checks `OPENCLAW_ROOT` env var first, falls back to default `~/.openclaw` — aligns Python with Docker entrypoint.sh
- Resolver checks `OPENCLAW_STATE_FILE` env var first, then derives from `OPENCLAW_ROOT` + project — aligns Python with container usage
- Context-aware: detects container environment (e.g., `/.dockerenv` or `OPENCLAW_ROOT=/openclaw`) and adjusts base path accordingly

### Constants organization
- Constants are defaults that get overridden at runtime — `config.py` has `DEFAULT_POOL_MAX = 3`, code reads `openclaw.json` and falls back to `config.py` default
- `MEMORY_CONTEXT_BUDGET` (currently hardcoded 2000 in spawn.py) moves to `config.py` in this phase

### Claude's Discretion
- Constants grouping style: flat module-level vars vs grouped dataclasses — pick what fits the volume of constants
- Naming convention: establish consistent scheme (e.g., subsystem-prefixed SCREAMING_SNAKE)
- Whether `_POOL_CONFIG_DEFAULTS` dict stays as a dict or breaks into individual constants — based on how it's consumed
- Path validation behavior: compute-only vs validate-and-raise — based on what callers need

### Migration strategy
- Hard swap, no deprecation — all 3 divergent resolvers (spawn.py `Path(__file__)`, monitor.py `_discover_projects`, project_config.py `_find_project_root`) replaced with the new one
- Batch all call site changes and test at end (not module-by-module)
- Both `pool.py` AND `project_config.py` import pool defaults from `config.py` — eliminates the `_POOL_CONFIG_DEFAULTS` duplication entirely

### Container path alignment
- spawn.py calls `get_state_path(project_id)` and injects the resolved path as `OPENCLAW_STATE_FILE` env var into L3 containers — containers read it directly instead of resolving themselves

</decisions>

<specifics>
## Specific Ideas

- Research flagged 3 divergent resolvers: spawn.py (Path(__file__).parent.parent.parent), monitor.py (_discover_projects), project_config.py (_find_project_root) — all must converge
- _POOL_CONFIG_DEFAULTS exists in both pool.py and project_config.py with identical values — both should import from config.py
- OPENCLAW_STATE_FILE env var is currently read by entrypoint.sh but ignored by Python — resolver must close this gap
- Success criterion: `grep` for pool defaults, lock timeouts, cache TTL, log levels, memory budget cap should only hit `config.py`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 45-path-resolver-constants-foundation*
*Context gathered: 2026-02-25*
