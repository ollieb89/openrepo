# Feature Research

**Domain:** Agent Memory Integration — AI Swarm Orchestration (OpenClaw v1.3)
**Researched:** 2026-02-24
**Confidence:** HIGH (memU API and architecture), MEDIUM (UI patterns), HIGH (orchestration integration patterns)

---

## Context: What Already Exists (Do Not Re-Build)

v1.2 shipped a fully operational orchestration system. This feature research covers ONLY the new
memory capabilities introduced in v1.3. Assume the following exist and are stable:

- L1→L2→L3 delegation chain, Docker isolation, Jarvis Protocol state sync
- Semantic snapshots (git diffs with metadata) for every L3 task completion
- Per-project config via `project_config.py`, SOUL templating, PoolRegistry
- occc dashboard with SSE real-time streaming, project switching, metrics
- Structured JSON logging across all orchestration components

The integration problem: these components operate statelessly across restarts. Every L3 container
starts from scratch. Every L2 review decision is lost after the task closes. memU adds the
persistent layer that makes the swarm learn over time.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any agent memory system must provide. Missing these = memory layer feels like
a prototype that doesn't actually work in production.

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| **Standalone memU service (Docker + PostgreSQL+pgvector)** | Memory must survive host restarts. An in-process store is a toy. Standard pattern: every production AI system externalizes memory to a persistent store with vector search. | MEDIUM | Docker Compose or equivalent service definition; PostgreSQL+pgvector image available. memU 1.4.0 supports self-hosted postgres mode natively. |
| **Internal REST API for memory operations** | Python orchestration code and Next.js dashboard both need to call memory. A shared HTTP API is the only integration point that doesn't require a Python import in the TS code. Standard pattern in any service-oriented system. | MEDIUM | Standalone memU service running. memu-py SDK exposes `memorize()` and `retrieve()`. Need thin HTTP wrapper if memU doesn't expose REST directly, or use memU cloud API locally forwarded. |
| **L3 auto-memorization of task outcomes** | If memory must be triggered manually, it won't happen. The git diff (semantic snapshot) already exists per task. Automatically writing that diff + conversation log to memory after L3 completes is the minimum viable learning loop. | MEDIUM | Semantic snapshot system (exists in v1.2). Post-task hook in spawn.py or pool.py. memU `memorize(resource_url=snapshot_path, modality="document")`. |
| **L2 memorization of review decisions** | L2 reviews every L3 diff and decides merge or reject with reasoning. Storing these decisions lets the swarm learn what "good" looks like for each project. Without this, L2 keeps repeating the same review errors. | MEDIUM | L2 review flow in orchestration (exists). memU `memorize()` called with review outcome and reasoning text. |
| **Per-agent + per-project memory scoping** | Memory from Project A must never contaminate retrieval in Project B. Agent-level scoping prevents L3 code specialist memory polluting L3 test specialist retrieval. Standard namespace isolation pattern in all memory frameworks (Mem0, Zep, memU). | MEDIUM | memU `user` parameter maps to agent_id. Project-level isolation via category or namespace prefix convention. |
| **Pre-spawn context retrieval** | Before an L3 container starts, retrieve relevant past outcomes and inject into the task description or SOUL. Without this, memory exists but is never actually used — the swarm doesn't learn. | HIGH | memU `retrieve(method="rag")` called in pool.py before `docker run`. Result formatted and appended to L3 task prompt or SOUL template. |
| **Dashboard memory panel (browse + search)** | Operators need to see what the swarm has memorized. "Black box" memory that can't be inspected is untrustworthy. Standard UX pattern: Agent Zero, Mem0, and Microsoft Foundry all ship memory dashboards. Operators need read access at minimum. | MEDIUM | REST API for memory ops. New `/memory` page in occc. |

### Differentiators (Competitive Advantage)

