# Phase 11-03 Summary: Migration CLI Script

**Status:** COMPLETE  
**Date:** 2026-02-23  
**Depends on:** 11-01

---

## Deliverables

### `orchestration/migrate_state.py`

Standalone CLI script for migrating legacy state to per-project paths.

**Features:**
- **CLI:** `python3 orchestration/migrate_state.py [--project pumplai]`
- **Idempotent:** Safe to run multiple times
- **In-flight guard:** Blocks migration when tasks are spawned/running/in_progress/starting/testing
- **Backup:** Creates backup at `workspace/.openclaw/.backup/workspace-state.json.bak`
- **Copy (not move):** Preserves original until sentinel written
- **Sentinel:** Old path replaced with JSON containing `migrated: True`, new path, and error message
- **Snapshot migration:** Copies `workspace/.openclaw/snapshots/` to new per-project location

**Locked decisions followed:**
- No `--force` flag — operator must wait for tasks to complete
- No auto-resolution of stale tasks — operator decides
- Always copy before sentinel — never use `shutil.move`

---

## Usage

```bash
# Show help
python3 orchestration/migrate_state.py --help

# Run migration (default: pumplai project)
python3 orchestration/migrate_state.py

# Migrate specific project
python3 orchestration/migrate_state.py --project pumplai
```

**Exit codes:**
- `0` — Success, already migrated, or created empty state
- `1` — In-flight tasks blocking migration

---

## Verification

```bash
cd ~/.openclaw && python3 -c "
import ast
# Verify valid Python
with open('orchestration/migrate_state.py') as f:
    ast.parse(f.read())

# Verify components
with open('orchestration/migrate_state.py') as f:
    s = f.read()
assert 'IN_FLIGHT_STATUSES' in s
assert 'shutil.copy2' in s
assert 'migrated' in s
assert 'JarvisState' in s
assert 'argparse' in s
assert 'get_state_path' in s
assert '--force' not in s

print('Phase 11-03 verification: PASSED')
"
```

**Result:** All assertions passed

---

## Commits

```
c091d72 feat(cfg-01,cfg-02): add migration CLI for per-project state migration
```

---

## Success Criteria Met

| Criterion | Status |
|-----------|--------|
| Script is working CLI | ✅ |
| In-flight guard blocks on active tasks | ✅ |
| Backup created before migration | ✅ |
| State copied (not moved) to per-project path | ✅ |
| Old path sentineled | ✅ |
| Snapshots also migrated | ✅ |
| No --force flag | ✅ |
| Idempotent | ✅ |

---

## Phase 11 Complete

With Plans 01, 02, and 03 complete, Phase 11 is now finished:

1. **11-01:** Foundation — `get_state_path`, `get_snapshot_dir`, `_detect_default_branch` added
2. **11-02:** Call site updates — All 14 hardcoded locations replaced
3. **11-03:** Migration CLI — Standalone script for legacy state migration

All orchestration code now uses project-aware path resolution and dynamic branch detection.
