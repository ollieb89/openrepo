# Dashboard Audit

**Date:** 2026-03-06

## Build & Type Errors

### TypeScript (`npx tsc --noEmit`) — Exit Code: 1

```
.next/types/app/api/metrics/route.ts(12,13): error TS2344: Type 'OmitWithTag<typeof import("/home/ob/Development/Tools/openrepo/packages/dashboard/src/app/api/metrics/route"), "GET" | "POST" | "config" | "DELETE" | "PUT" | "runtime" | "dynamic" | "generateStaticParams" | ... 7 more ... | "PATCH", "">' does not satisfy the constraint '{ [x: string]: never; }'.
  Property 'readPythonSnapshot' is incompatible with index signature.
    Type '(snapshotPath: string) => Promise<PythonSnapshotResult>' is not assignable to type 'never'.
.next/types/app/api/pipeline/route.ts(12,13): error TS2344: Type 'OmitWithTag<typeof import("/home/ob/Development/Tools/openrepo/packages/dashboard/src/app/api/pipeline/route"), "GET" | "POST" | "config" | "DELETE" | "PUT" | "runtime" | "dynamic" | "generateStaticParams" | ... 7 more ... | "PATCH", "">' does not satisfy the constraint '{ [x: string]: never; }'.
  Property 'filterPipelines' is incompatible with index signature.
    Type '(pipelines: PipelineItem[], taskId?: string | null | undefined) => PipelineItem[]' is not assignable to type 'never'.
src/app/api/config/gateway/route.ts(6,10): error TS2724: '"crypto"' has no exported member named 'crypto'. Did you mean 'scrypt'?
src/app/api/config/gateway/route.ts(34,21): error TS2304: Cannot find name 'uuidv4'.
```

Total TypeScript errors: 4

### Next.js Build (`npm run build`) — Exit Code: 1

```
> occc@0.1.0 build
> next build

   ▲ Next.js 15.5.12
   - Environments: .env.local

   Creating an optimized production build ...
 ✓ Compiled successfully in 20.0s
   Linting and checking validity of types ...
Failed to compile.

src/app/api/metrics/route.ts
Type error: Route "src/app/api/metrics/route.ts" does not match the required types of a Next.js Route.
  "readPythonSnapshot" is not a valid Route export field.

Next.js build worker exited with code: 1 and signal: null
```

**Build status: FAILED**

Root cause: `src/app/api/metrics/route.ts` exports a non-route helper function `readPythonSnapshot` at the module level, which Next.js rejects as an invalid route export. Similarly, `src/app/api/pipeline/route.ts` exports `filterPipelines`.

Additionally, `src/app/api/config/gateway/route.ts` has two errors:
- Incorrect named import `crypto` from the `"crypto"` module (should use `randomUUID` from `node:crypto` or similar)
- Reference to undefined `uuidv4` (missing import, likely from `uuid` package)

## Failing Tests

**Test run (`npm run test`) — Exit Code: 1**

```
 Test Files  4 failed | 18 passed (22)
      Tests  5 failed | 122 passed (127)
```

### Failure 1: `tests/connectors/slack-adapter.test.ts`

Test: `slack adapter > uses selected channels and first-sync default window when no checkpoint exists`

```
Error: ENOTEMPTY: directory not empty, rmdir '/home/ob/Development/Tools/openrepo/packages/dashboard/.tmp'
```

The test attempts to clean up a `.tmp` directory after the test run but the directory is not empty, suggesting incomplete teardown from a prior test run that left files behind.

### Failures 2 & 3: `tests/connectors/sync-engine.test.ts`

**Test 2:** `connector runtime primitives > persists checkpoints per connector + source pair`

```
AssertionError: expected undefined to deeply equal { ts: '22.0' }

- Expected:
{
  "ts": "22.0",
}

+ Received:
undefined

 ❯ tests/connectors/sync-engine.test.ts:63:33
     61|
     62|     expect(checkpointA?.cursor).toEqual({ ts: '10.0' });
     63|     expect(checkpointB?.cursor).toEqual({ ts: '22.0' });
       |                                 ^
```

**Test 3:** `connector runtime primitives > writes checkpoints only after successful persistence and resumes from the saved cursor`

```
AssertionError: expected undefined to deeply equal { sequence: 2 }

- Expected:
{
  "sequence": 2,
}

+ Received:
undefined

 ❯ tests/connectors/sync-engine.test.ts:153:44
    151|
    152|     const checkpointAfterFailure = await loadCheckpoint('connector-sla…
    153|     expect(checkpointAfterFailure?.cursor).toEqual({ sequence: 2 });
       |                                            ^
```

Both failures indicate that `loadCheckpoint` returns `undefined` when a saved checkpoint is expected. The checkpoint persistence logic in the sync engine is broken — either the write does not complete, the file path is wrong, or the read fails silently.

### Failure 4: `tests/connectors/sync-status.test.tsx`

Test: `sync status health aggregation > maps connector sync actions to provider-specific endpoints`

```
AssertionError: expected '/occc/api/connectors/slack/sync' to be '/api/connectors/slack/sync' // Object.is equality

Expected: "/api/connectors/slack/sync"
Received: "/occc/api/connectors/slack/sync"

 ❯ tests/connectors/sync-status.test.tsx:25:112
     23|
     24|   it('maps connector sync actions to provider-specific endpoints', () …
     25|     expect(resolveSyncEndpoint({ id: 'connector-slack-primary', provid…
       |                                                                                                                ^
     26|       '/api/connectors/slack/sync'
     27|     );
```

The `resolveSyncEndpoint` function produces URLs prefixed with `/occc` (the Next.js `basePath`), but the test expects bare `/api/...` paths. Either the function should strip the base path prefix, or the test expectation needs updating to match the configured base path.

