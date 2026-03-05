"""
Tests for SOUL injection verification (FR-08).

Verifies that build_dynamic_variables() returns live data at spawn time,
including topology context.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openclaw.soul_renderer import build_dynamic_variables, render_soul
from openclaw.agent_registry import AgentRegistry, AgentSpec, AgentLevel
from openclaw.topology.models import TopologyGraph, TopologyNode
from openclaw.topology.storage import save_topology


@pytest.fixture
def temp_project(tmp_path):
    """Create a minimal project structure for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create project config
    project_config = {
        "id": "test_project",
        "name": "Test Project",
        "agent_display_name": "Test Agent",
        "tech_stack": {
            "frontend": "React",
            "backend": "Python",
            "infra": "Docker"
        }
    }
    config_file = project_dir / "project.json"
    config_file.write_text(json.dumps(project_config))
    
    # Create workspace structure
    openclaw_dir = project_dir / "workspace" / ".openclaw" / "test_project"
    openclaw_dir.mkdir(parents=True)
    
    return project_dir


@pytest.fixture
def mock_registry(tmp_path):
    """Create a mock AgentRegistry with test agents."""
    registry = MagicMock(spec=AgentRegistry)
    
    # Mock L3 specialist agent
    l3_agent = AgentSpec(
        id="l3_specialist",
        name="L3 Code Specialist",
        level=AgentLevel.L3,
        reports_to="pumplai_pm",
        max_concurrent=3,
    )
    
    # Mock L2 PM agent
    pm_agent = AgentSpec(
        id="pumplai_pm",
        name="PumpLAI PM",
        level=AgentLevel.L2,
        reports_to="clawdia_prime",
        max_concurrent=2,
    )
    
    def mock_get(agent_id):
        if agent_id == "l3_specialist":
            return l3_agent
        if agent_id == "pumplai_pm":
            return pm_agent
        if agent_id == "clawdia_prime":
            return AgentSpec(id="clawdia_prime", name="Head of Development", level=AgentLevel.L1)
        return None
    
    registry.get = mock_get
    registry.list_by_level = lambda level: [l3_agent] if level == AgentLevel.L3 else []
    registry.get_subordinates = lambda agent_id: [l3_agent] if agent_id == "pumplai_pm" else []
    
    return registry


class TestBuildDynamicVariables:
    """Test that build_dynamic_variables returns live data."""
    
    def test_returns_basic_dynamic_vars(self, tmp_path, mock_registry):
        """Verify basic dynamic variables are populated."""
        with patch('openclaw.config.get_state_path') as mock_get_path:
            mock_get_path.return_value = tmp_path / "workspace-state.json"
            
            # Create empty state file
            state_file = tmp_path / "workspace-state.json"
            state_file.write_text(json.dumps({"tasks": {}}))
            
            vars = build_dynamic_variables("test_project", "l3_specialist", mock_registry)
            
            # Verify all expected keys are present
            assert "superior_name" in vars
            assert "superior_id" in vars
            assert "peer_agents" in vars
            assert "subordinate_agents" in vars
            assert "active_task_count" in vars
            assert "pool_utilization" in vars
            assert "autonomy_confidence" in vars
            assert "autonomy_state" in vars
            
            # Verify values are populated (not zeroed/stale)
            assert vars["superior_name"] == "PumpLAI PM"
            assert vars["superior_id"] == "pumplai_pm"
            assert vars["active_task_count"] == "0"
            assert vars["pool_utilization"] == "0/3"
    
    def test_topology_context_included(self, tmp_path, mock_registry):
        """Verify topology context is included in dynamic variables (FR-08)."""
        with patch('openclaw.config.get_state_path') as mock_get_path:
            with patch('openclaw.topology.storage.load_topology') as mock_load_topology:
                mock_get_path.return_value = tmp_path / "workspace-state.json"
                
                # Create empty state file
                state_file = tmp_path / "workspace-state.json"
                state_file.write_text(json.dumps({"tasks": {}}))
                
                # Mock topology with archetype and confidence
                mock_topology = MagicMock()
                mock_topology.nodes = [
                    TopologyNode(id="agent1", level=1, intent="coordinate", risk_level="low"),
                    TopologyNode(id="agent2", level=3, intent="execute", risk_level="medium"),
                ]
                mock_topology.metadata = {
                    "archetype": "balanced",
                    "structural_confidence": 0.85
                }
                mock_load_topology.return_value = mock_topology
                
                vars = build_dynamic_variables("test_project", "l3_specialist", mock_registry)
                
                # Verify topology context is present
                assert "topology_archetype" in vars
                assert "topology_agent_count" in vars
                assert "topology_confidence" in vars
                
                # Verify values are populated
                assert vars["topology_archetype"] == "balanced"
                assert vars["topology_agent_count"] == "2"
                assert vars["topology_confidence"] == "0.85"
    
    def test_topology_context_defaults_when_no_topology(self, tmp_path, mock_registry):
        """Verify topology context has safe defaults when no topology exists."""
        with patch('openclaw.config.get_state_path') as mock_get_path:
            with patch('openclaw.topology.storage.load_topology') as mock_load_topology:
                mock_get_path.return_value = tmp_path / "workspace-state.json"
                
                # Create empty state file
                state_file = tmp_path / "workspace-state.json"
                state_file.write_text(json.dumps({"tasks": {}}))
                
                # No topology available
                mock_load_topology.return_value = None
                
                vars = build_dynamic_variables("test_project", "l3_specialist", mock_registry)
                
                # Verify safe defaults
                assert vars["topology_archetype"] == "unknown"
                assert vars["topology_agent_count"] == "0"
                assert vars["topology_confidence"] == "0.0"


