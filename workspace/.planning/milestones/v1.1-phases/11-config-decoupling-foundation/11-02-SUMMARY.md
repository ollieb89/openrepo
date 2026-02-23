# Phase 11-02 Summary: Call Site Updates

**Status:** COMPLETE  
**Date:** 2026-02-23  
**Depends on:** 11-01

---

## Deliverables

All 14 hardcoded path/branch locations updated across 7 files.

### `orchestration/snapshot.py`

- `_detect_default_branch()` added to `capture_semantic_snapshot`, `l2_review_diff`, `l2_merge_staging`, `l2_reject_staging`
- `get_snapshot_dir()` replaces hardcoded `workspace/.openclaw/snapshots` in `capture_semantic_snapshot` and `cleanup_old_snapshots`
- Zero hardcoded `"main"` in git diff/checkout/merge contexts

### `orchestration/init.py`

- `get_state_path()` and `get_snapshot_dir()` imported with try/except for module/direct-exec support
- `initialize_workspace()` creates per-project directories
- `verify_workspace()` checks per-project paths

### `orchestration/config.py`

- `STATE_FILE` and `SNAPSHOT_DIR` marked as `DEPRECATED`
- Constants retained for backward compatibility (removal in Phase 13)

### `orchestration/monitor.py`

- `get_state_path()` imported
- All three `--state-file` argument defaults changed to `None`
- Parse-time resolution: `args.state_file = str(get_state_path())` with `STATE_FILE` fallback

### `skills/spawn_specialist/spawn.py`

- `get_state_path()` for state file path (CFG-01)
- `load_l3_config()` resolves `l3_agent_id` from `get_agent_mapping()` (CFG-07)
- `OPENCLAW_STATE_FILE` injected into L3 container environment

### `skills/spawn_specialist/pool.py`

- `get_state_path()` replaces hardcoded `workspace/.openclaw/workspace-state.json`

### `docker/l3-specialist/entrypoint.sh`

- `STATE_FILE="${OPENCLAW_STATE_FILE:-/workspace/.openclaw/workspace-state.json}"`
- Reads state path from env var with backward-compat fallback

---

## Verification

```bash
cd /home/ollie/.openclaw && python3 -c "
import re

# snapshot.py
with open('orchestration/snapshot.py') as f:
    s = f.read()
assert '_detect_default_branch' in s
assert 'get_snapshot_dir' in s
assert not re.findall(r\"'diff'[^\\n]*'main|'checkout', 'main'|into main'\", s)

# All other files
for path, check in [
    ('orchestration/init.py', ['get_state_path', 'get_snapshot_dir']),
    ('orchestration/config.py', ['DEPRECATED']),
    ('orchestration/monitor.py', ['get_state_path']),
    ('skills/spawn_specialist/spawn.py', ['get_state_path', 'OPENCLAW_STATE_FILE', 'l3_agent_id']),
    ('skills/spawn_specialist/pool.py', ['get_state_path']),
]:
    with open(path) as f:
        content = f.read()
    for c in check:
        assert c in content, f'{c} missing in {path}'

# entrypoint.sh
with open('docker/l3-specialist/entrypoint.sh') as f:
    assert 'OPENCLAW_STATE_FILE' in f.read()

print('Phase 11-02 verification: ALL PASSED')
"
```

**Result:** All assertions passed

---

## Commits

```
5362cc6 feat(cfg-02,cfg-06): snapshot.py uses _detect_default_branch and get_snapshot_dir
a1ba4df feat(cfg-01,cfg-02): init.py creates per-project directories via project_config
d91d75f chore: deprecate STATE_FILE and SNAPSHOT_DIR constants in config.py
1f5fa7d feat(cfg-01): monitor.py resolves default --state-file via get_state_path()
e6d7b7b feat(cfg-01,cfg-07): spawn.py uses get_state_path, resolves L3 agent from manifest, injects OPENCLAW_STATE_FILE
83df233 feat(cfg-01): pool.py uses get_state_path() for state file
b069faf feat(cfg-01): entrypoint.sh reads STATE_FILE from OPENCLAW_STATE_FILE env var
```

---

## Success Criteria Met

| Criterion | Status |
|-----------|--------|
| Zero hardcoded "main" in snapshot.py diff/checkout/merge | ✅ |
| Zero hardcoded state file paths in spawn.py, pool.py, monitor.py | ✅ |
| Zero hardcoded snapshot paths in snapshot.py, init.py | ✅ |
| L3 entrypoint reads state path from environment | ✅ |
| Agent config path resolved from project manifest (CFG-07) | ✅ |
| config.py constants deprecated with comments | ✅ |

---

## Next Steps

Phase 11 is functionally complete. All orchestration code now resolves paths and branches dynamically per project. The migration script (if needed) can use `get_state_path()` to move legacy state to new per-project location.
