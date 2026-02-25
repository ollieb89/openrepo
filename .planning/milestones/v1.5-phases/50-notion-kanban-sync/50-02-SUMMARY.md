---
phase: 50-notion-kanban-sync
plan: 02
subsystem: integration
tags: [notion, httpx, retry, backoff, bootstrap, kanban, event-sync]

# Dependency graph
requires: []
provides:
  - "NotionClient class: authenticated HTTP wrapper with retry/backoff for Notion API 2025-09-03"
  - "Bootstrap: discover-or-create Projects DB and Cards DB with full schema"
  - "Skill directory skeleton: skill.json, _meta.json, config.json, SKILL.md"
  - "DB ID caching: all 4 IDs (database_id + data_source_id per DB) in config.json"
affects:
  - 50-notion-kanban-sync (plans 03-06 depend on NotionClient for all Notion mutations)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Notion API 2025-09-03: database_id for creates, data_source_id for queries"
    - "Module-level threading.Lock() for thread-safe config reads/writes"
    - "Discover-first bootstrap with cached IDs and 404-triggered re-discovery"
    - "Read-before-write for Activity field append (2 API calls)"
    - "bulk_mode flag for reconcile: 350ms inter-request sleep"

key-files:
  created:
    - skills/notion-kanban-sync/skill.json
    - skills/notion-kanban-sync/_meta.json
    - skills/notion-kanban-sync/config.json
    - skills/notion-kanban-sync/SKILL.md
    - skills/notion-kanban-sync/notion_client.py
  modified: []

key-decisions:
  - "data_source_id used for all queries (/v1/data_sources/{id}/query); database_id used for page creation — API 2025-09-03 splits ID space"
  - "Module-level threading.Lock() in notion_client.py prevents concurrent bootstrap race (two threads both seeing null DB IDs)"
  - "bulk_mode flag on NotionClient controls 350ms inter-request sleep for reconcile bulk reads"
  - "append_activity always does read-before-write (GET page + PATCH) because Notion PATCH replaces entire rich_text field"
  - "notion_parent_page_id required in config.json when auto_create_dbs=true — raises clear RuntimeError if missing"

patterns-established:
  - "NotionClient: all Notion mutations go through _request() which handles retry/backoff"
  - "upsert_by_dedupe: query data_source_id by rich_text equals, then create or update"
  - "Bootstrap validates cached IDs with GET before trusting them; clears and re-discovers on 404"

requirements-completed: [NOTION-08, NOTION-11]

# Metrics
duration: 8min
completed: 2026-02-25
---

# Phase 50 Plan 02: Notion Kanban Sync — Infrastructure Summary

**Notion HTTP client wrapper with authenticated retry/backoff, discover-or-create DB bootstrap, and full Projects + Cards DB schema definitions for API version 2025-09-03**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-25T06:34:34Z
- **Completed:** 2026-02-25T06:42:36Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Skill directory skeleton with valid skill.json, _meta.json, config.json, and SKILL.md
- `NotionClient` class: authenticated HTTP using `Notion-Version: 2025-09-03` with per-request retry
- Retry policy: 429 → exponential backoff (`base_delay * 2^attempt`, max 3), 5xx → single retry after 2s, 400 → no retry
- Bootstrap: discover-first (POST /v1/search + signature property check), create-if-missing with full Projects and Cards DB schemas
- Caches all 4 IDs (projects_db_id, projects_ds_id, cards_db_id, cards_ds_id) to config.json under threading.Lock()
- `upsert_by_dedupe`: query by rich_text property, create or update idempotently
- `append_activity`: read-before-write GET + PATCH to prepend timestamped line without overwriting existing content

## Task Commits

Each task was committed atomically:

1. **Task 1: Create skill directory skeleton** - `15113cb` (feat)
2. **Task 2: Implement notion_client.py** - `d47f5d7` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `skills/notion-kanban-sync/skill.json` — Skill metadata: id, commands, handler (python3 notion_sync.py)
- `skills/notion-kanban-sync/_meta.json` — Hub metadata: ownerId=openclaw, slug, version 0.1.0
- `skills/notion-kanban-sync/config.json` — Runtime config with null DB IDs, retry tuning, area keywords
- `skills/notion-kanban-sync/SKILL.md` — Skill knowledge file documenting API version, field ownership, idempotency model, bootstrap flow
- `skills/notion-kanban-sync/notion_client.py` — Complete HTTP wrapper with retry, bootstrap, typed helpers, DB schemas

## Decisions Made

- **database_id vs data_source_id**: API 2025-09-03 requires `data_source_id` for queries (`/v1/data_sources/{id}/query`) and `database_id` for page creation. Both cached separately in config.json.
- **Thread-safe config**: Module-level `threading.Lock()` prevents concurrent bootstrap race where two daemon threads both discover null DB IDs and create duplicate databases.
- **bulk_mode**: Reconcile sets `client._bulk_mode = True` to enable 350ms inter-request sleep, avoiding 429 on bulk reads.
- **append_activity read-before-write**: Notion PATCH replaces entire `rich_text` field — must GET existing content first, prepend new line, then PATCH full combined text.
- **notion_parent_page_id required**: When `auto_create_dbs=true` and DBs are not found, bootstrap raises `RuntimeError` with actionable message if parent page ID is not configured.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Before using the skill, configure `skills/notion-kanban-sync/config.json`:

1. Set `NOTION_TOKEN` environment variable (Notion integration token)
2. Set `notion_parent_page_id` to the Notion page ID where databases should be created (only needed if `auto_create_dbs: true` and DBs don't exist yet)
3. Or set `notion_projects_db_id` / `notion_projects_ds_id` / `notion_cards_db_id` / `notion_cards_ds_id` directly if databases already exist

First invocation will discover or create the databases and cache the IDs.

## Next Phase Readiness

- `NotionClient` is complete and all downstream plans (03-06) can import and use it
- All typed helpers are implemented: `search_database`, `create_database`, `query_database`, `create_page`, `update_page`, `get_page`, `upsert_by_dedupe`, `append_activity`
- Plan 03 (event_bus.py + hook sites) can proceed independently — it doesn't depend on notion_client.py directly

---
*Phase: 50-notion-kanban-sync*
*Completed: 2026-02-25*
