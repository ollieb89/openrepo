---
name: memu-memory
description: Integrate and operate the memU proactive memory system with OpenClaw agents. Use for setting up cloud or self-hosted memU, wiring memorize/retrieve flows into agent loops, configuring providers (OpenAI/OpenRouter/custom), running proactive demos, or troubleshooting memory ingestion and retrieval.
---

# memU Memory for OpenClaw

Guidance for bringing memU (https://github.com/NevaMind-AI/memU) into OpenClaw agents with concise recipes for cloud and self-hosted runs.

## Quick Start
- Install from source (self-hosted): `pip install -e .` inside a memU checkout (Python 3.13+).
- Cloud API: base `https://api.memu.so`, auth header `Authorization: Bearer <API_KEY>`.
- Required secrets by mode: `OPENAI_API_KEY` (OpenAI), `OPENROUTER_API_KEY` (OpenRouter), or provider-specific keys in `llm_profiles`.
- Minimal sanity tests: `python tests/test_inmemory.py` (in-memory) or `python tests/test_postgres.py` after starting pgvector (see below).
- Local smoke test script (in-memory): `python scripts/memu_quickstart.py` with `OPENAI_API_KEY` or `OPENROUTER_API_KEY` to ingest a sample conversation and retrieve context (`MEMU_METHOD=rag|llm` to toggle retrieval mode).
- Make target for fast sanity run: from this skill folder, `make memu-quickstart` (respects same env vars as the script).

## Core Concepts
- Memory behaves like a filesystem: categories (folders), items (files), cross-references (symlinks), resources (mount points).
- Main APIs:
  - `memorize(...)`: ingest conversations/documents/assets, auto-extract items/categories immediately.
  - `retrieve(..., method="rag"|"llm")`: surface relevant categories/items/resources; `rag` is fast/cheap, `llm` is deeper/anticipatory.
- Proactive loop: agents stream events to memU, then pull predicted context for next turns to reduce prompt size.

## Wire into an OpenClaw Agent
1) Instantiate service with provider config:
```python
from memu import MemUService

service = MemUService(
    llm_profiles={
        "default": {"api_key": os.environ["OPENAI_API_KEY"], "chat_model": "gpt-4o"},
        "embedding": {"api_key": os.environ["OPENAI_API_KEY"], "embed_model": "text-embedding-3-small"},
    },
    database_config={"metadata_store": {"provider": "inmemory"}},
)
```
2) Ingest each user/agent turn (append transcripts or logs):
```python
await service.memorize(
    resource_url="memory://session-123/log-45",
    modality="conversation",
    user={"user_id": "session-123"},
    content=[{"role": "user", "content": {"text": user_msg}}, {"role": "assistant", "content": {"text": reply}}]
)
```
3) Before planning next action, fetch context:
```python
context = await service.retrieve(
    queries=[{"role": "system", "content": {"text": "What matters for this user?"}}],
    where={"user_id": "session-123"},
    method="rag"
)
# use categories/items/resources to prime the prompt or tools
```
4) For anticipatory steps, switch to `method="llm"` or combine both (RAG for speed, LLM for deeper intent).

## Cloud API Cheatsheet
- Endpoints: `POST /api/v3/memory/memorize`, `GET /api/v3/memory/memorize/status/{task_id}`, `POST /api/v3/memory/categories`, `POST /api/v3/memory/retrieve`.
- Example curl (memorize):
```bash
curl -X POST https://api.memu.so/api/v3/memory/memorize \
  -H "Authorization: Bearer $MEMU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resource_url":"memory://session-123/chat","modality":"conversation","content":[{"role":"user","content":{"text":"Hello"}}]}'
```
- Retrieval:
```bash
curl -X POST https://api.memu.so/api/v3/memory/retrieve \
  -H "Authorization: Bearer $MEMU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"queries":[{"role":"user","content":{"text":"What do they prefer?"}}],"where":{"user_id":"session-123"},"method":"rag"}'
```

## Self-Hosted Recipes
- In-memory quick run:
```bash
export OPENAI_API_KEY=...
python tests/test_inmemory.py
```
- Postgres + pgvector (persistent):
```bash
docker run -d --name memu-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=memu -p 5432:5432 pgvector/pgvector:pg16
export OPENAI_API_KEY=...
python tests/test_postgres.py
```
- docker-compose (pgvector + optional adminer):
```yaml
services:
  memu-postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: memu
    ports: ["5432:5432"]
  adminer:
    image: adminer
    restart: always
    ports: ["8080:8080"]
    depends_on: [memu-postgres]
```
Bring up with `docker compose -f docker-compose.memu.yml up -d`; then run `python tests/test_postgres.py`.
- OpenRouter profile:
```python
service = MemUService(
    llm_profiles={"default": {"provider": "openrouter", "client_backend": "httpx", "api_key": os.environ["OPENROUTER_API_KEY"], "chat_model": "anthropic/claude-3.5-sonnet", "embed_model": "openai/text-embedding-3-small"}},
    database_config={"metadata_store": {"provider": "inmemory"}},
)
```

## Proactive Patterns to Apply in OpenClaw
- Stream every agent action/result through `memorize` to build longitudinal context; include user_id/session ids for scoping.
- Before tool calls that rely on history (preferences, prior outputs), call `retrieve` with the active `where` filter and inject returned items/categories into the plan prompt.
- For monitoring loops, keep a background task that periodically calls `retrieve(method="rag")` to surface upcoming needs; elevate to `method="llm"` when planning ambiguous next steps.
- Keep prompts slim by pasting only the highest-signal items/resources returned by memU; avoid full transcripts.

## Troubleshooting & Validation
- If retrieval feels stale, check `where` filters and confirm `memorize` uses consistent ids.
- High latency: prefer `method="rag"` and smaller `content` batches; downgrade `chat_model` or embeddings if cost/latency sensitive.
- Missing embeddings: ensure provider keys are set and embedding profile exists.
- Postgres issues: confirm pgvector image is running and reachable on 5432; rerun `test_postgres.py` after configuration changes.
