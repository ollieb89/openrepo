# Phase 48: Config Integration Tests - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Write an automated pytest test suite covering the config layer implemented in phases 45–47: path resolution, schema validation, env var precedence, and pool config fallback. Tests give the operator confidence the config layer is correct and will stay correct. New config capabilities are out of scope — this phase only tests what phases 45–47 built.

</domain>

<decisions>
## Implementation Decisions

### Test isolation strategy
- Use `monkeypatch` to set `OPENCLAW_ROOT` to a `tmp_path` directory for path resolution tests
- Schema validation tests write real config files to `tmp_path` (tests the full file-read + validate path, not just validation logic in isolation)
- Rely on `monkeypatch` auto-cleanup for env var teardown — no manual teardown blocks
- All test configs are fully synthetic — no real `config/openclaw.json` or `projects/*.json` are ever read or modified

### Test file structure
- Single file: `packages/orchestration/tests/test_config_integration.py`
- Tests grouped by pytest class per area: `TestPathResolution`, `TestSchemaValidation`, `TestEnvPrecedence`, `TestPoolConfigFallback`
- File marked as `@pytest.mark.integration` to allow exclusion from fast unit test runs

### Test depth and parametrization
- One happy path + one failure/absence case per success criterion — no exhaustive edge cases
- Schema validation: parametrize over all required fields (each missing field tested individually)
- Env var precedence: parametrize over all 4 env vars (each one tested individually to prove complete coverage)
- Pool config fallback: one test with pool config present (returns configured values), one test with pool config absent (returns defaults from config.py)

### Fixture design
- Shared `valid_openclaw_config` pytest fixture returns a Python dict matching the full openclaw.json schema — tests copy and modify it
- File-writing fixtures use function-level scope (fresh `tmp_path` per test, no cross-test contamination)
- Shared fixtures added to the existing `conftest.py` at `packages/orchestration/tests/` (or created there if it doesn't exist yet)

### Claude's Discretion
- Exact set of required fields to parametrize over (determine from schema defined in phase 46)
- Names of the 4 env vars covered by precedence tests (determine from phase 47 implementation)
- Whether an existing `conftest.py` needs a config-specific fixture section or already has a structure to follow

</decisions>

<specifics>
## Specific Ideas

No specific references or examples beyond the success criteria — standard pytest patterns are fine.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 48-config-integration-tests*
*Context gathered: 2026-02-25*