### Failure 5: `tests/connectors/tracker-adapter.test.ts`

Test: `tracker adapters > re-ingests GitHub issues changed after the checkpoint based on updatedAt cursor`

```
Error: ENOENT: no such file or directory, open '/home/ob/.openclaw/workspace/.openclaw/records/connector-tracker-github/acme/repo.json'
 ❯ saveSyncRecords src/lib/sync/storage.ts:66:6
     64|   const mergedRecords = Array.from(recordMap.values());
     65|
     66|   fs.writeFileSync(filePath, JSON.stringify(mergedRecords, null, 2));
       |      ^
     67| }
     68|
 ❯ runIncrementalSync src/lib/sync/engine.ts:246:15
 ❯ tests/connectors/tracker-adapter.test.ts:106:5
```

The `saveSyncRecords` function in `src/lib/sync/storage.ts` calls `mkdirSync` with `recursive: true`, but only for the `connectorId` directory level. When `sourceId` contains a slash (e.g., `"acme/repo"`), the intermediate subdirectory (`acme/`) is not created before the `writeFileSync` call, causing ENOENT. The fix is to derive the full parent path from `filePath` and pass it to `mkdirSync`, rather than only creating the `connectorId` level directory.

### Notable stderr (non-fatal, tests still pass):

Multiple Ollama-related errors appear during `tests/connectors/tracker-adapter.test.ts`:
- `ResponseError: model "mxbai-embed-large" not found` — embedding model not installed locally
- `ResponseError: model 'phi3:mini' not found` — summarizer LLM model not installed locally

These errors are swallowed by the code and the affected tests still pass, but they indicate that Ollama-dependent paths cannot be fully exercised in CI without the models present.

## Lint Errors

```
> occc@0.1.0 lint
> next lint

`next lint` is deprecated and will be removed in Next.js 16.
For new projects, use create-next-app to choose your preferred linter.
For existing projects, migrate to the ESLint CLI:
npx @next/codemod@canary next-lint-to-eslint-cli .

✔ No ESLint warnings or errors
```

None — ESLint is clean. Note: `next lint` is deprecated as of Next.js 15 and will be removed in Next.js 16. Migration to the ESLint CLI is recommended.

## API Issues

**Dev server:** running at `http://localhost:6987/occc` (basePath `/occc` configured in `next.config.js`). All API routes require the `/occc` prefix — requests without it receive 404. The dev server that was running since March 5 was in a corrupted state (missing `.next/routes-manifest.json` and `next-font-manifest.json` after a failed `npm run build` wiped the `.next/server/` directory mid-build); it was restarted before this sweep.

**Auth:** Most routes are protected by `withAuth` middleware (`X-OpenClaw-Token` header or `Authorization: Bearer` header). The gateway token from `.env.local` was used for all authenticated tests.

| Endpoint | Method | Status (no auth) | Status (with auth) | Root Cause / Notes | Priority |
|----------|--------|-----------------|--------------------|--------------------|----------|
| /api/health | GET | 200 | 200 | OK — returns degraded (gateway `needs_ui_build`, event_bridge socket missing). No auth guard. | — |
| /api/health/gateway | GET | 200 | 200 | OK — returns `needs_ui_build`. **No `withAuth` wrapper** — any caller can read gateway status. | P3 |
| /api/health/filesystem | GET | 401 | 200 | OK — properly auth-protected. Inconsistent with `/api/health/gateway` and `/api/health/memory` which skip auth. | — |
| /api/health/memory | GET | 200 | 200 | OK — returns `{"status":"ok"}`. **No `withAuth` wrapper** — memory service status exposed without auth. Schema differs from `/api/health` aggregation (uses `"ok"` vs `"healthy"`). | P3 |
| /api/projects | GET | 401 | 200 | OK — returns 9 projects from disk. | — |
| /api/projects/active | GET | 401 | 200 | OK — returns active project. | — |
| /api/tasks | GET | 401 | 200 | OK — returns 4 stub tasks from workspace state. All tasks have `metadata: {}` — no `completed_at`, `container_started_at`, etc. | — |
| /api/agents | GET | 401 | 200 | OK — returns 1 agent (`clawdia_prime`). | — |
| /api/decisions | GET | 401 | 200 | OK — returns empty array `[]` (no decisions stored). | — |
| /api/metrics | GET | 401 | 200 | OK — returns metrics. `completionDurations: []` because all tasks have `metadata: {}` and no `completed_at` field. Exports `readPythonSnapshot` and the `PythonSnapshotResult` interface at module level — **breaks Next.js build** (invalid route export). | P1 |
| /api/metrics/summary | GET | 401 | 200 | OK — but uses `Math.random()` for trend direction/value calculation in `calculateTrend()` — non-deterministic, different values on every request. | P2 |
| /api/metrics/agents | GET | 401 | 200 | OK — returns agent breakdown. Tasks without `l2_agent`/`l3_agent` metadata fall under `"unassigned"` bucket. | — |
| /api/metrics/distribution | GET | 401 | 200 | OK — 7-day distribution. Current day shows 0 (no tasks completed today). | — |
| /api/metrics/trends | GET | 401 | 200 | **Stale/wrong data** — all points show `completed: 0, throughput: 0` even though 2 completed tasks exist. Root cause: `handler` filters on `task.metadata?.completed_at`, but all tasks have `metadata: {}` so the bucket loop produces no entries, triggering `generateEmptyPoints()`. | P2 |
| /api/pipeline | GET | 401 | 200 | OK — returns 4 pipeline items. Exports `filterPipelines` at module level — **breaks Next.js build** (invalid route export). | P1 |
| /api/events/latest | GET | 200 | 200 | **No auth guard** — ring buffer snapshot returned without authentication. Currently returns `{"events":[]}` (empty ring buffer). | P2 |
| /api/events | GET | 200 | 200 | SSE stream — **no auth guard**. Socket error logged on every connection: `connect ENOENT /home/ob/Development/Tools/openrepo/run/events.sock`. The socket file does not exist (orchestration not running). The SSE route sends an `event: error` frame and closes the stream immediately on every connect. | P1 |
| /api/suggestions | GET | 401 | 400 | **400 without `?project=` param** — returns `{"error":"project query parameter is required"}`. With `?project=pumplai` returns `200 {"version":"1.0","last_run":null,"suggestions":[]}`. The 400 is intentional validation but not documented. | P3 |
| /api/memory | GET | 401 | 200 | OK — returns `{"items":[],"total":0,"projectId":"pumplai","mode":"browse"}`. | — |
| /api/topology | GET | 401 | 200 | OK — returns approved topology for active project. | — |
| /api/connectors | GET | 401 | 200 | OK — returns `{"connectors":[]}` (none configured). | — |
| /api/connectors/health | GET | 401 | 200 | OK — returns `{"summary":{"dominantStatus":"disconnected",...},"connectors":[]}`. | — |
| /api/config/gateway | GET | 405 | 405 | **No GET handler** — route only exports `PATCH`. GET returns 405 Method Not Allowed. Additionally, the route file has two compile-time errors: `import { crypto } from 'crypto'` (no such named export — should be `import { randomUUID } from 'node:crypto'`) and `uuidv4()` called without import. These errors prevent production build. | P1 |
| /api/graph/ripple-effects | GET | 401 | 400 | **400 without `?id=` param** — returns `{"error":"Missing id parameter"}`. With `?id=test-task` returns `200 {"id":"test-task","effects":[],"count":0}`. The 400 is intentional validation but not documented. | P3 |
| /api/swarm/stream | GET | 401 | 400 | **400 without `?containerId=` param** — returns `"Container ID is required"` (plain text, not JSON). Auth check is **manual inline** (`validateToken()` called directly in handler body) rather than `withAuth` middleware — inconsistent with every other protected route in the app. The POST handler on the same file correctly uses `withAuth`. | P3 |

