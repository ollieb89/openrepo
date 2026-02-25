# Phase 40: Memory Health Monitor - Research

**Researched:** 2026-02-24
**Domain:** Memory health scanning, FastAPI endpoint extension, Next.js dashboard UI (tab, badges, side panel)
**Confidence:** HIGH

## Summary

Phase 40 adds a memory health monitoring layer on top of the existing memU REST service and occc dashboard. The core work splits cleanly into three concerns: (1) a health scan engine in the memory service that detects stale and conflicting memories using `created_at`/`last_reinforced_at` from the `extra` JSONB column and pgvector cosine distance queries; (2) a `PUT /memories/:id` endpoint that calls the already-implemented `update_memory_item()` on `MemoryService`; and (3) dashboard changes — health badges on the existing `MemoryRow`, a Health tab in `MemoryPanel`, and a conflict resolution side panel.

The staleness signal must combine age (`created_at`) AND retrieval frequency. No `last_retrieved_at` field exists in the current schema — the closest proxy is `last_reinforced_at` stored in `extra` (set when a memory is retrieved and reinforced). The implementation should treat `last_reinforced_at` as the retrieval-frequency proxy, configurable via threshold settings. This avoids any schema migration and aligns with how the existing `salience_score()` algorithm uses the same field.

For conflict detection, the system already has `vector_search_items()` with pgvector cosine distance in `PostgresMemoryItemRepo`. A cross-product similarity scan is needed (compare each item against all others within the same user scope), filtered to a configurable similarity window (e.g., 0.75-0.99 to exclude near-duplicates and unrelated items). The scan must run in the memory service layer, not in orchestration, since the service has direct DB/vector access.

**Primary recommendation:** Implement the health scan as a new `POST /memories/health-scan` endpoint in the memory service, storing flag results in a dedicated health flags table or JSON sidecar (favoring an in-process `health_flags` dict keyed by memory_id to avoid DB migration), with the PUT endpoint calling the existing `update_memory_item()` workflow.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Manual "Run Health Scan" button on /memory page AND a scheduled background scan at a fixed interval (e.g. hourly)
- Results appear in two places: inline badges on the main memory list AND a dedicated Health tab for focused triage
- Each flagged memory gets a recommended action (archive, merge, review, etc.) — operator can follow or ignore
- Health tab shows a summary bar at the top with colored count chips (e.g. "3 stale - 2 conflicts")
- Colored pill/tag badges next to memory titles — orange for stale, red for conflict
- Flagged memories stay in their normal list position; a filter toggle shows only flagged items
- Health tab in navigation shows a count badge (red/orange number) when unresolved flags exist
- Side panel with side-by-side layout showing both conflicting memories with differences highlighted
- Three actions: edit, delete, dismiss flag
- After resolving, auto-advance to the next flagged memory for efficient triage
- Edit is inline in the panel — content becomes editable, save button replaces action buttons
- Dismissed flags are hidden until the next scan; if the conflict still exists, it re-flags
- A memory is stale if it's old AND hasn't been retrieved recently (age + retrieval frequency)
- Stale memory actions: archive (soft-delete, recoverable) or dismiss (keep, re-scan later)
- Settings panel (gear icon on health tab) with all config in one place: scan interval, age threshold, retrieval window, similarity threshold
- Operators can adjust all thresholds from the dashboard

### Claude's Discretion

