# Codebase Architecture

**Analysis Date: 2026-03-03**

## Overview

The codebase follows a **Modular Plugin-based Gateway** architecture with **Multi-agent Orchestration**. The system is designed to be highly decoupled, event-driven, and extensible through a robust plugin system.

## Key Layers

### 1. CLI Layer
- **Entry Point:** `openclaw/src/index.ts`
- **Command Management:** Uses a lazy-loading command registry in `openclaw/src/cli/program/command-registry.ts` to manage various CLI commands.

### 2. Gateway Layer
- **Core Server:** `openclaw/src/gateway/server.impl.ts`
- **Responsibilities:** Acts as the central hub for all communication. It handles HTTP and WebSocket connections, routes messages, and manages sessions.
- **Plugin Registry:** Uses `openclaw/src/plugins/loader.ts` to dynamically discover and load extensions from `extensions/*` and bundled paths.

### 3. Agent Layer
- **Core Logic:** `openclaw/src/agents/` and the top-level `agents/` directory.
- **Execution:** The `pi-embedded-runner.ts` manages the lifecycle of agent runs, including context window management (`context-window-guard.ts`) and tool dispatching.
- **Providers:** Supports various providers (Anthropic, Gemini, etc.) through specialized runners.

### 4. Agent Control Protocol (ACP)
- **Implementation:** `openclaw/src/acp/`
- **Purpose:** Provides a standardized way for agents and clients to communicate with the gateway, using `AgentSideConnection` and `ndJsonStream`.

## Data Flow
1. **Inbound:** Messages from various channels (Telegram, Slack, WhatsApp, etc.) are received by the Gateway.
2. **Routing:** The Gateway routes the messages to the appropriate Agent runner.
3. **Execution:** The Agent runner uses tools (`pi-tools.ts`) to interact with the system, memory, or external APIs.
4. **Outbound:** Responses are sent back through the Gateway to the originating channel.

## Persistence
- Managed via `packages/memory` and SQLite databases located in the `memory/` directory.

---
*Architecture analysis: 2026-03-03*
