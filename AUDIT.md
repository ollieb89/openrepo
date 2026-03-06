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

To be filled in Task 2

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

2. **Test: `sync-engine` checkpoint persistence is broken** — `loadCheckpoint` returns `undefined` after a save. Any feature relying on resumable sync will silently fail. (`packages/dashboard/src/lib/sync/storage.ts`; test: `tests/sync/sync-engine.test.ts`)

3. **Test: `tracker-adapter` — sourceId slash causes ENOENT** — `saveSyncRecords` in `packages/dashboard/src/lib/sync/storage.ts` calls `mkdirSync` only for the `connectorId` level; when `sourceId` contains a slash (e.g., `"acme/repo"`), the intermediate subdirectory is not created, causing ENOENT at runtime. (test: `tests/sync/tracker-adapter.test.ts`)

### P2: Stale or Wrong Data

1. **`resolveSyncEndpoint` base-path mismatch** (P2, pending investigation) — Returns URLs with `/occc` prefix (the app's `basePath`) where tests expect bare `/api/...` paths. If basePath is applied twice in production, sync requests would 404. Needs investigation to determine if this is test-only or production bug.

2. **Test: `slack-adapter` teardown pollution** — `.tmp` directory is not cleaned up between test runs, causing an `ENOTEMPTY` error on the next run. Flaky test teardown only manifests on consecutive runs. Does not affect production. Classify as CI reliability issue (P2) unless evidence shows it blocks CI.

### P3: Cosmetic / Minor

1. **`next lint` deprecation warning** — `next lint` will be removed in Next.js 16. Should migrate to direct ESLint CLI invocation.

2. **Ollama models not available in test environment** — `mxbai-embed-large` and `phi3:mini` are referenced by `src/lib/ollama.ts` but not present locally. Errors are swallowed gracefully, but the indexing and summarization paths are untestable without the models or proper mocks.
