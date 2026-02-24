# Project State: OpenClaw

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.
**Current focus:** Phase 36: Dashboard Memory Panel (complete)

## Current Position

Phase: 36 of 36 (Dashboard Memory Panel)
Plan: 3 of 3 (complete)
Status: Phase 36 complete — all 3 plans done. v1.3 memory milestone feature-complete.
Last activity: 2026-02-24 — Phase 36 Plan 03 executed (MemorySearch component, ConfirmDialog component, search/delete wiring in MemoryPanel with optimistic UI and toast notifications)

Progress: [██████████] 100% (v1.3 gap closure)

## Performance Metrics

**Velocity:**
- v1.0: 10 phases, 25 plans across 7 days
- v1.1: 8 phases, 17 plans in ~5 hours
- v1.2: 7 phases, 14 plans in ~1 day
- v1.3 (29-01): 2 tasks, 1 file, 2 min
- v1.3 (29-02): 1 task, 1 file, 5 min

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

v1.3 decisions made (Phase 29 Plan 02):
- 12 tests written (vs planned 10) — added dict response format and missing SOUL file tests for complete branch coverage
- MagicMock (not AsyncMock) for httpx.Client — _retrieve_memories_sync is synchronous

v1.3 decisions made (Phase 30 Plan 01):
- Daemon threads over asyncio in snapshot.py — synchronous context, matches _retrieve_memories_sync pattern, avoids asyncio.run() RuntimeError
- GitOperationError paths excluded from memorization — those are programming errors, not L2 review decisions
- diff_summary sliced to [:500] in content string — bounds payload size, preserves most relevant conflict context
- Lazy imports of get_memu_config/AgentType inside _memorize_review_decision() — matches pool.py convention, avoids import-time side effects

v1.3 decisions made (Phase 30 Plan 02):
- Budget tracks bullet character counts, not total output length — section headers (~23 chars) are acceptable overhead above the 2,000-char cap
- Dual-check for review_decision: category=='review_decision' OR agent_type=='l2_pm' — handles both new review_decision category and l2_pm agent items without a category field
- Old tag suffixes ('(from memory)', '(from L2 review)') removed — section headers provide source context, bullets are cleaner

v1.3 decisions made (Phase 33 Plan 01):
- Docker DNS hostname 'openclaw-memory' used for MEMU_API_URL rewrite — matches container service name convention
- SOUL_ARGS bash array chosen over string interpolation for safe multiline --system-prompt quoting
- Persistent SOUL path workspace/.openclaw/<proj>/soul-<task>.md survives container exit for debug inspection
- PIPESTATUS[0] replaces $? to correctly capture CLI exit code from piped tee invocation
- Empty SOUL_ARGS array expands to nothing — safe no-op when no SOUL file mounted

Phase 34 Plan 01 decisions:
- Plain string literal 'review_decision' in payload — no constants or enums per prior user decision
- Backward-compat test added explicitly alongside existing test_format_work_only_no_review_section — documents the contract

Phase 35 Plan 01 decisions:
- printf used for JSON payload construction in bash test commands — avoids single-quote escaping issues when env vars need expansion inside JSON strings
- Project-only scoping (no global fallback) via OPENCLAW_PROJECT → where.user_id, consistent with memory_client.py and spawn.py
- Advisory-only framing in SOUL: unreachable memU or empty results must not abort task execution

Phase 36 Plan 01 decisions:
- memU response normalization: Array.isArray(data) ? data : (data.items ?? []) applied to both GET /memories (plain array) and POST /retrieve (array or object)
- useMemory uses revalidateOnFocus: false and no refreshInterval — memory items are not real-time data
- ToastContainer placed after ProjectProvider but inside ThemeProvider for dark mode support
- Brain/nerve Heroicons outline SVG used for Memory sidebar nav item

Phase 36 Plan 02 decisions:
- Array.from(new Set(...)) used instead of spread operator for Set to avoid TS2802 downlevelIteration error
- All sorting and filtering done client-side in MemoryPanel — data set is small (memory items per project)
- formatDate uses epoch*1000 conversion for numeric timestamps from memU API
- MemoryRow uses Set<string> for EXCLUDED_COLUMNS to filter extra metadata keys efficiently

Phase 36 Plan 03 decisions:
- DialogState discriminated union ({ type: 'none' | 'single' | 'bulk' }) used to share one ConfirmDialog for both single and bulk delete paths
- Set spread replaced with Array.from() for TypeScript es5 target compatibility (TS2802 downlevelIteration)
- 300ms DELETE_ANIMATION_MS constant: setDeletingIds -> await delay -> fetch DELETE -> optimistic mutate pattern
- MemorySearch enter-key-only trigger (no debounce/as-you-type) per plan locked decision

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 36-03-PLAN.md — MemorySearch, ConfirmDialog, search wiring, single/bulk delete with optimistic UI and toast notifications
Resume file: .planning/phases/36-dashboard-memory-panel/36-03-SUMMARY.md
