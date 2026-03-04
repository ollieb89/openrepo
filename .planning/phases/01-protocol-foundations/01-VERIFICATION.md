---
phase: 01-protocol-foundations
verified: 2026-03-04T12:57:14Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 01: Protocol Foundations Verification Report

**Phase Goal:** Shift ACP from an external bridge to a native Gateway capability with /v1/acp WebSocket endpoint, session metadata extensions (authProfileId, workspaceDir), and integration tests.
**Verified:** 2026-03-04T12:57:14Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Gateway accepts WebSocket upgrades on /v1/acp | VERIFIED | `ACP_WS_PATH = "/v1/acp"` exported from `server-http.ts` L628; `attachGatewayUpgradeHandler` routes pathname to `acpWss` at L646 |
| 2 | ACP clients can connect and initialize sessions without the 'openclaw acp' bridge | VERIFIED | `ServerAcpTranslator` dispatches directly to `GatewayRequestHandlers` via `dispatchRequest()` — no CLI bridge call anywhere in translator |
| 3 | ACP messages are dispatched to internal Gateway handlers with minimal latency | VERIFIED | `dispatchRequest()` in `server-translator.ts` L306-344 calls `this.handlers[method]` in-process, returning a Promise resolved by the handler's `respond` callback |
| 4 | IDE clients can resume existing sessions using the sessionKey metadata field | VERIFIED | `parseSessionMeta` in `session-mapper.ts` reads `["sessionKey", "session", "key"]` aliases; `loadSession` in `server-translator.ts` L141-158 applies it |
| 5 | Workspace isolation and authentication context are correctly applied to native ACP sessions | VERIFIED | `meta.workspaceDir` overrides `params.cwd` in both `newSession` and `loadSession`; `meta.authProfileId` stored on `AcpSession` and forwarded to `chat.send` at L230 |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `openclaw/src/acp/server-translator.ts` | Internal ACP-to-Gateway translation logic | VERIFIED | 487 lines, substantive — `ServerAcpTranslator` class with `initialize`, `newSession`, `loadSession`, `listSessions`, `prompt`, `cancel`, `handleGatewayEvent`, `dispatchRequest` all fully implemented |
| `openclaw/src/gateway/server-http.ts` | /v1/acp endpoint routing | VERIFIED | `ACP_WS_PATH` constant + `attachGatewayUpgradeHandler` routes to `acpWss` with auth gating via `authorizeGatewayConnect` at L649 |
| `openclaw/src/gateway/server-acp-ws.ts` | WebSocket lifecycle management for ACP sessions | VERIFIED | 256 lines — `attachAcpWsConnectionHandler` handles connection open, heartbeat, handshake timeout, envelope routing to all ACP message types, cleanup |
| `openclaw/src/acp/session-mapper.ts` | ACP-to-Gateway metadata mapping for orchestration | VERIFIED | `AcpSessionMeta` type includes `authProfileId` and `workspaceDir` with aliases; `parseSessionMeta` extracts all fields via `readString` helper |
| `openclaw/src/acp/server-translator.test.ts` | Unit tests for ServerAcpTranslator | VERIFIED | 520 lines, includes tests for workspaceDir override, authProfileId storage and propagation to `chat.send` |
| `openclaw/src/gateway/server-http.test.ts` | Unit tests for /v1/acp upgrade routing | VERIFIED | 207 lines present |
| `openclaw/src/gateway/server-acp-ws.test.ts` | Integration tests for ACP WebSocket lifecycle | VERIFIED | 271 lines present |
| `openclaw/src/acp/session-mapper.test.ts` | Unit tests for metadata parsing | VERIFIED | Tests for `authProfileId`, `authProfile` alias, `workspaceDir`, `workspace`/`dir` aliases, null input, combined parsing |
| `openclaw/test/e2e/server.acp.e2e.test.ts` | E2E tests for full ACP flow | VERIFIED | 476 lines — tests: connect, initialize handshake, session.new, prompt with final event, delta streaming, pre-init rejection, cancel + cancel.ack |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `openclaw/src/gateway/server-http.ts` | `openclaw/src/acp/server-translator.ts` | WebSocket connection handling | WIRED | `server-http.ts` exports `ACP_WS_PATH`; `server-acp-ws.ts` imports `ServerAcpTranslator` and instantiates it on connection; `server.impl.ts` wires both via `attachAcpWsConnectionHandler` |
| `openclaw/src/acp/session-mapper.ts` | `openclaw/src/acp/server-translator.ts` | Session initialization context propagation | WIRED | `server-translator.ts` L39 imports `parseSessionMeta` from `session-mapper.js`; called in `newSession` L126, `loadSession` L146, and `prompt` L204 |
| `openclaw/src/gateway/server-acp-ws.ts` | `openclaw/src/gateway/server.impl.ts` | Runtime wiring | WIRED | `server.impl.ts` L78 imports `attachAcpWsConnectionHandler`; called at L593-600 with `coreGatewayHandlers` and runtime context |
| `openclaw/src/gateway/server-runtime-state.ts` | `openclaw/src/gateway/server-http.ts` | acpWss WebSocketServer creation | WIRED | `server-runtime-state.ts` L164 creates `new WebSocketServer({ noServer: true })` for ACP; exported in runtime state object |