- Default threshold values (age, retrieval window, similarity score)
- Exact diff highlighting approach for conflict panel
- Animation/transition for auto-advance between flags
- Summary bar visual design and color palette

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUAL-01 | Batch health scan detects stale memories older than configurable threshold (default 30 days) that haven't been retrieved recently | `created_at` is a DB column; `last_reinforced_at` in `extra` JSONB is the retrieval proxy. Scan queries `memory_items` for age + absence/staleness of `last_reinforced_at`. |
| QUAL-02 | Batch health scan detects conflicting memories via pgvector cosine similarity range query (same topic, different verdict) | `vector_search_items()` in `PostgresMemoryItemRepo` uses `embedding.cosine_distance(query_vec)` via pgvector. For conflict detection: iterate items, cosine-search neighbors in similarity range 0.75–0.99, flag pairs. |
| QUAL-03 | Health scan returns scored list of flagged memories with flag type, similarity score, and recommendation | New endpoint `POST /memories/health-scan` in `docker/memory/memory_service/routers/`. Response shape: `{flags: [{memory_id, flag_type, score, recommendation, conflict_with?}], scanned_at, totals}`. |
| QUAL-04 | New `PUT /memories/:id` endpoint in memory service allows updating memory content | `MemoryService.update_memory_item()` already exists in `memu/app/crud.py`. Needs a new FastAPI route in `memories.py` and a corresponding `PUT /api/memory/[id]` Next.js proxy route. |
| QUAL-05 | Dashboard /memory page displays health badges on flagged memories with staleness and conflict indicators | `MemoryRow.tsx` renders badge pills — add health flag badge next to existing type/category badges. `MemoryPanel.tsx` needs health state (flags map, filter toggle, Health tab). |
| QUAL-06 | Dashboard side panel shows conflict details (both memories, similarity score) with actions: edit, delete, dismiss flag | New `ConflictPanel.tsx` component — slide-in side panel with side-by-side content, diff highlight, three action buttons, auto-advance on resolve. |
</phase_requirements>

---

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current (via requirements.txt) | REST endpoint for health scan + PUT | Already used for all memory service routes |
| SQLModel / SQLAlchemy | current | DB queries for staleness scan | Already used in all repos |
| pgvector | current | Cosine similarity for conflict detection | Already used in `vector_search_items()` |
| React / Next.js 15+ | current (occc) | Dashboard UI — tabs, badges, side panel | Existing dashboard stack |
| SWR | current | Data fetching in dashboard | `useMemory` hook already uses SWR |
| TypeScript | current | Dashboard typing | All components are typed |

### Supporting (Claude's discretion)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `difflib` (Python stdlib) | stdlib | Text diff for conflict detection highlights | No install needed; use `difflib.SequenceMatcher` for word-level diff |
| CSS transitions | built-in | Auto-advance animation | `transition-opacity` / `transition-transform` already used in `MemoryRow` |
| `pendulum` | current | Date arithmetic for staleness threshold | Already used in memU models |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-process flags dict | Separate DB table for flags | DB table survives restarts but requires migration; in-process dict is simpler, flags are ephemeral by design (re-scan regenerates them) |
| `difflib` | Third-party diff library | `difflib` is stdlib and sufficient for word-level diff; no new dependency |
| Auto-advance via React state | Full page navigation | State-based auto-advance keeps panel open, updates displayed item — no route change needed |

**Installation:** No new packages needed — all libraries already present.

---

## Architecture Patterns

### Memory Service Layer

#### New Endpoint: `POST /memories/health-scan`

Located in `docker/memory/memory_service/routers/memories.py` (extend the existing router):

```python
# Source: existing pattern from memories.py GET and DELETE
@router.post("/memories/health-scan")
async def run_health_scan(request: Request, body: HealthScanRequest):
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(status_code=503, content={"detail": "Memory service not initialized"})
    try:
        result = await memu.run_health_scan(
            user_id=body.user_id,
            age_threshold_days=body.age_threshold_days,
            retrieval_window_days=body.retrieval_window_days,
            similarity_min=body.similarity_min,
            similarity_max=body.similarity_max,
        )
        return result
    except Exception as e:
        logger.error(f"Health scan failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
```

#### New Endpoint: `PUT /memories/:id`

```python
# Source: existing pattern from DELETE handler in memories.py
@router.put("/memories/{memory_id}")
async def update_memory(memory_id: str, request: Request, body: MemoryUpdateRequest):
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(status_code=503, content={"detail": "Memory service not initialized"})
    try:
        result = await memu.update_memory_item(
            memory_id=memory_id,
            memory_content=body.content,
        )
        return result
    except ValueError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})
    except Exception as e:
        logger.error(f"Update memory {memory_id} failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
```

