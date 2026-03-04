# Phase 1: Protocol Foundations - Research

**Researched:** 2026-03-03
**Domain:** Agent Client Protocol (ACP) & OpenClaw Gateway Integration
**Confidence:** HIGH

## Summary
The primary goal is to shift ACP from an external bridge to a native Gateway capability. The Gateway already has a robust WebSocket infrastructure. Implementing `/v1/acp` requires path-based routing in the WebSocket upgrade handler and the integration of the existing ACP message translation logic into the Gateway's runtime state.

**Primary recommendation:** Reuse the existing `translator.ts` and `event-mapper.ts` logic from `src/acp/` but integrate them as a native `GatewayWsHandler` that responds to the `/v1/acp` path.

<user_constraints>
## User Constraints (from ROADMAP.md & REQUIREMENTS.md)

### Locked Decisions
- **Task 1.1:** Promote ACP to a native Gateway feature in `server.impl.ts`.
- **Task 1.2:** Implement `/v1/acp` WebSocket endpoint.
- **Task 1.3:** Extend session metadata mapping for `authProfileId` and `workspaceDir`.
- **Task 1.4:** Verify ACP-to-Gateway communication via standardized SDK.
- **HYB-01:** Integrate ACP (Agent Client Protocol) as a native Gateway server endpoint (`/v1/acp`).
- **HYB-02:** Support `@agentclientprotocol/sdk` for standard ACP messages.
- **HYB-04:** Implement `AcpGatewayAgent` directly within `server.impl.ts` for low-latency communication.

### Claude's Discretion
- Implementation details of the metadata mapping in `_meta` fields.
- Structural organization of the ACP handler within the Gateway's source tree.

### Deferred Ideas (OUT OF SCOPE)
- Intent-based routing (Phase 2).
- Multi-role swarm collaboration (Phase 3).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HYB-01 | Integrate ACP as a native Gateway server endpoint (`/v1/acp`). | Identified `server-ws-runtime.ts` and `ws-connection.ts` as the primary integration points for WebSocket path routing. |
| HYB-02 | Support `@agentclientprotocol/sdk` for standard ACP messages. | Confirmed dependency exists in `openclaw/package.json` and is already used in the `src/acp/` bridge. |
| HYB-03 | Extend ACP `_meta` fields for OpenClaw session metadata. | Confirmed ACP supports `_meta` in its protocol; mapped target fields to existing `GatewayWsClient` properties. |
| HYB-04 | Implement `AcpGatewayAgent` for low-latency communication. | Researched `server.impl.ts` to understand how to register new core handlers. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@agentclientprotocol/sdk` | 0.14.1 | Protocol handling | Official SDK for ACP implementation. |
| `ws` | 8.19.0 | WebSocket Server | Core Gateway transport library. |

## Architecture Patterns

### Recommended Project Structure
```
openclaw/src/
├── acp/             # Existing ACP logic (to be reused)
│   ├── translator.ts
│   ├── event-mapper.ts
│   └── ...
└── gateway/
    ├── server-acp.ts # NEW: ACP-specific handlers and session management
    ├── server.impl.ts
    └── ...
```

### Pattern 1: Path-Based WebSocket Routing
The Gateway's `httpServer.on('upgrade')` in `server-http.ts` needs to be modified to check `req.url`. Currently, it handles all upgrades via `wss.handleUpgrade`. It should distinguish between the default Gateway protocol and `/v1/acp`.

### Pattern 2: ACP-to-Gateway Translation
The native implementation should reuse the `translator.ts` logic that converts ACP `prompt` to Gateway `chat.send` and Gateway events back to ACP `message`/`tool_call`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ACP Message Validation | Custom JSON-RPC validation | `@agentclientprotocol/sdk` | Handles protocol nuances and future spec updates. |
| JSON-RPC 2.0 Transport | Custom framing | Existing `src/acp/translator.ts` | Already handles mapping OpenClaw events to ACP responses. |

## Common Pitfalls

### Pitfall 1: Session Mapping Collisions
**What goes wrong:** External ACP bridge sessions and native ACP sessions might use overlapping ID spaces.
**How to avoid:** Ensure native ACP sessions are prefixed or namespaced (e.g., `native-acp:<id>`) in the session registry.

### Pitfall 2: Auth Verification
**What goes wrong:** ACP clients often connect from IDEs with different header capabilities than standard browsers.
**How to avoid:** Reuse `authorizeGatewayConnect` in `server-http.ts` but ensure it correctly handles the ACP `initialize` handshake if tokens are passed there.

## Code Examples

### Suggested Metadata Extension (HYB-03)
```typescript
// Based on ACP spec for _meta in initialize/newSession
const openClawMeta = {
  sessionKey: "agent:main:default",
  authProfileId: "user-123",
  workspaceDir: "/home/user/project"
};
```

## Open Questions
1. **Bridge Deprecation:** Should the external `openclaw acp` bridge be deprecated immediately or coexist?
   - *Recommendation:* Keep it for backward compatibility but point it to the new native endpoint for better performance.

## Sources
- `openclaw/docs.acp.md` (High Confidence)
- `openclaw/src/gateway/server.impl.ts` (High Confidence)
- `openclaw/package.json` (High Confidence)
- `openclaw/src/acp/translator.ts` (Medium Confidence - Interrupted)

---
*Note: This research was finalized under a tool-call limit constraint; however, the architectural path for Phase 1 is well-defined by existing codebase patterns.*
