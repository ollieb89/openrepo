# Roadmap: OpenClaw (Grand Architect Protocol)

## Milestones

- ✅ **v1.0 Grand Architect Protocol Foundation** — Phases 1-10 (shipped 2026-02-23)
- ✅ **v1.1 Project Agnostic** — Phases 11-18 (shipped 2026-02-23)
- ✅ **v1.2 Orchestration Hardening** — Phases 19-25 (shipped 2026-02-24)
- 🚧 **v1.3 Agent Memory** — Phases 26-32 (in progress)

## Phases

<details>
<summary>✅ v1.0 Grand Architect Protocol Foundation (Phases 1-10) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Environment Substrate (2/2 plans) — completed 2026-02-17
- [x] Phase 2: Core Orchestration (2/2 plans) — completed 2026-02-17
- [x] Phase 3: Specialist Execution (4/4 plans) — completed 2026-02-18
- [x] Phase 4: Monitoring Uplink (4/4 plans) — completed 2026-02-18
- [x] Phase 5: Wiring Fixes & Initialization (3/3 plans) — completed 2026-02-23
- [x] Phase 6: Phase 3 Formal Verification (2/2 plans) — completed 2026-02-23
- [x] Phase 7: Phase 4 Formal Verification (2/3 plans, 1 skipped) — completed 2026-02-23
- [x] Phase 8: Final Gap Closure (1/1 plan) — completed 2026-02-23
- [x] Phase 9: Integration Wiring Cleanup (2/2 plans) — completed 2026-02-23
- [x] Phase 10: Housekeeping & Documentation (2/2 plans) — completed 2026-02-23

See: `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.1 Project Agnostic (Phases 11-18) — SHIPPED 2026-02-23</summary>

- [x] Phase 11: Config Decoupling Foundation (3/3 plans) — completed 2026-02-23
- [x] Phase 12: SOUL Templating (2/2 plans) — completed 2026-02-23
- [x] Phase 13: Multi-Project Runtime (2/2 plans) — completed 2026-02-23
- [x] Phase 14: Project CLI (2/2 plans) — completed 2026-02-23
- [x] Phase 15: Dashboard Project Switcher (2/2 plans) — completed 2026-02-23
- [x] Phase 16: Phase 11/12 Integration Fixes (2/2 plans) — completed 2026-02-23
- [x] Phase 17: Phase 11/12 Formal Verification (2/2 plans) — completed 2026-02-23
- [x] Phase 18: Integration Hardening (2/2 plans) — completed 2026-02-23

See: `.planning/milestones/v1.1-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.2 Orchestration Hardening (Phases 19-25) — SHIPPED 2026-02-24</summary>

- [x] Phase 19: Structured Logging (2/2 plans) — completed 2026-02-24
- [x] Phase 20: Reliability Hardening (2/2 plans) — completed 2026-02-24
- [x] Phase 21: State Engine Performance (3/3 plans) — completed 2026-02-24
- [x] Phase 22: Observability Metrics (2/2 plans) — completed 2026-02-24
- [x] Phase 23: Per-Project Pool Config (2/2 plans) — completed 2026-02-24
- [x] Phase 24: Dashboard Metrics (2/2 plans) — completed 2026-02-24
- [x] Phase 25: Monitor Cache Fix (1/1 plan) — completed 2026-02-24

