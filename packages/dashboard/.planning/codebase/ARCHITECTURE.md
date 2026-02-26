# Architecture

## System Pattern
- Pattern: Next.js 14 App Router monolith with server-side API routes and client-rendered dashboards.
- UI pages under `src/app/*/page.tsx` compose domain components and fetch via browser calls to internal `/api/*` routes.
- Server adapters under `src/lib/openclaw.ts` and `src/lib/docker.ts` isolate filesystem and Docker side effects from route handlers.
- Shared contracts in `src/lib/types.ts` define task, project, agent, metrics, and container payload shapes.
- State synchronization on the client uses SWR polling hooks in `src/lib/hooks/*.ts`.

## Entry Points
- HTML shell and providers: `src/app/layout.tsx`.
- Default route redirect: `src/app/page.tsx` redirects to `/tasks`.
- Feature pages:
- `src/app/tasks/page.tsx` -> `src/components/tasks/TaskBoard.tsx`.
- `src/app/agents/page.tsx` -> `src/components/agents/AgentTree.tsx`.
- `src/app/containers/page.tsx` -> `src/components/ContainerList.tsx` + `src/components/LogViewer.tsx`.
- `src/app/metrics/page.tsx` -> metrics cards/charts + `AgentTree`.

## UI and API Boundaries
- Client/UI boundary: all interactive screens are `"use client"` components under `src/components/**` and `src/app/**/page.tsx`.
- API boundary: Next route handlers under `src/app/api/**/route.ts` expose JSON (and SSE for logs).
- Infrastructure boundary:
- `src/lib/openclaw.ts` reads OpenClaw project/task state from disk (`OPENCLAW_ROOT`, `workspace-state.json`, snapshots).
- `src/lib/docker.ts` reads Docker container state and streams logs from Docker socket.
- Security/redaction boundary: `src/lib/redaction.ts` is applied in `streamContainerLogs` before log lines are emitted to clients.

## Data Flow
- Project selection flow:
- `src/context/ProjectContext.tsx` fetches `/api/projects`, chooses active project from localStorage or server `activeId`.
- `src/components/layout/Header.tsx` updates context and persists `occc-project` in localStorage.
- Tasks flow:
- `useTasks(projectId)` in `src/lib/hooks/useTasks.ts` polls `/api/tasks?project={id}` every 3s.
- `/api/tasks/route.ts` -> `getTaskState(projectId)` in `openclaw.ts` -> filesystem JSON parsing.
- Metrics flow:
- `useMetrics(projectId)` in `src/lib/hooks/useMetrics.ts` polls `/api/metrics?project={id}` every 5s.
- `/api/metrics/route.ts` combines `getTaskState` + `getProject` and computes durations/lifecycle/pool utilization server-side.
- Agent flow:
- `useAgents(projectId)` fetches `/api/agents` once and filters project/global agents client-side.
- Containers flow:
- `useContainers()` POSTs `/api/swarm/stream` every 5s for container list.
- `LogViewer` opens `EventSource('/api/swarm/stream?containerId=...')` for live SSE logs.
- `/api/swarm/stream` GET -> `streamContainerLogs` with abort handling and redaction.

## Key Abstractions
- Context providers:
- `ThemeProvider` (`src/context/ThemeContext.tsx`) controls `dark` class + localStorage theme.
- `ProjectProvider` (`src/context/ProjectContext.tsx`) centralizes selected project state.
- Hook layer (`src/lib/hooks/*.ts`): one hook per domain endpoint (`useTasks`, `useAgents`, `useMetrics`, `useProjects`, `useContainers`).
- Domain renderers:
- Task domain: `TaskBoard`, `TaskCard`, `ActivityLog`.
- Agent domain: recursive `AgentTree` + `AgentCard`.
- Metrics domain: `LifecycleStatCards`, `CompletionBarChart`, `PoolGauge`.
- Adapter layer:
- `openclaw.ts` for OpenClaw filesystem contract.
- `docker.ts` for Docker API contract and stream parsing.

## Runtime and Deployment Notes
- External package support for server components is enabled in `next.config.js` for `dockerode` and `ssh2`.
- API handlers consistently return fallback 500 JSON error bodies on exceptions.
- `tsconfig.json` path alias `@/* -> src/*` is the standard import boundary used across UI and server code.
