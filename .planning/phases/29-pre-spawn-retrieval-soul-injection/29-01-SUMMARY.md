---
phase: 29-pre-spawn-retrieval-soul-injection
plan: 01
subsystem: infra
tags: [httpx, tempfile, docker, memory, soul-injection, memu, spawn]

# Dependency graph
requires:
  - phase: 27-memory-client-scoping
    provides: MemoryClient with enforced project scoping and retrieve() payload format
  - phase: 28-memu-env-injection
    provides: get_memu_config() returning memu_api_url, MEMU_* env vars in containers

provides:
  - _retrieve_memories_sync: sync httpx.Client POST to memU /retrieve, graceful degradation
  - _format_memory_context: budget-aware bullet formatting (2000 char hard cap, whole-item drop)
  - _build_augmented_soul: reads L3 SOUL.md directly, appends Memory Context section
  - _write_soul_tempfile: NamedTemporaryFile(delete=False) for Docker volume bind mount
  - spawn_l3_specialist wired: retrieves memories, formats them, mounts augmented SOUL as read-only volume at /run/openclaw/soul.md, sets SOUL_FILE env var, cleans up in finally block

affects:
  - 29-02-retrieval-test-suite
  - phase 30 (L2 review memory — call site will use SOUL_FILE pattern established here)

# Tech tracking
tech-stack:
  added:
    - httpx.Client (sync) — already installed, now used directly in spawn path for sync retrieval
    - tempfile.NamedTemporaryFile(delete=False) — stdlib, used for SOUL file bind-mount lifecycle
  patterns:
    - "Sync httpx.Client in async-safe spawn path: avoids asyncio.run() RuntimeError when pool.py calls spawn from event loop"
    - "Tempfile bind-mount lifecycle: write before containers.run(), unlink in finally after — Docker holds inode in container"
    - "L3 SOUL read directly from agents/l3_specialist/agent/SOUL.md (no template vars, no render_soul() call)"
    - "Memory context appended post-read, not via soul_renderer.py — keeps soul_renderer.py unchanged (locked decision)"
    - "Budget enforcement: whole-item drop rather than truncation — missing bullet is honest, truncated bullet is misleading"

key-files:
  created: []
  modified:
    - skills/spawn_specialist/spawn.py

key-decisions:
  - "Use httpx.Client (sync) not asyncio.run(MemoryClient.retrieve()) — avoids RuntimeError when spawn called from pool.py async context"
  - "Read agents/l3_specialist/agent/SOUL.md directly (not render_soul()) — render_soul() generates L2 agent content, wrong target for L3 injection"
  - "MEMORY_CONTEXT_BUDGET=2000 hardcoded constant, not project-configurable (locked per CONTEXT.md)"
  - "Empty memory context produces no ## Memory Context header — no placeholder, clean blank (locked decision)"
  - "Tempfile cleanup in finally block after containers.run() — not before, Docker needs file at bind-mount time"
  - "SOUL mounted at /run/openclaw/soul.md (SOUL_CONTAINER_PATH) — avoids conflict with /orchestration directory mount"

patterns-established:
  - "Sync HTTP call pattern for memU in spawn context: httpx.Client with _RETRIEVE_TIMEOUT (3s total, 2s connect)"
  - "Graceful degradation chain: memU unavailable → [] → '' → base SOUL unchanged → container spawns normally"

requirements-completed: [RET-01, RET-02, RET-03, RET-04]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 29 Plan 01: Pre-Spawn Retrieval + SOUL Injection Summary

**Sync httpx.Client retrieval from memU /retrieve wired into spawn_l3_specialist with 2000-char budget-aware SOUL augmentation via tempfile bind mount at /run/openclaw/soul.md**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T08:18:41Z
- **Completed:** 2026-02-24T08:20:21Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Four helper functions added to spawn.py: `_retrieve_memories_sync`, `_format_memory_context`, `_build_augmented_soul`, `_write_soul_tempfile`
- `spawn_l3_specialist` now retrieves project-scoped memories from memU before container creation, formats them with a 2000-char hard budget, and mounts the augmented L3 SOUL as a read-only bind volume
- Full graceful degradation: memU unavailable or returning no memories produces no Memory Context section — container spawns normally with unmodified SOUL

## Task Commits

Each task was committed atomically:

1. **Task 1: Add memory retrieval and formatting helpers** - `9297b06` (feat)
2. **Task 2: Wire retrieval + SOUL injection into spawn_l3_specialist** - `e8eba90` (feat)

## Files Created/Modified

- `skills/spawn_specialist/spawn.py` - Added 4 helper functions, 4 module-level constants, and retrieval/injection wiring in spawn_l3_specialist

## Decisions Made

- Used `httpx.Client` (sync) directly rather than `asyncio.run(MemoryClient.retrieve())` — pool.py is async, and `asyncio.run()` raises RuntimeError when called from a running event loop
- Read `agents/l3_specialist/agent/SOUL.md` directly instead of calling `render_soul()` — render_soul() generates L2 agent content (tactical translation, quality gate); the L3 SOUL (workspace scope, branch discipline) is the correct injection target
- Tempfile unlinked in `finally` block after `containers.run()` — Docker bind-mounts by inode, so the container retains read access after host unlink
- SOUL mounted at `/run/openclaw/soul.md` — avoids conflict with existing `/orchestration` directory mount

## Deviations from Plan

None — plan executed exactly as written. Research (29-RESEARCH.md) provided precise implementation patterns including the L3 SOUL pitfall (Pitfall 5), making execution straightforward.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 01 complete. Ready for Plan 02: test suite validating retrieval, formatting, budget enforcement, and graceful degradation
- The `SOUL_FILE` env var pattern established here will be consumed by Phase 30 when L2 review memories are injected

---
*Phase: 29-pre-spawn-retrieval-soul-injection*
*Completed: 2026-02-24*
