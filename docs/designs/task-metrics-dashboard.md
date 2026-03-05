# Design: OpenClaw Task Metrics Dashboard

## Status
Approved → Ready for Planning

## Context
The OpenClaw orchestration system tracks tasks across projects, but lacks visibility into productivity metrics, bottlenecks, and trends. Project managers and developers need a dashboard to understand task completion rates, cycle times, and agent performance.

## Goals
- Provide at-a-glance visibility into task completion rates and trends
- Enable per-agent performance tracking and comparison
- Support time-based analysis (7/30/90 day views)
- Surface bottlenecks via WIP counts and failure rates
- Offer exportable task lists for further analysis

## Non-Goals
- Real-time WebSocket updates (Phase 2)
- Cost/token tracking overlay (Phase 2)
- Automated alerting on failure spikes (Phase 2)
- SLA/overdue tracking (Phase 2)
- Multi-gateway trust boundary support (out of scope)

## Proposal

### Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard UI (Next.js)                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ KPI     │  │ Charts  │  │ Leader  │  │ Task Table      │ │
│  │ Cards   │  │         │  │ board   │  │                 │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (Next.js API)                   │
│  /api/metrics/summary    - Current aggregates                │
│  /api/metrics/trends     - Time-series data                  │
│  /api/metrics/agents     - Per-agent stats                   │
│  /api/metrics/tasks      - Filtered task list                │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources                              │
│  workspace-state.json      - Current task state              │
│  analytics.db (SQLite)     - Historical snapshots/events     │
└─────────────────────────────────────────────────────────────┘
```

### Component Specifications

#### 1. KPI Cards (Top Row)
Five metric cards with trend indicators:

| Metric | Calculation | Format |
|--------|-------------|--------|
| Completion Rate | `completed / (completed + failed + pending + in_progress)` | Percentage with ↑↓ trend |
| Throughput | Count of tasks completed in period | Integer (# tasks) |
| Median Cycle Time | Median of `(completed_at - created_at)` for done tasks | Duration (e.g., "2h 15m") |
| WIP Count | Current `in_progress` + `starting` + `testing` | Integer |
| Failure Rate | `failed / (completed + failed)` | Percentage |

#### 2. Trend Charts

**Line Chart: Completion Rate & Throughput Over Time**
- X-axis: Date (daily buckets)
- Y-axis (left): Completion rate % (0-100)
- Y-axis (right): Throughput count
- Toggle: Daily / Weekly / Monthly aggregation

**Stacked Area Chart: Status Distribution**
- X-axis: Date
- Y-axis: Task count
- Series: pending, in_progress, completed, failed (stacked)

#### 3. Agent Leaderboard

**Bar Chart: Per-Agent Metrics**
- Agents sorted by throughput (descending)
- Bars: Tasks completed
- Secondary metric: Median cycle time (dot/line overlay)
- Click to drill down to agent-specific task list

#### 4. Task Data Table

**Columns:**
- Task ID
- Title (truncated)
- Agent
- Status (with badge)
- Created at
- Completed at (if applicable)
- Cycle time (calculated)

**Features:**
- Filter by: agent, status, date range
- Sort by: any column
- CSV export button
- Pagination (25/50/100 per page)

#### 5. Time Range Selector

**Quick Picks:**
- Last 7 days
- Last 30 days
- Last 90 days
- All time (with "since YYYY-MM-DD" label)

**Custom:**
- Date picker (from → to)

### Data Model

#### Current State (from workspace-state.json)
```typescript
interface Task {
  id: string;
  title: string;
  status: 'pending' | 'starting' | 'in_progress' | 'testing' | 'completed' | 'failed' | 'rejected';
  agent_id?: string;
  created_at: number;  // Unix timestamp
  updated_at: number;
  completed_at?: number;
  metadata?: {
    autonomy?: {
      escalation_reason?: string;
    };
  };
}

interface WorkspaceState {
  tasks: Record<string, Task>;
  project_id: string;
}
```

#### Historical Analytics (SQLite)
```sql
-- Daily snapshots for fast trend queries
CREATE TABLE daily_snapshots (
  date TEXT PRIMARY KEY,
  project_id TEXT,
  pending_count INTEGER,
  in_progress_count INTEGER,
  completed_count INTEGER,
  failed_count INTEGER,
  completed_today INTEGER,
  median_cycle_time_seconds INTEGER
);

-- Per-agent daily stats
CREATE TABLE agent_daily_stats (
  date TEXT,
  project_id TEXT,
  agent_id TEXT,
  tasks_completed INTEGER,
  tasks_failed INTEGER,
  median_cycle_time_seconds INTEGER,
  PRIMARY KEY (date, project_id, agent_id)
);

