---
status: awaiting_human_verify
trigger: "openclaw propose returns unknown command; Invalid config plugin manifest not found for orchestration-bridge"
created: 2026-03-04T00:00:00.000Z
updated: 2026-03-04T00:00:00.000Z
---

## Current Focus

hypothesis: TWO independent bugs confirmed. (1) orchestration-bridge is missing openclaw.plugin.json. (2) `openclaw propose` is not a Node.js CLI subcommand — it's only a Python entry point `openclaw-propose`.
test: Verified by reading discovery.ts, bundled-dir.ts, and pyproject.toml
expecting: Fix (1) by adding openclaw.plugin.json to extensions/orchestration-bridge/. Fix (2) by registering `propose` as a Node.js CLI subcommand.
next_action: implement fixes

## Symptoms

expected: `openclaw propose` should work as a valid command, and config should load without plugin manifest errors
actual: Every openclaw command first shows "Invalid config" warning about missing orchestration-bridge plugin manifest, then `propose` fails as unknown command
errors:
- "Invalid config at /home/ob/.openclaw/openclaw.json: plugins: plugin: plugin manifest not found: /home/ob/Development/Tools/openrepo/openclaw/extensions/orchestration-bridge/openclaw.plugin.json"
- "error: unknown command 'propose'"
reproduction: Run `openclaw propose` from the repo root
started: Current state on main branch

## Eliminated

- hypothesis: orchestration-bridge is referenced in user config (~/.openclaw/openclaw.json)
  evidence: User config has only qwen-portal-auth in plugins.entries. orchestration-bridge is not referenced anywhere in any JSON config.
  timestamp: 2026-03-04

- hypothesis: `openclaw-propose` Python binary is not installed
  evidence: Python package is installed in .venv with all six entry points including openclaw-propose.
  timestamp: 2026-03-04

## Evidence

- timestamp: 2026-03-04
  checked: openclaw/src/plugins/bundled-dir.ts
  found: Walks up from module's location and finds extensions/ at the openclaw package root (/home/ob/Development/Tools/openrepo/openclaw/extensions/)
  implication: All extension subdirectories are discovered as plugin candidates

- timestamp: 2026-03-04
  checked: openclaw/src/plugins/discovery.ts discoverInDirectory()
  found: For each subdirectory, if index.ts/index.js/index.mjs/index.cjs exists, it registers that directory as a plugin candidate (even without package.json or openclaw.plugin.json)
  implication: extensions/orchestration-bridge/ has index.ts → gets picked up as a plugin candidate

- timestamp: 2026-03-04
  checked: openclaw/extensions/orchestration-bridge/
  found: Directory contains only index.ts (a socket bridge utility, not a real plugin). No package.json, no openclaw.plugin.json.
  implication: loadPluginManifest() tries to load non-existent openclaw.plugin.json and emits a "plugin manifest not found" error diagnostic

- timestamp: 2026-03-04
  checked: openclaw/src/config/validation.ts validateConfigObjectWithPluginsBase()
  found: Registry diagnostics at level "error" are promoted to config validation issues → causes "Invalid config" message
  implication: Since user config has plugins.entries, the registry is loaded on every command, triggering the error every time

- timestamp: 2026-03-04
  checked: packages/orchestration/pyproject.toml [project.scripts]
  found: openclaw-propose is registered as Python CLI entry point (hyphen-separated), not as `propose` subcommand of Node.js openclaw CLI
  implication: `openclaw propose` routes to the Node.js CLI which has no `propose` command

- timestamp: 2026-03-04
  checked: openclaw/src/commands/ directory listing
  found: No propose.ts file exists in the Node.js commands directory
  implication: `openclaw propose` is definitively not implemented in the Node.js CLI

## Resolution

root_cause:
  issue_1: extensions/orchestration-bridge/ has index.ts which causes plugin discovery to pick it up as a
    candidate, but there is no openclaw.plugin.json manifest, so it emits a "plugin manifest not found"
    error diagnostic, which is promoted to an "Invalid config" fatal error because the user config has
    a plugins.entries section.
  issue_2: The Python package registers `openclaw-propose` (hyphenated) as a standalone CLI entry point,
    but the Node.js `openclaw` CLI has no `propose` subcommand registered. Users running `openclaw propose`
    hit the Node.js CLI which doesn't know about it.

fix:
  issue_1: Added openclaw.plugin.json manifest to extensions/orchestration-bridge/ with id, name,
    description, and configSchema. Plugin system now accepts it as a valid plugin — no more error diagnostic.
  issue_2: Created src/cli/propose-cli.ts that registers a `propose` Commander command which spawns
    `openclaw-propose` (Python) via spawnSync with all passthrough args. Registered in both
    register.subclis.ts (source) and register.subclis-Bg0mXCLD.js (compiled dist) so it works
    immediately without requiring a full TypeScript build.

verification:
  - `openclaw --help` no longer shows "Invalid config" warning (orchestration-bridge plugin now has valid manifest)
  - `openclaw --help` now lists `propose` in the commands section
  - `openclaw propose --help` shows correct usage with examples and delegation note
  - `openclaw propose memory` correctly spawns `openclaw-propose memory` (confirmed delegation works;
     downstream Python error is a separate pre-existing issue about no active project being configured)

files_changed:
  - openclaw/extensions/orchestration-bridge/openclaw.plugin.json (created)
  - openclaw/src/cli/propose-cli.ts (created)
  - openclaw/src/cli/program/register.subclis.ts (added propose entry)
  - openclaw/dist/register.subclis-Bg0mXCLD.js (added propose entry to compiled dist)
