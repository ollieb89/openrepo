"""Tests for enhanced AgentRegistry: drift detection, defaults inheritance, orphan handling."""

import json
import logging
import pytest
from pathlib import Path

from openclaw.agent_registry import AgentRegistry, AgentLevel, AgentSpec


# ── Test infrastructure ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def enable_registry_log_propagation():
    """Enable log propagation on the agent_registry logger so caplog can capture warnings.

    The get_logger() factory sets propagate=False by default (structured JSON mode).
    For tests we need the stdlib propagation chain so caplog works.
    """
    logger = logging.getLogger("openclaw.agent_registry")
    original = logger.propagate
    logger.propagate = True
    yield
    logger.propagate = original


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_agent_dir(tmp_path: Path, agent_id: str, config_data: dict) -> None:
    """Create agents/{agent_id}/agent/config.json with given data."""
    d = tmp_path / "agents" / agent_id / "agent"
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps(config_data))


def make_openclaw_json(
    tmp_path: Path,
    agents_list: list,
    defaults: dict | None = None,
) -> None:
    """Create openclaw.json with given agents list and optional defaults."""
    data: dict = {"gateway": {"port": 18789}, "agents": {"list": agents_list}}
    if defaults:
        data["agents"]["defaults"] = defaults
    (tmp_path / "openclaw.json").write_text(json.dumps(data))


# ── Orphan detection ─────────────────────────────────────────────────────────

def test_orphan_agent_registered_and_warns(tmp_path, caplog):
    """Agent in openclaw.json with no agents/ directory → registered + WARNING."""
    make_openclaw_json(tmp_path, [
        {"id": "orphan_agent", "name": "Orphan", "level": 2, "reports_to": None},
    ])
    # No agents/ directory at all

    with caplog.at_level(logging.WARNING, logger="openclaw.agent_registry"):
        registry = AgentRegistry(tmp_path)

    # Agent is still registered (from openclaw.json data)
    spec = registry.get("orphan_agent")
    assert spec is not None, "Orphan agent should be registered"
    assert spec.name == "Orphan"

    # WARNING log must contain "orphan", agent id, and scaffold hint
    warning_text = " ".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
    assert "orphan_agent" in warning_text
    assert "orphan" in warning_text.lower()
    assert "openclaw agent init" in warning_text


def test_orphan_scaffold_hint_includes_agent_id(tmp_path, caplog):
    """Scaffold hint in orphan WARNING includes the agent id for copy-paste."""
    make_openclaw_json(tmp_path, [
        {"id": "my_bot", "name": "MyBot", "level": 3, "reports_to": None},
    ])

    with caplog.at_level(logging.WARNING, logger="openclaw.agent_registry"):
        AgentRegistry(tmp_path)

    warning_text = " ".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
    assert "my_bot" in warning_text
    # The hint should include the agent id so the user can run: openclaw agent init my_bot
    assert "init" in warning_text


# ── Identity field drift detection ───────────────────────────────────────────

def test_drift_name_mismatch_warns(tmp_path, caplog):
    """Name mismatch between openclaw.json and per-agent config → WARNING with field 'name'."""
    make_openclaw_json(tmp_path, [
        {"id": "alpha", "name": "Alpha Central", "level": 2, "reports_to": None},
    ])
    make_agent_dir(tmp_path, "alpha", {
        "id": "alpha",
        "name": "Alpha Override",  # different from openclaw.json
        "level": 2,
        "reports_to": None,
    })

    with caplog.at_level(logging.WARNING, logger="openclaw.agent_registry"):
        registry = AgentRegistry(tmp_path)

    # Per-agent wins
    spec = registry.get("alpha")
    assert spec is not None
    assert spec.name == "Alpha Override"

    # WARNING must name the field and agent
    warning_text = " ".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
    assert "alpha" in warning_text
    assert "name" in warning_text
    assert "openclaw agent sync" in warning_text


def test_drift_level_mismatch_warns(tmp_path, caplog):
    """Level mismatch between openclaw.json and per-agent config → WARNING naming 'level'."""
    make_openclaw_json(tmp_path, [
        {"id": "beta", "name": "Beta", "level": 2, "reports_to": None},
    ])
    make_agent_dir(tmp_path, "beta", {
        "id": "beta",
        "name": "Beta",
        "level": 3,  # different level
        "reports_to": None,
    })

    with caplog.at_level(logging.WARNING, logger="openclaw.agent_registry"):
        AgentRegistry(tmp_path)

    warning_text = " ".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
    assert "beta" in warning_text
    assert "level" in warning_text


