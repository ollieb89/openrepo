# STACK

## Runtime and Platform
- Framework: Next.js App Router application in `src/app/`.
- Runtime target: Node.js server runtime for API routes (uses `fs/promises` and Docker socket access).
- UI runtime: React 18 client/server components (`'use client'` in interactive files).
- Type system: TypeScript with strict mode enabled in `tsconfig.json`.
- Port conventions: dev and prod server are pinned to `6987` via `package.json` scripts.

## Languages and Syntax
- TypeScript/TSX across app logic and UI: e.g. `src/app/metrics/page.tsx`, `src/lib/docker.ts`.
- JavaScript config files at repo root: `next.config.js`, `postcss.config.js`.
- CSS via Tailwind + global stylesheet: `src/app/globals.css`.
- Markdown/meta docs in workspace: `AGENTS.md`, planning docs under `.planning/`.

## Core Frameworks and Libraries
- `next@14.2.5` for routing, API handlers, and rendering.
- `react@18` and `react-dom@18` for UI.
- `swr` for polling/fetch state in hooks (`src/lib/hooks/useTasks.ts`, `useMetrics.ts`, `useContainers.ts`).
- `tailwindcss`, `postcss`, `autoprefixer` for styling pipeline.
- `recharts` for metrics visualization components under `src/components/metrics/`.
- `dockerode` for Docker Engine socket integration in `src/lib/docker.ts`.
- `zod` is present in dependencies but no active imports found in `src/`.
- `react-toastify` is installed but no active imports found in `src/`.

## Build, Dev, and Quality Commands
- `npm run dev` -> `next dev -p 6987`.
- `npm run build` -> `next build`.
- `npm run start` -> `next start -p 6987`.
- `npm run lint` -> `next lint`.
- No test script is defined in `package.json`.

## Configuration Surface
- Next config: `next.config.js` enables `experimental.serverComponentsExternalPackages` for `dockerode` and `ssh2`.
- TS config: `tsconfig.json` uses `moduleResolution: "bundler"`, path alias `@/* -> ./src/*`, `strict: true`.
- Tailwind config: `tailwind.config.ts` defines class-based dark mode and custom status colors (`pending`, `in-progress`, `testing`, etc.).
- PostCSS config: `postcss.config.js` loads Tailwind + Autoprefixer plugins.

## App and API Topology
- Page routes: `src/app/tasks/page.tsx`, `src/app/metrics/page.tsx`, `src/app/agents/page.tsx`, `src/app/containers/page.tsx`.
- Root redirect: `src/app/page.tsx` redirects `/` to `/tasks`.
- API endpoints live in `src/app/api/**/route.ts`.
- Data access layer is concentrated in `src/lib/openclaw.ts` and `src/lib/docker.ts`.

## Environment and Local Dependencies
- `OPENCLAW_ROOT` env var controls OpenClaw filesystem root (default `/home/ollie/.openclaw`) in `src/lib/openclaw.ts`.
- `DOCKER_SOCKET` env var controls Docker socket path (default `/var/run/docker.sock`) in `src/lib/docker.ts`.
- App expects OpenClaw state files such as ``/workspace/.openclaw/<project>/workspace-state.json`` and project configs under ``/projects/<id>/project.json``.
- App expects Docker daemon/socket availability for container listing and log streaming features.
