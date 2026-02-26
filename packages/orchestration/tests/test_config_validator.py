"""
Tests for openclaw.json and project.json schema validation.

Covers CONF-02 (unknown field warning, valid config, schema importable)
and CONF-06 (missing required fields, wrong type, project.json required field).

These tests call validate_openclaw_config() and validate_project_config_schema()
directly — they do NOT invoke sys.exit() wrappers.
"""
import pytest
from openclaw.config_validator import validate_openclaw_config, validate_project_config_schema, ConfigValidationError
from openclaw.config import OPENCLAW_JSON_SCHEMA


_VALID_MINIMAL = {"gateway": {"port": 18789}, "agents": {"list": []}}


def test_schema_importable():
    """OPENCLAW_JSON_SCHEMA is defined in config.py and has the expected shape."""
    assert isinstance(OPENCLAW_JSON_SCHEMA, dict)
    assert "type" in OPENCLAW_JSON_SCHEMA
    assert "required" in OPENCLAW_JSON_SCHEMA
    assert "properties" in OPENCLAW_JSON_SCHEMA


def test_valid_config_passes():
    """A minimal valid config produces no fatal errors and no warnings."""
    fatal, warnings = validate_openclaw_config(_VALID_MINIMAL, "config/openclaw.json")
    assert fatal == [], f"Expected no fatal errors, got: {fatal}"
    assert warnings == [], f"Expected no warnings, got: {warnings}"


def test_unknown_field_is_warning():
    """An unknown top-level field produces a warning, not a fatal error."""
    config = {**_VALID_MINIMAL, "gatewayy": {}}
    fatal, warnings = validate_openclaw_config(config, "config/openclaw.json")
    assert fatal == [], f"Unknown field must not be fatal, got: {fatal}"
    assert len(warnings) >= 1
    assert any("gatewayy" in w for w in warnings), f"Warning must name the unknown field, got: {warnings}"


def test_missing_gateway_port_is_fatal():
    """Missing gateway.port produces a fatal error naming the field."""
    config = {"gateway": {}, "agents": {"list": []}}
    fatal, warnings = validate_openclaw_config(config, "config/openclaw.json")
    assert len(fatal) >= 1
    combined = " ".join(fatal)
    assert "gateway" in combined.lower() or "port" in combined.lower(), (
        f"Fatal error must mention 'gateway.port', got: {fatal}"
    )


def test_missing_agents_is_fatal():
    """Missing agents key produces a fatal error naming the field."""
    config = {"gateway": {"port": 18789}}
    fatal, warnings = validate_openclaw_config(config, "config/openclaw.json")
    assert len(fatal) >= 1
    combined = " ".join(fatal)
    assert "agents" in combined.lower(), f"Fatal error must mention 'agents', got: {fatal}"


def test_wrong_type_is_fatal():
    """gateway.port as a string instead of int produces a fatal error."""
    config = {"gateway": {"port": "18789"}, "agents": {"list": []}}
    fatal, warnings = validate_openclaw_config(config, "config/openclaw.json")
    assert len(fatal) >= 1
    combined = " ".join(fatal)
    assert "port" in combined.lower() or "integer" in combined.lower() or "int" in combined.lower(), (
        f"Fatal error must mention the type issue, got: {fatal}"
    )


def test_project_json_missing_required():
    """Empty project.json dict triggers error mentioning 'workspace'."""
    with pytest.raises(Exception):
        # validate_project_config_schema raises ConfigValidationError or similar
        # when required fields (workspace, tech_stack) are absent
        validate_project_config_schema({}, "projects/test/project.json")


# ── CONF-04: Env Var Routing ──────────────────────────────────────────────────

def test_get_active_project_env_returns_none_when_unset(monkeypatch):
    """get_active_project_env() returns None when OPENCLAW_PROJECT is not set."""
    monkeypatch.delenv("OPENCLAW_PROJECT", raising=False)
    from openclaw.config import get_active_project_env
    assert get_active_project_env() is None


def test_get_active_project_env_returns_value_when_set(monkeypatch):
    """get_active_project_env() returns the env var value when OPENCLAW_PROJECT is set."""
    monkeypatch.setenv("OPENCLAW_PROJECT", "testproject")
    from openclaw.config import get_active_project_env
    result = get_active_project_env()
    assert result == "testproject"


def test_get_active_project_id_uses_env_var(monkeypatch, tmp_path):
    """get_active_project_id() returns OPENCLAW_PROJECT env var over config file value.

    Uses tmp_path to create a minimal openclaw.json with active_project="from_config"
    but sets OPENCLAW_PROJECT="from_env" — the env var must win.
    """
    import json as _json
    from pathlib import Path

    # Write a minimal openclaw.json with active_project
    config_content = {
        "gateway": {"port": 18789},
        "agents": {"list": []},
        "active_project": "from_config",
    }
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(_json.dumps(config_content))

    monkeypatch.setenv("OPENCLAW_PROJECT", "from_env")
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

    # Force project_config to reload so it picks up OPENCLAW_ROOT
    import importlib
    import openclaw.config as _config_mod
    import openclaw.project_config as _pc_mod
    importlib.reload(_config_mod)
    importlib.reload(_pc_mod)

    try:
        from openclaw.project_config import get_active_project_id
        result = get_active_project_id()
        assert result == "from_env", f"Expected 'from_env' from env var, got: {result!r}"
    finally:
        # Restore: reload modules to original state
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)