Features that go beyond "memory works" to "memory makes the swarm meaningfully smarter."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **SOUL template injection of retrieved context** | Rather than appending memory as a raw dump, retrieved context is woven into the SOUL template as a `{{ past_outcomes }}` variable. This means the L3 agent receives personalized, project-aware context at the start of every task — not just generic instructions. Context-aware agents perform measurably better on repeated task types. | HIGH | Requires: (1) retrieve() called before SOUL render, (2) soul_renderer.py accepts memory context dict, (3) SOUL template has `{{ memory.past_outcomes }}` placeholder. Chain: retrieve → format → inject → render → spawn. |
| **L3 in-execution memory queries** | L3 specialists can query memory mid-task (e.g., "have we solved this kind of auth bug before?"). This enables tool-call-style memory access during execution, not just at spawn time. Bridges ephemeral container with persistent knowledge. | HIGH | Requires: memU REST API accessible from inside L3 containers (network reachability). L3 entrypoint exposes `MEMU_API_URL` env var. Agent runtime (claude-code) can call HTTP tool. Non-trivial for security: read-only access to memory from L3. |
| **Auto-categorization of task memory by memU** | memU's `memorize()` automatically extracts facts into categories (Resource → Item → Category hierarchy). For OpenClaw, this means task outcomes are auto-organized by feature area, error type, and code pattern — without manual tagging. Operators can browse "Database migrations" category and see all past L3 outcomes in that domain. | MEDIUM | This is a built-in memU capability. Complexity is in ensuring the snapshot format passed to `memorize()` is rich enough for good extraction. Include: task description, L3 agent type, diff content, L2 review outcome. |
| **Memory search in dashboard (semantic, not keyword)** | The dashboard memory panel uses vector search (same as agent retrieval). Operators can search "OAuth bug fixes" and get semantically relevant memories, not just text matches. Standard in modern memory dashboards but not universal. | MEDIUM | REST endpoint wraps memU `retrieve(method="rag", query=...)`. Next.js search input with debounce. Semantic results ranked by relevance score. |
| **L2 review decision feedback loop** | When L2 rejects a diff, that rejection + reasoning is memorized with a "rejection" tag. Future L3 tasks in the same project domain retrieve past rejections as warnings: "Last time you tried this approach, L2 rejected it because X." This closes the quality feedback loop without human intervention. | HIGH | Requires: structured rejection format in memory, retrieve-before-spawn filters for rejections in project+domain scope, injection into SOUL as a "past mistakes" section. Three-component chain: memorize rejection → retrieve rejection → inject as warning. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time memory sync during L3 execution** | Feels powerful — write to memory as the container works, not just at completion. | L3 containers are ephemeral. If the container is killed mid-task, partial memory writes are misleading. The semantic snapshot (git diff) is only coherent at task completion. Mid-execution writes would record intermediate states as "outcomes." | Auto-memorize at task completion only, using the finalized semantic snapshot. This is the Jarvis Protocol model: state is committed at well-defined checkpoints, not continuously. |
| **Shared memory pool across projects** | Simpler — one memory service, one namespace. Might surface cross-project patterns. | Memory from Project A (e.g., a React app) polluting retrieval for Project B (e.g., a Python data pipeline) produces irrelevant context. Worse: confidential project details bleed across boundaries. The per-project scoping is non-negotiable. | Per-project namespace via memU `user` parameter convention: `{project_id}/{agent_type}`. Global knowledge (framework patterns) can be stored in a shared `global/` namespace with explicit opt-in retrieval. |
| **LLM-based memory summarization on every retrieval** | memU supports LLM-mode retrieval for deep reasoning. Seems like it would give better context. | LLM-mode retrieval takes seconds and costs tokens on every pre-spawn call. With 3 concurrent L3 containers spawning simultaneously, that's 3 serial LLM calls blocking spawn. Latency compounds at scale. | RAG-mode retrieval (milliseconds, embedding-based) for pre-spawn context. Reserve LLM-mode for the dashboard's "explain this memory" feature where a human is waiting anyway and latency is acceptable. |
| **Memory as L3 container's primary data store** | Seems elegant — L3 writes all its work-in-progress to memory. | The git staging branch is the L3 artifact. It is reviewable, diffable, and rollbackable. Memory is for *outcomes* after L2 review, not for in-flight work. Conflating the two removes the L2 review gate. | Maintain the staging branch as the authoritative L3 artifact. Memory receives only L2-approved outcomes (or explicitly tagged rejections). The semantic snapshot is the bridge. |
| **Full conversation transcript memorization** | Store everything — the entire L3 claude-code session log. | Token-heavy, noise-heavy. A 10,000-token conversation log has ~200 tokens of signal. memU's `memorize()` extracts facts from the conversation, but feeding raw transcripts is expensive and produces low-quality category extractions. | Pass the semantic snapshot (git diff + L2 review outcome) to `memorize()`. This is already structured, information-dense, and directly represents the outcome. If conversation context is needed, pass only the final L3 summary, not the full transcript. |
| **Memory UI write access (edit/delete from dashboard)** | Operators want to correct bad memories. | Editing memory from the dashboard creates a divergence between what the agent learned and what the operator thinks the agent learned. Memory integrity matters for retrieval quality. | Dashboard is read + delete only. Delete is the correct action for bad memories. Editing is done by memorizing a correction (new memory overrides the incorrect one), not by mutating stored facts in-place. |

