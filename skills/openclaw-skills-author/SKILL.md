---
name: openclaw-skills-author
description: Create, configure, and publish OpenClaw-compatible skills. Use when writing a new SKILL.md, adding gating requirements (bins/env/config), configuring per-skill env vars or API keys, setting up auto-installers (brew/npm/uv), publishing to ClawHub, disabling or enabling bundled skills, or troubleshooting skill load failures. Triggers for: "create a skill", "write SKILL.md", "skill gating", "clawhub install", "skill not loading", "skill env var", "user-invocable skill", "command-dispatch", "openclaw skill format", "skill requires".
---

# Authoring OpenClaw Skills

Skills are AgentSkills-compatible directories loaded by OpenClaw from three locations (highest precedence first): `<workspace>/skills/`, `~/.openclaw/skills/`, bundled skills.

## Minimal SKILL.md

```markdown
---
name: my-skill
description: What this skill does and when to trigger it. Be specific.
---

# My Skill

Instructions here.
```

## Full Frontmatter Reference

```markdown
---
name: my-skill
description: "Detailed description. Mention triggers explicitly."
homepage: https://github.com/you/my-skill
user-invocable: true
disable-model-invocation: false
command-dispatch: tool
command-tool: my_tool_name
command-arg-mode: raw
metadata: {"openclaw": {"emoji": "🔧", "requires": {"bins": ["uv"], "env": ["MY_API_KEY"]}, "primaryEnv": "MY_API_KEY", "os": ["darwin", "linux"]}}
---
```

**Key fields:**
- `user-invocable: true` → exposed as `/my-skill` slash command (default: true)
- `disable-model-invocation: true` → excluded from model system prompt, still user-invocable
- `command-dispatch: tool` → slash command bypasses model, calls tool directly
- `metadata.openclaw.always: true` → always include, skip all gates

## Gating

Skill only loads when gates pass:

```json
{
  "openclaw": {
    "requires": {
      "bins": ["ffmpeg"],          // all must be on PATH
      "anyBins": ["brew", "apt"],  // at least one on PATH
      "env": ["GEMINI_API_KEY"],   // env var must exist
      "config": ["browser.enabled"] // openclaw.json path must be truthy
    }
  }
}
```

`requires.bins` checked on host at load time. For sandboxed agents, binary must also exist inside the container.

## Auto-Installer

```json
{
  "openclaw": {
    "install": [
      {
        "id": "brew",
        "kind": "brew",
        "formula": "ffmpeg",
        "bins": ["ffmpeg"],
        "label": "Install ffmpeg (brew)",
        "os": ["darwin"]
      },
      {
        "id": "apt",
        "kind": "download",
        "url": "https://example.com/ffmpeg-linux.tar.gz",
        "archive": "tar.gz",
        "bins": ["ffmpeg"],
        "label": "Download ffmpeg (linux)",
        "os": ["linux"]
      }
    ]
  }
}
```

`kind` options: `brew`, `node`, `go`, `uv`, `download`

## Config Overrides (`openclaw.json`)

```json5
{
  skills: {
    entries: {
      "my-skill": {
        enabled: true,
        apiKey: "KEY_VALUE_HERE",
        env: {
          "MY_API_KEY": "KEY_VALUE_HERE",
          "MY_ENDPOINT": "https://api.example.com"
        },
        config: {
          "model": "fast"
        }
      }
    }
  }
}
```

`apiKey` maps to `primaryEnv` in skill metadata. `env` injected if not already set. `config` is a free-form bag readable by skill instructions.

## ClawHub

```bash
# Install a skill from the registry
clawhub install skill-slug

# Update all installed skills
clawhub update --all

# Publish your skill
clawhub sync --all
```

Registry: https://clawhub.com

## `{baseDir}` in Instructions

Reference skill folder from within SKILL.md instructions:

```markdown
Run the bundled script:
\`\`\`bash
python3 {baseDir}/scripts/process.py
\`\`\`
```

## Token Cost

Each skill adds to system prompt: ~195 chars base + ~97 chars + name/description/location per skill. ~24 tokens per skill. Keep descriptions tight.

See [references/skill-examples.md](references/skill-examples.md) for complete worked examples.
See [references/skill-directory-layout.md](references/skill-directory-layout.md) for directory conventions.