### Additional observations

**Auth inconsistency across health endpoints:**
- `/api/health` — public (no auth)
- `/api/health/gateway` — public (no `withAuth` in route file)
- `/api/health/memory` — public (no `withAuth` in route file)
- `/api/health/filesystem` — requires auth (`withAuth` wrapper present)

The sub-health routes have inconsistent auth protection. Gateway and memory status leak without credentials.

**`/api/events` SSE bridge permanently broken at rest:**
The SSE bridge in `src/app/api/events/route.ts` connects to `OPENCLAW_EVENTS_SOCK` (`$OPENCLAW_ROOT/run/events.sock`) on every request. The socket file does not exist when the orchestration engine is not running. The route sends `event: error` and closes immediately, so every client reconnect loops. There is no fallback to poll or degrade gracefully. The server log shows a constant flood of `[SSE Bridge] Socket error: connect ENOENT` lines from the dashboard's own polling.

**Schema mismatch — `/api/health/memory` vs `/api/health` aggregation:**
`/api/health/memory` returns `{"status":"ok"}` but the parent `/api/health` route calls `checkMemoryHealth()` independently and checks `memory.healthy` (boolean) — the two responses have different schemas. Any client that uses `/api/health/memory` directly instead of the aggregate will see different field names.

**Non-deterministic trend values:**
`/api/metrics/summary` computes trend direction/value using `Math.random()` on every request (see `calculateTrend()` in `src/app/api/metrics/summary/route.ts`). Two requests to the same endpoint will return opposite trends. This is not suitable for production display.

**`/api/metrics/trends` zero-counts bug:**
The route buckets tasks by `task.metadata.completed_at`. The workspace state JSON for all tasks has `metadata: {}` — no `completed_at` field. The filter skips all tasks, `sortedBuckets` is empty, and `generateEmptyPoints()` returns all-zero rows. Even when real tasks complete, if the state engine does not write `completed_at` into `metadata`, trends will always show zero.

**`/api/health` aggregate vs `/api/health/gateway` sub-route inconsistency:**
`/api/health/gateway` returns `{"status":"needs_ui_build",...}` with HTTP 200. The parent `/api/health` treats `gateway.needsUiBuild` as `healthy: false`, so the aggregate returns `"status":"degraded"`. The outer shell and the sub-route disagree on severity. The `/api/health` route wraps `checkGatewayHealth()` independently rather than delegating to `/api/health/gateway`.

**`/api/config/gateway` PATCH-only, no GET:**
The route only exposes `export const PATCH = withAuth(...)`. A GET to `/api/config/gateway` returns 405 Method Not Allowed. If any UI component tries to read current gateway config via GET, it will silently fail. No GET handler was found in the route file.

## Page Issues

**HTTP status sweep (GET with auth token, dev server at `http://localhost:6987/occc`):**

| Page | URL | HTTP Status | Notes |
|------|-----|-------------|-------|
| Home | `/occc/` | 308 → `/occc` | Permanent redirect to basePath root; `/occc` itself returns 200. Correct. |
| Mission Control | `/occc/mission-control` | 200 | — |
| Tasks | `/occc/tasks` | 200 | — |
| Metrics | `/occc/metrics` | 200 | — |
| Memory | `/occc/memory` | 200 | — |
| Topology | `/occc/topology` | 200 | — |
| Decisions | `/occc/decisions` | 200 | — |
| Agents | `/occc/agents` | 200 | — |
| Escalations | `/occc/escalations` | 200 | — |
| Suggestions | `/occc/suggestions` | 200 | — |
| Catch-up | `/occc/catch-up` | 200 | — |
| Settings | `/occc/settings` | 404 | No `page.tsx` at `src/app/settings/` root — only sub-pages exist. |
| Environment | `/occc/environment` | 200 | — |
| Containers | `/occc/containers` | 200 | — |
| Settings/Gateway | `/occc/settings/gateway` | 200 | — |
| Settings/Connectors | `/occc/settings/connectors` | 200 | — |
| Settings/Privacy | `/occc/settings/privacy` | 200 | — |

