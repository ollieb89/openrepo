# OpenClaw Mission Control Redesign

**Date:** 2026-03-05
**Status:** Approved
**Scope:** Dashboard `packages/dashboard` + Orchestration `packages/orchestration`

## Overview

Redesign the OpenClaw OCCC dashboard into a full mission control UI. Modern SaaS aesthetic (Linear/Vercel-style), dark-mode-first, replacing the current home page with a command center and adding four major capabilities:

1. **Command Center Homepage** — 4-quadrant operational overview
2. **Global Command Bar** (Cmd+K) — system commands + L1/L2 directive chat
3. **Terminal Side Drawer** — live L3 container output in task board
4. **Token & Cost Tracking** — full-stack instrumentation + Usage tab

## What Is NOT Changing

All existing pages remain untouched: topology, memory, agents, containers, escalations, suggestions, decisions, catch-up, environment, settings. The existing sidebar navigation is preserved with one addition (Usage). All existing API endpoints remain unchanged.

---

## 1. Command Center Homepage (`/`)

Replaces `packages/dashboard/src/app/page.tsx` (current: inference preview + privacy consent + recent decisions).

### Layout

Four equal quadrants in a 2×2 responsive grid. Below the grid, a persistent CMD+K hint bar.

```
┌─────────────────────────────────────────────────────────────┐
│  [≡] OpenClaw Mission Control    [pumplai ▾]   ● 3 active   │
│  ─────────────────────────────────────────────────────────  │
│  ┌──────────────────────┬────────────────────────────────┐  │
│  │  SWARM STATUS        │  LIVE EVENT FEED               │  │
│  │  L1 ●────● L2        │  ● task-042 started    2s ago  │  │
│  │       └────● L3 ×3   │  ● task-041 completed  8s ago  │  │
│  │  Pool: ███░ 3/3      │  ● escalation raised   12s ago │  │
│  │  Today: ~$1.24       │  ● L3 spawned task-040  1m ago │  │
│  ├──────────────────────┼────────────────────────────────┤  │
│  │  TASK PULSE          │  ATTENTION QUEUE               │  │
│  │  ▶ task-042 fixing…  │  ⚠ Escalation: confidence 38% │  │
│  │  ▶ task-041 testing… │  ✦ Decision: accept PR?        │  │
│  │  ▶ task-040 writing… │  💡 Suggestion: link to #47   │  │
│  │  + 8 pending         │  [Accept All] [Review]         │  │
│  └──────────────────────┴────────────────────────────────┘  │
│  ── Press CMD+K to send a directive to ClawdiaPrime ─────── │
└─────────────────────────────────────────────────────────────┘
```

### Quadrant: Swarm Status

**Component:** `components/mission-control/SwarmStatusPanel.tsx`

- Agent hierarchy visualization: L1 → L2 → L3 nodes (from `/api/agents`)
- Pool utilization gauge: reuses existing `PoolGauge` component
- Success rate: 30-day sparkline (from `/api/metrics`)
- Cost summary: "Today: ~$X.XX | XM tokens" (from new `/api/metrics/usage`)
- Each agent node links to `/agents`

### Quadrant: Live Event Feed

**Component:** `components/mission-control/LiveEventFeed.tsx`

- Consumes `/api/events` SSE endpoint (existing, with 100-event ring buffer)
- Renders last 50 events with type badges: `task` | `escalation` | `container` | `memory` | `token`
- Auto-scrolls with a "pause scroll" toggle
- Filter chips to show/hide event types
- Clicking an event navigates to the relevant page (e.g., task → `/tasks`)

### Quadrant: Task Pulse

**Component:** `components/mission-control/TaskPulse.tsx`

- Shows currently active L3 tasks (status: `in_progress` | `starting` | `testing`)
- Pulsing green dot per active task
- Task ID + truncated skill hint
- "N pending" count badge
- Clicking any task opens the Task Board with that task's terminal drawer pre-opened
- Data from `/api/tasks`

### Quadrant: Attention Queue

**Component:** `components/mission-control/AttentionQueue.tsx`

- Merged feed of: escalations needing action + pending decisions + unreviewed suggestions
- Sorted by urgency (escalations first, then decisions, then suggestions)
- Inline [Accept] / [Reject] buttons for decisions and suggestions (no navigation)
- [Review] button for escalations (navigates to `/escalations`)
- Data from: `/api/escalations`, `/api/decisions`, `/api/suggestions`

---

## 2. Global Command Bar (Cmd+K)

