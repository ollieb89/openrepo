# Stack Research

**Domain:** AI Swarm Orchestration — Agent Memory Integration (v1.3 additions)
**Researched:** 2026-02-24
**Confidence:** HIGH

> **Scope note:** This document covers ONLY stack additions/changes required for the v1.3
> "Agent Memory" milestone. The validated baseline (Python 3.14.3 host, Docker, Next.js 14,
> SWR, Tailwind, Bun, Recharts) is unchanged. Do not re-architect what works.
>
> Focus: memU as a standalone Docker service, its PostgreSQL+pgvector backend, the
> FastAPI wrapper that exposes it internally, and the httpx client that L3 containers
> and the orchestration layer use to call it.

---

## Recommended Stack

### New Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `memu-py` | 1.4.0 | Memory framework for agents — memorize, retrieve, categorize | The specified framework. Provides `MemUService` with dual-mode retrieval (RAG + LLM). Requires Python 3.13+. |
| `FastAPI` | 0.132.0 | HTTP wrapper service exposing memU to the rest of OpenClaw | Async-native, Pydantic validation built-in, OpenAPI docs free. Runs on Python 3.10+. Wraps `MemUService` in a stable internal REST API that both L2 orchestration and L3 containers can call. |
| `uvicorn` | 0.41.0 | ASGI server running the FastAPI memory service | Standard uvicorn[standard] ships with watchfiles, httptools, websockets. ~20MB memory footprint per worker. Sufficient for single-host, low-concurrency internal service. |
| `pgvector/pgvector:pg17` | pg17 (pgvector 0.8.1) | PostgreSQL 17 with pgvector extension pre-installed | Official image, maintained by pgvector team. pg17 is the current stable PostgreSQL major version. pgvector 0.8.1 is the latest stable release. The `pg17-bookworm` variant matches the Debian bookworm-slim base used by L3 containers, minimising surprise in apt package versions. |
| `python:3.13-slim-bookworm` | 3.13 (latest patch) | Base image for the memU Docker service container | memU requires Python >=3.13. Host runs Python 3.14.3 but the service runs in its own container. `slim-bookworm` matches the Debian bookworm foundation of L3 containers — consistent base OS across all service containers. |
| `httpx` | 0.28.1 | HTTP client for L2 orchestration and L3 containers to call the memory service | Supports both sync and async APIs — critical because L2 orchestration (asyncio) and L3 entrypoint (bash script calling python) have different concurrency models. A single library covers both call sites. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncpg` | 0.31.0 | Async PostgreSQL driver | Used internally by memU's postgres backend when `database_config.metadata_store.provider == "postgres"`. Install via `memu-py[postgres]` extra — do not install separately unless memU's dependency resolution misses it. |
| `pydantic` | v2 (via FastAPI) | Request/response validation in the FastAPI wrapper | FastAPI installs Pydantic v2 automatically. Define request schemas for `/memorize`, `/retrieve`, `/categories` endpoints. Validates agent_id, project_id scoping fields. |
| `python-dotenv` | latest | Load `MEMORY_SERVICE_*` env vars in the memU container | Standard pattern for Docker secrets/config. Keeps connection strings out of the image. Install in the memU service Dockerfile. |

### No New Frontend Libraries

The occc dashboard memory panel needs only what's already installed:

| Already Present | Version | Reuse Pattern |
|----------------|---------|---------------|
| `swr` | 2.4.0 | Poll `/api/memory/categories` and `/api/memory/items` — same SWR hook pattern as tasks/containers |
| `zod` | 3.23.8 | Validate memory API response shapes — extend existing Zod schema files |
| `recharts` | 3.7.0 | No memory charts needed in v1.3 — category counts are table/list, not time-series |
| `react-toastify` | 10.0.5 | Surface memory errors — already used for swarm alerts |

---

## Architecture: memU as a Standalone Service

The memU service is a separate Docker container — **not** embedded in L2 orchestration or L3 containers.

```
Host
├── openclaw-gateway (existing)
├── openclaw-<project>-l2 (existing L2 PM agent)
├── openclaw-<project>-l3-<task> (ephemeral, existing)
│
└── openclaw-memory-service  [NEW]
    ├── python:3.13-slim-bookworm
    ├── memu-py[postgres] + FastAPI + uvicorn
    └── listens on port 18791 (host-bound, internal only)
        │
        └── connects to openclaw-memory-db  [NEW]
            ├── pgvector/pgvector:pg17-bookworm
            └── port 5432 (host-bound, internal only)
```

**Why a separate container, not embedded:**
- memU requires Python 3.13+; L2 orchestration runs on host Python 3.14.3 but the L3 image uses system python3 (Debian bookworm = Python 3.11). Embedding creates a version conflict.
- memU's PostgreSQL connection is persistent; L3 containers are ephemeral and torn down after task completion. A standalone service maintains the connection pool across L3 lifetimes.
- The FastAPI wrapper provides a stable, versioned API surface. Both L2 (Python asyncio) and L3 (bash + python3) call the same HTTP endpoints — no shared-memory IPC needed.

**Call paths:**
- L2 review decisions → `POST http://localhost:18791/memorize` (via `httpx.AsyncClient`)
- L3 task outcomes → `POST http://localhost:18791/memorize` (via `httpx.Client`, sync, from entrypoint.sh python call)
- Pre-spawn context retrieval → `GET http://localhost:18791/retrieve` (L2, async, before `spawn.py`)
- Dashboard → `/api/memory/*` Next.js API routes → proxy to `http://localhost:18791/*`

