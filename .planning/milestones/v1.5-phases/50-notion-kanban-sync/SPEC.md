# Phase 50: Notion Kanban Sync

## Overview

A reactive L2-level skill that maintains a Notion kanban board as a read-only visibility mirror of OpenClaw state, covering both dev projects and life areas.

**Source of truth**: OpenClaw (authoritative) → Notion (visibility + planning metadata)

## Decisions Log

| # | Decision | Choice |
|---|----------|--------|
| 1 | Board scope | Dev projects + life areas (health, finance, learning, relationships) |
| 2 | Trigger model | Reactive — invoked by orchestration on OpenClaw events |
| 3 | Source of truth | OpenClaw → Notion. Notion owns only planning metadata |
| 4 | Life area capture | Conversational capture + manual quick-add, same skill |
| 5 | Notion discovery | Discover-first, create-if-missing |
| 6 | Event mapping | Phase start/complete = status moves; L3 = logs unless meaningful |
| 7 | Columns | Backlog \| This Week \| In Progress \| Waiting \| Done \| Archived |
| 8 | Agent location | L2 skill invoked by orchestration (+ optional scheduled reconcile) |
| 9 | Schema | Two DBs: Projects DB + Cards DB. Areas are a property, not projects |
| 10 | Field ownership | OpenClaw owns status/timestamps/IDs. Notion owns priority/notes/area/target week |
| 11 | Idempotency | Dedupe keys on all upserts — no duplicates on replay |
| 12 | Status ownership carve-out | OpenClaw-linked cards: OpenClaw owns Status. Unlinked cards: Notion owns Status |

## Architecture

### Skill Identity

```
skills/notion-kanban-sync/
├── SKILL.md                    # Skill definition (workflow, tools, patterns)
├── _meta.json                  # Skill metadata
├── reference/
│   ├── schema.md               # Notion DB schemas (Projects + Cards)
│   ├── event-mapping.md        # OpenClaw event → Notion mutation mapping
│   ├── field-ownership.md      # Who owns what fields
│   ├── reconcile.md            # Drift detection + nightly reconcile logic
│   └── idempotency.md          # Dedupe keys and upsert rules
└── examples/
    ├── phase-lifecycle.md       # Phase start → progress → complete flow
    └── conversational-capture.md # Life area quick-add examples
```

### Canonical Event Envelope

All events use a single standardized shape:

```json
{
  "event_type": "phase_started",
  "occurred_at": "2026-02-25T10:30:00Z",
  "project_id": "pumplai",
  "phase_id": "45",
  "container_id": null,
  "payload": {
    "phase_name": "Path Resolver + Constants Foundation",
    "milestone": "v1.5"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | yes | One of the defined event types |
| `occurred_at` | ISO 8601 | yes | When the event happened |
| `project_id` | string | if applicable | OpenClaw project ID |
| `phase_id` | string | if applicable | Phase number |
| `container_id` | string | if applicable | L3 container ID |
| `payload` | object | yes | Event-specific freeform data |

### Request Types

The skill accepts three request types via a single entry point:

#### 1. Event Sync (reactive)

Triggered by orchestration when OpenClaw events fire.

```json
{
  "request_type": "event_sync",
  "event": {
    "event_type": "phase_started",
    "occurred_at": "2026-02-25T10:30:00Z",
    "project_id": "pumplai",
    "phase_id": "45",
    "container_id": null,
    "payload": {
      "phase_name": "Path Resolver + Constants Foundation",
      "milestone": "v1.5"
    }
  }
}
```

#### 2. Conversational Capture

Triggered when ClawdiaPrime routes a life/task capture request.

```json
{
  "request_type": "capture",
  "capture": {
    "title": "Renew gym membership",
    "area": "Health",
    "status": "This Week",
    "notes": "Expires March 15, check for annual discount",
    "source": "conversation"
  }
}
```

#### 3. Reconcile (optional, scheduled)

Triggered by orchestration on a schedule (e.g., nightly). Compares OpenClaw state against Notion and fixes drift.

```json
{
  "request_type": "reconcile"
}
```

### Structured Result

Every invocation returns a structured result for observability:

```json
{
  "request_type": "event_sync",
  "result": {
    "created": 1,
    "updated": 0,
    "skipped": 0,
    "errors": [],
    "mutations": [
      {
        "action": "create",
        "target": "cards_db",
        "notion_page_id": "abc-123",
        "dedupe_key": "phase:pumplai:45",
        "timestamp": "2026-02-25T10:30:05Z"
      }
    ]
  }
}
```

## Idempotency & Dedupe Keys

**Rule: If dedupe key exists in Notion → update. If not → create.**

### Projects DB

| Dedupe Key | Format | Example |
|------------|--------|---------|
| `openclaw_project_id` | `{project_id}` | `pumplai` |

Unique constraint: one row per `openclaw_project_id`.

### Cards DB

| Card Origin | Dedupe Key Property | Format | Example |
|-------------|-------------------|--------|---------|
| Phase event | `openclaw_phase_id` | `{project_id}:{phase_id}` | `pumplai:45` |
| Container event | `openclaw_event_anchor` | `{project_id}:{container_id}:{event_type}` | `pumplai:l3-abc:container_failed` |
| Conversational capture | `capture_hash` | `sha256(normalize(title + area + target_week))[:12]` | `a3f8c2e91b04` |
| Manual (Notion-created) | none | — | User-created cards have no dedupe key |

**Normalization for capture_hash**: lowercase, strip whitespace, sort fields alphabetically. Target week is optional (omitted if not set).

### Upsert Logic

```
1. Search Cards DB for matching dedupe key
2. If found → update (respecting field ownership)
3. If not found → create
4. On replay: same dedupe key → update is a no-op (idempotent)
```

## Status Ownership Carve-Out

OpenClaw does **not** own Status on all cards. The rule:

| Condition | Status Owner | Rationale |
|-----------|-------------|-----------|
| Card has `openclaw_phase_id` or `openclaw_event_anchor` | OpenClaw | Lifecycle driven by events |
| Card has `capture_source = "Conversation"` but no OpenClaw linkage | Notion | User moves it manually |
| Card has `capture_source = "Manual"` (created in Notion) | Notion | OpenClaw doesn't know it exists |

**Implementation**: Before writing Status, check if `openclaw_phase_id` or `openclaw_event_anchor` is non-empty. If empty, skip Status field in the update.

## Notion Schema

### Projects DB

One row per real project (dev or life initiative).

| Property | Type | Dedupe | Description | Owner |
|----------|------|--------|-------------|-------|
| Name | title | — | Project name | OpenClaw |
| OpenClaw ID | rich_text | **unique** | `pumplai`, `smartai`, etc. | OpenClaw |
| Type | select | — | `Dev Project` \| `Life Initiative` | OpenClaw (initial), Notion (editable) |
| Status | select | — | `Active` \| `Paused` \| `Completed` \| `Archived` | OpenClaw |
| Repo/Path | url | — | Workspace path or repo URL | OpenClaw |
| Current Phase | rich_text | — | e.g., "Phase 45: Path Resolver" | OpenClaw |
| Milestone | rich_text | — | e.g., "v1.5 Config Consolidation" | OpenClaw |
| Sync Status | rich_text | — | Last sync result summary | OpenClaw |
| Sync Error | rich_text | — | Last error message (empty if clean) | OpenClaw |
| Notes | rich_text | — | Free-form annotations | Notion |
| Priority | select | — | `High` \| `Medium` \| `Low` | Notion |

### Cards DB

All actionable items — dev tasks, phase cards, life tasks.

| Property | Type | Dedupe | Description | Owner |
|----------|------|--------|-------------|-------|
| Name | title | — | Card title | OpenClaw (events) or User (capture) |
| Status | select | — | `Backlog` \| `This Week` \| `In Progress` \| `Waiting` \| `Done` \| `Archived` | Conditional (see carve-out) |
| Area | select | — | `Dev` \| `Health` \| `Finance` \| `Learning` \| `Relationships` \| `Admin` | OpenClaw (initial) or Notion |
| Project | relation | — | → Projects DB (optional) | OpenClaw |
| Card Type | select | — | `Phase` \| `Task` \| `Life Task` \| `Initiative` \| `Bug` \| `Incident` | OpenClaw |
| Capture Source | select | — | `OpenClaw Event` \| `Conversation` \| `Manual` | OpenClaw |
| OpenClaw Phase ID | rich_text | **dedupe** | `{project_id}:{phase_id}` | OpenClaw |
| OpenClaw Event Anchor | rich_text | **dedupe** | `{project_id}:{container_id}:{event_type}` | OpenClaw |
| Capture Hash | rich_text | **dedupe** | `sha256(norm(title+area+week))[:12]` | OpenClaw |
| Priority | select | — | `High` \| `Medium` \| `Low` | Notion |
| Target Week | date | — | When you intend to work on it | Notion |
| Notes | rich_text | — | Free-form | Notion |
| Activity | rich_text | — | Append-only event log | OpenClaw |
| Last Activity At | date | — | Timestamp of last activity log entry | OpenClaw |
| Last Synced | date | — | Last OpenClaw sync timestamp | OpenClaw |
| Created | created_time | — | Auto | System |

### Kanban Views (created on Cards DB)

| View | Filter | Sort |
|------|--------|------|
| All Cards | Status != Archived | Status group, then Priority |
| Dev | Area = Dev, Status != Archived | Status group |
| Health | Area = Health, Status != Archived | Status group |
| Finance | Area = Finance, Status != Archived | Status group |
| Learning | Area = Learning, Status != Archived | Status group |
| Relationships | Area = Relationships, Status != Archived | Status group |
| This Week (All) | Status = This Week | Area group, then Priority |

## Event → Mutation Mapping

### Project Events

| Event | Notion Mutation | Dedupe Key |
|-------|----------------|------------|
| `project_registered` | Upsert Projects DB row. Create "Project setup / triage" card (Status=Backlog, Area=Dev) | `openclaw_project_id` |
| `project_removed` | Update Projects DB row Status → Archived | `openclaw_project_id` |

### Phase Events

| Event | Notion Mutation | Dedupe Key |
|-------|----------------|------------|
| `phase_started` | Upsert phase card Status → In Progress. Update Projects DB Current Phase | `openclaw_phase_id` |
| `phase_completed` | Update phase card Status → Done. Append to Activity | `openclaw_phase_id` |
| `phase_blocked` | Update phase card Status → Waiting. Append blocker to Activity | `openclaw_phase_id` |

### Container Events (L3)

| Event | Notion Mutation | Card Created? |
|-------|----------------|---------------|
| `container_completed` (routine) | Append to parent phase card Activity | No |
| `container_completed` (meaningful — see rule below) | Create child card + append to Activity | Yes |
| `container_failed` (retries remaining) | Append failure to Activity | No |
| `container_failed` (retries exhausted) | Append to Activity. Set parent phase → Waiting | No |

#### Meaningful Container Rule (deterministic)

Create a card from an L3 container **only if any** of these are true:

1. Runtime > 10 minutes (configurable via `meaningful_container_runtime_min`)
2. Payload includes `requires_human_review: true`
3. Failure with actionable category: `tests_failed`, `lint_failed`, `deploy_failed`

Otherwise: activity log entry only.

### Build/Deploy Events

| Event | Notion Mutation |
|-------|----------------|
| `build_passed` / `tests_passed` / `deployed` | Append to Activity on relevant phase card |
| `tests_failed` | Append to Activity. Create "Fix: {suite}" card if persistent (>2 consecutive failures) |

### Activity Log Format

Append short structured lines to the `Activity` rich_text property:

```
[2026-02-25 14:03] build_passed: sha abc123
[2026-02-25 14:15] container_completed: l3-task-42 (3m12s)
[2026-02-25 15:00] tests_failed: unit tests (2/48 failed)
```

Update `Last Activity At` date on each append.

## Field Ownership (explicit)

### OpenClaw Owns (Notion should not override)
- Status transitions on OpenClaw-linked cards (has phase_id or event_anchor)
- OpenClaw IDs (project ID, phase ID, event anchor, capture hash)
- Timestamps (last synced, last activity at)
- Activity log (append-only)
- Card Type, Capture Source
- Project relation (on event-created cards)
- Sync Status, Sync Error (on Projects DB)

### Notion Owns (OpenClaw never writes)
- Priority
- Target Week
- Notes (free-form)
- Area (user can recategorize)
- Status on unlinked cards (no openclaw_phase_id, no event_anchor)

### Shared (OpenClaw sets initial, Notion can annotate)
- Name (OpenClaw sets from event, user can clarify)
- Project Type (OpenClaw sets "Dev Project", user can refine)

## Skill Workflow

### Event Sync Flow

```
1. Receive event envelope from orchestration
2. Resolve DB IDs (from cache or discover-first bootstrap)
3. Compute dedupe key from event envelope
4. Search Cards/Projects DB for existing row with that key
5. Route by event type:
   a. Project event → upsert Projects DB row
   b. Phase event → upsert phase card, update status (if OpenClaw-linked)
   c. Container event → find parent phase card, append to Activity
      - If meaningful container rule → also create child card
   d. Build event → find relevant card, append to Activity
