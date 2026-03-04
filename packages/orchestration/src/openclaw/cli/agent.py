"""
OpenClaw Agent CLI

Provides subcommands for listing and inspecting registered agents.

Usage:
    openclaw-agent list
    openclaw-agent list --json
"""

import argparse
import json
import sys
from typing import List

from openclaw.config import get_agent_registry
from openclaw.agent_registry import AgentLevel, AgentSpec


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


_SOURCE_STATUS = {
    "both":          "ok",
    "agents_dir":    "new",
    "openclaw_json": "orphan",
    "unknown":       "?",
}

_LEVEL_LABELS = {
    AgentLevel.L1: "L1  Strategic Orchestrators",
    AgentLevel.L2: "L2  Project Managers",
    AgentLevel.L3: "L3  Specialists",
}


def _format_table(agents: List[AgentSpec]) -> str:
    """Render agents grouped by level as a plain-text table."""
    lines = []
    header = f"{'ID':<25} {'NAME':<30} {'REPORTS TO':<20} {'STATUS'}"
    separator = "-" * 85

    current_level = None
    for spec in agents:  # already sorted by (level, id) from all_agents()
        if spec.level != current_level:
            current_level = spec.level
            lines.append("")
            lines.append(f"{Colors.BOLD}{_LEVEL_LABELS.get(spec.level, str(spec.level))}{Colors.RESET}")
            lines.append(f"{Colors.BOLD}{header}{Colors.RESET}")
            lines.append(separator)

        status_raw = _SOURCE_STATUS.get(spec.source, "?")
        if status_raw == "ok":
            status = f"{Colors.GREEN}{status_raw}{Colors.RESET}"
        elif status_raw == "orphan":
            status = f"{Colors.YELLOW}{status_raw}{Colors.RESET}"
        elif status_raw == "new":
            status = f"{Colors.BLUE}{status_raw}{Colors.RESET}"
        else:
            status = status_raw

        reports = spec.reports_to or "--"
        lines.append(f"{spec.id:<25} {spec.name:<30} {reports:<20} {status}")

    return "\n".join(lines)


def cmd_list(args: argparse.Namespace) -> int:
    """List all registered agents (AREG-02)."""
    try:
        registry = get_agent_registry()
    except Exception as e:
        print(f"Error loading agent registry: {e}", file=sys.stderr)
        return 1

    agents = registry.all_agents()

    if not agents:
        print("No agents found.")
        return 0

    if args.json:
        output = [
            {
                "id": a.id,
                "name": a.name,
                "level": int(a.level),
                "reports_to": a.reports_to,
                "source": a.source,
            }
            for a in agents
        ]
        print(json.dumps(output, indent=2))
        return 0

    print(_format_table(agents))
    return 0


def main(argv=None) -> int:
    """CLI entrypoint for OpenClaw Agent commands."""
    parser = argparse.ArgumentParser(
        description="OpenClaw Agent Registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List all registered agents")
    list_parser.add_argument(
        "--json",
        dest="json",
        action="store_true",
        help="Output as JSON array",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "list":
        return cmd_list(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
