---
name: notion-kanban-sync
description: "notion-kanban-sync"
metadata:
  openclaw:
    emoji: "📊"
    category: "integration"
---
# Skill: notion-kanban-sync

## Purpose

Maintains a Notion kanban board as a read-only visibility mirror of OpenClaw state. Covers dev projects (phases, containers, builds) and life areas (health, finance, learning, relationships, admin).

**Source of truth**: OpenClaw (authoritative) → Notion (visibility + planning metadata)

## Request Types

The skill accepts three request types via a single entry point (`notion_sync.py`):

### 1. event_sync (reactive)

Triggered by orchestration when OpenClaw events fire. Handles:
- `project_registered` / `project_removed` — upsert/archive Projects DB row
- `phase_started` / `phase_completed` / `phase_blocked` — upsert phase card, update status
- `container_completed` / `container_failed` — append to Activity log (+ create card if meaningful)
- `build_passed` / `tests_passed` / `tests_failed` / `deployed` — append to Activity log

### 2. capture (conversational)

Triggered when ClawdiaPrime routes a life/task capture request. Creates cards in Cards DB with area inference from keywords.

### 3. reconcile (scheduled)

Compares OpenClaw state against Notion, applies allowed-only corrections. Safe and idempotent — never deletes, never modifies Notion-owned fields.

## Config.json Fields

| Field | Type | Description |
|-------|------|-------------|
| `notion_projects_db_id` | string/null | Cached Notion Projects database_id (for page creation) |
| `notion_projects_ds_id` | string/null | Cached Notion Projects data_source_id (for queries) |
| `notion_cards_db_id` | string/null | Cached Notion Cards database_id (for page creation) |
| `notion_cards_ds_id` | string/null | Cached Notion Cards data_source_id (for queries) |
| `notion_parent_page_id` | string/null | Parent Notion page where DBs are created on first run |
| `auto_create_dbs` | bool | If true, bootstrap creates missing DBs automatically |
| `meaningful_container_runtime_min` | int | Containers running longer than this (minutes) get a card |
| `persistent_failure_threshold` | int | Consecutive test failures before a "Fix" card is created |
| `retry_max_attempts` | int | Max Notion API retry attempts on 429/5xx |
| `retry_base_delay_seconds` | float | Base delay for exponential backoff |
| `default_dev_area` | string | Default area for dev project cards |
| `area_keywords` | dict | Keyword → area mapping for conversational capture inference |

## Notion API Version

**Version**: `2025-09-03`

**Critical distinction — database_id vs data_source_id**:

In API version 2025-09-03, Notion renamed "databases" to "data sources" and split the ID space:

- `database_id` — used for **page creation** (`POST /v1/pages` with `parent.database_id`)
- `data_source_id` — used for **queries** (`POST /v1/data_sources/{data_source_id}/query`)

Both IDs are returned by search and create database responses. Both are cached separately in `config.json`. Never use `database_id` for queries — it will return 404.

## Field Ownership Rules

### OpenClaw Owns (never let Notion override)
- Status on cards with `OpenClaw Phase ID` or `OpenClaw Event Anchor` set
- All OpenClaw ID fields (phase ID, event anchor, capture hash)
- Timestamps (`Last Synced`, `Last Activity At`)
- Activity log (append-only, never truncate)
- Card Type, Capture Source
- Project relation on event-created cards
- Sync Status, Sync Error on Projects DB rows

### Notion Owns (OpenClaw never writes)
- Priority
- Target Week
- Notes
- Area (user may recategorize)
- Status on unlinked cards (no phase ID, no event anchor)

### Shared (OpenClaw sets initial value, Notion may annotate)
- Name (OpenClaw sets from event, user can clarify)
- Project Type (OpenClaw sets "Dev Project", user can refine)

## Idempotency Model

All upserts use dedupe keys to prevent duplicates on replay:

| Card Origin | Dedupe Property | Format |
|-------------|----------------|--------|
| Phase event | `OpenClaw Phase ID` | `{project_id}:{phase_id}` |
| Container event | `OpenClaw Event Anchor` | `{project_id}:{container_id}:{event_type}` |
| Conversational capture | `Capture Hash` | `sha256(normalize(title+area+week))[:12]` |
| Projects DB | `OpenClaw ID` | `{project_id}` |

**Rule**: If dedupe key exists in Notion → update. If not → create. On replay, same dedupe key → update is effectively a no-op (idempotent).

## Meaningful Container Rule

A container event creates a new card (rather than just appending to Activity) only if ANY of:
1. Runtime > `meaningful_container_runtime_min` minutes (default: 10)
2. Payload includes `requires_human_review: true`
3. Failure category is actionable: `tests_failed`, `lint_failed`, `deploy_failed`

Otherwise: append to parent phase card Activity only.

## Error Handling

| HTTP Status | Action |
|-------------|--------|
| 429 | Retry with exponential backoff: `base_delay * 2^attempt`, max `retry_max_attempts` |
| 5xx | Retry once after 2s, then record in Sync Error |
| 400 | Do not retry. Log error payload. Record in Sync Error |
| 404 | Clear cached DB ID, re-run discovery. If still 404, record error |

All errors are recorded to `Sync Error` field on the relevant Projects DB row. Failures never block orchestration (fire-and-forget).

## Bootstrap Flow

On first invocation (null DB IDs in config.json):
1. Search for "Projects" database with "OpenClaw ID" signature property
2. If found → cache both `database_id` and `data_source_id`
3. If not found and `auto_create_dbs` → create with full schema (requires `notion_parent_page_id`)
4. Repeat for "Cards" database with "OpenClaw Phase ID" signature property
5. Write all 4 IDs to `config.json` (thread-safe)

On subsequent invocations: use cached IDs, validate with single GET, re-discover only on 404.