#### Health Scan Engine

The scan is a new method `run_health_scan()` on `MemoryService` (as a new mixin or direct method):

**Staleness detection** — queries `memory_items` for items where:
- `created_at < now - age_threshold_days` (uses `pendulum.now("UTC").subtract(days=age_threshold_days)`)
- AND `extra->>'last_reinforced_at'` is NULL or older than `retrieval_window_days`

Since `last_reinforced_at` lives in the JSONB `extra` column, the staleness query filters in Python after fetching with `list_items(where={"user_id": user_id})` — acceptable given typical memory corpus size (<10k items per project). Recommended default: age=30 days, retrieval_window=14 days.

**Conflict detection** — for each item with an embedding, calls `vector_search_items()` filtered to same user scope. Collects pairs where similarity falls in `[similarity_min, similarity_max]` (recommended defaults: 0.75-0.97). To avoid O(n²) embedding load, fetches all items once, then uses the existing `cosine_topk()` from `memu/database/inmemory/vector.py` (which is pure numpy and available without pgvector). Each conflict pair is deduplicated (pair A→B and B→A collapse to one entry).

#### Flags Model (in-process, ephemeral)

Flags live in `app.state.health_flags` (a dict) rather than the database. This matches the dismissed-until-next-scan requirement: dismissing removes the flag from the dict; re-scanning regenerates it only if the condition still holds.

```python
# docker/memory/memory_service/models.py — new models
class HealthFlag(BaseModel):
    memory_id: str
    flag_type: Literal["stale", "conflict"]
    score: float  # age_score for stale (days/threshold), similarity for conflict
    recommendation: Literal["archive", "review", "merge"]
    conflict_with: Optional[str] = None  # memory_id of conflicting item

class HealthScanRequest(BaseModel):
    user_id: Optional[str] = None
    age_threshold_days: int = 30
    retrieval_window_days: int = 14
    similarity_min: float = 0.75
    similarity_max: float = 0.97

class HealthScanResult(BaseModel):
    flags: list[HealthFlag]
    scanned_at: str  # ISO timestamp
    totals: dict  # {"stale": N, "conflict": N, "total": N}

class MemoryUpdateRequest(BaseModel):
    content: str
```

### Next.js Dashboard Layer

#### API Proxy Routes

- `POST /api/memory/health-scan` → proxies to memU `POST /memories/health-scan` (same pattern as existing `/api/memory/route.ts`)
- `PUT /api/memory/[id]` → add `PUT` handler alongside existing `DELETE` in `/api/memory/[id]/route.ts`

#### Health State in MemoryPanel

`MemoryPanel.tsx` already manages all list state. Add:

```typescript
// Health state
const [healthFlags, setHealthFlags] = useState<Map<string, HealthFlag>>(new Map());
const [showOnlyFlagged, setShowOnlyFlagged] = useState(false);
const [activeTab, setActiveTab] = useState<'list' | 'health'>('list');
const [scanRunning, setScanRunning] = useState(false);
const [conflictPanel, setConflictPanel] = useState<ConflictPanelState | null>(null);

// Health scan trigger
async function runHealthScan() {
  setScanRunning(true);
  const res = await fetch('/api/memory/health-scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: projectId, ...healthSettings }),
  });
  const data = await res.json();
  const flagMap = new Map(data.flags.map((f: HealthFlag) => [f.memory_id, f]));
  setHealthFlags(flagMap);
  setScanRunning(false);
}
```

The scheduled background scan fires `runHealthScan()` on a `useEffect` interval — `setInterval` with cleanup on unmount, configurable from `healthSettings.scan_interval_ms`.

#### MemoryRow Badge Addition

```typescript
// In MemoryRow.tsx — add after existing badges
{healthFlag && (
  <span
    className={`${pillClass} cursor-pointer ${
      healthFlag.flag_type === 'stale'
        ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300'
        : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
    }`}
    onClick={(e) => { e.stopPropagation(); onBadgeClick(healthFlag); }}
  >
    {healthFlag.flag_type}
  </span>
)}
```

