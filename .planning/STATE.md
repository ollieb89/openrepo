# Project State: OpenClaw

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.
**Current focus:** v1.3 Agent Memory — Phase 29: Pre-Spawn Retrieval + SOUL Injection

## Current Position

Phase: 29 of 32 (Pre-Spawn Retrieval + SOUL Injection)
Plan: 1 of 2 (complete)
Status: Plan 01 complete, Plan 02 pending
Last activity: 2026-02-24 — Phase 29 Plan 01 executed (sync httpx retrieval + tempfile SOUL injection into spawn.py)

Progress: [████░░░░░░] 40% (v1.3)

## Performance Metrics

**Velocity:**
- v1.0: 10 phases, 25 plans across 7 days
- v1.1: 8 phases, 17 plans in ~5 hours
- v1.2: 7 phases, 14 plans in ~1 day
- v1.3 (29-01): 2 tasks, 1 file, 2 min

## Accumulated Context

### Decisions

All prior decisions logged in PROJECT.md Key Decisions table (v1.0 through v1.2).

v1.3 decisions made (Phase 26 Plan 01):
- Custom FastAPI wrapper around memu-py chosen over nevamindai/memu-server image (avoids unknown Temporal dependency)
- Port 18791 bound to 127.0.0.1 only — confirmed OpenClaw 187xx convention
- pgvector/pgvector:pg17-bookworm chosen (PG17 native vector performance improvements)
- memu-py[postgres] extra (not raw memu) — package name has hyphen, pulls psycopg3
- Single uvicorn worker required — multiple workers create separate MemUService instances
- DSN format: postgresql+psycopg:// (psycopg3, not psycopg2) for memu-py compatibility

v1.3 decisions made (Phase 26 Plan 02):
- MemoryService from memu.app (not MemUService from memu) — plan used wrong class name, correct class discovered via introspection
- MemoryService constructor is sync — init_service() is a regular function, no await in lifespan
- Dockerfile needs build-essential + libc6-dev + rustup — memu-py v1.4.0 uses maturin/pyo3 Rust extension
- pydantic-settings required in requirements.txt — missing from Plan 01, added as auto-fix
- memorize_config llm_temperature removed — not a valid MemorizeConfig field
- [Phase 27]: AgentType(str, Enum) so values serialize to JSON without .value
- [Phase 27]: retrieve() where clause maps project_id to user_id — memU user_id is project isolation key

v1.3 decisions made (Phase 29 Plan 01):
- Use httpx.Client (sync) not asyncio.run(MemoryClient.retrieve()) — avoids RuntimeError when spawn called from pool.py async context
- Read agents/l3_specialist/agent/SOUL.md directly (not render_soul()) — render_soul() generates L2 agent content, wrong target for L3 injection
- MEMORY_CONTEXT_BUDGET=2000 hardcoded constant, not project-configurable
- Empty memory context produces no Memory Context header — no placeholder, clean blank
- Tempfile cleanup in finally block after containers.run() — not before, Docker needs file at bind-mount time
- SOUL mounted at /run/openclaw/soul.md — avoids conflict with existing /orchestration directory mount

### Pending Todos

None.

### Blockers/Concerns

- Phase 30 research flag: L2 review call site unknown — must locate merge/reject decision point in codebase before planning

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 29-01-PLAN.md — sync httpx retrieval + tempfile SOUL injection (2 tasks, 1 file)
Resume file: .planning/phases/29-pre-spawn-retrieval-soul-injection/29-01-SUMMARY.md
