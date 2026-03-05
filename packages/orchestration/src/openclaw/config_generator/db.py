import sqlite3
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import os

class ConfigDatabase:
    """A SQLite-based configuration database for OpenClaw."""

    def __init__(self, db_path: str = "openclaw_config.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect to the database and ensure tables exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS providers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                base_url TEXT,
                api_key_env TEXT,
                enabled BOOLEAN DEFAULT 1,
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'chat',
                params TEXT,
                enabled BOOLEAN DEFAULT 1,
                FOREIGN KEY (provider_id) REFERENCES providers (id)
            );

            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                workspace TEXT,
                agent_dir TEXT,
                reports_to TEXT,
                subordinates TEXT,
                model_id TEXT,
                sandbox_mode TEXT DEFAULT 'off',
                orchestration_role TEXT,
                config TEXT,
                FOREIGN KEY (reports_to) REFERENCES agents (id),
                FOREIGN KEY (model_id) REFERENCES models (id)
            );

            CREATE TABLE IF NOT EXISTS gateway_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS plugins (
                id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS model_aliases (
                alias TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                FOREIGN KEY (model_id) REFERENCES models(id)
            );

            CREATE TABLE IF NOT EXISTS model_fallbacks (
                model_id TEXT PRIMARY KEY,
                priority INTEGER NOT NULL,
                FOREIGN KEY (model_id) REFERENCES models(id)
            );

            CREATE TABLE IF NOT EXISTS model_image_fallbacks (
                model_id TEXT PRIMARY KEY,
                priority INTEGER NOT NULL,
                FOREIGN KEY (model_id) REFERENCES models(id)
            );

            CREATE TABLE IF NOT EXISTS pairings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                account_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'approved'
            );

            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                scope TEXT
            );

            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT DEFAULT 'pending',
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS webhooks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS memory_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cron_jobs (
                id TEXT PRIMARY KEY,
                expression TEXT NOT NULL,
                command TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS browser_profiles (
                id TEXT PRIMARY KEY,
                is_default BOOLEAN DEFAULT 0,
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS hooks (
                id TEXT PRIMARY KEY,
                event TEXT NOT NULL,
                command TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS secrets_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                provider TEXT
            );

            CREATE TABLE IF NOT EXISTS security_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dashboard_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS acp_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dns_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tui_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                type TEXT,
                config TEXT
            );

            CREATE TABLE IF NOT EXISTS directory_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS docs_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sandbox_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        ''')
        self.conn.commit()

    def add_provider(self, id, name, type, base_url=None, api_key_env=None, enabled=True, config=None):
        """Add a provider to the database."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO providers (id, name, type, base_url, api_key_env, enabled, config)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (id, name, type, base_url, api_key_env, int(enabled), config_str))
        self.conn.commit()

    def add_model(self, id, provider_id, name, type="chat", params=None, enabled=True):
        """Add a model to the database."""
        cursor = self.conn.cursor()
        params_str = json.dumps(params) if params is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO models (id, provider_id, name, type, params, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (id, provider_id, name, type, params_str, int(enabled)))
        self.conn.commit()

    def add_channel(self, id, name, type, enabled=True, config=None):
        """Add a channel to the database."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO channels (id, name, type, enabled, config)
            VALUES (?, ?, ?, ?, ?)
        ''', (id, name, type, int(enabled), config_str))
        self.conn.commit()

    def add_agent(self, id, name, level=1, workspace=None, agent_dir=None, reports_to=None, subordinates=None, model_id=None, sandbox_mode="off", orchestration_role=None, config=None):
        """Add an agent to the database."""
        cursor = self.conn.cursor()
        subordinates_str = json.dumps(subordinates) if subordinates is not None else None
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO agents (id, name, level, workspace, agent_dir, reports_to, subordinates, model_id, sandbox_mode, orchestration_role, config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id, name, level, workspace, agent_dir, reports_to, subordinates_str, model_id, sandbox_mode, orchestration_role, config_str))
        self.conn.commit()

    def set_gateway(self, key, value):
        """Set a gateway setting."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value)
        cursor.execute('''
            INSERT OR REPLACE INTO gateway_settings (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def add_plugin(self, id, enabled=True, config=None):
        """Add a plugin setting."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO plugins (id, enabled, config)
            VALUES (?, ?, ?)
        ''', (id, int(enabled), config_str))
        self.conn.commit()

    def add_model_alias(self, alias, model_id):
        """Add a model alias."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO model_aliases (alias, model_id)
            VALUES (?, ?)
        ''', (alias, model_id))
        self.conn.commit()
    
    def add_model_fallback(self, model_id, priority):
        """Add a model fallback."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO model_fallbacks (model_id, priority)
            VALUES (?, ?)
        ''', (model_id, priority))
        self.conn.commit()
        
    def add_model_image_fallback(self, model_id, priority):
        """Add a model image fallback."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO model_image_fallbacks (model_id, priority)
            VALUES (?, ?)
        ''', (model_id, priority))
        self.conn.commit()

    def add_pairing(self, channel, account_id, status="approved"):
        """Add a channel pairing."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO pairings (channel, account_id, status)
            VALUES (?, ?, ?)
        ''', (channel, account_id, status))
        self.conn.commit()

    def add_device(self, id, role, scope=None):
        """Add an authorized device."""
        cursor = self.conn.cursor()
        scope_str = json.dumps(scope) if scope is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO devices (id, role, scope)
            VALUES (?, ?, ?)
        ''', (id, role, scope_str))
        self.conn.commit()

    def set_system_config(self, key, value):
        """Set a generic system configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO system_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def add_node(self, id, name=None, status="pending", config=None):
        """Add a compute node."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO nodes (id, name, status, config)
            VALUES (?, ?, ?, ?)
        ''', (id, name, status, config_str))
        self.conn.commit()

    def add_webhook(self, id, type, enabled=True, config=None):
        """Add a webhook configuration."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO webhooks (id, type, enabled, config)
            VALUES (?, ?, ?, ?)
        ''', (id, type, int(enabled), config_str))
        self.conn.commit()

    def add_skill(self, id, enabled=True, config=None):
        """Add a skill."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO skills (id, enabled, config)
            VALUES (?, ?, ?)
        ''', (id, int(enabled), config_str))
        self.conn.commit()

    def set_memory_config(self, key, value):
        """Set a memory configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO memory_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def add_cron_job(self, id, expression, command, enabled=True):
        """Add a cron job."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cron_jobs (id, expression, command, enabled)
            VALUES (?, ?, ?, ?)
        ''', (id, expression, command, int(enabled)))
        self.conn.commit()

    def add_browser_profile(self, id, is_default=False, config=None):
        """Add a browser profile."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO browser_profiles (id, is_default, config)
            VALUES (?, ?, ?)
        ''', (id, int(is_default), config_str))
        self.conn.commit()

    def add_hook(self, id, event, command, enabled=True):
        """Add an internal hook."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO hooks (id, event, command, enabled)
            VALUES (?, ?, ?, ?)
        ''', (id, event, command, int(enabled)))
        self.conn.commit()

    def set_secret_config(self, key, value, provider=None):
        """Set a secret configuration mapping."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO secrets_config (key, value, provider)
            VALUES (?, ?, ?)
        ''', (key, value, provider))
        self.conn.commit()

    def set_security_config(self, key, value):
        """Set a security configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO security_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_dashboard_config(self, key, value):
        """Set a dashboard configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO dashboard_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_acp_config(self, key, value):
        """Set an ACP bridge configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO acp_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_dns_config(self, key, value):
        """Set a DNS configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO dns_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_tui_config(self, key, value):
        """Set a TUI configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO tui_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def add_approval(self, id, status, type=None, config=None):
        """Add an approval configuration."""
        cursor = self.conn.cursor()
        config_str = json.dumps(config) if config is not None else None
        cursor.execute('''
            INSERT OR REPLACE INTO approvals (id, status, type, config)
            VALUES (?, ?, ?, ?)
        ''', (id, status, type, config_str))
        self.conn.commit()

    def set_directory_config(self, key, value):
        """Set a directory configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO directory_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_sessions_config(self, key, value):
        """Set a sessions configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO sessions_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_logs_config(self, key, value):
        """Set a logs configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO logs_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_docs_config(self, key, value):
        """Set a docs configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO docs_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def set_sandbox_config(self, key, value):
        """Set a global sandbox configuration."""
        cursor = self.conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO sandbox_config (key, value)
            VALUES (?, ?)
        ''', (key, value_str))
        self.conn.commit()

    def get_discovery_report(self, sitemap_path):
        """Analyze sitemap and compare with current DB to find missing components."""
        if not os.path.exists(sitemap_path):
            return {"error": f"Sitemap not found at {sitemap_path}"}

        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            # Handle namespace if present
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = [loc.text for loc in root.findall('.//ns:loc', ns)]
            if not urls:
                urls = [loc.text for loc in root.findall('.//loc')]
        except Exception as e:
            return {"error": f"Failed to parse sitemap: {e}"}

        report = {
            "channels": {"found": [], "missing": []},
            "providers": {"found": [], "missing": []},
            "skills": {"found": [], "missing": []},
            "tools": {"found": [], "missing": []}
        }

        # Categories mapping from URL paths
        mappings = {
            "/channels/": "channels",
            "/providers/": "providers",
            "/tools/": "tools",
            "/skills/": "skills",
            "/reference/": "system",
            "/concepts/": "system",
            "/gateway/": "gateway",
            "/design/": "system"
        }

        discovered = {
            "channels": set(),
            "providers": set(),
            "tools": set(),
            "skills": set(),
            "system": set(),
            "gateway": set()
        }

        for url in urls:
            for path, category in mappings.items():
                if path in url:
                    comp_id = url.split(path)[-1].strip("/")
                    if comp_id and "/" not in comp_id and comp_id not in ["models", "pairing", "groups", "troubleshooting"]:
                        discovered[category].add(comp_id)

        cursor = self.conn.cursor()

        # Check existing
        cursor.execute("SELECT id FROM channels")
        existing_channels = {row["id"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT id FROM providers")
        existing_providers = {row["id"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT id FROM skills")
        existing_skills = {row["id"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT key FROM system_config")
        existing_system = {row["key"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT key FROM gateway_settings")
        existing_gateway = {row["key"] for row in cursor.fetchall()}

        for cat, items in discovered.items():
            for item in items:
                if cat == "channels":
                    if item in existing_channels: report["channels"]["found"].append(item)
                    else: report["channels"]["missing"].append(item)
                elif cat == "providers":
                    if item in existing_providers: report["providers"]["found"].append(item)
                    else: report["providers"]["missing"].append(item)
                elif cat in ["skills", "tools"]:
                    if item in existing_skills: report.setdefault(cat, {"found": [], "missing": []})["found"].append(item)
                    else: report.setdefault(cat, {"found": [], "missing": []})["missing"].append(item)
                elif cat == "system":
                    if item in existing_system: report.setdefault("system", {"found": [], "missing": []})["found"].append(item)
                    else: report.setdefault("system", {"found": [], "missing": []})["missing"].append(item)
                elif cat == "gateway":
                    if item in existing_gateway: report.setdefault("gateway", {"found": [], "missing": []})["found"].append(item)
                    else: report.setdefault("gateway", {"found": [], "missing": []})["missing"].append(item)

        return report

    def add_component_from_discovery(self, category, component_id):
        """Add a component with a sensible default based on its ID."""
        if category == "channels":
            # Map some common ones
            config = {}
            if component_id == "bluebubbles":
                config = {"serverUrl": "http://localhost:1234", "password": "${BLUEBUBBLES_PASSWORD}"}
            elif component_id == "matrix":
                config = {"homeserver": "https://matrix.org", "accessToken": "${MATRIX_ACCESS_TOKEN}"}
            
            self.add_channel(component_id, component_id.capitalize(), component_id, enabled=False, config=config)
            return True
        elif category == "providers":
            self.add_provider(component_id, component_id.capitalize(), "openai" if component_id != "anthropic" else "anthropic")
            return True
        elif category == "skills" or category == "tools":
            self.add_skill(component_id, enabled=False)
            return True
        elif category == "system":
            self.set_system_config(component_id, None)
            return True
        elif category == "gateway":
            self.set_gateway(component_id, None)
            return True
        return False

    def generate_openclaw_json(self, output_path=None):
        """Generate openclaw.json from the database and write to an optional output_path."""
        cursor = self.conn.cursor()

        # Agents
        cursor.execute("SELECT * FROM agents")
        agents_rows = cursor.fetchall()
        agents_list = []
        for row in agents_rows:
            agent_obj = {
                "id": row["id"],
                "name": row["name"],
                "level": row["level"],
                "sandbox": {"mode": row["sandbox_mode"]}
            }
            if row["workspace"]:
                agent_obj["workspace"] = row["workspace"]
            if row["agent_dir"]:
                agent_obj["agentDir"] = row["agent_dir"]
            
            if row["reports_to"]:
                agent_obj["reportsTo"] = row["reports_to"]
            if row["subordinates"]:
                agent_obj["subordinates"] = json.loads(row["subordinates"])
            if row["model_id"]:
                agent_obj["model"] = row["model_id"]
            if row["orchestration_role"]:
                agent_obj["orchestrationRole"] = row["orchestration_role"]
            if row["config"]:
                agent_obj["config"] = json.loads(row["config"])
            agents_list.append(agent_obj)

        cursor.execute("SELECT * FROM models")
        models_rows = cursor.fetchall()
        models_dict = {}
        for row in models_rows:
            models_dict[row["id"]] = {"params": json.loads(row["params"]) if row["params"] else {}}

        cursor.execute("SELECT * FROM model_aliases")
        for row in cursor.fetchall():
            if row["model_id"] in models_dict:
                if "aliases" not in models_dict[row["model_id"]]:
                  models_dict[row["model_id"]]["aliases"] = []
                models_dict[row["model_id"]]["aliases"].append(row["alias"])

        cursor.execute("SELECT * FROM model_fallbacks ORDER BY priority ASC")
        fallbacks = [row["model_id"] for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM model_image_fallbacks ORDER BY priority ASC")
        image_fallbacks = [row["model_id"] for row in cursor.fetchall()]

        agents_section = {
            "defaults": {
                "model": {
                    "primary": "gpt-4o"
                },
                "models": models_dict,
                "maxConcurrent": 4,
                "subagents": {
                    "maxConcurrent": 8
                },
                "sandbox": {
                    "mode": "non-main",
                    "workspaceAccess": "none",
                    "scope": "session"
                }
            },
            "list": agents_list
        }
        
        if fallbacks:
             agents_section["defaults"]["model"]["fallbacks"] = fallbacks
        if image_fallbacks:
             agents_section["defaults"]["model"]["imageFallbacks"] = image_fallbacks

        # Channels
        cursor.execute("SELECT * FROM channels")
        channels_rows = cursor.fetchall()
        channels_section = {}
        for row in channels_rows:
            channel_obj = {
                "enabled": bool(row["enabled"])
            }
            if row["config"]:
                # Merge config fields into the channel object directly
                config_data = json.loads(row["config"])
                channel_obj.update(config_data)
            channels_section[row["id"]] = channel_obj

        # Gateway
        cursor.execute("SELECT * FROM gateway_settings")
        gateway_rows = cursor.fetchall()
        gateway_section = {}
        for row in gateway_rows:
            gateway_section[row["key"]] = json.loads(row["value"])
        if not gateway_section:
            # Fallback to sensible defaults
            gateway_section = {
                "port": 18789,
                "mode": "local",
                "bind": "loopback",
                "auth": {"mode": "none"}
            }

        # Plugins
        cursor.execute("SELECT * FROM plugins")
        plugin_rows = cursor.fetchall()
        plugins_section = {"slots": {}, "entries": {}}
        for row in plugin_rows:
            plugins_section["entries"][row["id"]] = {
                "enabled": bool(row["enabled"])
            }
            if row["config"]:
               plugins_section["entries"][row["id"]]["config"] = json.loads(row["config"])

        # Devices
        cursor.execute("SELECT * FROM devices")
        devices_rows = cursor.fetchall()
        devices_list = []
        for row in devices_rows:
            device = {"id": row["id"], "role": row["role"]}
            if row["scope"]:
                device["scope"] = json.loads(row["scope"])
            devices_list.append(device)
            
        # Pairings
        cursor.execute("SELECT * FROM pairings")
        pairing_rows = cursor.fetchall()
        pairings_list = []
        for row in pairing_rows:
            pairings_list.append({
                "channel": row["channel"],
                "accountId": row["account_id"],
                "status": row["status"]
            })

        # System
        cursor.execute("SELECT * FROM system_config")
        system_rows = cursor.fetchall()
        system_section = {}
        for row in system_rows:
            try:
                system_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                system_section[row["key"]] = row["value"]

        # Providers
        cursor.execute("SELECT * FROM providers")
        providers_rows = cursor.fetchall()
        providers_section = {}
        for row in providers_rows:
            provider_obj = {
                "name": row["name"],
                "type": row["type"],
                "enabled": bool(row["enabled"])
            }
            if row["base_url"]:
                provider_obj["baseUrl"] = row["base_url"]
            if row["api_key_env"]:
                provider_obj["apiKeyEnv"] = row["api_key_env"]
            if row["config"]:
                provider_obj.update(json.loads(row["config"]))
            providers_section[row["id"]] = provider_obj

        # Nodes
        cursor.execute("SELECT * FROM nodes")
        nodes_rows = cursor.fetchall()
        nodes_section = {}
        for row in nodes_rows:
            node_obj = {
                "status": row["status"]
            }
            if row["name"]:
                node_obj["name"] = row["name"]
            if row["config"]:
                node_obj.update(json.loads(row["config"]))
            nodes_section[row["id"]] = node_obj

        # Webhooks
        cursor.execute("SELECT * FROM webhooks")
        webhooks_rows = cursor.fetchall()
        webhooks_section = {}
        for row in webhooks_rows:
            webhook_obj = {
                "type": row["type"],
                "enabled": bool(row["enabled"])
            }
            if row["config"]:
                webhook_obj.update(json.loads(row["config"]))
            webhooks_section[row["id"]] = webhook_obj

        # Skills
        cursor.execute("SELECT * FROM skills")
        skills_rows = cursor.fetchall()
        skills_section = {}
        for row in skills_rows:
            skill_obj = {"enabled": bool(row["enabled"])}
            if row["config"]:
                skill_obj.update(json.loads(row["config"]))
            skills_section[row["id"]] = skill_obj

        # Memory
        cursor.execute("SELECT * FROM memory_config")
        memory_rows = cursor.fetchall()
        memory_section = {}
        for row in memory_rows:
            try:
                memory_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                memory_section[row["key"]] = row["value"]

        # Cron
        cursor.execute("SELECT * FROM cron_jobs")
        cron_rows = cursor.fetchall()
        cron_section = {}
        for row in cron_rows:
            cron_section[row["id"]] = {
                "expression": row["expression"],
                "command": row["command"],
                "enabled": bool(row["enabled"])
            }

        # Browser
        cursor.execute("SELECT * FROM browser_profiles")
        browser_rows = cursor.fetchall()
        browser_section = {"profiles": {}}
        for row in browser_rows:
            prof_obj = {"isDefault": bool(row["is_default"])}
            if row["config"]:
                prof_obj.update(json.loads(row["config"]))
            browser_section["profiles"][row["id"]] = prof_obj

        # Hooks
        cursor.execute("SELECT * FROM hooks")
        hooks_rows = cursor.fetchall()
        hooks_section = {}
        for row in hooks_rows:
            hooks_section[row["id"]] = {
                "event": row["event"],
                "command": row["command"],
                "enabled": bool(row["enabled"])
            }

        # Secrets
        cursor.execute("SELECT * FROM secrets_config")
        secrets_rows = cursor.fetchall()
        secrets_section = {}
        for row in secrets_rows:
            sec_obj = {"value": row["value"]}
            if row["provider"]:
                sec_obj["provider"] = row["provider"]
            secrets_section[row["key"]] = sec_obj

        # Security
        cursor.execute("SELECT * FROM security_config")
        security_rows = cursor.fetchall()
        security_section = {}
        for row in security_rows:
            try:
                security_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                security_section[row["key"]] = row["value"]

        # Dashboard
        cursor.execute("SELECT * FROM dashboard_config")
        dashboard_rows = cursor.fetchall()
        dashboard_section = {}
        for row in dashboard_rows:
            try:
                dashboard_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                dashboard_section[row["key"]] = row["value"]


        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        output = {
            "meta": {
                "lastTouchedVersion": "2026.2.23",
                "lastTouchedAt": now
            },
            "providers": providers_section,
            "agents": agents_section,
            "channels": channels_section,
            "gateway": gateway_section,
            "plugins": plugins_section,
        }
        
        if devices_list:
             output["devices"] = devices_list
        if pairings_list:
             output["pairings"] = pairings_list
        if system_section:
             output["system"] = system_section
        if nodes_section:
             output["nodes"] = nodes_section
        if webhooks_section:
             output["webhooks"] = webhooks_section
        if skills_section:
             output["skills"] = skills_section
        if memory_section:
             output["memory"] = memory_section
        if cron_section:
             output["cron"] = cron_section
        if browser_section["profiles"]:
             output["browser"] = browser_section
        if hooks_section:
             output["hooks"] = hooks_section
        if secrets_section:
             output["secrets"] = secrets_section
        if security_section:
             output["security"] = security_section
        if dashboard_section:
             output["dashboard"] = dashboard_section

        # ACP
        cursor.execute("SELECT * FROM acp_config")
        acp_rows = cursor.fetchall()
        acp_section = {}
        for row in acp_rows:
            try:
                acp_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                acp_section[row["key"]] = row["value"]
        if acp_section:
            output["acp"] = acp_section

        # DNS
        cursor.execute("SELECT * FROM dns_config")
        dns_rows = cursor.fetchall()
        dns_section = {}
        for row in dns_rows:
            try:
                dns_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                dns_section[row["key"]] = row["value"]
        if dns_section:
            output["dns"] = dns_section

        # TUI
        cursor.execute("SELECT * FROM tui_config")
        tui_rows = cursor.fetchall()
        tui_section = {}
        for row in tui_rows:
            try:
                tui_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                tui_section[row["key"]] = row["value"]
        if tui_section:
            output["tui"] = tui_section

        # Approvals
        cursor.execute("SELECT * FROM approvals")
        approval_rows = cursor.fetchall()
        approval_section = {}
        for row in approval_rows:
            app_obj = {"status": row["status"]}
            if row["type"]:
                app_obj["type"] = row["type"]
            if row["config"]:
                app_obj.update(json.loads(row["config"]))
            approval_section[row["id"]] = app_obj
        if approval_section:
            output["approvals"] = approval_section

        # Directory
        cursor.execute("SELECT * FROM directory_config")
        dir_rows = cursor.fetchall()
        dir_section = {}
        for row in dir_rows:
            try:
                dir_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                dir_section[row["key"]] = row["value"]
        if dir_section:
            output["directory"] = dir_section

        # Sessions
        cursor.execute("SELECT * FROM sessions_config")
        sess_rows = cursor.fetchall()
        sess_section = {}
        for row in sess_rows:
            try:
                sess_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                sess_section[row["key"]] = row["value"]
        if sess_section:
            output["sessions"] = sess_section

        # Logs
        cursor.execute("SELECT * FROM logs_config")
        log_rows = cursor.fetchall()
        log_section = {}
        for row in log_rows:
            try:
                log_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                log_section[row["key"]] = row["value"]
        if log_section:
            output["logs"] = log_section

        # Docs
        cursor.execute("SELECT * FROM docs_config")
        doc_rows = cursor.fetchall()
        doc_section = {}
        for row in doc_rows:
            try:
                doc_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                doc_section[row["key"]] = row["value"]
        if doc_section:
            output["docs"] = doc_section

        # Global Sandbox
        cursor.execute("SELECT * FROM sandbox_config")
        sb_rows = cursor.fetchall()
        sb_section = {}
        for row in sb_rows:
            try:
                sb_section[row["key"]] = json.loads(row["value"])
            except ValueError:
                sb_section[row["key"]] = row["value"]
        if sb_section:
            output["sandbox"] = sb_section

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)

        return output


def create_default_config(db_path="openclaw_config.db"):
    """Create a database with default OpenClaw settings."""
    db = ConfigDatabase(db_path)
    db.connect()

    # Defaults matching 'minimal setup' in example

    # Gateway
    db.set_gateway("port", 18789)
    db.set_gateway("mode", "local")
    db.set_gateway("bind", "loopback")
    db.set_gateway("auth", {"mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}"})

    # Agents
    db.add_agent(
        id="main",
        name="Central Core",
        level=1,
        sandbox_mode="off"
    )

    # Channels
    db.add_channel(
        id="telegram",
        name="Telegram",
        type="telegram",
        enabled=True,
        config={
            "dmPolicy": "pairing",
            "botToken": "${OPENCLAW_TELEGRAM_BOT_TOKEN}",
            "groupPolicy": "allowlist",
            "streaming": "partial"
        }
    )

    db.add_channel(
        id="discord",
        name="Discord",
        type="discord",
        enabled=True,
        config={
            "token": "${OPENCLAW_DISCORD_TOKEN}",
            "guilds": "allowlist",
            "streaming": "full"
        }
    )

    db.add_channel(
        id="slack",
        name="Slack",
        type="slack",
        enabled=True,
        config={
            "appToken": "${OPENCLAW_SLACK_APP_TOKEN}",
            "botToken": "${OPENCLAW_SLACK_BOT_TOKEN}",
            "signingSecret": "${OPENCLAW_SLACK_SIGNING_SECRET}",
            "socketMode": True
        }
    )

    db.add_channel(
        id="signal",
        name="Signal",
        type="signal",
        enabled=True,
        config={
            "account": "${OPENCLAW_SIGNAL_ACCOUNT}",
            "bin": "signal-cli"
        }
    )

    db.add_channel(
        id="whatsapp",
        name="WhatsApp",
        type="whatsapp",
        enabled=False,
        config={
            "pairing": "qr"
        }
    )

    # Core Plugins
    db.add_plugin("@openclaw/voice-call", enabled=False, config={"provider": "twilio"})
    db.add_plugin("@openclaw/msteams", enabled=False)
    db.add_plugin("memory-lancedb", enabled=True)
    db.add_plugin("copilot-proxy", enabled=False, config={"port": 5001})

    # Final CLI Domains Baseline
    db.set_acp_config("enabled", True)
    db.set_acp_config("port", 18888)
    db.set_dns_config("mode", "tailscale")
    db.set_tui_config("theme", "lobster")
    db.set_tui_config("historyLimit", 500)
    db.add_approval("default", "enabled", type="allowlist")
    db.set_directory_config("marketplace", "clawhub")
    db.set_sessions_config("persistence", "sqlite")
    db.set_sessions_config("activeMinutes", 60)
    db.set_logs_config("level", "info")
    db.set_logs_config("path", "~/.openclaw/logs")
    db.set_docs_config("index", "local")
    db.set_sandbox_config("defaultMode", "non-main")
    db.set_sandbox_config("workspaceAccess", "none")

    # Core Providers
    db.add_provider("openai", "OpenAI", "openai", api_key_env="OPENAI_API_KEY")
    db.add_provider("anthropic", "Anthropic", "anthropic", api_key_env="ANTHROPIC_API_KEY")
    db.add_provider("google", "Google Gemini", "google", api_key_env="GEMINI_API_KEY")
    db.add_provider("groq", "Groq", "openai", base_url="https://api.groq.com/openai/v1", api_key_env="GROQ_API_KEY")
    db.add_provider("perplexity", "Perplexity", "openai", base_url="https://api.perplexity.ai", api_key_env="PERPLEXITY_API_KEY")
    db.add_provider("openrouter", "OpenRouter", "openai", base_url="https://openrouter.ai/api/v1", api_key_env="OPENROUTER_API_KEY")

    # Core Models
    # OpenAI
    db.add_model("gpt-4o", "openai", "gpt-4o", params={"temperature": 0.7})
    db.add_model("gpt-4o-mini", "openai", "gpt-4o-mini", params={"temperature": 0.7})
    db.add_model("o1-preview", "openai", "o1-preview")
    
    # Anthropic
    db.add_model("claude-3-5-sonnet", "anthropic", "claude-3-5-sonnet-20241022", params={"max_tokens": 4096})
    db.add_model("claude-3-haiku", "anthropic", "claude-3-haiku-20240307")
    
    # Google
    db.add_model("gemini-1.5-pro", "google", "gemini-1.5-pro")
    db.add_model("gemini-1.5-flash", "google", "gemini-1.5-flash")
    
    # Groq / Llama
    db.add_model("llama-3-70b", "groq", "llama3-70b-8192")
    db.add_model("llama-3-8b", "groq", "llama3-8b-8192")
    db.add_model("mixtral-8x7b", "groq", "mixtral-8x7b-32768")

    # Model Aliases
    db.add_model_alias("gpt-4", "gpt-4o")
    db.add_model_alias("claude-3-5", "claude-3-5-sonnet")
    db.add_model_alias("gemini-pro", "gemini-1.5-pro")

    # Fallbacks
    db.add_model_fallback("gpt-4o", 1)
    db.add_model_fallback("claude-3-5-sonnet", 2)
    db.add_model_fallback("gpt-4o-mini", 3)
    
    db.add_model_image_fallback("claude-3-5-sonnet", 1)
    db.add_model_image_fallback("gpt-4o", 2)

    # Skills
    db.add_skill("web_search", enabled=True, config={"engine": "google", "max_results": 5})
    db.add_skill("researcher", enabled=True, config={"depth": "deep"})
    db.add_skill("coder", enabled=True, config={"language": "python"})
    db.add_skill("vision", enabled=True)

    # Cron Jobs
    db.add_cron_job("daily-cleanup", "0 0 * * *", "memory vacuum", enabled=True)
    db.add_cron_job("weekly-backup", "0 0 * * 0", "system backup", enabled=True)

    # Memory
    db.set_memory_config("vectorStore", "chromadb")
    db.set_memory_config("embeddingModel", "text-embedding-3-small")

    # System
    db.set_system_config("heartbeat", True)
    db.set_system_config("autoUpdate", False)

    # Dashboard
    db.set_dashboard_config("theme", "dark")
    db.set_dashboard_config("refreshRate", 5000)

    # Security
    db.set_security_config("disableLocalNetwork", False)
    db.set_security_config("auditMode", "warn")

    return db
