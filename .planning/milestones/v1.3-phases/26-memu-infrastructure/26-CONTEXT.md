# Phase 26: memU Infrastructure - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the memory service stack: a custom FastAPI wrapper around memu-py running in Docker alongside PostgreSQL+pgvector, with verified cold-start initialization, a working REST API (memorize, retrieve, list, delete, health), and Docker networking so both L2 (host) and L3 (containers) can reach the service.

</domain>

<decisions>
## Implementation Decisions

### Service Deployment
- Custom FastAPI wrapper around memu-py — NOT the pre-built nevamindai/memu-server image (avoids unknown Temporal dependency)
- Self-contained in `docker/memory/` directory: Dockerfile (python:3.13-slim-bookworm base), requirements.txt, memory_service/ app code, docker-compose.yml
- Port 18791 (follows OpenClaw's 187xx convention, next after gateway 18789)
- Container name: `openclaw-memory` (service) and `openclaw-memory-db` (postgres)

### Database Setup
- Image: `pgvector/pgvector:pg17-bookworm` — pg17 for native vector performance improvements
- Extension init via numbered shell script `00_init.sh` (not .sql) to prevent silent failures
- Init script includes: `CREATE EXTENSION IF NOT EXISTS vector`, `ALTER SYSTEM SET maintenance_work_mem = '128MB'`, `max_parallel_workers_per_gather = 4` for parallel vector operations
- Credentials: `POSTGRES_DB=openclaw_memory`, `POSTGRES_USER=claw_admin`, `POSTGRES_PASSWORD=${DB_PASSWORD}` from .env
- Named volume `pgdata` for persistence across restarts
- Healthcheck: `pg_isready -U claw_admin -d openclaw_memory` (interval 5s, retries 5)
- Schema managed by memu-py via `ddl_mode='create'` — auto-provisions tables on first connect
- Boot ordering: `depends_on` with `service_healthy` condition — memU service waits for postgres

### Network Topology
- Named bridge network: `openclaw-net` (created via `docker network create openclaw-net || true`)
- L2 (host-side Python) reaches memU via `http://localhost:18791` (port mapped with `127.0.0.1:18791:18791` for security)
- L3 containers reach memU via Docker DNS: `http://openclaw-memory:18791` (auto-joined to openclaw-net at spawn time by spawn.py)
- spawn.py adds `--network openclaw-net` when creating L3 containers — no manual network config needed
- MEMU_SERVICE_URL env var injected into L3 containers at spawn time
- Optional: service alias `memory.local` for semantic URL readability

### LLM Provider Config
- Extraction LLM: OpenAI GPT-4o-mini (Claude's discretion on exact model — fast, cheap, well-tested with memU prompts)
- Embedding model: OpenAI text-embedding-3-small (1536 dimensions, $0.02/1M tokens)
- API key via `docker/memory/.env` file (in .gitignore) — passed through Docker Compose env_file directive
- Async extraction: memorize() runs as FastAPI BackgroundTask — returns 202 Accepted immediately, processes in background
- Temperature 0.0 for extraction (strict fact extraction, no creative output)

### Claude's Discretion
- Exact FastAPI app structure (routers, middleware, error handling)
- Pydantic request/response models for API endpoints
- uvicorn configuration (workers, host, port)
- Exact memu-py MemoryService initialization parameters beyond what's specified
- Logging integration (should follow existing get_logger() pattern from orchestration layer)

</decisions>

<specifics>
## Specific Ideas

- Docker Compose port binding must use `127.0.0.1:18791:18791` — never expose on public interface
- Init script pattern from user: `set -e`, `psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"`
- After startup, verify pgvector with: `docker compose logs db | grep "extension \"vector\""`
- L2 config should detect environment: `IS_DOCKER = os.path.exists('/.dockerenv')` to switch between localhost and DNS endpoints
- `restart: unless-stopped` on the memory service container

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-memu-infrastructure*
*Context gathered: 2026-02-24*
