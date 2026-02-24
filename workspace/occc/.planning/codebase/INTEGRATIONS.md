# INTEGRATIONS

## Integration Overview
- This codebase is primarily an integration layer over local OpenClaw state files and a local Docker Engine.
- External-facing API routes are internal Next.js endpoints under `src/app/api/`.
- Frontend clients call only same-origin routes (e.g. `/api/tasks`, `/api/metrics`, `/api/swarm/stream`).

## OpenClaw Filesystem Integration
- Implemented in `src/lib/openclaw.ts` using `fs/promises` + `path`.
- Reads OpenClaw global config from ``${OPENCLAW_ROOT}/openclaw.json``.
- Enumerates projects from ``${OPENCLAW_ROOT}/projects/*/project.json``.
- Reads task state from ``${OPENCLAW_ROOT}/workspace/.openclaw/<projectId>/workspace-state.json``.
- Reads snapshot diffs from ``${OPENCLAW_ROOT}/workspace/.openclaw/<projectId>/snapshots/<taskId>.diff``.
- Integration is read-only in current code (no writes to OpenClaw files detected).

## Docker Engine Integration
- Implemented in `src/lib/docker.ts` using `dockerode` over Unix socket.
- Socket path is configurable via `DOCKER_SOCKET`, default ``/var/run/docker.sock``.
- Container discovery uses Docker list APIs and label filter `openclaw.managed=true`.
- Container metadata exposes labels like `openclaw.agent` to UI (`src/components/ContainerList.tsx`).
- Live log streaming is implemented server-side and bridged to browser via SSE.
- Log lines are passed through redaction middleware in `src/lib/redaction.ts` before emission.

## Internal API Surface (Network Boundary)
- `GET /api/tasks` and `GET /api/tasks/[id]` read task data from OpenClaw files.
- `GET /api/agents` exposes agent list from OpenClaw config.
- `GET /api/projects`, `GET /api/projects/[id]`, `GET /api/projects/active` expose project data.
- `GET /api/metrics` computes derived metrics from tasks + project concurrency config.
- `GET /api/snapshots/[taskId]` returns diff snapshots.
- `POST /api/swarm/stream` lists managed Docker containers.
- `GET /api/swarm/stream?containerId=...` opens SSE stream for container logs.

## Auth and Access Control Status
- No authentication/authorization middleware is present on API routes.
- No token/session/cookie validation logic is present in `src/app/api/**/route.ts`.
- No role-based checks are enforced before exposing project/task/container data.
- Effective trust boundary is network-level access to this app instance.

## Webhooks and Outbound Calls
- No inbound webhook handlers detected (no signature verification endpoints).
- No outbound HTTP integrations detected from server code (`fetch`, `axios`, SDK clients absent in `src/lib/*` for remote services).
- Browser-side polling uses SWR against same-origin endpoints only.

## Security-Relevant Mechanics
- Redaction attempts to scrub API keys, bearer/JWT-like tokens, passwords, and emails in streamed logs (`src/lib/redaction.ts`).
- Docker availability is probed with graceful fallback (`docker.ping()` cache flag in `src/lib/docker.ts`).
- Error handling generally returns generic `500` JSON payloads from route handlers.

## Infra Dependencies and Assumptions
- Requires filesystem visibility into OpenClaw root tree (default path under user home directory).
- Requires Docker daemon socket permissions for the runtime user.
- Requires long-lived HTTP connection support for SSE log streaming.
- State freshness depends on file snapshots and SWR polling intervals (3s/5s in hooks).

## Missing or Deferred Integrations
- No persistent database integration (Postgres/MySQL/SQLite/Redis absent).
- No external identity provider integration (OAuth/OIDC/SAML absent).
- No queue/stream bus integration (Kafka/RabbitMQ/SQS/NATS absent).
- No observability backend integration (Datadog/Prometheus exporter/OpenTelemetry SDK absent).
- `ssh2` is listed in `next.config.js` external packages but not imported in current `src/` code.
