# Technology Stack

**Analysis Date:** 2025-02-15

## Languages

**Primary:**
- TypeScript - Core logic, gateway, and plugins in `openclaw/src/`
- JavaScript - Build scripts and configuration in `openclaw/`

**Secondary:**
- Python 3.10+ - Workspace tools, orchestration, and monitoring in `packages/orchestration/` and root
- Swift - macOS and iOS application components in `openclaw/apps/`
- Shell (Bash) - Setup and build scripts

## Runtime

**Environment:**
- Node.js >= 22.12.0
- Python >= 3.10

**Package Manager:**
- pnpm 10.23.0 - TypeScript/JavaScript dependency management
- uv - Python dependency management and workspace handling

## Frameworks

**Core:**
- Express - Web server for gateway and API
- Lit - Frontend component framework for UI
- Agent Client Protocol (ACP) - Standardized agent communication

**Testing:**
- Vitest - TypeScript unit, e2e, and integration testing
- Pytest - Python testing for orchestration logic

**Build/Dev:**
- tsdown / Rolldown - TypeScript bundling
- oxlint / oxfmt - High-performance linting and formatting
- Xcode - For macOS/iOS builds

## Key Dependencies

**Critical:**
- `@agentclientprotocol/sdk` - Core protocol implementation
- `sqlite-vec` - Vector search capabilities for memory
- `@mariozechner/pi-*` - Core agent logic and TUI components
- `zod` / `typebox` - Schema validation

**Infrastructure:**
- `playwright-core` - Browser automation and web understanding
- `sharp` - Image processing
- `baileys` - WhatsApp integration
- `grammy` - Telegram bot framework
- `@slack/bolt` - Slack integration

## Configuration

**Environment:**
- `.env` files for secrets and API keys (managed via `dotenv`)
- `openclaw.json` for primary application configuration

**Build:**
- `package.json`, `tsconfig.json`, `pyproject.toml`, `pnpm-workspace.yaml`

## Platform Requirements

**Development:**
- macOS, Linux, or Windows with Node.js and Python
- Docker/Podman for sandboxed execution and E2E tests

**Production:**
- Node.js runtime environment
- Docker for isolation

---

*Stack analysis: 2025-02-15*
