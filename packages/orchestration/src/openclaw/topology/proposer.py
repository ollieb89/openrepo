"""
Topology Proposal Generation Pipeline

Transforms an outcome description into 3 structured topology proposals
(Lean, Balanced, Robust) via an LLM call with changelog context injection.

Public API:
  generate_proposals(...)       — async; returns raw LLM dict
  generate_proposals_sync(...)  — sync wrapper using asyncio.run()
  build_proposals(raw, proj)    — converts raw LLM dict to list[TopologyProposal]
  ask_clarifications(interactive) — hybrid input (TTY or defaults)
  PROPOSAL_JSON_SCHEMA          — JSON schema for validating LLM output
"""

import asyncio
import json
import logging
import sys
from typing import Dict, List, Optional

import jsonschema

from openclaw.agent_registry import AgentRegistry
from openclaw.topology.llm_client import call_llm, strip_markdown_fences
from openclaw.topology.models import EdgeType, TopologyEdge, TopologyGraph, TopologyNode
from openclaw.topology.proposal_models import TopologyProposal
from openclaw.topology.storage import load_changelog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON schema for LLM output validation
# ---------------------------------------------------------------------------

PROPOSAL_JSON_SCHEMA: Dict = {
    "type": "object",
    "required": ["lean", "balanced", "robust"],
    "additionalProperties": False,
    "properties": {
        "lean":     {"$ref": "#/$defs/archetype_proposal"},
        "balanced": {"$ref": "#/$defs/archetype_proposal"},
        "robust":   {"$ref": "#/$defs/archetype_proposal"},
    },
    "$defs": {
        "archetype_proposal": {
            "type": "object",
            "required": [
                "roles",
                "hierarchy",
                "delegation_boundaries",
                "coordination_model",
                "risk_assessment",
                "justification",
            ],
            "properties": {
                "roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "level", "intent", "risk_level"],
                        "properties": {
                            "id": {"type": "string"},
                            "level": {"type": "integer"},
                            "intent": {"type": "string"},
                            "risk_level": {"type": "string"},
                        },
                    },
                },
                "hierarchy": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["from_role", "to_role", "edge_type"],
                        "properties": {
                            "from_role": {"type": "string"},
                            "to_role": {"type": "string"},
                            "edge_type": {
                                "type": "string",
                                "enum": [
                                    "delegation",
                                    "coordination",
                                    "review_gate",
                                    "information_flow",
                                    "escalation",
                                ],
                            },
                        },
                    },
                },
                "delegation_boundaries": {"type": "string"},
                "coordination_model": {"type": "string"},
                "risk_assessment": {"type": "string"},
                "justification": {"type": "string"},
            },
        }
    },
}


# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

PROPOSAL_SYSTEM_PROMPT = (
    "You are an expert at designing multi-agent swarm topologies.\n"
    "Given an outcome description, generate exactly 3 topology proposals:\n"
    "one Lean (minimal roles, fast), one Balanced (moderate structure), one Robust (safe, redundant).\n\n"
    "STRICT CONSTRAINTS:\n"
    "- You MUST only use role IDs from this exact list: {available_roles}\n"
    "  Do NOT invent variants, suffixes, or task-specific role names.\n"
    "- Valid edge_type values are EXACTLY: delegation, coordination, review_gate, information_flow, escalation\n"
    "  Do NOT use other relationship terms like 'orchestrates', 'oversees', or 'informs'.\n"
    "- Project constraint: max {max_concurrent} concurrent L3 agents\n\n"
    "{rejection_context}"
    "Return ONLY valid JSON matching this schema: {json_schema}\n"
    "Do not include markdown fences or explanation outside the JSON."
)


# ---------------------------------------------------------------------------
# Clarifying questions
# ---------------------------------------------------------------------------

CLARIFYING_QUESTIONS = [
    ("risk_tolerance", "What is your risk tolerance? (low/medium/high, default: medium)"),
    ("timeline_pressure", "Timeline pressure? (relaxed/moderate/urgent, default: moderate)"),
]

_CLARIFICATION_DEFAULTS = {
    "risk_tolerance": "medium",
    "timeline_pressure": "moderate",
}


