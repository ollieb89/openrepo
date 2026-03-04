# Phase 36: Dashboard Memory Panel - Research

**Researched:** 2026-02-24
**Domain:** Next.js dashboard page — memory browsing, search, delete UI integrated with memU REST API
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Memory item presentation
- Table rows layout with sortable columns: Type, Category, Agent, Created
- Click a row to expand inline (accordion-style) showing full content and extra metadata
- Expanded content capped at ~300 characters with a "show more" toggle to reveal the rest
- Content in expanded view shows the memory text plus any additional metadata not in columns

#### Browse & navigation
- Filter bar above the table with dropdown selectors for Category, Agent source, and Type
- Default sort: newest first (most recently created at top)
- Compact stats bar above filters showing total count and per-agent breakdown (e.g., "42 items | l2_pm: 12 · l3_code: 22 · l3_test: 8")
- Classic pagination with page numbers at bottom, ~25 items per page
- Auto-reload silently when project changes in the project selector — consistent with existing dashboard pages

#### Search experience
- Prominent full-width search bar at the top of the page, above the stats bar and filters
- Search triggered on Enter key press (not debounced as-you-type — semantic search is not instant)
- Search results replace the table contents with a "Showing results for 'query'" banner and a clear button to return to browsing
- Filters still apply during search (can narrow search results by category/agent/type)

#### Delete workflow
- Delete button visible only in the expanded row view (not on every row)
- Confirmation dialog on click ("Are you sure?" popup)
- After successful deletion: row animates out, brief success toast, stats bar updates count
- Bulk delete supported: checkboxes on each row, "Delete selected" button appears when items are checked
- Bulk delete also uses confirmation dialog before executing

### Claude's Discretion
- Empty search results state design (friendly messaging with suggestions)
- Loading states and skeleton design
- Exact spacing, typography, color coding for agent/category badges
- Sort direction toggle UX
- Error state handling (API failures, timeout)
- Filter dropdown population (dynamic from available data vs static list)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSH-11 | /memory page in occc displays project-scoped memory categories and items | `GET /memories?user_id=<project_id>` returns scoped items; Next.js route at `src/app/memory/page.tsx`; SWR pattern from useTasks.ts applies |
| DSH-12 | Memory panel supports semantic search (vector-based) via retrieve endpoint | `POST /retrieve` with `queries` + `where.user_id` payload; search mode replaces browse table; enter-key triggered |
| DSH-13 | Memory panel supports delete action for individual memory items | `DELETE /memories/{memory_id}` endpoint exists and tested; confirmation dialog + optimistic row removal + toast |
| DSH-14 | Memory panel displays memory item metadata (type, category, created_at, agent source) | `GET /memories` returns items with metadata fields; table columns map 1:1 to these fields |
</phase_requirements>

## Summary

Phase 36 builds the `/memory` page in the occc Next.js 14 dashboard. The page lets an operator browse all project-scoped memory items stored in memU, run semantic searches against them via vector retrieval, inspect individual items with full metadata, and delete items individually or in bulk.

The backend API already exists and is complete: `GET /memories?user_id=<project_id>` returns all items scoped to a project, `POST /retrieve` performs vector-based semantic search, and `DELETE /memories/{memory_id}` removes a single item. The memory service runs at `http://localhost:18791` (configured in `openclaw.json` under `memory.memu_api_url`). The dashboard needs only a proxy API route (to avoid CORS and expose the memU URL as an implementation detail) and the React UI layer.

The occc dashboard has well-established patterns for this type of page. SWR with `?project=` query param handles project-scoped data fetching. Tailwind CSS + existing component primitives (Card, StatusBadge, activity-log patterns) provide the styling primitives. `react-toastify` is already installed (`^10.0.5`) and available for success toasts. The project has no existing dialog/modal component, so a confirmation dialog needs to be built inline (a small controlled `<dialog>` element or a simple div overlay — no external modal library is warranted).

**Primary recommendation:** Follow the exact pattern of the tasks page — proxy API route → SWR hook → page component → table sub-components. Add a `/api/memory` route that proxies to memU, a `useMemory` SWR hook, and a `MemoryTable` component. Keep the confirmation dialog as a minimal inline component.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 14.2.5 | Framework; App Router; API routes as proxy | Already the dashboard framework |
| React | ^18 | UI rendering, state management | Already in use |
| SWR | ^2.4.0 | Data fetching with cache-key-based project scoping | All existing hooks use it |
| Tailwind CSS | ^3.4.0 | Utility-first styling, dark mode | Already the styling system |
| react-toastify | ^10.0.5 | Toast notifications for delete success/error | Already installed, just not yet wired up |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| TypeScript | ^5 | Types for memory items, API responses | All source files are `.ts`/`.tsx` |
| Zod | ^3.23.8 | API response validation | Already in package.json; use for API route input parsing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom inline dialog | headlessui Dialog or radix-ui | External library not warranted for a single confirmation dialog; native `<dialog>` element or div overlay is lighter |
| SWR for search | `useState` + `fetch` on submit | Search results are one-shot (enter-key triggered), not polling — `useState` + manual `fetch` is simpler than SWR for this case |
| Dynamic filter population | Static hardcoded lists | Dynamic is better UX (shows only values that exist); computed from `GET /memories` response |