#### Health Tab + Summary Bar

```
MemoryPanel (tabs: list | health)
├── Tab bar with count badge on "Health" tab
├── List tab: existing MemoryTable + filter toggle "show only flagged"
└── Health tab:
    ├── SummaryBar: "3 stale  2 conflicts" chips + "Run Scan" button + gear icon
    ├── SettingsPanel (gear, slides open): threshold inputs
    └── FlagList: sorted flagged items with action buttons
        └── ConflictPanel (slide-in side panel): side-by-side diff + actions
```

#### ConflictPanel Component

```typescript
// New file: workspace/occc/src/components/memory/ConflictPanel.tsx
interface ConflictPanelProps {
  flaggedItem: MemoryItem;
  conflictItem: MemoryItem;
  similarityScore: number;
  onEdit: (id: string, content: string) => void;
  onDelete: (id: string) => void;
  onDismiss: (flagId: string) => void;
  onClose: () => void;
}
```

Diff highlighting: split content into words, use `difflib`-style comparison (or client-side word diff). For the React side, implement a lightweight word-diff function — two passes: common prefix/suffix, then mark additions/deletions with `<mark>` spans. No library needed.

Auto-advance: after resolving a flag (edit/delete/dismiss), identify the next unresolved flag in the list and set it as the active conflict. Uses an ordered array of flag IDs, finds `currentIndex + 1`.

### Anti-Patterns to Avoid

- **Calling health scan on every memory write:** Out of scope (confirmed in REQUIREMENTS.md). Scan is batch-only.
- **Storing flags permanently in the DB:** Flags are ephemeral — they regenerate on next scan. A DB table would require migration and adds write overhead for no benefit.
- **O(n²) embedding fetches:** Fetch all items once, compute cosine in Python (numpy) using the existing `cosine_topk()` infrastructure. Do not call `vector_search_items()` N times.
- **Exposing health settings in multiple locations:** All thresholds live in one consolidated settings panel (gear icon on health tab). Do not scatter them across page settings.
- **`archive` as hard delete:** Archive = soft delete. Store archived status in `extra['archived_at']` via the new PUT endpoint. The existing DELETE can still be used for hard delete.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cosine similarity | Custom similarity algorithm | `cosine_topk()` from `memu/database/inmemory/vector.py` + pgvector | Already battle-tested with numpy vectorization |
| Memory update persistence | Custom DB write | `MemoryService.update_memory_item()` (in `crud.py`) | Handles embedding re-generation, category re-linking, category summary patch |
| Word-level diff highlighting | Full diff library | 20-line word-diff function using Python `difflib.SequenceMatcher` for server-side or simple JS split for client | No new dependency; sufficient for memory content comparison |
| Scheduled scan timer | cron job, external scheduler | `setInterval` in React `useEffect` + `clearInterval` cleanup | Scan is UI-triggered; browser-side interval is correct for dashboard feature |

**Key insight:** The memU `MemoryService` already has complete update/delete/list pipelines. Phase 40 only needs to add a new scan workflow and one REST endpoint — it should not duplicate any storage logic.

---

## Common Pitfalls

### Pitfall 1: `update_memory_item()` requires at least one non-None field

**What goes wrong:** `PUT /memories/:id` with empty body or missing `content` triggers `ValueError: At least one of memory_type, memory_content, or memory_categories is required`.
**Why it happens:** Guard in `CRUDMixin.update_memory_item()` (line 324 of `crud.py`).
**How to avoid:** Pydantic model for `MemoryUpdateRequest` should require `content` as non-optional. Validate before calling the service method.
**Warning signs:** 422/500 from PUT endpoint during testing.

### Pitfall 2: Staleness check on items without `last_reinforced_at`

