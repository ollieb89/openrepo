"""
Topology Proposal Terminal Renderer

Renders topology proposals as ASCII DAGs and comparative matrices for display
in the terminal. Handles narrow terminals by switching to stacked layout.

Public API:
  render_dag(topology)                   — ASCII DAG of a single topology
  render_matrix(proposals, key_diffs)    — Comparative matrix table
  render_assumptions(assumptions)        — Formatted assumptions block
  render_justifications(proposals)       — Per-archetype justification text
  render_low_confidence_warning(...)     — Warning block when confidence < threshold
  render_full_output(proposal_set, ...)  — Complete terminal output (combines all)
"""

import shutil
import textwrap
from typing import List, Optional

from .diff import topology_diff
from .models import EdgeType, TopologyGraph
from .proposal_models import ProposalSet, RubricScore, TopologyProposal


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NARROW_TERMINAL_THRESHOLD = 100

# Human-readable dimension labels mapped from rubric field names
DIMENSION_LABELS = {
    "complexity":            "Complexity",
    "coordination_overhead": "Coordination Overhead",
    "risk_containment":      "Risk Containment",
    "time_to_first_output":  "Time To First Output",
    "cost_estimate":         "Cost Estimate",
    "preference_fit":        "Preference Fit",
}

DIMENSIONS_ORDER = list(DIMENSION_LABELS.keys())


# ANSI color codes for diff summary (green=improvement, red=regression)
_C_GREEN = '\033[92m'
_C_RED = '\033[91m'
_C_YELLOW = '\033[93m'
_C_RESET = '\033[0m'
_C_BOLD = '\033[1m'


# ---------------------------------------------------------------------------
# Diff summary renderer
# ---------------------------------------------------------------------------

def render_diff_summary(
    old_proposal: TopologyProposal,
    new_proposal: TopologyProposal,
) -> str:
    """
    Render a compact summary of structural changes between two proposals.

    Shows node/edge delta counts and rubric score changes (colored by direction).

    Args:
        old_proposal: The original TopologyProposal.
        new_proposal: The updated TopologyProposal after soft/hard correction.

    Returns:
        Multi-line string with diff summary for terminal display.
    """
    diff = topology_diff(old_proposal.topology, new_proposal.topology)

    # Node/edge change counts
    added_n = len(diff.added_nodes)
    removed_n = len(diff.removed_nodes)
    modified_n = len(diff.modified_nodes)
    added_e = len(diff.added_edges)
    removed_e = len(diff.removed_edges)
    modified_e = len(diff.modified_edges)

    archetype = new_proposal.archetype.upper()
    lines = [f"  {_C_BOLD}[{archetype}] Changes:{_C_RESET}"]
    lines.append(
        f"    Nodes: {_C_GREEN}+{added_n}{_C_RESET} {_C_RED}-{removed_n}{_C_RESET} ~{modified_n}  "
        f"Edges: {_C_GREEN}+{added_e}{_C_RESET} {_C_RED}-{removed_e}{_C_RESET} ~{modified_e}"
    )

    # Score deltas (if both proposals have rubric scores)
    if old_proposal.rubric_score and new_proposal.rubric_score:
        old_s = old_proposal.rubric_score
        new_s = new_proposal.rubric_score
        score_parts = []
        for dim in DIMENSIONS_ORDER:
            old_val = getattr(old_s, dim)
            new_val = getattr(new_s, dim)
            delta = new_val - old_val
            if delta == 0:
                continue
            label = DIMENSION_LABELS.get(dim, dim)
            if delta > 0:
                score_parts.append(f"{_C_GREEN}{label}: {old_val}->{new_val}{_C_RESET}")
            else:
                score_parts.append(f"{_C_RED}{label}: {old_val}->{new_val}{_C_RESET}")
        if score_parts:
            lines.append("    Scores: " + ", ".join(score_parts))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ASCII DAG renderer
# ---------------------------------------------------------------------------