**Installation:**
```bash
# No new packages needed — all dependencies already present
# react-toastify ^10.0.5 already in package.json
```

## Architecture Patterns

### Recommended Project Structure
```
workspace/occc/src/
├── app/
│   ├── memory/
│   │   └── page.tsx                # /memory page — 'use client', delegates to MemoryPanel
│   └── api/
│       └── memory/
│           ├── route.ts             # GET /api/memory?project= (list + search proxy)
│           └── [id]/
│               └── route.ts         # DELETE /api/memory/[id] (delete proxy)
├── components/
│   └── memory/
│       ├── MemoryPanel.tsx          # Top-level page layout (search, stats, filters, table)
│       ├── MemoryTable.tsx          # Table with sortable columns and accordion rows
│       ├── MemoryRow.tsx            # Individual row, expanded accordion view
│       ├── MemoryFilters.tsx        # Category/Agent/Type dropdown bar
│       ├── MemoryStatBar.tsx        # "42 items | l2_pm: 12 · l3_code: 22" stats bar
│       └── ConfirmDialog.tsx        # Reusable "Are you sure?" confirmation dialog
└── lib/
    ├── hooks/
    │   └── useMemory.ts             # SWR hook: GET /api/memory?project=&search=
    └── types/
        └── memory.ts                # MemoryItem, MemoryListResponse TypeScript types
```

### Pattern 1: SWR with project-scoped cache key (established pattern)

**What:** SWR key changes when `projectId` changes, triggering a fresh fetch. Disabled (null key) when no project is selected.

**When to use:** All browse/list data that is project-scoped.

**Example:**
```typescript
// Source: existing pattern in workspace/occc/src/lib/hooks/useTasks.ts
export function useMemory(projectId: string | null, searchQuery: string | null) {
  const params = new URLSearchParams();
  if (projectId) params.set('project', projectId);
  if (searchQuery) params.set('search', searchQuery);

  const { data, error, isLoading, mutate } = useSWR<MemoryListResponse>(
    projectId ? `/api/memory?${params.toString()}` : null,
    fetcher,
    { revalidateOnFocus: false }  // no auto-polling — memory doesn't change in real-time
  );

  return { items: data?.items ?? [], total: data?.total ?? 0, isLoading, error, mutate };
}
```

### Pattern 2: Next.js API route as proxy to memU

**What:** The dashboard never calls memU directly from the browser. All memU calls go through a Next.js API route running server-side. This avoids CORS issues and keeps the memU URL an implementation detail.

**When to use:** All memU interactions from the dashboard.

**Example:**
```typescript
// Source: pattern from workspace/occc/src/app/api/tasks/route.ts
// workspace/occc/src/app/api/memory/route.ts

import { NextRequest } from 'next/server';
import { readOpenClawConfig, getActiveProjectId } from '@/lib/openclaw';

async function getMemuUrl(): Promise<string> {
  const config = await readOpenClawConfig();
  const memory = config.memory as Record<string, string> | undefined;
  return memory?.memu_api_url ?? 'http://localhost:18791';
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project') || await getActiveProjectId();
  const search = searchParams.get('search');

  const memuUrl = await getMemuUrl();

  if (search) {
    // Semantic search — POST /retrieve
    const res = await fetch(`${memuUrl}/retrieve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        queries: [{ role: 'user', content: search }],
        where: { user_id: projectId },
      }),
    });
    const data = await res.json();
    const items = Array.isArray(data) ? data : (data.items ?? []);
    return Response.json({ items, total: items.length, projectId, mode: 'search' });
  } else {
    // Browse — GET /memories?user_id=
    const res = await fetch(`${memuUrl}/memories?user_id=${encodeURIComponent(projectId)}`);
    const data = await res.json();
    const items = Array.isArray(data) ? data : (data.items ?? []);
    return Response.json({ items, total: items.length, projectId, mode: 'browse' });
  }
}
```

### Pattern 3: Accordion row (expand inline without routing)

**What:** Table rows expand in-place on click. No navigation, no separate page. The expanded row shows full content, metadata, and the delete button.

**When to use:** The locked decision mandates this.

**Example:**
```typescript
// Simple controlled expand with useState:
const [expandedId, setExpandedId] = useState<string | null>(null);