**What goes wrong:** Items created without reinforcement (standard `create_item()` without `reinforce=True`) have no `last_reinforced_at` in `extra`. Treating absence as "never retrieved" may flag too aggressively.
**Why it happens:** `last_reinforced_at` is only set by `create_item_reinforce()` path. Regular memorize calls use `create_item()` and leave `extra` empty.
**How to avoid:** When `last_reinforced_at` is absent, use `created_at` as the retrieval proxy — items with no reinforcement data are considered "fresh" if `created_at` is within the retrieval window.
**Warning signs:** Massive false-positive stale flags on first scan.

### Pitfall 3: Conflict pairs counted twice

**What goes wrong:** Item A flagged as conflicting with B, AND item B flagged as conflicting with A — doubles the conflict count in the summary bar.
**Why it happens:** Symmetric cosine scan naturally produces both directions.
**How to avoid:** Deduplicate using a canonical pair key: `tuple(sorted([id_a, id_b]))`. Track seen pairs in a set during scan.
**Warning signs:** `totals.conflict` equals twice the expected value.

### Pitfall 4: `update_memory_item()` re-embeds on every PUT

**What goes wrong:** Every PUT to `/memories/:id` triggers a new embedding generation (via `_patch_update_memory_item` → `embed_payload`). If operator saves without changing content, wasted LLM call.
**Why it happens:** The update workflow re-embeds when `memory_payload["content"]` is truthy.
**How to avoid:** Dashboard should only send PUT if content actually changed (compare with original before submitting). In the service, `update_memory_item()` already skips embedding if `memory_content=None`, so pass `None` for content if only dismissing a flag (don't mix flag state changes with content updates).
**Warning signs:** Slow PUT responses, unexpected LLM costs.

### Pitfall 5: Background scan timer fires after component unmount

**What goes wrong:** `setInterval` continues after navigating away from /memory page — causes state updates on unmounted component (React warning).
**Why it happens:** Interval not cleaned up in `useEffect` return function.
**How to avoid:** Always return `() => clearInterval(intervalId)` from the `useEffect`. Disable interval when `projectId` is null.
**Warning signs:** React "Can't perform state update on unmounted component" warning.

### Pitfall 6: Health scan scope mismatch

**What goes wrong:** Scan returns flags for all projects when operator expects only the active project.
**Why it happens:** `user_id` not sent in scan request body.
**How to avoid:** `MemoryPanel` always includes `user_id: projectId` in the scan request. Service validates `user_id` presence in `HealthScanRequest` (make it required, not optional — or default to error if missing).
**Warning signs:** Cross-project flags appearing in scan results.

---

## Code Examples

### Health Scan Staleness Query (Python)

```python
# docker/memory/memory_service — new health scan logic
import pendulum
from datetime import datetime, timezone

def _check_staleness(
    item,  # MemoryItem
    age_threshold_days: int,
    retrieval_window_days: int,
    now: datetime,
) -> float | None:
    """Returns age_score (>1.0 means stale) or None if not stale."""
    item_age_days = (now - item.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 86400
    if item_age_days < age_threshold_days:
        return None  # Not old enough

    extra = item.extra or {}
    last_reinforced_str = extra.get("last_reinforced_at")

    if last_reinforced_str:
        try:
            last_reinforced = pendulum.parse(last_reinforced_str)
            days_since_retrieval = (now - last_reinforced).total_seconds() / 86400
            if days_since_retrieval < retrieval_window_days:
                return None  # Retrieved recently enough
        except (ValueError, TypeError):
            pass  # Treat as not retrieved
    # else: no last_reinforced_at — use created_at as proxy
    # If created_at is within retrieval_window, not stale
    if item_age_days < retrieval_window_days:
        return None

    age_score = item_age_days / age_threshold_days
    return age_score
```

### Conflict Detection (Python)

```python
# Conflict scan — O(n) per item via cosine_topk
from memu.database.inmemory.vector import cosine_topk

def _find_conflicts(
    items: list,  # list of MemoryItem with embeddings
    similarity_min: float = 0.75,
    similarity_max: float = 0.97,
) -> list[tuple[str, str, float]]:
    """Returns list of (id_a, id_b, similarity) pairs."""
    corpus = [(item.id, item.embedding) for item in items if item.embedding is not None]
    seen_pairs: set[tuple[str, str]] = set()
    conflicts: list[tuple[str, str, float]] = []

    for item in items:
        if item.embedding is None:
            continue
        neighbors = cosine_topk(item.embedding, corpus, k=10)
        for neighbor_id, score in neighbors:
            if neighbor_id == item.id:
                continue
            if not (similarity_min <= score <= similarity_max):
                continue
            pair_key = tuple(sorted([item.id, neighbor_id]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            conflicts.append((item.id, neighbor_id, score))

    return conflicts
```

### PUT /memories/:id FastAPI Route

```python
# docker/memory/memory_service/routers/memories.py (addition)
from ..models import MemoryUpdateRequest

@router.put("/memories/{memory_id}")
async def update_memory(memory_id: str, request: Request, body: MemoryUpdateRequest):
    """PUT /memories/{memory_id} — updates content of an existing memory item."""
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(status_code=503, content={"detail": "Memory service not initialized"})
    try:
        result = await memu.update_memory_item(
            memory_id=memory_id,
            memory_content=body.content,
        )
        return result
    except ValueError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})
    except Exception as e:
        logger.error(f"Update memory {memory_id} failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
```

### Next.js PUT Proxy Route

```typescript
// workspace/occc/src/app/api/memory/[id]/route.ts (add PUT alongside DELETE)
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const memuUrl = await getMemuUrl();
    const body = await request.json();
    const res = await fetch(`${memuUrl}/memories/${params.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      return Response.json({ error: 'Update failed' }, { status: res.status });
    }
    const data = await res.json();
    return Response.json(data);
  } catch (error) {
    console.error('Error updating memory:', error);
    return Response.json({ error: 'Failed to update memory item' }, { status: 500 });
  }
}
```

### Health Tab Count Badge (Sidebar)

The Sidebar component currently renders static nav items. To show a dynamic health count badge, the badge must live in `MemoryPanel.tsx` near the Health tab button (not in Sidebar) — the Sidebar has no data access. The Health tab count badge is internal to MemoryPanel's tab controls.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cosine similarity via in-memory numpy | pgvector native `cosine_distance()` for top-k | Added in v1.3 (Phase 30ish) | Conflict scan can use native pgvector ORDER BY for performance, or fall back to `cosine_topk()` numpy for simplicity |
| `list_items()` returns all items | `list_items(where={"user_id": ...})` for project-scoped queries | v1.1 | Always pass `user_id` scope to `list_items()` in health scan |
| No memory update support | `update_memory_item()` in `CRUDMixin` exists | v1.3 | PUT endpoint is a thin wrapper — all logic already implemented |

---

## Open Questions

1. **`update_memory_item()` requires `user` parameter — what to pass for PUT?**
   - What we know: `update_memory_item()` signature takes `user: dict[str, Any] | None = None`. If `user=None`, `user_scope = None`. Looking at `_patch_update_memory_item`, if `user` is None, `user_data = dict(None or {})` = `{}`. Categories are looked up from `ctx.category_name_to_id` which was initialized without user scope.
   - What's unclear: Whether a `user=None` call correctly restricts the update to only items in any scope, or can accidentally update items across users.
   - Recommendation: Pass `user={"user_id": memory_item.user_id}` by fetching the item first (using `get_item()`) to extract its `user_id`, then passing it back. Alternatively, accept `user_id` in `MemoryUpdateRequest` and trust the caller. Use the simpler approach first: accept `user_id` in the request body, validate it matches the item's user_id before calling update.

2. **Archive as soft-delete: where to store archived status?**
   - What we know: There is no `archived` column. `extra` is a JSONB column that supports arbitrary keys.
   - What's unclear: Whether future phases need to filter out archived items from retrieval (e.g., pre-spawn memory fetch should skip archived items).
   - Recommendation: Store `extra['archived_at'] = ISO_TIMESTAMP` via PUT. For Phase 40, archive action = PUT with `archived_at` field. Actual filtering is a future phase concern — document it but don't implement now.

3. **Scheduled scan: React interval vs. server-side cron?**
   - What we know: CONTEXT.md says "scheduled background scan at a fixed interval." The dashboard already uses polling intervals (containers: 5s, tasks: 3s) via `useEffect` + `setInterval`.
   - What's unclear: Whether "scheduled" means server-side (fires even when dashboard is closed) or client-side (fires while dashboard is open).
   - Recommendation: Implement as client-side interval in `MemoryPanel.tsx` for consistency with existing dashboard patterns. Server-side cron is a future enhancement. Scan interval default: 3600000ms (1 hour).

---

## Validation Architecture

*(nyquist_validation is not in `.planning/config.json` — config only has `workflow.research: true`. Skipping Validation Architecture section.)*

The existing test infrastructure uses `pytest` with `asyncio_mode = auto` (tests/pytest.ini). Phase 40 tests should follow existing patterns in `tests/test_memory_client.py` and `tests/test_spawn_memory.py`:

- Health scan logic (staleness + conflict detection) — unit tests with mocked `MemoryItem` objects
- PUT endpoint — integration test using `httpx.AsyncClient` against a test FastAPI app
- Dashboard changes — manual verification (no Playwright tests in scope for this phase per project config preference)

Run command: `uv run pytest tests/ -v -k "health"` for new tests.

---

## Sources

### Primary (HIGH confidence)

- `/home/ollie/.openclaw/docker/memory/memory_service/routers/memories.py` — existing GET/DELETE patterns
- `/home/ollie/.openclaw/docker/memory/memory_service/models.py` — existing Pydantic models
- `/home/ollie/.openclaw/workspace/memory/src/memu/app/crud.py` — `update_memory_item()` signature and behavior
- `/home/ollie/.openclaw/workspace/memory/src/memu/database/postgres/repositories/memory_item_repo.py` — `vector_search_items()`, `update_item()`, `list_items()` — all verified by reading source
- `/home/ollie/.openclaw/workspace/memory/src/memu/database/inmemory/vector.py` — `cosine_topk()` available for conflict scan
- `/home/ollie/.openclaw/workspace/memory/src/memu/database/models.py` — `MemoryItem.extra` JSONB field confirmed
- `/home/ollie/.openclaw/workspace/occc/src/components/memory/MemoryPanel.tsx` — existing component state patterns
- `/home/ollie/.openclaw/workspace/occc/src/components/memory/MemoryRow.tsx` — badge rendering pattern
- `/home/ollie/.openclaw/workspace/occc/src/app/api/memory/[id]/route.ts` — existing DELETE proxy pattern
- `.planning/REQUIREMENTS.md` — QUAL-01..06 requirements
- `.planning/phases/40-memory-health-monitor/40-CONTEXT.md` — locked user decisions

### Secondary (MEDIUM confidence)

- `memu/database/postgres/models.py` (MemoryItemModel) — `extra: dict[str, Any] = Field(default={}, sa_column=Column(JSONB, nullable=True))` — confirmed JSONB stores arbitrary keys including `last_reinforced_at`
- `vector_search_items()` in postgres repo — confirmed pgvector `cosine_distance` available; `cosine_topk()` numpy fallback also available

### Tertiary (LOW confidence)

- Default threshold values (30 days age, 14 days retrieval window, 0.75-0.97 similarity) — recommended based on domain knowledge of memory staleness patterns; empirical tuning needed after deployment

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified by direct source inspection
- Architecture: HIGH — all integration points verified (update_memory_item exists, vector search exists, proxy pattern established)
- Pitfalls: HIGH — all pitfalls derived from direct code reading (crud.py guards, model constraints)
- Threshold defaults: LOW — no production data to validate; need monitoring after deployment

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable stack — 30 days)