---

## Installation

```bash
# memU service container (Dockerfile.memory)
# Base: python:3.13-slim-bookworm
pip install "memu-py[postgres]==1.4.0"
pip install "fastapi[standard]==0.132.0"
pip install uvicorn==0.41.0
pip install python-dotenv

# L2 orchestration host additions (for calling the memory service)
pip install httpx==0.28.1

# L3 container additions (Dockerfile.l3-specialist update)
# Add to existing debian:bookworm-slim image:
pip3 install httpx==0.28.1

# PostgreSQL + pgvector (Docker image, no pip install)
docker pull pgvector/pgvector:pg17-bookworm
```

**docker-compose snippet for the new services:**

```yaml
services:
  memory-db:
    image: pgvector/pgvector:pg17-bookworm
    container_name: openclaw-memory-db
    environment:
      POSTGRES_USER: openclaw
      POSTGRES_PASSWORD: ${MEMORY_DB_PASSWORD}
      POSTGRES_DB: openclaw_memory
    volumes:
      - memory-db-data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5433:5432"  # Host-only, non-default port avoids conflict
    restart: unless-stopped

  memory-service:
    build:
      context: docker/memory-service
      dockerfile: Dockerfile
    container_name: openclaw-memory-service
    image: openclaw-memory-service:latest
    environment:
      MEMORY_DB_URL: postgresql://openclaw:${MEMORY_DB_PASSWORD}@memory-db:5432/openclaw_memory
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      MEMORY_SERVICE_PORT: 18791
    ports:
      - "127.0.0.1:18791:18791"  # Host-only
    depends_on:
      - memory-db
    restart: unless-stopped

volumes:
  memory-db-data:
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `FastAPI` wrapper around memU | Expose memU directly via its cloud REST API (`memu.so`) | If you don't need self-hosted control. For OpenClaw, self-hosted is required — no external SaaS dependencies for agent internals. |
| `FastAPI` wrapper | Flask or Starlette directly | FastAPI adds zero overhead over Starlette (it's a thin layer) and gives automatic request validation + docs. Flask is WSGI-only; async memU calls would need `asyncio.run()` workarounds. |
| `httpx` for HTTP calls | `requests` (sync) or `aiohttp` (async-only) | `httpx` covers both L2 (async) and L3 (sync) call sites with one library. `requests` has no async support. `aiohttp` has no sync API. Using two libraries for the same purpose is unnecessary. |
| `pgvector/pgvector:pg17-bookworm` | Build custom PostgreSQL + pgvector image | The official pgvector image is maintained by the pgvector team with correct compile flags. No custom build needed unless corporate registry restrictions apply. |
| `python:3.13-slim-bookworm` for memory service | `python:3.13-alpine` | Alpine uses musl libc; asyncpg and other C-extension packages require glibc. Bookworm matches L3 container base and avoids musl compilation issues. |
| Separate `openclaw-memory-service` container | Embed memU in L2 orchestration host process | Python version conflict (memU needs 3.13+, host is 3.14.3 — compatible but forces all L2 dependencies to 3.13+ as well). More importantly, service isolation allows restart, upgrade, and debug independently. |
| Port 18791 for memory service | Port 8080 or 3000 | 18791 follows the existing OpenClaw port convention (gateway: 18789, dashboard: 18795→6987). Keeps all OpenClaw ports in the 18xxx range and avoids collision with common development server ports. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `psycopg2` or `psycopg3` directly | memU manages its own PostgreSQL connection via asyncpg. Installing a second driver creates version conflicts and duplicate connections. | Let `memu-py[postgres]` pull in asyncpg as its transitive dependency. |
| Embedding memU in L3 container image | L3 containers are ephemeral and rebuilt per task. Installing memU (with its PostgreSQL driver and embedding dependencies) in every L3 image bloats the image and couples memory management to task execution. | L3 containers call the memory service via httpx HTTP calls. Only httpx (~2MB) gets added to the L3 image. |
| `mem0` (Mem0/Memory layer by Zep) | Different library entirely — not memU. Despite similar names and similar purposes, mem0 has a different API surface and SaaS orientation. | `memu-py==1.4.0` as specified. |
| LangChain or LangGraph for memory | Adds 50+ transitive dependencies. memU is already an opinionated memory framework — adding an orchestration framework on top creates two overlapping abstraction layers. | `MemUService` directly from `memu-py`. |
| Redis as vector store alternative | Redis Stack's vector search is less mature than pgvector for semantic similarity. pgvector is the standard choice for SQL-adjacent teams and memU is already tested against it. | `pgvector/pgvector:pg17-bookworm` |
| `Gunicorn` as process manager for memory service | Single-container deployment with one worker is sufficient. Gunicorn's pre-fork model adds memory overhead with no concurrency benefit for a low-traffic internal service. | `uvicorn` directly: `uvicorn memory_service.main:app --host 0.0.0.0 --port 18791 --workers 1` |

---

## Stack Patterns by Access Pattern

**If calling from L2 orchestration (asyncio context):**

```python
import httpx

