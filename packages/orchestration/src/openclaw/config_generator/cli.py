import argparse
import sys
from .db import ConfigDatabase, create_default_config

def init_db(args):
    print(f"Initializing database at {args.db}...")
    db = create_default_config(args.db)
    print("Default configuration created successfully.")
    db.close()

def generate_json(args):
    db = ConfigDatabase(args.db)
    db.connect()
    
    # Check if empty (e.g. no agents)
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM agents")
    if cursor.fetchone()[0] == 0:
        print(f"Warning: Database at {args.db} appears empty or uninitialized.", file=sys.stderr)
    
    print(f"Generating {args.output} from {args.db}...")
    db.generate_openclaw_json(args.output)
    print("Config generated successfully.")
    db.close()

def list_table(args, table_name, columns):
    db = ConfigDatabase(args.db)
    db.connect()
    cursor = db.conn.cursor()
    
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"No {table_name} found in database.")
            return

        # Calculate dynamic column widths (at least 15 wide to match old styling or width of column name)
        col_widths = {col: max(15, len(col)) for col in columns}
        for row in rows:
            for col in columns:
                val_len = len(str(row[col] if row[col] is not None else ""))
                if val_len > col_widths[col]:
                    col_widths[col] = val_len

        # Print header
        header_parts = []
        for col in columns:
            header_parts.append(col.upper().ljust(col_widths[col]))
        header = " | ".join(header_parts)
        print(header)
        print("-" * len(header))
        
        # Print rows
        for row in rows:
            row_data = []
            for col in columns:
                val = str(row[col] if row[col] is not None else "")
                row_data.append(val.ljust(col_widths[col]))
            print(" | ".join(row_data))
            
    except Exception as e:
        print(f"Error reading {table_name}: {e}", file=sys.stderr)
    finally:
        db.close()

def list_providers(args):
    list_table(args, "providers", ["id", "name", "type", "enabled"])

def list_models(args):
    list_table(args, "models", ["id", "provider_id", "name", "type", "enabled"])

def list_channels(args):
    list_table(args, "channels", ["id", "name", "type", "enabled"])

def list_agents(args):
    list_table(args, "agents", ["id", "name", "level", "reports_to", "model_id"])

def list_aliases(args):
    list_table(args, "model_aliases", ["alias", "model_id"])

def list_fallbacks(args):
    """Lists both fallbacks and image fallbacks by executing two queries."""
    list_table(args, "model_fallbacks", ["model_id", "priority"])
    print("\n--- Image Fallbacks ---")
    list_table(args, "model_image_fallbacks", ["model_id", "priority"])

def list_devices(args):
    list_table(args, "devices", ["id", "role", "scope"])

def list_pairings(args):
    list_table(args, "pairings", ["id", "channel", "account_id", "status"])

def list_system(args):
    list_table(args, "system_config", ["key", "value"])

def list_nodes(args):
    list_table(args, "nodes", ["id", "name", "status"])

def list_webhooks(args):
    list_table(args, "webhooks", ["id", "type", "enabled"])

def list_plugins(args):
    list_table(args, "plugins", ["id", "enabled"])

def list_skills(args):
    list_table(args, "skills", ["id", "enabled"])

def list_memory(args):
    list_table(args, "memory_config", ["key", "value"])

def list_cron(args):
    list_table(args, "cron_jobs", ["id", "expression", "command", "enabled"])

def list_browser(args):
    list_table(args, "browser_profiles", ["id", "is_default"])

def list_hooks(args):
    list_table(args, "hooks", ["id", "event", "command", "enabled"])

def list_secrets(args):
    list_table(args, "secrets_config", ["key", "value", "provider"])

def list_security(args):
    list_table(args, "security_config", ["key", "value"])

def list_dashboard(args):
    list_table(args, "dashboard_config", ["key", "value"])

def list_acp(args):
    list_table(args, "acp_config", ["key", "value"])

def list_dns(args):
    list_table(args, "dns_config", ["key", "value"])

def list_tui(args):
    list_table(args, "tui_config", ["key", "value"])

def list_approvals(args):
    list_table(args, "approvals", ["id", "status", "type"])

def list_directory(args):
    list_table(args, "directory_config", ["key", "value"])

def list_sessions(args):
    list_table(args, "sessions_config", ["key", "value"])

def list_logs(args):
    list_table(args, "logs_config", ["key", "value"])

def list_docs(args):
    list_table(args, "docs_config", ["key", "value"])

def list_sandbox(args):
    list_table(args, "sandbox_config", ["key", "value"])

def discover_components(args):
    db = ConfigDatabase(args.db)
    db.connect()
    
    print(f"Analyzing sitemap at {args.sitemap}...")
    report = db.get_discovery_report(args.sitemap)
    
    if "error" in report:
        print(f"Error: {report['error']}", file=sys.stderr)
        db.close()
        return

    print("\n=== Discovery Report ===")
    has_missing = False
    for category, data in report.items():
        missing = data.get("missing", [])
        if missing:
            has_missing = True
            print(f"\n[{category.upper()}] Missing integrations:")
            for item in sorted(missing):
                print(f"  - {item}")
        
    if not has_missing:
        print("\nAll components from sitemap are already in the database!")
    elif args.interactive:
        run_discovery_wizard(db, report)
    else:
        print("\nRun with --interactive to add these components to your database.")
    
    db.close()

