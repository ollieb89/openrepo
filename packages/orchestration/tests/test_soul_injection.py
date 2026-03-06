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


class TestSOULPopulationIntegration:
    """Integration tests verifying SOUL variables are populated from real data layer."""

    @pytest.fixture
    def project_env(self, tmp_path):
        """Create a minimal but real filesystem project structure under tmp_path."""
        # agents/_templates/soul-default.md — copy the real template
        real_template = (
            Path(__file__).parent.parent.parent.parent
            / "agents" / "_templates" / "soul-default.md"
        )
        template_dest = tmp_path / "agents" / "_templates" / "soul-default.md"
        template_dest.parent.mkdir(parents=True)
        template_dest.write_text(real_template.read_text())

        # projects/testproj/project.json
        project_dir = tmp_path / "projects" / "testproj"
        project_dir.mkdir(parents=True)
        project_config = {
            "id": "testproj",
            "name": "Test Project",
            "agent_display_name": "Test PM",
            "tech_stack": {"frontend": "React", "backend": "Python", "infra": "Docker"},
            "agents": {"l2_pm": "test_pm"},
        }
        (project_dir / "project.json").write_text(json.dumps(project_config))

        # workspace/.openclaw/testproj/workspace-state.json — empty tasks
        state_dir = tmp_path / "workspace" / ".openclaw" / "testproj"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "workspace-state.json"
        state_file.write_text(json.dumps({"tasks": {}}))

        # agents/test_pm/agent/config.json — L2 PM
        pm_agent_dir = tmp_path / "agents" / "test_pm" / "agent"
        pm_agent_dir.mkdir(parents=True)
        (pm_agent_dir / "config.json").write_text(json.dumps({
            "id": "test_pm",
            "name": "Test PM",
            "level": 2,
            "reports_to": "clawdia_prime",
            "max_concurrent": 2,
            "skills": [],
        }))

        # agents/l3_specialist/agent/config.json — L3, max_concurrent=1 for deterministic pool_utilization
        l3_agent_dir = tmp_path / "agents" / "l3_specialist" / "agent"
        l3_agent_dir.mkdir(parents=True)
        (l3_agent_dir / "config.json").write_text(json.dumps({
            "id": "l3_specialist",
            "name": "L3 Specialist",
            "level": 3,
            "reports_to": "test_pm",
            "max_concurrent": 1,
            "skills": [],
        }))

        return {"tmp_path": tmp_path, "state_file": state_file, "project_config": project_config}

    def test_active_task_count_nonzero_when_task_in_progress(self, project_env):
        """active_task_count and pool_utilization reflect a real in-progress task."""
        tmp_path = project_env["tmp_path"]
        state_file = project_env["state_file"]

        with patch("openclaw.config.get_project_root", return_value=tmp_path), \
             patch("openclaw.soul_renderer._find_project_root", return_value=tmp_path), \
             patch("openclaw.config.get_state_path", return_value=state_file):

            from openclaw.state_engine import JarvisState
            jarvis = JarvisState(state_file)
            jarvis.create_task("task-001", "code", metadata={})
            jarvis.update_task("task-001", "in_progress", "Starting work")

            registry = AgentRegistry(tmp_path)
            vars_ = build_dynamic_variables("testproj", "l3_specialist", registry)

        assert vars_["active_task_count"] == "1"
        assert vars_["pool_utilization"] == "1/1"

    def test_two_concurrent_states_show_different_counts(self, project_env):
        """Count before adding a task differs from count after."""
        tmp_path = project_env["tmp_path"]
        state_file = project_env["state_file"]

        with patch("openclaw.config.get_project_root", return_value=tmp_path), \
             patch("openclaw.soul_renderer._find_project_root", return_value=tmp_path), \
             patch("openclaw.config.get_state_path", return_value=state_file):

            registry = AgentRegistry(tmp_path)

            # Count before any tasks
            vars_before = build_dynamic_variables("testproj", "l3_specialist", registry)
            count_before = vars_before["active_task_count"]

            # Add a task and re-query
            from openclaw.state_engine import JarvisState
            jarvis = JarvisState(state_file)
            jarvis.create_task("task-002", "code", metadata={})
            jarvis.update_task("task-002", "in_progress", "Running")

            vars_after = build_dynamic_variables("testproj", "l3_specialist", registry)
            count_after = vars_after["active_task_count"]

        assert count_before != count_after
        assert count_after == "1"

    def test_topology_context_in_rendered_soul_after_save(self, project_env):
        """Topology data saved via save_topology() appears in rendered SOUL."""
        tmp_path = project_env["tmp_path"]
        state_file = project_env["state_file"]
        project_config = project_env["project_config"]

        nodes = [
            TopologyNode(id="agent-a", level=1, intent="orchestrate", risk_level="low"),
            TopologyNode(id="agent-b", level=2, intent="coordinate", risk_level="medium"),
            TopologyNode(id="agent-c", level=3, intent="execute", risk_level="low"),
        ]
        graph = TopologyGraph(
            project_id="testproj",
            nodes=nodes,
            edges=[],
            metadata={"archetype": "balanced", "structural_confidence": 0.82},
        )

        with patch("openclaw.config.get_project_root", return_value=tmp_path), \
             patch("openclaw.soul_renderer._find_project_root", return_value=tmp_path), \
             patch("openclaw.config.get_state_path", return_value=state_file), \
             patch("openclaw.topology.storage.get_project_root", return_value=tmp_path), \
             patch("openclaw.soul_renderer.load_project_config", return_value=project_config):

            save_topology("testproj", graph)

            registry = AgentRegistry(tmp_path)
            dynamic_vars = build_dynamic_variables("testproj", "l3_specialist", registry)

            assert dynamic_vars["topology_archetype"] == "balanced"
            assert dynamic_vars["topology_agent_count"] == "3"
            assert dynamic_vars["topology_confidence"] == "0.82"

            soul = render_soul(
                "testproj",
                extra_variables={**dynamic_vars, "memory_section": "No context loaded."},
            )

        assert "balanced" in soul

    def test_soul_template_has_topology_placeholders(self):
        """The real soul-default.md template contains all topology variable placeholders."""
        real_template = (
            Path(__file__).parent.parent.parent.parent
            / "agents" / "_templates" / "soul-default.md"
        )
        content = real_template.read_text()

        assert "$topology_archetype" in content
        assert "$topology_agent_count" in content
        assert "$topology_confidence" in content
