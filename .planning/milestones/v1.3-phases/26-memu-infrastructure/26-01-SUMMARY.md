---
phase: 26-memu-infrastructure
plan: 01
subsystem: infra
tags: [docker, docker-compose, postgresql, pgvector, fastapi, memu-py, python]

# Dependency graph
requires: []
provides:
  - Docker Compose stack definition for openclaw-memory-db (pgvector/pgvector:pg17-bookworm) and openclaw-memory (FastAPI wrapper)
  - Postgres pgvector extension init script with performance tuning
  - Dockerfile (python:3.13-slim-bookworm) ready for Plan 02 application code
  - openclaw-net external bridge network wiring for L2/L3 access
affects:
  - 26-02 (memory service application code — builds on this Dockerfile and Compose)
  - 27-memu-project-scoping (uses memory service via http://localhost:18791)
  - 28-memu-l2-integration (uses memory service URL and network topology)
  - 29-memu-l3-integration (uses openclaw-net to reach openclaw-memory:18791)

# Tech tracking
tech-stack:
  added:
    - pgvector/pgvector:pg17-bookworm (Postgres + pgvector extension, PG17)
    - memu-py[postgres]>=1.4.0 (AI memory library — package name has hyphen, NOT 'memu')
    - fastapi>=0.115.0
    - uvicorn[standard]>=0.30.0
    - python:3.13-slim-bookworm (Docker base image)
  patterns:
    - Docker Compose health-gated boot ordering (depends_on: service_healthy)
    - localhost-only port binding (127.0.0.1:18791:18791, never 0.0.0.0)
    - external named bridge network (openclaw-net) for cross-container DNS
    - numbered shell init scripts (00_init.sh) with set -e + ON_ERROR_STOP=1

key-files:
  created:
    - docker/memory/docker-compose.yml
    - docker/memory/Dockerfile
    - docker/memory/requirements.txt
    - docker/memory/init/00_init.sh
    - docker/memory/.env.example
    - docker/memory/.gitignore
  modified: []

key-decisions:
  - "Port 18791 bound to 127.0.0.1 only — memory service must never expose on public interface"
  - "openclaw-net declared external: true — network pre-created via docker network create openclaw-net before compose up"
  - "pgvector/pgvector:pg17-bookworm chosen for PG17 native vector performance improvements"
  - "Single uvicorn worker specified (--workers 1) — multiple workers would create separate MemUService DB connection pools"
  - "memu-py[postgres] extra pulls psycopg3 (postgresql-psycopgbinary) — DSN must use postgresql+psycopg:// not postgresql+psycopg2://"
  - "Init script is shell (.sh not .sql) to ensure ON_ERROR_STOP=1 prevents silent failures during pgvector setup"

patterns-established:
  - "Memory stack in docker/memory/: Dockerfile + requirements.txt + docker-compose.yml + init/ + .env.example"
  - "Port convention: OpenClaw services use 187xx range (gateway=18789, memory=18791)"
  - "Named volumes for postgres persistence (pgdata:), init scripts mounted to /docker-entrypoint-initdb.d"

requirements-completed: [INFRA-02, INFRA-03]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 26 Plan 01: memU Infrastructure Summary

**Docker Compose stack for PostgreSQL+pgvector (pg17-bookworm) and FastAPI memory service on openclaw-net, with health-gated boot ordering and pgvector init script**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T06:36:00Z
- **Completed:** 2026-02-24T06:38:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Docker Compose defines db (pgvector/pgvector:pg17-bookworm) + memory (FastAPI) services on openclaw-net external network
- Postgres healthcheck (pg_isready) gates memory service startup via depends_on: service_healthy
- Init script 00_init.sh creates pgvector extension and tunes maintenance_work_mem + max_parallel_workers with proper error handling
- Dockerfile built on python:3.13-slim-bookworm with libpq-dev for psycopg3 binary; exposes 18791 with single uvicorn worker
- Port binding locked to 127.0.0.1:18791:18791 (localhost only, never 0.0.0.0)

## Task Commits

Each task was committed atomically:

1. **Task 1: Docker Compose and Postgres infrastructure** - `3a1dd2c` (feat)
2. **Task 2: Dockerfile and requirements.txt** - `a3adbbc` (feat)

## Files Created/Modified
- `docker/memory/docker-compose.yml` - Service definitions: openclaw-memory-db + openclaw-memory on openclaw-net
- `docker/memory/Dockerfile` - python:3.13-slim-bookworm base, libpq-dev, memu-py install, memory_service/ copy
- `docker/memory/requirements.txt` - fastapi, uvicorn[standard], memu-py[postgres] (correct PyPI name with hyphen)
- `docker/memory/init/00_init.sh` - pgvector extension creation + Postgres tuning, executable
- `docker/memory/.env.example` - DB_PASSWORD and OPENAI_API_KEY template
- `docker/memory/.gitignore` - Excludes .env from version control

## Decisions Made
- Port bound to 127.0.0.1:18791:18791 — memory service contains LLM API keys and must not be publicly accessible
- Single uvicorn worker (--workers 1) — memu-py is async-internally; multiple workers create separate MemUService instances with independent DB connection pools, which would break deduplication
- pgvector init script uses shell (not .sql) to ensure `psql -v ON_ERROR_STOP=1` prevents silent extension failures
- libpq-dev installed in Dockerfile — required by psycopg3 binary (psycopgbinary) pulled by memu-py[postgres] extra
- requirements.txt uses `memu-py` (with hyphen) not `memu` (which is a GameBoy emulator on PyPI)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Before running `docker compose up`, the following is required:

1. Create the external network: `docker network create openclaw-net || true`
2. Copy `.env.example` to `.env` and set real values: `cp docker/memory/.env.example docker/memory/.env`
3. Edit `docker/memory/.env` with a secure DB_PASSWORD and valid OPENAI_API_KEY

## Next Phase Readiness

- docker/memory/ infrastructure is complete and ready for Plan 02 to add application code (memory_service/)
- Dockerfile COPY instruction expects `memory_service/` directory — Plan 02 will create this
- No containers started in this plan — building and running happens after application code exists (Plan 02)
- Pre-condition for docker compose up: `docker network create openclaw-net || true` must be run first

## Self-Check: PASSED

All 7 files verified present on disk. Both task commits (3a1dd2c, a3adbbc) confirmed in git log.

---
*Phase: 26-memu-infrastructure*
*Completed: 2026-02-24*
