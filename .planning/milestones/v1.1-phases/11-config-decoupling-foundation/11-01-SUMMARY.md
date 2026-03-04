# Phase 11-01 Summary: Config Decoupling Foundation

**Status:** COMPLETE  
**Date:** 2026-02-23  

---

## Deliverables

### Added to `orchestration/project_config.py`

- **`ProjectNotFoundError`** — exception raised when project manifest does not exist
- **`get_state_path(project_id=None) -> Path`** — returns `workspace/.openclaw/<project_id>/workspace-state.json`
- **`get_snapshot_dir(project_id=None) -> Path`** — returns `workspace/.openclaw/<project_id>/snapshots/`

### Added to `orchestration/snapshot.py`

- **`_detect_default_branch(workspace, project_id=None) -> str`** — detects default branch via:
  1. `default_branch` field in project.json
  2. `git symbolic-ref refs/remotes/origin/HEAD`
  3. Local `main` branch existence check
  4. Local `master` branch existence check
  5. Fallback to `"main"` with warning

---

## Verification

```bash
cd ~/.openclaw && python3 -c "
from orchestration.project_config import get_state_path, get_snapshot_dir, ProjectNotFoundError
from orchestration.snapshot import _detect_default_branch
from pathlib import Path

# CFG-03: path API
assert 'pumplai/workspace-state.json' in str(get_state_path('pumplai'))
assert 'pumplai/snapshots' in str(get_snapshot_dir('pumplai'))
try:
    get_state_path('nonexistent')
    assert False
except ProjectNotFoundError:
    pass

# CFG-06: branch detection
branch = _detect_default_branch(Path('~/.openclaw/workspace'))
assert isinstance(branch, str) and branch

print('Phase 11-01 complete: all assertions passed')
"
```

**Result:** All assertions passed

---

## Commits

```
d101d01 feat(cfg-03): add get_state_path, get_snapshot_dir, ProjectNotFoundError to project_config
e4e818b feat(cfg-06): add _detect_default_branch helper to snapshot.py
```

---

## Next Steps

Plan 02 can now import and use these APIs:
- Update `snapshot.py` call sites to use `_detect_default_branch()` (CFG-06)
- Update `snapshot.py` to use `get_snapshot_dir()` (CFG-02)
- Update `spawn.py` and `pool.py` to use `get_state_path()` (CFG-01)

All existing functions remain untouched — downstream consumers update in Plan 02.