def render_dag(topology: TopologyGraph) -> str:
    """
    Render a topology graph as an ASCII DAG.

    Finds root nodes (no incoming delegation edges), then DFS from each root.
    Children are indented with edge type labels.

    Example output:
        [clawdia_prime]
          -(delegation)-> [pumplai_pm]
              -(delegation)-> [l3_specialist_a]
              -(coordination)-> [l3_specialist_b]
          -(review_gate)-> [docs_pm]

    Args:
        topology: TopologyGraph to visualize.

    Returns:
        Multi-line ASCII string.
    """
    if not topology.nodes:
        return ""

    # Build adjacency map: node_id -> list of (to_role, edge_type_str)
    adj: dict = {n.id: [] for n in topology.nodes}
    incoming: set = set()  # nodes that have incoming delegation edges

    for edge in topology.edges:
        adj.setdefault(edge.from_role, []).append(
            (edge.to_role, edge.edge_type.value)
        )
        incoming.add(edge.to_role)

    # Find root nodes: nodes with no incoming edges of any type
    all_targets: set = set()
    for edge in topology.edges:
        all_targets.add(edge.to_role)

    all_node_ids = {n.id for n in topology.nodes}
    root_ids = [nid for nid in all_node_ids if nid not in all_targets]

    # If every node is a target (cycle or fully connected), pick first node
    if not root_ids:
        root_ids = [topology.nodes[0].id]

    # DFS render
    lines: List[str] = []
    visited: set = set()

    def _dfs(node_id: str, depth: int, indent_prefix: str) -> None:
        visited.add(node_id)
        if depth == 0:
            lines.append(f"[{node_id}]")
        # Render children
        children = adj.get(node_id, [])
        for to_role, edge_type in children:
            child_indent = "  " * (depth + 1)
            arrow = f"{child_indent}-({edge_type})-> [{to_role}]"
            lines.append(arrow)
            if to_role not in visited:
                _dfs(to_role, depth + 1, child_indent)

    for root_id in sorted(root_ids):
        _dfs(root_id, 0, "")

    # Render any nodes not reached (isolated nodes)
    for node in topology.nodes:
        if node.id not in visited:
            lines.append(f"[{node.id}]")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Comparative matrix renderer
# ---------------------------------------------------------------------------

def render_matrix(
    proposals: List[TopologyProposal],
    key_differentiators: List[str],
) -> str:
    """
    Render a comparative matrix table for the given proposals.

    Uses terminal width detection:
    - width >= 100: side-by-side table with box-drawing characters
    - width < 100: stacked layout (one archetype block per section)

    Key differentiator dimensions are marked with *.
    Preference fit cells get ~ suffix (no correction history yet).

    Args:
        proposals: List of TopologyProposal objects (typically 3).
        key_differentiators: List of dimension names to mark with *.

    Returns:
        Multi-line ASCII table string.
    """
    if not proposals:
        return ""

    terminal_cols = shutil.get_terminal_size(fallback=(80, 24)).columns

    if terminal_cols >= NARROW_TERMINAL_THRESHOLD:
        return _render_matrix_wide(proposals, key_differentiators)
    else:
        return _render_matrix_stacked(proposals, key_differentiators)


def _cell_value(score: RubricScore, dim: str, key_differentiators: List[str]) -> str:
    """Format a single cell value with optional * and ~ markers."""
    val = getattr(score, dim, "?")
    cell = f"{val}/10"
    if dim == "preference_fit":
        cell += " ~"
    if dim in key_differentiators:
        cell += " *"
    return cell


def _render_matrix_wide(
    proposals: List[TopologyProposal],
    key_differentiators: List[str],
) -> str:
    """Render a side-by-side matrix with box-drawing characters."""
    col_width = 14
    dim_col_width = 24

    # Column headers
    headers = ["Dimension"] + [p.archetype.title() for p in proposals]
    widths = [dim_col_width] + [col_width] * len(proposals)

    def _pad(text: str, width: int) -> str:
        return text[:width].ljust(width)

    def _border_top() -> str:
        parts = ["╔" + "═" * widths[0]]
        for w in widths[1:]:
            parts.append("╦" + "═" * w)
        return "".join(parts) + "╗"

    def _border_mid() -> str:
        parts = ["╠" + "═" * widths[0]]
        for w in widths[1:]:
            parts.append("╬" + "═" * w)
        return "".join(parts) + "╣"

    def _border_bot() -> str:
        parts = ["╚" + "═" * widths[0]]
        for w in widths[1:]:
            parts.append("╩" + "═" * w)
        return "".join(parts) + "╝"

    def _row(cells: List[str]) -> str:
        parts = ["║" + _pad(cells[0], widths[0])]
        for i, cell in enumerate(cells[1:], 1):
            parts.append("║" + _pad(cell, widths[i]))
        return "".join(parts) + "║"

    lines: List[str] = []
    lines.append(_border_top())
    lines.append(_row(headers))
    lines.append(_border_mid())

    for dim in DIMENSIONS_ORDER:
        label = DIMENSION_LABELS[dim]
        if dim in key_differentiators:
            label += " *"
        cells = [label]
        for p in proposals:
            if p.rubric_score:
                cells.append(_cell_value(p.rubric_score, dim, key_differentiators))
            else:
                cells.append("—")
        lines.append(_row(cells))

    # Overall confidence row
    cells = ["Overall Confidence"]
    for p in proposals:
        if p.rubric_score:
            cells.append(f"{p.rubric_score.overall_confidence}/10")
        else:
            cells.append("—")
    lines.append(_border_mid())
    lines.append(_row(cells))

    lines.append(_border_bot())
    lines.append("* = key differentiator  ~ = no correction history yet")

    return "\n".join(lines)