---

## Feature Dependencies

```
[Standalone memU service (Docker + postgres)]
    └──required by──> [Internal REST API]
                          └──required by──> [L3 auto-memorization]
                          └──required by──> [L2 memorization of review decisions]
                          └──required by──> [Dashboard memory panel]
                          └──required by──> [Pre-spawn context retrieval]
                                                └──required by──> [SOUL template injection]
                                                └──required by──> [L2 rejection feedback loop]

[Semantic snapshot system (v1.2 - exists)]
    └──feeds──> [L3 auto-memorization]
    └──feeds──> [L2 memorization of review decisions]

[Per-agent + per-project scoping]
    └──required by──> [Pre-spawn context retrieval] (scoped retrieve)
    └──required by──> [L3 auto-memorization] (scoped memorize)
    └──required by──> [Dashboard memory panel] (scoped browse)

[Pre-spawn context retrieval]
    └──enhances──> [SOUL template injection] (inject retrieved context into SOUL)
    └──enhances──> [L2 rejection feedback loop] (retrieve past rejections before spawn)

[L3 in-execution memory queries]
    └──requires──> [Internal REST API reachable from L3 containers]
    └──requires──> [Per-agent + per-project scoping]
    └──independent of──> [Pre-spawn context retrieval] (additive, not prerequisite)

[Dashboard memory panel]
    └──requires──> [Internal REST API]
    └──enhances──> [Memory search (semantic)] (adds search capability to browse)
```

### Dependency Notes

- **memU service is the root dependency**: Nothing else works without it. Phase 1 must be service + API up and reachable from Python orchestration code.
- **Scoping must precede retrieval**: If retrieval is implemented before scoping, every pre-spawn call returns cross-project noise. Scoping is not a later refinement — it is a precondition for correct retrieval.
- **L3 in-execution queries are independent**: They require the REST API but do not depend on SOUL injection or the feedback loop. Can be added after the core memorize/retrieve loop is stable.
- **Dashboard panel is last**: It requires the REST API and some memory already stored. Cannot be meaningfully validated until L3 auto-memorization has run at least a few tasks.
- **SOUL injection depends on soul_renderer.py**: The existing SOUL template engine (`soul_renderer.py`) must be extended to accept a memory context dict as an additional substitution source. This is a targeted change, not a rewrite.

---

## MVP Definition

### Launch With (v1.3)

The minimum loop: L3 does work → outcome is memorized → next L3 gets relevant context.

