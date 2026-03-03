"""
Topology Approval Module

Provides the approval workflow for topology confirmation:
  - approve_topology: atomically saves approved topology and appends changelog entry
  - compute_pushback_note: returns informational note when approved graph scores
    significantly lower than the original proposal on key dimensions
  - check_approval_gate: guards downstream operations requiring an approved topology

Requirements: CORR-04 (approve_topology), CORR-06 (pushback), CORR-07 (gate check).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from openclaw.topology.diff import topology_diff
from openclaw.topology.models import TopologyGraph
from openclaw.topology.proposal_models import RubricScore
from openclaw.topology.rubric import score_proposal
from openclaw.topology.storage import (
    append_changelog,
    delete_pending_proposals,
    load_topology,
    save_topology,
)

logger = logging.getLogger(__name__)

# Scoring dimensions that compute_pushback_note checks for significant drops
_PUSHBACK_DIMENSIONS = [
    "complexity",
    "coordination_overhead",
    "risk_containment",
    "time_to_first_output",
    "cost_estimate",
]


# ---------------------------------------------------------------------------
# approve_topology
# ---------------------------------------------------------------------------

def approve_topology(
    project_id: str,
    approved_graph: TopologyGraph,
    correction_type: str,
    pushback_note: str = "",
) -> dict:
    """
    Atomically save an approved topology and append a changelog entry.

    Steps:
    1. Load previous topology (for diff computation).
    2. Compute topology_diff if previous exists, else None.
    3. Build changelog entry dict with timestamp, correction_type, diff, annotations.
    4. Call save_topology then append_changelog.
    5. Delete pending-proposals.json (cleanup after approval).
    6. Return the changelog entry dict.

    Args:
        project_id: The project identifier.
        approved_graph: The topology graph the user approved.
        correction_type: "soft", "hard", "initial", etc. — recorded in changelog.
        pushback_note: Optional informational note about the original proposal scoring
                       higher (from compute_pushback_note). If non-empty, included
                       in entry["annotations"]["pushback_note"].

    Returns:
        The changelog entry dict that was appended.
    """
    # Load previous topology for diff
    previous = load_topology(project_id)

    # Compute diff if previous exists
    diff_dict = None
    if previous is not None:
        diff = topology_diff(previous, approved_graph)
        diff_dict = diff.to_dict()
        logger.debug(
            "Computed topology diff for project=%s: %s",
            project_id,
            diff.summary,
        )
    else:
        logger.debug("No previous topology for project=%s — first approval", project_id)

    # Build changelog entry
    timestamp = datetime.now(timezone.utc).isoformat()
    annotations: dict = {}
    if pushback_note:
        annotations["pushback_note"] = pushback_note

    entry = {
        "timestamp": timestamp,
        "correction_type": correction_type,
        "diff": diff_dict,
        "annotations": annotations,
    }

    # Persist approved topology atomically
    save_topology(project_id, approved_graph)

    # Append changelog entry
    append_changelog(project_id, entry)

    # Clean up pending proposals (approval completed)
    delete_pending_proposals(project_id)

    logger.info(
        "Topology approved for project=%s (correction_type=%s)",
        project_id,
        correction_type,
    )

    return entry


# ---------------------------------------------------------------------------
# compute_pushback_note
# ---------------------------------------------------------------------------

def compute_pushback_note(
    original_score: RubricScore,
    approved_graph: TopologyGraph,
    weights: dict,
    pushback_threshold: int = 8,
) -> str:
    """
    Return an informational note when the approved graph scores significantly
    lower than the original proposal on key dimensions.

    Never raises. Returns empty string if:
    - original overall_confidence < pushback_threshold (original was not highly confident)
    - No dimension drops by >= 2 points between original and approved scores

    Args:
        original_score: The RubricScore for the original (LLM-proposed) topology.
        approved_graph: The topology the user chose to approve.
        weights: Rubric scoring weights (dict of dimension -> float).
        pushback_threshold: Minimum original overall_confidence to trigger pushback (default 8).

    Returns:
        Informational string describing significant score drops, or "" if no note needed.
    """
    try:
        # If original was not highly confident, no pushback needed
        if original_score.overall_confidence < pushback_threshold:
            return ""

        # Score the approved graph
        approved_score = score_proposal(approved_graph, weights)

        # Compare each dimension — flag drops of >= 2
        dimension_notes = []
        for dim in _PUSHBACK_DIMENSIONS:
            original_val = getattr(original_score, dim)
            approved_val = getattr(approved_score, dim)
            drop = original_val - approved_val
            if drop >= 2:
                dimension_notes.append(
                    f"{dim} ({original_val} -> {approved_val})"
                )

        if not dimension_notes:
            return ""

        joined = ", ".join(dimension_notes)
        return (
            f"Note: My original proposal scored higher on {joined}. "
            "This is informational only — it does not block execution."
        )

    except Exception as exc:
        # compute_pushback_note must never raise
        logger.warning("compute_pushback_note failed (returning empty): %s", exc)
        return ""


# ---------------------------------------------------------------------------
# check_approval_gate
# ---------------------------------------------------------------------------

def check_approval_gate(
    project_id: str,
    auto_approve_l1: bool = False,
) -> dict:
    """
    Check whether an approved topology exists for the given project.

    Used to gate downstream operations (spawning L3, running tasks) that
    require a topology to have been approved first.

    Args:
        project_id: The project identifier.
        auto_approve_l1: If True, bypass the gate check and return approved=True
                         without loading from disk. Intended for L1-level automation.

    Returns:
        {"approved": True} if gate passes.
        {"approved": False, "reason": str} if gate fails.
    """
    if auto_approve_l1:
        logger.debug("Approval gate bypassed via auto_approve_l1 for project=%s", project_id)
        return {"approved": True}

    existing = load_topology(project_id)

    if existing is not None:
        logger.debug("Approval gate passed for project=%s (topology exists)", project_id)
        return {"approved": True}

    reason = (
        f"No approved topology for project '{project_id}'. "
        "Run 'openclaw-propose' to generate and approve a topology."
    )
    logger.debug("Approval gate blocked for project=%s: %s", project_id, reason)
    return {"approved": False, "reason": reason}
