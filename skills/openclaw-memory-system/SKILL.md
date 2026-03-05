---
name: openclaw-memory-system
description: Use when implementing, operating, or debugging OpenClaw task memory behavior (memU retrieval, SOUL/MEMORY context injection, and post-task memorization). Trigger for requests about where memory is injected, when learnings are stored, how agent-type scoping works (L2_PM/L3_CODE/L3_TEST), or where task execution is dispatched to the actual LLM runtime.
metadata:
  openclaw:
    emoji: "🧠"
    category: "orchestration-core"
---

# OpenClaw Memory System

Use this workflow to trace and validate memory behavior end-to-end.

## Locate Execution Dispatch

1. Treat `skills/spawn/spawn.py` as the L2 dispatch point.
2. Read `spawn_l3_specialist(...)` to confirm:
   - container creation
   - pre-spawn memory retrieval
   - SOUL augmentation and mount
3. Treat `docker/l3-specialist/entrypoint.sh` as the runtime execution loop.
4. Confirm the actual LLM CLI dispatch at:
   - `"${CLI_RUNTIME}" "${SOUL_ARGS[@]}" --task "${TASK_DESCRIPTION}"`
5. Treat orchestration state updates as side effects around the runtime call, not the model call itself.

## Validate Memory Injection Paths

1. Validate pre-spawn injection in `skills/spawn/spawn.py`:
   - `_retrieve_memories_sync(...)`
   - `_format_memory_context(...)`
   - `_build_augmented_soul(...)`
   - `_write_soul_file(...)`
2. Validate state-transition injection in `packages/orchestration/src/openclaw/state_engine.py`:
   - on `in_progress`, call `_run_memory_injector(...)`
   - injector writes `MEMORY.md` via `generate_memory_context(...)`
3. Validate container-side prompt injection in `docker/l3-specialist/entrypoint.sh`:
   - read `SOUL_FILE`
   - pass system prompt args for `claude-code` and `codex`
   - write `GEMINI.md` for `gemini-cli`

## Validate Post-Task Memorization

1. Inspect `packages/orchestration/src/openclaw/state_engine.py` status transitions.
2. Confirm terminal statuses trigger `_run_memory_extractor(...)`:
   - `completed`
   - `failed`
   - `rejected`
3. Inspect `packages/orchestration/src/openclaw/memory_extractor.py` for per-agent formatting:
   - `L2_PM` -> architecture/planning context
   - `L3_CODE` -> implementation/pattern context
   - `L3_TEST` -> testing/edge-case context

## Operate Safely

1. Treat memory calls as best-effort and non-blocking.
2. Keep spawn reliability first: do not fail task execution solely on memU outage.
3. Preserve project scoping and agent scoping in every memory operation.
4. Use short, task-specific retrieval queries to avoid irrelevant context.

## Quick Verification Checklist

1. Confirm memU URL exists in project config (`memu_api_url`).
2. Start a task and verify:
   - `.openclaw/<project_id>/soul-<task_id>.md` exists
   - `SOUL_FILE` is mounted and consumed
3. Move task to `in_progress` and verify `MEMORY.md` is generated.
4. Complete/fail/reject task and verify memorization call is issued.
5. Run orchestration tests:
   - `packages/orchestration/tests/test_memory_injector.py`
   - `packages/orchestration/tests/test_memory_extractor.py`
   - `packages/orchestration/tests/test_state_engine_memory.py`

## Reference

Read [references/runtime-and-memory-paths.md](references/runtime-and-memory-paths.md) for concrete file map and lifecycle order.