- [ ] **Standalone memU service** — Docker container with PostgreSQL+pgvector. Without this, nothing else can run.
- [ ] **Internal REST API wrapper** — Python wrapper around memu-py SDK, exposed as HTTP for occc dashboard to consume. Endpoints: `POST /memorize`, `POST /retrieve`, `GET /memories` (list), `DELETE /memories/{id}`.
- [ ] **Per-agent + per-project scoping** — Namespace convention established. All memorize/retrieve calls use `{project_id}/{agent_type}` as the scope key. Enforced at the API wrapper level.
- [ ] **L3 auto-memorization of task outcomes** — Called in `pool.py` (or `spawn.py`) after L3 container exits successfully. Uses the semantic snapshot file as the `resource_url`. Agent type determines scope.
- [ ] **L2 memorization of review decisions** — Called after L2 completes merge/reject decision. Stores decision, reasoning, and affected file list under L2's agent scope.
- [ ] **Pre-spawn context retrieval + SOUL injection** — `retrieve(method="rag")` called before L3 spawn. Top-N results formatted and injected into SOUL template as `{{ memory.past_outcomes }}`. Falls back gracefully if memory service unavailable.
- [ ] **Dashboard memory panel (browse only)** — `/memory` page in occc. Project-scoped list of memory categories and items. Semantic search. Delete action. Read-only (no edit).

### Add After Validation (v1.x)

- [ ] **L3 in-execution memory queries** — Trigger: L3 agents repeatedly solve problems they've already solved before, despite pre-spawn injection. Indicates they need query access mid-task.
- [ ] **L2 rejection feedback loop** — Trigger: L2 continues rejecting similar diffs after several cycles. Indicates pre-spawn context isn't surfacing past rejections effectively. Requires structured rejection tagging.
- [ ] **Memory health monitoring** — Trigger: memory store grows to >10K items and retrieval quality degrades. Add dashboard metrics: total items, items per category, retrieval latency.

### Future Consideration (v2+)

- [ ] **Cross-project pattern sharing (global/ namespace)** — Defer: requires careful curation to avoid noise. Only valuable when 5+ projects have built up substantial memory.
- [ ] **Memory forgetting / TTL policies** — Defer: premature optimization. memU supports retention limits but OpenClaw doesn't have enough memory volume yet to need expiry.
- [ ] **Memory-driven L1 strategy suggestions** — Defer: L1 using memory to suggest which projects need attention based on historical task patterns. Complex, unvalidated value.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Standalone memU service | HIGH — prerequisite for everything | LOW — Docker Compose, postgres:pgvector image, memu-py self-hosted mode | P1 |
| Internal REST API | HIGH — bridges Python and Next.js to memory | MEDIUM — thin FastAPI wrapper or Flask, 4 endpoints | P1 |
| Per-agent + per-project scoping | HIGH — without this, retrieval is noise | LOW — naming convention + enforce at API level | P1 |
| L3 auto-memorization | HIGH — the core learning loop | MEDIUM — hook into pool.py post-completion, format snapshot for memorize() | P1 |
| L2 memorization of decisions | HIGH — closes the review quality loop | MEDIUM — hook into L2 review flow, structure decision format | P1 |
| Pre-spawn context retrieval | HIGH — memory is useless if never consumed | MEDIUM — retrieve() in pool.py before spawn, SOUL template extension | P1 |
| SOUL template injection | HIGH — context reaches the agent meaningfully | MEDIUM — soul_renderer.py extension, template variable addition | P1 |
| Dashboard memory panel | MEDIUM — visibility and trust | MEDIUM — new Next.js page, API routes, search UI | P2 |
| L3 in-execution queries | MEDIUM — deeper learning during execution | HIGH — network reachability from L3, security scope, tool integration | P3 |
| L2 rejection feedback loop | MEDIUM — quality improves after several cycles | HIGH — structured tagging, inject-as-warning pattern | P3 |

**Priority key:**
- P1: Must have for v1.3 launch — establishes the memory loop
- P2: Should have, delivers observability
- P3: Nice to have, significant complexity, defer until P1 stable

---

## Integration Points with Existing System