def ask_clarifications(interactive: bool) -> Dict[str, str]:
    """Gather clarification answers interactively or return defaults.

    In interactive mode (TTY), prints each question and reads stdin input.
    Empty input accepts the default value.

    In non-interactive mode (piped stdin / CI), skips all prompts and
    returns default values. The caller should surface these as assumptions.

    Args:
        interactive: True if stdin is a TTY; False for piped/non-interactive.

    Returns:
        Dict with keys matching CLARIFYING_QUESTIONS keys.
    """
    answers: Dict[str, str] = {}

    if not interactive:
        logger.debug(
            "Non-interactive mode — using clarification defaults: %s",
            _CLARIFICATION_DEFAULTS,
        )
        return dict(_CLARIFICATION_DEFAULTS)

    for key, question in CLARIFYING_QUESTIONS:
        default = _CLARIFICATION_DEFAULTS[key]
        raw = input(f"{question}: ").strip()
        answers[key] = raw if raw else default

    return answers


# ---------------------------------------------------------------------------
# Rejection context from changelog
# ---------------------------------------------------------------------------

def _load_rejection_context(project_id: str) -> Optional[str]:
    """Load rejected patterns from the topology changelog.

    Gracefully handles missing changelog, unexpected entry formats, and
    changelogs with no rejection entries.

    Args:
        project_id: Project identifier for changelog lookup.

    Returns:
        Formatted string describing rejected patterns, or None if none exist.
    """
    try:
        entries = load_changelog(project_id)
    except Exception as exc:
        logger.warning("Could not load changelog for project %s: %s", project_id, exc)
        return None

    rejected_patterns: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # Support both "correction_type" == "rejected" and entries with "rejected_pattern"
        correction_type = entry.get("correction_type", "")
        if correction_type == "rejected":
            pattern = entry.get("rejected_pattern") or entry.get("pattern") or str(entry)
            rejected_patterns.append(str(pattern))

    if not rejected_patterns:
        return None

    lines = ["Previously rejected patterns to AVOID:"]
    for pattern in rejected_patterns:
        lines.append(f"  - {pattern}")
    return "\n".join(lines) + "\n\n"


# ---------------------------------------------------------------------------
# Core async proposal generator
# ---------------------------------------------------------------------------

async def generate_proposals(
    outcome: str,
    project_id: str,
    registry: AgentRegistry,
    max_concurrent: int,
    fresh: bool = False,
    clarifications: Optional[Dict[str, str]] = None,
    rejected_roles: Optional[List[str]] = None,
) -> dict:
    """Generate topology proposals via LLM call.

    Builds a system prompt that includes:
    - Available agent roles from the registry
    - Project max_concurrent constraint
    - Rejection context from the changelog (unless fresh=True)
    - Explicit rejected_roles block (for retry scenarios)
    - Clarification context (risk tolerance, timeline pressure)

    Strips markdown fences from the LLM response before JSON parsing.
    Validates the parsed JSON against PROPOSAL_JSON_SCHEMA.

    Args:
        outcome: Free-text outcome description from the user.
        project_id: Project identifier (for changelog lookup and graph scoping).
        registry: AgentRegistry providing available role IDs.
        max_concurrent: Maximum concurrent L3 agents (pool constraint).
        fresh: If True, skip changelog context — ignore past rejections.
        clarifications: Pre-supplied clarification answers (skips interactive input).
        rejected_roles: List of role IDs to explicitly block (retry scenario).

    Returns:
        Validated raw dict with "lean", "balanced", and "robust" keys.

    Raises:
        json.JSONDecodeError: If LLM output is not valid JSON after fence stripping.
        jsonschema.ValidationError: If parsed JSON doesn't match PROPOSAL_JSON_SCHEMA.
        httpx.HTTPStatusError: On LLM API HTTP errors (caller handles retries).
    """
    # Gather available agent role IDs
    available_roles = ", ".join(sorted(registry._agents.keys())) or "(none registered)"

    # Load rejection context
    rejection_context_str = ""
    if not fresh:
        ctx = _load_rejection_context(project_id)
        if ctx:
            rejection_context_str = ctx

    # Build explicit rejected-roles block for retry scenarios
    if rejected_roles:
        rejection_context_str += (
            f"DO NOT use these roles (previously rejected): {', '.join(rejected_roles)}\n\n"
        )

    # Build clarification context for user message
    clarification_notes = ""
    if clarifications:
        risk = clarifications.get("risk_tolerance", "medium")
        timeline = clarifications.get("timeline_pressure", "moderate")
        clarification_notes = (
            f"\nContext: risk_tolerance={risk}, timeline_pressure={timeline}"
        )

    # Build system prompt
    system_prompt = PROPOSAL_SYSTEM_PROMPT.format(
        available_roles=available_roles,
        max_concurrent=max_concurrent,
        rejection_context=rejection_context_str,
        json_schema=json.dumps(PROPOSAL_JSON_SCHEMA, separators=(",", ":")),
    )

    # Build user message
    user_message = f"Outcome description: {outcome}{clarification_notes}"

    # Call LLM
    logger.debug("Calling LLM for topology proposals (project=%s, fresh=%s)", project_id, fresh)
    raw_response = await call_llm(system_prompt, user_message)

    # Strip markdown fences and parse JSON
    clean_response = strip_markdown_fences(raw_response)
    parsed = json.loads(clean_response)

    # Validate against schema
    jsonschema.validate(parsed, PROPOSAL_JSON_SCHEMA)

    logger.debug("Generated valid proposals for project=%s", project_id)
    return parsed


