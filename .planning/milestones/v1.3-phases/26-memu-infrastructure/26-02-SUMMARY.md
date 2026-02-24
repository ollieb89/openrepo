---
phase: 26-memu-infrastructure
plan: 02
subsystem: memory
tags: [fastapi, memu-py, postgresql, pgvector, docker, python, rest-api]

# Dependency graph
requires:
  - 26-01 (Docker Compose stack, Dockerfile, requirements.txt)
provides:
  - FastAPI memory_service package with 5 REST endpoints (health, memorize, retrieve, list, delete)
  - MemoryService initialization via memu.app with postgres+pgvector backend
  - Structured JSON logging via StructuredFormatter
  - Pydantic Settings from environment variables with psycopg3 DSN
  - Full end-to-end verified stack: build, health, memorize 202, pgvector cold-start, Docker DNS
affects:
  - 27-memu-project-scoping (uses http://localhost:18791 REST API)
  - 28-memu-l2-integration (calls /memorize and /retrieve endpoints)
  - 29-memu-l3-integration (reaches openclaw-memory:18791 via openclaw-net DNS)

# Tech tracking
tech-stack:
  added:
    - pydantic-settings>=2.0.0 (was missing from requirements.txt — auto-fixed)
    - build-essential + libc6-dev (Dockerfile — required by Rust/maturin linker for memu-py)
    - rustup stable (Dockerfile — memu-py uses maturin/pyo3 and requires Rust toolchain to build)
  patterns:
    - FastAPI lifespan for singleton initialization via app.state.memu
    - BackgroundTasks for async /memorize (202 Accepted, non-blocking)
    - StructuredFormatter JSON logging to stderr matching orchestration layer pattern
    - 503 guard pattern — all routers check app.state.memu is not None before calling service
    - Sync constructor / async methods — MemoryService.__init__ is sync; memorize/retrieve/list/delete are async

key-files:
  created:
    - docker/memory/memory_service/__init__.py
    - docker/memory/memory_service/main.py
    - docker/memory/memory_service/config.py
    - docker/memory/memory_service/service.py
    - docker/memory/memory_service/models.py
    - docker/memory/memory_service/logging.py
    - docker/memory/memory_service/routers/__init__.py
    - docker/memory/memory_service/routers/health.py
    - docker/memory/memory_service/routers/memorize.py
    - docker/memory/memory_service/routers/retrieve.py
    - docker/memory/memory_service/routers/memories.py
  modified:
    - docker/memory/Dockerfile
    - docker/memory/requirements.txt
    - docker/memory/memory_service/main.py
    - docker/memory/memory_service/service.py

key-decisions:
  - "MemoryService from memu.app, not MemUService from memu — plan used wrong class name, correct class discovered via introspection"
  - "MemoryService constructor is sync (not async) — init_service() is a regular function, called directly in lifespan without await"
  - "memu-py requires Rust toolchain — Dockerfile updated with build-essential + libc6-dev + rustup for maturin/pyo3 compilation"
  - "pydantic-settings added to requirements.txt — was missing from Plan 01 infrastructure, required by config.py"
  - "memorize_config with llm_temperature removed — not a valid MemorizeConfig field (discovered via introspection)"
  - "retrieve endpoint returns 500 without real OpenAI key — expected: vector search needs embeddings; auth gate documented"

# Metrics
duration: 13min
completed: 2026-02-24
---

# Phase 26 Plan 02: memU FastAPI Application Summary

**FastAPI wrapper around memu.app.MemoryService with 5 REST endpoints, postgres+pgvector backend, structured JSON logging, and full stack verified end-to-end including cold-start and Docker DNS**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-02-24T06:39:54Z
- **Completed:** 2026-02-24T06:52:29Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Created complete `memory_service/` Python package (11 files): config, logging, service, models, main, and 4 routers
- Pydantic Settings read DB/OpenAI config from env vars; `dsn` property returns `postgresql+psycopg://` (psycopg3)
- StructuredFormatter outputs JSON lines with UTC timestamp, level, `memory.{name}` component
- MemoryService initialized synchronously in FastAPI lifespan, stored as `app.state.memu` singleton
- All 5 endpoints: GET /health, POST /memorize (202 + BackgroundTasks), POST /retrieve, GET /memories, DELETE /memories/{id}
- All routers guard against uninitialized service (returns 503 if `app.state.memu is None`)
- Docker image built successfully with Rust toolchain for memu-py Rust extension (maturin/pyo3)
- Full stack verified: health 200, memorize 202, list memories, pgvector cold-start, Docker DNS from openclaw-net

## Task Commits

Each task committed atomically:

1. **Task 1: Create FastAPI application with all endpoints** - `88fba8b` (feat)
2. **Task 2: Build and verify the complete memory stack** - `b8827fc` (feat)

## Files Created/Modified

- `docker/memory/memory_service/__init__.py` - Empty package marker
- `docker/memory/memory_service/config.py` - Pydantic Settings: DB vars, OpenAI key, dsn property
- `docker/memory/memory_service/logging.py` - StructuredFormatter + get_logger() factory
- `docker/memory/memory_service/service.py` - init_service() wrapping MemoryService (sync constructor)
- `docker/memory/memory_service/models.py` - MemorizeRequest, RetrieveRequest, MemorizeAccepted, HealthResponse
- `docker/memory/memory_service/main.py` - FastAPI lifespan + app + router includes
- `docker/memory/memory_service/routers/__init__.py` - Empty package marker
- `docker/memory/memory_service/routers/health.py` - GET /health with memu_initialized flag
- `docker/memory/memory_service/routers/memorize.py` - POST /memorize, BackgroundTasks, 202 Accepted
- `docker/memory/memory_service/routers/retrieve.py` - POST /retrieve, async blocking call
- `docker/memory/memory_service/routers/memories.py` - GET /memories (user_id filter) + DELETE /memories/{id}
- `docker/memory/Dockerfile` - Added build-essential, libc6-dev, rustup for memu-py Rust compilation
- `docker/memory/requirements.txt` - Added pydantic-settings>=2.0.0

## Decisions Made

- `MemoryService` from `memu.app` — plan referenced `MemUService` from `memu` which does not exist; correct class found via introspection
- Sync constructor, async methods — `MemoryService.__init__` is synchronous; all operation methods (`memorize`, `retrieve`, `list_memory_items`, `delete_memory_item`) are async coroutines
- Rust toolchain in Dockerfile — memu-py v1.4.0 contains a Rust extension (maturin/pyo3); `python:3.13-slim-bookworm` lacks C stdlib headers; added `build-essential` + `libc6-dev` + `rustup stable`
- `memorize_config.llm_temperature` removed — not a field in `MemorizeConfig`; discovered via `inspect.getsource()`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Dependency] Added pydantic-settings to requirements.txt**
- **Found during:** Task 1
- **Issue:** `config.py` uses `pydantic_settings.BaseSettings` but `pydantic-settings` was not in `requirements.txt`
- **Fix:** Added `pydantic-settings>=2.0.0` to `docker/memory/requirements.txt`
- **Files modified:** `docker/memory/requirements.txt`
- **Commit:** 88fba8b

