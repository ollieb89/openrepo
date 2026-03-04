"""
OpenClaw Structure Proposal Engine CLI

Provides the `openclaw-propose` entry point: takes an outcome description and
returns 2-3 scored topology proposals as a formatted comparative matrix.

Full pipeline:
  input -> clarify -> generate -> lint -> score -> classify -> render

When running interactively (TTY), enters a correction session loop:
  feedback -> soft correction (re-proposal with feedback)
  edit [N]  -> hard correction (export draft, wait for 'done')
  approve N -> approve the selected topology (saves to storage)
  quit      -> save pending proposals and exit

Subcommands:
  memory          -> show structural memory report for active project
  memory --detail -> show full archetype affinity and pattern breakdown

Usage:
    openclaw-propose "build a chat app"
    openclaw-propose --json "deploy ML pipeline"
    openclaw-propose --fresh --project myproj "refactor auth service"
    openclaw-propose --edit "build something"
    openclaw-propose memory
    openclaw-propose memory --detail
    echo "build a chat app" | openclaw-propose
"""

import argparse
import json
import random
import sys
from typing import Optional

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
from openclaw.topology.renderer import render_full_output, render_diff_summary
from openclaw.topology.correction import (
    CorrectionSession,
    apply_soft_correction,
    export_draft,
    import_draft,
)
from openclaw.topology.approval import approve_topology, compute_pushback_note
from openclaw.topology.storage import save_pending_proposals


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
# Selection helpers
# ---------------------------------------------------------------------------

def _parse_selection(
    input_str: str,
    proposal_set: ProposalSet,
) -> Optional[TopologyProposal]:
    """Parse a selection from user input like 'approve 1', 'edit lean', 'approve'.

    Supports:
    - 1-based numeric index: 'approve 1' -> proposals[0]
    - Archetype name: 'approve lean' -> first proposal with archetype 'lean'
    - Bare command: 'approve' -> proposals[0] (first proposal)

    Returns:
        The matching TopologyProposal, or None if index out of range.
    """
    parts = input_str.strip().lower().split()
    # Strip command prefix (approve/edit) if present
    if parts and parts[0] in ("approve", "edit"):
        parts = parts[1:]

    if not parts:
        # Bare command: return first proposal
        return proposal_set.proposals[0] if proposal_set.proposals else None

    token = parts[0]

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


def _find_original_proposal(
    session: CorrectionSession,
    archetype: str,
) -> Optional[TopologyProposal]:
    """Find the original proposal for a given archetype from session history.

    Looks first in correction_history initial state, then falls back to
    best_proposal_set.

    Returns:
        The original TopologyProposal for this archetype, or None.
    """
    # Walk correction_history to find the first proposal_set (before any correction)
    # Since we don't store the initial proposal_set in history, use best_proposal_set
    for p in session.best_proposal_set.proposals:
        if p.archetype == archetype:
            return p
    return None


# ---------------------------------------------------------------------------
# Interactive session loop
# ---------------------------------------------------------------------------

