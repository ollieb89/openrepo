# Mission Control: Proper Implementation Design

**Date:** 2026-03-05
**Scope:** Stabilize and complete the four Mission Control dashboard components — AttentionQueue, LiveEventFeed, SwarmStatusPanel, TaskPulse

---

## Problem Statement

All four Mission Control components have working API connections, but three have correctness or robustness gaps:

| Component | Gap |
|---|---|
| `AttentionQueue` | Manual `setInterval` polling: no dedup, no error states, no stale-data UX |
| `LiveEventFeed` | No connection state UI; blank panel when `events.sock` is absent |
| `SwarmStatusPanel` | `todayCostUsd` / `todayTokens` hard-coded `null` — cost data exists in gateway but never persists |
| `TaskPulse` | Already correct (SWR, 3s, reads `workspace-state.json`) — no changes needed |

---

## Architecture: Three Independent Streams

```
Stream 1: SWR standardization   → AttentionQueue
Stream 2: SSE robustness         → LiveEventFeed
Stream 3: Cost tracking          → Gateway → NDJSON → /api/metrics → SwarmStatusPanel
```

Each stream is independently deployable. Stream 3 spans two packages.

---

## Stream 1 — AttentionQueue: SWR Migration

### What changes

Delete the `setInterval` / `loadItems` pattern in `AttentionQueue.tsx`. Replace with three SWR hooks that each wrap `apiJson()` (existing — handles `/occc` basePath + `X-OpenClaw-Token`).

### New hooks (`lib/hooks/`)

Three focused hooks. SWR key is the logical API path; `apiJson` resolves the full URL internally.

```ts
// useEscalatingTasks.ts
export function useEscalatingTasks(projectId: string | null) {
  return useSWR<{ tasks: Task[] }>(
    projectId ? `/api/tasks?state=escalating&project=${projectId}` : null,
    (url) => apiJson(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}

// useDecisions.ts — NOTE: route uses `projectId=` (not `project=`)
export function useDecisions(projectId: string | null) {
  return useSWR<Decision[]>(
    projectId ? `/api/decisions?projectId=${projectId}` : null,
    (url) => apiJson(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}

// useSuggestions.ts — NOTE: route uses `project=` (not `projectId=`)
export function useSuggestions(projectId: string | null) {
  return useSWR<{ version: string; last_run: number | null; suggestions: SuggestionRecord[] }>(
    projectId ? `/api/suggestions?project=${projectId}` : null,
    (url) => apiJson(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}
```

**Query param naming is intentionally different per route** — this matches the actual backend:
- `/api/tasks` → `project=`
- `/api/decisions` → `projectId=`
- `/api/suggestions` → `project=`

### Component UX

- **Loading (no data yet):** skeleton list
- **Stale data visible + any hook errored:** show a "data may be stale" banner above the list (single banner, not per-kind)
- **Per-kind error badges:** if a specific kind fails to load, suppress that kind's items and show a small inline badge (e.g., "ESC unavailable")
- **Sort order preserved:** escalations → decisions → suggestions (unchanged)
- **Dismiss/action buttons:** unchanged behavior, now using SWR `mutate` to optimistically remove items

---

## Stream 2 — LiveEventFeed: Connection Robustness

### Connection state machine

The `EventSource` connection passes through these states:

```
connecting → live → reconnecting → offline
               ↑_________________________|  (periodic retry every 10s)
```

- **connecting:** initial state on mount
- **live:** `EventSource.onopen` fired
- **reconnecting:** `EventSource.onerror` fired while previously live
- **offline:** 4s elapsed without reaching `live` on the most recent connect attempt; also triggered if repeated reconnect attempts fail

When `offline`, the hook continues attempting SSE reconnect every 10s in the background (so the panel recovers without a page refresh). Fallback polling is active while offline.

### New hook: `useLiveEvents`

```ts
// lib/hooks/useLiveEvents.ts
export type LiveEventStatus = 'connecting' | 'live' | 'reconnecting' | 'offline';

export interface LiveEvent {
  id: number;
  type: string;
  project_id?: string;
  task_id?: string;
  message?: string;
  rawAt: number;
}

export function useLiveEvents(projectId: string | null): {
  events: LiveEvent[];
  status: LiveEventStatus;
}
```