class TestSoulInjectionIntegration:
    """Integration tests for SOUL rendering with dynamic variables."""
    
    def test_rendered_soul_contains_dynamic_sections(self, tmp_path):
        """Verify rendered SOUL contains populated dynamic sections."""
        # This test requires a full project setup with templates
        # Skip if template doesn't exist
        template_path = tmp_path / "agents" / "_templates" / "soul-default.md"
        template_path.parent.mkdir(parents=True)
        template_path.write_text("""
# Soul: $agent_name ($tier)

## Hierarchy
Superior: $superior_name ($superior_id)
Peers: $peer_agents
Subordinates: $subordinate_agents

## Status
Active Tasks: $active_task_count
Pool Utilization: $pool_utilization
Topology Archetype: $topology_archetype
Topology Agents: $topology_agent_count
Topology Confidence: $topology_confidence

## Context
$memory_section
""")
        
        # Create project config
        project_dir = tmp_path / "projects" / "test_project"
        project_dir.mkdir(parents=True)
        project_config = {
            "id": "test_project",
            "name": "Test Project",
            "agent_display_name": "Test PM",
            "agents": {"l2_pm": "test_pm"}
        }
        (project_dir / "project.json").write_text(json.dumps(project_config))
        
        with patch('openclaw.soul_renderer._find_project_root') as mock_root:
            with patch('openclaw.soul_renderer.load_project_config') as mock_config:
                mock_root.return_value = tmp_path
                mock_config.return_value = project_config
                
                # Render with dynamic variables
                extra_vars = {
                    "superior_name": "Clawdia Prime",
                    "superior_id": "clawdia_prime",
                    "peer_agents": "Other PM",
                    "subordinate_agents": "L3 Specialist",
                    "active_task_count": "2",
                    "pool_utilization": "2/3",
                    "topology_archetype": "balanced",
                    "topology_agent_count": "4",
                    "topology_confidence": "0.85",
                    "memory_section": "- Memory item 1\n- Memory item 2",
                }
                
                soul = render_soul("test_project", extra_variables=extra_vars)
                
                # Verify dynamic sections are populated
                assert "Clawdia Prime" in soul
                assert "2/3" in soul
                assert "balanced" in soul
                assert "0.85" in soul
                assert "Memory item 1" in soul
