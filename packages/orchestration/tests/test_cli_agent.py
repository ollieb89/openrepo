"""Tests for openclaw agent CLI (openclaw-agent entry point)."""

import json
import pytest
from unittest.mock import MagicMock
from openclaw.cli.agent import main
from openclaw.agent_registry import AgentSpec, AgentLevel


def make_spec(id, name, level, reports_to=None, source="both"):
    return AgentSpec(id=id, name=name, level=AgentLevel(level), reports_to=reports_to, source=source)


@pytest.fixture
def mock_registry(monkeypatch):
    specs = [
        make_spec("clawdia_prime", "ClawdiaPrime", 1, source="both"),
        make_spec("pumplai_pm", "PumpLAI PM", 2, reports_to="clawdia_prime", source="agents_dir"),
        make_spec("l3_specialist", "L3 Specialist", 3, reports_to="pumplai_pm", source="openclaw_json"),
    ]
    registry = MagicMock()
    registry.all_agents.return_value = specs
    monkeypatch.setattr("openclaw.cli.agent.get_agent_registry", lambda: registry)
    return registry


@pytest.fixture
def empty_registry(monkeypatch):
    registry = MagicMock()
    registry.all_agents.return_value = []
    monkeypatch.setattr("openclaw.cli.agent.get_agent_registry", lambda: registry)
    return registry


# ---- Table output tests ----

def test_list_contains_all_agent_ids(mock_registry, capsys):
    """main(["list"]) stdout contains all agent IDs."""
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "clawdia_prime" in out
    assert "pumplai_pm" in out
    assert "l3_specialist" in out


def test_list_shows_level_headers(mock_registry, capsys):
    """main(["list"]) shows level group headers L1, L2, L3."""
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "L1" in out
    assert "L2" in out
    assert "L3" in out


def test_list_agents_dir_shows_new(mock_registry, capsys):
    """source='agents_dir' agent shows 'new' in Status column."""
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "new" in out


def test_list_openclaw_json_shows_orphan(mock_registry, capsys):
    """source='openclaw_json' agent shows 'orphan' in Status column."""
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "orphan" in out


def test_list_both_shows_ok(mock_registry, capsys):
    """source='both' agent shows 'ok' in Status column."""
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ok" in out


# ---- JSON output tests ----

def test_list_json_is_valid(mock_registry, capsys):
    """main(["list", "--json"]) outputs valid JSON array."""
    rc = main(["list", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)


def test_list_json_has_required_keys(mock_registry, capsys):
    """Each JSON object has required keys: id, name, level, reports_to, source."""
    rc = main(["list", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    for obj in data:
        assert "id" in obj
        assert "name" in obj
        assert "level" in obj
        assert "reports_to" in obj
        assert "source" in obj


def test_list_json_length_matches_registry(mock_registry, capsys):
    """JSON array length matches number of agents in mock registry."""
    rc = main(["list", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert len(data) == 3


# ---- Error/edge case tests ----

def test_no_subcommand_prints_help_exits_1(capsys):
    """main([]) prints help text and exits with code 1."""
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower() or "subcommand" in out.lower() or "list" in out.lower()


def test_empty_registry_prints_no_agents(empty_registry, capsys):
    """main(["list"]) with empty registry prints 'No agents found.' and exits 0."""
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "No agents found." in out
