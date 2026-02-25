# Phase 47: Env Var Precedence + Migration CLI - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Two deliverables for operators:
1. Env var resolution is uniform — `OPENCLAW_ROOT`, `OPENCLAW_PROJECT`, `OPENCLAW_LOG_LEVEL`, `OPENCLAW_ACTIVITY_LOG_MAX`, and `OPENCLAW_STATE_FILE` are consistently honoured by every Python component through `config.py` as the single authoritative resolver.
2. `openclaw config migrate` CLI command upgrades existing `openclaw.json` and all `project.json` files to the current schema, with dry-run preview and auto-backup.

Schema validation tests and deeper config integration coverage are Phase 48.

</domain>

<decisions>
## Implementation Decisions

### Migration CLI output format
- Claude decides format and verbosity for dry-run and applied-changes output (probably human-readable list of changes)
- When no changes needed: print "Already up-to-date" and exit 0
- After writing changes: Claude decides summary verbosity (probably "Migrated X: N changes applied. Backup saved to X.bak")

### Migration backup behaviour
- Auto-create `openclaw.json.bak` before any write (always, no flags required)
- Also backup each `project.json` before writing (e.g., `project.json.bak`)

### Migration trigger and detection
- Claude decides detection strategy (structural diff is likely cleanest given no prior schema version field)
- Minimum viable input: config must have at least the top-level structure (gateway object, agents array) — freeform JSON gets a clear rejection
- Unknown fields: removed during migration (config comes out valid per Phase 46 schema)
- Scope: migrates `openclaw.json` AND all `project.json` files found under `projects/`

### Env var resolution
- All callers route through `config.py` — one authoritative resolver, no direct `os.environ` reads scattered across components
- `OPENCLAW_STATE_FILE` gap fixed: Python `get_state_path()` must honour this env var (currently only entrypoint.sh reads it)
- `OPENCLAW_ROOT` pointing to a non-existent directory → auto-create with `mkdir -p`
- Override logging: Claude decides signal level (likely DEBUG — silent in normal operation, visible with verbose flag)

### Precedence documentation
- `openclaw.json.example` updated with inline comments on each overridable field (e.g., `// Override with OPENCLAW_LOG_LEVEL env var`)
- `config.py` gets a comment block near the resolver functions documenting the full precedence chain
- `openclaw config --help` includes a concise list of env vars with brief one-line descriptions (no full examples)

### Claude's Discretion
- Exact dry-run and post-migration output format and verbosity
- Whether env var override logging is DEBUG or a different level
- Migration detection strategy (structural diff vs version field vs combined)
- How the precedence comment block in config.py is structured

</decisions>

<specifics>
## Specific Ideas

- OPENCLAW_STATE_FILE is currently a gap: entrypoint.sh reads it but Python ignores it — Phase 47 closes this gap
- The migration tool should feel complete for operators: one command updates everything (openclaw.json + all project.json files)
- Auto-backup should be unconditional — no flag to skip it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 47-env-var-precedence-migration-cli*
*Context gathered: 2026-02-25*
