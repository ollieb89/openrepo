# Runtime And Memory Paths

## File Map

- Dispatch and pre-spawn memory: `skills/spawn/spawn.py`
- Container runtime execution loop: `docker/l3-specialist/entrypoint.sh`
- State transitions and async hooks: `packages/orchestration/src/openclaw/state_engine.py`
- Memory retrieval/write client: `packages/orchestration/src/openclaw/memory_client.py`
- In-progress context writer: `packages/orchestration/src/openclaw/memory_injector.py`
- Completion/failure extractor: `packages/orchestration/src/openclaw/memory_extractor.py`

## Lifecycle Order

1. L2 calls `spawn_l3_specialist(...)`.
2. Spawner creates task state entry and reads memory cursor.
3. Spawner retrieves memU context and appends it into an augmented SOUL file.
4. Spawner starts L3 container with `SOUL_FILE` and runtime env vars.
5. Container entrypoint updates task state and invokes selected runtime CLI (`claude-code`, `codex`, or `gemini-cli`).
6. `JarvisState.update_task(...)` transitions trigger background memory hooks:
   - `in_progress` -> memory injection (`MEMORY.md`)
   - `completed|failed|rejected` -> memory extraction + memorize call

## Where The Actual LLM Call Happens

The direct model-facing runtime invocation is in `docker/l3-specialist/entrypoint.sh`, where it executes:

- `${CLI_RUNTIME} ... --task "${TASK_DESCRIPTION}"`

This means orchestration prepares context and state, while the container runtime performs the actual CLI-to-LLM execution.
