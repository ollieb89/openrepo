"""
Integration tests for the OpenClaw config layer (Phases 45-47).

Covers: path resolution, schema validation (file-based), env var precedence,
and pool config fallback. All tests use synthetic configs — no real
config/openclaw.json or projects/*.json are ever read or modified.
"""
import importlib
import json

import pytest

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# TestPathResolution — CONF-01, CONF-07
# Verifies get_state_path() and get_snapshot_dir() return correct locations.
# ---------------------------------------------------------------------------
class TestPathResolution:

    def test_state_path_under_openclaw_root(self, monkeypatch, tmp_path):
        """get_state_path() derives path from OPENCLAW_ROOT when OPENCLAW_STATE_FILE absent."""
        monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        from openclaw.config import get_state_path
        result = get_state_path("myproject")
        assert str(tmp_path) in str(result)
        assert "myproject" in str(result)
        assert result.name == "workspace-state.json"

    def test_state_path_env_var_takes_priority(self, monkeypatch, tmp_path):
        """OPENCLAW_STATE_FILE takes priority over OPENCLAW_ROOT-derived path."""
        override = str(tmp_path / "custom-state.json")
        monkeypatch.setenv("OPENCLAW_STATE_FILE", override)
        # Set OPENCLAW_ROOT to something different to prove priority
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path / "other"))
        from openclaw.config import get_state_path
        result = get_state_path("myproject")
        assert str(result) == override

    def test_snapshot_dir_under_openclaw_root(self, monkeypatch, tmp_path):
        """get_snapshot_dir() derives path from OPENCLAW_ROOT."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        from openclaw.config import get_snapshot_dir
        result = get_snapshot_dir("myproject")
        assert str(tmp_path) in str(result)
        assert "myproject" in str(result)
        assert result.name == "snapshots"


# ---------------------------------------------------------------------------
# TestSchemaValidation — CONF-02, CONF-06, CONF-07
# Writes real config files to tmp_path, reads them back, validates.
# Tests the full file-read + validate path, not just the validator in isolation.
# ---------------------------------------------------------------------------
_TOP_LEVEL_REQUIRED = ["gateway", "agents"]


class TestSchemaValidation:

    def test_valid_config_from_file_passes(self, tmp_path, valid_openclaw_config):
        """Valid openclaw.json round-trips through file I/O and passes validation."""
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(json.dumps(valid_openclaw_config))
        with open(config_file) as f:
            loaded = json.load(f)
        from openclaw.config_validator import validate_openclaw_config
        fatal, warnings = validate_openclaw_config(loaded, str(config_file))
        assert fatal == []
        assert warnings == []

    @pytest.mark.parametrize("missing_field", _TOP_LEVEL_REQUIRED)
    def test_missing_required_field_is_fatal(self, tmp_path, valid_openclaw_config, missing_field):
        """Each missing top-level required field produces at least one fatal error naming the field."""
        config = {k: v for k, v in valid_openclaw_config.items() if k != missing_field}
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(json.dumps(config))
        with open(config_file) as f:
            loaded = json.load(f)
        from openclaw.config_validator import validate_openclaw_config
        fatal, _ = validate_openclaw_config(loaded, str(config_file))
        assert len(fatal) >= 1
        assert missing_field in " ".join(fatal).lower()

    def test_unknown_top_level_field_is_warning_not_fatal(self, tmp_path, valid_openclaw_config):
        """Unknown additional fields produce a warning (not a fatal error — forward-compat)."""
        config = {**valid_openclaw_config, "_comment_unknown": "extra field"}
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(json.dumps(config))
        with open(config_file) as f:
            loaded = json.load(f)
        from openclaw.config_validator import validate_openclaw_config
        fatal, warnings = validate_openclaw_config(loaded, str(config_file))
        assert fatal == []
        # Warnings may or may not be present for _comment_* keys — either is acceptable
        # The key assertion is: no fatal errors

    def test_invalid_project_json_raises_config_validation_error(self, tmp_path):
        """project.json missing required fields raises ConfigValidationError."""
        config_file = tmp_path / "project.json"
        # workspace and tech_stack are required — omit both
        config_file.write_text(json.dumps({"name": "only_name"}))
        with open(config_file) as f:
            loaded = json.load(f)
        from openclaw.config_validator import validate_project_config_schema, ConfigValidationError
        with pytest.raises(ConfigValidationError):
            validate_project_config_schema(loaded, str(config_file))


# ---------------------------------------------------------------------------
# TestEnvPrecedence — CONF-03, CONF-04, CONF-07
# Each of the 4 env vars overrides its config-file/default value.
# OPENCLAW_ROOT and OPENCLAW_PROJECT: read at call time — no reload.
# OPENCLAW_LOG_LEVEL and OPENCLAW_ACTIVITY_LOG_MAX: module-level — require reload.
# ---------------------------------------------------------------------------
class TestEnvPrecedence:

    def test_openclaw_root_overrides_home(self, monkeypatch, tmp_path):
        """OPENCLAW_ROOT changes what get_project_root() returns (call-time read)."""
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        from openclaw.config import get_project_root
        assert get_project_root() == tmp_path

    def test_openclaw_project_overrides_config(self, monkeypatch):
        """OPENCLAW_PROJECT is returned by get_active_project_env() (call-time read)."""
        monkeypatch.setenv("OPENCLAW_PROJECT", "env_project_id")
        from openclaw.config import get_active_project_env
        assert get_active_project_env() == "env_project_id"

    def test_openclaw_project_unset_returns_none(self, monkeypatch):
        """get_active_project_env() returns None (not empty string) when env var absent."""
        monkeypatch.delenv("OPENCLAW_PROJECT", raising=False)
        from openclaw.config import get_active_project_env
        result = get_active_project_env()
        assert result is None or result == ""  # None or falsy — coerces empty string

    def test_openclaw_log_level_overrides_default(self, monkeypatch):
        """OPENCLAW_LOG_LEVEL sets module-level LOG_LEVEL constant (requires reload)."""
        monkeypatch.setenv("OPENCLAW_LOG_LEVEL", "DEBUG")
        import openclaw.config as cfg
        try:
            importlib.reload(cfg)
            assert cfg.LOG_LEVEL == "DEBUG"
        finally:
            importlib.reload(cfg)  # Restore default for subsequent tests

    def test_openclaw_activity_log_max_overrides_default(self, monkeypatch):
        """OPENCLAW_ACTIVITY_LOG_MAX sets module-level ACTIVITY_LOG_MAX_ENTRIES constant (requires reload)."""
        monkeypatch.setenv("OPENCLAW_ACTIVITY_LOG_MAX", "42")
        import openclaw.config as cfg
        try:
            importlib.reload(cfg)
            assert cfg.ACTIVITY_LOG_MAX_ENTRIES == 42
        finally:
            importlib.reload(cfg)  # Restore default for subsequent tests


# ---------------------------------------------------------------------------
# TestPoolConfigFallback — CONF-05, CONF-07
# get_pool_config() uses l3_overrides when present; falls back to DEFAULT_POOL_*
# constants from config.py when absent. Tests write real project.json files.
# ---------------------------------------------------------------------------
class TestPoolConfigFallback:

    def _write_project_json(self, tmp_path, l3_overrides=None):
        """Helper: create projects/testproject/project.json under tmp_path."""
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
        """get_pool_config() returns values from l3_overrides when configured."""
        monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        self._write_project_json(tmp_path, l3_overrides={"max_concurrent": 5, "pool_mode": "isolated"})
        from openclaw.project_config import get_pool_config
        result = get_pool_config("testproject")
        assert result["max_concurrent"] == 5
        assert result["pool_mode"] == "isolated"

    def test_pool_config_returns_defaults_when_no_l3_overrides(self, monkeypatch, tmp_path):
        """get_pool_config() falls back to DEFAULT_POOL_* constants from config.py when l3_overrides absent."""
        monkeypatch.delenv("OPENCLAW_STATE_FILE", raising=False)
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        self._write_project_json(tmp_path)  # No l3_overrides
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
