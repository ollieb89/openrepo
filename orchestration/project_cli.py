"""
OpenClaw Project Manager CLI

Provides subcommands for managing OpenClaw projects without hand-editing JSON files.
Consistent with monitor.py and spawn.py patterns.

Usage:
    python3 orchestration/project_cli.py init --id myproj --name "My Project"
    python3 orchestration/project_cli.py list
    python3 orchestration/project_cli.py switch <project_id>
    python3 orchestration/project_cli.py remove <project_id> [--force]
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Handle both module import and direct execution
try:
    from .project_config import _find_project_root, get_active_project_id
except ImportError:
    # Direct execution — add parent dir to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestration.project_config import _find_project_root, get_active_project_id


# ANSI color codes — same as monitor.py and init.py
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_interactive() -> bool:
    """Return True if stdin is a TTY (interactive terminal)."""
    return sys.stdin.isatty()


def _validate_project_id(project_id: str) -> None:
    """
    Validate project ID format.

    Must match ^[a-zA-Z0-9-]{1,20}$ — same convention as spawn.py task IDs.

    Raises:
        ValueError: If project_id does not match the required pattern.
    """
    pattern = re.compile(r'^[a-zA-Z0-9\-]{1,20}$')
    if not pattern.match(project_id):
        raise ValueError(
            f"Invalid project ID '{project_id}'. "
            "Must be 1-20 characters, alphanumeric and hyphens only."
        )


def _list_projects(root: Path) -> List[Dict[str, Any]]:
    """
    Enumerate projects/ directory, skipping _-prefixed entries.

    Returns a list of dicts with keys:
        id, name, workspace, corrupt (bool)
    """
    projects_dir = root / "projects"
    results: List[Dict[str, Any]] = []

    if not projects_dir.exists():
        return results

    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        manifest_path = entry / "project.json"
        if not manifest_path.exists():
            # Directory exists but no manifest — treat as corrupt
            results.append({
                "id": entry.name,
                "name": "(no manifest)",
                "workspace": "--",
                "corrupt": True,
            })
            continue
        try:
            with open(manifest_path) as f:
                data = json.load(f)
            results.append({
                "id": entry.name,
                "name": data.get("name", entry.name),
                "workspace": data.get("workspace", "--"),
                "corrupt": False,
            })
        except (json.JSONDecodeError, OSError):
            results.append({
                "id": entry.name,
                "name": "(corrupt)",
                "workspace": "--",
                "corrupt": True,
            })

    return results


def _has_running_l3_containers(project_id: str) -> bool:
    """
    Check if any L3 containers are running for the given project.

    Uses docker label openclaw.project=<project_id>.
    On Docker import/connection failure, returns False (allows switch) and warns.
    """
    try:
        import docker  # type: ignore
        client = docker.from_env()
        containers = client.containers.list(
            filters={"label": f"openclaw.project={project_id}"}
        )
        return len(containers) > 0
    except ImportError:
        print(
            f"{Colors.YELLOW}Warning: docker package not available. "
            f"Cannot verify running containers.{Colors.RESET}",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(
            f"{Colors.YELLOW}Warning: Could not connect to Docker daemon: {e}. "
            f"Assuming no running containers.{Colors.RESET}",
            file=sys.stderr,
        )
        return False


def _set_active_project(project_id: str, root: Path) -> None:
    """
    Update the active_project field in openclaw.json.

    Read-modify-write with indent=2 and trailing newline.
    """
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    config["active_project"] = project_id
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    """
    Initialize a new project (CLI-01, CLI-05).

    Creates projects/<id>/project.json and agents/<l2_pm>/agent/SOUL.md.
    Auto-activates the new project.
    """
    root = _find_project_root()

    # Resolve --id
    project_id = args.id
    if not project_id:
        if _is_interactive():
            project_id = input("Project ID: ").strip()
        else:
            print("Error: --id is required in non-interactive mode.", file=sys.stderr)
            return 1

    # Resolve --name
    project_name = args.name
    if not project_name:
        if _is_interactive():
            project_name = input("Project name: ").strip()
        else:
            print("Error: --name is required in non-interactive mode.", file=sys.stderr)
            return 1

    # Validate project ID
    try:
        _validate_project_id(project_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Collision check
    manifest_path = root / "projects" / project_id / "project.json"
    if manifest_path.exists() and not args.force:
        if _is_interactive():
            answer = input(
                f"Project '{project_id}' already exists. Overwrite? [y/N] "
            ).strip().lower()
            if answer != "y":
                print("Aborted.", file=sys.stderr)
                return 1
        else:
            print(
                f"Error: Project '{project_id}' already exists. "
                "Use --force to overwrite.",
                file=sys.stderr,
            )
            return 1

    # Build default workspace path — prefer first source_directories entry
    if args.workspace:
        workspace_path = args.workspace
    else:
        config_path = root / "openclaw.json"
        try:
            with open(config_path) as f:
                _cfg = json.load(f)
            source_dirs = _cfg.get("source_directories", [])
            if source_dirs:
                workspace_path = str(Path(source_dirs[0]) / project_id)
            else:
                workspace_path = str(root / "workspace" / project_id) + "/"
        except (json.JSONDecodeError, OSError):
            workspace_path = str(root / "workspace" / project_id) + "/"

    # Build default project config
    project_config: Dict[str, Any] = {
        "id": project_id,
        "name": project_name,
        "agent_display_name": f"{project_name.replace(' ', '')}_PM",
        "workspace": workspace_path,
        "tech_stack": {
            "frontend": "",
            "backend": "",
            "infra": "",
        },
        "agents": {
            "l2_pm": f"{project_id}_pm",
            "l3_executor": "l3_specialist",
        },
        "l3_overrides": {
            "mem_limit": "4g",
            "cpu_quota": 100000,
            "runtimes": ["claude-code", "codex", "gemini-cli"],
        },
    }

    # Merge template if --template specified
    if args.template:
        template_path = root / "projects" / "_templates" / f"{args.template}.json"
        if not template_path.exists():
            print(
                f"Error: Template '{args.template}' not found at {template_path}",
                file=sys.stderr,
            )
            return 1
        with open(template_path) as f:
            template_data = json.load(f)
        # Template values are base; project_config already has explicit defaults
        # Merge tech_stack (template overwrites blanks)
        if "tech_stack" in template_data:
            project_config["tech_stack"].update(template_data["tech_stack"])
        # Merge l3_overrides (template overwrites defaults)
        if "l3_overrides" in template_data:
            project_config["l3_overrides"].update(template_data["l3_overrides"])

    # Override workspace if --workspace explicitly provided
    if args.workspace:
        project_config["workspace"] = args.workspace

    # Write project.json
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(project_config, f, indent=2)
        f.write("\n")

    # Generate SOUL.md (lazy import to avoid circular import risk — Phase 18 pattern)
    try:
        from orchestration.soul_renderer import write_soul
        soul_path = write_soul(project_id, skip_if_exists=not args.force)
        if soul_path is not None:
            print(f"SOUL.md written to: {soul_path}")
        else:
            print(
                f"{Colors.YELLOW}SOUL.md already exists (use --force to overwrite){Colors.RESET}"
            )
    except Exception as e:
        print(
            f"{Colors.YELLOW}Warning: Could not generate SOUL.md (non-fatal): {e}{Colors.RESET}",
            file=sys.stderr,
        )

    # Auto-activate
    _set_active_project(project_id, root)

    # Validate L2 agent ID against openclaw.json agents list (non-fatal warning)
    l2_pm_id = project_config["agents"]["l2_pm"]
    openclaw_config_path = root / "openclaw.json"
    try:
        with open(openclaw_config_path) as f:
            openclaw_config = json.load(f)
        agent_ids = [a.get("id") for a in openclaw_config.get("agents", {}).get("list", [])]
        if l2_pm_id not in agent_ids:
            print(
                f"{Colors.YELLOW}Warning: L2 agent '{l2_pm_id}' is not registered in "
                f"openclaw.json agents.list. Add it before delegating tasks.{Colors.RESET}",
                file=sys.stderr,
            )
    except Exception:
        pass  # Non-fatal

    print(
        f"{Colors.GREEN}Created project '{project_id}' (now active){Colors.RESET}"
    )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """
    List all projects with ID, name, workspace, and active marker (CLI-02).
    """
    root = _find_project_root()
    projects = _list_projects(root)

    try:
        active_id = get_active_project_id()
    except Exception:
        active_id = None

    if not projects:
        print("No projects found.")
        return 0

    # Header
    print(
        f"{Colors.BOLD}"
        f"{'ID':<15} {'NAME':<15} {'WORKSPACE':<40} {'ACTIVE'}"
        f"{Colors.RESET}"
    )
    print("-" * 80)

    for project in projects:
        pid = project["id"]
        name = project["name"] if not project["corrupt"] else f"(corrupt)"
        workspace = project["workspace"] if not project["corrupt"] else "--"

        # Truncate workspace with ellipsis if too long
        if len(workspace) > 40:
            workspace = workspace[:37] + "..."

        active_marker = "*" if pid == active_id else ""

        print(f"{pid:<15} {name:<15} {workspace:<40} {active_marker}")

    return 0


def cmd_switch(args: argparse.Namespace) -> int:
    """
    Switch the active project (CLI-03).

    Blocked if L3 containers are running for the current active project.
    """
    root = _find_project_root()
    project_id = args.project_id

    # Validate project exists
    manifest_path = root / "projects" / project_id / "project.json"
    if not manifest_path.exists():
        print(
            f"Error: Project '{project_id}' not found. "
            f"Run 'list' to see available projects.",
            file=sys.stderr,
        )
        return 1

    # Validate project.json is not corrupt
    try:
        with open(manifest_path) as f:
            json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"Error: Project '{project_id}' has a corrupt project.json: {e}",
            file=sys.stderr,
        )
        return 1

    # Guard: check for running L3 containers on the CURRENT active project
    try:
        current_active = get_active_project_id()
    except Exception:
        current_active = None

    if current_active and _has_running_l3_containers(current_active):
        print(
            f"{Colors.RED}Error: Cannot switch: L3 containers are running for project "
            f"'{current_active}'. Wait for tasks to complete or stop containers.{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    _set_active_project(project_id, root)
    print(f"{Colors.GREEN}Switched to project '{project_id}'{Colors.RESET}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    """
    Remove a project directory (CLI-04).

    Deletes projects/<id>/ but preserves workspace/<id>/.
    Blocked if attempting to remove the currently active project.
    """
    root = _find_project_root()
    project_id = args.project_id

    # Guard: cannot remove the active project
    try:
        active_id = get_active_project_id()
    except Exception:
        active_id = None

    if project_id == active_id:
        print(
            f"{Colors.RED}Error: Cannot remove the active project. "
            f"Switch to another project first.{Colors.RESET}",
            file=sys.stderr,
        )
        return 1

    # Check project directory exists
    project_dir = root / "projects" / project_id
    if not project_dir.exists():
        print(
            f"Error: Project '{project_id}' not found at {project_dir}",
            file=sys.stderr,
        )
        return 1

    # Confirmation
    if not args.force:
        if _is_interactive():
            answer = input(
                f"Remove project '{project_id}' and all its files? [y/N] "
            ).strip().lower()
            if answer != "y":
                print("Aborted.", file=sys.stderr)
                return 1
        else:
            print(
                f"Error: --force required to remove project in non-interactive mode.",
                file=sys.stderr,
            )
            return 1

    # Delete projects/<id>/ directory
    shutil.rmtree(project_dir)

    print(
        f"{Colors.GREEN}Removed project '{project_id}' "
        f"(workspace preserved at workspace/{project_id}/){Colors.RESET}"
    )
    return 0


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entrypoint for OpenClaw Project Manager."""
    parser = argparse.ArgumentParser(
        description="OpenClaw Project Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # --- init ---
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument(
        "--id",
        dest="id",
        type=str,
        default=None,
        help="Project ID (alphanumeric + hyphens, 1-20 chars)",
    )
    init_parser.add_argument(
        "--name",
        dest="name",
        type=str,
        default=None,
        help="Human-readable project name",
    )
    init_parser.add_argument(
        "--template",
        dest="template",
        choices=["fullstack", "backend", "ml-pipeline"],
        default=None,
        help="Template preset to scaffold from",
    )
    init_parser.add_argument(
        "--workspace",
        dest="workspace",
        type=str,
        default=None,
        help="Custom workspace path (default: workspace/<id>/)",
    )
    init_parser.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Overwrite existing project files without prompting",
    )

    # --- list ---
    subparsers.add_parser("list", help="List all projects")

    # --- switch ---
    switch_parser = subparsers.add_parser("switch", help="Switch the active project")
    switch_parser.add_argument(
        "project_id",
        type=str,
        help="Project ID to switch to",
    )

    # --- remove ---
    remove_parser = subparsers.add_parser("remove", help="Remove a project")
    remove_parser.add_argument(
        "project_id",
        type=str,
        help="Project ID to remove",
    )
    remove_parser.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "switch":
        return cmd_switch(args)
    elif args.command == "remove":
        return cmd_remove(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