Hook manages:
- `EventSource` lifecycle with status state machine
- In-memory ring of last 50 events
- Project-id filtering (same logic as current component)
- Cleanup on unmount

### New API endpoint: `GET /api/events/latest`

Exposes the existing module-level `ringBuffer` from `events/route.ts`.

**Confirmed:** `ringBuffer` is module-scope (lines 9–10 of `events/route.ts`), populated on every SSE data forward. It stores `{ id: number; data: string }` where `data` is the raw JSON string from the Python socket.

**Endpoint behavior:**
- Query param: `?limit=N` (default 50, max 200)
- Returns last N entries, parsed back to objects
- Response shape:

```ts
interface EventsLatestResponse {
  events: LiveEvent[];  // parsed from ring buffer data field
}
```

Parsing is resilient: each `data` line is JSON-parsed; malformed lines are skipped.

**Auth:** matches existing `/api/events` behavior (currently unauthed, matching `events/route.ts`). Risk callout: if Mission Control is ever exposed beyond localhost, auth should be added here at the same time as the SSE endpoint.

### Fallback polling when offline

```ts
// Active only when status === 'offline'
useSWR<EventsLatestResponse>(
  status === 'offline' ? `/api/events/latest?limit=50` : null,
  (url) => apiJson(url),
  { refreshInterval: 3000 }
)
```

### Component UI changes

The header area gains a status pill:

| State | Pill |
|---|---|
| `connecting` | grey "connecting…" |
| `live` | green "live" (existing behavior) |
| `reconnecting` | amber "reconnecting…" |
| `offline` | red "offline (polling)" |

Existing pause/filter buttons unchanged.

---

## Stream 3 — Cost/Token Tracking

The TypeScript `openclaw` gateway already computes `costUsd` and token counts per model call (`agent-runner.ts:437`) and emits `DiagnosticUsageEvent` (`type: "model.usage"`) via `emitDiagnosticEvent`. These events currently have no persistent subscriber — they die in memory.

### File path (canonical, shared by gateway and dashboard)

```
${OPENCLAW_ROOT}/workspace/.openclaw/<projectId>/usage.ndjson
```

- Gateway resolves: `path.join(process.env.OPENCLAW_ROOT ?? expandHome('~/.openclaw'), 'workspace', '.openclaw', projectId, 'usage.ndjson')`
- Dashboard resolves: `path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'usage.ndjson')` (same `OPENCLAW_ROOT` env var)

### Part A — Gateway: `src/infra/usage-logger.ts`

New module. Subscribes to diagnostic events, appends `model.usage` events to NDJSON.

**Line shape (one JSON object per line):**

```json
{
  "ts": "2026-03-05T12:34:56.789Z",
  "type": "model.usage",
  "projectId": "pumplai",
  "taskId": "task-abc123",
  "agentId": "pumplai_pm",
  "runId": "run-xyz",
  "model": "claude-sonnet-4-6",
  "usage": {
    "inputTokens": 1234,
    "outputTokens": 456,
    "totalTokens": 1690
  },
  "costUsd": 0.01234
}
```

**Field rules:**
- `ts`: ISO 8601 UTC string (`new Date().toISOString()`)
- `costUsd`: always present; 0 if not computable
- `usage.totalTokens`: always present; other fields best-effort
- `runId`: include if available from the diagnostic event or run context
- `projectId`: resolved from session/channel context; omit rather than write `undefined`

**Write behavior:**
- Append-only; create file if absent (and parent directory)
- Best-effort: `fs.appendFile` failures log a warning via existing logger, never throw
- No rotation in v1; file grows indefinitely (rotation is v2)
- V1 perf note: if file exceeds 50MB, reads will be capped to the last 50MB (see Part B)

**Initialization:** call `initUsageLogger()` at gateway startup, alongside other infra setup. Returns an unsubscribe function for clean shutdown.

### Part B — Dashboard: `/api/metrics/route.ts` aggregation

After existing lifecycle computation, read and aggregate `usage.ndjson`:

**Parsing strategy (resilient):**
```ts
async function readTodayUsage(projectId: string): Promise<{ tokens: number; costUsd: number; hasLog: boolean }> {
  const filePath = path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'usage.ndjson');

  try {
    const raw = await fs.readFile(filePath, 'utf-8');  // v1: read whole file; cap at last 50MB in v2
    const todayOslo = getTodayOslo();  // see timezone section below

    let tokens = 0;
    let costUsd = 0;

    for (const line of raw.split('\n')) {
      if (!line.trim()) continue;  // skip blank lines
      try {
        const entry = JSON.parse(line);
        if (entry.type !== 'model.usage') continue;  // future-proof
        if (!entry.ts) continue;
        if (getOsloDateString(new Date(entry.ts)) !== todayOslo) continue;
        tokens += entry.usage?.totalTokens ?? 0;
        costUsd += entry.costUsd ?? 0;
      } catch {
        continue;  // skip malformed lines
      }
    }

    return { tokens, costUsd, hasLog: true };
  } catch (err: unknown) {
    if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
      return { tokens: 0, costUsd: 0, hasLog: false };
    }
    throw err;
  }
}
```

**Oslo day bucketing (no library):**
```ts
function getOsloDateString(date: Date): string {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Oslo' }).format(date);
  // returns 'YYYY-MM-DD' (sv-SE locale produces ISO date format)
}

function getTodayOslo(): string {
  return getOsloDateString(new Date());
}
```

Compare event date string to today's date string. No start/end-of-day timestamp math needed.

### Part C — Updated `MetricsResponse` type

```ts
export interface MetricsResponse {
  // ... existing fields unchanged ...
  todayTokens: number;      // 0 if no usage log or no usage today
  todayCostUsd: number;     // 0 if no usage log or no cost today
  hasUsageLog: boolean;     // false if usage.ndjson absent (gateway not instrumented yet)
}
```

`null` is avoided — `0` with `hasUsageLog: false` is cleaner for consumers.

### Part D — `SwarmStatusPanel.tsx` UI unlock

Replace the hard-coded null values:
```ts
// Before:
const todayCostUsdVal = null as number | null;
const todayTokensVal = null as number | null;

// After:
const todayCostUsdVal = metrics?.todayCostUsd ?? null;
const todayTokensVal = metrics?.todayTokens ?? null;
// Guard: only show if hasUsageLog is true (avoids showing "0.00 · 0.0M tok" before instrumented)
const showCost = metrics?.hasUsageLog === true;
```

The existing conditional render block is already written — swap the guard condition to `showCost` instead of `todayCostUsdVal != null`.

---

## What We Are NOT Doing (YAGNI)

- **No `/api/mission-control` aggregation endpoint** — SWR deduplication handles N concurrent hooks hitting the same key efficiently
- **No NDJSON daily rotation** — v2 when file size matters; architecture supports it (filename convention: `usage-YYYY-MM-DD.ndjson`)
- **No per-model usage breakdown in metrics** — add to UI when breakdown view is designed
- **No live `model.usage` events in LiveEventFeed** — can be added later by tailing NDJSON or bridging gateway diagnostics to the Python event socket

---

## File Changes Summary

| File | Change | Stream |
|---|---|---|
| `lib/hooks/useEscalatingTasks.ts` | New | 1 |
| `lib/hooks/useDecisions.ts` | New | 1 |
| `lib/hooks/useSuggestions.ts` | New | 1 |
| `components/mission-control/AttentionQueue.tsx` | Rewrite (remove setInterval, use new hooks) | 1 |
| `lib/hooks/useLiveEvents.ts` | New | 2 |
| `app/api/events/latest/route.ts` | New | 2 |
| `components/mission-control/LiveEventFeed.tsx` | Refactor (use hook, add status pill) | 2 |
| `openclaw/src/infra/usage-logger.ts` | New (gateway package) | 3 |
| `openclaw/src/[gateway-startup].ts` | Add `initUsageLogger()` call | 3 |
| `app/api/metrics/route.ts` | Add `readTodayUsage()`, add fields to response | 3 |
| `lib/types.ts` | Add `todayTokens`, `todayCostUsd`, `hasUsageLog` to `MetricsResponse` | 3 |
| `components/mission-control/SwarmStatusPanel.tsx` | Unlock cost display | 3 |