-- Event log for accurate cycle time (optional event model)
CREATE TABLE task_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT,
  project_id TEXT,
  event_type TEXT,  -- 'created', 'started', 'completed', 'failed'
  agent_id TEXT,
  timestamp INTEGER,
  metadata TEXT  -- JSON
);
```

### API Endpoints

```typescript
// GET /api/metrics/summary?project=pumplai&days=30
interface MetricsSummary {
  completion_rate: number;  // 0-1
  throughput: number;       // count
  median_cycle_time_ms: number;
  wip_count: number;
  failure_rate: number;     // 0-1
  period: {
    start: string;  // ISO date
    end: string;
  };
}

// GET /api/metrics/trends?project=pumplai&days=30&granularity=daily
interface MetricsTrends {
  dates: string[];  // ISO dates
  completion_rates: number[];
  throughputs: number[];
  status_distribution: {
    pending: number[];
    in_progress: number[];
    completed: number[];
    failed: number[];
  };
}

// GET /api/metrics/agents?project=pumplai&days=30
interface AgentMetrics {
  agents: Array<{
    agent_id: string;
    tasks_completed: number;
    tasks_failed: number;
    median_cycle_time_ms: number;
    completion_rate: number;
  }>;
}

// GET /api/metrics/tasks?project=pumplai&status=&agent=&start=&end=&page=&limit=
interface TaskListResponse {
  tasks: Array<Task & { cycle_time_ms?: number }>;
  total: number;
  page: number;
  limit: number;
}
```

### Implementation Approach

#### Phase 1: MVP (Current Scope)
1. **Current State Only**: Parse `workspace-state.json` for all metrics
2. **Calculate trends client-side**: Compare current state vs. synthetic "old" state (if available)
3. **Simple aggregations**: No historical database needed

#### Phase 2: Historical Trends (Future)
1. **Snapshot Model**: Daily cron job writes aggregate counts to SQLite
2. **Event Model**: Hook into task transitions to append events

### UI/UX Specifications

#### Layout
```
┌──────────────────────────────────────────────────────────────┐
│  Task Metrics Dashboard                    [Project Selector] │
├──────────────────────────────────────────────────────────────┤
│  [7d] [30d] [90d] [All] [Custom Range ▼]                     │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │Complete │ │Throughput│ │Cycle   │ │   WIP   │ │ Failure │ │
│  │  87% ↑  │ │  42     │ │ 2h 15m │ │   5    │ │  3%  ↓  │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌───────────────────────────┐ │
│  │ Completion Rate +        │  │   Status Distribution     │ │
│  │ Throughput Trend         │  │   (stacked area)          │ │
│  │       [Line Chart]       │  │                           │ │
│  └──────────────────────────┘  └───────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Agent Leaderboard                                        │ │
│  │ [Bar chart: tasks completed per agent]                   │ │
│  └──────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Task Details                                    [Export] │ │
│  │ [Filter ▼] [Agent ▼] [Status ▼]                    [↻] │ │
│  │ ┌──────────┬────────┬────────┬─────────┬───────────────┐ │ │
│  │ │ Task ID  │ Title  │ Agent  │ Status │ Cycle Time    │ │ │
│  │ └──────────┴────────┴────────┴─────────┴───────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### Design System
- Use existing dashboard components (Card, Button, Select, etc.)
- Charts: Recharts (already in dependencies)
- Color coding:
  - Completed: green
  - In progress: blue
  - Failed: red
  - Pending: gray

### Performance Considerations
- Parse workspace-state.json once per request (cache for 30s)
- Client-side pagination for task table
- Debounce filter inputs (300ms)

### Testing Strategy
- Unit tests for metric calculations
- API route tests with mock workspace state
- Component tests for chart rendering
- E2E: Verify dashboard loads with real project data

## Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Current state only** (MVP) | Simple, no DB needed | No historical trends | ✅ MVP |
| **Snapshot model** (Phase 2) | Fast queries, simple | Loses intra-day detail | Future |
| **Event model** (Phase 2) | Accurate cycle time, replay | More complex, larger storage | Future |

## Open Questions
1. Should we persist analytics data in SQLite or JSONL?
2. Do we need authentication/authorization on metrics endpoints?
3. Should the dashboard be accessible at `/occc/metrics` or `/occc/analytics`?

## Implementation Phases

### Phase 1 (MVP) - This Design
- [ ] KPI cards from current state
- [ ] Status breakdown chart
- [ ] Per-agent leaderboard
- [ ] Task table with filters
- [ ] Time range selector (7/30/90 days)

### Phase 2 (Future)
- [ ] Historical trend database
- [ ] Real-time updates via SSE
- [ ] Failure taxonomy analysis
- [ ] SLA/overdue tracking
- [ ] Automated alerts

---

**Next Step:** Create implementation plan (Phase 1 tasks)
