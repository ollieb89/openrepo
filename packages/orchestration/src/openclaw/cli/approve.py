"""
openclaw-approve — Resume approval for pending topology proposals.

Loads pending proposals saved by openclaw-propose (via 'quit' or session exit),
displays them, and prompts the user to select one for approval.

Usage:
    openclaw-approve
    openclaw-approve --project myproject
"""

import argparse
import sys
from typing import Optional

from openclaw.config import get_topology_config
from openclaw.project_config import get_active_project_id
from openclaw.topology.approval import approve_topology, compute_pushback_note
from openclaw.topology.proposal_models import ProposalSet, TopologyProposal
from openclaw.topology.renderer import render_full_output
from openclaw.topology.storage import load_pending_proposals


# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def _is_interactive() -> bool:
    """Return True if stdin is a TTY (interactive terminal)."""
    return sys.stdin.isatty()


# ---------------------------------------------------------------------------
# Selection helper (mirrors propose.py _parse_selection without command prefix)
# ---------------------------------------------------------------------------

def _parse_selection(
    input_str: str,
    proposal_set: ProposalSet,
) -> Optional[TopologyProposal]:
    """Parse a selection from user input like '1', 'lean', 'balanced'.

    Supports:
    - 1-based numeric index: '1' -> proposals[0]
    - Archetype name: 'lean' -> first proposal with archetype 'lean'

    Returns:
        The matching TopologyProposal, or None if not found.
    """
    token = input_str.strip().lower()

    if not token:
        return proposal_set.proposals[0] if proposal_set.proposals else None

    # Try numeric index (1-based)
    try:
        idx = int(token) - 1
        if 0 <= idx < len(proposal_set.proposals):
            return proposal_set.proposals[idx]
        return None  # Out of range
    except ValueError:
        pass

    # Try archetype name match
    for p in proposal_set.proposals:
        if p.archetype.lower() == token:
            return p

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entrypoint for the openclaw-approve command."""
    parser = argparse.ArgumentParser(
        description="openclaw-approve — approve pending topology proposals"
    )
    parser.add_argument(
        "--project",
        dest="project",
        type=str,
        default=None,
        help="Project ID (default: active project from openclaw.json)",
    )
    args = parser.parse_args()

    # --- Resolve project ---
    project_id = args.project or get_active_project_id()
    if not project_id:
        print(
            f"{Colors.RED}Error: No project ID. Use --project or set active_project"
            f" in openclaw.json{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    # --- Load pending proposals ---
    data = load_pending_proposals(project_id)
    if data is None:
        print(
            "No pending proposals found for project '{project_id}'."
            " Run 'openclaw-propose' first.".format(project_id=project_id)
        )
        return 1

    # --- Reconstruct ProposalSet ---
    proposal_set = ProposalSet.from_dict(data)

    # --- Load topology config for rendering ---
    topo_config = get_topology_config()
    threshold = topo_config["proposal_confidence_warning_threshold"]
    weights = topo_config["rubric_weights"]

    # --- Display proposals ---
    print(render_full_output(proposal_set, threshold))

    # --- Require interactive terminal ---
    if not _is_interactive():
        print(
            f"{Colors.RED}Approval requires an interactive terminal."
            f" Run 'openclaw-approve' in a TTY.{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    # --- Prompt for selection (loop until valid) ---
    n = len(proposal_set.proposals)
    prompt = f"Select proposal to approve [1-{n} or archetype name]: "

    while True:
        try:
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 1

        selected = _parse_selection(user_input, proposal_set)
        if selected is None:
            print(
                f"{Colors.RED}Invalid selection '{user_input}'."
                f" Enter a number (1-{n}) or archetype name.{Colors.RESET}"
            )
            continue
        break

    # --- Compute pushback note ---
    pushback = ""
    if selected.rubric_score:
        pushback = compute_pushback_note(
            selected.rubric_score,
            selected.topology,
            weights,
        )

    # --- Build rubric scores dict from all proposals ---
    rubric_scores = {
        p.archetype: p.rubric_score.to_dict()
        for p in proposal_set.proposals
        if p.rubric_score is not None
    } or None

    # --- Approve ---
    approve_topology(
        project_id,
        selected.topology,
        "initial",
        pushback,
        rubric_scores=rubric_scores,
    )

    if pushback:
        print(f"\n{Colors.YELLOW}{pushback}{Colors.RESET}\n")

    print(f"{Colors.GREEN}Topology approved and saved.{Colors.RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
