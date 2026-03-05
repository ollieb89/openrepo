"""
OpenClaw Config CLI

Provides subcommands for inspecting and migrating the OpenClaw configuration.

Usage:
    openclaw-config show              # Print effective openclaw.json config
    openclaw-config migrate           # Upgrade config files to current schema
    openclaw-config migrate --dry-run # Preview what would change
"""

import argparse
import json
import re
import shutil
import sys

from openclaw.project_config import load_and_validate_openclaw_config
from openclaw.config import get_project_root
from openclaw.config_validator import validate_openclaw_config, validate_project_config_schema, ConfigValidationError


# ANSI color codes — same as project.py and monitor.py
class Colors:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    YELLOW = '\033[93m'
    BLUE   = '\033[94m'
    RESET  = '\033[0m'
    BOLD   = '\033[1m'


def _collect_unknown_field_names(config: dict, schema: dict) -> list:
    """Return a list of unknown top-level field names in config per schema.

    Uses Draft202012Validator.iter_errors() directly to get clean field names
    from additionalProperties validation errors.
    """
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(schema)
    unknown = []
    for error in validator.iter_errors(config):
        if error.validator == "additionalProperties":
            # error.message format: "Additional properties are not allowed ('foo', 'bar' were unexpected)"
            # Parse field names from the message
            names = re.findall(r"'([^']+)'", error.message)
            unknown.extend(names)
    return unknown