### Per-page analysis

#### Home (`src/app/page.tsx`)

- `'use client'` present; uses `useState`, `useEffect`, `useMemo` — correct.
- Fetches `/api/decisions` (working endpoint, returns `[]`). Array check before `.slice()` is guarded: `if (Array.isArray(data))`. No crash risk.
- Links to `/settings/privacy` which is a valid sub-page (200). The link target is a relative path without basePath — Next.js `<Link>` handles basePath automatically. Correct.
- No SSE dependency.
- **Issues:** None. Page renders correctly (empty decisions state shown).

#### Mission Control (`src/app/mission-control/page.tsx`)

- `'use client'` present; delegates entirely to four child components.
- `LiveEventFeed` uses `useLiveEvents` hook → opens `EventSource` to `/api/events`. The SSE route immediately returns `event: error` (socket ENOENT). The hook transitions to `offline` after 4 seconds and then polls `/api/events/latest` every 3 seconds as fallback. Ring buffer is currently empty, so the feed shows "Offline — waiting for events…". **Impact: live feed always shows offline with zero events.**
- `AttentionQueue` calls three hooks: `useEscalatingTasks` (`/api/tasks` — working), `useDecisions` (`/api/decisions` — working, returns `[]`), `useSuggestions` (`/api/suggestions?project=...` — working, returns `[]`). All gracefully handle empty responses. No crash risk.
- `TaskPulse` calls `useTasks` (`/api/tasks` — working) and `usePipeline` per expanded task (`/api/pipeline` — working). No crash risk.
- `SwarmStatusPanel` calls `useAgents` (`/api/agents` — working) and `useMetrics` (`/api/metrics` — working). No crash risk.
- **Issues:** `LiveEventFeed` is permanently offline due to SSE bridge failure (P1, already classified). All other panels functional.

#### Tasks (`src/app/tasks/page.tsx`)

- `'use client'` present; delegates to `TaskBoard` component.
- No direct broken endpoint usage at page level.
- `TaskBoard` would use `useTasks` or similar — not read in detail, but `/api/tasks` is working.
- **Issues:** None found at page level.

#### Metrics (`src/app/metrics/page.tsx`)

- `'use client'` present; complex page with 5 parallel `apiJson` calls.
- Calls `/api/metrics/summary` — returns non-deterministic trend values due to `Math.random()` (P2 known).
- Calls `/api/metrics/trends` — always returns all-zero data because `completed_at` is missing from task metadata (P2 known). `TrendLineChart` receives `null` for `data` prop (handled with `data={trends}` — component must handle null gracefully).
- Calls `/api/metrics/agents` — working.
- Calls `/api/tasks` — working.
- Calls `/api/metrics/distribution` — working.
- All five fetches use `.catch(() => null)` so one failure does not prevent others from rendering. Safe.
- No SSE dependency.
- **Issues:** TrendLineChart shows all-zero data (P2). Summary KPI trends are non-deterministic (P2). Both are known issues.

#### Memory (`src/app/memory/page.tsx`)

- `'use client'` present; delegates entirely to `MemoryPanel` component.
- `MemoryPanel` would call `/api/memory` — working (returns `{"items":[],"total":0,...}`).
- **Issues:** None found at page level.

#### Topology (`src/app/topology/page.tsx`)

- `'use client'` present; uses `useTopology` and `useTopologyChangelog` hooks.
- `useTopology` fetches `/api/topology?project=<id>` — working (returns approved topology).
- `useTopologyChangelog` fetches `/api/topology/changelog?project=<id>` — endpoint exists (`src/app/api/topology/changelog/`) and returns HTTP 200.
- **Style inconsistency (not a bug):** Page reads `localStorage.getItem('occc-project')` directly in a `useEffect` instead of using `useProject()` from `ProjectContext`. Both use the same key `'occc-project'`, so the value is identical. No functional impact.
- Empty state renders correctly when `!projectId || !hasData`.
- **Issues:** Minor: bypasses `ProjectContext` in favor of direct `localStorage` access. Not a bug but diverges from every other page pattern.

#### Decisions (`src/app/decisions/page.tsx`)

- `'use client'` present; fetches `/api/decisions?projectId=<id>` — working (returns `[]`).
- `handleHide` calls `DELETE /api/decisions/<id>` and `handleReSummarize` calls `POST /api/decisions/<id>/re-summarize` — these routes were not explicitly tested, but they are not broken based on existing audit. If they 404, the `catch` block logs to console and the UI does not crash.
- Array check `Array.isArray(data)` guards the `.map()`. Safe.
- **Issues:** None found.

#### Agents (`src/app/agents/page.tsx`)

- `'use client'` present; delegates entirely to `AgentTree` component.
- `AgentTree` would use `/api/agents` — working (returns 1 agent).
- **Issues:** None found at page level.

#### Escalations (`src/app/escalations/page.tsx`)

- `'use client'` present; delegates to `EscalationsPage` component.
- `EscalationsPage` fetches from `/api/tasks` (working) and `/api/tasks/<id>/autonomy` or similar for escalation data. No broken endpoints identified.
- **Issues:** None found at page level.

#### Suggestions (`src/app/suggestions/page.tsx`)

- `'use client'` present; delegates to `SuggestionsPanel` with `projectId` from `ProjectContext`.
- `SuggestionsPanel` would call `/api/suggestions?project=<id>` — when `projectId` is null (not yet loaded), `useSuggestions` passes `null` as SWR key, so no request is made. Correct.
- **Issues:** None found at page level.

