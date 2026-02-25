# Skill Directory Layout

## Standard Layout

```
my-skill/
├── SKILL.md              (required)
├── scripts/              (optional)
│   ├── main.py
│   └── helpers.py
├── references/           (optional)
│   ├── api-docs.md
│   └── examples.md
└── assets/               (optional)
    └── template.html
```

## Minimal (Single File)

```
my-skill/
└── SKILL.md
```

Fine for knowledge/reference skills with no external resources.

## Loading Precedence

```
<workspace>/skills/my-skill/  ← highest (overrides all)
~/.openclaw/skills/my-skill/  ← managed/local
[bundled in install]           ← lowest
```

Name conflicts resolved by precedence. Only one skill with a given name loads.

## Skills Watcher

OpenClaw watches `~/.openclaw/skills/` and `<workspace>/skills/` for changes:
```json5
{
  skills: {
    load: {
      watch: true,
      watchDebounceMs: 250
    }
  }
}
```

Changes take effect on next new session (or mid-session when watcher fires).

## Extra Skill Directories

```json5
{
  skills: {
    load: {
      extraDirs: [
        "~/shared-skills",
        "/srv/team-skills"
      ]
    }
  }
}
```

Extra dirs have lowest precedence (below bundled).

## Skill Snapshot (Performance)

OpenClaw snapshots eligible skills at session start and reuses the list for subsequent turns. This means:
- Skill changes during a session don't affect current session (unless watcher fires)
- New skills available on next new session

## Bundled Skill Allowlist

To restrict which bundled skills load:
```json5
{
  skills: {
    allowBundled: ["memory-core", "web-search"]
    // only these two bundled skills load
    // managed and workspace skills unaffected
  }
}
```
