---
phase: 73-unified-agent-registry
plan: "02"
subsystem: agent-registry-cli
tags:
  - agent-registry
  - cli
  - tdd
dependency_graph:
  requires:
    - packages/orchestration/src/openclaw/agent_registry.py (AgentRegistry.all_agents())
    - packages/orchestration/src/openclaw/config.py (get_agent_registry())
  provides:
    - openclaw-agent CLI entry point
    - openclaw agent list (table output, grouped by level, status column)
    - openclaw agent list --json (JSON array output)
  affects:
    - pyproject.toml [project.scripts] (new entry point registered)
tech_stack:
  added: []
  patterns:
    - TDD (Red-Green cycle)
    - argparse subcommands (project.py pattern)
    - monkeypatch + capsys for CLI testing
key_files:
  created:
    - packages/orchestration/src/openclaw/cli/agent.py
    - packages/orchestration/tests/test_cli_agent.py
  modified:
    - packages/orchestration/pyproject.toml
decisions:
  - "openclaw-agent entry point installed in project .venv (not system PATH) — same pattern as all other openclaw-* CLIs"
  - "ANSI color codes used for status column (ok=green, new=blue, orphan=yellow) — consistent with monitor.py"
  - "main() accepts argv param for testability — allows monkeypatching without subprocess"
metrics:
  duration: "2 minutes"
  completed: "2026-03-04"
  tasks_completed: 2
  files_modified: 3
  tests_added: 10
  tests_total: 752
requirements_satisfied:
  - AREG-02
  - AREG-03
---

# Phase 73 Plan 02: Agent CLI Summary

**One-liner:** `openclaw-agent list` CLI with table output grouped by level (L1/L2/L3) and Status column (ok/new/orphan), plus `--json` mode, backed by 10 TDD tests.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 (RED) | Failing tests for agent list CLI | ca7599c | tests/test_cli_agent.py |
| 1 (GREEN) | Implement cli/agent.py | 499a600 | cli/agent.py, test_cli_agent.py |
| 2 | Register openclaw-agent entry point | a9711bc | pyproject.toml |

## What Was Built

### cli/agent.py

New CLI module following the `project.py` pattern exactly:

- `main(argv=None) -> int` — argparse entrypoint with `list` subcommand
- `cmd_list(args)` — calls `get_agent_registry().all_agents()`, renders table or JSON
- `_format_table(agents)` — groups by level, prints section headers, colorized Status column
- `Colors` class — same ANSI codes as project.py and monitor.py
- `_SOURCE_STATUS` mapping: `"both"` → `"ok"`, `"agents_dir"` → `"new"`, `"openclaw_json"` → `"orphan"`
- `_LEVEL_LABELS` mapping for L1/L2/L3 section headers

### Status Column Semantics

| source value | Status | Color | Meaning |
|---|---|---|---|
| `"both"` | `ok` | green | Agent in openclaw.json AND has agents/ directory |
| `"agents_dir"` | `new` | blue | Filesystem-only — needs adding to openclaw.json |
| `"openclaw_json"` | `orphan` | yellow | In config only — needs `openclaw agent init` scaffold |

### pyproject.toml

Added `openclaw-agent = "openclaw.cli.agent:main"` to `[project.scripts]`.

### Real-World Validation

Running `openclaw-agent list` on the actual repo shows 8 agents across 3 levels:
- `clawdia_prime` (L1, source=both, ok)
- `docs_pm`, `main`, `nextjs_pm`, `pumplai_pm`, `python_backend_worker` (L2)
- `agent`, `l3_specialist` (L3)

Drift warnings emitted to structured JSON log (stderr) for 3 agents with name/level/reports_to mismatches — exactly as expected from Plan 01 validation.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

```
uv run pytest packages/orchestration/tests/test_cli_agent.py -v
→ 10 passed in 0.15s

uv run pytest packages/orchestration/tests/ -x -q
→ 752 passed in 7.71s (0 regressions)

openclaw-agent list
→ Formatted table with L1/L2/L3 groupings and ok/new/orphan status

openclaw-agent list --json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} agents')"
→ 8 agents
```

## Self-Check: PASSED

Files created/modified:
- FOUND: /home/ob/Development/Tools/openrepo/packages/orchestration/src/openclaw/cli/agent.py
- FOUND: /home/ob/Development/Tools/openrepo/packages/orchestration/tests/test_cli_agent.py
- FOUND: /home/ob/Development/Tools/openrepo/packages/orchestration/pyproject.toml

Commits:
- ca7599c — test(73-02): add failing tests for openclaw agent list CLI
- 499a600 — feat(73-02): implement openclaw agent list CLI (AREG-02/03)
- a9711bc — feat(73-02): register openclaw-agent entry point in pyproject.toml