def run_discovery_wizard(db, report):
    print("\n=== Discovery Wizard ===")
    added_count = 0
    
    for category, data in report.items():
        missing = data.get("missing", [])
        if not missing:
            continue
            
        print(f"\nFound {len(missing)} missing {category}. Add them?")
        choice = input(f"Add all {category}? (y/n/individual): ").lower()
        
        if choice == 'y':
            for item in missing:
                if db.add_component_from_discovery(category, item):
                    print(f"  + Added {item}")
                    added_count += 1
        elif choice == 'individual':
            for item in missing:
                sub_choice = input(f"  Add {item}? (y/n): ").lower()
                if sub_choice == 'y':
                    if db.add_component_from_discovery(category, item):
                        print(f"    + Added {item}")
                        added_count += 1
    
    if added_count > 0:
        print(f"\nSuccessfully added {added_count} components. Remember to run 'generate' to update openclaw.json.")
    else:
        print("\nNo components were added.")

def main():
    parser = argparse.ArgumentParser(description="OpenClaw Config Generator")
    parser.add_argument("--db", default="openclaw_config.db", help="Path to the SQLite database")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    subparsers.required = True
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Create database with defaults")
    init_parser.set_defaults(func=init_db)
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate openclaw.json")
    generate_parser.add_argument("--output", "-o", default="openclaw.json", help="Output JSON file path")
    generate_parser.set_defaults(func=generate_json)
    
    # List commands
    providers_parser = subparsers.add_parser("providers", help="List providers")
    providers_parser.set_defaults(func=list_providers)

    models_parser = subparsers.add_parser("models", help="List models")
    models_parser.set_defaults(func=list_models)
    
    channels_parser = subparsers.add_parser("channels", help="List channels")
    channels_parser.set_defaults(func=list_channels)
    
    agents_parser = subparsers.add_parser("agents", help="List agents")
    agents_parser.set_defaults(func=list_agents)
    
    aliases_parser = subparsers.add_parser("aliases", help="List model aliases")
    aliases_parser.set_defaults(func=list_aliases)
    
    fallbacks_parser = subparsers.add_parser("fallbacks", help="List model fallbacks")
    fallbacks_parser.set_defaults(func=list_fallbacks)
    
    devices_parser = subparsers.add_parser("devices", help="List authorized devices")
    devices_parser.set_defaults(func=list_devices)
    
    pairings_parser = subparsers.add_parser("pairings", help="List channel pairings")
    pairings_parser.set_defaults(func=list_pairings)
    
    system_parser = subparsers.add_parser("system", help="List system configuration")
    system_parser.set_defaults(func=list_system)

    nodes_parser = subparsers.add_parser("nodes", help="List compute nodes")
    nodes_parser.set_defaults(func=list_nodes)

    webhooks_parser = subparsers.add_parser("webhooks", help="List webhook configurations")
    webhooks_parser.set_defaults(func=list_webhooks)
    
    plugins_parser = subparsers.add_parser("plugins", help="List plugin configurations")
    plugins_parser.set_defaults(func=list_plugins)
    
    skills_parser = subparsers.add_parser("skills", help="List skills")
    skills_parser.set_defaults(func=list_skills)

    memory_parser = subparsers.add_parser("memory", help="List memory configuration")
    memory_parser.set_defaults(func=list_memory)

    cron_parser = subparsers.add_parser("cron", help="List cron jobs")
    cron_parser.set_defaults(func=list_cron)

    browser_parser = subparsers.add_parser("browser", help="List browser profiles")
    browser_parser.set_defaults(func=list_browser)

    hooks_parser = subparsers.add_parser("hooks", help="List internal hooks")
    hooks_parser.set_defaults(func=list_hooks)

    secrets_parser = subparsers.add_parser("secrets", help="List secret configurations")
    secrets_parser.set_defaults(func=list_secrets)

    security_parser = subparsers.add_parser("security", help="List security configurations")
    security_parser.set_defaults(func=list_security)

    dashboard_parser = subparsers.add_parser("dashboard", help="List dashboard configuration")
    dashboard_parser.set_defaults(func=list_dashboard)

    acp_parser = subparsers.add_parser("acp", help="List ACP bridge configuration")
    acp_parser.set_defaults(func=list_acp)

    dns_parser = subparsers.add_parser("dns", help="List DNS configuration")
    dns_parser.set_defaults(func=list_dns)

    tui_parser = subparsers.add_parser("tui", help="List TUI configuration")
    tui_parser.set_defaults(func=list_tui)

    approvals_parser = subparsers.add_parser("approvals", help="List approvals configuration")
    approvals_parser.set_defaults(func=list_approvals)

    directory_parser = subparsers.add_parser("directory", help="List directory configuration")
    directory_parser.set_defaults(func=list_directory)

    sessions_parser = subparsers.add_parser("sessions", help="List sessions configuration")
    sessions_parser.set_defaults(func=list_sessions)

    logs_parser = subparsers.add_parser("logs", help="List logs configuration")
    logs_parser.set_defaults(func=list_logs)

    docs_parser = subparsers.add_parser("docs", help="List docs configuration")
    docs_parser.set_defaults(func=list_docs)

    sandbox_parser = subparsers.add_parser("sandbox", help="List global sandbox configuration")
    sandbox_parser.set_defaults(func=list_sandbox)

    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover missing components from sitemap")
    discover_parser.add_argument("--sitemap", default="docs/sitemap.xml", help="Path to sitemap.xml")
    discover_parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive wizard")
    discover_parser.set_defaults(func=discover_components)

    args = parser.parse_args()
    args.func(args)
