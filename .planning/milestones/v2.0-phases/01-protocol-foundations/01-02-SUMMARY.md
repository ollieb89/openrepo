---
phase: 01-protocol-foundations
plan: 02
subsystem: api
tags: [acp, websocket, typescript, vitest, session-management, authentication]

# Dependency graph
requires:
  - phase: 01-01
    provides: ServerAcpTranslator, ACP WebSocket endpoint, session store infrastructure
provides:
  - AcpSessionMeta extended with authProfileId and workspaceDir fields
  - parseSessionMeta parses new fields with canonical + alias key support
  - ServerAcpTranslator.newSession/loadSession apply workspaceDir as cwd and store authProfileId
  - authProfileId propagated to Gateway chat.send handler for credential-scoped requests
affects: [01-03, any-phase-using-acp-sessions, gateway-session-routing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "readString() multi-alias parsing for ACP _meta fields — same pattern as existing sessionKey aliases"
    - "Optional spread for conditional Gateway params: ...(value ? { key: value } : {})"

key-files:
  created: []
  modified:
    - openclaw/src/acp/session-mapper.ts
    - openclaw/src/acp/session-mapper.test.ts
    - openclaw/src/acp/server-translator.ts
    - openclaw/src/acp/server-translator.test.ts
    - openclaw/src/acp/session.ts
    - openclaw/src/acp/types.ts

key-decisions:
  - "workspaceDir in _meta overrides params.cwd — meta takes precedence for workspace isolation"
  - "authProfileId stored on AcpSession and forwarded to chat.send — enables per-session credential scoping without re-parsing _meta on every prompt"
  - "Alias support: authProfile for authProfileId, workspace/dir for workspaceDir — consistent with existing sessionKey/session/key aliases"

patterns-established:
  - "AcpSessionMeta fields use readString() with primary key + aliases — follows existing sessionKey alias pattern"
  - "Session-level context stored on AcpSession, not re-parsed per request — parse once on create/load, use throughout session lifetime"

requirements-completed: [HYB-03]

# Metrics
duration: 3min
completed: 2026-03-04
---

# Phase 01 Plan 02: ACP Metadata Extensions Summary

**AcpSessionMeta extended with authProfileId and workspaceDir for workspace isolation and credential scoping, with full propagation to Gateway session handlers**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-04T12:51:01Z
- **Completed:** 2026-03-04T12:53:48Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extended `AcpSessionMeta` with `authProfileId` (aliases: `authProfile`) and `workspaceDir` (aliases: `workspace`, `dir`) fields
- `ServerAcpTranslator.newSession` and `loadSession` now use `meta.workspaceDir` as the effective cwd and store `authProfileId` on the session
- `authProfileId` forwarded to `chat.send` Gateway dispatch, enabling per-session credential profile targeting

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend ACP Metadata for Orchestration** - `ace7e87` (feat)
2. **Task 2: Apply metadata to Gateway session** - `8c9b568` (feat)

## Files Created/Modified

- `openclaw/src/acp/session-mapper.ts` - Added `authProfileId` and `workspaceDir` to `AcpSessionMeta`; `parseSessionMeta` extracts both with alias support
- `openclaw/src/acp/session-mapper.test.ts` - 8 new tests covering new fields, aliases, null input, combined parsing
- `openclaw/src/acp/server-translator.ts` - `newSession`/`loadSession` apply `workspaceDir` override and store `authProfileId`; `prompt` forwards `authProfileId` to `chat.send`
- `openclaw/src/acp/server-translator.test.ts` - 7 new tests: workspace override, auth profile storage, propagation to chat.send handler
- `openclaw/src/acp/session.ts` - `createSession` accepts and stores optional `authProfileId`
- `openclaw/src/acp/types.ts` - `AcpSession` gains optional `authProfileId` field

## Decisions Made

- `workspaceDir` in `_meta` overrides `params.cwd` — metadata has higher precedence for explicit workspace isolation
- `authProfileId` stored on `AcpSession` and forwarded once per `chat.send` — avoids re-parsing `_meta` on every prompt call
- Alias support (`authProfile`, `workspace`, `dir`) follows the existing `sessionKey`/`session`/`key` alias pattern for consistency

## Deviations from Plan

None — plan executed exactly as written. `sessionKey` was already present in `AcpSessionMeta` from Plan 01; only `authProfileId` and `workspaceDir` were new additions. The session store (`session.ts`) and session type (`types.ts`) required minor supporting changes to propagate `authProfileId` end-to-end, consistent with the plan's intent.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ACP metadata contract complete: `sessionKey`, `authProfileId`, `workspaceDir` all parsed and propagated
- Gateway session creation now workspace-isolated and credential-scoped
- Ready for Phase 01-03 which can rely on `session.authProfileId` being available for routing decisions

---
*Phase: 01-protocol-foundations*
*Completed: 2026-03-04*

## Self-Check: PASSED

- SUMMARY.md: FOUND at .planning/phases/01-protocol-foundations/01-02-SUMMARY.md
- Task 1 commit ace7e8745: FOUND in openclaw submodule
- Task 2 commit 8c9b56825: FOUND in openclaw submodule
- All 29 tests pass (10 session-mapper + 19 server-translator)
