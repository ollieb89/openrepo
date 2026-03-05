# OpenClaw API Endpoints

This document maps all the API endpoints used by the OpenClaw codebase.

## External Provider APIs

### AI Model Providers

| Provider | Base URL | Endpoints |
|----------|----------|-----------|
| OpenAI | `https://api.openai.com/v1` | `/chat/completions`, `/embeddings` |
| Anthropic | `https://api.anthropic.com` | `/v1/messages`, `/v1OAuth/usage` |
| Google Gemini | `https://generativelanguage.googleapis.com/v1` | `/models/:generateContent` |
| OpenRouter | `https://openrouter.ai/api/v1` | `/chat/completions`, `/models` |
| Ollama | `http://localhost:11434` | `/api/chat`, `/api/tags` |
| ZAI (China) | `https://api.z.ai/api/paas/v4` | `/chat/completions` |
| Venice AI | `https://api.venice.ai/api/v1` | `/chat/completions` |
| Qwen Portal | `https://chat.qwen.ai` | `/api/v1/oauth2/token` |
| Perplexity | `https://api.perplexity.ai` | `/chat/completions` |
| GitHub Copilot | `https://api.individual.githubcopilot.com` | `/v1/chat/completions` |

### TTS Providers

| Provider | Base URL |
|----------|----------|
| ElevenLabs | `https://api.elevenlabs.io` |
| OpenAI TTS | `https://api.openai.com/v1` |

### Memory/Embedding Providers

| Provider | Base URL |
|----------|----------|
| OpenAI Embeddings | `https://api.openai.com/v1` |
| Google Gemini Embeddings | `https://generativelanguage.googleapis.com/v1` |

## Messaging Channel APIs

### Telegram
- **Base URL**: `https://api.telegram.org`
- **Endpoint pattern**: `/bot{botToken}/{method}`

### Discord
- **Base URL**: `https://discord.com/api/v10`
- **Endpoints**: `/channels/{id}/messages`, `/guilds/{id}`, `/users/@me`

### Slack
- **Base URL**: `https://slack.com/api`
- **Endpoints**: `/chat.postMessage`, `/conversations.history`

### Signal
- **Base URL**: Configurable (self-hosted)
- **Endpoints**: `/api/v1/rpc`, `/api/v1/check`, `/api/v1/events`

### Other Channels
- Microsoft Teams: `/api/messages` (configurable)
- Matrix: Client-server API
- Feishu (Lark): `/open_apis/{endpoint}`
- LINE: `/v2/bot/message`

## Internal Gateway APIs

### Browser Control Server
- `GET/POST /profiles` - Browser profiles
- `POST /start`, `POST /stop` - Browser control
- `POST /navigate` - Navigate to URL
- `GET /snapshot` - Get page snapshot
- `POST /screenshot` - Take screenshot
- `GET/POST /tabs` - Tab management
- `GET/POST /cookies` - Cookie management

### Media Server
- `GET /media/:id` - Serve media files

### Gateway HTTP
- WebSocket endpoints for real-time communication
- HTTP endpoints for REST API

## Usage/Quota APIs

| Provider | Endpoint |
|----------|----------|
| Anthropic | `https://api.anthropic.com/api/oauth/usage` |
| Claude (org) | `https://claude.ai/api/organizations/{orgId}/usage` |
| ZAI | `https://api.z.ai/api/monitor/usage/quota/limit` |
| MiniMax | `https://api.minimaxi.com/v1/api/openplatform/coding_plan/remains` |

## Configuration

The OpenClaw config (`openclaw.json`) supports the following provider configurations:

```json
{
  "models": {
    "providers": {
      "openai": {
        "apiKey": "${OPENAI_API_KEY}",
        "baseUrl": "https://api.openai.com/v1"
      },
      "anthropic": {
        "apiKey": "${ANTHROPIC_API_KEY}"
      },
      "google": {
        "apiKey": "${GEMINI_API_KEY}"
      }
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "${OPENCLAW_TELEGRAM_BOT_TOKEN}"
    }
  }
}
```

## Environment Variables

Key environment variables used:

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key  
- `GEMINI_API_KEY` - Google Gemini API key
- `OPENROUTER_API_KEY` - OpenRouter API key
- `OPENCLAW_TELEGRAM_BOT_TOKEN` - Telegram bot token
- `OPENCLAW_GATEWAY_TOKEN` - Gateway authentication token

## Using the Config Generator

Use the Python config generator to create `openclaw.json` from a SQLite database:

```bash
# Initialize database with defaults
python -m openclaw.config_generator init

# Add custom provider
# (use the Python API)

# Generate openclaw.json
python -m openclaw.config_generator generate

# List items
python -m openclaw.config_generator providers
python -m openclaw.config_generator models
python -m openclaw.config_generator channels
python -m openclaw.config_generator agents
```
