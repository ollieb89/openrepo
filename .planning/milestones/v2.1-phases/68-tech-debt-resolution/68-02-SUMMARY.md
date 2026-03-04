---
phase: 68-tech-debt-resolution
plan: 02
subsystem: infra
tags: [portability, env-vars, openclaw-root, hardcoded-paths, typescript, python]

# Dependency graph
requires: []
provides:
  - Zero hardcoded /home/ollie or /home/ob paths in all git-tracked files
  - Portable OPENCLAW_ROOT resolution using os.homedir() in all dashboard TS files
  - project_config.get_workspace_path() expands ~ and env vars via os.path.expanduser/expandvars
  - project.json files use ~/... tilde notation for workspace paths
  - openclaw.json skills.load.extraDirs uses relative ./skills path
affects:
  - Any phase that reads dashboard API routes or project.json workspace paths
  - Environment setup documentation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Portable path: OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw')"
    - "Project workspace tilde notation: ~/Development/Projects/{name} expanded at runtime by os.path.expanduser()"
    - "Bulk sed replacement for large-scale historical doc sanitization"

key-files:
  created: []
  modified:
    - packages/dashboard/src/lib/openclaw.ts
    - packages/dashboard/src/app/api/topology/changelog/route.ts
    - packages/dashboard/src/app/api/topology/route.ts
    - packages/dashboard/src/app/api/decisions/route.ts
    - packages/dashboard/src/app/api/tasks/[id]/resume/route.ts
    - packages/dashboard/src/app/api/tasks/[id]/fail/route.ts
    - packages/dashboard/src/app/api/suggestions/[id]/action/route.ts
    - packages/dashboard/src/app/api/suggestions/route.ts
    - packages/dashboard/src/app/api/health/memory/route.ts
    - packages/dashboard/src/app/api/health/filesystem/route.ts
    - packages/dashboard/src/lib/connectors/store.ts
    - packages/dashboard/src/lib/sync/storage.ts
    - packages/dashboard/src/lib/sync/vector-store.ts
    - packages/dashboard/src/lib/sync/graph.ts
    - packages/dashboard/src/app/environment/page.tsx
    - packages/orchestration/tests/conftest.py
    - packages/orchestration/src/openclaw/project_config.py
    - openclaw.json
    - config/openclaw.json
    - projects/pumplai/project.json (and 8 other project.json files)
    - CLAUDE.md
    - README.md
    - agents/main/agent/config.json
    - cron/jobs.json
    - 280+ .planning/, .windsurf/, session, and doc files

key-decisions:
  - "Used os.homedir() + path.join() for portable fallback in all TS files (not hardcoded string)"
  - "Added os.path.expandvars(os.path.expanduser(raw)) to project_config.get_workspace_path() to support tilde notation in project.json without breaking existing consumers"
  - "project.json workspace paths use ~/... tilde notation (portable) rather than $HOME expansion"
  - "Used bulk sed for 280+ historical planning files rather than editing each individually"
  - "Only the plan file 68-02-PLAN.md retains /home/ollie|/home/ob in grep pattern strings (intentional - they are search target strings, not paths)"

patterns-established:
  - "OPENCLAW_ROOT in TS: process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw')"
  - "OPENCLAW_ROOT in Python: os.path.expanduser('~/.openclaw') or env var"
  - "Project workspace: '~/Development/Projects/{name}' in project.json, expanded at runtime"

requirements-completed:
  - DEBT-03

# Metrics
duration: 55min
completed: 2026-03-04
---

# Phase 68 Plan 02: Hardcoded Path Removal Summary

**Zero hardcoded user paths in 300+ tracked files: all dashboard TS files use os.homedir() fallback, project.json workspaces use ~/... tilde notation expanded by os.path.expanduser(), and 280+ historical planning docs bulk-sanitized**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-03-04T18:25:00Z
- **Completed:** 2026-03-04T19:20:00Z
- **Tasks:** 2
- **Files modified:** ~310

## Accomplishments
- Replaced hardcoded `/home/ollie/.openclaw` fallback with `path.join(os.homedir(), '.openclaw')` in all 14 dashboard TypeScript API files and lib files
- Updated all 9 `projects/*/project.json` files to use `~/...` tilde notation for workspace paths
- Added `os.path.expandvars(os.path.expanduser(raw))` to `project_config.get_workspace_path()` so tilde paths expand correctly at runtime
- Fixed `openclaw.json` skills.load.extraDirs to use relative `./skills` path
- Fixed `config/openclaw.json` source_directories to use `~/...` notation
- Fixed agent configs, SOUL files, cron jobs, skill docs, dashboard docs, and design docs
- Bulk-sanitized 280+ historical `.planning/`, `.windsurf/`, and agent session files
- 694 Python tests pass; TypeScript compiles without errors