6. Apply mutation via Notion:notion-create-pages or Notion:notion-update-page
7. Update Sync Status / Sync Error on Projects DB row
8. Return structured result: { created, updated, skipped, errors, mutations }
```

### Conversational Capture Flow

```
1. Receive capture payload from ClawdiaPrime
2. Resolve Cards DB ID (from cache)
3. Compute capture_hash from normalized title + area + target_week
4. Search Cards DB for existing capture_hash (dedupe check)
5. If exists → update (append notes, adjust status if explicitly changed)
6. If new → infer defaults:
   - Area from keywords ("gym" → Health, "taxes" → Finance)
   - Status: "This Week" if urgent language, else "Backlog"
   - Project relation: match if obvious, else leave empty
7. Notion:notion-create-pages → create card with properties
8. Return structured result: { created|updated, title, area, status, notion_url }
```

### Reconcile Flow

**Reconcile is boring and safe.** It never surprises you.

```
1. Read all OpenClaw project states (projects/*.json, .planning/ROADMAP.md)
2. Notion:notion-search → fetch all rows from Projects DB and active Cards
3. Allowed corrections:
   a. Projects in OpenClaw but missing from Notion → create
   b. Status mismatch on OpenClaw-linked cards → fix Notion to match OpenClaw
   c. Missing relations (card ↔ project) → backfill
   d. Missing views/properties on DBs → repair
   e. Dangling cards (phase no longer exists in OpenClaw) → Status → Archived
4. NOT allowed:
   a. Change Status on unlinked cards (Notion owns those)
   b. Delete anything (use Archived status instead)
   c. Modify Notion-owned fields (priority, notes, target week)
5. Apply corrections via Notion:notion-update-page
6. Return drift report: { corrections_made, in_sync_count, archived_count, errors }
```

## Discovery & Bootstrap

On first invocation (no cached DB IDs):

```
1. Notion:notion-search query="Projects" → look for existing Projects database
2. If found → Notion:notion-fetch to verify schema (check for OpenClaw ID property)
   - If schema matches → cache database_id, proceed
   - If schema differs → warn user, suggest migration
3. If not found → Notion:notion-create-pages to create Projects DB with schema above
4. Repeat for Cards DB (search for "Cards" or "Tasks")
5. Create default kanban views on Cards DB
6. Store discovered/created IDs in skill config (skills/notion-kanban-sync/config.json)
```

## Error Handling & Observability

### Per-Project Sync Status

The Projects DB carries `Sync Status` and `Sync Error` fields, updated after every sync:

- **Sync Status**: `"OK: 3 created, 1 updated"` or `"Error: see Sync Error"`
- **Sync Error**: `"429 Too Many Requests at 14:03"` or empty if clean

### Notion API Error Handling

| Error | Action |
|-------|--------|
| 429 (rate limit) | Retry with exponential backoff (1s, 2s, 4s, max 3 retries) |
| 5xx (server error) | Retry once after 2s, then skip and record in Sync Error |
| 400 (bad request) | Do not retry. Log error payload. Record in Sync Error |
| 404 (page not found) | Clear cached DB ID, re-run discovery. If still 404, record error |

### Structured Logs

Every mutation emits a log line:

```json
{"level": "info", "skill": "notion-kanban-sync", "action": "upsert", "target": "cards_db", "dedupe_key": "phase:pumplai:45", "result": "created", "notion_page_id": "abc-123"}
```

## Integration Points

### Orchestration → Skill Invocation

The skill is invoked via standard OpenClaw skill dispatch:

```bash
openclaw agent --agent main --skill notion-kanban-sync --payload '{"request_type":"event_sync","event":{...}}'
```

Or via the router skill when ClawdiaPrime delegates.

### Event Sources

Events come from existing OpenClaw components:

| Source | Events | Envelope Fields Set |
|--------|--------|---------------------|
| `state_engine.py` | `phase_started`, `phase_completed`, `phase_blocked` | project_id, phase_id, payload.phase_name, payload.milestone |
| `spawn.py` / `pool.py` | `container_completed`, `container_failed` | project_id, phase_id, container_id, payload.runtime_seconds, payload.requires_human_review, payload.failure_category |
| `project_cli.py` | `project_registered`, `project_removed` | project_id, payload.name, payload.workspace_path |
| Future: CI hooks | `build_passed`, `tests_passed`, `tests_failed`, `deployed` | project_id, phase_id, payload.sha, payload.suite, payload.failure_count |

### Hooks (new)

New event hooks needed in OpenClaw orchestration:

1. **State engine hook**: After `update_task_status()` → emit phase event via envelope
2. **Spawn hook**: After container lifecycle → emit container event via envelope
3. **Project CLI hook**: After `init`/`remove` → emit project event via envelope

## Configuration

```json
// skills/notion-kanban-sync/config.json
{
  "notion_projects_db_id": null,
  "notion_cards_db_id": null,
  "auto_create_dbs": true,
  "reconcile_schedule": "nightly",
  "meaningful_container_runtime_min": 10,
  "persistent_failure_threshold": 2,
  "retry_max_attempts": 3,
  "retry_base_delay_seconds": 1,
  "default_dev_area": "Dev",
  "area_keywords": {
    "Health": ["gym", "workout", "doctor", "health", "exercise", "diet", "sleep"],
    "Finance": ["tax", "invest", "budget", "payment", "invoice", "expense"],
    "Learning": ["course", "book", "study", "learn", "tutorial", "certification"],
    "Relationships": ["family", "friend", "birthday", "gift", "catch up", "dinner"],
    "Admin": ["renew", "insurance", "passport", "appointment", "register"]
  }
}
```

## Implementation Plan

### Phase 0 — Plumbing (1-2 sessions)

- Skill skeleton: `skills/notion-kanban-sync/` with SKILL.md, _meta.json, config.json
- Notion client wrapper: rate-limit, retry with backoff, typed helpers (search DB, upsert page, update props)
- Bootstrap/discover-first: find existing DBs by name + signature properties, create if missing
- Cache DB IDs to config.json after discovery

### Phase 1 — Core Data Model

- Implement schema creation for Projects DB and Cards DB (all properties)
- Create kanban views (All, This Week, per-area)
- Verify bootstrap end-to-end: first run creates DBs, second run uses cached IDs

### Phase 2 — Event Sync MVP

- Implement upsert handlers for: `project_registered`, `phase_started`, `phase_completed`
- Container/build → append Activity log entries
- Idempotency: enforce dedupe keys, test replays produce no duplicates
- Structured result returned for every invocation

### Phase 3 — Conversational Capture MVP

- Capture handler: parse area + title, infer defaults
- Capture hash generation and dedupe check
- Status defaults: "This Week" for urgent language, "Backlog" otherwise

### Phase 4 — Reconcile + Polish

- Reconcile: verify DB schema, spot-check OpenClaw-linked cards for drift
- Allowed corrections only (backfill relations, archive dangling, fix status mismatch)
- Drift report with structured output

### Phase 5 — Hardening

- Tests: idempotent replays, duplicate prevention, partial failures (429/5xx)
- Observability: structured logs, Sync Status/Sync Error on Projects DB
- Error handling: retry logic, cached ID invalidation on 404

## Success Criteria

1. Phase lifecycle events create/update Notion cards with correct status transitions
2. Replay of the same event produces no duplicates (idempotent)
3. New project registration creates Projects DB row + triage card
4. Conversational capture creates cards with correct area inference and dedupe
5. Container events append to activity log without spamming new cards (meaningful rule enforced)
6. Unlinked cards (manual/conversational) have Notion-owned Status — OpenClaw never overwrites
7. Reconcile detects drift, applies only allowed corrections, never deletes
8. DB discovery works on first run; cached IDs used on subsequent runs
9. Field ownership respected — every write checks ownership before touching a field
10. Structured result returned for every invocation with created/updated/skipped/errors
11. 429/5xx errors handled with retry + backoff; failures recorded in Sync Error

## Out of Scope (for this phase)

- Calendar integration
- Habit tracker integration
- Financial data ingestion
- Bidirectional sync (Notion → OpenClaw)
- Sub-task hierarchy (L3 tasks as child cards)
- Recurring task automation
- Dashboard integration (OCCC showing Notion state)
- Events DB (future upgrade from Activity rich_text if it outgrows the field)

## Dependencies

- Existing Notion MCP tools (`notion-search`, `notion-fetch`, `notion-create-pages`, `notion-update-page`)
- OpenClaw event hook infrastructure (new — needs implementation or can piggyback on existing patterns)
- Notion workspace with API access configured
