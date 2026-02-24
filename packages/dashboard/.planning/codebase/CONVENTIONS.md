# Codebase Conventions

## Scope and Evidence
- This document reflects conventions observed in current repository files under `src/` and root config files.
- Primary evidence sources: `package.json`, `tsconfig.json`, `tailwind.config.ts`, and App Router/API files in `src/app/api/`.

## Language, Framework, and Layout
- Stack is TypeScript + React + Next.js App Router (`package.json`, `src/app/layout.tsx`).
- Shared types are centralized in `src/lib/types.ts` and reused across hooks/components/routes.
- `@/*` path alias maps to `src/*` (`tsconfig.json`), and imports use this alias consistently.
- Client components explicitly opt in with `'use client'` (examples: `src/app/tasks/page.tsx`, `src/context/ProjectContext.tsx`).

## Naming and File Conventions
- Components and providers use PascalCase file names and exports (`TaskBoard.tsx`, `ThemeContext.tsx`, `ProjectProvider`).
- Hooks use `useX` naming and live under `src/lib/hooks/` (`useTasks.ts`, `useMetrics.ts`, `useAgents.ts`).
- API routes follow Next.js App Router naming (`route.ts`) in folder-based endpoints (`src/app/api/tasks/route.ts`, `src/app/api/projects/[id]/route.ts`).
- Type names are PascalCase (`Task`, `Project`, `MetricsResponse`), while JSON fields match upstream snake_case where needed (`agent_display_name`, `in_progress`).

## Style and Formatting Patterns
- Code uses 2-space indentation and semicolon-terminated statements across TS/TSX files.
- Import order is typically: framework/third-party first, then `@/` local modules, then types.
- Small inline comments are used to explain non-obvious behavior, especially in infra code (`src/lib/docker.ts`) and API metrics derivation (`src/app/api/metrics/route.ts`).
- Tailwind utility classes are the primary styling mechanism; shared visual mappings use object records (example: `src/components/common/StatusBadge.tsx`).

## Error Handling Patterns
- API routes generally use `try/catch`, log with `console.error`, then return JSON error payloads with status codes.
- Typical failure payload shape is `{ error: 'message' }` with `500` (`src/app/api/tasks/route.ts`, `src/app/api/projects/route.ts`, `src/app/api/metrics/route.ts`).
- Not-found resources are mapped to `404` (`src/app/api/tasks/[id]/route.ts`, `src/app/api/projects/[id]/route.ts`).
- Infrastructure helpers prefer graceful fallbacks over hard failures:
- `getTaskState()` returns `[]` on read/parse failure (`src/lib/openclaw.ts`).
- Docker discovery returns `null`/`[]` when unavailable (`src/lib/docker.ts`).

## State and Data Flow Patterns
- Data fetching uses SWR with polling for near-real-time pages (`refreshInterval` in `useTasks.ts` and `useMetrics.ts`).
- Context providers hold global UI state:
- Project selection and persistence in `src/context/ProjectContext.tsx` using `localStorage` + `/api/projects` bootstrap.
- Theme persistence and `html.dark` toggling in `src/context/ThemeContext.tsx`.
- Pages compose state as `loading -> error -> success` branches (example: `src/app/metrics/page.tsx`).
- API layer transforms filesystem and Docker results into UI-oriented JSON shapes (`src/lib/openclaw.ts`, `src/app/api/swarm/stream/route.ts`).

## Linting and Quality Tooling
- Only lint script configured is `next lint` (`package.json`).
- `npm run lint` currently triggers Next.js ESLint setup prompt because no ESLint config file exists yet.
- ESLint packages are present (`eslint`, `eslint-config-next`) but repository-level rule customization is not yet committed.
- Type safety guardrails are enabled via `"strict": true` and `"noEmit": true` in `tsconfig.json`.

## Practical Convention Baseline
- Keep new API endpoints in App Router `route.ts` files and use consistent JSON error shapes.
- Reuse shared types from `src/lib/types.ts` instead of local duplicate interfaces.
- Continue alias-based imports (`@/...`) and hook naming (`useX`) for discoverability.
- Preserve graceful fallback behavior in infra-dependent code (filesystem and Docker).
