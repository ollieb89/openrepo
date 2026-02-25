"""
Phase 49 test suite — Deferred Reliability, Quality, and Observability.

Covers three requirements:
  REL-09 — Docker health checks for L3 containers (sentinel file approach)
  QUAL-07 — Cosine similarity conflict threshold calibration
  OBS-05  — Adaptive monitor polling
"""

from pathlib import Path
import pytest


# ---------------------------------------------------------------------------
# REL-09 — Dockerfile and entrypoint inspection (file content tests, no Docker daemon needed)
# ---------------------------------------------------------------------------

def test_dockerfile_has_healthcheck():
    """HEALTHCHECK instruction present with correct parameters."""
    dockerfile = Path(__file__).parent.parent.parent.parent / "docker/l3-specialist/Dockerfile"
    content = dockerfile.read_text()
    assert "HEALTHCHECK" in content
    assert "--interval=30s" in content
    assert "--timeout=5s" in content
    assert "--retries=3" in content
    assert "--start-period=30s" in content
    assert "test -f /tmp/openclaw-healthy" in content


def test_entrypoint_writes_sentinel():
    """entrypoint.sh writes /tmp/openclaw-healthy after startup initialization."""
    entrypoint = Path(__file__).parent.parent.parent.parent / "docker/l3-specialist/entrypoint.sh"
    content = entrypoint.read_text()
    assert "touch /tmp/openclaw-healthy" in content
    # Sentinel must appear AFTER the update_state "starting" line
    starting_pos = content.index('update_state "starting"')
    sentinel_pos = content.index("touch /tmp/openclaw-healthy")
    assert sentinel_pos > starting_pos, "Sentinel must be written after update_state starting"


# ---------------------------------------------------------------------------
# QUAL-07 — config.py constant and openclaw.json schema
# ---------------------------------------------------------------------------

def test_conflict_threshold_constant():
    """MEMORY_CONFLICT_THRESHOLD exists in config.py with value in (0.7, 1.0)."""
    from openclaw.config import MEMORY_CONFLICT_THRESHOLD
    assert isinstance(MEMORY_CONFLICT_THRESHOLD, float)
    assert 0.7 < MEMORY_CONFLICT_THRESHOLD < 1.0


def test_conflict_threshold_override(tmp_path, monkeypatch):
    """get_conflict_threshold() reads conflict_threshold override from openclaw.json."""
    import json
    config = {
        "gateway": {"port": 18789},
        "agents": {"list": []},
        "memory": {"conflict_threshold": 0.91},
    }
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(json.dumps(config))
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
    from openclaw.project_config import get_conflict_threshold
    threshold = get_conflict_threshold()
    assert threshold == 0.91


def test_conflict_threshold_schema():
    """conflict_threshold is a valid field in the openclaw.json schema (no additionalProperties violation)."""
    from openclaw.config import OPENCLAW_JSON_SCHEMA
    memory_schema = OPENCLAW_JSON_SCHEMA["properties"]["memory"]
    assert "properties" in memory_schema, "memory schema must have explicit properties for documentation"
    assert "conflict_threshold" in memory_schema["properties"]
    ct_schema = memory_schema["properties"]["conflict_threshold"]
    assert ct_schema.get("type") == "number"


# ---------------------------------------------------------------------------
# OBS-05 — adaptive polling in monitor
# ---------------------------------------------------------------------------

def test_adaptive_poll_idle(monkeypatch):
    """_count_active_l3_containers returns 0 when no containers running (mocked Docker)."""
    import types
    mock_docker = types.SimpleNamespace(
        from_env=lambda: types.SimpleNamespace(
            containers=types.SimpleNamespace(
                list=lambda filters: []
            )
        )
    )
    monkeypatch.setattr("openclaw.cli.monitor.docker", mock_docker, raising=False)
    from openclaw.cli.monitor import _count_active_l3_containers
    assert _count_active_l3_containers() == 0


def test_adaptive_poll_active(monkeypatch):
    """_count_active_l3_containers returns >0 when containers running (mocked Docker)."""
    import types
    fake_container = object()
    mock_docker = types.SimpleNamespace(
        from_env=lambda: types.SimpleNamespace(
            containers=types.SimpleNamespace(
                list=lambda filters: [fake_container, fake_container]
            )
        )
    )
    monkeypatch.setattr("openclaw.cli.monitor.docker", mock_docker, raising=False)
    from openclaw.cli.monitor import _count_active_l3_containers
    assert _count_active_l3_containers() == 2


def test_adaptive_poll_docker_failure(monkeypatch):
    """Returns POLL_INTERVAL_IDLE on Docker connection failure (fail-open)."""
    import types

    def raise_error():
        raise ConnectionError("Docker not available")

    mock_docker = types.SimpleNamespace(from_env=raise_error)
    monkeypatch.setattr("openclaw.cli.monitor.docker", mock_docker, raising=False)
    from openclaw.cli.monitor import _count_active_l3_containers, POLL_INTERVAL_IDLE
    # Should return 0 (not raise), causing caller to sleep POLL_INTERVAL_IDLE
    count = _count_active_l3_containers()
    assert count == 0
