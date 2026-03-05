---
name: openclaw-workspace-bootstrap
description: "Set up and maintain an OpenClaw agent workspace. Use when initializing a new workspace, editing identity or persona files (SOUL.md, IDENTITY.md), configuring user profile (USER.md), setting up tool notes (TOOLS.md), managing AGENTS.md operating instructions, configuring HEARTBEAT.md, or understanding workspace file layout. Triggers for: \"bootstrap workspace\", \"setup agent\", \"SOUL.md\", \"IDENTITY.md\", \"USER.md\", \"TOOLS.md\", \"AGENTS.md\", \"workspace files\", \"first run\", \"BOOTSTRAP.md\", \"agent persona\"."
metadata:
  openclaw:
    emoji: "🏠"
    category: "orchestration-core"
---

# OpenClaw Workspace Bootstrap

## Workspace Layout

```
<workspace>/
├── AGENTS.md      — Operating instructions + session ritual
├── SOUL.md        — Persona, values, boundaries, vibe
├── IDENTITY.md    — Name, creature type, emoji, avatar
├── USER.md        — User profile, preferred address, context
├── TOOLS.md       — Local tool notes (device names, SSH hosts, etc.)
├── HEARTBEAT.md   — Periodic check tasks (leave blank to skip)
├── BOOTSTRAP.md   — One-time first-run ritual (auto-deleted after use)
├── MEMORY.md      — Curated long-term memory (optional)
├── memory/
│   └── YYYY-MM-DD.md  — Daily session logs
└── skills/        — Workspace-level skill overrides
```

## Initialization

```bash
openclaw setup
# Creates ~/.openclaw/openclaw.json and workspace template files
```

To skip BOOTSTRAP.md creation:
```json5
{ agent: { skipBootstrap: true } }
```

## File-by-File Guide

**AGENTS.md** — Session ritual and operating rules. Injected every session.
Minimum content: session startup sequence (read SOUL → USER → memory), memory write policy, safety boundaries.

**SOUL.md** — Persona and values. "You're not a chatbot. You're becoming someone."
Keep genuine: opinions, resourcefulness, boundaries. Evolve it as the agent develops.

**IDENTITY.md** — Name + emoji + vibe + avatar path. Affects platform display (macOS Skills UI, channel avatars).

**USER.md** — Who the agent is helping. Update continually: timezone, projects, preferences, communication style.

**TOOLS.md** — Local-only notes. Camera names, SSH aliases, TTS voice preferences, device nicknames. Skills are shared — this file is yours.

**HEARTBEAT.md** — Leave empty (or comments only) to disable periodic checks. Add task lines to enable batch monitoring (email, calendar, weather checks).

**BOOTSTRAP.md** — One-time ritual. Agent reads it, follows it, then **deletes it**. Not recreated after deletion. Use for: set your name, read the codebase, introduce yourself.

## What NOT to Put in the Workspace

- Credentials, API keys (keep in `~/.openclaw/` config, not workspace)
- Session transcripts (auto-stored at `~/.openclaw/agents/{id}/sessions/`)
- Docker/infra config (lives in `openclaw.json`)

## Git Backup

Workspace = private memory. Back up in a private git repo:
```bash
cd <workspace>
git init && git remote add origin git@github.com:you/my-agent-workspace.git
echo "memory/" >> .gitignore  # optional: exclude daily logs
git add -A && git commit -m "backup workspace"
```

Never commit credentials. Use `.gitignore` for `*.key`, `.env`, `credentials/`.

See [references/file-templates.md](references/file-templates.md) for starter content for each file.