**Component:** `components/command/CommandBar.tsx`
**Mounted in:** Root layout (`app/layout.tsx`)

### Behavior

- `Cmd+K` (macOS) / `Ctrl+K` (other) opens a centered modal overlay
- Keyboard shortcut registered globally, works on any page
- A "CMD+K" hint button in the homepage footer also opens it

### Input Modes

| Prefix | Mode | Example |
|--------|------|---------|
| `/pause <id>` | System command | `/pause task-042` |
| `/resume <id>` | System command | `/resume task-041` |
| `/cancel <id>` | System command | `/cancel task-040` |
| `/spawn <desc>` | System command | `/spawn write unit tests for auth module` |
| (no prefix) | LLM directive | `prioritize the API fixes for pumplai` |

### System Commands (no LLM)

- `/pause <task-id>` → sends pause message via `POST /api/gateway/directive` with `{ type: "control", action: "pause", taskId }`
- `/resume <task-id>` → calls existing `POST /api/tasks/[id]/resume`
- `/cancel <task-id>` → calls existing `POST /api/tasks/[id]/fail`
- `/spawn <description>` → calls `POST /api/tasks` to create a new pending task

### Natural Language Directives

- Freetext (no `/` prefix) → `POST /api/gateway/directive` with `{ message, projectId }`
- Gateway endpoint proxies to `http://localhost:18789` (openclaw gateway)
- Response streams back inline in the command bar (SSE if gateway supports it, otherwise polling)
- Directive is addressed to the active project's L2 agent

### New API Endpoint

**`POST /api/gateway/directive`**

```typescript
// Request
{ message: string; projectId: string; type?: "control" | "directive" }

// Response (streaming or JSON)
{ status: "sent" | "error"; response?: string }
```

Proxies to the openclaw gateway at `process.env.OPENCLAW_GATEWAY_URL ?? "http://localhost:18789"`.

### UX Details

- Recent commands stored in localStorage (last 5, shown as quick-picks below input)
- Active task IDs auto-completed when typing `/pause `, `/resume `, `/cancel `
- Escape or click outside closes
- Loading spinner while awaiting gateway response

---

## 3. Terminal Side Drawer (`/tasks`)

**Component:** `components/tasks/TerminalDrawer.tsx`
**Modified:** `app/tasks/page.tsx` and `components/tasks/TaskBoard.tsx`

### Trigger

Clicking any in-progress task card (`status: in_progress | starting | testing`) opens the drawer. Clicking a completed/failed task card opens existing task detail (unchanged).

### Layout

Right-side slide-over: 420px wide (resizable with drag handle), full viewport height, slides in over the task board (task board remains usable behind it).

```
[Task Board — still fully visible and interactive]
                        ┌───────────────────────────┐
                        │ ✕ [task-042] [task-041]   │ ← task tabs
                        │ ─────────────────────────  │
                        │ $ openclaw l3 task-042     │
                        │ > Analyzing requirements   │
                        │ > Reading workspace...     │
                        │ > Writing implementation   │
                        │ ▌                          │
                        │ ─────────────────────────  │
                        │ [■ Pause] [✕ Cancel]       │
                        │ [↓ Bottom] [⧉ Fullscreen]  │
                        └───────────────────────────┘
```

### Implementation

- Consumes existing `GET /api/swarm/stream?taskId=<id>` SSE endpoint
- State in `TaskBoard`: `activeTerminalTask: string | null`
- Each active task card shows a "▶ Terminal" button on hover
- Tabs allow switching between active tasks without losing scroll position (each maintains its own scroll + buffer)
- Pause/Cancel buttons call gateway directive API and existing task API respectively
- Fullscreen mode expands to overlay entire viewport

### Existing Component Reuse

`components/tasks/TaskTerminalPanel.tsx` exists and provides the core terminal rendering — `TerminalDrawer` wraps it in the slide-over shell.

---

## 4. Token & Cost Tracking

### Python Instrumentation

**Modified:** `packages/orchestration/src/openclaw/gateway_client.py`
**Modified/Created:** `packages/orchestration/src/openclaw/metrics.py`

#### What Gets Captured

Every LLM API call in `gateway_client.py` captures the usage from the response:

```python
# After each LLM response
token_data = {
    "task_id": current_task_id,
    "agent_id": agent_id,
    "model": model_name,
    "input_tokens": response.usage.input_tokens,
    "output_tokens": response.usage.output_tokens,
    "timestamp": datetime.utcnow().isoformat(),
}
```