function MemoryRow({ item }: { item: MemoryItem }) {
  const isExpanded = expandedId === item.id;
  return (
    <>
      <tr onClick={() => setExpandedId(isExpanded ? null : item.id)} className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50">
        {/* ... columns ... */}
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={5} className="px-4 py-3 bg-gray-50 dark:bg-gray-800">
            {/* full content, delete button */}
          </td>
        </tr>
      )}
    </>
  );
}
```

### Pattern 4: Confirmation dialog (no external library)

**What:** Simple controlled overlay div that acts as a modal. No external dialog library — a single `ConfirmDialog.tsx` component with `isOpen`, `onConfirm`, `onCancel` props.

**Example:**
```typescript
// Minimal — no portal, just fixed overlay
export function ConfirmDialog({ isOpen, title, message, onConfirm, onCancel }: ConfirmDialogProps) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{message}</p>
        <div className="mt-4 flex justify-end gap-3">
          <button onClick={onCancel} className="...">Cancel</button>
          <button onClick={onConfirm} className="... bg-red-600 text-white">Delete</button>
        </div>
      </div>
    </div>
  );
}
```

### Pattern 5: Toast for delete success/error

**What:** `react-toastify` is already in `package.json` but not yet used anywhere in the codebase. The `ToastContainer` needs to be mounted once (in layout or within the page), then `toast.success()` / `toast.error()` called after delete operations.

**Example:**
```typescript
// In memory/page.tsx or layout.tsx, mount once:
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
// <ToastContainer position="bottom-right" autoClose={3000} />

// After delete:
import { toast } from 'react-toastify';
toast.success('Memory item deleted');
```

### Pattern 6: Optimistic UI for delete

**What:** On successful DELETE response, call SWR's `mutate()` to remove the item from local cache without waiting for a refetch. Avoids a round-trip GET after every delete.

**Example:**
```typescript
async function handleDelete(id: string) {
  await fetch(`/api/memory/${id}`, { method: 'DELETE' });
  mutate(prev => prev ? { ...prev, items: prev.items.filter(i => i.id !== id) } : prev, false);
  toast.success('Memory item deleted');
}
```

### Anti-Patterns to Avoid
- **Calling memU directly from browser:** Always proxy through Next.js API routes. Direct calls create CORS issues and expose the internal service URL.
- **Polling memory data:** Memory items don't change in real-time (unlike tasks). Use `revalidateOnFocus: false` and manual `mutate()` after mutations rather than `refreshInterval`.
- **Debounced search:** Locked decision says Enter-key triggered. Debounce-as-you-type would fire expensive vector search on every keystroke.
- **Fetching all data then client-side filtering:** For categories/agents/types, compute filter options from the fetched `GET /memories` response rather than making separate API calls.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom notification system | `react-toastify` (already installed) | Handles queue, auto-dismiss, dark mode, accessibility |
| Data fetching + cache | Manual fetch + useState | SWR | Handles deduplication, revalidation, cache key management |
| Project-scoped API | Fetching raw memU from browser | Next.js API route proxy | Handles CORS, keeps memU URL as server-side secret |
| Search state machine | Complex reducer | Simple `useState` for `searchQuery` | Two modes (browse/search) are straightforward to represent |

**Key insight:** The entire pattern — proxy API route + SWR hook + table component — already exists in the codebase for tasks, agents, metrics. This phase is an application of the established pattern to a new data type.

## Common Pitfalls

### Pitfall 1: memU `GET /memories` response shape is a raw list
**What goes wrong:** The endpoint returns a plain JSON array, not `{ items: [] }`. Code that destructures `{ items }` from the response will get `undefined`.
**Why it happens:** The memU `list_memory_items()` returns the list directly; the FastAPI router returns it as-is.
**How to avoid:** In the API proxy route, normalize: `const items = Array.isArray(data) ? data : (data.items ?? []);`
**Warning signs:** `items` is always undefined or empty even when memU has data.

### Pitfall 2: `POST /retrieve` response shape varies
**What goes wrong:** The retrieve endpoint can return a plain list OR `{ items: [...] }` depending on the memU version and mode. `memory_client.py` already handles both shapes (see lines 243-248).
**Why it happens:** The memu-py library's retrieve result is not stable across versions.
**How to avoid:** Apply the same normalization as the existing Python client: `if isinstance(data, list): return data; if 'items' in data: return data['items']`
**Warning signs:** Search returns empty when memU logs show hits.

### Pitfall 3: Memory item field names are unknown without running the service
**What goes wrong:** The TypeScript `MemoryItem` type is written with assumed field names that differ from what memU actually returns.
**Why it happens:** The memU `list_memory_items()` return schema is not exposed as a documented API contract in this codebase — it's inferred from the Python `memu.app` library internals.
**How to avoid:** The `MemoryItem` type should start as `Record<string, unknown>` with known fields typed optionally (`id?: string; content?: string; category?: string; agent_type?: string; created_at?: string | number`). Render defensively.
**Warning signs:** TypeScript compiler errors about missing properties OR items render blank because field names don't match.

### Pitfall 4: ToastContainer not mounted
**What goes wrong:** `toast.success()` calls succeed silently without any visible toast.
**Why it happens:** `react-toastify` requires `<ToastContainer />` to be mounted somewhere in the React tree.
**How to avoid:** Mount `<ToastContainer position="bottom-right" autoClose={3000} />` in `layout.tsx` (global) or in the memory page component. If mounting globally, import the CSS once in `globals.css` or `layout.tsx`.
**Warning signs:** No toast appears after delete, no error thrown.

### Pitfall 5: Sidebar not updated with Memory nav link
**What goes wrong:** `/memory` page is created but not reachable from the sidebar navigation.
**Why it happens:** Sidebar has a hardcoded `navItems` array in `Sidebar.tsx`.
**How to avoid:** Add a Memory nav item to `navItems` in `src/components/layout/Sidebar.tsx`.
**Warning signs:** Page loads at `/memory` directly but has no nav link.

### Pitfall 6: Search results intermixed with browse results
**What goes wrong:** When returning from search mode (clicking "clear"), the SWR cache may still show search results until a fresh GET fetch completes.
**Why it happens:** SWR cache key for search (`?search=foo`) is different from browse (`?project=pumplai`). Cache for browse mode is already populated and valid — SWR returns it immediately.
**How to avoid:** Use separate `searchQuery` state; when `searchQuery` is null, SWR key uses browse endpoint, which is already cached. No explicit cache invalidation needed.

## Code Examples

Verified patterns from existing codebase:

### Delete via Next.js API route (proxy pattern)
```typescript
// Source: pattern from workspace/occc/src/app/api/tasks/[id]/route.ts analogue
// New file: workspace/occc/src/app/api/memory/[id]/route.ts

