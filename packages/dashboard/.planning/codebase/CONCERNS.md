# CONCERNS

## Evidence Scope
- Review basis: `src/app/api/*`, `src/lib/*`, `src/lib/hooks/*`, and key UI consumers.
- Risk statements below cite concrete file paths and line-level evidence.

## Security Risks
- **[Critical] Unauthenticated internal data exposure across API routes.**
- Evidence: `src/app/api/tasks/route.ts`, `src/app/api/tasks/[id]/route.ts`, `src/app/api/projects/route.ts`, `src/app/api/projects/[id]/route.ts`, `src/app/api/agents/route.ts`, `src/app/api/metrics/route.ts`, `src/app/api/swarm/stream/route.ts` expose data with no authn/authz checks.
- Impact: any reachable client can enumerate projects, agents, task metadata, container names/images/status, and stream logs.
- Mitigation: add shared auth middleware for all `/api/*`, enforce project-scoped authorization, and reject unauthorized container/log access.

- **[High] Path traversal risk from unsanitized route/query params used in filesystem joins.**
- Evidence: `src/lib/openclaw.ts:33-39` (`getProject(id)`), `src/lib/openclaw.ts:50-57` (`getTaskState(projectId)`), `src/lib/openclaw.ts:81-87` (`getSnapshot(projectId, taskId)`) consume external ids directly in `path.join(...)`.
- Impact: crafted ids like `../...` can escape intended directories and read unintended files if extension/path constraints are satisfied.
- Mitigation: validate identifiers with strict allowlist regex (`^[a-zA-Z0-9_-]+$`), normalize+verify prefix stays under allowed root, and reject invalid inputs with 400.

- **[Medium] Sensitive infrastructure metadata is exposed to clients.**
- Evidence: `src/app/api/swarm/stream/route.ts:58-65` returns raw `labels` for each container.
- Impact: labels may reveal internal topology, environment naming, or integration hints.
- Mitigation: return only allowlisted label keys needed by UI (e.g., `openclaw.agent`) and drop all others.

- **[Medium] Redaction is best-effort and easy to bypass.**
- Evidence: `src/lib/redaction.ts` regex-based patterns only; no deterministic secret inventory or structured field policy.
- Impact: false negatives can leak secrets into streamed logs.
- Mitigation: apply structured redaction at source where possible, expand patterns with tests, and support denylist/allowlist config.

## Reliability Risks
- **[High] Docker availability gets permanently latched off after one transient failure.**
- Evidence: `src/lib/docker.ts:17`, `src/lib/docker.ts:23-31` sets `dockerAvailable=false` and never retries in-process.
- Impact: temporary socket issues can cause persistent degraded behavior until app restart.
- Mitigation: replace latch with backoff retry + periodic health recheck window.

- **[High] Error swallowing hides data corruption and outages.**
- Evidence: `src/lib/openclaw.ts:25-27`, `40-42`, `64-66`, `88-89` convert parse/read failures to empty/null without error context.
- Impact: UI shows "no data" indistinguishable from real empty state; incidents become silent.
- Mitigation: return typed error states, log structured error reasons, and expose non-sensitive diagnostics in API responses.

- **[Medium] Hardcoded default active project can route reads to wrong tenant/context.**
- Evidence: `src/lib/openclaw.ts:45-47` defaults to `'pumplai'` when config is missing.
- Impact: accidental cross-project reads and misleading dashboard state.
- Mitigation: fail closed when active project is unavailable; require explicit selection.

## Performance Risks
- **[High] Unbounded in-memory log accumulation in UI.**
- Evidence: `src/components/LogViewer.tsx:45-49` appends every event (`setLogs(prev => [...prev, data])`) with no cap/virtualization.
- Impact: long sessions cause memory growth, frequent rerenders, and UI jank/crashes.
- Mitigation: keep a ring buffer (e.g., last 500-2000 lines), throttle repaint, and virtualize rendering.

- **[Medium] Aggressive polling cadence across multiple SWR hooks.**
- Evidence: `src/lib/hooks/useTasks.ts:10` (3s), `src/lib/hooks/useMetrics.ts:28` (5s), `src/lib/hooks/useContainers.ts:42` (5s).
- Impact: repeated API/file IO and Docker calls even when tabs are idle.
- Mitigation: use focus/visibility-aware revalidation, websocket/SSE where appropriate, and adaptive intervals.

## Maintainability Risks
- **[Medium] API contracts rely on implicit JSON shape with minimal runtime validation.**
- Evidence: `src/lib/openclaw.ts` uses raw `JSON.parse(...)` and casts (`as`) into `Project/Task/Agent` without schema checks.
- Impact: malformed state files produce latent runtime bugs and inconsistent UI behavior.
- Mitigation: validate all loaded JSON with `zod` schemas before returning typed objects.

- **[Low] Duplicate fetcher logic and inconsistent error behavior across hooks.**
- Evidence: repeated `fetch(url).then(res => res.json())` in `src/lib/hooks/useTasks.ts`, `useMetrics.ts`, `useProjects.ts`, `useAgents.ts`, `useContainers.ts`.
- Impact: non-2xx responses are parsed as success payloads; behavior diverges over time.
- Mitigation: centralize fetch utility with status checks, typed errors, and retry policy.

- **[Low] Dead/unused parser function increases cognitive load.**
- Evidence: `src/lib/docker.ts:110-148` (`parseDockerStreamChunk`) is not used by `streamContainerLogs`.
- Impact: maintainers may patch wrong path or miss real parser behavior.
- Mitigation: remove unused function or wire it with tests and single parsing path.

## Operational & Fragility Risks
- **[High] No automated test safety net for API/data parsing/log streaming paths.**
- Evidence: no `*.test.*` or `*.spec.*` files found via repository scan.
- Impact: regressions in parsing, auth, and streaming likely to reach production unnoticed.
- Mitigation: add minimal unit tests for `openclaw` loaders, redaction, docker parser, and route handler integration tests.

- **[Medium] Host-coupled operational dependencies without readiness gating.**
- Evidence: `src/lib/openclaw.ts:5` hard default path `/home/ollie/.openclaw`; `src/lib/docker.ts:13` default docker socket path.
- Impact: environment drift causes runtime failures outside a narrow host setup.
- Mitigation: validate required env/config at startup and expose a health/readiness endpoint.

## Top Priority Mitigation Order
- 1. Add authn/authz guardrails for all API routes, especially log streaming and container listing.
- 2. Block path traversal by validating and canonicalizing all id/path inputs.
- 3. Cap log memory and optimize rendering to prevent client-side degradation.
- 4. Replace Docker availability latch with retry/recovery behavior.
- 5. Introduce schema validation (`zod`) for all filesystem JSON loads.
- 6. Add focused tests around loaders, stream parsing, and redaction behavior.
