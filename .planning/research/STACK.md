# Technology Stack

**Project:** OpenClaw (Grand Architect Protocol)
**Researched:** 2026-02-17

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| OpenClaw | 2026.2.15 | Agentic Orchestration | Multi-agent framework with tiered routing and skill integration. |
| Next.js | 16.1.6 (occc) | Swarm Dashboard | Real-time monitoring and visualization of agent matrix. |
| Gemini API | 2.5 Flash / 3 Pro | LLM Backend | Primary reasoning engines for Tier 1-3 agents. |

### Database & State
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| JSON (Jarvis) | N/A | Shared Swarm State | `state.json` provides low-latency synchronization across isolated containers. |
| PostgreSQL | 16+ | Project Database | Robust relational storage for SaaS projects (PumplAI). |
| Redis | 7+ | Caching | In-memory storage for high-speed project tasks (GeriApp). |

### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Ubuntu | 24.04 LTS | Host OS | Latest kernel support for Nvidia drivers and containerization. |
| Docker / Compose | 27+ | Isolation | Strict sandbox environment for each specialist worker. |
| Bun | 1.3.0 | JS Runtime | High-performance execution for Next.js and specialist tools. |
| Nvidia Toolkit | 550+ drivers | GPU Acceleration | Required for Tier 3 ML specialist (Worker-ML-Eng). |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Tailwind CSS | 4.0 | UI Styling | Standard for the dashboard (occc) frontend. |
| SWR | 2.4.0 | Data Fetching | Polling the `state.json` API route every 2s for "live" feel. |
| Lucide React | 0.572.0 | Icons | Visual cues for agent status and roles in the dashboard. |
| Playwright | Latest | E2E Testing | UI verification via Semantic Snapshots. |
| Pixi | Latest | Env Management | Isolation of Python/ML dependencies. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Runtime | Bun | Node.js (raw) | Bun offers better performance and built-in SQLite/shell tools. |
| Models | Gemini 2.5 | GPT-4o | Gemini provides larger context windows and better integration with CLI tools. |
| Comm | Lane Queues | WebSockets | Queues handle concurrency and persistence better for long-running agent tasks. |

## Installation

```bash
# Core Swarm Setup
bun install -g openclaw-cli
openclaw onboarding

# Dashboard (occc) Setup
cd workspace/occc
bun install
```

## Sources

- `/home/ollie/.openclaw/docs/SWARM_PLAN.md`
- `/home/ollie/.openclaw/workspace/occc/package.json`
- `/home/ollie/.openclaw/openclaw.json`