**2. [Rule 1 - Bug] Wrong class name — MemoryService not MemUService**
- **Found during:** Task 2 (container startup crash)
- **Issue:** Plan specified `from memu import MemUService` — this class does not exist. The correct import is `from memu.app import MemoryService`
- **Fix:** Updated `service.py` and `main.py` to use `MemoryService` from `memu.app`
- **Files modified:** `docker/memory/memory_service/service.py`, `docker/memory/memory_service/main.py`
- **Commit:** b8827fc

**3. [Rule 1 - Bug] MemoryService constructor is synchronous**
- **Found during:** Task 2 (container startup)
- **Issue:** Plan suggested `await init_service(settings)` — but `MemoryService.__init__` is synchronous (confirmed via `inspect.iscoroutinefunction`)
- **Fix:** `init_service()` made a regular (non-async) function; called directly in lifespan without await
- **Files modified:** `docker/memory/memory_service/service.py`, `docker/memory/memory_service/main.py`
- **Commit:** b8827fc

**4. [Rule 1 - Bug] Dockerfile missing Rust toolchain for memu-py**
- **Found during:** Task 2 (docker compose build failure)
- **Issue:** memu-py v1.4.0 contains a Rust extension compiled via maturin/pyo3; `python:3.13-slim-bookworm` lacks C stdlib development files (`Scrt1.o`, `crti.o`) needed by Rust linker
- **Fix:** Added `build-essential`, `libc6-dev`, `curl` to apt-get install; installed `rustup` stable minimal profile; set `PATH` to include `~/.cargo/bin`
- **Files modified:** `docker/memory/Dockerfile`
- **Commit:** b8827fc

**5. [Rule 1 - Bug] Invalid MemorizeConfig field**
- **Found during:** Task 2 (code review during fix)
- **Issue:** Plan included `memorize_config={"llm_temperature": 0.0}` but `MemorizeConfig` has no `llm_temperature` field — would raise Pydantic validation error at runtime
- **Fix:** Removed `memorize_config` argument from `MemoryService()` call (defaults are fine)
- **Files modified:** `docker/memory/memory_service/service.py`
- **Commit:** b8827fc

## Auth Gate

POST /retrieve returns 500 with a placeholder `OPENAI_API_KEY`. This is expected behavior — vector similarity search requires real OpenAI embeddings. The endpoint structure is correct; LLM calls fail with `401 invalid_api_key`. All other endpoints (health, memorize 202, list memories, delete) function correctly without a valid key.

**To use /retrieve:** Set a real `OPENAI_API_KEY` in `docker/memory/.env` and restart.

## Verification Results

| Check | Result |
|-------|--------|
| GET /health returns 200, `memu_initialized: true` | PASS |
| POST /memorize returns 202 Accepted | PASS |
| GET /memories returns list | PASS |
| pgvector present after volume delete + restart | PASS |
| Docker DNS: `openclaw-memory:18791` from `openclaw-net` | PASS |

## Self-Check: PASSED

All 11 Python files verified present on disk. Both task commits (88fba8b, b8827fc) confirmed in git log.
