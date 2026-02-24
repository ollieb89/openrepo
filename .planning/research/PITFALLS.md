# Pitfalls Research

**Domain:** Adding persistent agent memory (memU) to an existing multi-agent Docker orchestration system (OpenClaw v1.3)
**Researched:** 2026-02-24
**Confidence:** HIGH — derived from direct codebase inspection of v1.2 implementation, memU-server architecture review, official pgvector documentation, and Docker networking documentation

---

## Critical Pitfalls

### Pitfall 1: L3 Containers Run Python 3.11 — memU Requires Python 3.13

**What goes wrong:**
The L3 Dockerfile (`docker/l3-specialist/Dockerfile`) is based on `debian:bookworm-slim` and installs Python via `apt-get install python3`. Debian bookworm's APT repository ships Python 3.11 as the default `python3` package. memU explicitly requires Python 3.13+. Any attempt to `pip install memu-py` inside the L3 container will either fail immediately due to version mismatch or install silently but fail at import time when memU exercises 3.13-specific syntax (notably, PEP 695 type aliases and PEP 702 deprecation warnings used internally by the framework).

The memU service container (memU-server) also requires Python 3.13+. If the memU service Docker image is built from `debian:bookworm-slim` rather than `python:3.13-slim-bookworm`, the same version mismatch will block startup.

**Why it happens:**
The default `python3` package on Debian bookworm resolves to 3.11 because Python 3.13 is not in the standard bookworm repository. Developers assume `python:3.13-slim-bookworm` (the official Docker Python image) and `debian:bookworm-slim` with `apt-get install python3` are equivalent — they are not. The official Docker Python images compile Python from source and bundle 3.13 themselves regardless of the Debian APT version.

**How to avoid:**
- For the memU-server service: base the Dockerfile on `python:3.13-slim-bookworm` from Docker Hub, not on `debian:bookworm-slim`
- For the L3 specialist container: if L3 needs to call memU directly (in-execution queries), the call must go through the REST API to the standalone memU service, not via direct Python import — this eliminates any Python version requirement for L3 itself. The L3 entrypoint only needs `curl` or `python3 -c "import urllib"` to make HTTP calls.
- If direct Python import is ever needed inside L3, the Dockerfile must switch to `python:3.13-slim-bookworm` as its base, which changes the image size, startup time, and rebuild cadence — a separate decision to plan explicitly.

**Warning signs:**
- `pip install memu-py` succeeds but `import memu` raises `SyntaxError` or `ImportError` at runtime inside L3
- `python3 --version` inside the L3 container returns 3.11.x
- memU-server fails to start with `SyntaxError: invalid syntax` pointing at a memU source file

**Phase to address:** Phase 1 (memU Service Setup) — base image decision must be locked before any memU integration code is written

---

### Pitfall 2: pgvector Extension Fails to Create During Docker Initialization

**What goes wrong:**
The standard pattern for initializing a PostgreSQL Docker container is to place a `.sql` file in `/docker-entrypoint-initdb.d/`. However, `CREATE EXTENSION IF NOT EXISTS vector` in a raw `.sql` init script can fail silently or with an error during Docker startup, even when using the `pgvector/pgvector:pg17` image. The extension creation timing has a known ordering dependency: PostgreSQL must fully initialize the base database before extension creation scripts run, but script execution order depends on alphabetical filename sorting. If the schema migration script (which creates tables with `vector` column types) sorts alphabetically before the extension creation script, the table creation fails with `type "vector" does not exist`.

**Why it happens:**
Files in `/docker-entrypoint-initdb.d/` execute in alphabetical order. A schema file named `schema.sql` runs before an extension file named `vector.sql`. Additionally, raw `.sql` scripts cannot check whether the extension is already installed, so re-running against an existing volume produces an error that halts initialization. Finally, `docker-entrypoint-initdb.d` only runs when the container data directory is empty — developers who reuse volumes without clearing them miss initialization failures entirely.

**How to avoid:**
- Use `pgvector/pgvector:pg17` (or pg16) as the base image — it has the extension pre-compiled and available
- Place extension creation in a shell script (`00_init.sh`) rather than a SQL file, using the `psql -c "CREATE EXTENSION IF NOT EXISTS vector"` command. Shell scripts in the init directory are reliably executed before SQL files at the same sort position
- Prefix filenames numerically: `00_extensions.sh`, `01_schema.sql` to guarantee ordering
- Add `--shm-size=256m` to the Docker run command (or `shm_size` in docker-compose) if HNSW index builds are planned — pgvector HNSW parallel builds require shared memory exceeding the Docker default 64MB