def test_drift_reports_to_mismatch_warns(tmp_path, caplog):
    """reports_to mismatch between openclaw.json and per-agent config → WARNING naming 'reports_to'."""
    make_openclaw_json(tmp_path, [
        {"id": "gamma", "name": "Gamma", "level": 3, "reports_to": "alpha"},
    ])
    make_agent_dir(tmp_path, "gamma", {
        "id": "gamma",
        "name": "Gamma",
        "level": 3,
        "reports_to": "beta",  # different reports_to
    })

    with caplog.at_level(logging.WARNING, logger="openclaw.agent_registry"):
        AgentRegistry(tmp_path)

    warning_text = " ".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
    assert "gamma" in warning_text
    assert "reports_to" in warning_text


def test_no_drift_no_warning(tmp_path, caplog):
    """No mismatch → no WARNING emitted."""
    make_openclaw_json(tmp_path, [
        {"id": "delta", "name": "Delta", "level": 2, "reports_to": None},
    ])
    make_agent_dir(tmp_path, "delta", {
        "id": "delta",
        "name": "Delta",   # same as openclaw.json
        "level": 2,
        "reports_to": None,
    })

    with caplog.at_level(logging.WARNING, logger="openclaw.agent_registry"):
        AgentRegistry(tmp_path)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 0, f"Expected no warnings, got: {[r.message for r in warnings]}"


# ── Defaults inheritance ──────────────────────────────────────────────────────

def test_defaults_max_concurrent_applied_when_not_set(tmp_path):
    """agents.defaults.maxConcurrent applies when per-agent config has no max_concurrent."""
    make_openclaw_json(tmp_path, [
        {"id": "epsilon", "name": "Epsilon", "level": 2, "reports_to": None},
    ], defaults={"maxConcurrent": 4})
    make_agent_dir(tmp_path, "epsilon", {
        "id": "epsilon",
        "name": "Epsilon",
        "level": 2,
        "reports_to": None,
        # no max_concurrent
    })

    registry = AgentRegistry(tmp_path)
    spec = registry.get("epsilon")
    assert spec is not None
    assert spec.max_concurrent == 4


def test_defaults_max_concurrent_not_overriding_explicit(tmp_path):
    """Per-agent max_concurrent=2 wins over defaults maxConcurrent=4."""
    make_openclaw_json(tmp_path, [
        {"id": "zeta", "name": "Zeta", "level": 2, "reports_to": None},
    ], defaults={"maxConcurrent": 4})
    make_agent_dir(tmp_path, "zeta", {
        "id": "zeta",
        "name": "Zeta",
        "level": 2,
        "reports_to": None,
        "max_concurrent": 2,
    })

    registry = AgentRegistry(tmp_path)
    spec = registry.get("zeta")
    assert spec is not None
    assert spec.max_concurrent == 2


def test_defaults_model_applied_when_not_set(tmp_path):
    """agents.defaults.model.primary applies when per-agent has no model."""
    default_model = "google-gemini-cli/gemini-2.5-flash"
    make_openclaw_json(tmp_path, [
        {"id": "eta", "name": "Eta", "level": 2, "reports_to": None},
    ], defaults={"model": {"primary": default_model}})
    make_agent_dir(tmp_path, "eta", {
        "id": "eta",
        "name": "Eta",
        "level": 2,
        "reports_to": None,
        # no model
    })

    registry = AgentRegistry(tmp_path)
    spec = registry.get("eta")
    assert spec is not None
    assert spec.model == default_model


def test_defaults_model_not_overriding_explicit(tmp_path):
    """Per-agent model wins over defaults model."""
    make_openclaw_json(tmp_path, [
        {"id": "theta", "name": "Theta", "level": 2, "reports_to": None},
    ], defaults={"model": {"primary": "default-model/v1"}})
    make_agent_dir(tmp_path, "theta", {
        "id": "theta",
        "name": "Theta",
        "level": 2,
        "reports_to": None,
        "model": "custom-model/v2",
    })

    registry = AgentRegistry(tmp_path)
    spec = registry.get("theta")
    assert spec is not None
    assert spec.model == "custom-model/v2"


# ── Directory without config.json ─────────────────────────────────────────────

def test_dir_without_config_json_not_auto_registered(tmp_path):
    """agents/ directory without agents/{id}/agent/config.json is NOT auto-registered."""
    make_openclaw_json(tmp_path, [])
    # Create directory structure but no config.json
    agent_dir = tmp_path / "agents" / "no_config_agent" / "agent"
    agent_dir.mkdir(parents=True)
    # Note: no config.json written

    registry = AgentRegistry(tmp_path)
    spec = registry.get("no_config_agent")
    assert spec is None, "Agent without config.json should not be auto-registered"


def test_templates_dir_silently_skipped(tmp_path):
    """agents/_templates/ is silently skipped — no spec, no warning."""
    make_openclaw_json(tmp_path, [])
    # Create _templates directory with a config.json
    tpl_dir = tmp_path / "agents" / "_templates" / "agent"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "config.json").write_text(json.dumps({
        "id": "_templates",
        "name": "Template",
        "level": 3,
    }))

    registry = AgentRegistry(tmp_path)
    spec = registry.get("_templates")
    assert spec is None, "_templates directory should be silently skipped"