async def memorize_review_decision(agent_id: str, project_id: str, payload: dict):
    async with httpx.AsyncClient(base_url="http://localhost:18791") as client:
        response = await client.post("/memorize", json={
            "agent_id": agent_id,
            "project_id": project_id,
            **payload
        })
        response.raise_for_status()
```

**If calling from L3 entrypoint (sync context, bash-invoked python3):**

```python
import httpx

def memorize_task_outcome(task_id: str, project_id: str, git_diff: str, summary: str):
    with httpx.Client(base_url="http://localhost:18791", timeout=30.0) as client:
        response = client.post("/memorize", json={
            "agent_id": f"l3-{task_id}",
            "project_id": project_id,
            "content": summary,
            "metadata": {"git_diff": git_diff[:4096]}  # cap diff size
        })
        response.raise_for_status()
```

**If the memory service is down (failure mode):**
- L3 memorization failure must NOT block task completion — wrap in try/except, log warning, continue
- L2 pre-spawn retrieval failure should degrade gracefully — proceed with empty context rather than blocking spawn

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `memu-py==1.4.0` | Python >=3.13 | cp313-abi3 wheels available for Linux x86_64. Host is Python 3.14.3 (compatible, but service runs in python:3.13 container). |
| `fastapi==0.132.0` | Python >=3.10, Pydantic v2 | Pydantic v2 is the default. No legacy Pydantic v1 compatibility layer needed. |
| `uvicorn==0.41.0` | Python >=3.10 | Dropped Python 3.9 support in 0.40.0. Python 3.13 fully supported. |
| `httpx==0.28.1` | Python >=3.8 | Works on Python 3.14.3 (host, L2) and Python 3.11 (Debian bookworm system python, L3 containers). |
| `asyncpg==0.31.0` | Python 3.9–3.14 | Pulled in by `memu-py[postgres]`. Python 3.14 beta support confirmed. |
| `pgvector/pgvector:pg17-bookworm` | PostgreSQL 17, pgvector 0.8.1 | Uses Debian bookworm as OS base — consistent with L3 `debian:bookworm-slim` containers. |
| `python:3.13-slim-bookworm` | Debian bookworm | Confirmed available on Docker Hub. Latest patch is 3.13.12 as of Feb 2026. |

---

## Sources

- [memu-py PyPI](https://pypi.org/project/memu-py/) — Python >=3.13 requirement, postgres/claude/langgraph extras (HIGH confidence, verified 2026-02-24)
- [NevaMind-AI/memU GitHub README](https://github.com/NevaMind-AI/memU/blob/main/README.md) — `MemUService` API, PostgreSQL setup with `pgvector/pgvector:pg16`, connection config (HIGH confidence, verified 2026-02-24)
- [FastAPI PyPI](https://pypi.org/project/fastapi/) — version 0.132.0, Python >=3.10, Starlette + Pydantic v2 (HIGH confidence, verified 2026-02-24)
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) — version 0.41.0, dropped Python 3.9 in 0.40.0 (HIGH confidence, verified 2026-02-24)
- [httpx PyPI](https://pypi.org/project/httpx/) — version 0.28.1, Python >=3.8, sync + async APIs (HIGH confidence, verified 2026-02-24)
- [asyncpg PyPI](https://pypi.org/project/asyncpg/) — version 0.31.0, Python 3.9–3.14 (HIGH confidence, verified 2026-02-24)
- [pgvector Docker Hub tags](https://hub.docker.com/r/pgvector/pgvector/tags) — pg17, 0.8.1-pg17-bookworm confirmed available (MEDIUM confidence, tag list from search results 2026-02-24)
- [python Docker Hub](https://hub.docker.com/_/python) — python:3.13-slim-bookworm confirmed, latest patch 3.13.12 (HIGH confidence, verified 2026-02-24)
- Host Python version — `python3 --version` → 3.14.3; `python3.13` not available as alias (HIGH confidence, verified live 2026-02-24)
- Existing occc `package.json` — swr@2.4.0, zod@3.23.8, recharts@3.7.0 confirmed; no memory-related packages present (HIGH confidence, read from source 2026-02-24)
- L3 Dockerfile — `docker/l3-specialist/Dockerfile` uses `debian:bookworm-slim`; python3 system package installed (HIGH confidence, read from source 2026-02-24)

---

*Stack research for: OpenClaw v1.3 — Agent Memory (memU integration)*
*Researched: 2026-02-24*
*Previous baseline (v1.0–v1.2): Python 3 stdlib orchestration, Docker SDK, Next.js 14, SWR, Recharts — all unchanged*
