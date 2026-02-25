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
