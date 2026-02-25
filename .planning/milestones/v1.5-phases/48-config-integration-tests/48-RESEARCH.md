# Phase 48: Config Integration Tests - Research

**Researched:** 2026-02-25
**Domain:** pytest integration testing — OpenClaw config layer (path resolution, schema validation, env var precedence, pool config fallback)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Test isolation strategy
- Use `monkeypatch` to set `OPENCLAW_ROOT` to a `tmp_path` directory for path resolution tests
- Schema validation tests write real config files to `tmp_path` (tests the full file-read + validate path, not just validation logic in isolation)
- Rely on `monkeypatch` auto-cleanup for env var teardown — no manual teardown blocks
- All test configs are fully synthetic — no real `config/openclaw.json` or `projects/*.json` are ever read or modified

#### Test file structure
- Single file: `packages/orchestration/tests/test_config_integration.py`
- Tests grouped by pytest class per area: `TestPathResolution`, `TestSchemaValidation`, `TestEnvPrecedence`, `TestPoolConfigFallback`
- File marked as `@pytest.mark.integration` to allow exclusion from fast unit test runs

#### Test depth and parametrization
- One happy path + one failure/absence case per success criterion — no exhaustive edge cases
- Schema validation: parametrize over all required fields (each missing field tested individually)
- Env var precedence: parametrize over all 4 env vars (each one tested individually to prove complete coverage)
- Pool config fallback: one test with pool config present (returns configured values), one test with pool config absent (returns defaults from config.py)

