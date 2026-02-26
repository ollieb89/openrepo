# Phase 55: Self-Directed Task Decomposition - Research

## Objective
Answer: "What do I need to know to PLAN this phase well?"

## 1. Architectural Integration Points

### 1.1 L3 Container Entrypoint (`docker/l3-specialist/entrypoint.sh`)
- Currently, `entrypoint.sh` directly invokes the chosen `CLI_RUNTIME` (e.g., `claude-code`) passing the `$TASK_DESCRIPTION`.
- To insert a planning phase *before* execution:
  - We need a two-stage execution model in the container.
  - Stage 1: Planning pass (invoking the LLM to generate the plan).
  - Stage 2: Execution pass (invoking the LLM to execute the steps).
- The container already mounts `/openclaw_src`, allowing us to write a robust Python script (e.g., `l3_autonomy_runner.py`) that handles this lifecycle rather than complicating `entrypoint.sh` with bash logic.

### 1.2 Event Bus Emission
- CONTEXT.md dictates: "Emitted as a single complete plan event to the Event Bus".
- Currently, `AutonomyEventBus.emit()` is available in `openclaw_src`.
- A new event class (e.g., `AutonomyPlanGenerated(AutonomyEvent)`) should be added to `src/openclaw/autonomy/events.py`.
- The event must contain the serialized plan structure.

### 1.3 Plan Format & Parsing
- CONTEXT.md delegates format to Claude's Discretion. A strict JSON schema is recommended to allow the Python runner to parse the plan, validate it, and emit it reliably over the Event Bus.
- `l3_autonomy_runner.py` can prompt the CLI runtime to output *only* JSON wrapped in a specific delimiter (or directly parse the stdout).

### 1.4 LLM Self-Reflection & Execution Boundary
- The runner must evaluate the plan (self-reflection). It can do this by feeding the generated plan *back* to the LLM with a verification prompt.
- Read-only commands (like `ls` or `cat`) are allowed during validation. If we use `claude-code`, it naturally executes tools. If we just want a static check with some commands, we can let `claude-code` run a validation pass.
- Execution happens inline sequentially: The Python runner parses the steps, and for each step, invokes the CLI runtime, captures the result, and emits detailed metadata to the Event Bus.

### 1.5 Fallback Behavior
- If a step fails, the runner catches the error, prompts the LLM with the error and the remaining steps, and asks for a revised plan (Auto-modify and Retry).
- If retries are exhausted, the runner emits a state change to `BLOCKED` and exits, keeping the container alive or allowing the orchestrator to keep the task state as `BLOCKED`.
- *Note on container lifespan*: If `entrypoint.sh` exits, the container dies. If we want to allow direct plan editing while `BLOCKED`, the runner must `sleep` or poll for plan updates from the orchestrator.

## 2. Dependencies
- Modifying `openclaw-l3-specialist:latest` behavior (requires updates to `entrypoint.sh` or injecting a new python script).
- Adding new event models to `openclaw.autonomy.events`.

## 3. Recommended Approach for Planning
1. **Runner Script:** Create `packages/orchestration/src/openclaw/autonomy/runner.py`.
2. **Modify Entrypoint:** Update `entrypoint.sh` to delegate to `python3 /openclaw_src/openclaw/autonomy/runner.py` if `AUTONOMY_ENABLED=1`.
3. **Planning Stage:** Runner invokes `claude-code` with a system prompt instructing it to produce a JSON execution plan for the given `$TASK_DESCRIPTION`.
4. **Validation Stage:** Runner invokes `claude-code` again to review the generated JSON.
5. **Execution Loop:** Runner iterates over the JSON steps, invoking `claude-code` for each, emitting events for progress and handling failures via retry/replanning logic.

## Validation Architecture
- **Unit Tests:** `packages/orchestration/tests/autonomy/test_runner.py` with mocked CLI invocations.
- **Integration Tests:** Test the full two-stage pipeline with dummy bash commands.
- **Observability Check:** Verify that `AutonomyPlanGenerated` and step progress events appear on the Event Bus.