#### Catch-up (`src/app/catch-up/page.tsx`)

- `'use client'` present.
- POSTs to `/api/sync/catch-up`. Tested: returns HTTP 500 with `{"error":"Failed to process catch-up query"}`. Any user query results in a 500 error.
- The page renders an error state via `setError(err.message)` in the catch block — it will display the error message. No crash. But the feature is completely non-functional.
- Hard-coded `activeProjectId: 'default'` in the POST body — does not use the `useProject()` context, so the project selection UI has no effect on catch-up queries.
- **Issues:** `/api/sync/catch-up` returns 500 for all queries (P1 — feature completely broken). Hard-coded `activeProjectId: 'default'` ignores active project selection (P2).

#### Settings (root) (`src/app/settings/`)

- **No `page.tsx` exists at `src/app/settings/`**. Navigating to `/occc/settings` returns 404. There are only sub-pages: `/settings/gateway`, `/settings/connectors`, `/settings/privacy`.
- Any navigation link or UI element pointing to `/settings` (not a sub-page) results in a 404.
- **Issues:** Missing root settings index page — 404 on `/occc/settings` (P2).

#### Settings/Gateway (`src/app/settings/gateway/page.tsx`)

- No `'use client'` directive at the page level — but it imports `DiffViewer` which is `'use client'`. This is valid in Next.js App Router: a server component can import a client component.
- `DiffViewer` fetches `/api/config/staged` (HTTP 200 — returns `{"staged":{},"live":{...}}`). Working.
- `DiffViewer` calls `POST /api/config/apply` on button click. Endpoint exists. Not tested for correctness, but no crash on fetch.
- **Issues:** None found. (The `DiffViewer` on this page does NOT hit `/api/config/gateway` — that broken route is a separate resource.)

#### Settings/Connectors (`src/app/settings/connectors/page.tsx`)

- No `'use client'` at page level; child components are likely client components.
- Renders `SlackConnectorCard`, `TrackerConnectorCard`, `SyncDashboard`, `SyncToast`.
- These components call connector-related endpoints (`/api/connectors`, `/api/connectors/health`) which are working (return empty arrays).
- **Issues:** None at page level.

#### Settings/Privacy (`src/app/settings/privacy/page.tsx`)

- `'use client'` present; delegates to `PrivacyCenter`.
- No broken endpoint dependency identified.
- **Issues:** None found at page level.

#### Environment (`src/app/environment/page.tsx`)

- `'use client'` present.
- Calls `/api/health/gateway` — returns 200 (`{"status":"needs_ui_build",...}`). `res.ok` is `true`, so Gateway shows as **healthy** even though the status is `needs_ui_build`. Misleading display.
- Calls `/api/health/memory` — returns 200 (`{"status":"ok"}`). Correctly shows healthy.
- Hard-codes `'healthy'` for "Event Bridge" without any real check — placeholder comment in code. Always shows green regardless of SSE bridge state.
- Calls `/api/tasks?projectId=<id>` for "Jarvis State" check — working, returns 200.
- Reads `process.env.OPENCLAW_ROOT` on the client side. This is a server-side env var not prefixed `NEXT_PUBLIC_`, so it will always be `undefined` in the browser. The page displays "Not set" as the Project Root value.
- Hard-coded string `/tmp/openclaw-events.sock` for "Event Socket" is wrong — the actual socket path is `$OPENCLAW_ROOT/run/events.sock`. The env var is not client-accessible anyway.
- **Issues:** Gateway health shows "healthy" when status is actually `needs_ui_build` (misleading — P3). Event Bridge always shows healthy despite SSE being broken (P2). `OPENCLAW_ROOT` always shows "Not set" in browser (P3). Socket path is hard-coded and wrong (P3).

#### Containers (`src/app/containers/page.tsx`)

- `'use client'` present; uses `ContainerList` and `LogViewer`.
- `ContainerList` would fetch from a containers-related endpoint (likely `/api/containers` or Docker-related route). Not a known broken endpoint.
- `LogViewer` with `containerId={selectedContainerId}` — when `undefined`, the viewer likely shows an empty/idle state. No null safety issue at page level.
- **Issues:** None found at page level (functionality depends on Docker being available, which is a runtime environment concern, not a code defect).

### Summary table

| Page | HTTP Status | Broken Endpoint Dependency | SSE Affected | New Issues Found | Priority |
|------|-------------|---------------------------|--------------|-----------------|----------|
| Home | 200 (via 308) | None | No | None | — |
| Mission Control | 200 | `/api/events` SSE (LiveEventFeed always offline) | Yes | None beyond known | P1 |
| Tasks | 200 | None | No | None | — |
| Metrics | 200 | `/api/metrics/trends` (all-zero), `/api/metrics/summary` (random trends) | No | None beyond known | P2 |
| Memory | 200 | None | No | None | — |
| Topology | 200 | None | No | Bypasses `useProject()`, reads localStorage directly | P3 |
| Decisions | 200 | None | No | None | — |
| Agents | 200 | None | No | None | — |
| Escalations | 200 | None | No | None | — |
| Suggestions | 200 | None | No | None | — |
| Catch-up | 200 | `/api/sync/catch-up` returns 500 for all queries | No | Hard-coded `activeProjectId: 'default'` | P1 |
| Settings (root) | 404 | — | No | Missing `page.tsx` — 404 on nav | P2 |
| Settings/Gateway | 200 | None (uses `/api/config/staged`, not broken `/api/config/gateway`) | No | None | — |
| Settings/Connectors | 200 | None | No | None | — |
| Settings/Privacy | 200 | None | No | None | — |
| Environment | 200 | None (but misleads on health) | No | Gateway shows healthy when `needs_ui_build`; Event Bridge always green; `OPENCLAW_ROOT` always "Not set"; wrong socket path | P2/P3 |
| Containers | 200 | None | No | None | — |

