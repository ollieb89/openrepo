# Plan 28-01 Summary: Config + Env Injection

**Status:** Complete
**Commit:** feat(28-01): add memU config to openclaw.json and inject MEMU env vars into L3 containers

## What was done

1. **openclaw.json** — Added `memory.memu_api_url` field (`http://localhost:18791`) after the `gateway` block
2. **orchestration/project_config.py** — Added `get_memu_config()` helper that reads `memory` from openclaw.json with safe defaults (empty URL, enabled=True). Never raises.
3. **skills/spawn_specialist/spawn.py** — Added `get_memu_config` import and injected 4 MEMU env vars into L3 container environment: `MEMU_API_URL`, `MEMU_AGENT_ID`, `MEMU_PROJECT_ID`, `MEMU_ENABLED`

## Verification

- `get_memu_config()` returns `{"memu_api_url": "http://localhost:18791", "enabled": True}`
- All 4 MEMU env vars present in spawn.py container environment dict
- No import errors or circular dependencies