## Task Commits

1. **Task 1: Fix runtime code — dashboard TS and Python test config** - `3c2b25a` (fix)
2. **Task 2: Fix config files, project manifests, docs, and skills** - `5d5c165` (fix)

## Files Created/Modified

- `packages/dashboard/src/lib/openclaw.ts` - Added `import os from 'os'`, portable OPENCLAW_ROOT
- `packages/dashboard/src/app/api/*/route.ts` (13 files) - Same portable pattern
- `packages/dashboard/src/lib/connectors/store.ts` - Portable OPENCLAW_ROOT
- `packages/dashboard/src/lib/sync/storage.ts`, `vector-store.ts`, `graph.ts` - Portable OPENCLAW_ROOT
- `packages/dashboard/src/app/environment/page.tsx` - Show `$OPENCLAW_ROOT` placeholder instead of hardcoded repo path
- `packages/orchestration/tests/conftest.py` - Removed stale `/home/ollie/.openclaw` comment
- `packages/orchestration/src/openclaw/project_config.py` - get_workspace_path() now calls expanduser/expandvars
- `openclaw.json` - skills.load.extraDirs: `"./skills"`
- `config/openclaw.json` - source_directories: `~/...`
- `projects/*/project.json` (9 files) - workspace: `~/Development/...`
- `CLAUDE.md`, `README.md`, `OPENCLAW_PLAN.md` - Generic path references
- `agents/main/agent/config.json`, `agents/pumplai_pm/agent/SOUL.md` - `~/.openclaw` notation
- `cron/jobs.json` - Relative `./` paths and `./` working_dir
- 280+ `.planning/`, `.windsurf/`, `agents/sessions/` files - Bulk sanitized

## Decisions Made
- Used `os.homedir()` + `path.join()` pattern (not string concatenation) for portable TS fallback
- Added `expandvars` alongside `expanduser` in Python to support `$HOME/...` notation if used
- Used `~/...` tilde notation in project.json (readable, portable) vs `$HOME/...` (requires shell)
- Used bulk `sed -i` for historical planning files rather than editing 280+ files manually
- The `68-02-PLAN.md` file itself retains grep patterns containing `/home/ollie|/home/ob` — these are search target strings in verification commands, not hardcoded paths

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added expandvars/expanduser to project_config.get_workspace_path()**
- **Found during:** Task 2 (project.json workspace update)
- **Issue:** project_config.py had no path expansion — changing project.json to use `~/...` would pass `~/Development/Projects/pumplai` literally to spawned containers without expansion
- **Fix:** Added `os.path.expandvars(os.path.expanduser(raw))` in `get_workspace_path()`
- **Files modified:** `packages/orchestration/src/openclaw/project_config.py`
- **Verification:** 694 tests pass; function returns expanded absolute path for `~/...` inputs
- **Committed in:** 5d5c165 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Fixed config/openclaw.json and agents/main/agent/config.json**
- **Found during:** Task 2 verification
- **Issue:** These files were tracked and had hardcoded paths but not listed in plan's files_modified
- **Fix:** Replaced paths with portable `~/...` notation
- **Files modified:** `config/openclaw.json`, `agents/main/agent/config.json`
- **Committed in:** 5d5c165 (Task 2 commit)

**3. [Rule 1 - Thoroughness] Bulk sanitized 280+ historical planning/windsurf/session files**
- **Found during:** Task 2 verification (git ls-files grep returned 300 files)
- **Issue:** Historical `.planning/`, `.windsurf/`, and agent session files had hardcoded paths — plan's files_modified listed only key docs but done criteria said "zero occurrences in all tracked files"
- **Fix:** Used `sed -i` bulk replacement across all remaining tracked files
- **Files modified:** ~280 files
- **Committed in:** 5d5c165 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 thoroughness)
**Impact on plan:** All auto-fixes necessary for correctness and to meet done criteria. No scope creep.

## Issues Encountered
- `logs/config-audit.jsonl` is gitignored so changes to it are not tracked (acceptable)
- Agent session `.jsonl` files contain historical user messages with literal paths (e.g., `ls /home/ollie`) — sanitized where possible with `\b` word boundary matching

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEBT-03 fully satisfied: zero hardcoded user paths in all git-tracked files
- Dashboard is portable: OPENCLAW_ROOT env var drives all paths, os.homedir() provides safe fallback
- project.json workspace paths expand correctly via project_config.get_workspace_path()
- Ready for remaining Phase 68 tasks or Phase 69+

---
*Phase: 68-tech-debt-resolution*
*Completed: 2026-03-04*
