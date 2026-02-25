# Project State: OpenClaw

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.
**Current focus:** v2.0 Notion Kanban Sync — Phase 50, Plan 05 complete (conversational capture handler)

## Current Position

Phase: 50 of 50 (Notion Kanban Sync)
Plan: 5 of 6 complete
Status: Ready
Last activity: 2026-02-25 — 50-05 complete: conversational capture handler (area inference, capture hash dedupe, batch parsing) wired into notion_sync.py dispatcher (NOTION-04)

Progress: [########░░] 83% — Phase 45 done (2/2), Phase 46 done (3/3), Phase 50 in progress (5/6)

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
- [Phase 50-05]: _parse_batch sentence heuristic skips comma-split when '. ', '? ', or '! ' present — avoids splitting natural language sentences
- [Phase 50-05]: Status ownership on capture update: explicit status in payload respected directly; no _is_openclaw_linked guard needed for capture cards (Capture Hash is our ownership marker)
- [Phase 50-05]: card_type=Task for Dev area, Life Task for all others — consistent with Cards DB schema options
- [Phase 50]: [Phase 50-04]: _should_write_status() is canonical status ownership guard — _is_openclaw_linked() delegates to it for backward compat
- [Phase 50]: [Phase 50-04]: container child cards use upsert_by_dedupe on OpenClaw Event Anchor for idempotent replay

### Pending Todos

None.

### Blockers/Concerns

- Human verification pending for live Docker/browser tests (SIGTERM E2E, memory health UI, suggestions UI) — accepted as tech debt per v1.4 audit

## Session Continuity

Last session: 2026-02-25
Stopped at: 50-05 complete — capture_handler.py (area inference, capture hash dedupe, batch parsing), notion_sync.handle_capture wired, 167 tests passing.
Resume: Run `/gsd:execute-plan 50 06` to execute Phase 50 Plan 06 (reconcile drift detection — final plan)
