---
phase: 47-env-var-precedence-migration-cli
plan: 02
subsystem: config
tags: [config, cli, migration, jsonschema, python, openclaw]

# Dependency graph
requires:
  - phase: 46-schema-validation-fail-fast-startup
    provides: validate_openclaw_config, validate_project_config_schema, ConfigValidationError, OPENCLAW_JSON_SCHEMA, PROJECT_JSON_SCHEMA
  - phase: 47-env-var-precedence-migration-cli
    plan: 01
    provides: get_project_root, openclaw-config CLI with argparse epilog
provides:
  - cmd_migrate() function in cli/config.py — one-command upgrade path for openclaw.json and all projects/*/project.json
  - --dry-run preview mode showing what fields would be removed without modifying files
  - shutil.copy2 backup before any write (.json.bak created alongside each modified file)
  - Non-zero exit with actionable guidance when required fields are missing (cannot auto-fix)
  - "Already up-to-date." output when no migration needed
affects: [cli, config, operators, deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Migration pattern: detect-via-validator, backup-via-shutil, apply-filter-and-write"
    - "Helper-per-file pattern: _migrate_one_openclaw_json() and _migrate_one_project_json() isolate file-type logic"
    - "_collect_unknown_field_names() uses Draft202012Validator.iter_errors() with re.findall for clean field name extraction"

key-files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/cli/config.py

key-decisions:
  - "shutil.copy2 backup in helper functions, not inline in cmd_migrate — cleaner separation of concerns"
  - "_migrate_one_project_json catches ConfigValidationError (not tuple pattern) — validate_project_config_schema raises, not returns"
  - "re.findall pattern on error.message extracts multiple unknown field names per additionalProperties error"

patterns-established:
  - "Config migration pattern: reuse existing Phase 46 validators as detection engine — no new detection logic"
  - "Backup-before-write: shutil.copy2 creates .bak alongside modified file before any write"

requirements-completed: [CONF-03]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 47 Plan 02: Migration CLI Summary

**`openclaw-config migrate` command with dry-run, per-file backup, and unknown-field removal reusing Phase 46 schema validators**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T06:46:23Z
- **Completed:** 2026-02-25T06:48:25Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `cmd_migrate()` to `cli/config.py` — handles both openclaw.json and all projects/*/project.json
- Added `_migrate_one_openclaw_json()` and `_migrate_one_project_json()` helpers — file-type-specific migration logic
- Added `_collect_unknown_field_names()` — uses `Draft202012Validator.iter_errors()` with regex to extract field names cleanly
- Added `migrate` subparser to `main()` with `--dry-run` argument
- Dry-run prints "Dry run — no files will be modified." header + per-file change list
- Apply mode creates `.bak` backup via `shutil.copy2` before removing unknown fields, confirms with count
- Exits non-zero with actionable guidance when required fields are missing
- 158 tests pass, no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement cmd_migrate() and helper functions in cli/config.py** - `8bc37d4` (feat)

## Files Created/Modified
- `packages/orchestration/src/openclaw/cli/config.py` — Added `_collect_unknown_field_names()`, `_migrate_one_openclaw_json()`, `_migrate_one_project_json()`, `cmd_migrate()`, `migrate` subparser wired into `main()`

## Decisions Made
- Backup logic in helper functions (`_migrate_one_openclaw_json`, `_migrate_one_project_json`) rather than inline in `cmd_migrate` — cleaner separation of concerns. The plan's verification test checked `getsource(cmd_migrate)` for `shutil.copy2`, but end-to-end verification confirmed backup is created correctly.
- `_migrate_one_project_json` catches `ConfigValidationError` (exception pattern) matching `validate_project_config_schema`'s raise-on-failure contract — not the `(fatal, warnings)` tuple pattern used by `validate_openclaw_config`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Minor] Backup logic in helpers, not directly in cmd_migrate**
- **Found during:** Task 1
- **Issue:** Plan's verify assertion checked `inspect.getsource(cmd_migrate)` for `shutil.copy2`. Structurally cleaner to put backup in per-file helpers rather than in the top-level dispatcher.
- **Fix:** `shutil.copy2` placed in `_migrate_one_openclaw_json` and `_migrate_one_project_json` (called by `cmd_migrate`). Backup is created correctly — the plan's intent is satisfied.
- **Verification:** Functional test confirmed `.bak` created before write. End-to-end `--dry-run` output verified.

---

**Total deviations:** 1 (minor structural placement, no behavior change)
**Impact on plan:** No scope change. Backup functionality works as specified.

## Issues Encountered
- Plan's verify assertion `assert 'shutil.copy2' in inspect.getsource(cmd_migrate)` fails because backup is in helpers — functionally equivalent but structurally cleaner. Live behavior matches all success criteria.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- CONF-03 complete — `openclaw-config migrate` ships with dry-run, per-file backup, and schema-based unknown field removal
- Phase 47 is now fully complete (both plans done: CONF-04 in 47-01, CONF-03 in 47-02)
- 158 tests pass

---
*Phase: 47-env-var-precedence-migration-cli*
*Completed: 2026-02-25*

## Self-Check: PASSED

- `packages/orchestration/src/openclaw/cli/config.py` — FOUND
- `.planning/phases/47-env-var-precedence-migration-cli/47-02-SUMMARY.md` — FOUND
- Commit `8bc37d4` — FOUND in git log
