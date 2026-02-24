# Testing Posture

## Current Status (Evidence-Based)
- There is no dedicated automated test framework configured in the repository today.
- `package.json` scripts include `dev`, `build`, `start`, and `lint`; no `test` script is defined.
- Dependency list does not include Jest, Vitest, Playwright, Cypress, Testing Library, or test runners.
- Search for common test patterns in `src/` returns no `*.test.*`, `*.spec.*`, or `__tests__` files.
- Running `npm run lint` currently opens Next.js interactive ESLint setup, indicating no committed ESLint config yet.

## Quality Signals That Exist
- TypeScript strict mode is enabled (`tsconfig.json`: `"strict": true`), which catches many structural errors early.
- App routes use defensive `try/catch` and explicit status codes (`src/app/api/tasks/route.ts`, `src/app/api/metrics/route.ts`).
- Error/empty/loading states are present in UI code (`src/app/metrics/page.tsx`, `src/components/tasks/TaskBoard.tsx`).
- Log redaction logic is isolated in `src/lib/redaction.ts`, which is a good candidate for first unit tests.

## Manual Test Strategy (Current Practical Approach)
- Because there is no automated suite, validation should be scenario-driven across key pages and APIs.
- Start local app with `npm run dev` (port `6987`) and validate:
- `/tasks` for live task polling, empty state, and task detail panel (`src/app/tasks/page.tsx`, `src/components/tasks/TaskBoard.tsx`).
- `/metrics` for loading, error retry, and chart/gauge rendering (`src/app/metrics/page.tsx`).
- `/agents` and `/containers` pages for data presence and resilience during backend unavailability.
- Exercise API endpoints directly:
- `/api/projects`, `/api/projects/active`, `/api/tasks`, `/api/metrics` for 200 responses and payload shape.
- `/api/tasks/[id]` and `/api/projects/[id]` for not-found behavior (`404` branch).
- `/api/swarm/stream` for missing `containerId` (`400`) and stream lifecycle handling.
- Validate cross-cutting behaviors:
- Theme persistence in `localStorage` (`src/context/ThemeContext.tsx`).
- Project selection persistence and filtering (`src/context/ProjectContext.tsx`, `src/lib/hooks/useAgents.ts`).

## Key Gaps
- No unit tests for pure logic (metrics aggregation in `src/app/api/metrics/route.ts`, redaction regexes in `src/lib/redaction.ts`).
- No integration tests for API endpoints and status/error contracts.
- No end-to-end coverage for major user journeys (`/tasks`, `/metrics`, `/containers`).
- No CI gate for lint/typecheck/build/test to prevent regressions before merge.
- Lint is not currently non-interactive in fresh clones due missing ESLint config file.

## Recommended Next Steps (Priority Order)
- 1) Commit an ESLint config so `npm run lint` is deterministic and CI-safe.
- 2) Add a `test` script and lightweight unit framework (Vitest preferred for TS speed).
- 3) Add first unit test targets:
- `src/lib/redaction.ts` (token/email/API-key masking cases and false positives).
- Metrics derivation helpers extracted from `src/app/api/metrics/route.ts`.
- 4) Add API integration tests for core routes and status-code expectations.
- 5) Add minimal Playwright smoke tests for `/tasks` and `/metrics` happy path + error path.
- 6) Add CI pipeline stages: lint, typecheck, build, unit tests, and optional e2e smoke job.

## Definition of Done for Improved Posture
- `npm run lint` runs without setup prompts.
- `npm run test` exists and executes at least core unit coverage.
- Core API routes have contract checks for success and failure modes.
- At least one browser-level smoke test verifies critical dashboard flows.