See: `.planning/milestones/v1.2-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.3 Agent Memory (In Progress)

**Milestone Goal:** Integrate memU memory framework so agents learn across sessions — L3 outcomes and L2 decisions are memorized, and relevant context is retrieved and injected before task execution.

- [x] **Phase 26: memU Infrastructure** — Standalone memory service (memu-server + PostgreSQL+pgvector) running in Docker with a verified REST API and cold-start-safe extension initialization (completed 2026-02-24)
- [x] **Phase 27: Memory Client + Scoping** — MemoryClient wrapper in orchestration layer that makes per-project and per-agent scoping structurally mandatory (completed 2026-02-24)
- [ ] **Phase 28: L3 Auto-Memorization** — L3 task outcomes fire-and-forget memorized after container exit; MEMU env vars injected at spawn time
- [ ] **Phase 29: Pre-Spawn Retrieval + SOUL Injection** — spawn.py retrieves relevant context before L3 creation; soul_renderer.py injects it under a hard 2,000-character budget
- [ ] **Phase 30: L2 Review Decision Memorization** — merge/reject decisions with reasoning are memorized after each L2 review cycle
- [ ] **Phase 31: L3 In-Execution Memory Queries** — L3 containers can query memU via HTTP during task execution for on-demand lookups
- [ ] **Phase 32: Dashboard Memory Panel** — /memory page in occc for browsing, searching, and deleting project-scoped memory items

## Phase Details

### Phase 26: memU Infrastructure
**Goal**: A running memory stack — memu-server and PostgreSQL+pgvector — is accessible from the host and from within Docker containers, with verified cold-start initialization and a working REST API
**Depends on**: Phase 25 (v1.2 complete)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. `docker compose up` in `docker/memory/` brings up memu-server and memu-postgres without errors on a clean volume
  2. GET /health returns 200 from the host, confirming the service is reachable at its configured port
  3. POST /memorize and POST /retrieve succeed from the host with a sample payload, returning expected JSON
  4. After deleting the postgres volume and restarting, the pgvector extension is present in `pg_extension` (verifying init ordering is correct)
  5. L3 containers joined to openclaw-net can reach memu-server by Docker DNS name (verified via docker exec curl)
**Plans**: 2 plans

Plans:
- [ ] 26-01-PLAN.md — Docker infrastructure (Compose, Dockerfile, pgvector init, requirements)
- [ ] 26-02-PLAN.md — FastAPI application code + full stack build & verification

### Phase 27: Memory Client + Scoping
**Goal**: A MemoryClient wrapper in the orchestration layer makes it structurally impossible to call memorize or retrieve without a project_id; per-agent scoping is supported via agent_type parameter
**Depends on**: Phase 26
**Requirements**: SCOPE-01, SCOPE-02, SCOPE-03
**Success Criteria** (what must be TRUE):
  1. `MemoryClient(base_url, project_id)` is the only way to construct a client — no project_id means no client
  2. A two-project isolation test passes: memories written for project A return zero results when retrieved for project B
  3. `memory_client.health()` returns True when the service is up and False (not an exception) when it is down
  4. memorize and retrieve calls include agent_type in the request payload, enabling per-agent scoping at the API level
**Plans**: 1 plan

Plans:
- [ ] 27-01-PLAN.md — MemoryClient module with enforced scoping + comprehensive test suite

### Phase 28: L3 Auto-Memorization
**Goal**: After a successful L3 task completes, its semantic snapshot is memorized in memU via a fire-and-forget HTTP call that does not delay container exit or hold the pool slot
**Depends on**: Phase 27
**Requirements**: MEM-01, MEM-03, MEM-04
**Success Criteria** (what must be TRUE):
  1. After a test L3 task completes, a memory item attributed to that agent/project appears in memU (verifiable via GET /memories)
  2. The L3 container exits and the pool slot is released before the memU memorize pipeline finishes (fire-and-forget confirmed by timing)
  3. When memU service is stopped, an L3 task still completes successfully — memorization failure is non-blocking
  4. MEMU_SERVICE_URL, MEMU_AGENT_ID, MEMU_PROJECT_ID, and MEMU_ENABLED are present in the L3 container environment at spawn time
**Plans**: 2 plans

Plans:
- [ ] 28-01-PLAN.md — Config + env injection (openclaw.json memory field, get_memu_config(), MEMU env vars in spawn.py)
- [ ] 28-02-PLAN.md — Fire-and-forget memorization (pool.py _memorize_snapshot_fire_and_forget, asyncio.create_task on success, test suite)

### Phase 29: Pre-Spawn Retrieval + SOUL Injection
**Goal**: Before an L3 container is created, relevant memories are retrieved and injected into the SOUL template so the agent starts with accumulated context from past tasks
**Depends on**: Phase 28
**Requirements**: RET-01, RET-02, RET-03, RET-04
**Success Criteria** (what must be TRUE):
  1. A spawned L3 container's rendered SOUL.md contains a "Memory Context" section with content retrieved from Phase 28 memories
  2. The injected memory context never exceeds 2,000 characters — verified by inspecting the rendered SOUL byte count
  3. When memU service is unavailable during spawn, the container still starts — the SOUL renders with an empty memory context section
  4. The SOUL template's `$memory_context` variable renders as blank (no error, no placeholder text) when no memories exist for a project
**Plans**: 2 plans

Plans:
- [ ] 29-01-PLAN.md — Retrieval helpers + SOUL injection wiring in spawn.py
- [ ] 29-02-PLAN.md — Test suite for pre-spawn memory retrieval and SOUL injection

### Phase 30: L2 Review Decision Memorization
**Goal**: Every L2 merge or reject decision — including the reasoning — is memorized after the review cycle completes, so future L3 spawns receive context about past review outcomes
**Depends on**: Phase 27
**Requirements**: MEM-02
**Success Criteria** (what must be TRUE):
  1. After an L2 merge decision, a memory item attributed to l2_pm with the merge reasoning appears in memU for that project
  2. After an L2 reject decision, a memory item attributed to l2_pm with the rejection reason appears in memU
  3. A rejected task's future L3 spawn (Phase 29 retrieval) can surface the prior rejection as context in its SOUL
  4. If memU is unavailable, the L2 review cycle completes and the state file is updated — memorization failure does not block the decision
**Plans**: TBD

Plans:
- [ ] 30-01: TBD

### Phase 31: L3 In-Execution Memory Queries
**Goal**: L3 containers can query memU for task-specific context during execution — not just at spawn time — via HTTP calls that are independent of SOUL injection
**Depends on**: Phase 26
**Requirements**: RET-05
**Success Criteria** (what must be TRUE):
  1. From within a running L3 container, an HTTP GET to `http://memu-server:8765/retrieve` with a query payload returns relevant memory items
  2. An L3 task that performs a mid-execution memory query completes successfully whether or not the query returns results
