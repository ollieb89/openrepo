# Project State: OpenClaw

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.
**Current focus:** v2.0 Notion Kanban Sync — Phase 50, Plan 03 complete; Phase 47-03 complete (CONF-03, CONF-04 tests)

## Current Position

Phase: 50 of 50 (Notion Kanban Sync)
Plan: 3 of 6 complete
Status: Ready
Last activity: 2026-02-25 — 50-03 complete: event sync handlers (project/phase lifecycle), SyncResult builder, field ownership guards, event_bus_hook.py (NOTION-01, NOTION-02, NOTION-03, NOTION-09, NOTION-10)

Progress: [#####░░░░░] 50% — Phase 45 done (2/2), Phase 46 done (3/3), Phase 50 in progress (3/6)

## Performance Metrics

**Velocity (shipped milestones):**
- v1.0: 10 phases, 25 plans across 7 days
- v1.1: 8 phases, 17 plans in ~5 hours
- v1.2: 7 phases, 14 plans in ~1 day
- v1.3: 11 phases, 19 plans in ~1 day
- v1.4: 6 phases, 16 plans in ~1 day

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table (v1.0–v1.4).

Notable for v1.5:
- Cosine similarity conflict detection threshold (0.92) needs empirical tuning — addressed in Phase 49
- `workspace/` path divergence (runtime `data/workspace/.openclaw/` vs code-resolved `OPENCLAW_ROOT/workspace/.openclaw/`) — addressed in Phase 45
- Phase 49 depends on Phase 45 (shares OPENCLAW_ROOT plumbing) but is independent of Phases 46-48

**45-01 decisions:**
- get_state_path() and get_snapshot_dir() require project_id — no Optional default, no active-project fallback
- OPENCLAW_STATE_FILE env var takes priority in get_state_path() to align with container entrypoint.sh behavior
- _find_project_root() never uses Path(__file__).parent — resolves to site-packages, not live project root

**45-02 decisions:**
- pool.py init builds defaults dict inline from DEFAULT_POOL_* constants — no separate dict variable needed
- init.py resolves project_id via get_active_project_id() with "default" fallback for path function calls
- soul_renderer.py aliases get_project_root as _find_project_root to minimize diff while aligning to config source

**46-01 decisions (TDD RED):**
- validate_openclaw_config returns (fatal: list, warnings: list) tuple — testable without mocking sys.exit
- validate_project_config_schema is a separate entry point for project.json — raises exception on failure
- test_project_json_missing_required uses pytest.raises(Exception) broadly — exact exception type is Plan 02's decision

**46-02 decisions (schema implementation GREEN):**
- additionalProperties violations are warnings not fatal errors — unknown fields may be forward-compatible
- sys.exit(1) fires in _emit_validation_results() at call site in project_config.py, not inside the validator
- OPENCLAW_JSON_SCHEMA and PROJECT_JSON_SCHEMA imported lazily inside validator functions to avoid circular imports
- Draft202012Validator.iter_errors() collect-all strategy — user sees all errors at once

**46-03 decisions (CLI + documentation):**
- openclaw-config show calls load_and_validate_openclaw_config() — reuses existing validation path rather than loading config directly
- FileNotFoundError caught separately from generic Exception in cmd_show for actionable error messages
- _comment_* JSON keys pattern used for inline schema documentation (standard JSON workaround, file remains parseable)
- config/openclaw.json.example documents all 9 schema properties including nested gateway.auth, agents.defaults, channels.telegram
- [Phase 50-01]: event_bus.py has zero openclaw imports at module level to avoid circular imports
- [Phase 50-01]: Each emit() handler gets its own daemon thread — no shared thread pool needed
- [Phase 50-notion-kanban-sync]: data_source_id used for queries, database_id for creates — API 2025-09-03 splits ID space; both cached in config.json
- [Phase 50-notion-kanban-sync]: Module-level threading.Lock() in notion_client.py prevents concurrent bootstrap race creating duplicate Notion DBs
- [Phase 47-env-var-precedence-migration-cli]: get_active_project_env() returns None (not empty string) when OPENCLAW_PROJECT unset — or None idiom coerces empty string
- [Phase 47-env-var-precedence-migration-cli]: mkdir auto-create in _find_project_root() applies only to OPENCLAW_ROOT env var path, not ~/.openclaw fallback
- [Phase 47-02-migration-cli]: shutil.copy2 backup in helpers (_migrate_one_*) not in cmd_migrate — cleaner separation; _migrate_one_project_json catches ConfigValidationError (raise pattern), not (fatal, warnings) tuple
- [Phase 47-03-tests]: get_active_project_env() tests do not need importlib.reload — function reads os.environ at call time; test_get_active_project_id_uses_env_var uses reload in try/finally for OPENCLAW_ROOT override
- [Phase 50-03]: _safe_set_status is exclusive — if not openclaw-linked, Status key is absent from update dict (Notion's value is untouched)
- [Phase 50-03]: activity append is best-effort — failure logs warning but never aborts the main Cards DB mutation
- [Phase 50-03]: Module-level _project_page_id_cache dict avoids repeated Projects DB queries within one process lifetime

### Pending Todos

None.

### Blockers/Concerns

- Human verification pending for live Docker/browser tests (SIGTERM E2E, memory health UI, suggestions UI) — accepted as tech debt per v1.4 audit

## Session Continuity

Last session: 2026-02-25
Stopped at: 47-03 complete — CONF-03/CONF-04 test cases appended to test_config_validator.py (9 new functions, 16/16 pass, 167 total passing). Phase 47 complete.
Resume: Run `/gsd:execute-plan 50 04` to execute Phase 50 Plan 04 (next plan)
