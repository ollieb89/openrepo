---
name: openclaw-models
description: "Model selection, fallbacks, and configuration in OpenClaw. Use when switching models, setting primary/fallback models, adding model aliases, scanning OpenRouter for free models, checking auth status, configuring per-agent model overrides, or troubleshooting \"model not allowed\" errors. Triggers for: \"change model\", \"model fallback\", \"OpenRouter\", \"/model\", \"model alias\", \"set primary model\", \"model auth\", \"model scan\", \"image model\", \"models list\", \"model not allowed\"."
metadata:
  openclaw:
    emoji: "🤖"
    category: "orchestration-core"
---

# OpenClaw Model Configuration

## Quick Model Operations

```bash
# Interactive picker
openclaw models
# or in chat: /model

# List available models
openclaw models list          # configured models
openclaw models list --all    # full catalog

# Set primary model
openclaw models set anthropic/claude-sonnet-4-5

# Check auth and status
openclaw models status
openclaw models status --check   # exits 1 if expired, 2 if expiring soon
```

## Selection Priority

1. `agents.defaults.model.primary` (or `agents.list[].model` override)
2. `agents.defaults.model.fallbacks` (in order)
3. Provider auth failover (within a provider, before next fallback)

## Config: Primary + Fallbacks

```json5
{
  agents: {
    defaults: {
      model: {
        primary: "anthropic/claude-sonnet-4-5",
        fallbacks: [
          "openai/gpt-4o",
          "openrouter/google/gemini-2.5-pro"
        ]
      },
      imageModel: {
        primary: "openai/gpt-4o",
        fallbacks: ["openrouter/google/gemini-3-pro-preview"]
      }
    }
  }
}
```

## Model Aliases

```bash
openclaw models aliases list
openclaw models aliases add "fast" anthropic/claude-haiku-4-5
openclaw models aliases remove "fast"
```

In chat: `/model fast` selects via alias.

## "Model Not Allowed" Error

Happens when `agents.defaults.models` is set (acts as allowlist). Fix:
```json5
{
  agents: {
    defaults: {
      models: {
        "anthropic/claude-sonnet-4-5": { alias: "Sonnet" },
        "anthropic/claude-opus-4-6": { alias: "Opus" },
        // add the model you need here, or remove the models key to allow all
      }
    }
  }
}
```

## OpenRouter ID Format

For models with `/` in the model name (OpenRouter-style), always include provider prefix:
```
✓  openrouter/moonshotai/kimi-k2
✗  moonshotai/kimi-k2   (ambiguous)
```

## Scanning for Free Models

```bash
# Scan OpenRouter free catalog
openclaw models scan

# With live probing (slower, more accurate)
openclaw models scan --min-params 7 --max-age-days 90

# Auto-configure best model
openclaw models scan --set-default --set-image
```

Ranked by: image support → tool latency → context size → parameter count.

## Per-Agent Model Override

```json5
{
  agents: {
    list: [
      {
        id: "pumplai_pm",
        model: {
          primary: "anthropic/claude-opus-4-6",
          fallbacks: ["anthropic/claude-sonnet-4-5"]
        }
      }
    ]
  }
}
```

See [references/auth-setup.md](references/auth-setup.md) for Anthropic Claude Code token setup and OAuth provider configuration.
