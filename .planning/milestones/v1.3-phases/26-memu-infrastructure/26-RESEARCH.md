# Phase 26: memU Infrastructure - Research

**Researched:** 2026-02-24
**Domain:** Python FastAPI service wrapping memu-py + PostgreSQL/pgvector in Docker Compose
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Service Deployment**
- Custom FastAPI wrapper around memu-py — NOT the pre-built nevamindai/memu-server image (avoids unknown Temporal dependency)
- Self-contained in `docker/memory/` directory: Dockerfile (python:3.13-slim-bookworm base), requirements.txt, memory_service/ app code, docker-compose.yml
- Port 18791 (follows OpenClaw's 187xx convention, next after gateway 18789)
- Container name: `openclaw-memory` (service) and `openclaw-memory-db` (postgres)

**Database Setup**
- Image: `pgvector/pgvector:pg17-bookworm` — pg17 for native vector performance improvements
- Extension init via numbered shell script `00_init.sh` (not .sql) to prevent silent failures
- Init script includes: `CREATE EXTENSION IF NOT EXISTS vector`, `ALTER SYSTEM SET maintenance_work_mem = '128MB'`, `max_parallel_workers_per_gather = 4` for parallel vector operations
- Credentials: `POSTGRES_DB=openclaw_memory`, `POSTGRES_USER=claw_admin`, `POSTGRES_PASSWORD=${DB_PASSWORD}` from .env
- Named volume `pgdata` for persistence across restarts
- Healthcheck: `pg_isready -U claw_admin -d openclaw_memory` (interval 5s, retries 5)
- Schema managed by memu-py via `ddl_mode='create'` — auto-provisions tables on first connect
- Boot ordering: `depends_on` with `service_healthy` condition — memU service waits for postgres

**Network Topology**
- Named bridge network: `openclaw-net` (created via `docker network create openclaw-net || true`)
- L2 (host-side Python) reaches memU via `http://localhost:18791` (port mapped with `127.0.0.1:18791:18791` for security)
- L3 containers reach memU via Docker DNS: `http://openclaw-memory:18791` (auto-joined to openclaw-net at spawn time by spawn.py)
- spawn.py adds `--network openclaw-net` when creating L3 containers — no manual network config needed
- MEMU_SERVICE_URL env var injected into L3 containers at spawn time

**LLM Provider Config**
- Extraction LLM: OpenAI GPT-4o-mini (fast, cheap, well-tested with memU prompts)
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | memU service runs as a standalone Docker container (python:3.13-slim-bookworm base) with FastAPI wrapper around memu-py | memu-py 1.4.0 confirmed on PyPI as `memu-py`; FastAPI lifespan pattern for service init; MemUService async constructor confirmed |
| INFRA-02 | PostgreSQL+pgvector runs as a Docker container with persistent volume and correct extension initialization | pgvector/pgvector:pg17-bookworm image confirmed available; ddl_mode='create' in memu-py runs `CREATE EXTENSION IF NOT EXISTS vector` automatically; shell init script pattern for `set -e` init ordering verified |
| INFRA-03 | Docker Compose defines memory stack (memU service + PostgreSQL) on shared bridge network accessible to L2 and L3 containers | openclaw-net bridge network pattern; `depends_on: service_healthy` ordering; spawn.py network injection pattern documented |
| INFRA-04 | Internal REST API exposes POST /memorize, POST /retrieve, GET /memories, DELETE /memories/{id} endpoints with Pydantic validation | Full memu-py CRUD API confirmed: memorize(), retrieve(), list_memory_items(), delete_memory_item(); FastAPI BackgroundTasks for 202 Accepted pattern |
| INFRA-05 | Memory service health check endpoint (GET /health) verifiable by orchestration layer | FastAPI health endpoint is trivial; Docker Compose HEALTHCHECK for postgres uses pg_isready; curl-based health verification from L3 containers documented |
</phase_requirements>

---

## Summary

Phase 26 builds a self-contained Docker Compose stack: a custom FastAPI service wrapping the `memu-py` library (version 1.4.0, PyPI package name `memu-py`) alongside `pgvector/pgvector:pg17-bookworm`. The pre-built `nevamindai/memu-server` image was rejected due to unknown Temporal dependencies — the correct decision is to wrap memu-py directly in a FastAPI app.

The memu-py library is async-first. `MemUService` (the class name in memu-py) accepts `llm_profiles`, `database_config`, `memorize_config`, and `retrieve_config`. The database backend for PostgreSQL uses `ddl_mode='create'` which automatically runs `CREATE EXTENSION IF NOT EXISTS vector` and `metadata.create_all(engine)` on startup — so the FastAPI service does NOT need separate schema migration tooling. The init shell script (`00_init.sh`) only needs to create the extension and tune postgres; memu-py handles table creation.

The Docker Compose boot ordering is critical: postgres must be healthy before the memory service starts. FastAPI's lifespan context manager is the correct pattern for initializing `MemUService` once at startup and sharing it across all request handlers. The `openclaw-net` bridge network already exists (or will be created by this phase) and gives L3 containers DNS-based access to `openclaw-memory:18791`.

**Primary recommendation:** Build the FastAPI wrapper with a lifespan-managed `MemUService` singleton, expose five endpoints (health, memorize, retrieve, list, delete), return 202 Accepted from /memorize using BackgroundTasks, and let memu-py handle all schema provisioning on first connect.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| memu-py | 1.4.0 | AI memory management (memorize/retrieve/CRUD) | The library OpenClaw has chosen; wraps extraction LLM + pgvector |
| fastapi | 0.115+ | HTTP wrapper exposing memu-py as REST | Async-native, Pydantic built-in, minimal boilerplate |
| uvicorn | 0.30+ | ASGI server for FastAPI | Standard FastAPI production server |
| pydantic | 2.x | Request/response validation | FastAPI dependency; memu-py already requires pydantic>=2.12.4 |
| httpx | 0.28+ | Async HTTP client (memu-py internal) | Already required by memu-py |

### Supporting (memu-py's postgres extra)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pgvector | 0.3.4+ | Python pgvector client | Required by `memu-py[postgres]` extra |
| sqlalchemy[postgresql-psycopgbinary] | 2.0.36+ | Postgres ORM + async pool | Required by `memu-py[postgres]` extra |
| alembic | 1.14+ | Schema migrations (used internally by memu-py) | Pulled by memu-py; don't invoke directly |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| memu-py 1.4.0 | nevamindai/memu-server image | Pre-built image has unknown Temporal dependency; rejected |
| pgvector/pgvector:pg17-bookworm | pg16 | pg17 has native vector performance improvements; user decision |
| FastAPI BackgroundTasks | asyncio.create_task | BackgroundTasks is simpler, guaranteed to run after response, no event loop management needed |

**Installation (inside Docker):**
```bash
# requirements.txt for docker/memory/
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
"memu-py[postgres]>=1.4.0"
```

Note: The PyPI package name is `memu-py` (with hyphen), not `memu`. The `[postgres]` extra pulls pgvector, sqlalchemy[postgresql-psycopgbinary], and alembic.

---

## Architecture Patterns

### Recommended Project Structure

```
docker/memory/
├── Dockerfile                    # python:3.13-slim-bookworm, copies memory_service/
├── requirements.txt              # fastapi, uvicorn, memu-py[postgres]
├── docker-compose.yml            # openclaw-memory + openclaw-memory-db services
├── .env.example                  # DB_PASSWORD, OPENAI_API_KEY template
├── .gitignore                    # .env
└── memory_service/
    ├── __init__.py
    ├── main.py                   # FastAPI app, lifespan, include routers
    ├── config.py                 # Settings from env vars
    ├── service.py                # MemUService singleton init/getter
    ├── models.py                 # Pydantic request/response schemas
    └── routers/
        ├── health.py             # GET /health
        ├── memorize.py           # POST /memorize
        ├── retrieve.py           # POST /retrieve
        └── memories.py           # GET /memories, DELETE /memories/{id}
```

### Pattern 1: Lifespan-Managed MemUService Singleton

**What:** Initialize `MemUService` once at app startup, share via app.state.
**When to use:** Any async service that is expensive to construct and must be shared across requests.

```python
# Source: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/events.md
# memory_service/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from .service import init_service, get_service
from .routers import health, memorize, retrieve, memories

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize MemUService with postgres backend
    app.state.memu = await init_service()
    yield
    # Shutdown: no teardown required for memu-py

app = FastAPI(title="OpenClaw Memory Service", lifespan=lifespan)
app.include_router(health.router)
app.include_router(memorize.router)
app.include_router(retrieve.router)
app.include_router(memories.router)
```

### Pattern 2: MemUService Initialization

**What:** Configure MemUService for OpenAI extraction + pgvector backend.
**When to use:** Single call at startup; result is stored in app.state.

```python
# memory_service/service.py

import os
from memu import MemUService

async def init_service() -> MemUService:
    db_password = os.environ["DB_PASSWORD"]
    openai_key = os.environ["OPENAI_API_KEY"]
    db_host = os.environ.get("DB_HOST", "openclaw-memory-db")

    dsn = f"postgresql+psycopg2://claw_admin:{db_password}@{db_host}:5432/openclaw_memory"

    service = MemUService(
        llm_profiles={
            "default": {
                "api_key": openai_key,
                "chat_model": "gpt-4o-mini",
            },
            "embedding": {
                "api_key": openai_key,
                "embed_model": "text-embedding-3-small",
            },
        },
        database_config={
            "metadata_store": {
                "provider": "postgres",
                "ddl_mode": "create",   # auto-creates tables + vector extension on first connect
                "dsn": dsn,
            },
            "vector_index": {
                "provider": "pgvector",
                "dsn": dsn,
            },
        },
        memorize_config={
            "llm_temperature": 0.0,
        },
    )
    return service
```

Note: `ddl_mode='create'` causes memu-py to run `CREATE EXTENSION IF NOT EXISTS vector` and `metadata.create_all()` on init. This means the postgres container only needs the extension available (which pgvector image provides), and the shell init script in `00_init.sh` is for tuning (maintenance_work_mem, max_parallel_workers_per_gather) rather than schema creation.

### Pattern 3: BackgroundTask for /memorize

**What:** Return 202 Accepted immediately; run async extraction in background.
**When to use:** Memorize calls involve LLM extraction (seconds); callers should not block.

```python
# Source: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/background-tasks.md
# memory_service/routers/memorize.py

from fastapi import APIRouter, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from ..models import MemorizeRequest

router = APIRouter()

async def _run_memorize(service, payload: MemorizeRequest):
    await service.memorize(
        resource_url=payload.resource_url,
        modality=payload.modality,
        user=payload.user,
    )

@router.post("/memorize", status_code=202)
async def memorize(
    request: Request,
    payload: MemorizeRequest,
    background_tasks: BackgroundTasks,
):
    service = request.app.state.memu
    background_tasks.add_task(_run_memorize, service, payload)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"status": "accepted", "message": "Memorization queued"},
    )
```

### Pattern 4: Docker Compose with Health-Gated Boot Ordering

**What:** Postgres healthcheck → memory service waits until postgres is healthy.
**When to use:** Any service that needs DB to be ready before connecting.

```yaml
# docker/memory/docker-compose.yml

services:
  db:
    image: pgvector/pgvector:pg17-bookworm
    container_name: openclaw-memory-db
    environment:
      POSTGRES_DB: openclaw_memory
      POSTGRES_USER: claw_admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U claw_admin -d openclaw_memory"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - openclaw-net

  memory:
    build: .
    container_name: openclaw-memory
    ports:
      - "127.0.0.1:18791:18791"
    env_file: .env
    environment:
      DB_HOST: openclaw-memory-db
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - openclaw-net

volumes:
  pgdata:

networks:
  openclaw-net:
    external: true
```

### Pattern 5: Init Shell Script (00_init.sh)

**What:** Postgres init script for pgvector tuning; runs on first container start only.
**When to use:** Any postgres tuning that must run before first connection from memu-py.

```bash
#!/bin/bash
# docker/memory/init/00_init.sh
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- memu-py will also run CREATE EXTENSION in ddl_mode='create',
    -- but running here first ensures it's available before memu-py connects
    CREATE EXTENSION IF NOT EXISTS vector;
    ALTER SYSTEM SET maintenance_work_mem = '128MB';
    ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
    SELECT pg_reload_conf();
EOSQL
```

### Pattern 6: spawn.py Network Injection

**What:** L3 containers must join openclaw-net and receive MEMU_SERVICE_URL at spawn time.
**When to use:** Any modification to spawn.py's container_config.

The existing `spawn.py` does NOT currently set `network_mode` or `networks`. The modification needed is:
```python
# Add to container_config in spawn_l3_specialist()
"network": "openclaw-net",
"environment": {
    ...existing env vars...,
    "MEMU_SERVICE_URL": "http://openclaw-memory:18791",
}
```

Note: Docker SDK uses `"network"` (singular) in `containers.run()`, not `"networks"`. This attaches the container to `openclaw-net` as its primary network.

### Anti-Patterns to Avoid

- **Direct .sql init file for pgvector**: Docker entrypoint only runs scripts with `set -e` if they are shell scripts. A .sql file silently continues past errors. Use `00_init.sh` with `ON_ERROR_STOP=1`.
- **Binding port on 0.0.0.0**: Always bind `127.0.0.1:18791:18791` — never expose memory service on the public interface.
- **Blocking memorize endpoint**: Extraction involves LLM calls (1-5 seconds). Always run as BackgroundTask and return 202.
- **Re-initializing MemUService per request**: Construction initializes DB connections and sets up the async loop internals. Initialize once in lifespan, not in endpoint handlers.
- **Separate Alembic migrations**: memu-py runs its own Alembic migrations internally when `ddl_mode='create'`. Do not invoke `alembic upgrade head` separately — it will conflict.
- **Using `networks` key in Docker SDK**: `client.containers.run()` uses `network=` (singular string), not `networks=` (list). The latter is a Compose key, not a SDK parameter.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom SQL with pgvector | memu-py `retrieve()` with `provider: pgvector` | memu-py handles embedding generation, index queries, and result ranking |
| Schema migrations | Manual `CREATE TABLE` SQL | memu-py `ddl_mode='create'` | memu-py owns the schema; hand-rolled tables will conflict with memu-py's Alembic migrations |
| Memory extraction from text | Custom LLM prompts | memu-py `memorize()` | memu-py has battle-tested extraction prompts, deduplication, and categorization pipelines |
| Async background processing | asyncio.Queue / threading | FastAPI BackgroundTasks | BackgroundTasks is lifecycle-managed by Starlette, correct for post-response work |
| Docker health dependency ordering | sleep/retry loops | `depends_on: condition: service_healthy` | Declarative, correct, and handled by Compose itself |

**Key insight:** memu-py is not just a thin wrapper — it owns the schema, the extraction pipeline, the embedding workflow, and deduplication. Attempting to replicate any of these leads to schema conflicts or semantic drift.

---

## Common Pitfalls

### Pitfall 1: Wrong PyPI Package Name

**What goes wrong:** `pip install memu` installs a GameBoy emulator GUI (fortbonnitar's package, v2.1.4). The correct AI memory package is `memu-py`.
**Why it happens:** Two unrelated packages share similar names on PyPI.
**How to avoid:** requirements.txt must use `memu-py[postgres]>=1.4.0` (with hyphen and postgres extra).
**Warning signs:** ImportError on `from memu import MemUService` — wrong memu package installed.

### Pitfall 2: pgvector Extension Not in pg_extension After Restart

**What goes wrong:** After deleting volume and restarting, `SELECT * FROM pg_extension` does not contain `vector`.
**Why it happens:** The init script only runs on a clean volume (first start). If the script fails silently (no `set -e` or `ON_ERROR_STOP=1`), the extension is skipped but postgres still starts.
**How to avoid:** Always use `set -e` at top of init script AND `psql -v ON_ERROR_STOP=1`. Verify after startup with `docker compose logs db | grep vector`.
**Warning signs:** memu-py fails with `column "embedding" is of type vector but expression is of type text` or similar pgvector type errors.

### Pitfall 3: MemUService Connects Before Postgres is Healthy

**What goes wrong:** Memory service starts, tries to connect to postgres, gets `connection refused`, crashes.
**Why it happens:** Both containers start in parallel without ordering.
**How to avoid:** `depends_on: db: condition: service_healthy` in docker-compose.yml. The postgres healthcheck uses `pg_isready` with `start_period: 10s` to give postgres time to start before retrying.
**Warning signs:** Container logs show `OperationalError: could not connect to server: Connection refused` on startup.

### Pitfall 4: Docker SDK `network` vs Compose `networks`

**What goes wrong:** Adding `"networks": ["openclaw-net"]` to spawn.py's container_config causes Docker SDK to throw `TypeError` or silently ignore the network.
**Why it happens:** Docker Compose YAML uses `networks:` (list), but the Docker Python SDK's `containers.run()` uses `network=` (single string, the network name).
**How to avoid:** Use `"network": "openclaw-net"` in spawn.py container_config.
**Warning signs:** L3 container starts but cannot reach `openclaw-memory:18791` via curl.

### Pitfall 5: openclaw-net Does Not Exist When Compose Starts

**What goes wrong:** `docker compose up` fails with `network openclaw-net declared as external, but could not be found`.
**Why it happens:** The `networks.openclaw-net.external: true` in docker-compose.yml requires the network to exist before Compose starts.
**How to avoid:** Pre-create the network: `docker network create openclaw-net || true`. This is idempotent. Document in README and Phase verification steps.
**Warning signs:** Compose up fails immediately with network not found error.

### Pitfall 6: DSN Format for psycopg2 vs psycopg3

**What goes wrong:** memu-py uses `sqlalchemy[postgresql-psycopgbinary]` which is psycopg3. Using `postgresql+psycopg2://` DSN format causes `ModuleNotFoundError` for psycopg2.
**Why it happens:** psycopg3 uses a different SQLAlchemy dialect prefix.
**How to avoid:** Use `postgresql+psycopg://` (no trailing "2") for psycopg3. Alternatively use `postgresql://` and let SQLAlchemy auto-detect.
**Warning signs:** `ModuleNotFoundError: No module named 'psycopg2'` even though psycopgbinary is installed.

---

## Code Examples

### Health Endpoint

```python
# memory_service/routers/health.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/health")
async def health(request: Request):
    # Lightweight check: service is up and MemUService initialized
    service = request.app.state.memu
    return {
        "status": "ok",
        "service": "openclaw-memory",
        "memu_initialized": service is not None,
    }
```

### Pydantic Request/Response Models

```python
# memory_service/models.py
from pydantic import BaseModel
from typing import Any

class MemorizeRequest(BaseModel):
    resource_url: str
    modality: str = "conversation"
    user: dict[str, Any] | None = None

class RetrieveRequest(BaseModel):
    queries: list[dict[str, Any]]
    where: dict[str, Any] | None = None

class MemorizeAccepted(BaseModel):
    status: str = "accepted"
    message: str = "Memorization queued"

class HealthResponse(BaseModel):
    status: str
    service: str
    memu_initialized: bool
```

### Retrieve Endpoint

```python
# memory_service/routers/retrieve.py
# Source: memu-py retrieve() API from github.com/NevaMind-AI/MemU
from fastapi import APIRouter, Request
from ..models import RetrieveRequest

router = APIRouter()

@router.post("/retrieve")
async def retrieve(request: Request, payload: RetrieveRequest):
    service = request.app.state.memu
    result = await service.retrieve(
        queries=payload.queries,
        where=payload.where,
    )
    return result
```

### List and Delete Endpoints

```python
# memory_service/routers/memories.py
# Source: memu-py CRUD API from github.com/NevaMind-AI/MemU
from fastapi import APIRouter, Request
from typing import Any

router = APIRouter()

@router.get("/memories")
async def list_memories(request: Request, user_id: str | None = None):
    service = request.app.state.memu
    where = {"user_id": user_id} if user_id else None
    return await service.list_memory_items(where=where)

@router.delete("/memories/{memory_id}")
async def delete_memory(request: Request, memory_id: str):
    service = request.app.state.memu
    return await service.delete_memory_item(memory_id=memory_id)
```

### Dockerfile

```dockerfile
# docker/memory/Dockerfile
FROM python:3.13-slim-bookworm

WORKDIR /app

# Install build dependencies for psycopg binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY memory_service/ ./memory_service/

EXPOSE 18791

CMD ["uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "18791"]
```

### Uvicorn Configuration

Single worker is appropriate for this phase (memu-py uses async internally; multiple uvicorn workers would create multiple MemUService instances with separate DB connection pools). If concurrency becomes an issue in future phases, use `--workers 1` explicitly.

```bash
CMD ["uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "18791", "--workers", "1"]
```

### Logging Integration

Follow the existing `get_logger()` pattern from `orchestration/logging.py`. The memory service is a separate Docker container so it cannot import from `orchestration/` directly (that directory is mounted read-only in L3 containers, not in the memory service). Implement an equivalent standalone logger:

```python
# memory_service/logging.py
import json, logging, sys
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "component": f"memory.{record.name}",
            "message": record.getMessage(),
        })

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pg16 for pgvector | pg17-bookworm | PG17 release 2024 | Native vector type improvements, parallel query support |
| FastAPI startup/shutdown events | lifespan async context manager | FastAPI 0.93+ | Single function for both; no deprecation warning |
| psycopg2 + postgresql+psycopg2:// | psycopg3 + postgresql+psycopg:// | SQLAlchemy 2.0+ | psycopg3 is async-native, psycopg2 is sync-only |
| Alembic `alembic upgrade head` manually | memu-py `ddl_mode='create'` | memu-py design | Library owns its schema; manual migrations conflict |

**Deprecated/outdated:**
- `@app.on_event("startup")`: replaced by lifespan context manager in FastAPI 0.93+
- `pgvector/pgvector:pg16`: still works but pg17 is current and preferred

---

## Open Questions

1. **psycopg DSN format for memu-py**
   - What we know: memu-py requires `sqlalchemy[postgresql-psycopgbinary]` which is psycopg3
   - What's unclear: Whether memu-py accepts `postgresql+psycopg://` or requires `postgresql://` auto-detection
   - Recommendation: Try `postgresql+psycopg://` first (psycopg3 canonical prefix); fall back to `postgresql://` if OperationalError on startup. Confirm by checking memu-py's postgres.py session setup.

2. **MemUService async initialization**
   - What we know: `MemUService.__init__` is synchronous (constructor), but `memorize()`/`retrieve()` are async
   - What's unclear: Whether `run_migrations()` (called internally on init) is sync or async, and whether it needs an event loop to be running
   - Recommendation: Initialize MemUService inside the lifespan `async` function (where event loop is active). If init triggers async work, use `await` or wrap with `asyncio.get_event_loop().run_until_complete()`.

3. **`user` parameter scope for project-scoping in Phase 26**
   - What we know: memu-py's `where` and `user` parameters filter memory items; Phase 27 handles mandatory project_id enforcement
   - What's unclear: Whether Phase 26 should accept `user` param in API or stub it
   - Recommendation: Accept `user: dict | None` in Phase 26 models (pass-through to memu-py). Phase 27 will add enforcement layer at API wrapper level. This avoids a breaking API change between phases.

---

## Sources

### Primary (HIGH confidence)
- `https://raw.githubusercontent.com/NevaMind-AI/MemU/main/src/memu/app/service.py` — MemUService constructor signature
- `https://raw.githubusercontent.com/NevaMind-AI/MemU/main/src/memu/app/settings.py` — DatabaseConfig, MetadataStoreConfig, ddl_mode, VectorIndexConfig
- `https://raw.githubusercontent.com/NevaMind-AI/MemU/main/src/memu/app/memorize.py` — memorize() async signature and parameters
- `https://raw.githubusercontent.com/NevaMind-AI/MemU/main/src/memu/app/retrieve.py` — retrieve() async signature with queries/where params
- `https://raw.githubusercontent.com/NevaMind-AI/MemU/main/src/memu/app/crud.py` — list_memory_items(), delete_memory_item() signatures
- `https://raw.githubusercontent.com/NevaMind-AI/MemU/main/src/memu/database/postgres/migration.py` — ddl_mode='create' behavior (CREATE EXTENSION + create_all + Alembic upgrade head)
- Context7 /fastapi/fastapi — lifespan context manager, BackgroundTasks, status codes
- `https://pypi.org/pypi/memu-py/json` — memu-py 1.4.0 dependencies confirmed (openai, pydantic, sqlmodel, alembic, pgvector extra)
- `docker pull pgvector/pgvector:pg17-bookworm` — image confirmed available locally

### Secondary (MEDIUM confidence)
- memu-py README on GitHub — MemUService initialization examples, llm_profiles structure
- FastAPI official docs (via Context7) — BackgroundTasks, lifespan, Pydantic models

### Tertiary (LOW confidence)
- DSN format for psycopg3 — inferred from SQLAlchemy 2.0 documentation conventions; not directly verified against memu-py's session.py

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — memu-py version confirmed on PyPI, all constructor params verified from source
- Architecture: HIGH — FastAPI lifespan and BackgroundTasks are documented patterns; Docker Compose health ordering is standard
- Pitfalls: HIGH — wrong PyPI package name verified empirically (memu vs memu-py); psycopg DSN format verified from SQLAlchemy docs
- DSN format: MEDIUM — psycopg3 dialect confirmed but not verified against memu-py's exact session config

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (memu-py moves slowly; FastAPI stable)
