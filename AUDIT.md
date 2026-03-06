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

To be filled in Task 3

## SSE / Real-time Issues

To be filled in Task 4

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

6. **Dev server was in a corrupt state due to failed production build** — Running `npm run build` (which failed, Task 1 audit) caused a partial wipe of `.next/server/`, deleting `next-font-manifest.json` and `routes-manifest.json`. The already-running dev server could no longer serve any route (all 500). A dev server restart was required before this API sweep could produce meaningful results.

### P2: Stale or Wrong Data

1. **`/api/metrics/trends` always returns all-zero counts** — The route buckets tasks by `task.metadata.completed_at`. All tasks in the workspace state have `metadata: {}` — no `completed_at` field — so the bucket map is empty and `generateEmptyPoints()` is called instead, producing all-zero rows. Trends are invisible on the Metrics page even when tasks have been completed. (`packages/dashboard/src/app/api/metrics/trends/route.ts`)

2. **`/api/metrics/summary` uses `Math.random()` for trend direction** — `calculateTrend()` simulates historical comparison with random variation: `const variation = (Math.random() - 0.5) * 0.2`. Two identical requests return different trend arrows and percentages. Not suitable for production display. (`packages/dashboard/src/app/api/metrics/summary/route.ts`)

3. **`/api/events/latest` is unauthenticated** — Returns ring buffer snapshot without any auth check. No `withAuth` wrapper in `packages/dashboard/src/app/api/events/latest/route.ts`. Any caller can read all recent events.

4. **`resolveSyncEndpoint` base-path mismatch** (P2, pending investigation) — Returns URLs with `/occc` prefix (the app's `basePath`) where tests expect bare `/api/...` paths. If basePath is applied twice in production, sync requests would 404. Needs investigation to determine if this is test-only or production bug.

5. **Test: `slack-adapter` teardown pollution** — `.tmp` directory is not cleaned up between test runs, causing an `ENOTEMPTY` error on the next run. Flaky test teardown only manifests on consecutive runs. Does not affect production. Classify as CI reliability issue (P2) unless evidence shows it blocks CI.

### P3: Cosmetic / Minor

1. **`next lint` deprecation warning** — `next lint` will be removed in Next.js 16. Should migrate to direct ESLint CLI invocation.

2. **Auth inconsistency across health sub-routes** — `/api/health/gateway` and `/api/health/memory` have no `withAuth` wrapper; `/api/health/filesystem` does. Gateway port and memory service URL are leaked without authentication. (`packages/dashboard/src/app/api/health/gateway/route.ts`, `packages/dashboard/src/app/api/health/memory/route.ts`)

3. **`/api/health/memory` schema mismatch** — Returns `{"status":"ok"}` but the parent `/api/health` checks `memory.healthy` (boolean) via its own internal `checkMemoryHealth()` call. Two different response shapes for the same conceptual check.

4. **`/api/suggestions` and `/api/graph/ripple-effects` return 400 without required query params** — Both are intentional validations but not documented in any OpenAPI spec or error shape. Dashboard callers must always supply `?project=` and `?id=` respectively or receive a 400.

5. **`/api/config/gateway` has no GET handler** — Only `PATCH` is exported. GET returns 405. If any UI component attempts to read current gateway config, it will fail silently.

6. **Ollama models not available in test environment** — `mxbai-embed-large` and `phi3:mini` are referenced by `src/lib/ollama.ts` but not present locally. Errors are swallowed gracefully, but the indexing and summarization paths are untestable without the models or proper mocks.
