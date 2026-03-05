"""
OpenClaw Config Generator

This module provides a SQLite-based configuration database for OpenClaw.
It allows storing providers, models, channels, and agents, then generates
an openclaw.json configuration file from the database.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Any


class ConfigDatabase:
    """SQLite database for OpenClaw configuration."""
    
    def __init__(self, db_path: str = "openclaw_config.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def connect(self) -> None:
        """Connect to the database and create tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _create_tables(self) -> None:
        """Create all necessary tables."""
        cursor = self.conn.cursor()
        
        # Providers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS providers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                base_url TEXT,
                api_key_env TEXT,
                enabled INTEGER DEFAULT 1,
                config TEXT
            )
        """)
        
        # Models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'chat',
                params TEXT,
                enabled INTEGER DEFAULT 1,
                FOREIGN KEY (provider_id) REFERENCES providers(id)
            )
        """)
        
        # Channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                config TEXT
            )
        """)
        
        # Agents table (Index/Cache + Metadata)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,          -- Normalised slug: [a-z0-9-_]
                name TEXT NOT NULL,
                path TEXT NOT NULL,           -- Relative path from OPENCLAW_ROOT
                level INTEGER DEFAULT 1,
                reports_to TEXT,
                subordinates TEXT,
                model_id TEXT,
                provider_id TEXT,
                sandbox_mode TEXT,
                orchestration_role TEXT,
                enabled INTEGER DEFAULT 1,
                last_indexed DATETIME DEFAULT CURRENT_TIMESTAMP,
                config TEXT,                  -- Legacy config field
                metadata_json TEXT,           -- Catch-all for extra UI/dashboard fields
                FOREIGN KEY (model_id) REFERENCES models(id)
            )
        """)

        # Audit log for change tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,           -- UUID
                request_id TEXT,              -- UUID to correlate batch changes
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                actor TEXT,                   -- 'system' or user identifier
                action TEXT,                  -- 'update_staged', 'apply', 'agent_create', etc.
                target TEXT,                  -- 'gateway', 'agent:bot1', etc.
                before_json TEXT,
                after_json TEXT,
                diff_summary TEXT,            -- Human-readable summary
                status TEXT,                  -- 'success', 'failure'
                message TEXT,
                config_hash TEXT              -- Hash of openclaw.json
            )
        """)
        
        # Gateway settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gateway_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Plugins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plugins (
                id TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                config TEXT
            )
        """)
        
        self.conn.commit()
    
    # Providers
    def add_provider(self, id: str, name: str, type: str, base_url: Optional[str] = None,
                     api_key_env: Optional[str] = None, enabled: bool = True,
                     config: Optional[dict] = None) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO providers (id, name, type, base_url, api_key_env, enabled, config) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id, name, type, base_url, api_key_env, enabled, json.dumps(config) if config else None)
        )
        self.conn.commit()
    
    def get_providers(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM providers")
        return [dict(row) for row in cursor.fetchall()]
    
    # Models
    def add_model(self, id: str, provider_id: str, name: str, type: str = "chat",
                  params: Optional[dict] = None, enabled: bool = True) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO models (id, provider_id, name, type, params, enabled) VALUES (?, ?, ?, ?, ?, ?)",
            (id, provider_id, name, type, json.dumps(params) if params else None, enabled)
        )
        self.conn.commit()
    
    def get_models(self, provider_id: Optional[str] = None) -> list[dict]:
        cursor = self.conn.cursor()
        if provider_id:
            cursor.execute("SELECT * FROM models WHERE provider_id = ?", (provider_id,))
        else:
            cursor.execute("SELECT * FROM models")
        return [dict(row) for row in cursor.fetchall()]
    
    # Channels
    def add_channel(self, id: str, name: str, type: str, enabled: bool = True,
                    config: Optional[dict] = None) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO channels (id, name, type, enabled, config) VALUES (?, ?, ?, ?, ?)",
            (id, name, type, enabled, json.dumps(config) if config else None)
        )
        self.conn.commit()
    
    def get_channels(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM channels")
        return [dict(row) for row in cursor.fetchall()]
    
    # Agents
    def add_agent(self, id: str, name: str, level: int = 1, reports_to: Optional[str] = None,
                  subordinates: Optional[list[str]] = None, model_id: Optional[str] = None,
                  sandbox_mode: str = "off", orchestration_role: Optional[str] = None,
                  config: Optional[dict] = None) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO agents (id, name, level, reports_to, subordinates, model_id, sandbox_mode, orchestration_role, config) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (id, name, level, reports_to, json.dumps(subordinates) if subordinates else None,
             model_id, sandbox_mode, orchestration_role, json.dumps(config) if config else None)
        )
        self.conn.commit()
    
    def get_agents(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM agents")
        return [dict(row) for row in cursor.fetchall()]
    
    # Gateway
    def set_gateway(self, key: str, value: Any) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO gateway_settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value))
        )
        self.conn.commit()
    
    def get_gateway(self) -> dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM gateway_settings")
        return {row["key"]: row["value"] for row in cursor.fetchall()}
    
    # Plugins
    def add_plugin(self, id: str, enabled: bool = True, config: Optional[dict] = None) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO plugins (id, enabled, config) VALUES (?, ?, ?)",
            (id, enabled, json.dumps(config) if config else None)
        )
        self.conn.commit()
    
    def get_plugins(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM plugins")
        return [dict(row) for row in cursor.fetchall()]
    
    # Generate Config
    def generate_openclaw_json(self, output_path: Optional[str] = None) -> dict:
        """Generate openclaw.json configuration from the database."""
        config = {
            "meta": {
                "lastTouchedVersion": "2026.2.23",
                "lastTouchedAt": "2026-03-05T00:00:00.000Z"
            },
            "agents": {
                "defaults": {
                    "model": {},
                    "maxConcurrent": 4,
                    "subagents": {"maxConcurrent": 8},
                    "sandbox": {"mode": "non-main", "workspaceAccess": "none", "scope": "session"}
                },
                "list": []
            },
            "channels": {},
            "gateway": {
                "port": 18789,
                "mode": "local",
                "bind": "loopback",
                "auth": {"mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}"}
            },
            "plugins": {"slots": {}, "entries": {}}
        }
        
        # Add providers and models
        providers = self.get_providers()
        models = self.get_models()
        
        provider_models = {}
        for model in models:
            pid = model["provider_id"]
            if pid not in provider_models:
                provider_models[pid] = {}
            model_name = model["name"]
            provider_models[pid][model_name] = {"params": json.loads(model["params"]) if model["params"] else {}}
        
        if models:
            first_model = models[0]
            config["agents"]["defaults"]["model"]["primary"] = first_model["name"]
            config["agents"]["defaults"]["models"] = provider_models.get(first_model["provider_id"], {})
        
        # Add agents
        for agent in self.get_agents():
            agent_entry = {
                "id": agent["id"],
                "name": agent["name"],
                "level": agent["level"],
                "sandbox": {"mode": agent["sandbox_mode"] or "off"}
            }
            if agent["reports_to"]:
                agent_entry["reports_to"] = agent["reports_to"]
            if agent["subordinates"]:
                agent_entry["subordinates"] = json.loads(agent["subordinates"])
            if agent["orchestration_role"]:
                agent_entry["orchestration"] = {"role": agent["orchestration_role"]}
            config["agents"]["list"].append(agent_entry)
        
        # Add channels
        for channel in self.get_channels():
            if channel["enabled"]:
                ch_config = json.loads(channel["config"]) if channel["config"] else {}
                ch_config["enabled"] = True
                config["channels"][channel["type"]] = ch_config
        
        # Add plugins
        for plugin in self.get_plugins():
            if plugin["enabled"]:
                plugin_config = json.loads(plugin["config"]) if plugin["config"] else {}
                config["plugins"]["entries"][plugin["id"]] = {"enabled": True, "config": plugin_config}
        
        # Add gateway settings
        for key, value in self.get_gateway().items():
            try:
                config["gateway"][key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                config["gateway"][key] = value
        
        if output_path:
            with open(output_path, "w") as f:
                json.dump(config, f, indent=2)
        
        return config


def create_default_config(db_path: str = "openclaw_config.db") -> ConfigDatabase:
    """Create a config database with default OpenClaw settings."""
    db = ConfigDatabase(db_path)
    db.connect()
    
    # Add default providers
    db.add_provider("openai", "OpenAI", "openai", "https://api.openai.com/v1", "OPENAI_API_KEY")
    db.add_provider("anthropic", "Anthropic", "anthropic", "https://api.anthropic.com", "ANTHROPIC_API_KEY")
    db.add_provider("google", "Google Gemini", "google", "https://generativelanguage.googleapis.com/v1", "GEMINI_API_KEY")
    db.add_provider("openrouter", "OpenRouter", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY")
    
    # Add default models
    db.add_model("gpt-4o", "openai", "gpt-4o", "chat", {"temperature": 0.7})
    db.add_model("gpt-4o-mini", "openai", "gpt-4o-mini", "chat", {"temperature": 0.7})
    db.add_model("claude-3-5-sonnet", "anthropic", "claude-3-5-sonnet-20241022", "chat", {"temperature": 0.7})
    db.add_model("claude-3-haiku", "anthropic", "claude-3-haiku-20240307", "chat", {"temperature": 0.7})
    db.add_model("gemini-2.0-flash", "google", "gemini-2.0-flash-exp", "chat", {"temperature": 0.7})
    db.add_model("gemini-2.5-flash", "google", "google-gemini-cli/gemini-2.5-flash", "chat", {"temperature": 0.7})
    
    # Add default channels
    db.add_channel("telegram", "Telegram", "telegram", True, {
        "dmPolicy": "pairing",
        "botToken": "${OPENCLAW_TELEGRAM_BOT_TOKEN}",
        "groupPolicy": "allowlist",
        "streaming": "partial"
    })
    
    # Add default agents
    db.add_agent("main", "Central Core", 1, None, None, "claude-3-5-sonnet")
    
    # Add gateway defaults
    db.set_gateway("port", 18789)
    db.set_gateway("mode", "local")
    db.set_gateway("bind", "loopback")
    
    return db


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python config_generator.py <command>")
        print("Commands:")
        print("  init       - Create a new config database with defaults")
        print("  generate   - Generate openclaw.json from database")
        print("  providers  - List all providers")
        print("  models     - List all models")
        print("  channels   - List all channels")
        print("  agents     - List all agents")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        db = create_default_config()
        print("Created default config database")
        db.close()
    elif command == "generate":
        db = ConfigDatabase()
        db.connect()
        config = db.generate_openclaw_json("openclaw.json")
        print("Generated openclaw.json")
        db.close()
    elif command == "providers":
        db = ConfigDatabase()
        db.connect()
        for p in db.get_providers():
            print(f"  {p['id']}: {p['name']} ({p['type']})")
        db.close()
    elif command == "models":
        db = ConfigDatabase()
        db.connect()
        for m in db.get_models():
            print(f"  {m['id']}: {m['provider_id']} - {m['name']}")
        db.close()
    elif command == "channels":
        db = ConfigDatabase()
        db.connect()
        for c in db.get_channels():
            print(f"  {c['id']}: {c['name']} ({c['type']})")
        db.close()
    elif command == "agents":
        db = ConfigDatabase()
        db.connect()
        for a in db.get_agents():
            print(f"  {a['id']}: {a['name']} (level {a['level']})")
        db.close()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