# ── CONF-03: Migration CLI ────────────────────────────────────────────────────

def test_migration_up_to_date(tmp_path, capsys):
    """Migration reports 'Already up-to-date.' when config has no unknown fields."""
    import json as _json
    config = {"gateway": {"port": 18789}, "agents": {"list": []}}
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(_json.dumps(config))

    from openclaw.cli.config import _migrate_one_openclaw_json
    rc = _migrate_one_openclaw_json(config_file, dry_run=False)

    assert rc == 0
    captured = capsys.readouterr()
    assert "Already up-to-date" in captured.out


def test_migration_removes_unknown_field(tmp_path, capsys):
    """Migration removes unknown fields and creates a .bak file."""
    import json as _json
    config = {"gateway": {"port": 18789}, "agents": {"list": []}, "legacy_field": "remove_me"}
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(_json.dumps(config))

    from openclaw.cli.config import _migrate_one_openclaw_json
    rc = _migrate_one_openclaw_json(config_file, dry_run=False)

    assert rc == 0
    # Backup must exist
    bak_file = tmp_path / "openclaw.json.bak"
    assert bak_file.exists(), "Backup file must be created before writing"
    # Updated config must not contain the unknown field
    updated = _json.loads(config_file.read_text())
    assert "legacy_field" not in updated, "Unknown field must be removed"
    assert "gateway" in updated, "Known fields must be preserved"
    # Summary printed
    captured = capsys.readouterr()
    assert "legacy_field" in captured.out or "1 field" in captured.out


def test_migration_dry_run_does_not_write(tmp_path, capsys):
    """Migration dry-run prints changes but does not modify the file."""
    import json as _json
    config = {"gateway": {"port": 18789}, "agents": {"list": []}, "stale_key": "old_value"}
    config_file = tmp_path / "openclaw.json"
    original_text = _json.dumps(config)
    config_file.write_text(original_text)

    from openclaw.cli.config import _migrate_one_openclaw_json
    rc = _migrate_one_openclaw_json(config_file, dry_run=True)

    assert rc == 0
    # File unchanged
    assert config_file.read_text() == original_text, "Dry run must not modify the file"
    # No backup created
    bak_file = tmp_path / "openclaw.json.bak"
    assert not bak_file.exists(), "Dry run must not create a backup file"
    # Output mentions the field
    captured = capsys.readouterr()
    assert "stale_key" in captured.out


def test_migration_fatal_on_missing_required_fields(tmp_path, capsys):
    """Migration exits non-zero and prints guidance when required fields are missing."""
    import json as _json
    # Missing both 'gateway' and 'agents'
    config = {"only_field": "value"}
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(_json.dumps(config))

    from openclaw.cli.config import _migrate_one_openclaw_json
    rc = _migrate_one_openclaw_json(config_file, dry_run=False)

    assert rc != 0, "Must return non-zero when required fields are missing"
    # File unchanged — must not write a broken config
    updated = _json.loads(config_file.read_text())
    assert "only_field" in updated, "File must not be modified when fatal errors exist"


def test_migration_project_json_up_to_date(tmp_path, capsys):
    """Migration reports 'Already up-to-date.' for a valid project.json."""
    import json as _json
    config = {
        "id": "myproject",
        "name": "My Project",
        "workspace": "/home/user/projects/myproject",
        "tech_stack": {"primary": "python"},
    }
    config_file = tmp_path / "project.json"
    config_file.write_text(_json.dumps(config))

    from openclaw.cli.config import _migrate_one_project_json
    rc = _migrate_one_project_json(config_file, dry_run=False)

    assert rc == 0
    captured = capsys.readouterr()
    assert "Already up-to-date" in captured.out


def test_migration_project_json_removes_unknown_field(tmp_path, capsys):
    """Migration removes unknown fields from project.json and creates a .bak file."""
    import json as _json
    config = {
        "workspace": "/home/user/projects/myproject",
        "tech_stack": {"primary": "python"},
        "old_ci_config": "legacy",
    }
    config_file = tmp_path / "project.json"
    config_file.write_text(_json.dumps(config))

    from openclaw.cli.config import _migrate_one_project_json
    rc = _migrate_one_project_json(config_file, dry_run=False)

    assert rc == 0
    bak_file = tmp_path / "project.json.bak"
    assert bak_file.exists(), "Backup file must be created before writing"
    updated = _json.loads(config_file.read_text())
    assert "old_ci_config" not in updated, "Unknown field must be removed"
    assert "workspace" in updated, "Required fields must be preserved"