def _migrate_one_openclaw_json(config_path, dry_run: bool) -> int:
    """Migrate a single openclaw.json file. Returns 0 on success, 1 on fatal error."""
    from openclaw.config import OPENCLAW_JSON_SCHEMA

    try:
        with open(config_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"{Colors.RED}ERROR{Colors.RESET}: Cannot parse {config_path}: {exc}", file=sys.stderr)
        return 1

    fatal, _ = validate_openclaw_config(config, str(config_path))
    if fatal:
        print(f"{Colors.RED}ERROR{Colors.RESET}: {config_path} has required fields missing — manual fix needed:")
        for e in fatal:
            print(f"  {e}")
        print("  (Migration cannot auto-fill required fields. Fix manually, then re-run migrate.)")
        return 1

    unknown = _collect_unknown_field_names(config, OPENCLAW_JSON_SCHEMA)
    if not unknown:
        print(f"{config_path}: Already up-to-date.")
        return 0

    changes = [f"  - removed unknown field: '{f}'" for f in unknown]
    if dry_run:
        print(f"{config_path}:")
        for c in changes:
            print(c)
        print("  Run without --dry-run to apply.")
        return 0

    # Apply: backup then write
    bak_path = str(config_path) + ".bak"
    shutil.copy2(config_path, bak_path)
    migrated = {k: v for k, v in config.items() if k not in unknown}
    with open(config_path, "w") as f:
        json.dump(migrated, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Migrated {config_path}: {len(unknown)} field(s) removed. Backup saved to {bak_path}")
    return 0


def _migrate_one_project_json(config_path, dry_run: bool) -> int:
    """Migrate a single project.json file. Returns 0 on success, 1 on fatal error."""
    from openclaw.config import PROJECT_JSON_SCHEMA

    try:
        with open(config_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"{Colors.RED}ERROR{Colors.RESET}: Cannot parse {config_path}: {exc}", file=sys.stderr)
        return 1

    try:
        validate_project_config_schema(config, str(config_path))
        # If no exception, required fields present — check for unknown fields only
    except ConfigValidationError as exc:
        # Required fields missing — cannot auto-fix
        print(f"{Colors.RED}ERROR{Colors.RESET}: {config_path} has required fields missing — manual fix needed:")
        print(f"  {exc}")
        print("  (Migration cannot auto-fill required fields. Fix manually, then re-run migrate.)")
        return 1

    unknown = _collect_unknown_field_names(config, PROJECT_JSON_SCHEMA)
    if not unknown:
        print(f"{config_path}: Already up-to-date.")
        return 0

    changes = [f"  - removed unknown field: '{f}'" for f in unknown]
    if dry_run:
        print(f"{config_path}:")
        for c in changes:
            print(c)
        print("  Run without --dry-run to apply.")
        return 0

    # Apply: backup then write
    bak_path = str(config_path) + ".bak"
    shutil.copy2(config_path, bak_path)
    migrated = {k: v for k, v in config.items() if k not in unknown}
    with open(config_path, "w") as f:
        json.dump(migrated, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Migrated {config_path}: {len(unknown)} field(s) removed. Backup saved to {bak_path}")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """
    Upgrade openclaw.json and all project.json files to the current schema.

    Removes unknown fields (additionalProperties violations per the Phase 46 schema).
    Cannot auto-fix missing required fields — prints guidance and exits non-zero.

    --dry-run: prints what would change without modifying any file.
    Always creates a .bak backup before modifying any file.

    Note: _comment_* documentation keys are removed from live configs during
    migration (they are unknown per the schema). See config/openclaw.json.example
    for reference documentation.
    """
    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        print("Dry run — no files will be modified.\n")

    root = get_project_root()
    rc = 0

    # 1. Migrate openclaw.json
    openclaw_json = root / "openclaw.json"
    if openclaw_json.exists():
        result = _migrate_one_openclaw_json(openclaw_json, dry_run)
        if result != 0:
            rc = result
    else:
        print(f"{Colors.YELLOW}WARNING{Colors.RESET}: {openclaw_json} not found — skipping.")

    # 2. Migrate all project.json files under projects/
    projects_dir = root / "projects"
    if projects_dir.exists():
        for project_dir in sorted(projects_dir.iterdir()):
            if project_dir.is_dir() and not project_dir.name.startswith("_"):
                manifest = project_dir / "project.json"
                if manifest.exists():
                    print()
                    result = _migrate_one_project_json(manifest, dry_run)
                    if result != 0:
                        rc = result

    return rc


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


def cmd_sync_agents(args: argparse.Namespace) -> int:
    """Sync agents from unified registry to agents/*/agent/config.json."""
    from openclaw.agent_registry import AgentRegistry
    import json
    
    root = get_project_root()
    registry = AgentRegistry(root)
    
    for aid, spec in registry._agents.items():
        if aid == "main": # Skip main if needed or keep it, let's keep it.
            pass
            
        agent_dir = root / "agents" / aid
        if not agent_dir.exists():
            print(f"{Colors.YELLOW}WARNING{Colors.RESET}: Directory for agent '{aid}' does not exist. Skipping.")
            continue
            
        agent_config_dir = agent_dir / "agent"
        agent_config_dir.mkdir(parents=True, exist_ok=True)
        config_path = agent_config_dir / "config.json"
        
        # Load existing to preserve unknown fields, or create new
        config_data = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            except Exception:
                pass
                
        config_data["id"] = spec.id
        config_data["name"] = spec.name
        config_data["level"] = int(spec.level)
        if spec.reports_to:
            config_data["reports_to"] = spec.reports_to
        if spec.subordinates:
            config_data["subordinates"] = spec.subordinates
        if spec.role:
            config_data["role"] = spec.role
        if spec.projects:
            config_data["projects"] = spec.projects
        if spec.max_concurrent:
            config_data["max_concurrent"] = spec.max_concurrent
        if spec.skill_registry:
            config_data["skill_registry"] = spec.skill_registry
        if spec.container:
            config_data["container"] = spec.container
        if spec.runtime:
            config_data["runtime"] = spec.runtime
            
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            
        print(f"Synced {aid} -> {config_path}")
        
    return 0

def cmd_validate(args: argparse.Namespace) -> int:
    """Validate full agent hierarchy."""
    from openclaw.agent_registry import AgentRegistry
    from openclaw.config_validator import validate_agent_hierarchy_advanced
    
    root = get_project_root()
    registry = AgentRegistry(root)
    
    errors = validate_agent_hierarchy_advanced(registry)
    if errors:
        print(f"{Colors.RED}Validation Failed:{Colors.RESET}")
        for err in errors:
            print(f"  - {err}")
        return 1
        
    print(f"{Colors.GREEN}Validation Passed!{Colors.RESET} Hierarchy is valid.")
    return 0

def main() -> None:
    """CLI entrypoint for OpenClaw Config tools."""
    parser = argparse.ArgumentParser(
        description="OpenClaw Config Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Environment variables (override config file values):
  OPENCLAW_ROOT             Project root directory (default: ~/.openclaw)
  OPENCLAW_PROJECT          Active project ID (default: openclaw.json active_project)
  OPENCLAW_LOG_LEVEL        Log verbosity: DEBUG|INFO|WARNING|ERROR (default: INFO)
  OPENCLAW_ACTIVITY_LOG_MAX Max activity log entries per task (default: 100)
  OPENCLAW_STATE_FILE       Workspace state file path (L3 containers only)
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # --- show ---
    subparsers.add_parser(
        "show",
        help="Print the effective openclaw.json configuration (file values + defaults merged)",
    )

    # --- migrate ---
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Upgrade openclaw.json and all project.json files to the current schema",
    )
    migrate_parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Print what would change without modifying any files",
    )

    # --- sync-agents ---
    subparsers.add_parser(
        "sync-agents",
        help="Sync agents from unified registry to agents/*/agent/config.json",
    )
    
    # --- validate ---
    subparsers.add_parser(
        "validate",
        help="Validate full agent hierarchy",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "show":
        sys.exit(cmd_show(args))
    elif args.command == "migrate":
        sys.exit(cmd_migrate(args))
    elif args.command == "sync-agents":
        sys.exit(cmd_sync_agents(args))
    elif args.command == "validate":
        sys.exit(cmd_validate(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