# ---------------------------------------------------------------------------
# Synchronous wrapper
# ---------------------------------------------------------------------------

def generate_proposals_sync(
    outcome: str,
    project_id: str,
    registry: AgentRegistry,
    max_concurrent: int,
    fresh: bool = False,
    clarifications: Optional[Dict[str, str]] = None,
    rejected_roles: Optional[List[str]] = None,
) -> dict:
    """Synchronous wrapper around generate_proposals() using asyncio.run().

    Suitable for CLI entry points and non-async contexts.

    Args: (same as generate_proposals)

    Returns:
        Validated raw dict with "lean", "balanced", and "robust" keys.
    """
    return asyncio.run(
        generate_proposals(
            outcome=outcome,
            project_id=project_id,
            registry=registry,
            max_concurrent=max_concurrent,
            fresh=fresh,
            clarifications=clarifications,
            rejected_roles=rejected_roles,
        )
    )


# ---------------------------------------------------------------------------
# build_proposals: raw dict -> list[TopologyProposal]
# ---------------------------------------------------------------------------

def build_proposals(raw: dict, project_id: str) -> List[TopologyProposal]:
    """Convert a validated raw LLM dict into an ordered list of TopologyProposal.

    Processes archetypes in order: lean, balanced, robust.
    Each archetype's roles → TopologyNode list, hierarchy → TopologyEdge list.

    Args:
        raw: Validated dict matching PROPOSAL_JSON_SCHEMA (3 archetype keys).
        project_id: Project identifier to stamp on each TopologyGraph.

    Returns:
        List of 3 TopologyProposal objects (lean, balanced, robust).
    """
    proposals: List[TopologyProposal] = []

    for archetype_key in ("lean", "balanced", "robust"):
        entry = raw[archetype_key]

        # Build nodes
        nodes: List[TopologyNode] = []
        for role in entry.get("roles", []):
            node = TopologyNode(
                id=role["id"],
                level=int(role["level"]),
                intent=role.get("intent", ""),
                risk_level=role.get("risk_level", "medium"),
            )
            nodes.append(node)

        # Build edges — map edge_type string to EdgeType enum with fallback
        edges: List[TopologyEdge] = []
        for h in entry.get("hierarchy", []):
            edge_type_str = h.get("edge_type", "delegation")
            try:
                edge_type = EdgeType(edge_type_str)
            except ValueError:
                logger.warning(
                    "Unknown edge_type %r in archetype %r; defaulting to delegation",
                    edge_type_str,
                    archetype_key,
                )
                edge_type = EdgeType.DELEGATION

            edge = TopologyEdge(
                from_role=h["from_role"],
                to_role=h["to_role"],
                edge_type=edge_type,
            )
            edges.append(edge)

        # Build topology graph
        graph = TopologyGraph(
            nodes=nodes,
            edges=edges,
            project_id=project_id,
            metadata={"archetype": archetype_key},
        )

        proposal = TopologyProposal(
            archetype=archetype_key,
            graph=graph,
            justification=entry.get("justification", ""),
            delegation_boundaries=entry.get("delegation_boundaries", ""),
            coordination_model=entry.get("coordination_model", ""),
            risk_assessment=entry.get("risk_assessment", ""),
        )
        proposals.append(proposal)

    return proposals
