# OpenClaw Config Generator

A SQLite-based configuration database for OpenClaw that allows storing providers, models, channels, and agents, then generates an `openclaw.json` configuration file from the database.

## Quick Start

```bash
cd packages/orchestration

# Initialize database with default providers, models, and channels
uv run python -m openclaw.config_generator init

# Generate openclaw.json from the database
uv run python -m openclaw.config_generator generate

# List what's in the database
uv run python -m openclaw.config_generator providers
uv run python -m openclaw.config_generator models
uv run python -m openclaw.config_generator channels
uv run python -m openclaw.config_generator agents
```

## Installation

The config generator is included in the orchestration package:

```bash
cd packages/orchestration
uv sync
```

## Database Schema

### Tables

| Table | Description |
|-------|-------------|
| providers | AI model providers (OpenAI, Anthropic, Google, etc.) |
| models | Models associated with providers |
| model_aliases | Aliases mapped to specific model IDs |
| model_fallbacks | Fallback order for chat models |
| model_image_fallbacks | Fallback order for image models |
| channels | Messaging channels (Telegram, Discord, Slack, etc.) |
| pairings | Channel Account pairings for authenticated sessions |
| devices | Authorized devices, roles, and scopes |
| agents | Agent configurations (level, sandbox, orchestration) |
| gateway_settings | Gateway configuration (port, mode, bind, auth) |
| plugins | Plugin configurations |
| system_config | General system settings (heartbeat, limits, cron) |
| nodes | Managed compute nodes for code execution, browser, etc |
| webhooks | Configured incoming webhooks |
| skills | Assistant skills (enabled toggles and configs) |
| memory_config | Long-term memory index and store configurations |
| cron_jobs | Scheduled commands and scripts |
| browser_profiles | Pre-configured Chrome/Playwright remote browser profiles |
| hooks | Outgoing hooks for app events |
| secrets_config | Mappings and settings for secret resolution |
| security_config | Hardening settings and audit exemptions |
| dashboard_config | Visual UI web dashboard configs |

## Python API

### ConfigDatabase Class

```python
from openclaw.config_generator import ConfigDatabase
```

#### Constructor

```python
db = ConfigDatabase(db_path: str = "openclaw_config.db")
```

#### Methods

##### connect()
Connect to the database and create tables.

```python
db.connect()
```

##### close()
Close the database connection.

```python
db.close()
```

##### add_provider(id, name, type, base_url=None, api_key_env=None, enabled=True, config=None)
Add a provider to the database.

##### add_model(id, provider_id, name, type="chat", params=None, enabled=True)
Add a model to the database.

##### add_channel(id, name, type, enabled=True, config=None)
Add a channel to the database.

##### add_agent(id, name, level=1, reports_to=None, subordinates=None, model_id=None, sandbox_mode="off", orchestration_role=None, config=None)
Add an agent to the database.

##### add_model_alias(alias, model_id)
Map a custom alias to an existing model.

##### add_model_fallback(model_id, priority)
Set a sequential fallback position for chat models.

##### add_model_image_fallback(model_id, priority)
Set a sequential fallback position for image models.

##### add_pairing(channel, account_id, status="approved")
Pre-approve a channel-account pairing.

##### add_device(id, role, scope=None)
Initialize a hardware/software device configuration.

##### set_gateway(key, value)
Set a gateway setting.

##### set_system_config(key, value)
Set a generic system configuration (heartbeat, cron toggles, limits).

##### add_node(id, name=None, status="pending", config=None)
Add a compute node configuration.

##### add_webhook(id, type, enabled=True, config=None)
Add a webhook configuration.

##### add_plugin(id, enabled=True, config=None)
Add a plugin setting.

##### add_skill(id, enabled=True, config=None)
Add a skill.

##### set_memory_config(key, value)
Set a memory configuration.

##### add_cron_job(id, expression, command, enabled=True)
Add a cron job.

##### add_browser_profile(id, is_default=False, config=None)
Add a browser profile.

##### add_hook(id, event, command, enabled=True)
Add an internal hook.

##### set_secret_config(key, value, provider=None)
Set a secret configuration mapping.

##### set_security_config(key, value)
Set a security configuration.

##### set_dashboard_config(key, value)
Set a dashboard configuration.

##### generate_openclaw_json(output_path=None)
Generate openclaw.json from the database. Returns dict.

### Helper Functions

##### create_default_config(db_path="openclaw_config.db")
Create a database with default OpenClaw settings.

## CLI Commands

The CLI supports a global `--db` argument to specify the database file (defaults to `openclaw_config.db`).

| Command | Description |
|---------|-------------|
| `init` | Create database with defaults |
| `generate` | Generate config file (supports `--output` or `-o` flag, defaults to `openclaw.json`) |
| `providers` | List providers |
| `models` | List models |
| `aliases` | List model aliases |
| `fallbacks` | List model fallbacks (chat and image) |
| `channels` | List channels |
| `pairings` | List channel pairings |
| `agents` | List agents |
| `devices` | List authorized devices |
| `system` | List system configuration |
| `nodes` | List compute nodes |
| `webhooks` | List webhook configurations |
| `skills` | List skills |
| `memory` | List memory configuration |
| `cron` | List cron jobs |
| `browser` | List browser profiles |
| `hooks` | List internal hooks |
| `secrets` | List secret configurations |
| `security` | List security configurations |
| `dashboard` | List dashboard configuration |

