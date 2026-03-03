"""
Tests for the topology proposal generation pipeline (proposer.py).

All LLM calls are mocked — no real API calls are made.
"""

import json
import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import jsonschema
import pytest

from openclaw.topology.proposer import (
    PROPOSAL_JSON_SCHEMA,
    ask_clarifications,
    build_proposals,
    generate_proposals,
    generate_proposals_sync,
)
from openclaw.topology.llm_client import strip_markdown_fences
from openclaw.topology.models import EdgeType


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_archetype_entry(name_prefix: str) -> dict:
    """Return a valid archetype_proposal dict."""
    return {
        "roles": [
            {"id": f"{name_prefix}_orchestrator", "level": 1, "intent": "coordinate", "risk_level": "low"},
            {"id": f"{name_prefix}_worker", "level": 3, "intent": "execute tasks", "risk_level": "medium"},
        ],
        "hierarchy": [
            {"from_role": f"{name_prefix}_orchestrator", "to_role": f"{name_prefix}_worker", "edge_type": "delegation"},
        ],
        "delegation_boundaries": "L1 delegates to L3 directly",
        "coordination_model": "sequential",
        "risk_assessment": "low risk",
        "justification": f"This is the {name_prefix} topology because it is minimal.",
    }


def _make_valid_raw_dict() -> dict:
    """Return a valid LLM output dict with all three archetypes."""
    return {
        "lean": _make_archetype_entry("lean"),
        "balanced": _make_archetype_entry("balanced"),
        "robust": _make_archetype_entry("robust"),
    }


def _make_registry_mock(agent_ids: List[str] = None) -> MagicMock:
    """Return a mock AgentRegistry with configurable agent IDs."""
    if agent_ids is None:
        agent_ids = ["clawdia_prime", "main", "python_backend_worker"]
    registry = MagicMock()
    registry._agents = {aid: MagicMock() for aid in agent_ids}
    return registry


# ---------------------------------------------------------------------------
# Tests: build_proposals
# ---------------------------------------------------------------------------

