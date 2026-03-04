# Phase 50: Notion Kanban Sync - Research

**Researched:** 2026-02-25
**Domain:** Notion API integration, event-driven architecture, L2 skill authoring
**Confidence:** HIGH (codebase verified directly; Notion API from project's own SKILL.md)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Event model**: Event bus / hook registry pattern — components emit to central registry, listeners subscribe
- **Failure isolation**: Fire-and-forget — Notion sync failure never blocks orchestration. Errors logged, not propagated
- **Notion API access**: Use existing Notion MCP tools (notion-search, notion-create-pages, notion-update-page) — no custom HTTP client
- **Token storage**: NOTION_TOKEN as environment variable
- **DB ID persistence**: Cache discovered Notion DB IDs to `skills/notion-kanban-sync/config.json` across sessions
- **Capture UX**: Keyword detection for routing, silent creation with summary, best-guess area inference tagged "(area inferred)", batch input supported
- **Phase scope**: All 6 internal sub-phases (plumbing, schema, event sync, capture, reconcile, hardening) in this single GSD phase
- **Milestone boundary**: New milestone (v2.0) — independent of v1.5 Config Consolidation

### Claude's Discretion

- Event bus module placement and internal architecture
- Rate limiting wrapper implementation details
- Area keyword matching algorithm specifics
- Exact retry queue format and cleanup strategy
- Reconcile scheduling mechanism

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

The REQUIREMENTS.md does not yet contain NOTION-01 through NOTION-11 — they are defined only in the SPEC.md. These must be added to REQUIREMENTS.md as part of this phase's Wave 0.

Based on the SPEC.md success criteria and the request IDs from the prompt, the requirements map as:

| ID | Behavior | Research Support |
|----|----------|-----------------|
| NOTION-01 | Phase lifecycle events create/update Notion cards with correct status transitions | Event bus hook in state_engine.py + pool.py → notion_client upsert |
| NOTION-02 | Replay of same event produces no duplicates (idempotent) | Dedupe key model in SPEC; upsert-if-exists logic in Notion client wrapper |
| NOTION-03 | New project registration creates Projects DB row + triage card | Hook in project_cli.py cmd_init + cmd_remove → notion_client upsert |
| NOTION-04 | Conversational capture creates cards with correct area inference and dedupe | capture_hash generation, keyword map, capture handler |
| NOTION-05 | Container events append to activity log without spamming new cards (meaningful rule) | meaningful_container_runtime_min config + 3-condition rule from SPEC |
| NOTION-06 | Unlinked cards have Notion-owned Status — OpenClaw never overwrites | Field ownership check before every Status write |
| NOTION-07 | Reconcile detects drift, applies only allowed corrections, never deletes | Reconcile handler with allowed-corrections-only guard |
| NOTION-08 | DB discovery works on first run; cached IDs used on subsequent runs | Discover-first bootstrap + config.json cache |
| NOTION-09 | Field ownership respected — every write checks ownership before touching a field | Ownership check in every mutation helper |
| NOTION-10 | Structured result returned for every invocation with created/updated/skipped/errors | Unified return shape from all three request_type handlers |
| NOTION-11 | 429/5xx errors handled with retry + backoff; failures recorded in Sync Error | Retry wrapper with exponential backoff; Sync Error field on Projects DB row |

</phase_requirements>

---

## Summary

Phase 50 delivers the Notion Kanban Sync capability as a new L2-level skill with a full event bus infrastructure built inline. There are three distinct engineering concerns:

**1. Event Bus Infrastructure.** No event bus exists in the codebase today. The project uses direct function calls and threading for side-effects (memory injection, extraction). The event bus must be a new lightweight module (recommended: `packages/orchestration/src/openclaw/event_bus.py`) that provides `emit(event_envelope)` and `subscribe(event_type, handler)`. Hook sites are: `state_engine.py:update_task()` (phase events), `pool.py:_attempt_task()` (container events), and `cli/project.py:cmd_init()/cmd_remove()` (project events). All hooks are fire-and-forget — exceptions must never propagate to callers.

**2. Notion Client Wrapper.** The project's `skills/notion/SKILL.md` documents the Notion API version `2025-09-03` with a key behavioral difference: databases are now "data sources" with two IDs (`database_id` for page creation, `data_source_id` for queries). All API interaction is via direct HTTP using the stored token — the Notion MCP tools referenced in CONTEXT.md are for the agent's interactive use, not Python-level automation. The skill itself is a Python script callable by the agent, which in turn uses `httpx` (already a dependency) for direct API calls. Rate limit is ~3 requests/second; retry with exponential backoff (1s, 2s, 4s, max 3) is required.

**3. Skill Structure.** Existing L2 skills (router: Node.js, spawn: Python, review: Python) are minimal scripts with a `skill.json` metadata file. The new skill follows the Python pattern with a SKILL.md knowledge file, `_meta.json` (hub metadata), `config.json` (cached DB IDs + tuning), and a main entry point Python script. The skill accepts three `request_type` values via a JSON payload: `event_sync`, `capture`, `reconcile`.

**Primary recommendation:** Build `event_bus.py` as a standalone module in the `openclaw` package (imported by state_engine, pool, project_cli), implement the Notion client wrapper using `httpx` with the 2025-09-03 API, and structure the skill as a single Python entry point dispatching to three handlers. Keep all Notion mutations fire-and-forget from the orchestration perspective.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | (already in pyproject.toml) | HTTP client for Notion API calls | Already a project dependency; used by spawn.py for memU |
| json | stdlib | Config persistence, payload parsing | No additional dependency needed |
| hashlib | stdlib | sha256 for capture_hash generation | SHA256 needed for dedupe key; stdlib |
| threading | stdlib | Fire-and-forget event emission (same pattern as memory_injector) | Already used for memory side-effects in state_engine.py |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + pytest-asyncio | already in dev deps | Test suite for idempotency, retry logic | All test phases |
| functools.lru_cache | stdlib | In-process config cache for DB IDs | Avoid re-reading config.json on every event |
| datetime / timezone | stdlib | ISO 8601 timestamps in event envelopes | Consistent with existing state_engine.py pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx (direct API) | notion-client (official Python SDK) | notion-client adds a new pip dependency; httpx already present and sufficient |
| threading fire-and-forget | asyncio.create_task | Pool context is async; state_engine context is sync. Threading (like memory_injector) works in both |
| JSON file for retry queue | SQLite | JSON file is simpler, consistent with existing config.json pattern; SQLite overkill for <100 events |

**Installation:**
```bash
# No new dependencies — httpx already in pyproject.toml
# jsonschema already in pyproject.toml for config.json validation if needed
```

---

## Architecture Patterns

### Recommended Skill Structure

```
skills/notion-kanban-sync/
├── SKILL.md                    # Skill knowledge file (workflow, API patterns)
├── _meta.json                  # Hub metadata (ownerId, slug, version)
├── skill.json                  # Skill definition (id, commands, handler)
├── config.json                 # Runtime state: DB IDs, tuning params
├── notion_sync.py              # Main entry point — dispatches by request_type
├── notion_client.py            # HTTP wrapper: rate-limit, retry, typed helpers
├── event_bus_hook.py           # Thin shim: called by event_bus.py subscription
├── retry_queue.json            # Failed events for re-attempt (auto-created)
└── reference/
    ├── schema.md
    ├── event-mapping.md
    ├── field-ownership.md
    ├── reconcile.md
    └── idempotency.md
```

Event bus placement (in orchestration package):

```
packages/orchestration/src/openclaw/
├── event_bus.py               # NEW: emit() + subscribe() registry
├── state_engine.py            # MODIFIED: emit after update_task()
├── cli/
│   └── project.py             # MODIFIED: emit after cmd_init() / cmd_remove()
└── ...
```

Pool hook placement:

```
skills/spawn/
├── pool.py                    # MODIFIED: emit after _attempt_task() completion/failure
└── ...
```

### Pattern 1: Event Bus — Thin Registry with Fire-and-Forget

**What:** A module-level dict mapping `event_type → List[Callable]`. `emit()` calls each handler in a daemon thread. Exceptions in handlers are caught and logged, never re-raised.

**When to use:** Any time state changes in orchestration that downstream observers may care about.

**Example:**
```python
# packages/orchestration/src/openclaw/event_bus.py
import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List

_handlers: Dict[str, List[Callable]] = defaultdict(list)
_logger = None  # set lazily to avoid circular import

def subscribe(event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
    """Register a handler for an event type. Handler receives the full envelope."""
    _handlers[event_type].append(handler)

def emit(envelope: Dict[str, Any]) -> None:
    """Emit an event envelope to all registered handlers. Fire-and-forget."""
    event_type = envelope.get("event_type", "")
    for handler in list(_handlers.get(event_type, [])):
        t = threading.Thread(target=_call_handler, args=(handler, envelope), daemon=True)
        t.start()

def _call_handler(handler: Callable, envelope: Dict[str, Any]) -> None:
    try:
        handler(envelope)
    except Exception as exc:
        import logging
        logging.getLogger("event_bus").error(f"Handler {handler.__name__} failed: {exc}")
```

### Pattern 2: Hook Site in state_engine.update_task()

**What:** After the successful `_write_state_locked()` call and before memory triggers, emit a phase event. The event_type derives from the status transition.

**Example:**
```python
# In state_engine.py update_task() — after _write_state_locked()
# Add after existing memory trigger block
try:
    from .event_bus import emit
    from datetime import datetime, timezone
    _status_to_event = {
        "in_progress": "phase_started",
        "completed": "phase_completed",
        "waiting": "phase_blocked",
    }
    evt_type = _status_to_event.get(status)
    if evt_type and task_id:
        emit({
            "event_type": evt_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "phase_id": task_id,
            "container_id": None,
            "payload": {"activity_entry": activity_entry},
        })
except Exception as _evt_exc:
    logger.error(f"Event emission failed (non-blocking): {_evt_exc}")
```

Note: `project_id` must be retrieved inside the hook — `update_task()` currently calls `get_active_project_id()` for memory triggers. The same call works here.

### Pattern 3: Hook Site in pool.py _attempt_task()

**What:** After the container result is determined (completed/failed/timeout), emit a container event. Runtime in seconds is available as `completed_at - spawn_requested_at`. The meaningful container rule is evaluated in the Notion handler, not at the emit site.

**Example:**
```python
# In pool.py _attempt_task() — after result["status"] is set
try:
    from openclaw.event_bus import emit
    from datetime import datetime, timezone
    runtime_seconds = completed_at - spawn_requested_at if completed_at else 0
    evt_type = "container_completed" if result["status"] == "completed" else "container_failed"
    emit({
        "event_type": evt_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "project_id": self.project_id,
        "phase_id": task_id,  # task_id maps to phase context
        "container_id": container_name if container else None,
        "payload": {
            "runtime_seconds": round(runtime_seconds, 1),
            "exit_code": result.get("exit_code"),
            "retry_count": retry_count,
            "failure_category": None,  # populated for known failure modes
            "requires_human_review": False,
        },
    })
except Exception as _evt_exc:
    logger.error(f"Event emission failed: {_evt_exc}")
```

The `container_name` variable exists in `spawn_l3_specialist()` but not directly in `_attempt_task()`. The container's `.name` attribute is accessible via `container.name` in the pool's active_containers dict.

### Pattern 4: Hook Site in project_cli.py

**What:** After `_set_active_project()` in `cmd_init()`, emit `project_registered`. After `shutil.rmtree()` in `cmd_remove()`, emit `project_removed`.

**Example:**
```python
# At end of cmd_init() success path
try:
    from openclaw.event_bus import emit
    from datetime import datetime, timezone
    emit({
        "event_type": "project_registered",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "phase_id": None,
        "container_id": None,
        "payload": {
            "name": project_name,
            "workspace_path": workspace_path,
        },
    })
except Exception:
    pass  # non-fatal; CLI must not fail due to event emission
```

### Pattern 5: Notion Upsert with Dedupe Key

**What:** Search for existing page by dedupe property value, then create-or-update.

**Example (from skills/notion/SKILL.md patterns):**
```python
# notion_client.py — upsert_card()
def _search_by_property(self, db_id: str, property_name: str, value: str) -> Optional[str]:
    """Return page_id if a page with property_name == value exists, else None."""
    # POST /v1/data_sources/{data_source_id}/query with filter
    # Note: use data_source_id for queries, database_id for creates
    resp = self._request("POST", f"/v1/data_sources/{self._get_ds_id(db_id)}/query", json={
        "filter": {
            "property": property_name,
            "rich_text": {"equals": value}
        }
    })
    results = resp.get("results", [])
    return results[0]["id"] if results else None

def upsert_card(self, dedupe_property: str, dedupe_value: str, properties: dict) -> dict:
    page_id = self._search_by_property(self._cards_db_id, dedupe_property, dedupe_value)
    if page_id:
        return self._update_page(page_id, properties)
    else:
        return self._create_page(self._cards_db_id, properties)
```

### Pattern 6: Skill Invocation

Existing skills are invoked by the agent or router. The `skill.json` defines the command and handler. For Python skills, the handler is `python3 notion_sync.py`. The agent passes a JSON payload via stdin or argument.

```json
// skills/notion-kanban-sync/skill.json
{
  "id": "notion-kanban-sync",
  "name": "Notion Kanban Sync",
  "description": "Syncs OpenClaw state to Notion kanban board. Handles event sync, conversational capture, and reconciliation.",
  "owner": "main",
  "commands": [
    {
      "name": "sync",
      "description": "Handle an event sync, capture, or reconcile request.",
      "parameters": {
        "payload": { "type": "string", "required": true }
      },
      "handler": "python3 notion_sync.py"
    }
  ]
}
```

### Anti-Patterns to Avoid

- **Blocking the caller on Notion failure**: All event handlers must be in daemon threads. The `emit()` call returns immediately — never `thread.join()` on a Notion handler in the orchestration hot path.
- **Re-querying Notion on every event**: Bootstrap once, cache `projects_db_id` and `cards_db_id` in `config.json`. Read on startup, write after discovery. Never re-discover if IDs are cached and valid (only re-discover on 404).
- **Writing Notion-owned fields on every sync**: Check field ownership before every property write. Priority, Notes, Target Week, Area (on user-modified cards) are never written by OpenClaw.
- **Using `database_id` for queries in API 2025-09-03**: The Notion SKILL.md documents that queries use `data_source_id`, not `database_id`. Creates still use `database_id`. This is a hard correctness requirement.
- **Treating all task_ids as phase_ids**: The state_engine `task_id` field corresponds to GSD plan tasks within a phase, not the phase number. The phase_id in the event envelope should come from a higher-level context (the active phase, or from the task metadata). Clarification needed — see Open Questions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client for Notion | Custom requests wrapper | httpx (already present) | Already used for memU; consistent pattern |
| Exponential backoff | Manual sleep loop | Built-in retry logic in notion_client.py | 3 lines with httpx transport or manual; not complex enough to need a library |
| SHA256 hashing | Custom hash function | `hashlib.sha256()` | stdlib, correct, already used elsewhere in Python ecosystem |
| Event notification | asyncio event system | threading.Thread (daemon) | state_engine is sync; threading works in both sync and async contexts without event loop dependency |
| Config file parsing | Custom parser | `json.load()` / `json.dump()` | Consistent with every other config file in the project (openclaw.json, project.json, skill.json) |

**Key insight:** The codebase consistently uses stdlib + minimal third-party (httpx, docker). Match this pattern exactly. Adding notion-client SDK would introduce an unreviewed dependency when httpx is already sufficient.

---

## Common Pitfalls

### Pitfall 1: Notion API Version — data_source_id vs database_id

**What goes wrong:** Using `database_id` when querying, getting 404 or incorrect results. The SKILL.md explicitly documents: use `data_source_id` for queries (`/v1/data_sources/{id}/query`), use `database_id` for page creation (`parent: {"database_id": "..."}`).

**Why it happens:** The 2025-09-03 API version renamed "databases" to "data sources" and split the ID space. Older docs and pre-September knowledge show a single `database_id` for all operations.

**How to avoid:** Cache BOTH `database_id` and `data_source_id` in `config.json`. The search result for a database returns both. Wrapper must track them separately.

**Warning signs:** 404 on `/v1/data_sources/{id}/query` — check if `database_id` was passed instead of `data_source_id`.

### Pitfall 2: Event Bus Registration Timing

**What goes wrong:** Event bus subscriptions registered after the first event fires (e.g., if project CLI emits `project_registered` before `event_bus_hook.py` registers its listener).

**Why it happens:** Python module import order. If `event_bus.py` is imported early but the Notion handler subscription only happens when `notion_sync.py` is explicitly invoked, the hook registration is never set up for CLI-triggered events.

**How to avoid:** The event bus subscription must be registered at import time of a module that is guaranteed to be imported before any hook sites fire. Best approach: a separate `openclaw/notion_hook.py` that is imported in `__init__.py` or in each hook site's own import block (lazy import pattern used throughout the codebase).

**Warning signs:** Events are emitted (logs show `emit()` called) but no Notion mutations happen.

### Pitfall 3: Circular Import — event_bus ↔ state_engine

**What goes wrong:** `event_bus.py` imports from `state_engine.py` (for logging or project ID resolution), `state_engine.py` imports from `event_bus.py`, causing circular import at module load.

**Why it happens:** The `openclaw` package already has several lazy import patterns (e.g., `from .memory_injector import ...` inside functions) specifically to avoid this. The event bus must follow the same pattern.

**How to avoid:** `event_bus.py` must have zero imports from the `openclaw` package at module level. Use `import logging` (stdlib) for its own logger. State_engine imports event_bus via lazy import inside `update_task()`:
```python
from .event_bus import emit  # inside the function, not at module top
```

**Warning signs:** `ImportError: cannot import name 'emit' from partially initialized module 'openclaw.event_bus'`

### Pitfall 4: Concurrent Config.json Writes

**What goes wrong:** Two simultaneous events both discover that `projects_db_id` is null (race condition), both trigger bootstrap, both write different values to `config.json`, second write wins — but by then the first created a duplicate DB.

**Why it happens:** No locking on `config.json` reads/writes. Multiple events can fire in parallel (daemon threads from `emit()`).

**How to avoid:** Use a module-level `threading.Lock()` in `notion_client.py` for config reads/writes and for the bootstrap sequence. The lock scope is small (just the dict read + file write). This is the same pattern the codebase uses for `_docker_client` singleton in spawn.py.

**Warning signs:** Two Projects DBs appear in Notion named "Projects" — first run created one, second created another before the ID was cached.

### Pitfall 5: project_id Missing from state_engine.update_task() Context

**What goes wrong:** The event envelope requires `project_id`, but `update_task()` doesn't currently receive it as a parameter — it calls `get_active_project_id()` internally for memory triggers.

**Why it happens:** `update_task()` takes `task_id, status, activity_entry` — no project_id argument. The `get_active_project_id()` call inside works for single-project scenarios but may be incorrect in multi-project concurrent scenarios.

**How to avoid:** Follow the existing memory trigger pattern exactly — call `get_active_project_id()` in the event emission block too. This is the established pattern and consistent with v1.5 decisions (45-01 locked: `get_state_path()` requires explicit project_id, but runtime active project is still resolved via `get_active_project_id()` at call time).

**Warning signs:** Events emitted with wrong `project_id` (shows a different project's ID in Notion cards).

### Pitfall 6: Notion API Rate Limit in Reconcile

**What goes wrong:** Reconcile fetches all projects and all cards in a loop — each fetch is a separate API call. With 10 projects and 200 cards, that's 210+ calls in rapid succession, hitting the ~3 req/s rate limit (≈70 seconds minimum for sequential calls).

**Why it happens:** Reconcile is a bulk read operation. The Notion API does not support bulk queries.

**How to avoid:** Add a `time.sleep(0.35)` between requests in `notion_client.py` request wrapper when in "bulk" mode, or use the retry mechanism (429 → backoff) and accept that reconcile is slow. Reconcile runs nightly — slowness is acceptable. Do not try to parallelize Notion API calls.

**Warning signs:** Reconcile logs show many 429 errors in sequence.

### Pitfall 7: Activity Field Append Requires Read-Before-Write

**What goes wrong:** Appending to the `Activity` rich_text property requires reading the current value first, appending the new line, then writing the full updated string. Writing just the new line overwrites the existing content.

**Why it happens:** The Notion API `PATCH /pages/{id}` with a `rich_text` property replaces the entire field — it does not append.

**How to avoid:** In `notion_client.py`, `append_activity()` must: (1) fetch current page to get existing Activity text, (2) prepend or append new line, (3) PATCH with full combined text. This is 2 API calls per append. Factor this into rate limit planning.

**Warning signs:** Activity field shows only the most recent entry — previous entries disappear.

---

## Code Examples

Verified patterns from `skills/notion/SKILL.md` (project's own authoritative source, API version 2025-09-03):

### Create a page in a database

```python
# Source: skills/notion/SKILL.md
import httpx, os

NOTION_KEY = os.environ["NOTION_TOKEN"]
HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json",
}

def create_page(database_id: str, properties: dict) -> dict:
    resp = httpx.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json={
            "parent": {"database_id": database_id},
            "properties": properties,
        }
    )
    resp.raise_for_status()
    return resp.json()
```

### Query a database (data source)

```python
# Source: skills/notion/SKILL.md — uses data_source_id, NOT database_id
def query_database(data_source_id: str, filter_: dict) -> list:
    resp = httpx.post(
        f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
        headers=HEADERS,
        json={"filter": filter_},
    )
    resp.raise_for_status()
    return resp.json().get("results", [])
```

### Update page properties

```python
# Source: skills/notion/SKILL.md
def update_page(page_id: str, properties: dict) -> dict:
    resp = httpx.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS,
        json={"properties": properties},
    )
    resp.raise_for_status()
    return resp.json()
```

### Property formats (from SKILL.md)

```python
# rich_text property
{"Activity": {"rich_text": [{"text": {"content": "new content"}}]}}

# select property
{"Status": {"select": {"name": "In Progress"}}}

# date property
{"Last Synced": {"date": {"start": "2026-02-25T10:30:00Z"}}}

# relation property (card → project)
{"Project": {"relation": [{"id": "project-page-uuid"}]}}
```

### Create a database

```python
# Source: skills/notion/SKILL.md
def create_database(parent_page_id: str, title: str, properties: dict) -> dict:
    resp = httpx.post(
        "https://api.notion.com/v1/data_sources",
        headers=HEADERS,
        json={
            "parent": {"page_id": parent_page_id},
            "title": [{"text": {"content": title}}],
            "properties": properties,
            "is_inline": True,
        }
    )
    resp.raise_for_status()
    return resp.json()
```

### Retry wrapper with exponential backoff

```python
# Pattern: mirrors state_engine.py retry loop structure
import time, httpx

def _request_with_retry(method: str, url: str, max_retries: int = 3, **kwargs) -> dict:
    base_delay = 1.0
    for attempt in range(max_retries + 1):
        try:
            resp = httpx.request(method, url, headers=HEADERS, **kwargs)
            if resp.status_code == 429:
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise RuntimeError(f"Rate limit after {max_retries} retries")
            if resp.status_code >= 500:
                if attempt < max_retries:
                    time.sleep(2.0)
                    continue
                raise RuntimeError(f"Server error {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as exc:
            if attempt == max_retries:
                raise
            time.sleep(base_delay * (2 ** attempt))
    raise RuntimeError("Request failed after all retries")
```

### Capture hash generation

```python
# Source: SPEC.md idempotency model
import hashlib

def compute_capture_hash(title: str, area: str, target_week: str = "") -> str:
    """Normalize and hash for dedupe. target_week omitted if empty."""
    parts = {"title": title.strip().lower(), "area": area.strip().lower()}
    if target_week:
        parts["target_week"] = target_week.strip().lower()
    # Sort fields alphabetically, join
    normalized = "|".join(f"{k}:{v}" for k, v in sorted(parts.items()))
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]
```

### Fire-and-forget event bus subscription

```python
# In event_bus_hook.py (registered at import time)
from openclaw.event_bus import subscribe

def _handle_phase_started(envelope: dict) -> None:
    from skills.notion_kanban_sync.notion_sync import handle_event_sync
    handle_event_sync(envelope)

def _handle_container_event(envelope: dict) -> None:
    from skills.notion_kanban_sync.notion_sync import handle_event_sync
    handle_event_sync(envelope)

subscribe("phase_started", _handle_phase_started)
subscribe("phase_completed", _handle_phase_started)
subscribe("phase_blocked", _handle_phase_started)
subscribe("container_completed", _handle_container_event)
subscribe("container_failed", _handle_container_event)
subscribe("project_registered", _handle_phase_started)
subscribe("project_removed", _handle_phase_started)
```

---

## Codebase Hook Analysis

### state_engine.py: update_task()

**Current shape**: `update_task(task_id, status, activity_entry)` — no project_id arg.

**Hook insertion point**: After `_write_state_locked()` succeeds, before `rotate_activity_log()` call. The `project_id` is obtained via `get_active_project_id()` (same call used for memory triggers at line 362). The status-to-event mapping: `in_progress` → `phase_started`, `completed` → `phase_completed`, `waiting` → `phase_blocked`. All other statuses do not emit.

**Risk**: LOW. The hook is inside the `break` of the retry loop, after the write lock is released. Exception isolation (try/except) matches the memory trigger pattern already present.

### pool.py: _attempt_task()

**Current shape**: Async method, resolves `completed_at` and `spawn_requested_at` as floats, has `container.name` accessible via `container` variable.

**Hook insertion point**: After the `if result["status"] == "completed"` / `else` branch (lines ~428-455), before `jarvis.set_task_metric(task_id, "lock_wait_ms", ...)`. The `self.project_id` field is available directly. Runtime seconds = `completed_at - spawn_requested_at`. Container name = `container.name` if container is not None.

**Risk**: LOW. Same fire-and-forget pattern as `_memorize_snapshot_fire_and_forget`. The threading approach works in async context (daemon thread launched from asyncio coroutine).

### project_cli.py: cmd_init() and cmd_remove()

**Current shape**: Synchronous functions returning int exit code. `project_id` and `project_name` are local variables.

**Hook insertion point**:
- `cmd_init()`: After `_set_active_project(project_id, root)` succeeds (line 293), before the success print.
- `cmd_remove()`: After `shutil.rmtree(project_dir)` (line 456), before the success print.

**Risk**: VERY LOW. CLI functions are synchronous. The event emission is fire-and-forget in a daemon thread. If Notion is unconfigured (no NOTION_TOKEN), the handler should detect this and return silently.

### What Does NOT Need Hooking

- `state_engine.create_task()` — task creation is an L3 setup event, not a phase event. Container events come from pool.
- `state_engine.set_task_metric()` — internal metric, not phase-level.
- `state_engine.rotate_activity_log()` — housekeeping, not observable.

---

## Discovery and Bootstrap Architecture

### First-Run Bootstrap Flow (verified against Notion SKILL.md API)

```
1. Read skills/notion-kanban-sync/config.json
   - If notion_projects_db_id is null → trigger bootstrap
   - If non-null → use cached IDs (validate with single GET, skip if 200)
2. Bootstrap:
   a. POST /v1/search {"query": "Projects", "filter": {"value": "database", "property": "object"}}
   b. Filter results: look for object type "data_source" with title "Projects" AND "OpenClaw ID" property
   c. If found → cache database_id + data_source_id
   d. If not found → POST /v1/data_sources to create (requires parent page_id)
3. Repeat for Cards DB
4. Write both IDs to config.json (thread-safe with Lock)
```

**Critical gap**: Creating a new database requires a `parent.page_id`. On first bootstrap, the user must provide a parent page. This means `NOTION_PARENT_PAGE_ID` is a required config alongside `NOTION_TOKEN`. Store in `config.json` (user sets it once, then it's persisted).

**Alternative**: Skip DB creation and require user to pre-create the DBs and provide IDs directly in `config.json`. This avoids the parent page requirement and is simpler. The SPEC supports this via `auto_create_dbs: true` toggle.

### Retry Queue Design

```json
// skills/notion-kanban-sync/retry_queue.json
[
  {
    "envelope": { "event_type": "phase_started", ... },
    "failed_at": "2026-02-25T10:30:00Z",
    "attempt_count": 1,
    "last_error": "429 Too Many Requests"
  }
]
```

The retry queue is read and replayed on each Notion handler invocation. Queue file is protected by a module-level threading.Lock(). Events older than 24 hours are dropped (configurable). Max queue size: 100 events (configurable). On retry, use same upsert logic — idempotent by design.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Notion database queries use `database_id` | Must use `data_source_id` for queries | Notion API 2025-09-03 | All query calls must use the new endpoint and ID type |
| Notion search returns `"object": "database"` | Returns `"object": "data_source"` | API 2025-09-03 | Filter logic in bootstrap must check for `"data_source"` not `"database"` |
| OpenClaw has no event bus | New `event_bus.py` module | Phase 50 | First use of observer pattern in the orchestration package |

**Deprecated/outdated:**
- Querying Notion databases via `POST /v1/databases/{id}/query` — now `POST /v1/data_sources/{id}/query`
- Search result object type `"database"` — now `"data_source"` in API 2025-09-03

---

## Open Questions

1. **Phase ID vs Task ID in state_engine context**
   - What we know: `update_task(task_id, ...)` receives a `task_id` that is a GSD plan task ID (e.g., `"47-01-wave1"`), not a phase number. But the event envelope `phase_id` field should carry the phase number (e.g., `"47"`).
   - What's unclear: How to extract the phase number from a task_id. Is there a reliable convention? The task format appears to be `{phase}-{plan}-{wave}` or similar.
   - Recommendation: Parse the phase number from `task_id` by taking the first segment before `-`. Alternatively, add `phase_id` to task metadata in `create_task()` so it's available at update time. The latter is more robust but requires a wider change.

2. **event_bus_hook.py import registration timing**
   - What we know: Python module subscriptions must happen before events are emitted. The hook file must be imported somewhere guaranteed to run before the first event fires.
   - What's unclear: Where to import `event_bus_hook.py` in the existing codebase. Options: (a) in `openclaw/__init__.py` — runs on any package import; (b) lazy import in each hook site just before emit; (c) explicit import in the agent's startup sequence.
   - Recommendation: Option (b) — each hook site does `import openclaw.notion_hook` (or equivalent) before calling `emit()`. This is explicit and doesn't pollute `__init__.py`. Guarded by `if NOTION_TOKEN configured` check to avoid loading Notion code when the feature is unconfigured.

3. **NOTION_PARENT_PAGE_ID requirement for DB creation**
   - What we know: Creating a Notion database via API requires a parent page ID. This is not mentioned in the SPEC but is a real API requirement.
   - What's unclear: Whether the user should pre-create the databases and provide IDs, or whether the skill should create them with a configured parent page.
   - Recommendation: Add `notion_parent_page_id` to `config.json`. If null and `auto_create_dbs: true`, bootstrap fails with a clear error: "Set notion_parent_page_id in config.json to the ID of the Notion page where databases should be created." This is a one-time setup step.

4. **Meaningful container rule: runtime tracking**
   - What we know: The meaningful container rule checks `runtime > 10 minutes`. Runtime is `completed_at - spawn_requested_at` in pool.py. Both values are `time.time()` floats available in `_attempt_task()`.
   - What's unclear: Whether the runtime check uses actual wall-clock (pool monitoring time) or container execution time. They differ if container start took a long time.
   - Recommendation: Use `execution_ms` (container_started_at to completed_at) as the meaningful runtime, not spawn_to_complete_ms. This is already calculated and logged in `_attempt_task()`. Pass it in the event envelope as `payload.runtime_seconds`.

5. **Reconcile trigger mechanism**
   - What we know: SPEC says "nightly" reconcile. CONTEXT.md says this is Claude's discretion.
   - What's unclear: How to schedule nightly reconcile without a separate cron process. Options: (a) OpenClaw heartbeat skill; (b) manual invocation only; (c) cron entry.
   - Recommendation: Start with manual invocation (ClawdiaPrime can be instructed to run reconcile) + document how to add a cron entry. The `openclaw-heartbeat` skill in `skills/openclaw-heartbeat/` likely provides a scheduling hook — check it. No blocking dependency either way.

---

## Validation Architecture

Note: `.planning/config.json` has `workflow.nyquist_validation` absent (only `workflow.research: true`). Treating as false — skip mandatory Nyquist section. However, the project has a mature pytest infrastructure and all behavior in this phase is testable.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.0+ with pytest-asyncio |
| Config file | `packages/orchestration/pyproject.toml` (dev extras) |
| Quick run command | `uv run pytest packages/orchestration/tests/test_notion_sync.py -x` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |
| Estimated runtime | ~10-30 seconds (no Docker, mock Notion API) |

### Wave 0 Gaps (test files that must be created before implementation)

- [ ] `packages/orchestration/tests/test_event_bus.py` — covers NOTION-01 (emit/subscribe), fire-and-forget isolation
- [ ] `packages/orchestration/tests/test_notion_sync.py` — covers NOTION-02 (idempotency), NOTION-04 (capture hash), NOTION-05 (meaningful rule), NOTION-06 (field ownership), NOTION-10 (structured result)
- [ ] `packages/orchestration/tests/test_notion_client.py` — covers NOTION-11 (429/5xx retry), NOTION-08 (bootstrap/cache)
- [ ] `packages/orchestration/tests/test_notion_reconcile.py` — covers NOTION-07 (reconcile corrections-only)

All tests use `respx` (already in dev deps) to mock httpx calls to the Notion API. No live Notion token required for unit tests.

---

## Sources

### Primary (HIGH confidence)

- `~/.openclaw/skills/notion/SKILL.md` — Notion API 2025-09-03 reference, property formats, endpoint patterns, data_source_id vs database_id distinction
- `~/.openclaw/packages/orchestration/src/openclaw/state_engine.py` — hook site analysis, memory trigger pattern, project_id resolution
- `~/.openclaw/skills/spawn/pool.py` — container lifecycle hook sites, runtime tracking variables
- `~/.openclaw/packages/orchestration/src/openclaw/cli/project.py` — project_registered and project_removed hook sites
- `~/.openclaw/packages/orchestration/src/openclaw/config.py` — constants pattern, project root resolution
- `~/.openclaw/.planning/phases/50-notion-kanban-sync/SPEC.md` — authoritative schema, event mappings, dedupe model, ownership rules
- `~/.openclaw/.planning/phases/50-notion-kanban-sync/50-CONTEXT.md` — locked decisions, user constraints

### Secondary (MEDIUM confidence)

- `~/.openclaw/skills/review/review.py` + `skill.json` — existing Python skill structure pattern
- `~/.openclaw/skills/spawn/spawn.py` — `_retrieve_memories_sync` as fire-and-forget threading pattern reference
- `~/.openclaw/packages/orchestration/tests/conftest.py` — test infrastructure, sys.path pattern for skills

---

## Metadata

**Confidence breakdown:**
- Event bus architecture: HIGH — codebase verified, existing patterns match proposed approach
- Notion API patterns: HIGH — project's own SKILL.md is the reference; API version 2025-09-03 explicitly documented
- Hook sites: HIGH — source code read directly, line-level analysis performed
- Retry/backoff: HIGH — pattern matches existing state_engine retry loops in codebase
- Open questions: MEDIUM — 5 gaps identified that need resolution during planning/execution

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (Notion API stable; codebase changes invalidate hook site line numbers)
