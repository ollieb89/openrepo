# Structure

## Directory Map
- `src/app/`
- App Router shell and route segments.
- `src/app/layout.tsx` defines global frame (`Sidebar`, `Header`, providers).
- `src/app/page.tsx` redirects root to `/tasks`.
- `src/app/tasks/page.tsx`, `src/app/agents/page.tsx`, `src/app/containers/page.tsx`, `src/app/metrics/page.tsx` are top-level feature screens.
- `src/app/api/`
- Server endpoints organized by domain.
- Task endpoints: `tasks/route.ts`, `tasks/[id]/route.ts`.
- Project endpoints: `projects/route.ts`, `projects/active/route.ts`, `projects/[id]/route.ts`.
- Other endpoints: `agents/route.ts`, `metrics/route.ts`, `snapshots/[taskId]/route.ts`, `swarm/stream/route.ts`.
- `src/components/`
- Reusable UI grouped by feature domain.
- `src/components/tasks/`: `TaskBoard.tsx`, `TaskCard.tsx`, `ActivityLog.tsx`.
- `src/components/agents/`: `AgentTree.tsx`, `AgentCard.tsx`.
- `src/components/metrics/`: chart/stat/skeleton/error widgets.
- `src/components/layout/`: `Sidebar.tsx`, `Header.tsx`.
- `src/components/common/`: generic `Card.tsx`, `StatusBadge.tsx`.
- `src/context/`
- Cross-page client state providers: `ProjectContext.tsx`, `ThemeContext.tsx`.
- `src/lib/`
- Adapters and contracts: `openclaw.ts`, `docker.ts`, `redaction.ts`, `types.ts`.
- `src/lib/hooks/`
- SWR data-access hooks per domain (`useTasks.ts`, `useAgents.ts`, `useMetrics.ts`, `useProjects.ts`, `useContainers.ts`).

## Responsibilities by Folder
- `src/app`: route composition, no heavy domain logic except metrics aggregation route.
- `src/app/api`: HTTP boundary + request parsing + error normalization.
- `src/components`: presentation and interaction logic.
- `src/context`: client app state that must survive route navigation (theme/project).
- `src/lib`: integration logic for OpenClaw files, Docker API, and shared types/redaction.
- `src/lib/hooks`: API call policies (poll intervals, SWR options, endpoint URL construction).

## Naming and Organization Patterns
- Route handlers follow App Router convention `route.ts` and dynamic segment folders like `[id]`, `[taskId]`.
- Page modules are always `page.tsx` under route segment folders.
- Type contracts are centralized in `src/lib/types.ts` and imported by UI, hooks, and APIs.
- Component naming is PascalCase; hooks use `useX` names.
- Import aliasing uses `@/` (configured in `tsconfig.json`) instead of long relative paths.
- Status taxonomy is shared through string literals (`pending`, `starting`, `in_progress`, `testing`, `completed`, `failed`, `rejected`).

## Hotspots for Change
- `src/lib/openclaw.ts`
- High-impact integration point for OpenClaw file paths and JSON schema assumptions.
- Changes here affect `/api/tasks`, `/api/projects`, `/api/metrics`, and `/api/snapshots`.
- `src/lib/docker.ts`
- High-risk area for socket availability, stream parsing, and redaction correctness.
- Affects both container listing and SSE log streaming behavior.
- `src/app/api/metrics/route.ts`
- Business logic hotspot for derived metrics calculations and pool utilization semantics.
- `src/context/ProjectContext.tsx`
- Controls project resolution precedence (localStorage vs server active project); impacts all project-scoped hooks.
- `src/components/agents/AgentTree.tsx`
- Encodes hierarchy rendering and status derivation rules for L1/L2/L3 visualization.
- `src/components/tasks/TaskBoard.tsx`
- Encodes Kanban column mapping (`starting` merged into in-progress column) and detail panel behavior.
- `src/lib/hooks/*.ts`
- Polling cadence and revalidation options are centralized and can alter system load/latency globally.

## Cross-Cutting Notes
- Root configs (`next.config.js`, `tailwind.config.ts`, `postcss.config.js`) define runtime compatibility and styling behavior.
- `src/app/globals.css` holds global typography, scrollbar styling, and transition defaults.
- No explicit test directory exists; quality gates currently rely on lint/manual verification.
