"""
Integration tests for the approval gate (router plan 63-03).

Tests verify the Python check_approval_gate function behavior with file presence
and absence — gating L3 spawns when no approved topology exists.

Requirements: CORR-07 (approval gate enforcement).
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_current_json(topo_dir: Path) -> Path:
    """Write a minimal valid current.json into topo_dir. Returns path."""
    topo_dir.mkdir(parents=True, exist_ok=True)
    current = topo_dir / "current.json"
    current.write_text(json.dumps({
        "project_id": "test-project",
        "nodes": [],
        "edges": [],
    }))
    return current


def _topo_dir(root: Path, project_id: str) -> Path:
    """Return workspace/.openclaw/<project_id>/topology path under root."""
    return root / "workspace" / ".openclaw" / project_id / "topology"


# ---------------------------------------------------------------------------
# TestApprovalGateBlocking — gate blocks when no current.json exists
# ---------------------------------------------------------------------------

class TestApprovalGateBlocking:

    def test_gate_blocks_no_topology(self, tmp_path):
        """check_approval_gate returns approved=False when current.json absent."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "test-proj"
        # Don't create topology dir or current.json

        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            result = check_approval_gate(project_id, auto_approve_l1=False)

        assert result["approved"] is False
        assert "reason" in result

    def test_gate_blocks_returns_reason_string(self, tmp_path):
        """When gate blocks, result['reason'] must be a non-empty string."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "my-proj"
        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            result = check_approval_gate(project_id, auto_approve_l1=False)

        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_gate_blocks_message_includes_project_id(self, tmp_path):
        """Blocked gate reason must contain the project_id."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "unique-project-xyz"
        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            result = check_approval_gate(project_id, auto_approve_l1=False)

        assert project_id in result["reason"], (
            f"project_id '{project_id}' not found in reason: {result['reason']}"
        )

    def test_gate_blocks_message_mentions_propose_command(self, tmp_path):
        """Blocked gate reason must mention 'openclaw-propose' so user knows the fix."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "proj-no-topo"
        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            result = check_approval_gate(project_id, auto_approve_l1=False)

        assert "openclaw-propose" in result["reason"], (
            f"'openclaw-propose' not in reason: {result['reason']}"
        )


# ---------------------------------------------------------------------------
# TestApprovalGatePassing — gate passes when current.json exists
# ---------------------------------------------------------------------------

class TestApprovalGatePassing:

    def test_gate_passes_with_topology(self, tmp_path):
        """check_approval_gate returns approved=True when current.json exists."""
        from openclaw.topology.approval import check_approval_gate
        from openclaw.topology.models import TopologyGraph

        project_id = "approved-project"
        topo_dir = _topo_dir(tmp_path, project_id)

        # Write a minimal topology so save_topology produces current.json
        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            from openclaw.topology.storage import save_topology
            graph = TopologyGraph(project_id=project_id, nodes=[], edges=[])
            save_topology(project_id, graph)

            result = check_approval_gate(project_id, auto_approve_l1=False)

        assert result["approved"] is True
        assert "reason" not in result

    def test_gate_passes_current_json_present(self, tmp_path):
        """Manually written current.json is sufficient for gate to pass."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "manual-topo-proj"
        topo_dir = _topo_dir(tmp_path, project_id)
        _write_current_json(topo_dir)

        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            result = check_approval_gate(project_id, auto_approve_l1=False)

        assert result["approved"] is True


# ---------------------------------------------------------------------------
# TestApprovalGateAutoApprove — auto_approve_l1 bypasses gate
# ---------------------------------------------------------------------------

class TestApprovalGateAutoApprove:

    def test_gate_bypassed_when_auto_approve_true(self, tmp_path):
        """auto_approve_l1=True returns approved=True without checking disk."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "no-topo-auto-approved"
        # No topology dir created — gate would normally block

        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            result = check_approval_gate(project_id, auto_approve_l1=True)

        assert result["approved"] is True

    def test_gate_bypass_does_not_require_topology_file(self, tmp_path):
        """auto_approve_l1=True returns approved even when current.json is absent."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "bypass-no-file"
        topo_dir = _topo_dir(tmp_path, project_id)
        # Explicitly verify dir doesn't exist
        assert not topo_dir.exists()

        with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
            result = check_approval_gate(project_id, auto_approve_l1=True)

        assert result == {"approved": True}


# ---------------------------------------------------------------------------
# TestApprovalGateConfigIntegration — gate reads auto_approve_l1 from config
# ---------------------------------------------------------------------------

class TestApprovalGateConfigIntegration:

    def test_gate_config_key_auto_approve_l1_accessible(self):
        """get_topology_config() exposes auto_approve_l1 key for router consumption."""
        from openclaw.config import get_topology_config
        tc = get_topology_config()
        assert "auto_approve_l1" in tc
        assert isinstance(tc["auto_approve_l1"], bool)

    def test_gate_config_key_pushback_threshold_accessible(self):
        """get_topology_config() exposes pushback_threshold key."""
        from openclaw.config import get_topology_config
        tc = get_topology_config()
        assert "pushback_threshold" in tc
        assert isinstance(tc["pushback_threshold"], (int, float))

    def test_gate_respects_auto_approve_from_config(self, tmp_path, monkeypatch):
        """When openclaw.json sets auto_approve_l1=true, gate bypass works end-to-end."""
        from openclaw.topology.approval import check_approval_gate

        project_id = "config-driven-bypass"
        # No topology on disk

        # Patch get_topology_config to return auto_approve_l1=True
        with patch("openclaw.config.get_topology_config") as mock_cfg:
            mock_cfg.return_value = {
                "auto_approve_l1": True,
                "pushback_threshold": 8,
                "proposal_confidence_warning_threshold": 5,
                "rubric_weights": {},
            }
            with patch("openclaw.topology.storage.get_project_root", return_value=tmp_path):
                # Consumer (router) reads config then calls check_approval_gate with auto_approve_l1
                tc = mock_cfg()
                result = check_approval_gate(project_id, auto_approve_l1=tc["auto_approve_l1"])

        assert result["approved"] is True
