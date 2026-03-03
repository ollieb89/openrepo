"""
OpenClaw Structure Proposal Engine CLI

Provides the `openclaw-propose` entry point: takes an outcome description and
returns 2-3 scored topology proposals as a formatted comparative matrix.

Full pipeline:
  input -> clarify -> generate -> lint -> score -> classify -> render

Usage:
    openclaw-propose "build a chat app"
    openclaw-propose --json "deploy ML pipeline"
    openclaw-propose --fresh --project myproj "refactor auth service"
    echo "build a chat app" | openclaw-propose
"""

import argparse
import json
import sys

from openclaw.config import get_project_root, get_topology_config
from openclaw.project_config import get_active_project_id
from openclaw.agent_registry import AgentRegistry
from openclaw.topology.proposer import (
    generate_proposals_sync,
    build_proposals as _build_proposer_proposals,
    ask_clarifications,
)
from openclaw.topology.linter import ConstraintLinter, MAX_RETRIES
from openclaw.topology.rubric import score_proposal, find_key_differentiators
from openclaw.topology.classifier import ArchetypeClassifier
from openclaw.topology.proposal_models import TopologyProposal, ProposalSet
from openclaw.topology.renderer import render_full_output


# ---------------------------------------------------------------------------
# ANSI colors — same pattern as project.py and monitor.py
# ---------------------------------------------------------------------------

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def _is_interactive() -> bool:
    """Return True if stdin is a TTY (interactive terminal)."""
    return sys.stdin.isatty()


# ---------------------------------------------------------------------------
# Conversion: proposer.TopologyProposal -> proposal_models.TopologyProposal
# ---------------------------------------------------------------------------

def _to_pm_proposals(proposer_proposals: list) -> list:
    """Convert proposer.TopologyProposal objects to proposal_models.TopologyProposal.

    proposer.TopologyProposal uses `.graph` (TopologyGraph), while
    proposal_models.TopologyProposal uses `.topology`. The conversion maps
    the graph field and pulls over all qualitative fields.

    Returns:
        List of proposal_models.TopologyProposal objects.
    """
    pm_proposals = []
    for pp in proposer_proposals:
        pm = TopologyProposal(
            archetype=pp.archetype,
            topology=pp.graph,
            delegation_boundaries=pp.delegation_boundaries,
            coordination_model=pp.coordination_model,
            risk_assessment=pp.risk_assessment,
            justification=pp.justification,
        )
        pm_proposals.append(pm)
    return pm_proposals


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entrypoint for the OpenClaw Structure Proposal Engine."""
    parser = argparse.ArgumentParser(
        description="OpenClaw Structure Proposal Engine — generates scored topology proposals"
    )
    parser.add_argument(
        "outcome",
        nargs="?",
        help="Outcome description (reads from stdin if not provided)",
    )
    parser.add_argument(
        "--project",
        dest="project",
        type=str,
        default=None,
        help="Project ID (default: active project from openclaw.json)",
    )
    parser.add_argument(
        "--fresh",
        dest="fresh",
        action="store_true",
        help="Generate without changelog history influence (skip past rejections)",
    )
    parser.add_argument(
        "--json",
        dest="json",
        action="store_true",
        help="Output raw JSON instead of formatted terminal table",
    )
    args = parser.parse_args()

    # --- Resolve outcome ---
    outcome = args.outcome
    if not outcome:
        if _is_interactive():
            print(f"{Colors.BOLD}Describe the outcome:{Colors.RESET}")
            outcome = input("> ").strip()
        else:
            outcome = sys.stdin.read().strip()

    if not outcome:
        print(
            f"{Colors.RED}Error: No outcome description provided{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    # --- Resolve project ---
    project_id = args.project or get_active_project_id()
    if not project_id:
        print(
            f"{Colors.RED}Error: No project ID. Use --project or set active_project in openclaw.json{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    # --- Load registry and topology config ---
    root = get_project_root()
    registry = AgentRegistry(root)
    topo_config = get_topology_config()
    threshold = topo_config["proposal_confidence_warning_threshold"]
    weights = topo_config["rubric_weights"]

    # Determine max_concurrent: use first L2 agent's max_concurrent, or default 3
    max_concurrent = 3
    for spec in registry._agents.values():
        if spec.level == 2:
            max_concurrent = spec.max_concurrent
            break

    # --- Clarifying questions ---
    interactive = _is_interactive()
    clarifications = ask_clarifications(interactive)

    # --- Generate -> Lint -> Retry loop ---
    attempt = 0
    rejected_roles_acc = []
    raw = None

    while attempt <= MAX_RETRIES:
        try:
            raw = generate_proposals_sync(
                outcome=outcome,
                project_id=project_id,
                registry=registry,
                max_concurrent=max_concurrent,
                fresh=args.fresh,
                clarifications=clarifications,
                rejected_roles=rejected_roles_acc or None,
            )
        except Exception as e:
            print(f"{Colors.RED}LLM error: {e}{Colors.RESET}", file=sys.stderr)
            return 1

        # Lint each archetype
        linter = ConstraintLinter(registry, max_concurrent)
        all_valid = True
        for arch_key in ("lean", "balanced", "robust"):
            if arch_key not in raw:
                continue
            result = linter.lint(arch_key, raw[arch_key])
            if not result.valid:
                all_valid = False
                rejected_roles_acc.extend(result.rejected_roles)
                print(
                    f"{Colors.YELLOW}Retry {attempt + 1}: {arch_key} rejected roles:"
                    f" {result.rejected_roles}{Colors.RESET}",
                    file=sys.stderr,
                )
            elif result.adjusted:
                raw[arch_key] = result.proposal
                for adj in result.adjustments:
                    print(f"{Colors.YELLOW}  {adj}{Colors.RESET}", file=sys.stderr)

        if all_valid:
            break
        attempt += 1

    if raw is None:
        print(
            f"{Colors.RED}Failed to generate proposals after {MAX_RETRIES + 1} attempts{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    # --- Build proposals (proposer format) and convert to proposal_models format ---
    proposer_proposals = _build_proposer_proposals(raw, project_id)
    proposals = _to_pm_proposals(proposer_proposals)

    # --- Score each proposal ---
    for p in proposals:
        p.rubric_score = score_proposal(p.topology, weights)

    # --- Find key differentiators ---
    scores = [p.rubric_score for p in proposals if p.rubric_score]
    key_diffs = find_key_differentiators(scores) if len(scores) > 1 else []
    for p in proposals:
        if p.rubric_score:
            p.rubric_score.key_differentiators = key_diffs

    # --- Verify archetype classification ---
    classifier = ArchetypeClassifier()
    for p in proposals:
        result = classifier.classify(p.topology)
        if result.archetype != p.archetype:
            print(
                f"{Colors.YELLOW}Note: {p.archetype} proposal classified as"
                f" {result.archetype} by structural analysis{Colors.RESET}",
                file=sys.stderr,
            )

    # --- Sort by overall confidence descending ---
    proposals.sort(
        key=lambda p: (p.rubric_score.overall_confidence if p.rubric_score else 0),
        reverse=True,
    )

    # --- Build ProposalSet ---
    assumptions = []
    for k, v in clarifications.items():
        assumptions.append(f"{k.replace('_', ' ').title()}: {v}")

    proposal_set = ProposalSet(
        proposals=proposals,
        assumptions=assumptions,
        outcome=outcome,
    )

    # --- Output ---
    if args.json:
        print(json.dumps(proposal_set.to_dict(), indent=2))
    else:
        output = render_full_output(proposal_set, threshold)
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