**Warning signs:**
- `psql -c "\dx"` inside the postgres container shows `vector` extension missing
- memU-server logs show `type "vector" does not exist` during table creation
- PostgreSQL container health check passes but memU connection to DB fails with a column type error
- Volume mounted from a previous run skips `initdb.d` scripts entirely, masking first-run failures

**Phase to address:** Phase 1 (memU Service Setup) — database initialization must be validated with a cold-start test (removing volumes and re-running) before any memory API work begins

---

### Pitfall 3: Multiple Concurrent L3 Containers Overwhelm the memU Memorize Endpoint

**What goes wrong:**
Up to 3 L3 containers can complete simultaneously (per the pool's `max_concurrent=3` configuration). Each container's completion triggers a `POST /memorize` call to the memU service. The memU memorize operation is not a simple write — it invokes an LLM to categorize, embed, and store the content. Under the default memU-server configuration, memorize calls are synchronous from the client's perspective and can take 5-15 seconds each depending on content size and LLM latency. Three simultaneous memorize calls from 3 completing L3 containers create a thundering-herd against the single-threaded FastAPI server.

The memU-server uses Temporal as its background workflow engine. Temporal adds significant overhead (its own PostgreSQL database, gRPC server, UI server), and the self-hosted Temporal setup requires careful initialization ordering that the memU-server `docker-compose.yml` does not fully automate (Temporal schema migrations must complete before the API server starts).

**Why it happens:**
The memU memorize endpoint is designed for single-agent or low-concurrency use. The OpenClaw pool allows burst completion of 3 tasks simultaneously. The entrypoint calls memorize synchronously in the completion block, so a slow memU service directly extends L3 container lifetime beyond the task's actual work duration, consuming the pool slot and potentially causing queue starvation for the next task.

**How to avoid:**
- Call memU's memorize endpoint in a fire-and-forget pattern from L3: the entrypoint should not wait for the memorize response. Use a detached subprocess call (`python3 -c "..." &`) or a short-timeout HTTP call (3s timeout) that drops the result if it times out
- Alternatively, have L3 write task outcome metadata to the state file as a `pending_memorize` field, and have the L2 post-review step trigger memorize after the L3 container has exited and its pool slot is freed
- Rate-limit memorize calls in the REST API wrapper with a simple asyncio semaphore (max 2 concurrent memorize operations)
- Evaluate whether Temporal is necessary for the OpenClaw use case — for the scale of this system (3 concurrent L3s, single host), a simple asyncio background task queue is sufficient and eliminates Temporal's 3-service overhead

**Warning signs:**
- L3 containers show `completed` status in state.json but continue running for 30+ seconds after task completion
- Pool utilization stays at 3/3 even after tasks have finished their actual work
- memU-server logs show multiple simultaneous `POST /memorize` requests piling up
- Docker container for Temporal shows unhealthy status, causing memU memorize calls to hang indefinitely

**Phase to address:** Phase 2 (L3 Auto-Memorization) — must establish the fire-and-forget pattern before any L3 memorize integration; Phase 1 (memU Service Setup) must evaluate whether to include Temporal

---

### Pitfall 4: SOUL Template Context Size Explosion from Memory Injection

**What goes wrong:**
The pre-spawn memory retrieval step fetches relevant memories from memU and injects them into the SOUL template before the L3 agent starts. The current `soul_renderer.py` uses `string.Template.safe_substitute()` which performs simple variable interpolation — a memory block injected via a `$memory_context` variable placeholder has no length limit. If the retrieve call returns 20 memory items (each potentially 2-5KB of conversation context), the injected SOUL grows by 40-100KB. This bloated SOUL is passed to the L2 prompt and the L3 agent's system prompt.

Modern LLMs have large context windows (200K tokens for Claude), but injecting 50-100KB of raw memory into the system prompt has two concrete failure modes: (1) the most relevant recent memories are crowded out by verbose older memories that weren't well-filtered by retrieval, and (2) the L3 agent spends its token budget responding to or referencing stale memories rather than executing the task. For claude-code, a bloated system prompt is also never truncated — the full content is sent on every conversation turn, multiplying costs linearly with conversation length.

**Why it happens:**
`retrieve()` returns whatever memU finds as relevant. Without an explicit `limit` parameter or a character budget cap on the retrieved context, the default behavior is to return all matches above a similarity threshold. Developers integrate memory injection by concatenating retrieved memories as-is into a template variable, treating all memory as equally useful context.

**How to avoid:**
- Always set an explicit `limit` on `retrieve()` calls — default to 5 memories maximum for pre-spawn SOUL injection
- Impose a hard character budget: the injected `$memory_context` block must not exceed 2,000 characters. If retrieved memories exceed this, truncate to the most recent N entries that fit
- Structure injected memories as a brief summary section, not raw conversation transcripts: `"In a previous task on [date], you [summary]. Key outcome: [outcome]."` — not the full conversation log
- Add `$memory_context` as an optional placeholder in `soul-default.md` using `safe_substitute` — if no memories exist (first run, new project), the placeholder is simply omitted without error
- Scope the retrieve query specifically: `retrieve(query=task_description, agent_id=l3_agent_id, project_id=project_id, limit=5)` — do not retrieve global memories across all agents

**Warning signs:**
- SOUL.md rendered size exceeds 10KB (the v1.2 baseline SOUL is ~3KB)
- L3 agent's first response references a past task that is not relevant to the current task description
- LLM API costs per task spike after memory injection is added
- `string.Template.safe_substitute()` renders a `$memory_context` variable with 40+ KB of content

**Phase to address:** Phase 3 (Pre-Spawn Context Retrieval) — memory injection template must be designed with budget constraints before the retrieve integration is wired up

---

### Pitfall 5: Container Networking — L3 Cannot Reach memU Service via localhost

**What goes wrong:**
L3 containers are spawned with the existing spawn.py configuration which does not add them to a named Docker network — they run in the default bridge network. The memU service (which will be a separate Docker container) is also in the default bridge network or its own network, exposed on a host port (e.g., 8000). From inside an L3 container, `http://localhost:8000/memorize` resolves to the container's own loopback interface, not the host or the memU service. The call silently fails with `Connection refused`.

This is not caught during development because the developer tests memorize calls from the host machine (where `localhost:8000` works) rather than from inside a container.

**Why it happens:**
Each Docker container has its own network namespace. `localhost` inside a container is the container's loopback (`127.0.0.1`), not the host's. The L3 entrypoint (`entrypoint.sh`) currently has no concept of external service URLs — it only accesses the workspace volume and the orchestration volume. The networking topology for the memory service was not established in v1.0-v1.2 because no external services were required.

**How to avoid:**
- Inject the memU service URL as an environment variable at spawn time: `MEMU_API_URL=http://host.docker.internal:8000` on Linux (or the host's Docker bridge IP, typically `172.17.0.1`)
- Add `extra_hosts: ["host.docker.internal:host-gateway"]` to the docker-compose service definition for L3 (or equivalent `--add-host host.docker.internal:host-gateway` in the spawn.py `docker.containers.run()` call)
- Alternatively, place the memU service and L3 containers on a shared named Docker network, and reference the memU service by its container name: `http://memu-service:8000`
- Document the chosen approach in `openclaw.json` as `memory.service_url` so that L2 (which also needs to call memU for decision memorization) and L3 use the same URL resolution path

**Warning signs:**
- `curl http://localhost:8000/health` from inside a running L3 container returns `Connection refused`
- memU memorize calls from host succeed, but the same call from the entrypoint fails
- L3 entrypoint exits with error code related to network connectivity rather than task failure
- `MEMU_API_URL` not present in `docker inspect` environment output for L3 containers

**Phase to address:** Phase 1 (memU Service Setup) — service URL resolution strategy must be decided before any container integration is attempted; add `MEMU_API_URL` to the spawn environment variable specification in Phase 2

---

### Pitfall 6: Per-Project Memory Scoping Implemented as Metadata Filter — Not Enforced at Storage Layer

**What goes wrong:**
memU stores memories in a single PostgreSQL database. Per-project isolation is achieved by including `project_id` and `agent_id` as metadata fields on each memory record and filtering on these fields during `retrieve()` calls. If the `project_id` filter is accidentally omitted from any retrieve call, the agent receives memories from all projects — including code patterns, decisions, and credentials from projects it should not see. This is a silent failure: the retrieve call succeeds, returns plausible-looking data, and the agent acts on cross-project contaminated memory without any error signal.

In the OpenClaw architecture, the multi-project pattern already has a precedent: the earlier mistake was a single state file shared across projects (v1.1's Pitfall 1). The same mistake pattern recurs here with a single memory database where the isolation is filter-based rather than schema-based.

**Why it happens:**
Developers write the first retrieve call with all filters correctly, test it, and it passes. Later retrieve calls added for different features (dashboard search, L2 decision context) omit the `project_id` filter because the code is written quickly and the test data only has one project's memories — so the contamination is not visible during development. The first multi-project production run surfaces the leak.

**How to avoid:**
- Create a `MemoryClient` wrapper class that is initialized with `project_id` and `agent_id` and always includes these in every `memorize()` and `retrieve()` call — make it impossible to call the raw memU API without scoping parameters
- Namespace memory categories with the project ID as a prefix: `pumplai/code-patterns` rather than just `code-patterns` — this provides human-readable isolation visible in the dashboard
- Write a test that explicitly creates memories for two projects and asserts that `retrieve()` for project A returns zero results from project B's records
- Treat cross-project memory leakage as a security failure in code review, not just a correctness issue

**Warning signs:**
- `retrieve(query="database schema")` returns memory items whose metadata shows a different `project_id` than the calling agent's project
- Dashboard memory panel shows memory categories from projects that are not the active project
- An L3 agent's task outcome references a tech stack (e.g., Rails) that belongs to a different project

**Phase to address:** Phase 2 (Per-Agent + Per-Project Memory Scoping) — the `MemoryClient` wrapper with mandatory scoping must be built before any memorize/retrieve calls are made in Phase 3 or Phase 4

---

### Pitfall 7: pgvector HNSW Index Degrades on Non-Vector Column Updates

**What goes wrong:**
Every time a memory record is updated (e.g., a memory item's relevance score is bumped, a category label is changed, or a `last_accessed` timestamp is written), PostgreSQL must update the HNSW index even though the vector column itself has not changed. This causes UPDATE operations to be 10-50x slower than inserts for tables with HNSW indexes. In the memU schema, if memory records are updated frequently (e.g., to record retrieval counts or merge similar memories), this update penalty accumulates and degrades overall write throughput.

This is a confirmed pgvector bug/design limitation documented in the pgvector GitHub issues (issue #875) and still present in pgvector 0.7.x.

**Why it happens:**
HNSW indexes are not designed for high-update workloads. They are optimized for insert-then-query patterns. PostgreSQL's MVCC means every UPDATE creates a new version of the row, forcing the HNSW index to process the new tuple even when the vector is unchanged.

**How to avoid:**
- Separate mutable metadata (access counts, timestamps, labels) from the vector/content columns: put them in a companion table `memory_metadata` with a foreign key to the immutable `memory_items` table. The HNSW index lives only on `memory_items`, which receives inserts but rarely updates
- Avoid updating memory records — prefer inserting new records with a `supersedes_id` reference rather than updating existing ones. This matches the append-only pattern that HNSW handles well
- Defer creation of the HNSW index until after initial bulk import of historical memories — create with `CONCURRENTLY` to avoid write blocking
- Set `maintenance_work_mem = 256MB` in the postgres container's `postgresql.conf` for faster HNSW index builds

**Warning signs:**
- PostgreSQL slow query log shows UPDATE statements on `memory_items` table taking >100ms
- memU-server response times for memorize degrade progressively as the memory store grows
- `EXPLAIN ANALYZE` on retrieve queries shows HNSW index scan time increasing nonlinearly with record count
- Docker postgres container memory usage continuously growing during operations that should only read

**Phase to address:** Phase 1 (memU Service Setup) — database schema decisions are final; the mutable/immutable split must be designed before schema is committed

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Call `memorize()` synchronously in L3 entrypoint completion block | Simpler code, guaranteed delivery | L3 container lifetime extended 10-30s per task; pool slot blocked; queue starvation | Never — always fire-and-forget or post-exit memorize via L2 |
| Use single shared PostgreSQL database for all projects without schema-level isolation | No per-project DB provisioning needed | Cross-project memory leakage on any missed `project_id` filter; single DB failure takes all projects offline | Acceptable for single-project use; must add `MemoryClient` wrapper before second project added |
| Inject raw retrieved memory transcripts directly into SOUL template | Maximum context richness | 40-100KB SOUL injection bloats every LLM call; old irrelevant memories crowd out recent context | Never — always summarize and budget-cap memory injection |
| Base memU-server Docker image on `debian:bookworm-slim` + manual Python install | Familiar base image, smaller final image | Must add Deadsnakes PPA or compile Python 3.13 from source; fragile build | Never — use `python:3.13-slim-bookworm` which is maintained and verifiably correct |
| Use Temporal for memU background jobs | Durable workflow execution | 3 extra services (Temporal server, Temporal UI, separate temporal DB) just to handle async memorize; overkill for 3 concurrent L3 workers | Only if memU-server's Temporal integration cannot be disabled; otherwise skip Temporal, use asyncio background tasks |
| Include ALL memory categories in pre-spawn SOUL injection | Complete memory picture for agent | Token cost grows O(N) with memory store size; agents paralyzed by irrelevant historical context | Never — always limit retrieve to 5 items and 2,000 character budget |

---

## Integration Gotchas

Common mistakes when connecting the memU service to existing subsystems.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| L3 entrypoint → memU REST API | Using `http://localhost:8000` which resolves to the L3 container's own loopback | Set `MEMU_API_URL` env var at spawn time using `host.docker.internal` or the Docker bridge IP; inject via spawn.py |
| soul_renderer.py → memory retrieval | Adding `$memory_context` variable without a character budget guard | Enforce 2,000 character max in the retrieval wrapper before calling `safe_substitute`; treat oversize context as a warning, not a fatal error |
| spawn.py → memU pre-spawn retrieve | Calling retrieve at spawn time from the host Python process (where memU is reachable via localhost) then injecting into container env | This pattern is correct and avoids the container networking problem — host calls memU, injects result as `SOUL_MEMORY_CONTEXT` env var before container starts |
| PostgreSQL pgvector initialization | Placing `CREATE EXTENSION vector` in a `.sql` file in `/docker-entrypoint-initdb.d/` | Use a `.sh` shell script (`00_init.sh`) with `psql -c "CREATE EXTENSION IF NOT EXISTS vector"` to avoid the SQL-only init ordering bug |
| L2 decision memorize → memU | L2 memorizes immediately on `merge`/`reject` decision before the state file is updated | Update state file first, then memorize — ensures that if memorize fails, the decision is not lost |
| dashboard → memory panel API | Using the raw memU REST API directly from the Next.js API routes | Route through an OpenClaw memory proxy API (`/api/memory/*`) that enforces project scoping and rate limiting |
| memU retrieve → L3 in-execution | L3 calling memU during task execution without a timeout | Set a 3-second timeout on all in-execution retrieve calls; log a warning and proceed without memory if the call times out |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous memorize in L3 completion block | Pool stays at 3/3 utilization after all tasks complete; next task waits | Fire-and-forget: detach memorize call before container exits | First concurrent run of 3 L3 tasks that all complete within the same minute |
| Unbounded retrieve returning all matching memories | Pre-spawn SOUL injection takes 10+ seconds; SOUL file >50KB | Always pass `limit=5` to retrieve; cache retrieved context with a 60s TTL keyed on `(project_id, task_description_hash)` | First project accumulating >50 memory records |
| HNSW index on a table with frequent non-vector updates | UPDATE statements on memory records take 100ms+ each | Separate mutable metadata into companion table; use append-only inserts with `supersedes_id` | When the memU memory store exceeds ~500 records and update frequency is >1/minute |
| Temporal service not ready when memU API starts | memU memorize calls hang for 30+ seconds waiting for Temporal gRPC; Docker healthcheck passes but memorize silently fails | Add health check that verifies Temporal gRPC is reachable before marking memU service healthy; or bypass Temporal entirely with asyncio task queue | Every cold start of the memU service Docker stack |
| PostgreSQL `shared_buffers` at default 128MB with HNSW index | Query times for retrieve degrade as index grows beyond shared_buffers cache | Set `shared_buffers=512m` and `effective_cache_size=1g` in postgres container's `postgresql.conf` or via env var `POSTGRES_SHARED_BUFFERS` | When memory store exceeds ~5,000 records (typical HNSW index at 1,536 dim exceeds 128MB shared_buffers well before this) |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing PostgreSQL port 5432 on the host interface | Any process on the host (or network if Docker host is exposed) can read/write all agent memories including credentials, code patterns, API keys | In docker-compose, bind postgres to `127.0.0.1:5432` not `0.0.0.0:5432`; within Docker network, containers can reach postgres by service name without exposing the host port |
| Memory injection accepts arbitrary retrieved content without sanitization | Prompt injection: a malicious task output stored in memory is retrieved and injected into the SOUL of a future agent, causing the future agent to execute the attacker's instructions | Sanitize retrieved memory content before SOUL injection: strip any lines starting with `#` (markdown headings that could be parsed as SOUL sections), limit to plain prose, reject content containing `$` or `{{` patterns |
| OpenAI API key in memU-server container environment accessible to L3 containers | If L3 container is compromised, it can inspect env vars of sibling containers via `/proc` or Docker API | Isolate the memU-server on a dedicated Docker network not shared with L3 containers; L3 accesses memU only through the host-network proxy, never directly to the memU container |
| All projects share one PostgreSQL credentials | A bug that executes arbitrary SQL (e.g., in a badly sanitized retrieve query) can access all projects' memory | Use separate PostgreSQL users per project with row-level security (`CREATE POLICY`) if the single-DB approach is used; minimum viable: use a read-only user for retrieve operations |
| memU service REST API has no authentication | Any process that can reach the host port can memorize arbitrary data or read all memories | Add a shared secret header (`X-Openclaw-Token`) checked by the memU proxy; since this is a single-host internal service, even a static shared secret provides adequate protection |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **memU service startup:** `docker-compose up` returns healthy — verify with `curl http://localhost:8000/health` AND `curl http://localhost:8000/retrieve` (health endpoint may pass while retrieve fails due to pgvector extension missing)
- [ ] **Python version in L3:** memU REST client in L3 entrypoint uses HTTP (curl or urllib), not Python import of memu-py — verify no `import memu` in L3 code paths
- [ ] **Cold-start database init:** Delete the postgres volume, restart docker-compose, and verify pgvector extension is present with `psql -c "SELECT extname FROM pg_extension WHERE extname='vector'"` — must pass on every cold start
- [ ] **Container networking:** Run the memorize call from inside a running L3 container (using `docker exec`) to verify it reaches the memU service — host-machine success does not prove in-container success
- [ ] **Project scoping enforcement:** Create memories for project A, then retrieve with project B's scoping parameters — must return zero results
- [ ] **SOUL injection budget:** After memory injection, measure the rendered SOUL.md byte count — must be under 8KB (2x the v1.2 baseline of ~3KB with headroom)
- [ ] **Fire-and-forget memorize:** Verify that L3 container exit happens within 5 seconds of task completion regardless of memU service latency — test by introducing an artificial 10s delay in the memU memorize endpoint
- [ ] **L2 memorize ordering:** Confirm that the state file reflects the `merge`/`reject` decision before the memorize call returns — not dependent on memorize success

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Python version mismatch in L3 (imported memu-py fails) | LOW | Remove `import memu` from L3 code; switch to HTTP REST calls via `urllib.request` or `curl` subprocess — no Python version dependency |
| pgvector extension missing after cold start | LOW | `docker exec -it memu-postgres psql -U postgres -d memu -c "CREATE EXTENSION IF NOT EXISTS vector"` — then add init script to prevent recurrence |
| Cross-project memory contamination (memories leaked between projects) | MEDIUM | Add `project_id` column filter retroactively to all records without it; DELETE records with NULL `project_id`; add NOT NULL constraint on `project_id` column going forward |
| SOUL injection bloated (SOUL >50KB) | LOW | Add character budget check in `soul_renderer.py` before `safe_substitute`; truncate `$memory_context` variable value to 2,000 chars before injection |
| Temporal not starting, memU memorize hangs | MEDIUM | Disable Temporal integration if possible; replace with asyncio background task queue; or add 5s timeout to memorize HTTP calls and treat failure as non-fatal |
| PostgreSQL data loss (single DB for all projects) | HIGH | Restore from volume backup; implement per-project backup cron (`pg_dump -t "memory_items WHERE project_id='X'"` for each project); treat as a signal to move to per-project schemas |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Python 3.13 version mismatch in L3/memU | Phase 1: memU Service Setup | `python3 --version` inside memU container returns 3.13.x; L3 integration uses HTTP REST only, no Python import |
| pgvector extension init ordering | Phase 1: memU Service Setup | Cold-start test: delete volume, restart, verify `pg_extension` table shows vector extension |
| Thundering-herd memorize from concurrent L3 completion | Phase 2: L3 Auto-Memorization | L3 containers exit within 5s of task completion; pool utilization drops immediately after task end |
| SOUL context size explosion | Phase 3: Pre-Spawn Context Retrieval | Rendered SOUL.md byte count is under 8KB; retrieve is called with `limit=5` |
| Container networking (localhost misroute) | Phase 1: memU Service Setup | Memorize call succeeds from inside a running L3 container via `docker exec` |
| Missing project_id scoping on retrieve | Phase 2: Per-Agent + Per-Project Scoping | Two-project test: project B retrieve returns zero project A memories |
| HNSW index update penalty | Phase 1: memU Service Setup | Schema separates mutable metadata from immutable vector/content; no direct UPDATEs on vector column |
| Temporal overhead | Phase 1: memU Service Setup | Decision to include or bypass Temporal documented; if included, healthcheck verifies gRPC before marking service ready |

---

## Sources

- Direct codebase inspection: `docker/l3-specialist/Dockerfile`, `docker/l3-specialist/entrypoint.sh`, `orchestration/soul_renderer.py`, `skills/spawn_specialist/spawn.py`, `agents/l3_specialist/config.json` — HIGH confidence
- memU official README and memU-server repository: [NevaMind-AI/memU](https://github.com/NevaMind-AI/memU), [NevaMind-AI/memU-server](https://github.com/NevaMind-AI/memU-server) — HIGH confidence
- Python 3.13 on Debian bookworm: [docker-library/python slim-bookworm Dockerfile](https://github.com/docker-library/python/blob/master/3.13/slim-bookworm/Dockerfile), [pascallj/python3.13-backport](https://github.com/pascallj/python3.13-backport) — HIGH confidence
- pgvector extension init ordering bug: [pgvector/pgvector Issue #355](https://github.com/pgvector/pgvector/issues/355), [pgvector/pgvector Issue #512](https://github.com/pgvector/pgvector/issues/512) — HIGH confidence
- pgvector HNSW index update performance issue: [pgvector/pgvector Issue #875](https://github.com/pgvector/pgvector/issues/875), [HNSW Indexes with Postgres and pgvector — Crunchy Data](https://www.crunchydata.com/blog/hnsw-indexes-with-postgres-and-pgvector) — HIGH confidence
- Docker container localhost networking: [Docker Docs: Host Network Driver](https://docs.docker.com/engine/network/drivers/host/), [How to Connect to Localhost Within a Docker Container — HowToGeek](https://www.howtogeek.com/devops/how-to-connect-to-localhost-within-a-docker-container/) — HIGH confidence
- Multi-tenant memory namespace design: [Amazon Bedrock AgentCore: Specify namespaces](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/specify-long-term-memory-organization.html), [Multi-Tenant Isolation Challenges in Enterprise LLM Agent Platforms](https://www.researchgate.net/publication/399564099_Multi-Tenant_Isolation_Challenges_in_Enterprise_LLM_Agent_Platforms) — MEDIUM confidence
- Concurrent LLM memorize latency: [Asynchronous LLM Function Calling — arXiv:2412.07017](https://arxiv.org/abs/2412.07017) — MEDIUM confidence
- Memory injection attacks via retrieval: [Palo Alto Unit 42: Persistent Behaviors in Agents' Memory](https://unit42.paloaltonetworks.com/indirect-prompt-injection-poisons-ai-longterm-memory/) — MEDIUM confidence (context: threat awareness)
- Temporal alternatives for small projects: [A lightweight alternative to Temporal for Node.js](https://dev.to/louis_dussarps_e656bc7b01/a-lightweight-alternative-to-temporal-for-nodejs-applications-9e4) — MEDIUM confidence

---
*Pitfalls research for: Adding memU persistent memory to OpenClaw v1.3*
*Researched: 2026-02-24*