def _render_matrix_stacked(
    proposals: List[TopologyProposal],
    key_differentiators: List[str],
) -> str:
    """Render stacked layout — one archetype block per section."""
    lines: List[str] = []

    for p in proposals:
        lines.append(f"--- {p.archetype.upper()} ---")
        if p.rubric_score:
            for dim in DIMENSIONS_ORDER:
                label = DIMENSION_LABELS[dim]
                cell = _cell_value(p.rubric_score, dim, key_differentiators)
                lines.append(f"  {label}: {cell}")
            lines.append(f"  Overall Confidence: {p.rubric_score.overall_confidence}/10")
        else:
            lines.append("  (no score available)")
        lines.append("")

    lines.append("* = key differentiator  ~ = no correction history yet")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Assumptions renderer
# ---------------------------------------------------------------------------

def render_assumptions(assumptions: List[str]) -> str:
    """
    Render the assumptions block above the proposals.

    Format:
        ASSUMPTIONS
          - Risk tolerance: medium (from clarifying answers)
          - Timeline pressure: moderate (default — not specified)

    Args:
        assumptions: List of assumption strings.

    Returns:
        Formatted multi-line string.
    """
    if not assumptions:
        return "ASSUMPTIONS\n  (none)\n"

    lines = ["ASSUMPTIONS"]
    for assumption in assumptions:
        lines.append(f"  - {assumption}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Justifications renderer
# ---------------------------------------------------------------------------

def render_justifications(proposals: List[TopologyProposal]) -> str:
    """
    Render full justification text for each archetype.

    Args:
        proposals: List of TopologyProposal objects.

    Returns:
        Multi-line string with per-archetype justifications.
    """
    if not proposals:
        return ""

    lines = ["JUSTIFICATIONS"]
    for p in proposals:
        lines.append(f"\n  {p.archetype.upper()}")
        wrapped = textwrap.fill(p.justification, width=72, initial_indent="    ", subsequent_indent="    ")
        lines.append(wrapped)
        if p.delegation_boundaries:
            lines.append(f"    Delegation: {p.delegation_boundaries}")
        if p.coordination_model:
            lines.append(f"    Coordination: {p.coordination_model}")
        if p.risk_assessment:
            lines.append(f"    Risk: {p.risk_assessment}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Low confidence warning
# ---------------------------------------------------------------------------

def render_low_confidence_warning(
    proposals: List[TopologyProposal],
    threshold: int,
) -> str:
    """
    Emit a warning if any proposal's overall_confidence is below threshold.

    Args:
        proposals: List of TopologyProposal objects with rubric scores.
        threshold: Minimum acceptable confidence level (from config).

    Returns:
        Warning string if any proposal is below threshold; empty string otherwise.
    """
    low = [
        p for p in proposals
        if p.rubric_score and p.rubric_score.overall_confidence < threshold
    ]
    if not low:
        return ""

    return (
        "\n⚠ Low confidence — consider simplifying the outcome or adding constraints."
    )


# ---------------------------------------------------------------------------
# Full output combinator
# ---------------------------------------------------------------------------

def render_full_output(proposal_set: ProposalSet, threshold: int) -> str:
    """
    Combine all rendering sections into complete terminal output.

    Order: assumptions → comparative matrix → ASCII DAGs → justifications → warning

    Args:
        proposal_set: ProposalSet with proposals (pre-sorted by caller).
        threshold: Confidence warning threshold from topology config.

    Returns:
        Complete formatted terminal output string.
    """
    sections: List[str] = []

    # 1. Outcome
    sections.append(f"OUTCOME: {proposal_set.outcome}\n")

    # 2. Assumptions
    if proposal_set.assumptions:
        sections.append(render_assumptions(proposal_set.assumptions))

    # 3. Comparative matrix
    proposals = proposal_set.proposals
    if proposals:
        key_diffs: List[str] = []
        if proposals[0].rubric_score:
            key_diffs = proposals[0].rubric_score.key_differentiators
        sections.append(render_matrix(proposals, key_diffs))
        sections.append("")

    # 4. ASCII DAGs (one per proposal)
    if proposals:
        sections.append("TOPOLOGY DIAGRAMS")
        for p in proposals:
            sections.append(f"\n  {p.archetype.upper()}:")
            dag = render_dag(p.topology)
            indented = "\n".join("    " + line for line in dag.splitlines())
            sections.append(indented)
        sections.append("")

    # 5. Justifications
    if proposals:
        sections.append(render_justifications(proposals))
        sections.append("")

    # 6. Low confidence warning
    if proposals:
        warning = render_low_confidence_warning(proposals, threshold)
        if warning:
            sections.append(warning)

    return "\n".join(sections)