## SSE / Real-time Issues

### How It Works

`useLiveEvents` (at `packages/dashboard/src/lib/hooks/useLiveEvents.ts`) is the primary real-time hook. It opens a browser `EventSource` to `/api/events`, which the Next.js route handler bridges to a Unix socket (`$OPENCLAW_ROOT/run/events.sock`). Events arriving on the socket are pushed to the browser as SSE frames and simultaneously written into an in-process ring buffer (`src/lib/event-ring-buffer.ts`, capacity 100). If the SSE connection does not reach `open` state within 4 000 ms (`OFFLINE_TIMEOUT_MS`), the hook transitions to `'offline'` and activates a SWR-based polling fallback that hits `/api/events/latest` every 3 seconds. The fallback reads the same ring buffer and returns a snapshot as `{ events: [...] }`. A periodic reconnect timer (10 000 ms, `RECONNECT_INTERVAL_MS`) retries the SSE connection whenever the hook is in `'offline'` or `'reconnecting'` state.

There is a second, older SSE hook — `useEvents` (at `packages/dashboard/src/hooks/useEvents.ts`) — that connects directly to `/api/events` without any offline fallback or status tracking. It is used only by `TaskBoard`. It also has no `projectId` filtering in the `useCallback` dependency array (see Hook Code Issues below).

`LogViewer` (`packages/dashboard/src/components/LogViewer.tsx`) opens its own independent `EventSource` to `/api/events` and filters for `EventType.TASK_OUTPUT` frames matching a specific `task_id`. It implements exponential-backoff reconnect (1 s → 30 s cap).

### SSE Endpoint (/api/events)

**Status: Broken when orchestration engine is not running.**

Root cause: `packages/dashboard/src/app/api/events/route.ts` calls `net.connect(socketPath)` immediately when the SSE stream is opened. The socket path resolves to `$OPENCLAW_ROOT/run/events.sock` (default: `~/.openclaw/run/events.sock`). When the orchestration engine is not running, the socket file does not exist. The `'error'` event fires synchronously with `ENOENT`, the route sends `event: error\ndata: {"message":"connect ENOENT ..."}\n\n`, and the stream closes via the `'close'` handler calling `controller.close()`.

The consequence is a permanent connect-error-close cycle: the browser `EventSource` fires `onerror`, the hook sets a timer, and attempts to reconnect every 10 s. The server log floods with `[SSE Bridge] Socket error: connect ENOENT` on every cycle. There is no guard that holds the SSE response open, sends a retry hint, or delays the socket connection attempt.

One additional flaw: when the socket error fires before `onopen`, the `onerror` handler in `useLiveEvents` does not transition state (line 99–109 only acts if `statusRef.current === 'live'`). The offline timer set during `connect()` is the only mechanism that eventually moves the hook to `'offline'`. This means the UI stays in `'connecting'` or `'reconnecting'` for the full 4 s timeout on every reconnect cycle before falling back, rather than reacting immediately to the error frame.

### Fallback Polling (/api/events/latest)

**Status: Endpoint works; always returns an empty array when the orchestration engine has never run.**

`curl -s -H "Authorization: Bearer dev-token" http://localhost:6987/occc/api/events/latest` returns:
```json
{"events":[]}
```

The ring buffer (`event-ring-buffer.ts`) is a module-scope in-process singleton. It is only populated when the SSE bridge successfully reads data from the Unix socket and calls `addToRingBuffer()`. Because the socket never connects when the engine is not running, the buffer is always empty. The fallback polling therefore returns `{"events":[]}` indefinitely — it does not fail or throw, but it also provides no data.

The `/api/events/latest` route has no `withAuth` guard (already classified as P2 in the API Issues section).

The fallback polling is triggered only when `status === 'offline'`. Because the hook's `onerror` callback does not immediately set offline state (it waits for the 4 s timer), there is a 4 s gap on every reconnect cycle where the fallback SWR key is `null` and no polling request is made.

### Hook Code Issues

**1. `useLiveEvents` — `onerror` does not immediately transition to offline on initial connect failure (useLiveEvents.ts lines 98–110)**

The `onerror` handler only calls `updateStatus('reconnecting')` and restarts the offline timer when `statusRef.current === 'live'`. If the hook is in `'connecting'` or `'reconnecting'` state when the error fires (which is always the case when the socket does not exist), the error is silently swallowed and the hook waits for the offline timer to expire. The UI stays frozen in `'connecting'` for 4 s instead of reacting immediately to the server's explicit `event: error` frame. A fix would be to also handle the `'reconnecting'` → timer-restart case and the `'connecting'` → immediate-offline case in `onerror`.

**2. `useEvents` (legacy hook) — no fallback, no status, no reconnect limit (hooks/useEvents.ts)**

The legacy `useEvents` hook in `src/hooks/useEvents.ts` opens an `EventSource` with no offline fallback, no status reporting, and no reconnect throttle. The browser `EventSource` specification reconnects automatically on every error; without any limiting logic, this produces a tight reconnect loop against the permanently-broken `/api/events` endpoint. The hook exposes a `reconnect` function but no `status` state, so consumers (`TaskBoard`) have no way to indicate offline state in the UI.

**3. `useEvents` — missing `projectId` in URL path (hooks/useEvents.ts line 17)**

`useEvents` constructs the URL as `/api/events?project=${projectId}`. However, the server-side route handler in `packages/dashboard/src/app/api/events/route.ts` does not read or apply a `project` query parameter — it forwards all socket events to all connected clients. Project filtering is performed client-side only inside `useLiveEvents` (line 83). The `?project=` parameter is silently ignored by the server, so `useEvents` provides no server-side filtering despite implying it does.