**Plans**: TBD

Plans:
- [ ] 31-01: TBD

### Phase 32: Dashboard Memory Panel
**Goal**: The occc dashboard has a /memory page where the operator can browse project-scoped memory categories, inspect individual items with metadata, run semantic search, and delete items
**Depends on**: Phases 28, 30
**Requirements**: DSH-11, DSH-12, DSH-13, DSH-14
**Success Criteria** (what must be TRUE):
  1. Navigating to /memory in the dashboard shows memory items scoped to the currently selected project — switching projects updates the view
  2. Typing a query in the search bar returns semantically relevant memory items (vector-based retrieval via POST /retrieve)
  3. Clicking delete on a memory item removes it — a subsequent page refresh confirms the item is gone
  4. Each memory item displays its type, category, created_at timestamp, and agent source (l2_pm, l3_code, l3_test)
**Plans**: TBD

Plans:
- [ ] 32-01: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Environment Substrate | v1.0 | 2/2 | ✓ Complete | 2026-02-17 |
| 2. Core Orchestration | v1.0 | 2/2 | ✓ Complete | 2026-02-17 |
| 3. Specialist Execution | v1.0 | 4/4 | ✓ Complete | 2026-02-18 |
| 4. Monitoring Uplink | v1.0 | 4/4 | ✓ Complete | 2026-02-18 |
| 5. Wiring Fixes | v1.0 | 3/3 | ✓ Complete | 2026-02-23 |
| 6. Phase 3 Verification | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 7. Phase 4 Verification | v1.0 | 2/3 | ✓ Complete | 2026-02-23 |
| 8. Final Gap Closure | v1.0 | 1/1 | ✓ Complete | 2026-02-23 |
| 9. Integration Wiring | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 10. Housekeeping & Docs | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 11. Config Decoupling Foundation | v1.1 | 3/3 | ✓ Complete | 2026-02-23 |
| 12. SOUL Templating | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 13. Multi-Project Runtime | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 14. Project CLI | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 15. Dashboard Project Switcher | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 16. Phase 11/12 Integration Fixes | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 17. Phase 11/12 Formal Verification | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 18. Integration Hardening | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 19. Structured Logging | v1.2 | 2/2 | ✓ Complete | 2026-02-24 |
| 20. Reliability Hardening | v1.2 | 2/2 | ✓ Complete | 2026-02-24 |
| 21. State Engine Performance | v1.2 | 3/3 | ✓ Complete | 2026-02-24 |
| 22. Observability Metrics | v1.2 | 2/2 | ✓ Complete | 2026-02-24 |
| 23. Per-Project Pool Config | v1.2 | 2/2 | ✓ Complete | 2026-02-24 |
| 24. Dashboard Metrics | v1.2 | 2/2 | ✓ Complete | 2026-02-24 |
| 25. Monitor Cache Fix | v1.2 | 1/1 | ✓ Complete | 2026-02-24 |
| 26. memU Infrastructure | 2/2 | Complete    | 2026-02-24 | - |
| 27. Memory Client + Scoping | 1/1 | Complete    | 2026-02-24 | - |
| 28. L3 Auto-Memorization | v1.3 | 0/? | Not started | - |
| 29. Pre-Spawn Retrieval + SOUL Injection | 1/2 | In Progress|  | - |
| 30. L2 Review Decision Memorization | v1.3 | 0/? | Not started | - |
| 31. L3 In-Execution Memory Queries | v1.3 | 0/? | Not started | - |
| 32. Dashboard Memory Panel | v1.3 | 0/? | Not started | - |
