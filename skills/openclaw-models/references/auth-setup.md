# Model Auth Setup

## Anthropic (Preferred: Claude Code Token)

```bash
# Set up Claude Code CLI token (recommended)
claude setup-token

# Verify
openclaw models status
# Should show: auth.oauth.status: valid
```

This avoids managing API keys manually. Token auto-refreshes.

## API Key Setup (Alternative)

```json5
{
  models: {
    providers: {
      anthropic: { apiKey: "${ANTHROPIC_API_KEY}" }
    }
  }
}
```

Set `ANTHROPIC_API_KEY` in shell or via `openclaw config set models.providers.anthropic.apiKey YOUR_KEY`.

## OpenRouter

```json5
{
  models: {
    providers: {
      openrouter: { apiKey: "${OPENROUTER_API_KEY}" }
    }
  }
}
```

Note: use `openrouter/` prefix for all OpenRouter models in `primary`/`fallbacks`.

## Google Gemini CLI (Zero-Key Local)

```bash
# Install gemini CLI then:
openclaw models set google-gemini-cli/gemini-2.5-flash
```

No API key needed — uses Gemini CLI's own auth.

## Status Flags

```bash
openclaw models status --check
# Exit codes:
# 0 — all good
# 1 — missing or expired auth
# 2 — auth expiring soon (use in CI pre-flight)
```

## Auth Profiles (Multiple Providers)

```json5
{
  models: {
    providers: {
      anthropic: { apiKey: "${ANTHROPIC_API_KEY}" },
      openai: { apiKey: "${OPENAI_API_KEY}" },
      openrouter: { apiKey: "${OPENROUTER_API_KEY}" }
    }
  }
}
```

Provider auth failover happens inside a provider before moving to the next model in `fallbacks`.