import { NextRequest } from 'next/server';
import { readOpenClawConfig, getActiveProjectId } from '@/lib/openclaw';

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const config = await readOpenClawConfig();
    const memory = config.memory as Record<string, string> | undefined;
    const memuUrl = memory?.memu_api_url ?? 'http://localhost:18791';

    const res = await fetch(`${memuUrl}/memories/${params.id}`, { method: 'DELETE' });
    if (!res.ok) {
      return Response.json({ error: 'Delete failed' }, { status: res.status });
    }
    const data = await res.json();
    return Response.json(data);
  } catch (error) {
    console.error('Error deleting memory:', error);
    return Response.json({ error: 'Failed to delete memory item' }, { status: 500 });
  }
}
```

### SWR hook with project and search parameters
```typescript
// Source: adapted from workspace/occc/src/lib/hooks/useTasks.ts
// New file: workspace/occc/src/lib/hooks/useMemory.ts

import useSWR from 'swr';
import type { MemoryListResponse } from '@/lib/types/memory';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useMemory(projectId: string | null, searchQuery: string | null = null) {
  const params = new URLSearchParams();
  if (projectId) params.set('project', projectId);
  if (searchQuery) params.set('search', searchQuery);

  const key = projectId ? `/api/memory?${params.toString()}` : null;

  const { data, error, isLoading, mutate } = useSWR<MemoryListResponse>(
    key,
    fetcher,
    { revalidateOnFocus: false }
  );

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    mode: data?.mode ?? 'browse',
    isLoading,
    error,
    mutate,
  };
}
```

### Stats bar computation (client-side from items)
```typescript
// Compute from loaded items — no separate API call
function computeStats(items: MemoryItem[]) {
  const byAgent = items.reduce<Record<string, number>>((acc, item) => {
    const agent = item.agent_type ?? 'unknown';
    acc[agent] = (acc[agent] ?? 0) + 1;
    return acc;
  }, {});
  return { total: items.length, byAgent };
}
```

### Pagination (client-side, ~25 per page)
```typescript
const PAGE_SIZE = 25;
const [page, setPage] = useState(1);
const paginated = items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
const totalPages = Math.ceil(items.length / PAGE_SIZE);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pages/` router (Next.js) | `app/` router with Server Components | Next.js 13+ | Memory page is `'use client'` — follows existing dashboard pattern; all pages in `src/app/` are client components |
| Manual fetch + useEffect | SWR | Already established | SWR handles cache separation by URL key; no migration needed |
| `window.confirm()` | Custom dialog component | Always | `window.confirm()` blocks the thread and can't be styled; custom component required |

**Deprecated/outdated:**
- `pages/` directory: Not used in this project. All pages are in `src/app/`.
- `getServerSideProps` / `getStaticProps`: Not applicable in App Router.

## Open Questions

1. **memU memory item schema — exact field names**
   - What we know: The FastAPI `GET /memories` endpoint calls `memu.list_memory_items()`. The Python service returns items directly from the memu-py library. The `memory_client.py` in orchestration treats items as `dict` (no type annotation).
   - What's unclear: The exact JSON field names returned by `list_memory_items()` — particularly whether it's `category`, `type`, `agent_type`, `created_at`, or similar. The memu-py `app/crud.py` at `~/.openclaw/workspace/memory/src/memu/app/crud.py` can be read to determine the schema definitively.
   - Recommendation: Read `workspace/memory/src/memu/app/crud.py` during Wave 0 (type definition task) to determine exact schema. Define `MemoryItem` TypeScript type from that. The planner should include this as the first task of the first plan.

2. **react-toastify CSS import**
   - What we know: `react-toastify ^10.0.5` is in `package.json`. The package requires its CSS to be imported once.
   - What's unclear: Whether `globals.css` or `layout.tsx` is the right import point. The `globals.css` currently only has Tailwind directives.
   - Recommendation: Import `react-toastify/dist/ReactToastify.css` in `layout.tsx` alongside the `globals.css` import.

3. **Bulk delete API: individual requests vs batch endpoint**
   - What we know: The memU service only has `DELETE /memories/{id}` (single item). There is no batch delete endpoint.
   - What's unclear: Whether to fire N parallel DELETE requests or sequence them.
   - Recommendation: Fire parallel `Promise.all()` for selected IDs. For typical batch sizes (< 50 items), this is acceptable. After all settle, refresh the list via `mutate()`.

## Validation Architecture

The planning config has `workflow.nyquist_validation` absent (not set to `true`) — validation architecture section is omitted per instructions.

However, the `tests/` directory in `workspace/occc/` exists (currently has only `tests/privacy/`). Playwright is the configured testing framework (per `.planning/config.json preferences.testing_framework`). No test scaffolding is needed for this phase — it is a UI-only phase and validation is manual (view the page in browser, verify behaviour).

## Sources

### Primary (HIGH confidence)
- `~/.openclaw/docker/memory/memory_service/routers/memories.py` — GET /memories and DELETE /memories/{id} implementations (read directly)
- `~/.openclaw/docker/memory/memory_service/routers/retrieve.py` — POST /retrieve implementation (read directly)
- `~/.openclaw/docker/memory/memory_service/models.py` — RetrieveRequest schema (read directly)
- `~/.openclaw/workspace/occc/src/lib/hooks/useTasks.ts` — SWR hook pattern (read directly)
- `~/.openclaw/workspace/occc/src/app/api/tasks/route.ts` — Next.js proxy API route pattern (read directly)
- `~/.openclaw/workspace/occc/src/components/layout/Sidebar.tsx` — Nav item pattern (read directly)
- `~/.openclaw/workspace/occc/package.json` — Installed deps including react-toastify ^10.0.5 (read directly)
- `~/.openclaw/orchestration/memory_client.py` — retrieve() response normalization pattern (lines 243-248) (read directly)

### Secondary (MEDIUM confidence)
- react-toastify v10 API (`toast.success()`, `<ToastContainer />`, CSS import) — established library; training knowledge cross-referenced with package version

### Tertiary (LOW confidence)
- Exact memU `list_memory_items()` return schema — inferred from Python layer; requires verification against `workspace/memory/src/memu/app/crud.py`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in package.json, all API endpoints verified by reading source
- Architecture: HIGH — patterns directly copied from existing occc pages; proxy route pattern is proven
- Pitfalls: HIGH for API shape pitfalls (verified from source); MEDIUM for ToastContainer (verified from package presence, library training knowledge)
- memU item schema: LOW — requires reading crud.py to confirm exact field names

**Research date:** 2026-02-24
**Valid until:** 2026-03-10 (stable stack, memU service already deployed)