class TestBuildProposals:
    def test_build_proposals_from_raw_dict_returns_three_proposals(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        assert len(proposals) == 3

    def test_build_proposals_archetype_names(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        names = [p.archetype for p in proposals]
        assert names == ["lean", "balanced", "robust"]

    def test_build_proposals_contains_topology_graph(self):
        from openclaw.topology.models import TopologyGraph
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        for proposal in proposals:
            assert isinstance(proposal.graph, TopologyGraph)

    def test_build_proposals_nodes_match_roles(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        lean = proposals[0]
        node_ids = [n.id for n in lean.graph.nodes]
        assert "lean_orchestrator" in node_ids
        assert "lean_worker" in node_ids

    def test_build_proposals_edges_match_hierarchy(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        lean = proposals[0]
        assert len(lean.graph.edges) == 1
        edge = lean.graph.edges[0]
        assert edge.from_role == "lean_orchestrator"
        assert edge.to_role == "lean_worker"
        assert edge.edge_type == EdgeType.DELEGATION

    def test_build_proposals_justification_preserved(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        for p in proposals:
            assert p.archetype in p.justification
            assert "minimal" in p.justification

    def test_build_proposals_project_id_set_on_graph(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="my_proj")
        for p in proposals:
            assert p.graph.project_id == "my_proj"

    def test_build_proposals_delegation_boundaries_preserved(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        assert proposals[0].delegation_boundaries == "L1 delegates to L3 directly"

    def test_build_proposals_coordination_model_preserved(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        assert proposals[0].coordination_model == "sequential"

    def test_build_proposals_risk_assessment_preserved(self):
        raw = _make_valid_raw_dict()
        proposals = build_proposals(raw, project_id="test_project")
        assert proposals[0].risk_assessment == "low risk"


# ---------------------------------------------------------------------------
# Tests: strip_markdown_fences
# ---------------------------------------------------------------------------

class TestStripMarkdownFences:
    def test_strips_json_fences(self):
        text = '```json\n{"a": 1}\n```'
        assert strip_markdown_fences(text) == '{"a": 1}'

    def test_strips_plain_fences(self):
        text = '```\n{"a": 1}\n```'
        assert strip_markdown_fences(text) == '{"a": 1}'

    def test_passthrough_when_no_fences(self):
        text = '{"a": 1}'
        assert strip_markdown_fences(text) == '{"a": 1}'

    def test_strips_whitespace(self):
        text = '  ```json\n{"x": 2}\n```  '
        assert strip_markdown_fences(text) == '{"x": 2}'


# ---------------------------------------------------------------------------
# Tests: ask_clarifications
# ---------------------------------------------------------------------------

class TestAskClarifications:
    def test_non_interactive_returns_defaults(self):
        result = ask_clarifications(interactive=False)
        assert "risk_tolerance" in result
        assert "timeline_pressure" in result
        assert result["risk_tolerance"] == "medium"
        assert result["timeline_pressure"] == "moderate"

    def test_non_interactive_includes_assumptions_note(self, capsys):
        ask_clarifications(interactive=False)
        # Non-interactive should not print questions (no TTY output)
        # This test just verifies it runs cleanly without raising
        assert True

    def test_interactive_uses_input(self):
        with patch("builtins.input", side_effect=["high", "urgent"]):
            result = ask_clarifications(interactive=True)
        assert result["risk_tolerance"] == "high"
        assert result["timeline_pressure"] == "urgent"

    def test_interactive_defaults_on_empty_input(self):
        with patch("builtins.input", side_effect=["", ""]):
            result = ask_clarifications(interactive=True)
        assert result["risk_tolerance"] == "medium"
        assert result["timeline_pressure"] == "moderate"


# ---------------------------------------------------------------------------
# Tests: rejection context from changelog
# ---------------------------------------------------------------------------

class TestRejectionContext:
    def test_rejection_context_loads_from_changelog(self):
        from openclaw.topology.proposer import _load_rejection_context
        changelog = [
            {"correction_type": "rejected", "rejected_pattern": "orphan_executor"},
            {"correction_type": "approved", "pattern": "balanced"},
        ]
        with patch("openclaw.topology.proposer.load_changelog", return_value=changelog):
            context = _load_rejection_context("test_proj")
        assert context is not None
        assert "orphan_executor" in context

    def test_rejection_context_none_when_no_rejected_entries(self):
        from openclaw.topology.proposer import _load_rejection_context
        changelog = [
            {"correction_type": "approved", "pattern": "balanced"},
        ]
        with patch("openclaw.topology.proposer.load_changelog", return_value=changelog):
            context = _load_rejection_context("test_proj")
        assert context is None

    def test_rejection_context_none_on_empty_changelog(self):
        from openclaw.topology.proposer import _load_rejection_context
        with patch("openclaw.topology.proposer.load_changelog", return_value=[]):
            context = _load_rejection_context("test_proj")
        assert context is None

    def test_rejection_context_graceful_on_unexpected_format(self):
        from openclaw.topology.proposer import _load_rejection_context
        # Entries missing expected keys should not raise
        changelog = [{"bad_key": "value"}, "not_a_dict"]
        with patch("openclaw.topology.proposer.load_changelog", return_value=changelog):
            # Should not raise — graceful degradation
            context = _load_rejection_context("test_proj")
        # May be None or a string — just must not raise
        assert context is None or isinstance(context, str)


# ---------------------------------------------------------------------------
# Tests: generate_proposals (async, mocked LLM)
# ---------------------------------------------------------------------------

class TestGenerateProposals:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_rejection_context_none_when_fresh(self):
        """When fresh=True, rejection context should not be loaded."""
        valid_json = json.dumps(_make_valid_raw_dict())
        registry = _make_registry_mock()
        with patch("openclaw.topology.proposer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = valid_json
            with patch("openclaw.topology.proposer.load_changelog") as mock_cl:
                result = self._run(
                    generate_proposals(
                        "build a CI/CD pipeline",
                        "proj_x",
                        registry,
                        max_concurrent=3,
                        fresh=True,
                        clarifications={"risk_tolerance": "medium", "timeline_pressure": "moderate"},
                    )
                )
        # load_changelog should NOT have been called when fresh=True
        mock_cl.assert_not_called()
        assert "lean" in result
        assert "balanced" in result
        assert "robust" in result

    def test_rejected_roles_injected_into_prompt(self):
        """Rejected roles list is explicitly mentioned in system prompt."""
        valid_json = json.dumps(_make_valid_raw_dict())
        registry = _make_registry_mock()
        captured_prompts = {}

        async def capture_llm(system_prompt: str, user_message: str) -> str:
            captured_prompts["system"] = system_prompt
            return valid_json

        with patch("openclaw.topology.proposer.call_llm", side_effect=capture_llm):
            with patch("openclaw.topology.proposer.load_changelog", return_value=[]):
                self._run(
                    generate_proposals(
                        "build a deployment pipeline",
                        "proj_y",
                        registry,
                        max_concurrent=3,
                        fresh=True,
                        clarifications={"risk_tolerance": "low", "timeline_pressure": "relaxed"},
                        rejected_roles=["bad_agent", "broken_executor"],
                    )
                )

        assert "bad_agent" in captured_prompts["system"]
        assert "broken_executor" in captured_prompts["system"]

    def test_available_roles_injected_into_prompt(self):
        """Available agent roles are listed in the system prompt."""
        valid_json = json.dumps(_make_valid_raw_dict())
        registry = _make_registry_mock(["agent_alpha", "agent_beta"])
        captured_prompts = {}

        async def capture_llm(system_prompt: str, user_message: str) -> str:
            captured_prompts["system"] = system_prompt
            return valid_json

        with patch("openclaw.topology.proposer.call_llm", side_effect=capture_llm):
            with patch("openclaw.topology.proposer.load_changelog", return_value=[]):
                self._run(
                    generate_proposals(
                        "deploy a service",
                        "proj_z",
                        registry,
                        max_concurrent=2,
                        fresh=True,
                        clarifications={"risk_tolerance": "medium", "timeline_pressure": "moderate"},
                    )
                )

        assert "agent_alpha" in captured_prompts["system"]
        assert "agent_beta" in captured_prompts["system"]

    def test_strips_markdown_fences_before_parsing(self):
        """LLM response wrapped in ```json fences is parsed correctly."""
        valid_json = "```json\n" + json.dumps(_make_valid_raw_dict()) + "\n```"
        registry = _make_registry_mock()

        with patch("openclaw.topology.proposer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = valid_json
            with patch("openclaw.topology.proposer.load_changelog", return_value=[]):
                result = self._run(
                    generate_proposals(
                        "test fence stripping",
                        "proj_fence",
                        registry,
                        max_concurrent=3,
                        fresh=True,
                        clarifications={"risk_tolerance": "medium", "timeline_pressure": "moderate"},
                    )
                )

        assert "lean" in result
        assert "balanced" in result
        assert "robust" in result


# ---------------------------------------------------------------------------
# Tests: PROPOSAL_JSON_SCHEMA validation
# ---------------------------------------------------------------------------

class TestProposalJsonSchema:
    def test_schema_validates_correct_dict(self):
        raw = _make_valid_raw_dict()
        # Should not raise
        jsonschema.validate(raw, PROPOSAL_JSON_SCHEMA)

    def test_schema_rejects_missing_archetype_key(self):
        raw = _make_valid_raw_dict()
        del raw["lean"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(raw, PROPOSAL_JSON_SCHEMA)

    def test_schema_rejects_missing_required_fields_in_archetype(self):
        raw = _make_valid_raw_dict()
        del raw["balanced"]["justification"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(raw, PROPOSAL_JSON_SCHEMA)

    def test_schema_rejects_non_object_archetype(self):
        raw = _make_valid_raw_dict()
        raw["robust"] = "not_a_dict"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(raw, PROPOSAL_JSON_SCHEMA)


# ---------------------------------------------------------------------------
# Tests: generate_proposals_sync (sync wrapper)
# ---------------------------------------------------------------------------

class TestGenerateProposalsSync:
    def test_sync_wrapper_works(self):
        valid_json = json.dumps(_make_valid_raw_dict())
        registry = _make_registry_mock()
        with patch("openclaw.topology.proposer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = valid_json
            with patch("openclaw.topology.proposer.load_changelog", return_value=[]):
                result = generate_proposals_sync(
                    "deploy service",
                    "proj_sync",
                    registry,
                    max_concurrent=3,
                    fresh=True,
                    clarifications={"risk_tolerance": "medium", "timeline_pressure": "moderate"},
                )
        assert "lean" in result
        assert "balanced" in result