| New Feature | Existing Code Touched | Change Type |
|-------------|----------------------|-------------|
| memU service | New `docker-compose.yml` or service definition. `openclaw.json` adds `memu_api_url`. | New infrastructure |
| Internal REST API | New `orchestration/memory_api.py` (client wrapper). New `workspace/occc/src/app/api/memory/route.ts`. | New files |
| Per-project scoping | `orchestration/memory_api.py` encodes scope convention. `project_config.py` may expose helper. | New file, minor extension |
| L3 auto-memorization | `skills/spawn_specialist/pool.py` — post-container-exit hook. `orchestration/snapshot.py` — snapshot path lookup. | Extend existing |
| L2 memorization | L2 PM review flow — agent-side (claude-code session or orchestration hook). | Agent-side change or L2 hook |
| Pre-spawn retrieval | `skills/spawn_specialist/pool.py` — before `docker run`. `orchestration/soul_renderer.py` — new `memory_context` param. | Extend existing |
| SOUL template injection | `agents/*/SOUL.md` templates — add `{{ memory.past_outcomes }}` block. `orchestration/soul_renderer.py` — extend substitution dict. | Template edit + renderer extension |
| Dashboard memory panel | New `workspace/occc/src/app/memory/page.tsx`. New `workspace/occc/src/hooks/useMemory.ts`. New API routes. | New files |

---

## memU API Specifics (memu-py 1.4.0)

Based on PyPI and GitHub documentation (HIGH confidence — official sources):

```python
from memu import MemuClient

client = MemuClient(api_key="...", base_url="http://localhost:8000")  # self-hosted

# Memorize a task outcome
result = client.memorize(
    resource_url="/path/to/snapshot.diff",
    modality="document",
    user="pumplai/l3_code"  # {project_id}/{agent_type} scoping convention
)

# Retrieve before spawn (RAG mode — milliseconds, low cost)
context = client.retrieve(
    query="similar auth token implementation tasks",
    method="rag",
    user="pumplai/l3_code"
)

# Retrieve for operator (LLM mode — seconds, acceptable for dashboard)
rich_context = client.retrieve(
    query="database migration errors",
    method="llm",
    user="pumplai/l3_code"
)
```

**Key constraints (from research):**
- Python >=3.13 required (matches project's Python 3.13 target)
- PostgreSQL+pgvector backend available via `pip install memu-py[postgres]`
- `user` parameter is the primary scoping mechanism — maps to namespace in memU
- `memorize()` returns: resource metadata, extracted items, auto-updated categories
- `retrieve()` returns: ranked list of relevant memory items with scores
- LLM profiles must be configured for extraction (OpenAI or Anthropic via OpenRouter)

---

## Sources

- [memU GitHub (NevaMind-AI/memU)](https://github.com/NevaMind-AI/memU) — PRIMARY: API, architecture, self-hosted setup
- [memu-py PyPI 1.4.0](https://pypi.org/project/memu-py/) — PRIMARY: Python requirements, API methods, install extras
- [Agent Zero Memory Dashboard (DeepWiki)](https://deepwiki.com/agent0ai/agent-zero/5.6-memory-dashboard) — UI patterns: browse, search, semantic retrieval, category organization
- [IBM: What Is AI Agent Memory](https://www.ibm.com/think/topics/ai-agent-memory) — Memory type taxonomy (episodic, semantic, working, parametric)
- [Redis: AI Agent Memory — Stateful Systems](https://redis.io/blog/ai-agent-memory-stateful-systems/) — Production patterns: checkpointing, scoping, async extraction
- [mem0.ai: AI Memory Security Best Practices](https://mem0.ai/blog/ai-memory-security-best-practices) — Scoping, isolation, RBAC, sanitization patterns
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Pre-task context injection, trust labels, dynamic tool loading
- [arXiv: Memory in the Age of AI Agents (2512.13564)](https://arxiv.org/abs/2512.13564) — Survey: formation, evolution, retrieval lifecycle
- [Microsoft Foundry: Memory Concepts](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/what-is-memory?view=foundry) — Multi-agent memory isolation guidance
- Existing codebase: `/home/ollie/.openclaw/orchestration/soul_renderer.py`
- Existing codebase: `/home/ollie/.openclaw/skills/spawn_specialist/pool.py`
- Existing codebase: `/home/ollie/.openclaw/orchestration/snapshot.py`

---

*Feature research for: OpenClaw v1.3 — memU agent memory integration*
*Researched: 2026-02-24*
