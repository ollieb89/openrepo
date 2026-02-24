# Requirements: OpenClaw

**Defined:** 2026-02-24
**Core Value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## v1.3 Requirements

Requirements for Agent Memory milestone. Each maps to roadmap phases.

### Infrastructure

- [ ] **INFRA-01**: memU service runs as a standalone Docker container (python:3.13-slim-bookworm base) with FastAPI wrapper around memu-py
- [ ] **INFRA-02**: PostgreSQL+pgvector runs as a Docker container with persistent volume and correct extension initialization
- [ ] **INFRA-03**: Docker Compose defines memory stack (memU service + PostgreSQL) on shared bridge network accessible to L2 and L3 containers
- [ ] **INFRA-04**: Internal REST API exposes POST /memorize, POST /retrieve, GET /memories, DELETE /memories/{id} endpoints with Pydantic validation
- [ ] **INFRA-05**: Memory service health check endpoint (GET /health) verifiable by orchestration layer

### Scoping

- [ ] **SCOPE-01**: All memory operations enforce per-project scoping via mandatory project_id parameter at the API wrapper level
- [ ] **SCOPE-02**: Memory operations support per-agent scoping via agent_type parameter (l2_pm, l3_code, l3_test)
- [ ] **SCOPE-03**: MemoryClient wrapper in orchestration layer enforces scoping — impossible to call memorize/retrieve without project_id

### Memory Operations

- [ ] **MEM-01**: L3 task outcomes (semantic snapshots) are auto-memorized after successful container exit via fire-and-forget pattern
- [ ] **MEM-02**: L2 review decisions (merge/reject with reasoning) are memorized after each review cycle
- [ ] **MEM-03**: Memorization failure is non-blocking — L3 task lifecycle and L2 review flow continue uninterrupted if memory service is unavailable
- [ ] **MEM-04**: MEMU_API_URL environment variable is injected into L3 containers at spawn time

### Retrieval & Injection

- [ ] **RET-01**: Pre-spawn context retrieval calls memU retrieve (RAG mode) before L3 container creation
- [ ] **RET-02**: Retrieved memories are injected into SOUL template via soul_renderer.py with a memory context section
- [ ] **RET-03**: Retrieved memory injection has a hard 2,000-character budget cap to prevent SOUL template bloat
- [ ] **RET-04**: Pre-spawn retrieval degrades gracefully to empty context if memory service is unavailable
- [ ] **RET-05**: L3 containers can query memU service during execution via HTTP for task-specific lookups

### Dashboard

- [ ] **DSH-11**: /memory page in occc displays project-scoped memory categories and items
- [ ] **DSH-12**: Memory panel supports semantic search (vector-based) via retrieve endpoint
- [ ] **DSH-13**: Memory panel supports delete action for individual memory items
- [ ] **DSH-14**: Memory panel displays memory item metadata (type, category, created_at, agent source)

## Future Requirements

Deferred to subsequent milestone. Tracked but not in current roadmap.

### Quality Loop

- **QUAL-01**: L2 rejection feedback loop surfaces past rejections as warnings to future L3s
- **QUAL-02**: Memory health monitoring dashboard (total items, retrieval latency, category distribution)

### Advanced Memory

- **ADV-01**: Cross-project pattern sharing via global/ namespace with explicit opt-in
- **ADV-02**: Memory TTL/forgetting policies for stale items
- **ADV-03**: Memory-driven L1 strategic suggestions based on historical patterns

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time memory sync during L3 execution | Partial writes from mid-task are misleading; semantic snapshot at completion is coherent |
| Shared memory pool across projects | Cross-project contamination; violates per-project isolation model |
| LLM-mode retrieval for pre-spawn | Too slow (seconds) and expensive for the spawn path; RAG mode sufficient |
| Memory editing from dashboard | Creates divergence; delete + re-memorize is the correct correction pattern |
| Full conversation transcript memorization | Token-heavy, noisy; semantic snapshots are structured and information-dense |
| Cloud memu.so API | Self-hosted library chosen; no external API dependency |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| INFRA-04 | — | Pending |
| INFRA-05 | — | Pending |
| SCOPE-01 | — | Pending |
| SCOPE-02 | — | Pending |
| SCOPE-03 | — | Pending |
| MEM-01 | — | Pending |
| MEM-02 | — | Pending |
| MEM-03 | — | Pending |
| MEM-04 | — | Pending |
| RET-01 | — | Pending |
| RET-02 | — | Pending |
| RET-03 | — | Pending |
| RET-04 | — | Pending |
| RET-05 | — | Pending |
| DSH-11 | — | Pending |
| DSH-12 | — | Pending |
| DSH-13 | — | Pending |
| DSH-14 | — | Pending |

**Coverage:**
- v1.3 requirements: 21 total
- Mapped to phases: 0
- Unmapped: 21 ⚠️

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after initial definition*