**4. `LogViewer` — tight exponential-backoff loop against broken endpoint (LogViewer.tsx lines 93–107)**

`LogViewer` starts backoff at 1 s and doubles up to 30 s. While this is better than no throttle, it still produces a significant number of connection attempts (at 1 s, 2 s, 4 s, 8 s, 16 s, then every 30 s) against an endpoint that is permanently broken. All reconnect attempts generate server-side socket ENOENT errors and log noise.

**5. `LogViewer` — `connectToEventSource` callback has `effectiveTaskId` and `isActive` in deps, but Effect B also lists `connectToEventSource` as dep (LogViewer.tsx lines 152–179)**

When `effectiveTaskId` changes, `connectToEventSource` is re-created (new callback reference), which re-triggers Effect B, which closes the old `EventSource` and opens a new one. This is the intended behavior. However, there is a subtle race: Effect A (lines 127–150) runs before Effect B (lines 152–179) on the same render. If Effect A sets state (`setLogs([])`) and Effect B immediately opens a new connection, the cleanup of the previous Effect B's `EventSource` happens inside Effect B's return function — which runs before the new Effect B body. This ordering is correct but tightly coupled; a future change that re-orders effects could introduce a double-open or leak.

**6. No `Last-Event-ID` sent by browser `EventSource` API for `useLiveEvents` — replay logic is unreachable in practice (route.ts lines 22–28)**

`packages/dashboard/src/app/api/events/route.ts` implements replay of missed events using `Last-Event-ID`. The browser `EventSource` API does send this header automatically after a reconnect if the server assigned event IDs. The route does assign IDs via `id: ${e.id}` on each emitted event. However, since the socket never connects when the engine is not running, no events with IDs are ever sent, so `Last-Event-ID` is never populated by the client in practice. The replay logic is correct but unreachable in the current environment.

### Affected Components

The following components are directly affected by the SSE bridge failure:

| Component | File | Hook Used | Impact |
|-----------|------|-----------|--------|
| `LiveEventFeed` | `src/components/mission-control/LiveEventFeed.tsx` | `useLiveEvents` | Always shows "offline (polling)" status; event list always empty; polls `/api/events/latest` every 3 s with no result |
| `TaskBoard` | `src/components/tasks/TaskBoard.tsx` | `useEvents` (legacy) | No live task updates; tight reconnect loop against broken endpoint; no visual indicator of offline state |
| `LogViewer` | `src/components/LogViewer.tsx` | Direct `EventSource` | Never shows live task output; exponential-backoff reconnects every 1–30 s; always shows "Reconnecting…" status |
| `TaskTerminalPanel` | `src/components/tasks/TaskTerminalPanel.tsx` | `LogViewer` (child) | Inherits `LogViewer` failure; task output pane permanently empty |
| Containers page | `src/app/containers/page.tsx` | `LogViewer` (child) | Inherits `LogViewer` failure; container log view permanently empty |

The Mission Control page (`/occc/mission-control`) is the primary user-visible surface area. Its `LiveEventFeed` shows "offline (polling)" immediately after 4 s and remains in that state. All other real-time panels on Mission Control (`AttentionQueue`, `TaskPulse`, `SwarmStatusPanel`) use SWR polling against REST endpoints and are unaffected by the SSE failure.

## Priority Classification

### P1: Crashes / Errors (blockers)

1. **Build is broken** — `npm run build` exits with code 1. Production deployments are impossible until resolved.
   - `packages/dashboard/src/app/api/metrics/route.ts` exports `readPythonSnapshot` as a module-level named export, which Next.js interprets as an invalid route handler export field.
   - `packages/dashboard/src/app/api/pipeline/route.ts` exports `filterPipelines` at the module level — same class of error.
   - `packages/dashboard/src/app/api/config/gateway/route.ts` has a broken `crypto` import and an undefined `uuidv4` reference.

2. **`/api/config/gateway` PATCH handler has compile-time errors** — `import { crypto } from 'crypto'` is an invalid named import (no such export); `uuidv4()` is called without any import. These errors are caught by TypeScript and prevent production build. (`packages/dashboard/src/app/api/config/gateway/route.ts`)

3. **`/api/events` SSE bridge immediately errors on every connection** — The route connects to a Unix socket (`$OPENCLAW_ROOT/run/events.sock`) that does not exist unless the orchestration engine is running. On every SSE connect, the socket error fires immediately, the stream sends `event: error` and closes. The server log floods with `[SSE Bridge] Socket error: connect ENOENT` on every dashboard poll cycle. No graceful fallback or retry-after. (`packages/dashboard/src/app/api/events/route.ts`)

4. **Test: `sync-engine` checkpoint persistence is broken** — `loadCheckpoint` returns `undefined` after a save. Any feature relying on resumable sync will silently fail. (`packages/dashboard/src/lib/sync/storage.ts`; test: `tests/connectors/sync-engine.test.ts`)

5. **Test: `tracker-adapter` — sourceId slash causes ENOENT** — `saveSyncRecords` in `packages/dashboard/src/lib/sync/storage.ts` calls `mkdirSync` only for the `connectorId` level; when `sourceId` contains a slash (e.g., `"acme/repo"`), the intermediate subdirectory is not created, causing ENOENT at runtime. (test: `tests/connectors/tracker-adapter.test.ts`)

6. **`/api/sync/catch-up` returns 500 for all user queries** — Catch-up page posts to this route; the endpoint returns `{"error":"Failed to process catch-up query"}` regardless of input. The Catch-up feature is completely non-functional. (`packages/dashboard/src/app/api/sync/catch-up/`)