## Examples

### Example 1: Minimal Setup

```python
from openclaw.config_generator import create_default_config

# Create database with defaults
db = create_default_config()

# Generate config file
db.generate_openclaw_json("openclaw.json")

db.close()
```

### Example 2: Custom Provider

```python
from openclaw.config_generator import ConfigDatabase

db = ConfigDatabase("my_config.db")
db.connect()

# Add a custom provider
db.add_provider(
    id="mistral",
    name="Mistral AI",
    type="mistral",
    base_url="https://api.mistral.ai/v1",
    api_key_env="MISTRAL_API_KEY"
)

# Add models for the provider
db.add_model("mistral-large", "mistral", "mistral-large-latest", params={"temperature": 0.7})
db.add_model("mistral-small", "mistral", "mistral-small-latest", params={"temperature": 0.7})

# Generate config
db.generate_openclaw_json("openclaw.json")
db.close()
```

### Example 3: Custom Agent Hierarchy

```python
from openclaw.config_generator import ConfigDatabase

db = ConfigDatabase("agents.db")
db.connect()

# Add L1 agent (strategic)
db.add_agent(
    id="clawdia_prime",
    name="Head of Development",
    level=1,
    sandbox_mode="off"
)

# Add L2 agent (tactical)
db.add_agent(
    id="pumplai_pm",
    name="Project Manager",
    level=2,
    reports_to="clawdia_prime",
    subordinates=["l3_specialist"],
    orchestration_role="tactical"
)

# Add L3 agent
db.add_agent(
    id="l3_specialist",
    name="L3 Specialist",
    level=3,
    reports_to="pumplai_pm",
    sandbox_mode="all"
)

# Generate config
db.generate_openclaw_json("openclaw.json")
db.close()
```

### Example 4: Multiple Channels

```python
from openclaw.config_generator import ConfigDatabase

db = ConfigDatabase("channels.db")
db.connect()

# Add Telegram
db.add_channel("telegram", "Telegram", "telegram", True, {
    "botToken": "${OPENCLAW_TELEGRAM_BOT_TOKEN}",
    "dmPolicy": "pairing",
    "groupPolicy": "allowlist"
})

# Add Discord
db.add_channel("discord", "Discord", "discord", True, {
    "botToken": "${OPENCLAW_DISCORD_BOT_TOKEN}"
})

# Add Slack
db.add_channel("slack", "Slack", "slack", True, {
    "botToken": "${OPENCLAW_SLACK_BOT_TOKEN}",
    "signingSecret": "${OPENCLAW_SLACK_SIGNING_SECRET}"
})

db.generate_openclaw_json("openclaw.json")
db.close()
```

### Example 5: Gateway Configuration

```python
from openclaw.config_generator import ConfigDatabase

db = ConfigDatabase("gateway.db")
db.connect()

# Configure gateway settings
db.set_gateway("port", 18789)
db.set_gateway("mode", "local")
db.set_gateway("bind", "loopback")
db.set_gateway("auth", {"mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}"})

db.generate_openclaw_json("openclaw.json")
db.close()
```

### Example 6: Plugins

```python
from openclaw.config_generator import ConfigDatabase

db = ConfigDatabase("plugins.db")
db.connect()

# Add memory plugin
db.add_plugin("memory-memu", True, {
    "geminiApiKey": "${GEMINI_API_KEY}"
})

# Add Telegram plugin
db.add_plugin("telegram", True, {})

db.generate_openclaw_json("openclaw.json")
db.close()
```

## Output Format

The generated `openclaw.json`:

```json
{
  "meta": {
    "lastTouchedVersion": "2026.2.23",
    "lastTouchedAt": "2026-03-05T00:00:00.000Z"
  },
  "agents": {
    "defaults": {
      "model": { "primary": "gpt-4o" },
      "models": { "gpt-4o": { "params": { "temperature": 0.7 } } },
      "maxConcurrent": 4,
      "subagents": { "maxConcurrent": 8 },
      "sandbox": { "mode": "non-main", "workspaceAccess": "none", "scope": "session" }
    },
    "list": [
      { "id": "main", "name": "Central Core", "level": 1, "sandbox": { "mode": "off" } }
    ]
  },
  "channels": {
    "telegram": { "enabled": true, "dmPolicy": "pairing", "botToken": "${OPENCLAW_TELEGRAM_BOT_TOKEN}" }
  },
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": { "mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}" }
  },
  "plugins": { "slots": {}, "entries": {} }
}
```

## File Locations

| File | Description |
|------|-------------|
| openclaw_config.db | SQLite database (created in working directory) |
| openclaw.json | Generated configuration file |

## Notes

- The database uses SQLite. Each ConfigDatabase instance connects to the same file.
- Use json.dumps() for complex config objects before storing.
- Environment variables in config values use ${VAR_NAME} syntax and are resolved at runtime by OpenClaw.