def _run_session(
    session: CorrectionSession,
    weights: dict,
    threshold: int,
    pushback_threshold: int = 8,
) -> int:
    """Run the interactive correction/approval session loop.

    Commands:
        feedback text   — soft correction (re-proposal with feedback)
        edit [N]        — hard correction (export draft, wait for done/cancel)
        approve [N]     — approve the Nth proposal
        quit            — save pending and exit 0

    At cycle limit: display best proposals, offer approve/edit only.

    Returns:
        0 on successful approval or quit, 1 on unrecoverable error.
    """
    correction_type = "initial"

    while True:
        if session.cycle_limit_reached:
            print(
                f"\n{Colors.BOLD}I've refined this {session.max_cycles} times."
                f" Here's the best I achieved:{Colors.RESET}"
            )
            print(render_full_output(session.best_proposal_set, threshold))
            prompt = "Approve [N] or edit [N]: "
        else:
            prompt = "Feedback, 'edit [N]', 'approve [N]', or 'quit': "

        try:
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            save_pending_proposals(session.project_id, session.proposal_set.to_dict())
            print("\nProposals saved. Resume with: openclaw-approve")
            return 0

        lower = user_input.lower()

        # --- Quit ---
        if lower == "quit":
            save_pending_proposals(session.project_id, session.proposal_set.to_dict())
            print("Proposals saved. Resume with: openclaw-approve")
            return 0

        # --- Approve ---
        if lower.startswith("approve"):
            selected = _parse_selection(user_input, session.proposal_set)
            if selected is None:
                print(f"{Colors.RED}Invalid selection. Use 'approve 1', 'approve lean', etc.{Colors.RESET}")
                continue

            # Compute pushback note
            pushback = ""
            if selected.rubric_score:
                original = _find_original_proposal(session, selected.archetype)
                if original and original.rubric_score:
                    pushback = compute_pushback_note(
                        original.rubric_score,
                        selected.topology,
                        weights,
                        pushback_threshold,
                    )

            entry = approve_topology(
                session.project_id,
                selected.topology,
                correction_type,
                pushback,
            )

            if pushback:
                print(f"\n{Colors.YELLOW}{pushback}{Colors.RESET}\n")
            print(f"{Colors.GREEN}Topology approved and saved.{Colors.RESET}")
            return 0

        # --- Edit (hard correction) ---
        if lower.startswith("edit"):
            selected = _parse_selection(user_input, session.proposal_set)
            if selected is None:
                selected = session.proposal_set.proposals[0]

            draft_path = export_draft(selected, session.project_id)
            print(f"Draft exported to: {draft_path}")
            print("Edit the file, then type 'done' to import or 'cancel':")

            try:
                resp = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nEdit cancelled.")
                continue

            if resp == "done":
                try:
                    graph, lint_result = import_draft(
                        session.project_id,
                        session.registry,
                        session.max_concurrent,
                    )
                except (FileNotFoundError, ValueError) as e:
                    print(f"{Colors.RED}Import error: {e}{Colors.RESET}")
                    print("Your file has been left in place. Fix the error and try again.")
                    continue

                if not lint_result.valid:
                    print(f"{Colors.RED}Blocked: {lint_result.rejected_roles}{Colors.RESET}")
                    print("Your file has been left in place.")
                    continue

                if lint_result.adjusted:
                    for adj in lint_result.adjustments:
                        print(f"{Colors.YELLOW}  Adjusted: {adj}{Colors.RESET}")

                # Show diff summary between exported proposal and imported result
                # Build a temporary proposal wrapping the imported graph for diff
                from openclaw.topology.proposal_models import TopologyProposal as _TP
                imported_proposal = _TP(
                    archetype=selected.archetype,
                    topology=graph,
                    delegation_boundaries=selected.delegation_boundaries,
                    coordination_model=selected.coordination_model,
                    risk_assessment=selected.risk_assessment,
                    justification=selected.justification,
                    rubric_score=None,
                )
                diff_summary = render_diff_summary(selected, imported_proposal)
                print(diff_summary)

                # Compute pushback and approve
                pushback = ""
                if selected.rubric_score:
                    pushback = compute_pushback_note(
                        selected.rubric_score,
                        graph,
                        weights,
                        pushback_threshold,
                    )

                entry = approve_topology(
                    session.project_id,
                    graph,
                    "hard",
                    pushback,
                )

                if pushback:
                    print(f"\n{Colors.YELLOW}{pushback}{Colors.RESET}\n")
                print(f"{Colors.GREEN}Edited topology approved.{Colors.RESET}")
                return 0
            else:
                print("Edit cancelled.")
                continue

        # --- Feedback (soft correction) ---
        if session.cycle_limit_reached:
            print(
                f"{Colors.YELLOW}Cycle limit reached."
                f" Use 'approve [N]' or 'edit [N]'.{Colors.RESET}"
            )
            continue

        if not user_input:
            continue

        old_proposals = session.proposal_set
        try:
            new_set = apply_soft_correction(session, user_input, weights)
        except ValueError as e:
            print(f"{Colors.RED}Re-proposal error: {e}{Colors.RESET}")
            continue
        except Exception as e:
            print(f"{Colors.RED}Re-proposal error: {e}{Colors.RESET}")
            continue

        correction_type = "soft"

        # Show diff for each archetype pair
        for old_p in old_proposals.proposals:
            for new_p in new_set.proposals:
                if old_p.archetype == new_p.archetype:
                    print(render_diff_summary(old_p, new_p))

        # Show full updated output
        print(render_full_output(new_set, threshold))
        save_pending_proposals(session.project_id, new_set.to_dict())

    return 0  # Unreachable but satisfies type checker


# ---------------------------------------------------------------------------
# Memory report subcommand
# ---------------------------------------------------------------------------