---

### Requirements Coverage

The HYB-xx requirements are defined in the phase RESEARCH file (`01-RESEARCH.md`) and not in the project-wide `REQUIREMENTS.md` (which tracks v2.0 Structural Intelligence requirements only). This is expected — the phase RESEARCH file serves as the local requirements registry for this phase.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HYB-01 | 01-01-PLAN.md | Integrate ACP as a native Gateway server endpoint (`/v1/acp`) | SATISFIED | `ACP_WS_PATH = "/v1/acp"` in `server-http.ts`, routing live in `attachGatewayUpgradeHandler` |
| HYB-02 | 01-01-PLAN.md | Support `@agentclientprotocol/sdk` for standard ACP messages | SATISFIED | `@agentclientprotocol/sdk@0.14.1` in `openclaw/package.json`; `PROTOCOL_VERSION`, `InitializeRequest`, `PromptRequest` etc. all imported from SDK in `server-translator.ts` |
| HYB-03 | 01-02-PLAN.md | Extend ACP `_meta` fields for OpenClaw session metadata | SATISFIED | `AcpSessionMeta` has `authProfileId` and `workspaceDir` with alias support; propagated through session lifecycle and to `chat.send` |
| HYB-04 | 01-01-PLAN.md | Implement `AcpGatewayAgent` for low-latency communication | SATISFIED | Implemented as `ServerAcpTranslator` with direct `dispatchRequest` to `GatewayRequestHandlers` — no CLI bridge |

**Note on REQUIREMENTS.md:** The main `.planning/REQUIREMENTS.md` does not reference HYB-xx IDs. These requirements exist only in the phase's own RESEARCH file. No orphaned requirements detected — all four HYB IDs claimed in the PLAN frontmatter are defined and satisfied.

---

### Anti-Patterns Found

No blocking anti-patterns detected. Scan results:

- `return {}` at `server-translator.ts` L158, L245, L256 — valid ACP protocol empty-object responses (`LoadSessionResponse`, early return on missing modeId, `SetSessionModeResponse`), not stubs.
- No `TODO`, `FIXME`, `XXX`, `HACK`, or `PLACEHOLDER` comments in any phase-created file.
- No console-only implementations or empty handlers.

---

### Human Verification Required

None. All observable truths are verifiable from the codebase. The test suite (25+ tests across unit, integration, and E2E) covers the full ACP protocol flow. No external service integration or visual UI was introduced in this phase.

---

### Gaps Summary

No gaps. All five observable truths are verified at all three levels (exists, substantive, wired). All four phase requirements (HYB-01 through HYB-04) are satisfied. All artifacts are present and substantive. All key links are wired.

The phase goal — "shift ACP from an external bridge to a native Gateway capability with /v1/acp WebSocket endpoint, session metadata extensions (authProfileId, workspaceDir), and integration tests" — is fully achieved.

**Commit verification:**
- `39859ac38` — ServerAcpTranslator (Task 1, Plan 01)
- `4108e8359` — /v1/acp routing and tests (Task 2, Plan 01)
- `0d604409e` — E2E wiring (Task 3, Plan 01)
- `ace7e8745` — metadata extensions (Task 1, Plan 02)
- `8c9b56825` — metadata propagation (Task 2, Plan 02)

All 5 commits confirmed present in `openclaw` submodule git log.

---

_Verified: 2026-03-04T12:57:14Z_
_Verifier: Claude (gsd-verifier)_
