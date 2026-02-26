# Phase 46: Schema Validation + Fail-Fast Startup - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a documented, machine-validated schema to `openclaw.json` and `project.json`. OpenClaw refuses to start if `openclaw.json` is malformed or missing required fields — exiting before doing any work, with a clear actionable error. Env var precedence, migration tooling, and test coverage are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Error message format
- Missing required field → contextual error with hint: names the field, names the file, and suggests the expected value/example. e.g. `ERROR: config/openclaw.json is missing required field 'gateway.port'. Add it: "port": 18789`
- Unknown field → warning, continue startup. e.g. `WARNING: openclaw.json contains unknown field 'gatewayy'`
- Errors and warnings go to stderr only — pre-startup, before logging is configured
- ANSI color: red `ERROR`, yellow `WARNING` when stdout is a TTY; auto-detect TTY, strip color when piped/redirected

### Validation scope
- Validate in the central config loader (config.py) when the config is first loaded — all entry points automatically get validation for free, no per-command duplication
- Dashboard gets validation indirectly via the Python API; if the API returns an error, the dashboard surfaces it — dashboard does not validate independently
- `openclaw.json` is validated eagerly at startup; missing required field = exit immediately, no fall-back to defaults
- `project.json` is validated lazily when that project is first accessed/switched to — bad project configs fail on use, not at startup

### Schema implementation
- Schema defined as Python dict/dataclass in `config.py` alongside existing constants — single source of truth, no extra files
- `jsonschema>=4.26.0` used for validation (already flagged as the only new v1.5 dependency)
- Validate types on required fields (int, str, list), not just presence — wrong type is as bad as missing field
- Human-readable schema docs: inline comments in `config/openclaw.json.example`, explaining each field's type, default, and required/optional status

### Required vs optional fields
- `openclaw.json` required (missing = exit): `gateway.port` (int) and `agents` (list) — everything else has sensible defaults
- `project.json` required fields: **Claude's discretion** — review actual project.json files and determine what's operationally necessary at load time
- Error hints include an expected value/example for required fields
- New `openclaw config show` CLI command: prints the resolved effective config (file values merged with defaults) for operator auditing

### Claude's Discretion
- Exact Python structure for schema definition (typed dict, dataclass, plain dict, or JSON Schema dict)
- `project.json` required fields determination (review real files)
- TTY detection implementation details
- Exact shape of `openclaw config show` output (table vs JSON vs pretty-printed dict)
- Where in the startup call path `validate()` is called within `config.py`

</decisions>

<specifics>
## Specific Ideas

- The `openclaw config show` command was explicitly requested — it should show the *effective* config (file + defaults merged), not just the raw file content
- `jsonschema>=4.26.0` was already identified as the only new pip dependency for v1.5 — confirm it's added to `packages/orchestration/pyproject.toml`

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-schema-validation-fail-fast-startup*
*Context gathered: 2026-02-25*
