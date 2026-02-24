# Repository Guidelines

## Project Structure & Module Organization
- Core application code lives in `src/`.
- Route handlers and pages use Next.js App Router under `src/app/` (for example, `src/app/api/tasks/route.ts`, `src/app/metrics/page.tsx`).
- Reusable UI components are organized in `src/components/` by domain (`agents/`, `metrics/`, `tasks/`, `layout/`, `common/`).
- Shared logic, hooks, and utilities live in `src/lib/` and `src/context/`.
- Configuration is at the repo root (`next.config.js`, `tailwind.config.ts`, `tsconfig.json`, `postcss.config.js`).

## Build, Test, and Development Commands
- `npm run dev` starts the local dev server on port `6987`.
- `npm run build` creates a production build.
- `npm run start` serves the production build on port `6987`.
- `npm run lint` runs ESLint via Next.js rules.

Use `rg --files src` to inspect structure and `rg "pattern" src` to navigate quickly.

## Coding Style & Naming Conventions
- Language stack: TypeScript + React (Next.js 14).
- Follow existing formatting in touched files; use 2-space indentation and keep imports grouped logically.
- Components and context providers use PascalCase (`TaskBoard.tsx`, `ProjectContext.tsx`).
- Hooks use `useX` naming (`useTasks.ts`, `useMetrics.ts`).
- Keep route files named `route.ts` in App Router API folders.
- Prefer small, focused modules and colocate domain UI in the matching subfolder.

## Testing Guidelines
- There is no dedicated test framework configured yet.
- At minimum, run `npm run lint` before opening a PR.
- For behavior changes, manually verify affected pages and API endpoints (for example `/tasks`, `/metrics`, `/api/tasks`).
- If you add tests, colocate them clearly (e.g., `*.test.ts[x]`) and document the command in `package.json`.

## Commit & Pull Request Guidelines
- This repository currently has no commit history; adopt Conventional Commits going forward (e.g., `feat: add task filter`, `fix: handle metrics fetch timeout`).
- Keep commits scoped to one concern.
- PRs should include: what changed, why, manual verification steps, and screenshots for UI changes.
- Link related issues/tasks and call out any follow-up work explicitly.

## Security & Configuration Tips
- Do not commit secrets; use environment variables for sensitive values.
- Be cautious when changing Docker or API integration code in `src/lib/docker.ts` and `src/lib/openclaw.ts`.
