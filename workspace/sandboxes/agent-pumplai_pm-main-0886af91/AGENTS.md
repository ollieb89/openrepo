# Repository Guidelines

## Project Structure & Module Organization

- Turborepo with pnpm workspaces: `apps/web` (Next.js 16, port 3000), `apps/dashboard` (Next.js 16, port 3001), `apps/api` (FastAPI, port 8000).
- Shared packages in `packages/*`: UI kit (`ui`), shared types (`types`), validators (`validators`), AI helpers (`ai`), SDK (`sdk`), monitoring config (`monitoring`), lint/TS bases (`eslint-config`, `typescript-config`).
- Tooling/config: `turbo.json`, `pnpm-workspace.yaml`, `tsconfig.json`, `vitest.config.ts`, `playwright.config.ts`; docs in `docs/`, scripts in `scripts/`, infra in `docker/`.

## Build, Test, and Development Commands

- `pnpm install` (Node 20+), `pnpm dev` (`turbo dev`; scope with `--filter apps/web` or `apps/dashboard`).
- `pnpm build` (`turbo build`), `pnpm lint`, `pnpm format` (Prettier writes `**/*.{ts,tsx,md}`).
- `pnpm test:unit` (Vitest projects), `pnpm test:e2e` / `pnpm test:e2e:ui` (Playwright), `pnpm test:responsive`, `pnpm test:performance:*`, `pnpm test:coverage`.
- `LOW_RESOURCE=true` on any test command to serialize workers and skip coverage for constrained machines.

## Coding Style & Naming Conventions

- TypeScript-first; React components in PascalCase; hooks start with `use`; utilities/tests in `kebab-case` files; co-locate `*.test.ts[x]` or use `__tests__/`.
- Prettier + `@workspace/eslint-config` enforce 2-space indent, import/order rules, and React/Next best practices. Run `pnpm format && pnpm lint` before commits.
- Keep shared UI in `packages/ui`; prefer typed props and Tailwind utilities in apps.

## Testing Guidelines

- Vitest workspace config (`vitest.config.ts`) covers web, dashboard, ui, types, validators, ai; add new projects there if needed.
- E2E lives under Playwright; use headed mode (`pnpm test:e2e:ui`) for debugging and responsive/perf suites under `tests/`.
- Mark slow/flaky tests and note rationale; keep coverage meaningful for changed areas.

## Commit & Pull Request Guidelines

- Commit messages short and imperative, matching current style (e.g., “Refactor code structure for improved readability”, “Fix React Server Components CVE vulnerabilities”); keep scope tight with tests/doc updates.
- PRs: include summary, affected apps/packages, linked issues, screenshots for UI, and call out migrations or breaking changes; confirm lint + unit + relevant Playwright jobs locally.

## Security & Configuration Tips

- Never commit secrets; use `.env.local` per app. Rotate keys shared via secure channels.
- `docker compose up -d` brings Postgres/Redis/API; use `scripts/kill-dev-ports.sh` to clear stuck ports.
- Review `vercel.json` and `railway.*` before deployment changes; avoid broadening CORS/auth without approval.