#### Fixture design
- Shared `valid_openclaw_config` pytest fixture returns a Python dict matching the full openclaw.json schema — tests copy and modify it
- File-writing fixtures use function-level scope (fresh `tmp_path` per test, no cross-test contamination)
- Shared fixtures added to the existing `conftest.py` at `packages/orchestration/tests/` (or created there if it doesn't exist yet)

### Claude's Discretion
- Exact set of required fields to parametrize over (determine from schema defined in phase 46)
- Names of the 4 env vars covered by precedence tests (determine from phase 47 implementation)
- Whether an existing `conftest.py` needs a config-specific fixture section or already has a structure to follow

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-07 | Config integration tests cover path resolution (state/snapshot paths), env var precedence, fail-fast validation, and pool config fallback — and run with `uv run pytest` | Full: existing test infrastructure (214 tests, pytest 9.0.2, monkeypatch, tmp_path, parametrize) supports all four test areas; specific functions/classes to test are all identified below |
</phase_requirements>

---

## Summary

Phase 48 is a pure test-writing phase. The implementation under test (phases 45–47) is fully shipped: `config.py` exports `get_state_path()`, `get_snapshot_dir()`, `get_active_project_env()`, `_find_project_root()`, and all DEFAULT_POOL_* constants; `config_validator.py` exports `validate_openclaw_config()` and `validate_project_config_schema()`/`ConfigValidationError`; `project_config.py` exports `get_pool_config()`, `get_active_project_id()`, and `load_and_validate_openclaw_config()`. The four env vars are `OPENCLAW_ROOT`, `OPENCLAW_PROJECT`, `OPENCLAW_LOG_LEVEL`, and `OPENCLAW_ACTIVITY_LOG_MAX`.

The existing test suite already has 214 passing tests in 3.12 seconds (pytest 9.0.2, Python 3.13.10). A `conftest.py` exists at `packages/orchestration/tests/conftest.py` — it adds sys.path entries for skills/spawn and docker/memory, but has no config-specific fixtures yet. The existing `test_config_validator.py` covers unit-level schema validation (calling validators in isolation). Phase 48 adds `test_config_integration.py` which covers the full call paths: path resolution via real `tmp_path` directories, schema validation via real file reads, env var precedence via real `os.environ` manipulation, and pool config fallback by constructing real `project.json` files.

**Primary recommendation:** Write `test_config_integration.py` with four pytest classes, a `valid_openclaw_config` fixture in `conftest.py`, and use `monkeypatch` + `tmp_path` throughout. No new dependencies required.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 (installed) | Test runner, fixtures, parametrize, monkeypatch, tmp_path | Already in use across 214 tests; required by pyproject.toml dev deps |
| pytest.monkeypatch | built-in fixture | Env var injection + auto-cleanup | `monkeypatch.setenv` / `monkeypatch.delenv` auto-restore on teardown — no manual teardown needed |
| pytest.tmp_path | built-in fixture | Per-test temporary directories | Function-scoped by default; each test gets a fresh isolated dir |
| pytest.mark.parametrize | built-in decorator | Multi-case coverage with one test function | Used for required-field enumeration and 4-env-var coverage |
| jsonschema | 4.26.0 (installed) | Schema validation (used by config_validator.py) | Already in pyproject.toml dependencies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| importlib.reload | stdlib | Force re-evaluation of module-level code after env var change | Only needed for `OPENCLAW_LOG_LEVEL` and `OPENCLAW_ACTIVITY_LOG_MAX` — both are read at import time in config.py as `os.environ.get(...)` defaults |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| monkeypatch + tmp_path | unittest.mock.patch + tempfile.mkdtemp | pytest builtins are idiomatic here; monkeypatch auto-cleans, tmp_path is function-scoped automatically |

**Installation:**
```bash
# No new dependencies — all already installed
uv run pytest packages/orchestration/tests/test_config_integration.py -v
```

---

## Architecture Patterns

### Recommended Project Structure
```
packages/orchestration/tests/
├── conftest.py                    # Add valid_openclaw_config fixture here
├── test_config_integration.py     # New file — Phase 48 target
└── test_config_validator.py       # Existing unit tests (do not modify)
```

### Pattern 1: OPENCLAW_ROOT-Isolated Path Resolution Test
**What:** monkeypatch sets `OPENCLAW_ROOT` to `tmp_path`; test calls `get_state_path(project_id)` and asserts the returned path is under `tmp_path`.
**When to use:** `TestPathResolution` — tests for `get_state_path()` and `get_snapshot_dir()`.

**Key insight:** `get_state_path()` reads `os.environ.get("OPENCLAW_ROOT")` at call time via `_find_project_root()`. No module reload needed — the function is not module-level. Same for `get_snapshot_dir()`.

**Exception:** `OPENCLAW_STATE_FILE` takes priority over `OPENCLAW_ROOT` in `get_state_path()`. Tests must monkeypatch `OPENCLAW_STATE_FILE` absent (delenv) before setting `OPENCLAW_ROOT` to avoid interference.

```python
# Source: config.py — verified from codebase
def test_state_path_under_openclaw_root(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
    from openclaw.config import get_state_path
    result = get_state_path("myproject")
    assert str(tmp_path) in str(result)
    assert "myproject" in str(result)
    assert result.name == "workspace-state.json"

def test_snapshot_dir_under_openclaw_root(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
    from openclaw.config import get_snapshot_dir
    result = get_snapshot_dir("myproject")
    assert str(tmp_path) in str(result)
    assert "myproject" in str(result)
    assert result.name == "snapshots"
```

### Pattern 2: Full File-Read Schema Validation Test
**What:** Write a synthetic config file to `tmp_path`, then call `load_and_validate_openclaw_config()` (which does actual file I/O + validation). Tests the full integrated path, not just the validator function in isolation.
**When to use:** `TestSchemaValidation` — tests for fail-fast validation triggered on missing required fields.

**Key challenge:** `load_and_validate_openclaw_config()` calls `_emit_validation_results()` which calls `sys.exit(1)` on fatal errors. The test cannot just call `load_and_validate_openclaw_config()` directly for the failure case. Two approaches:

1. **Recommended (per CONTEXT.md):** Call `validate_openclaw_config()` directly with a config dict read from the file — this is what the "full file-read + validate path" means. The test writes the file, reads it back with `json.load()`, then passes the dict to the validator and asserts on `(fatal, warnings)`.

2. **Alternative:** Use `pytest.raises(SystemExit)` and intercept `sys.exit(1)` — but this is fragile.

The CONTEXT.md says "write real config files to `tmp_path` (tests the full file-read + validate path)". The cleanest interpretation is: write file → open + json.load → validate. This tests that the config format survives a real file round-trip.

```python
# Pattern: write file, read back, validate
import json

def test_valid_config_from_file_passes(tmp_path, valid_openclaw_config):
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(json.dumps(valid_openclaw_config))
    with open(config_file) as f:
        config = json.load(f)
    from openclaw.config_validator import validate_openclaw_config
    fatal, warnings = validate_openclaw_config(config, str(config_file))
    assert fatal == []
    assert warnings == []

@pytest.mark.parametrize("missing_field", ["gateway", "agents"])
def test_missing_top_level_required_field_is_fatal(tmp_path, valid_openclaw_config, missing_field):
    config = {k: v for k, v in valid_openclaw_config.items() if k != missing_field}
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(json.dumps(config))
    with open(config_file) as f:
        loaded = json.load(f)
    from openclaw.config_validator import validate_openclaw_config
    fatal, _ = validate_openclaw_config(loaded, str(config_file))
    assert len(fatal) >= 1
    assert missing_field in " ".join(fatal).lower()
```

### Pattern 3: Env Var Precedence Test (Function-Level Reads)
**What:** `OPENCLAW_ROOT` and `OPENCLAW_PROJECT` are read at call time — no module reload needed. `OPENCLAW_LOG_LEVEL` and `OPENCLAW_ACTIVITY_LOG_MAX` are read at import time into module-level constants — module reload IS required.
**When to use:** `TestEnvPrecedence` — proves each of the 4 env vars overrides its config-file default.

**Confirmed from config.py source:**
- `LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()` — module-level, requires `importlib.reload(openclaw.config)` to observe change
- `ACTIVITY_LOG_MAX_ENTRIES = int(os.environ.get("OPENCLAW_ACTIVITY_LOG_MAX", "100"))` — same
- `get_active_project_env()` reads `os.environ.get("OPENCLAW_PROJECT")` at call time — no reload
- `_find_project_root()` reads `os.environ.get("OPENCLAW_ROOT")` at call time — no reload

For `OPENCLAW_LOG_LEVEL` and `OPENCLAW_ACTIVITY_LOG_MAX` tests that use `importlib.reload`, use the try/finally pattern established in the existing `test_get_active_project_id_uses_env_var` test.

```python
# OPENCLAW_ROOT — no reload needed
def test_openclaw_root_env_overrides_home(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
    from openclaw.config import get_project_root
    assert get_project_root() == tmp_path

# OPENCLAW_PROJECT — no reload needed
def test_openclaw_project_env_overrides_config(monkeypatch):
    monkeypatch.setenv("OPENCLAW_PROJECT", "env_project")
    from openclaw.config import get_active_project_env
    assert get_active_project_env() == "env_project"

# OPENCLAW_LOG_LEVEL — requires reload
def test_openclaw_log_level_env_sets_constant(monkeypatch):
    import importlib
    monkeypatch.setenv("OPENCLAW_LOG_LEVEL", "DEBUG")
    import openclaw.config as cfg
    try:
        importlib.reload(cfg)
        assert cfg.LOG_LEVEL == "DEBUG"
    finally:
        importlib.reload(cfg)

# OPENCLAW_ACTIVITY_LOG_MAX — requires reload
def test_openclaw_activity_log_max_env_sets_constant(monkeypatch):
    import importlib
    monkeypatch.setenv("OPENCLAW_ACTIVITY_LOG_MAX", "42")
    import openclaw.config as cfg
    try:
        importlib.reload(cfg)
        assert cfg.ACTIVITY_LOG_MAX_ENTRIES == 42
    finally:
        importlib.reload(cfg)
```

### Pattern 4: Pool Config Fallback via Real project.json
**What:** Write a `project.json` under `tmp_path/projects/<id>/` (matching the real directory structure), set `OPENCLAW_ROOT` to `tmp_path`, call `get_pool_config(project_id)`.
**When to use:** `TestPoolConfigFallback`

**Required directory structure** (from `project_config.py` line 129: `root / "projects" / project_id / "project.json"`):
```
tmp_path/
├── openclaw.json          ← required by get_project_root / load_and_validate_openclaw_config
└── projects/
    └── testproject/
        └── project.json   ← has or lacks l3_overrides
```

**Both `openclaw.json` AND `project.json` must be present** in `tmp_path` because `get_pool_config()` calls `load_project_config()` which calls `get_project_root()` (reads `OPENCLAW_ROOT`) and loads `projects/<id>/project.json`. The test must also ensure the root `openclaw.json` is valid (otherwise `load_and_validate_openclaw_config()` called by `get_active_project_id()` will fail).

Actually, `get_pool_config(project_id)` accepts an explicit `project_id` — it passes it to `load_project_config(project_id)` directly, which does NOT call `get_active_project_id()`. So only `project.json` and `OPENCLAW_ROOT` are needed — no `openclaw.json` required if project_id is passed explicitly.

```python
def test_pool_config_returns_configured_values(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
    project_dir = tmp_path / "projects" / "testproject"
    project_dir.mkdir(parents=True)
    project_json = {
        "workspace": "/tmp/test",
        "tech_stack": {"primary": "python"},
        "l3_overrides": {"max_concurrent": 5, "pool_mode": "isolated"},
    }
    (project_dir / "project.json").write_text(json.dumps(project_json))
    from openclaw.project_config import get_pool_config
    result = get_pool_config("testproject")
    assert result["max_concurrent"] == 5
    assert result["pool_mode"] == "isolated"

def test_pool_config_returns_defaults_when_no_l3_overrides(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
    project_dir = tmp_path / "projects" / "testproject"
    project_dir.mkdir(parents=True)
    project_json = {
        "workspace": "/tmp/test",
        "tech_stack": {"primary": "python"},
        # No l3_overrides
    }
    (project_dir / "project.json").write_text(json.dumps(project_json))
    from openclaw.project_config import get_pool_config
    from openclaw.config import (
        DEFAULT_POOL_MAX_CONCURRENT,
        DEFAULT_POOL_MODE,
        DEFAULT_POOL_OVERFLOW_POLICY,
        DEFAULT_POOL_QUEUE_TIMEOUT_S,
        DEFAULT_POOL_RECOVERY_POLICY,
    )
    result = get_pool_config("testproject")
    assert result["max_concurrent"] == DEFAULT_POOL_MAX_CONCURRENT
    assert result["pool_mode"] == DEFAULT_POOL_MODE
    assert result["overflow_policy"] == DEFAULT_POOL_OVERFLOW_POLICY
    assert result["queue_timeout_s"] == DEFAULT_POOL_QUEUE_TIMEOUT_S
    assert result["recovery_policy"] == DEFAULT_POOL_RECOVERY_POLICY
```

### Pattern 5: `valid_openclaw_config` Fixture
**What:** Shared fixture in `conftest.py` returning a minimal valid `openclaw.json` dict. Schema requires `gateway.port` (int) and `agents.list` (array).

```python
# Add to packages/orchestration/tests/conftest.py
import pytest

@pytest.fixture
def valid_openclaw_config():
    """Minimal valid openclaw.json dict — tests copy and modify it."""
    return {
        "gateway": {"port": 18789},
        "agents": {"list": []},
    }
```

### Anti-Patterns to Avoid
- **Calling `load_and_validate_openclaw_config()` for failure cases:** It calls `sys.exit(1)` on fatal errors. Test `validate_openclaw_config()` directly for failure cases; only use the full load function for the happy path.
- **Forgetting OPENCLAW_STATE_FILE interference:** `get_state_path()` checks `OPENCLAW_STATE_FILE` first. Always `monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)` before testing `OPENCLAW_ROOT` path derivation.
- **Module reload without finally:** `importlib.reload()` for LOG_LEVEL/ACTIVITY_LOG_MAX tests must always restore in a `finally` block to avoid cross-test contamination.
- **Missing `openclaw.json` in tmp_path for active-project lookups:** Only matters when calling functions that resolve the active project; calling `get_pool_config(project_id)` with explicit ID bypasses this.
- **Using class-scoped tmp_path:** `tmp_path` is function-scoped by default in pytest — keep it that way. Do not use `tmp_path_factory` for class-scoped sharing; it creates cross-test contamination risk.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var isolation | Manual os.environ save/restore | `monkeypatch.setenv` / `monkeypatch.delenv` | Auto-cleanup on teardown; no try/finally needed for env vars |
| Temporary directories | `tempfile.mkdtemp()` + manual cleanup | `tmp_path` fixture | Function-scoped, auto-cleaned, receives fresh Path each test |
| Multi-field coverage | Separate test functions per field | `@pytest.mark.parametrize` | Single test body, one assertion per parametrized case, scales cleanly |

**Key insight:** pytest's built-in fixtures (monkeypatch, tmp_path, parametrize) cover all test isolation needs here. No external test utilities needed.

---

## Common Pitfalls

### Pitfall 1: Module-Level Constant Staleness
**What goes wrong:** `LOG_LEVEL` and `ACTIVITY_LOG_MAX_ENTRIES` in `config.py` are set at import time. Setting `OPENCLAW_LOG_LEVEL` via `monkeypatch.setenv` after the module is imported has no effect on the constants until the module is reloaded.
**Why it happens:** Python evaluates `os.environ.get(...)` once at import time and stores the result in the module-level variable.
**How to avoid:** Use `importlib.reload(openclaw.config)` inside a try/finally. The existing test `test_get_active_project_id_uses_env_var` shows this pattern for `OPENCLAW_ROOT`.
**Warning signs:** Test passes in isolation but fails when run after other tests that already imported config.

### Pitfall 2: OPENCLAW_STATE_FILE Shadowing OPENCLAW_ROOT
**What goes wrong:** `get_state_path()` checks `OPENCLAW_STATE_FILE` first. If the test environment has `OPENCLAW_STATE_FILE` set (e.g., from a previous test or shell env), the `OPENCLAW_ROOT`-derived path is never used.
**Why it happens:** Priority order: `OPENCLAW_STATE_FILE` > derived path from `OPENCLAW_ROOT`.
**How to avoid:** Always `monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)` at the top of path-resolution tests.
**Warning signs:** `get_state_path()` returns a path that doesn't contain `tmp_path`.

### Pitfall 3: Missing Directory Structure for Pool Config Tests
**What goes wrong:** `load_project_config("testproject")` looks for `<root>/projects/testproject/project.json`. If the directory doesn't exist, the test raises `FileNotFoundError` rather than testing pool fallback.
**Why it happens:** The function is file-based; it requires the directory structure to match what `get_project_root()` returns.
**How to avoid:** Always call `project_dir.mkdir(parents=True)` before writing `project.json` in pool config tests.

### Pitfall 4: `@pytest.mark.integration` Unregistered
**What goes wrong:** pytest emits `PytestUnknownMarkWarning` if `integration` is not in the registered marks.
**Why it happens:** pytest 9.x warns on unrecognised marks.
**How to avoid:** Add `integration` to `[tool.pytest.ini_options] markers` in root `pyproject.toml`, or add `--strict-marks` only if you want it to error. Current pyproject.toml has no `markers` list — add it.

```toml
# In /home/ollie/.openclaw/pyproject.toml
[tool.pytest.ini_options]
testpaths = ["packages/orchestration/tests"]
asyncio_mode = "auto"
markers = [
    "integration: integration tests that touch the filesystem",
]
```

---

## Code Examples

### conftest.py Addition
```python
# Source: design from CONTEXT.md decisions
import pytest

@pytest.fixture
def valid_openclaw_config():
    """Minimal valid openclaw.json dict. Tests copy and modify."""
    return {
        "gateway": {"port": 18789},
        "agents": {"list": []},
    }
```

### TestPathResolution Skeleton
```python
# Source: config.py get_state_path / get_snapshot_dir verified behavior
import pytest

class TestPathResolution:
    """CONF-01: get_state_path() and get_snapshot_dir() return correct paths."""

    def test_state_path_under_openclaw_root(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        from openclaw.config import get_state_path
        result = get_state_path("myproject")
        assert str(tmp_path) in str(result)
        assert "myproject" in str(result)
        assert result.name == "workspace-state.json"

    def test_state_path_env_var_takes_priority(self, monkeypatch, tmp_path):
        override = str(tmp_path / "custom-state.json")
        monkeypatch.setenv("OPENCLAW_STATE_FILE", override)
        from openclaw.config import get_state_path
        result = get_state_path("myproject")
        assert str(result) == override

    def test_snapshot_dir_under_openclaw_root(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        from openclaw.config import get_snapshot_dir
        result = get_snapshot_dir("myproject")
        assert str(tmp_path) in str(result)
        assert "myproject" in str(result)
        assert result.name == "snapshots"
```

### TestSchemaValidation Skeleton
```python
import json
import pytest

# Required top-level fields from OPENCLAW_JSON_SCHEMA: "gateway", "agents"
# Required nested: gateway.port (int), agents.list (array)
_TOP_LEVEL_REQUIRED = ["gateway", "agents"]

class TestSchemaValidation:
    """CONF-02, CONF-06: fail-fast validation via file read."""

    def test_valid_config_from_file_passes(self, tmp_path, valid_openclaw_config):
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(json.dumps(valid_openclaw_config))
        with open(config_file) as f:
            config = json.load(f)
        from openclaw.config_validator import validate_openclaw_config
        fatal, warnings = validate_openclaw_config(config, str(config_file))
        assert fatal == []
        assert warnings == []

    @pytest.mark.parametrize("missing_field", _TOP_LEVEL_REQUIRED)
    def test_missing_required_field_is_fatal(self, tmp_path, valid_openclaw_config, missing_field):
        config = {k: v for k, v in valid_openclaw_config.items() if k != missing_field}
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(json.dumps(config))
        with open(config_file) as f:
            loaded = json.load(f)
        from openclaw.config_validator import validate_openclaw_config
        fatal, _ = validate_openclaw_config(loaded, str(config_file))
        assert len(fatal) >= 1
        assert missing_field in " ".join(fatal).lower()

    def test_invalid_project_json_raises(self, tmp_path):
        """Missing workspace/tech_stack raises ConfigValidationError via file path."""
        config_file = tmp_path / "project.json"
        config_file.write_text(json.dumps({"name": "only_name"}))
        with open(config_file) as f:
            loaded = json.load(f)
        from openclaw.config_validator import validate_project_config_schema, ConfigValidationError
        with pytest.raises(ConfigValidationError):
            validate_project_config_schema(loaded, str(config_file))
```

### TestEnvPrecedence Skeleton
```python
import importlib
import pytest

# The 4 env vars from CONF-04 (config.py verified)
class TestEnvPrecedence:
    """CONF-04: Each env var overrides its config-file default."""

    def test_openclaw_root_overrides_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        from openclaw.config import get_project_root
        assert get_project_root() == tmp_path

    def test_openclaw_project_overrides_config(self, monkeypatch):
        monkeypatch.setenv("OPENCLAW_PROJECT", "env_project_id")
        from openclaw.config import get_active_project_env
        assert get_active_project_env() == "env_project_id"

    def test_openclaw_log_level_overrides_default(self, monkeypatch):
        monkeypatch.setenv("OPENCLAW_LOG_LEVEL", "DEBUG")
        import openclaw.config as cfg
        try:
            importlib.reload(cfg)
            assert cfg.LOG_LEVEL == "DEBUG"
        finally:
            importlib.reload(cfg)

    def test_openclaw_activity_log_max_overrides_default(self, monkeypatch):
        monkeypatch.setenv("OPENCLAW_ACTIVITY_LOG_MAX", "42")
        import openclaw.config as cfg
        try:
            importlib.reload(cfg)
            assert cfg.ACTIVITY_LOG_MAX_ENTRIES == 42
        finally:
            importlib.reload(cfg)
```

### TestPoolConfigFallback Skeleton
```python
import json
import pytest

class TestPoolConfigFallback:
    """CONF-05, CONF-07: Pool config returns configured values or defaults."""

    def _write_project(self, tmp_path, l3_overrides=None):
        project_dir = tmp_path / "projects" / "testproject"
        project_dir.mkdir(parents=True)
        manifest = {
            "workspace": str(tmp_path / "workspace"),
            "tech_stack": {"primary": "python"},
        }
        if l3_overrides is not None:
            manifest["l3_overrides"] = l3_overrides
        (project_dir / "project.json").write_text(json.dumps(manifest))

    def test_pool_config_uses_l3_overrides_when_present(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        self._write_project(tmp_path, l3_overrides={"max_concurrent": 5, "pool_mode": "isolated"})
        from openclaw.project_config import get_pool_config
        result = get_pool_config("testproject")
        assert result["max_concurrent"] == 5
        assert result["pool_mode"] == "isolated"

    def test_pool_config_returns_defaults_when_no_l3_overrides(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        self._write_project(tmp_path)  # No l3_overrides
        from openclaw.project_config import get_pool_config
        from openclaw.config import (
            DEFAULT_POOL_MAX_CONCURRENT, DEFAULT_POOL_MODE,
            DEFAULT_POOL_OVERFLOW_POLICY, DEFAULT_POOL_QUEUE_TIMEOUT_S,
            DEFAULT_POOL_RECOVERY_POLICY,
        )
        result = get_pool_config("testproject")
        assert result["max_concurrent"] == DEFAULT_POOL_MAX_CONCURRENT
        assert result["pool_mode"] == DEFAULT_POOL_MODE
        assert result["overflow_policy"] == DEFAULT_POOL_OVERFLOW_POLICY
        assert result["queue_timeout_s"] == DEFAULT_POOL_QUEUE_TIMEOUT_S
        assert result["recovery_policy"] == DEFAULT_POOL_RECOVERY_POLICY
```

---

## Implementation Reference

### What the 4 env vars govern (from config.py, verified)

| Env Var | Module-Level or Call-Time | What It Controls | Requires Reload? |
|---------|--------------------------|-----------------|-----------------|
| `OPENCLAW_ROOT` | Call-time (`_find_project_root()`) | Project root directory | No |
| `OPENCLAW_PROJECT` | Call-time (`get_active_project_env()`) | Active project ID | No |
| `OPENCLAW_LOG_LEVEL` | Module-level (`LOG_LEVEL = os.environ.get(...)`) | Log verbosity | Yes |
| `OPENCLAW_ACTIVITY_LOG_MAX` | Module-level (`ACTIVITY_LOG_MAX_ENTRIES = int(os.environ.get(...))`) | Activity log rotation | Yes |

### Required fields in OPENCLAW_JSON_SCHEMA (from config.py, verified)

Top-level required: `["gateway", "agents"]`

Nested required:
- `gateway.port` — integer, 1–65535
- `agents.list` — array

Additional unknown top-level fields: WARNING (not fatal)

### Required fields in PROJECT_JSON_SCHEMA (from config.py, verified)

Top-level required: `["workspace", "tech_stack"]`

- `workspace` — non-empty string
- `tech_stack` — object

### Pool config defaults (from config.py, verified)

```python
DEFAULT_POOL_MAX_CONCURRENT = 3
DEFAULT_POOL_MODE = "shared"
DEFAULT_POOL_OVERFLOW_POLICY = "wait"
DEFAULT_POOL_QUEUE_TIMEOUT_S = 300
DEFAULT_POOL_RECOVERY_POLICY = "mark_failed"
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `/home/ollie/.openclaw/pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/orchestration/tests/test_config_integration.py -v` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |
| Estimated runtime | ~4-5 seconds (214 existing pass in 3.12s; new file adds ~15 tests) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONF-07 | Path resolution: state path under correct OPENCLAW_ROOT | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestPathResolution -v` | ❌ Wave 0 gap |
| CONF-07 | Path resolution: OPENCLAW_STATE_FILE takes priority | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestPathResolution -v` | ❌ Wave 0 gap |
| CONF-07 | Path resolution: snapshot dir under correct OPENCLAW_ROOT | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestPathResolution -v` | ❌ Wave 0 gap |
| CONF-07 | Fail-fast: valid config from file passes | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestSchemaValidation -v` | ❌ Wave 0 gap |
| CONF-07 | Fail-fast: missing required top-level fields produce fatal errors | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestSchemaValidation -v` | ❌ Wave 0 gap |
| CONF-07 | Fail-fast: invalid project.json raises ConfigValidationError | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestSchemaValidation -v` | ❌ Wave 0 gap |
| CONF-07 | Env precedence: OPENCLAW_ROOT overrides ~/.openclaw | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestEnvPrecedence -v` | ❌ Wave 0 gap |
| CONF-07 | Env precedence: OPENCLAW_PROJECT overrides active_project | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestEnvPrecedence -v` | ❌ Wave 0 gap |
| CONF-07 | Env precedence: OPENCLAW_LOG_LEVEL overrides INFO default | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestEnvPrecedence -v` | ❌ Wave 0 gap |
| CONF-07 | Env precedence: OPENCLAW_ACTIVITY_LOG_MAX overrides 100 default | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestEnvPrecedence -v` | ❌ Wave 0 gap |
| CONF-07 | Pool fallback: configured l3_overrides respected | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestPoolConfigFallback -v` | ❌ Wave 0 gap |
| CONF-07 | Pool fallback: absent l3_overrides returns config.py defaults | integration | `uv run pytest packages/orchestration/tests/test_config_integration.py::TestPoolConfigFallback -v` | ❌ Wave 0 gap |

### Nyquist Sampling Rate
- **Minimum sample interval:** After every committed task → run: `uv run pytest packages/orchestration/tests/test_config_integration.py -v`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green (`uv run pytest`) before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~2-3 seconds (new file only)

### Wave 0 Gaps (must be created before implementation)
- [ ] `packages/orchestration/tests/test_config_integration.py` — the entire CONF-07 test file (does not exist yet)
- [ ] Add `valid_openclaw_config` fixture to `packages/orchestration/tests/conftest.py`
- [ ] Add `integration` marker to `[tool.pytest.ini_options]` in `/home/ollie/.openclaw/pyproject.toml`

---

## Open Questions

1. **`@pytest.mark.integration` on class vs module**
   - What we know: CONTEXT.md says "File marked as `@pytest.mark.integration`"
   - What's unclear: Whether to mark the class, each test method, or use `pytestmark = [pytest.mark.integration]` at module level
   - Recommendation: Use `pytestmark = [pytest.mark.integration]` at module level — marks all tests in the file without per-test decoration

2. **Whether to test `get_active_project_id()` from project.json fallback**
   - What we know: CONTEXT.md success criteria require env var precedence to be tested; existing `test_config_validator.py` already has `test_get_active_project_id_uses_env_var`
   - What's unclear: Whether `TestEnvPrecedence` should duplicate this existing test or focus only on the 4 module/function-level reads
   - Recommendation: Do not duplicate — the existing test covers `get_active_project_id()` env var precedence. `TestEnvPrecedence` should cover only the 4 env vars directly (OPENCLAW_ROOT, OPENCLAW_PROJECT, OPENCLAW_LOG_LEVEL, OPENCLAW_ACTIVITY_LOG_MAX).

---

## Sources

### Primary (HIGH confidence)
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/config.py` — verified: `get_state_path()`, `get_snapshot_dir()`, `get_project_root()`, `get_active_project_env()`, `LOG_LEVEL`, `ACTIVITY_LOG_MAX_ENTRIES`, `DEFAULT_POOL_*` constants, `OPENCLAW_JSON_SCHEMA`, `PROJECT_JSON_SCHEMA`
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/config_validator.py` — verified: `validate_openclaw_config()`, `validate_project_config_schema()`, `ConfigValidationError`
- `/home/ollie/.openclaw/packages/orchestration/src/openclaw/project_config.py` — verified: `get_pool_config()`, `load_project_config()`, `load_and_validate_openclaw_config()`, `_emit_validation_results()` (calls sys.exit)
- `/home/ollie/.openclaw/packages/orchestration/tests/conftest.py` — verified: structure, existing sys.path additions
- `/home/ollie/.openclaw/packages/orchestration/tests/test_config_validator.py` — verified: existing tests, patterns for monkeypatch + tmp_path + importlib.reload
- `/home/ollie/.openclaw/pyproject.toml` — verified: pytest config, testpaths, asyncio_mode
- `uv run pytest packages/orchestration/tests/ -v --tb=no -q` — confirmed 214 passing, 3.12s runtime, pytest 9.0.2

### Secondary (MEDIUM confidence)
- CONTEXT.md phase 48 decisions — locked decisions verified against source code

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in active use
- Architecture: HIGH — verified against actual source code of phases 45-47
- Pitfalls: HIGH — identified from direct source code inspection (sys.exit path, module-level constants, directory structure requirements)

**Research date:** 2026-02-25
**Valid until:** 2026-03-27 (stable — tests against stable implementation, 30-day window appropriate)
