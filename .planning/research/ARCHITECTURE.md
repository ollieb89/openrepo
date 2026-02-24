# Architecture Research

**Domain:** memU Memory Integration for OpenClaw AI Swarm Orchestration
**Researched:** 2026-02-24
**Confidence:** HIGH — based on direct codebase analysis + memU-server source/docs

---

## Context: What Already Exists (v1.2)

This document is scoped exclusively to v1.3 memU integration. It describes how a standalone
memU service fits into the existing operational architecture, which integration points require
modification, and what is entirely new.

### Existing Components (Do Not Rewrite)

| Component | File | v1.3 Status |
|-----------|------|-------------|
| JarvisState | `orchestration/state_engine.py` | Unchanged — file-lock state sync untouched |
| spawn_specialist | `skills/spawn_specialist/spawn.py` | Modify: add pre-spawn retrieve + env injection |
| pool.py | `skills/spawn_specialist/pool.py` | Unchanged |
| soul_renderer.py | `orchestration/soul_renderer.py` | Modify: add `$memory_context` variable slot |
| entrypoint.sh | `docker/l3-specialist/entrypoint.sh` | Modify: add post-task memorize call |
| snapshot.py | `orchestration/snapshot.py` | Modify: expose git diff output for memorize payload |
| occc API routes | `workspace/occc/src/app/api/` | Add: new `/api/memory/*` routes |
| occc dashboard pages | `workspace/occc/src/app/` | Add: new memory panel page |

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENCLAW HOST (Ubuntu 24.04)                         │
│                                                                               │
│  ┌──────────────┐   ┌────────────────────────────────────────────────────┐  │
│  │  L1          │   │  OpenClaw Docker Bridge Network (openclaw-net)      │  │
│  │  ClawdiaPrime│   │                                                      │  │
│  │  (L1 agent)  │   │  ┌─────────────────┐    ┌──────────────────────┐   │  │
│  └──────┬───────┘   │  │  memU-server    │    │  PostgreSQL+pgvector │   │  │
│         │ CLI call  │  │  FastAPI :8765  │◄──►│  :5432               │   │  │
│  ┌──────▼───────┐   │  │  (nevamindai/   │    │  (pgvector/pgvector: │   │  │
│  │  L2          │   │  │  memu-server)   │    │   pg16)              │   │  │
│  │  PumplAI_PM  │   │  └────────▲────────┘    └──────────────────────┘   │  │
│  │  (L2 agent)  │   │           │                                          │  │
│  └──────┬───────┘   │           │ HTTP REST (host → container via port)    │  │
│         │           │           │                                           │  │
│  spawn_specialist.py│   ┌───────┴──────┐                                   │  │
│  (pre-spawn: GET)   │   │  memory_     │                                    │  │
│  (post-review: POST)│   │  client.py   │                                    │  │
│         │           │   │  (new)       │                                    │  │
│  ┌──────▼───────┐   │   └──────────────┘                                   │  │
│  │  L3          │   │                                                        │  │
│  │  Ephemeral   │   │  ┌─────────────────────────────────────────────────┐ │  │
│  │  Container   │───┼─►│  L3 Container (openclaw-{project}-l3-{task_id}) │ │  │
│  │  (spawned)   │   │  │  - MEMU_SERVICE_URL env var injected            │ │  │
│  └──────────────┘   │  │  - entrypoint.sh: POST /memorize on completion  │ │  │
│                      │  │  - optional mid-task GET /retrieve              │ │  │
│  ┌──────────────┐   │  └─────────────────────────────────────────────────┘ │  │
│  │  occc        │   │                                                        │  │
│  │  Next.js     │───┼─► HTTP → memU-server :8765 (via /api/memory/* proxy) │  │
│  │  :6987       │   │                                                        │  │
│  └──────────────┘   └────────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### New Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| memU-server container | FastAPI wrapper: memorize/retrieve/categories REST API | Docker container via `nevamindai/memu-server:latest` |
| PostgreSQL+pgvector container | Persistent vector store for memory items | Docker container via `pgvector/pgvector:pg16` |
| `orchestration/memory_client.py` | Python client for memU-server (memorize, retrieve, health) | New file |
| `docker/memory/docker-compose.yml` | Bring up memU-server + PostgreSQL together | New file |
| `workspace/occc/src/app/api/memory/route.ts` | Proxy endpoint: list categories + items | New file |
| `workspace/occc/src/app/api/memory/search/route.ts` | Proxy endpoint: semantic search | New file |
| Memory Panel page | Dashboard UI for browsing/searching agent memories | New Next.js page |

### Modified Components

| Component | What Changes | Why |
|-----------|-------------|-----|
| `skills/spawn_specialist/spawn.py` | 1. Call `memory_client.retrieve()` before container spawn. 2. Inject `MEMU_SERVICE_URL` + `MEMU_AGENT_ID` env vars into container config. | Pre-spawn context retrieval + L3 access to memU |
| `orchestration/soul_renderer.py` `build_variables()` | Add `memory_context` key with retrieved text (may be empty string). | Inject retrieved memories into SOUL prompt |
| `agents/_templates/soul-default.md` | Add `## Memory Context` section consuming `$memory_context`. | Surface pre-retrieved memories to L2 agent |
| `docker/l3-specialist/entrypoint.sh` | After task completes, POST git diff + task log to `/memorize`. | Automated L3 outcome memorization |
| `orchestration/snapshot.py` | Expose git diff text as return value (currently writes to disk only). | Feed diff into memorize payload without re-reading file |
| `openclaw.json` | Add `memory_service` config block (url, agent scoping, enabled flag). | Central config for memory feature toggle |

---

## Docker Networking

### Approach: Shared Bridge Network (not per-project networks)

PROJECT.md explicitly records "Per-project Docker networks — no inter-container networking
needed" as out of scope. The correct approach is a **single named bridge network** shared by
all OpenClaw-managed containers.

```bash
# Create once during setup
docker network create openclaw-net
```

The following containers join `openclaw-net`:
- `memu-server` (FastAPI, :8765)
- `memu-postgres` (PostgreSQL, :5432 internal only)
- L3 specialist containers (ephemeral, need outbound access to memu-server)

**L3 access pattern:** L3 containers call memU-server via the Docker bridge IP or container
hostname. Because L3 containers are ephemeral and spawned dynamically, the simplest approach
is to inject `MEMU_SERVICE_URL=http://memu-server:8765` as an env var. Docker's built-in DNS
resolves `memu-server` within `openclaw-net`.

**L2/orchestration access pattern:** The host-side Python process (spawn.py, pool.py) calls
memU-server via `http://localhost:8765` (port mapped to host). No network config changes
needed for host-side calls.

**occc dashboard access pattern:** Next.js API routes run server-side and call
`http://localhost:8765` (same host). Client-side browser calls go to `/api/memory/*` which
proxies to memU-server — browser never calls memU-server directly.

### docker-compose for Memory Service

```yaml
# docker/memory/docker-compose.yml
version: "3.9"
services:
  memu-postgres:
    image: pgvector/pgvector:pg16
    container_name: memu-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: memu
    volumes:
      - memu-pgdata:/var/lib/postgresql/data
    networks:
      - openclaw-net
    restart: unless-stopped

  memu-server:
    image: nevamindai/memu-server:latest
    container_name: memu-server
    ports:
      - "8765:8000"
    environment:
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
      DATABASE_URL: "postgresql://postgres:postgres@memu-postgres:5432/memu"
    depends_on:
      - memu-postgres
    networks:
      - openclaw-net
    restart: unless-stopped

networks:
  openclaw-net:
    external: true

volumes:
  memu-pgdata:
```

**Port choice:** 8765 avoids collision with existing ports (gateway: 18789, dashboard: 6987,
dashboard container: 18795).

---

## Memory Scoping Model

memU supports `user_id` and `agent_id__in` for filtering. OpenClaw maps these fields as:

| memU field | OpenClaw value | Example |
|------------|---------------|---------|
| `user_id` | `project_id` | `"pumplai"` |
| `agent_id` | Agent tier + ID | `"l2:pumplai_pm"`, `"l3:l3_specialist"` |

This gives per-project isolation (all memories for project `pumplai` share `user_id=pumplai`)
and per-agent sub-scoping for attribution (L2 decisions vs L3 outcomes are separately
queryable).

**Retrieve filter for pre-spawn L3 context:**
```python
where={"user_id": project_id, "agent_id__in": ["l2:pumplai_pm", "l3:l3_specialist"]}
```

**Retrieve filter for L2 decision context (similar tasks only):**
```python
where={"user_id": project_id, "agent_id__in": ["l2:pumplai_pm"]}
```

---

## Data Flows

### Flow 1: Pre-Spawn Retrieve (L2 calls memU before spawning L3)

```
L2 agent decides to spawn L3
    ↓
spawn_l3_specialist() called in spawn.py
    ↓
memory_client.retrieve(
    query=task_description,
    method="rag",
    where={"user_id": project_id}
) → memory_context: str
    ↓
soul_renderer.build_variables() receives memory_context
    ↓
string.Template substitutes $memory_context in soul-default.md
    ↓
SOUL.md rendered with relevant past outcomes injected
    ↓
L3 container spawned with enriched task context
```

**Timing constraint:** retrieve must complete before container spawn. Use a short timeout
(3s default, configurable) — if memU-server is unreachable, log warning and spawn with empty
context (graceful degradation).

### Flow 2: Post-Task Memorize (L3 auto-memorization on completion)

```
L3 entrypoint.sh task execution completes
    ↓
git diff --cached captured → /tmp/task-diff.patch
update_state "completed" called (existing)
    ↓
[NEW] curl POST http://memu-server:8765/memorize \
  -d '{"messages": [{"role": "system", "content": "Task: {desc}"},
                     {"role": "assistant", "content": "Outcome: {diff}"}],
       "user_id": "{project_id}",
       "agent_id": "l3:{agent_id}"}'
    ↓
memU-server processes async — L3 exits immediately after POST
(fire-and-forget: memorize is async pipeline in memU-server)
```

**Why fire-and-forget:** memU-server memorize is a pipeline operation (extract → embed →
store) that takes seconds. L3 containers should not block on it. The POST returns a `task_id`
immediately; actual processing is async. L3 just needs to fire the POST before exiting.

### Flow 3: L2 Post-Review Memorize (decision logging)

```
L2 reviews snapshot diff
    ↓
Decision: merge (approved) or reject
    ↓
[NEW] memory_client.memorize(
    messages=[
        {"role": "system", "content": "Review task {task_id}: {description}"},
        {"role": "assistant", "content": "Decision: {merge|reject}. Reasoning: {rationale}"}
    ],
    user_id=project_id,
    agent_id=f"l2:{l2_agent_id}"
)
    ↓
Fire-and-forget (async) — L2 continues workflow
```

This is called from wherever L2 implements the merge/reject decision logic. In the current
architecture that is an L2 agent action, not a Python file — the call site will be in
`snapshot.py` or a new `orchestration/review.py` helper depending on how L2 invokes review.

### Flow 4: L3 Mid-Task Retrieve (optional, on-demand)

```
L3 container executing task via CLI runtime
    ↓
CLI runtime calls: curl -s "http://memu-server:8765/retrieve" \
  -d '{"queries": ["how to fix X"], "method": "rag",
       "where": {"user_id": "{project_id}"}}'
    ↓
memU-server returns relevant memory items as JSON
    ↓
CLI runtime injects into its context window
```

This is the L3 direct access path. The CLI runtime (claude-code, codex, gemini-cli) can
make HTTP calls during execution. The `MEMU_SERVICE_URL` and `MEMU_AGENT_ID` env vars are
always injected so L3 containers can query memU regardless of whether L2 pre-fetched context.

### Flow 5: Dashboard Memory Browse (occc reads memU)

```
User navigates to /memory page in occc
    ↓
Browser → GET /api/memory?project=pumplai&category=all
    ↓
Next.js API route: GET http://localhost:8765/categories
  (with user_id=project_id filter)
    ↓
Returns category list + item counts
    ↓
Browser → GET /api/memory/search?q=docker+error&project=pumplai
    ↓
Next.js API route: POST http://localhost:8765/retrieve
  (with query + user_id filter)
    ↓
Returns matching memory items
```

---

## New File Structure

```
orchestration/
└── memory_client.py         # Python HTTP client for memU-server (new)

docker/
└── memory/
    ├── docker-compose.yml   # memU-server + PostgreSQL services (new)
    └── .env.example         # OPENAI_API_KEY placeholder (new)

workspace/occc/src/app/
├── api/
│   └── memory/
│       ├── route.ts         # GET categories + items (new)
│       └── search/
│           └── route.ts     # POST retrieve / semantic search (new)
└── memory/
    └── page.tsx             # Memory browser page (new)

workspace/occc/src/lib/
└── memory.ts                # useMemory() SWR hook (new)
```

---

## `memory_client.py` Design

```python
# orchestration/memory_client.py
import httpx
from typing import Optional

class MemoryClient:
    """Thin HTTP client for memU-server REST API.

    Raises MemoryServiceUnavailable on connection errors — callers
    should catch and degrade gracefully (log + continue without memory).
    """

    def __init__(self, base_url: str, timeout: float = 3.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def memorize(
        self,
        messages: list[dict],
        user_id: str,
        agent_id: str,
    ) -> dict:
        """Fire-and-forget memorize. Returns task_id from memU-server."""
        resp = httpx.post(
            f"{self.base_url}/memorize",
            json={"messages": messages, "user_id": user_id, "agent_id": agent_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def retrieve(
        self,
        queries: list[str],
        user_id: str,
        method: str = "rag",
        agent_id_filter: Optional[list[str]] = None,
    ) -> str:
        """Retrieve relevant memory context as formatted string."""
        where: dict = {"user_id": user_id}
        if agent_id_filter:
            where["agent_id__in"] = agent_id_filter
        resp = httpx.post(
            f"{self.base_url}/retrieve",
            json={"queries": queries, "method": method, "where": where},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        # Flatten categories + items into prompt-injectable text
        return _format_memory_context(data)

    def health(self) -> bool:
        """Returns True if memU-server is reachable."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=1.0)
            return resp.status_code == 200
        except Exception:
            return False


def get_memory_client() -> MemoryClient:
    """Create MemoryClient from openclaw.json memory_service config."""
    from orchestration.project_config import _find_project_root
    import json, os
    root = _find_project_root()
    config = json.loads((root / "openclaw.json").read_text())
    svc = config.get("memory_service", {})
    url = svc.get("url", os.environ.get("MEMU_SERVICE_URL", "http://localhost:8765"))
    timeout = svc.get("timeout_s", 3.0)
    return MemoryClient(base_url=url, timeout=timeout)
```

**Dependency:** `httpx` (sync client, no new async complexity). Add to orchestration
dependencies. Alternative: use stdlib `urllib.request` to maintain zero-external-deps
policy — acceptable since this is an optional feature path with graceful degradation.

**Decision point:** `httpx` vs stdlib. Prefer `httpx` for cleaner timeout handling and
JSON support. Add to `docker/l3-specialist/requirements.txt` as well since L3 entrypoint
needs it for curl-equivalent calls (or use bash `curl` in entrypoint.sh directly).

---

## SOUL Template Injection

The existing `soul_renderer.py` `build_variables()` already returns a dict of template
variables. Adding memory context requires:

1. Add `memory_context` key to the dict (empty string default)
2. Populate it by calling `MemoryClient.retrieve()` at render time or pass it in as a
   parameter from spawn.py (preferred — avoids memory_client import inside soul_renderer)

**Preferred pattern: parameter injection**

```python
# spawn.py (modified)
memory_context = ""
try:
    client = get_memory_client()
    memory_context = client.retrieve(
        queries=[task_description],
        user_id=project_id,
    )
except Exception as e:
    logger.warning("Memory retrieve failed, spawning without context", extra={"error": str(e)})

soul_content = render_soul(project_id, extra_vars={"memory_context": memory_context})
```

```python
# soul_renderer.py (modified)
def build_variables(project_config, extra_vars=None) -> dict:
    base = { ...existing vars... }
    base["memory_context"] = ""  # default empty
    if extra_vars:
        base.update(extra_vars)
    return base
```

```markdown
<!-- soul-default.md — new section added -->
## Memory Context

$memory_context
```

If `$memory_context` is empty, the section renders as an empty `## Memory Context` heading
which is harmless. Alternatively, use a conditional marker and strip the section in
`merge_sections()` when the value is empty.

---

## L3 Container Environment Variables (New)

Added to `container_config["environment"]` in `spawn.py`:

| Variable | Value | Purpose |
|----------|-------|---------|
| `MEMU_SERVICE_URL` | `http://memu-server:8765` | memU-server address inside Docker net |
| `MEMU_AGENT_ID` | `l3:{l3_agent_id}` | Agent attribution for stored memories |
| `MEMU_PROJECT_ID` | `{project_id}` | Memory scoping (user_id in memU terms) |
| `MEMU_ENABLED` | `"true"` / `"false"` | Feature toggle — skip memorize if false |

The L3 entrypoint uses these to POST to memU-server without needing Python — curl is
sufficient for the fire-and-forget memorize POST.

---

## openclaw.json Config Block (New)

```json
{
  "memory_service": {
    "enabled": true,
    "url": "http://localhost:8765",
    "timeout_s": 3,
    "retrieve_method": "rag",
    "memorize_on_l3_complete": true,
    "memorize_on_l2_review": true,
    "inject_into_soul": true
  }
}
```

The `enabled` flag gates all memory operations system-wide. When `false`, spawn.py skips
the retrieve call, entrypoint.sh skips the memorize POST, and dashboard API routes return
empty responses. This is the feature-toggle pattern used throughout OpenClaw.

---

## Dashboard API Routes

### GET `/api/memory?project={id}`

Returns categories + item counts for the project. Calls:
```
GET http://localhost:8765/categories  (with user_id filter)
```

Response shape:
```typescript
interface MemoryCategory {
  name: string
  itemCount: number
  lastUpdated: string
}
interface MemoryResponse {
  categories: MemoryCategory[]
  projectId: string
}
```

### POST `/api/memory/search`

Semantic search over memories. Calls:
```
POST http://localhost:8765/retrieve  (with query + user_id filter)
```

Request body: `{ query: string, project: string, method?: "rag" | "llm" }`

Response shape:
```typescript
interface MemoryItem {
  id: string
  content: string
  category: string
  agentId: string
  createdAt: string
  score?: number
}
interface SearchResponse {
  items: MemoryItem[]
  query: string
}
```

### Dashboard Memory Panel Page

`/memory` page in occc with:
- Project-scoped display (inherits current project from `ProjectProvider`)
- Category list sidebar (SWR polling, 30s interval — memory changes slowly)
- Item table for selected category
- Search bar that hits `/api/memory/search`
- Agent attribution column (shows L2 vs L3 source)

---

## Architectural Patterns

### Pattern 1: Graceful Degradation on Memory Unavailability

**What:** All memory operations wrapped in try/except. On failure, log warning and continue
without memory context.
**When to use:** Always — memU-server is a non-critical auxiliary service.
**Implementation:** `MemoryClient` raises `MemoryServiceUnavailable`. Callers catch it,
log at WARNING level, and proceed with `memory_context = ""`.

### Pattern 2: Fire-and-Forget Memorize

**What:** POST to `/memorize` without waiting for processing to complete. memU-server returns
`task_id` immediately; actual extraction/embedding is async in its Temporal workflow.
**When to use:** All memorize calls from L3 entrypoint.sh and L2 review decisions.
**Why:** Memorize pipeline takes 2-10 seconds (LLM extraction + embed + store). Blocking
L3 container exit or L2 review flow on this is unacceptable.

### Pattern 3: Config-Gated Feature

**What:** `memory_service.enabled` in `openclaw.json` gates all memory operations.
**When to use:** All new memory code paths check `enabled` before doing anything.
**Why:** Allows v1.3 to ship with memory disabled by default for projects that don't need it,
and for testing without a running memU-server.

### Pattern 4: Host-Port Access for L2, Container-DNS for L3

**What:** L2/orchestration (host Python) calls `http://localhost:8765`. L3 containers call
`http://memu-server:8765` via Docker DNS on `openclaw-net`.
**Why:** L3 containers are inside Docker network; they cannot use `localhost` to reach the
host. L2 is a host process; it cannot use Docker DNS names.
**Implementation:** `MEMU_SERVICE_URL` env var in L3 container always set to
`http://memu-server:8765`. `memory_client.py` reads from `openclaw.json` which specifies
`http://localhost:8765` for host-side access.

---

## Anti-Patterns

### Anti-Pattern 1: Blocking L3 Container Exit on Memorize

**What people do:** `curl -s ... /memorize && wait_for_task_id` in entrypoint.sh
**Why it's wrong:** memU memorize pipeline is async (Temporal workflow). Blocking adds 2-10s
to every L3 container lifecycle with no benefit.
**Do this instead:** Fire the POST, check for HTTP 200/202, log the returned task_id, exit.

### Anti-Pattern 2: Storing Full Git Diffs as Raw Memory

**What people do:** `content = open("task.diff").read()` → memorize entire diff verbatim
**Why it's wrong:** Large diffs (thousands of lines) hit token limits in LLM extraction step
and store noisy/irrelevant content. Vector retrieval matches patch syntax not semantics.
**Do this instead:** Summarize: task description + changed file names + exit code + key log
lines. Diffs > 200 lines should be truncated or summarized before memorize POST.

### Anti-Pattern 3: Per-Request L2 Memory Retrieve During Monitoring

**What people do:** Call `memory_client.retrieve()` inside the monitor poll loop
**Why it's wrong:** Monitor polls every 1s. Memory retrieval is 50-200ms per call.
This adds 5-20% overhead to monitoring with zero benefit (monitoring doesn't need memory).
**Do this instead:** Only retrieve at spawn time (pre-spawn). Never in monitor/status paths.

### Anti-Pattern 4: Using localhost in L3 Container

**What people do:** `MEMU_SERVICE_URL=http://localhost:8765` in L3 container environment
**Why it's wrong:** Inside a Docker container, `localhost` resolves to the container itself,
not the host. The call fails silently or hangs.
**Do this instead:** `MEMU_SERVICE_URL=http://memu-server:8765` — Docker DNS resolves
`memu-server` via `openclaw-net` bridge network.

---

## Build Order (Component Dependencies)

The following order respects dependency relationships. Each phase is a logical build unit.

```
Phase 1: Infrastructure (no code deps)
  - docker/memory/docker-compose.yml
  - docker network create openclaw-net
  - Add L3 containers to openclaw-net in spawn.py (network= param)
  - Verify: docker compose up → memu-server health check passes

Phase 2: Python Client (depends on Phase 1)
  - orchestration/memory_client.py
  - Add httpx to L3 requirements (or confirm curl sufficient)
  - Add memory_service block to openclaw.json (enabled: false initially)
  - Verify: memory_client.health() returns True

Phase 3: L3 Memorize (depends on Phase 2)
  - entrypoint.sh: add post-task memorize POST
  - MEMU_* env vars injected in spawn.py
  - Verify: spawn test task → memory item appears in memU-server

Phase 4: L2 Pre-Spawn Retrieve + SOUL Injection (depends on Phase 3)
  - spawn.py: retrieve call before container creation
  - soul_renderer.py: extra_vars support + memory_context variable
  - soul-default.md: Memory Context section
  - Verify: spawned task SOUL.md contains retrieved context from Phase 3

Phase 5: L2 Review Memorize (depends on Phase 2)
  - orchestration/memory_client.py used from review logic
  - Verify: merge/reject decision stored, retrievable in Phase 4

Phase 6: Dashboard (depends on Phase 1)
  - workspace/occc/src/app/api/memory/route.ts
  - workspace/occc/src/app/api/memory/search/route.ts
  - workspace/occc/src/app/memory/page.tsx
  - workspace/occc/src/lib/memory.ts
  - Verify: dashboard /memory page shows categories + search works
```

---

## Integration Points: New vs Modified

### New (create from scratch)

| Artifact | Type | Purpose |
|----------|------|---------|
| `docker/memory/docker-compose.yml` | Config | memU-server + PostgreSQL services |
| `orchestration/memory_client.py` | Python | HTTP client for memU-server |
| `workspace/occc/src/app/api/memory/route.ts` | API route | Categories endpoint |
| `workspace/occc/src/app/api/memory/search/route.ts` | API route | Search endpoint |
| `workspace/occc/src/app/memory/page.tsx` | UI | Memory browser page |
| `workspace/occc/src/lib/memory.ts` | Hook | `useMemory()` SWR hook |

### Modified (surgical changes only)

| Artifact | Change | Risk |
|----------|--------|------|
| `skills/spawn_specialist/spawn.py` | +retrieve call +env vars | LOW — wrapped in try/except, graceful degradation |
| `orchestration/soul_renderer.py` | +extra_vars param | LOW — additive, backward compat |
| `agents/_templates/soul-default.md` | +Memory Context section | LOW — empty renders harmlessly |
| `docker/l3-specialist/entrypoint.sh` | +memorize POST after completion | LOW — fire-and-forget, not on critical path |
| `openclaw.json` | +memory_service block | LOW — new key, existing code ignores unknown keys |

---

## Scaling Considerations

This is a single-host system. Scaling concerns are operational, not distributed:

| Concern | At current scale (3 concurrent L3) | Notes |
|---------|-------------------------------------|-------|
| memU-server throughput | Not a bottleneck — 3 memorize calls/task-completion cycle | Async pipeline absorbs bursts |
| PostgreSQL storage | pgvector indexes grow with usage — acceptable indefinitely on SSD | Add pg_partman if > 1M items |
| Retrieve latency | RAG: ~50ms, LLM: ~2s — set retrieve_method="rag" for pre-spawn | LLM method only for dashboard search |
| Memory disk usage | pgvector embedding (1536 dims × 4 bytes = 6KB/item) — 1M items ≈ 6GB | Monitor with pg_database_size() |

---

## Sources

- memU GitHub README: https://github.com/NevaMind-AI/memU/blob/main/README.md
- memU-server GitHub (backend wrapper): https://github.com/NevaMind-AI/memU-server
- memu-py PyPI: https://pypi.org/project/memu-py/
- pgvector Docker image: https://hub.docker.com/r/pgvector/pgvector
- OpenClaw codebase: `skills/spawn_specialist/spawn.py`, `orchestration/soul_renderer.py`, `orchestration/state_engine.py`, `docker/l3-specialist/entrypoint.sh`

---

*Architecture research for: memU integration into OpenClaw v1.3*
*Researched: 2026-02-24*