def _run_memory_report(args: list) -> int:
    """Run the structural memory report for the active project.

    Usage:
        openclaw-propose memory [--project ID] [--detail]

    Shows correction count, threshold status, archetype affinity, and top patterns.
    Use --detail for full archetype affinity and pattern confidence breakdown.

    Returns:
        0 on success, 1 on error.
    """
    detail = "--detail" in args

    # Parse --project if present
    project_id = None
    for i, arg in enumerate(args):
        if arg == "--project" and i + 1 < len(args):
            project_id = args[i + 1]
            break

    if not project_id:
        project_id = get_active_project_id()
    if not project_id:
        print(
            f"{Colors.RED}Error: No project ID. Use --project or set active_project{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    from openclaw.topology.memory import MemoryProfiler, PatternExtractor
    from openclaw.config import get_topology_config

    topo_config = get_topology_config()
    profiler = MemoryProfiler(
        project_id,
        decay_lambda=topo_config["decay_lambda"],
        exploration_rate=topo_config["exploration_rate"],
        min_threshold=topo_config["pattern_extraction_threshold"],
    )
    report = profiler.get_report(detail=detail)

    # Compact output
    print(f"\n{Colors.BOLD}Structural Memory: {project_id}{Colors.RESET}")
    print(
        f"  Corrections: {report['correction_count']} total"
        f" ({report.get('soft_correction_count', 0)} soft,"
        f" {report.get('hard_correction_count', 0)} hard)"
    )
    status = report.get("threshold_status", "below_threshold")
    status_color = Colors.GREEN if status == "active" else Colors.YELLOW
    print(f"  Profile: {status_color}{status}{Colors.RESET}")

    # Archetype affinity (only shown when profile is active)
    affinities = report.get("archetype_affinity", {})
    if affinities and status == "active":
        print(f"\n  {Colors.BOLD}Archetype Affinity:{Colors.RESET}")
        for arch in ("lean", "balanced", "robust"):
            val = affinities.get(arch, 5.0)
            bar = "#" * round(val)
            print(f"    {arch:>10}: {val:4.1f} {bar}")

    # Top patterns
    patterns = report.get("top_patterns", report.get("patterns", []))
    if patterns:
        print(f"\n  {Colors.BOLD}Top Patterns:{Colors.RESET}")
        for p in patterns[:3]:
            conf = p.get("confidence", 0)
            print(f"    - {p.get('pattern', '?')} (confidence: {conf:.2f})")
    elif status == "below_threshold":
        threshold = topo_config.get("pattern_extraction_threshold", 5)
        remaining = threshold - report["correction_count"]
        print(
            f"\n  {Colors.YELLOW}Not enough data yet."
            f" {remaining} more correction(s) needed for pattern extraction.{Colors.RESET}"
        )

    # Detail mode: full breakdown
    if detail and status == "active":
        all_patterns = report.get("all_patterns", patterns)
        if all_patterns:
            print(f"\n  {Colors.BOLD}Full Pattern List:{Colors.RESET}")
            for p in all_patterns:
                print(f"    - {p.get('pattern', '?')}")
                print(
                    f"      confidence: {p.get('confidence', 0):.2f}"
                    f"  bias: {p.get('archetype_bias', 'none')}"
                    f"  sources: {len(p.get('source_correction_ids', []))}"
                )

    print()
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entrypoint for the OpenClaw Structure Proposal Engine."""
    # Quick subcommand detection — memory report bypasses proposal generation
    if len(sys.argv) > 1 and sys.argv[1] == "memory":
        return _run_memory_report(sys.argv[2:])

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
    parser.add_argument(
        "--edit",
        dest="edit",
        action="store_true",
        help="Launch $EDITOR on the first proposal draft immediately after generation",
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
    # Draw a single epsilon-greedy explore flag at session level (not per proposal)
    explore = random.random() < topo_config.get("exploration_rate", 0.20)
    for p in proposals:
        p.rubric_score = score_proposal(
            p.topology, weights,
            project_id=project_id, archetype=p.archetype, explore=explore,
        )

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
        return 0

    output = render_full_output(proposal_set, threshold)
    print(output)

    # --- Non-interactive: exit immediately ---
    if not interactive:
        return 0

    # --- Interactive: create session and enter loop ---
    session = CorrectionSession(
        outcome=outcome,
        project_id=project_id,
        proposal_set=proposal_set,
        best_proposal_set=proposal_set,
        clarifications=clarifications,
        registry=registry,
        max_concurrent=max_concurrent,
    )

    # Save proposals for session persistence (openclaw-approve resume)
    save_pending_proposals(project_id, proposal_set.to_dict())

    # Handle --edit flag: immediately launch hard correction on first proposal
    if args.edit:
        selected = proposal_set.proposals[0] if proposal_set.proposals else None
        if selected:
            draft_path = export_draft(selected, project_id)
            import subprocess
            import os
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(draft_path)])
            # After editor exits, continue session loop normally
            # (user can type 'done' to import or 'quit')

    return _run_session(session, weights, threshold)


if __name__ == "__main__":
    sys.exit(main())
