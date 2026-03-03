# Codebase Integrations

**Analysis Date: 2026-03-03**

## External Services & APIs

### 1. Messaging Channels
- **WhatsApp (Baileys):**
  - **Package:** `@whiskeysockets/baileys` (v7.0.0-rc.9)
  - **Implementation:** `openclaw/src/web/inbound/monitor.ts`, `openclaw/src/web/session.ts`.
  - **Features:** WebSocket connections, QR code login (`openclaw/src/web/login-qr.ts`), and media processing.
- **Telegram (GrammY):**
  - **Package:** `grammy` (v1.40.0)
  - **Implementation:** `openclaw/src/telegram/bot.ts`, `openclaw/src/telegram/monitor.ts`.
  - **Patterns:** Uses `runner` for long polling and `webhookCallback` for webhooks.
- **Slack (Bolt):**
  - **Package:** `@slack/bolt` (v4.6.0)
  - **Implementation:** `openclaw/src/slack/monitor/provider.ts`.
  - **Features:** Event handling, slash commands, and actions via the Bolt framework.
- **Discord:**
  - **Package:** `discord-api-types`
  - **Implementation:** Native REST/WS implementation.
- **Twitch:**
  - **Package:** `@twurple/api`, `@twurple/chat`
  - **Location:** `openclaw/extensions/twitch/`.
- **Feishu/Lark:**
  - **Package:** `@larksuiteoapi/node-sdk`
  - **Location:** `openclaw/extensions/feishu/`.

### 2. Communication Protocols
- **Agent Client Protocol (ACP):**
  - **Package:** `@agentclientprotocol/sdk` (v0.14.1)
  - **Implementation:** `openclaw/src/acp/server.ts`.
  - **Usage:** Standardized communication between agents and the gateway using `ndJsonStream`.

### 3. AI Providers
- **Anthropic / Gemini / OpenAI:**
  - **Implementation:** Managed via specialized runners in `openclaw/src/agents/`.
  - **Features:** Context window management, tool calling, and response streaming.

### 4. System & Workspace
- **Browser Automation:**
  - **Package:** `playwright-core`
  - **Usage:** Used for web understanding and browser-based tasks.
- **Image Processing:**
  - **Package:** `sharp`
  - **Usage:** Image optimization and manipulation.

## Internal Integrations
- **Vector Search:** `sqlite-vec` provides vector search capabilities for the memory layer.
- **Validation:** `zod` and `typebox` are used for schema validation across API and tool boundaries.

---
*Integrations analysis: 2026-03-03*