This data is:
1. Written to `workspace-state.json` → `token_usage` array (via Jarvis Protocol / `fcntl.flock`)
2. Emitted as a `token_usage` event on the event bridge

#### Cost Calculation

Cost is computed in the Python layer using configurable rates (per model, per 1M tokens). Defaults based on Anthropic published pricing. Configurable via `config/openclaw.json` → `token_rates`.

### New Dashboard API

**`GET /api/metrics/usage`**

```typescript
// Query params: projectId, timeRange (1d|7d|30d), granularity (hour|day)
{
  summary: {
    inputTokens: number;
    outputTokens: number;
    estimatedCost: number;  // USD
    taskCount: number;
  };
  byAgent: Array<{ agentId: string; tokens: number; cost: number }>;
  byTask: Array<{ taskId: string; tokens: number; cost: number }>;
  trend: Array<{ timestamp: string; tokens: number; cost: number }>;
}
```

Reads from `workspace-state.json` → `token_usage` array for the active project.

### Usage Tab in Metrics Page

**Component:** `components/metrics/UsageTab.tsx`
**Modified:** `app/metrics/page.tsx` (add "Usage" tab alongside existing tabs)

Content:
- Summary cards: Total input tokens, total output tokens, estimated cost, cost/task
- Bar chart: daily cost over selected time range
- Agent leaderboard: most expensive agents
- Table: per-task token breakdown (sortable)
- Time range selector: 1D / 7D / 30D (reuses existing `TimeRangeSelector` component)

### Settings Integration

**Modified:** `app/settings/connectors/page.tsx` or new settings section

- Cost rate editor: input box per model name with $/1M tokens value
- Stored in `config/openclaw.json` → `token_rates`
- API: `GET/POST /api/settings/token-rates`

### Homepage Integration

The **Swarm Status** quadrant shows: `Today: ~$1.24 | 2.3M tokens` pulled from `/api/metrics/usage?timeRange=1d`. Displays as a muted secondary line below the pool utilization gauge.

---

## Component Map

| Component | Path | New/Modified |
|-----------|------|-------------|
| `SwarmStatusPanel` | `components/mission-control/SwarmStatusPanel.tsx` | New |
| `LiveEventFeed` | `components/mission-control/LiveEventFeed.tsx` | New |
| `TaskPulse` | `components/mission-control/TaskPulse.tsx` | New |
| `AttentionQueue` | `components/mission-control/AttentionQueue.tsx` | New |
| `CommandBar` | `components/command/CommandBar.tsx` | New |
| `TerminalDrawer` | `components/tasks/TerminalDrawer.tsx` | New |
| `UsageTab` | `components/metrics/UsageTab.tsx` | New |
| `app/page.tsx` | Homepage | Modified (full replace) |
| `app/layout.tsx` | Root layout | Modified (add CommandBar) |
| `app/tasks/page.tsx` | Tasks page | Modified (integrate TerminalDrawer) |
| `app/metrics/page.tsx` | Metrics page | Modified (add Usage tab) |
| `app/api/gateway/directive/route.ts` | Gateway proxy | New |
| `app/api/metrics/usage/route.ts` | Usage metrics | New |
| `app/api/settings/token-rates/route.ts` | Rate config | New |
| `components/layout/Sidebar.tsx` | Navigation | Modified (add Usage item) |

## Python Changes

| File | Change |
|------|--------|
| `openclaw/gateway_client.py` | Capture token usage from LLM responses, write to state + event bridge |
| `openclaw/metrics.py` | Add `get_token_usage()` and `aggregate_usage()` functions |
| `openclaw/cli/config.py` | Add `token_rates` config section |
| `config/openclaw.json` | Add `token_rates` defaults |

---

## Out of Scope

- Redesigning any existing page beyond homepage and the two targeted modifications (tasks, metrics)
- Changing the navigation structure beyond adding "Usage"
- Integrating the separate `openclaw/ui` Lit-based chat — it remains a separate app
- WebSocket upgrade (SSE is sufficient for all current use cases)
- Mobile-responsive redesign (desktop-first)

---

## Implementation Phases

This work should be executed as sequential phases to allow testing at each stage:

1. **Homepage** — New command center (`/`) with 4 quadrants
2. **Command Bar** — Global Cmd+K overlay + gateway directive endpoint
3. **Terminal Drawer** — Side drawer on task board
4. **Token Tracking (Python)** — Instrumentation in orchestration layer
5. **Token Tracking (UI)** — Usage tab + homepage integration