7. **Dev server was in a corrupt state due to failed production build** — Running `npm run build` (which failed, Task 1 audit) caused a partial wipe of `.next/server/`, deleting `next-font-manifest.json` and `routes-manifest.json`. The already-running dev server could no longer serve any route (all 500). A dev server restart was required before this API sweep could produce meaningful results.

### P2: Stale or Wrong Data

1. **`/api/metrics/trends` always returns all-zero counts** — The route buckets tasks by `task.metadata.completed_at`. All tasks in the workspace state have `metadata: {}` — no `completed_at` field — so the bucket map is empty and `generateEmptyPoints()` is called instead, producing all-zero rows. Trends are invisible on the Metrics page even when tasks have been completed. (`packages/dashboard/src/app/api/metrics/trends/route.ts`)

2. **`/api/metrics/summary` uses `Math.random()` for trend direction** — `calculateTrend()` simulates historical comparison with random variation: `const variation = (Math.random() - 0.5) * 0.2`. Two identical requests return different trend arrows and percentages. Not suitable for production display. (`packages/dashboard/src/app/api/metrics/summary/route.ts`)

3. **`/api/events/latest` is unauthenticated** — Returns ring buffer snapshot without any auth check. No `withAuth` wrapper in `packages/dashboard/src/app/api/events/latest/route.ts`. Any caller can read all recent events.

4. **`resolveSyncEndpoint` base-path mismatch** (P2, pending investigation) — Returns URLs with `/occc` prefix (the app's `basePath`) where tests expect bare `/api/...` paths. If basePath is applied twice in production, sync requests would 404. Needs investigation to determine if this is test-only or production bug.

5. **Test: `slack-adapter` teardown pollution** — `.tmp` directory is not cleaned up between test runs, causing an `ENOTEMPTY` error on the next run. Flaky test teardown only manifests on consecutive runs. Does not affect production. Classify as CI reliability issue (P2) unless evidence shows it blocks CI.

6. **`/occc/settings` returns 404 — missing root settings page** — `src/app/settings/` has no `page.tsx`. Any link to `/settings` (without a sub-path) produces a Next.js 404. Three sub-pages exist (`/settings/gateway`, `/settings/connectors`, `/settings/privacy`) but the parent route is unroutable. (`packages/dashboard/src/app/settings/`)

7. **Environment page reports Event Bridge as healthy when SSE is broken** — Hard-coded `newStatuses[2].status = 'healthy'` in `src/app/environment/page.tsx` makes Event Bridge always show green, masking the actual SSE ENOENT failure. (`packages/dashboard/src/app/environment/page.tsx`)

### P3: Cosmetic / Minor

1. **`next lint` deprecation warning** — `next lint` will be removed in Next.js 16. Should migrate to direct ESLint CLI invocation.

2. **Auth inconsistency across health sub-routes** — `/api/health/gateway` and `/api/health/memory` have no `withAuth` wrapper; `/api/health/filesystem` does. Gateway port and memory service URL are leaked without authentication. (`packages/dashboard/src/app/api/health/gateway/route.ts`, `packages/dashboard/src/app/api/health/memory/route.ts`)

3. **`/api/health/memory` schema mismatch** — Returns `{"status":"ok"}` but the parent `/api/health` checks `memory.healthy` (boolean) via its own internal `checkMemoryHealth()` call. Two different response shapes for the same conceptual check.

4. **`/api/suggestions` and `/api/graph/ripple-effects` return 400 without required query params** — Both are intentional validations but not documented in any OpenAPI spec or error shape. Dashboard callers must always supply `?project=` and `?id=` respectively or receive a 400.

5. **`/api/config/gateway` has no GET handler** — Only `PATCH` is exported. GET returns 405. If any UI component attempts to read current gateway config, it will fail silently.

6. **Ollama models not available in test environment** — `mxbai-embed-large` and `phi3:mini` are referenced by `src/lib/ollama.ts` but not present locally. Errors are swallowed gracefully, but the indexing and summarization paths are untestable without the models or proper mocks.

7. **`/api/swarm/stream` GET handler uses manual inline auth instead of `withAuth`** — The GET handler in `packages/dashboard/src/app/api/swarm/stream/route.ts` calls `validateToken()` and `createUnauthorizedResponse()` directly in the handler body. All other protected routes in the app use the `withAuth` middleware wrapper. The POST handler in the same file correctly uses `withAuth`. The inconsistency means any future auth policy change applied to `withAuth` (token rotation, rate limiting, audit logging) will silently not apply to the GET SSE stream. Additionally, the GET 400 error body is plain text (`"Container ID is required"`) while all other routes return JSON error objects — inconsistent error shape.

8. **Topology page bypasses `ProjectContext` and reads `localStorage` directly** — `src/app/topology/page.tsx` uses a manual `useEffect` + `localStorage.getItem('occc-project')` pattern instead of calling `useProject()`. The same key `'occc-project'` is used, so there is no functional difference, but the inconsistency means topology will not reactively update if project selection changes mid-session without a re-render. (`packages/dashboard/src/app/topology/page.tsx`)

9. **Environment page: `OPENCLAW_ROOT` always shows "Not set"** — `process.env.OPENCLAW_ROOT` is not prefixed with `NEXT_PUBLIC_`, so it is `undefined` in the browser. The page always displays "Not set" for Project Root. The socket path is also hard-coded to `/tmp/openclaw-events.sock`, which differs from the actual path `$OPENCLAW_ROOT/run/events.sock`. (`packages/dashboard/src/app/environment/page.tsx`)

10. **Catch-up page hard-codes `activeProjectId: 'default'`** — The POST body sent to `/api/sync/catch-up` always contains `activeProjectId: 'default'` regardless of which project is selected in the UI. `useProject()` is not used in this page. (`packages/dashboard/src/app/catch-up/page.tsx`)
