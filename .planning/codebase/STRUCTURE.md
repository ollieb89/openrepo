# Codebase Structure

**Analysis Date: 2026-03-03**

## Directory Map

### Core Source (`openclaw/src/`)
- `acp/`: Types and clients for the Agent Control Protocol.
- `agents/`: Implementation of the AI agent "soul," including runners and tool implementations.
- `gateway/`: Core server implementation, session management, and plugin hooks.
- `plugins/`: Infrastructure for discovery, loading, and isolation of plugins.
- `plugin-sdk/`: Shared types and utilities for plugin development.
- `utils/`: Common utility functions used across the TypeScript codebase.

### Monorepo Packages (`packages/`)
- `dashboard/`: UI components and logic for the management dashboard.
- `memory/`: Core persistence and vector search logic.
- `orchestration/`: Logic for managing and coordinating multiple agents.

### Agent Implementations (`agents/`)
- `clawdia_prime/`: Specific agent implementation.
- `main/`: The primary agent logic.
- `python_backend_worker/`: Specialized Python-based worker agents.
- `_templates/`: Scaffolding for new agents.

### Other Key Directories
- `extensions/`: Additional functionality like BlueBubbles, Twitch, and Feishu integrations.
- `skills/`: Reusable capabilities that agents can utilize.
- `config/`: Configuration management and example files.
- `memory/`: Storage for SQLite databases used by the agents.
- `tests/` & `test/`: Unit, integration, and E2E test suites.

## Notable Files
- `openclaw/src/index.ts`: Main CLI entry point.
- `openclaw/src/gateway/server.impl.ts`: Gateway server implementation.
- `openclaw/src/plugins/loader.ts`: Plugin loading logic.
- `package.json`: Project dependencies and scripts.
- `pnpm-workspace.yaml`: Monorepo configuration.

---
*Structure analysis: 2026-03-03*
