---
phase: 01-protocol-foundations
plan: 01
subsystem: api
tags: [acp, websocket, gateway, typescript, vitest]

# Dependency graph
requires: []
provides:
  - "Native ACP WebSocket endpoint at /v1/acp in Gateway server"
  - "ServerAcpTranslator: in-process ACP-to-Gateway dispatch (no CLI bridge)"
  - "attachAcpWsConnectionHandler: WebSocket lifecycle management for ACP sessions"
  - "E2E test coverage for full ACP initialize → session → prompt → delta flow"
affects: [02-protocol-foundations, acp-clients, gateway-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AcpEnvelope framing: {id, type, sessionId, timestamp, payload} over WebSocket"
    - "Translator pattern: ServerAcpTranslator dispatches to GatewayRequestHandlers directly"
    - "Broadcast patching: context.broadcast wrapped to forward events to ACP translators"
    - "Heartbeat + handshake timeout: 30s ping / 10s initialize timeout per connection"

key-files:
  created:
    - openclaw/src/acp/server-translator.ts
    - openclaw/src/acp/server-translator.test.ts
    - openclaw/src/gateway/server-http.test.ts
    - openclaw/src/gateway/server-acp-ws.ts
    - openclaw/src/gateway/server-acp-ws.test.ts
    - openclaw/test/e2e/server.acp.e2e.test.ts
  modified: []

key-decisions:
  - "ACP endpoint at /v1/acp uses a separate WebSocketServer (acpWss) distinct from main wss — clean separation with no path collision"
  - "ServerAcpTranslator dispatches directly to GatewayRequestHandlers via dispatchRequest — eliminates CLI bridge latency"
  - "context.broadcast is patched (not replaced) so all existing broadcast consumers still receive events while ACP translators also receive them"
  - "E2E tests placed in test/e2e/ as *.e2e.test.ts to match vitest.e2e.config.ts include pattern"
  - "Handshake timeout 10s, heartbeat 30s — matches conventions of existing Gateway WS handlers"

patterns-established:
  - "ACP envelope framing pattern: all WebSocket messages use {id, type, sessionId, timestamp, payload}"
  - "Mock context factory pattern: createMockContext() with vi.fn() stubs for all GatewayRequestContext fields"

requirements-completed: [HYB-01, HYB-02, HYB-04]

# Metrics
duration: 15min
completed: 2026-03-04
---

# Phase 01 Plan 01: Protocol Foundations Summary

**Native ACP WebSocket endpoint at /v1/acp with in-process ServerAcpTranslator dispatch, eliminating the CLI bridge and verified by 25 unit + E2E tests**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-04T12:42:45Z
- **Completed:** 2026-03-04T12:57:00Z
- **Tasks:** 3
- **Files modified:** 6 created

## Accomplishments
- ServerAcpTranslator dispatches ACP messages (initialize, session, prompt, cancel) directly to Gateway internal handlers
- Gateway /v1/acp endpoint routes WebSocket upgrades to dedicated acpWss server with auth gating
- Full ACP protocol E2E flow verified: connection open → initialize → session.new → prompt with streaming → cancel

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ServerAcpAgent for in-process dispatching** - `39859ac38` (feat)
2. **Task 2: Register /v1/acp endpoint in Gateway** - `4108e8359` (feat)
3. **Task 3: Wire ACP translator to WebSocket events** - `0d604409e` (feat)

## Files Created/Modified
- `openclaw/src/acp/server-translator.ts` - ServerAcpTranslator: dispatches ACP protocol messages to internal Gateway handlers
- `openclaw/src/acp/server-translator.test.ts` - 12 unit tests covering initialize, session CRUD, prompt dispatch, streaming, cancel, cleanup
- `openclaw/src/gateway/server-http.test.ts` - 6 unit tests for /v1/acp upgrade routing, auth failure, fallback behavior
- `openclaw/src/gateway/server-acp-ws.ts` - attachAcpWsConnectionHandler: WebSocket lifecycle, envelope framing, heartbeat, handshake timeout
- `openclaw/src/gateway/server-acp-ws.test.ts` - 6 integration tests using a real WebSocket server
- `openclaw/test/e2e/server.acp.e2e.test.ts` - 7 E2E tests: connect, initialize, session.new, prompt with delta streaming, cancel

## Decisions Made
- ACP endpoint uses separate `acpWss` instance (not the main wss) — clean routing in `attachGatewayUpgradeHandler` with `ACP_WS_PATH = "/v1/acp"`
- `context.broadcast` is patched in-place so existing Gateway WS clients are unaffected; ACP translators intercept events via wrap
- E2E tests named `*.e2e.test.ts` and placed in `test/e2e/` to match the `vitest.e2e.config.ts` include pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Vitest config mock needed importOriginal for config module**
- **Found during:** Task 2 (server-http.test.ts)
- **Issue:** Mocking `config.js` without `importOriginal` caused missing `STATE_DIR` export error breaking import chain
- **Fix:** Changed to `vi.mock("../config/config.js", async (importOriginal) => { const actual = await importOriginal(); return { ...actual, loadConfig: mockLoadConfig }; })`
- **Files modified:** `src/gateway/server-http.test.ts`
- **Verification:** All 6 tests pass
- **Committed in:** `4108e8359`

**2. [Rule 1 - Naming] E2E test file renamed to match vitest convention**
- **Found during:** Task 3 verification
- **Issue:** Plan specified `test/e2e/server.acp.test.ts` but vitest e2e config requires `*.e2e.test.ts` pattern
- **Fix:** Named file `server.acp.e2e.test.ts` to match `test/**/*.e2e.test.ts` include glob
- **Files modified:** `test/e2e/server.acp.e2e.test.ts`
- **Verification:** `pnpm vitest run --config vitest.e2e.config.ts test/e2e/server.acp.e2e.test.ts` — 7 tests pass
- **Committed in:** `0d604409e`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - bug/naming)
**Impact on plan:** Both fixes required for tests to run. No scope creep.

## Issues Encountered
- `server-translator.ts` and `server-acp-ws.ts` already existed in the codebase (untracked) — discovered during initial read. Committed as-is after verifying tests pass.

## Next Phase Readiness
- /v1/acp endpoint live; ACP clients can connect and initialize sessions without the CLI bridge
- Ready for Plan 02: additional protocol features or integration with real Gateway handler stack

---
*Phase: 01-protocol-foundations*
*Completed: 2026-03-04*
