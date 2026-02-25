"""
OpenClaw Config CLI

Provides subcommands for inspecting the OpenClaw configuration.

Usage:
    openclaw-config show          # Print effective openclaw.json config
"""

import argparse
import json
import sys

from openclaw.project_config import load_and_validate_openclaw_config
from openclaw.config import get_project_root


# ANSI color codes — same as project.py and monitor.py
class Colors:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    YELLOW = '\033[93m'
    BLUE   = '\033[94m'
    RESET  = '\033[0m'
    BOLD   = '\033[1m'


def cmd_show(args: argparse.Namespace) -> int:
    """
    Print the effective openclaw.json configuration.

    Loads the config through the normal validation path — schema validation
    and agent hierarchy validation run as part of the load. If the config
    is invalid, validation errors are printed to stderr and this command
    exits non-zero before printing.

    Output format: pretty-printed JSON (indent=2) to stdout.
    """
    root = get_project_root()
    config_path = root / "openclaw.json"

    try:
        config = load_and_validate_openclaw_config()
    except FileNotFoundError:
        print(
            f"{Colors.RED}ERROR{Colors.RESET}: openclaw.json not found at {config_path}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            f"{Colors.RED}ERROR{Colors.RESET}: Failed to load config: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"# Effective config loaded from: {config_path}")
    print(json.dumps(config, indent=2, default=str))
    return 0


def main() -> None:
    """CLI entrypoint for OpenClaw Config tools."""
    parser = argparse.ArgumentParser(
        description="OpenClaw Config Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # --- show ---
    subparsers.add_parser(
        "show",
        help="Print the effective openclaw.json configuration (file values + defaults merged)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "show":
        sys.exit(cmd_show(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