# ── ID mismatch drift ─────────────────────────────────────────────────────────

def test_id_mismatch_in_config_warns(tmp_path, caplog):
    """Per-agent config.json with id≠directory name → WARNING about id mismatch."""
    make_openclaw_json(tmp_path, [
        {"id": "iota", "name": "Iota", "level": 2, "reports_to": None},
    ])
    make_agent_dir(tmp_path, "iota", {
        "id": "wrong_id",  # does not match directory name "iota"
        "name": "Iota",
        "level": 2,
        "reports_to": None,
    })

    with caplog.at_level(logging.WARNING, logger="openclaw.agent_registry"):
        AgentRegistry(tmp_path)

    warning_text = " ".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
    assert "iota" in warning_text
    assert "wrong_id" in warning_text


# ── all_agents() method ───────────────────────────────────────────────────────

def test_all_agents_returns_all_specs(tmp_path):
    """all_agents() returns all registered AgentSpec objects."""
    make_openclaw_json(tmp_path, [
        {"id": "agent_a", "name": "Agent A", "level": 1, "reports_to": None},
        {"id": "agent_b", "name": "Agent B", "level": 2, "reports_to": "agent_a"},
    ])
    make_agent_dir(tmp_path, "agent_a", {"id": "agent_a", "name": "Agent A", "level": 1})
    make_agent_dir(tmp_path, "agent_b", {"id": "agent_b", "name": "Agent B", "level": 2})

    registry = AgentRegistry(tmp_path)
    all_agents = registry.all_agents()

    assert len(all_agents) == 2
    ids = {a.id for a in all_agents}
    assert "agent_a" in ids
    assert "agent_b" in ids


def test_all_agents_sorted_by_level_then_id(tmp_path):
    """all_agents() returns list sorted by level ascending then id alphabetically."""
    make_openclaw_json(tmp_path, [
        {"id": "z_agent", "name": "Z Agent", "level": 2, "reports_to": None},
        {"id": "a_agent", "name": "A Agent", "level": 2, "reports_to": None},
        {"id": "l1_agent", "name": "L1 Agent", "level": 1, "reports_to": None},
    ])

    registry = AgentRegistry(tmp_path)
    all_agents = registry.all_agents()

    assert len(all_agents) == 3
    assert all_agents[0].id == "l1_agent"   # level 1 first
    assert all_agents[1].id == "a_agent"    # level 2, 'a' before 'z'
    assert all_agents[2].id == "z_agent"


def test_all_agents_empty_registry(tmp_path):
    """all_agents() returns empty list when no agents registered."""
    make_openclaw_json(tmp_path, [])

    registry = AgentRegistry(tmp_path)
    assert registry.all_agents() == []


# ── Source tracking ───────────────────────────────────────────────────────────

def test_source_openclaw_json_only(tmp_path):
    """Agent from openclaw.json only → source='openclaw_json'."""
    make_openclaw_json(tmp_path, [
        {"id": "src_test", "name": "SrcTest", "level": 2, "reports_to": None},
    ])
    # No agents/ directory

    registry = AgentRegistry(tmp_path)
    spec = registry.get("src_test")
    assert spec is not None
    assert spec.source == "openclaw_json"


def test_source_both_when_in_both(tmp_path):
    """Agent from both openclaw.json and agents/ dir → source='both'."""
    make_openclaw_json(tmp_path, [
        {"id": "dual", "name": "Dual", "level": 2, "reports_to": None},
    ])
    make_agent_dir(tmp_path, "dual", {
        "id": "dual",
        "name": "Dual",
        "level": 2,
    })

    registry = AgentRegistry(tmp_path)
    spec = registry.get("dual")
    assert spec is not None
    assert spec.source == "both"


def test_source_agents_dir_only(tmp_path):
    """Agent from agents/ dir only (not in openclaw.json) → source='agents_dir'."""
    make_openclaw_json(tmp_path, [])
    make_agent_dir(tmp_path, "dir_only", {
        "id": "dir_only",
        "name": "Dir Only",
        "level": 3,
    })

    registry = AgentRegistry(tmp_path)
    spec = registry.get("dir_only")
    assert spec is not None
    assert spec.source == "agents_dir"


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_no_openclaw_json_returns_empty_registry(tmp_path):
    """Missing openclaw.json → registry loads without error, possibly empty."""
    # No openclaw.json, no agents directory
    registry = AgentRegistry(tmp_path)
    assert registry.all_agents() == []


def test_agents_dir_only_no_openclaw_json(tmp_path):
    """agents/ directory present with config.json but no openclaw.json → agent registered from dir."""
    make_agent_dir(tmp_path, "standalone", {
        "id": "standalone",
        "name": "Standalone",
        "level": 3,
    })

    registry = AgentRegistry(tmp_path)
    spec = registry.get("standalone")
    assert spec is not None
    assert spec.source == "agents_dir"
