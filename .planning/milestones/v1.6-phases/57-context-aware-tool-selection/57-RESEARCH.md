# Phase 57 Research: Context-Aware Tool Selection

## Objective
Implement AUTO-03: Context-aware tool selection based on task intent. The L3 agent must dynamically identify and constrain the tools it uses depending on the specific requirements of the task.

## Current Architecture Analysis
1. **Autonomy Runner (`runner.py`)**:
   - Currently runs a `planning_phase` and an `execution_phase`.
   - Tool usage is entirely open. `claude-code` or `codex` is invoked with a static `soul_file` (system prompt) and relies on the underlying LLM's default toolset (Bash, FileRead, FileEdit, etc.).
   
2. **Missing Capabilities**:
   - No pre-execution analysis of what tools are actually needed.
   - No constraints passed to the underlying CLI runtime to limit scope.

## Technical Options

### Option 1: CLI-level Tool Disablement (Hard Constraint)
If the CLI runtime (e.g., `claude-code`) supports explicitly disabling tools via CLI flags (e.g., `--disable-tool bash`), we could parse the command and pass these flags.
*Pros*: Highly secure, physically prevents tool usage.
*Cons*: Requires specific support from the CLI tool which might not exist universally across `claude-code` or `codex`.

### Option 2: System Prompt Injection (Soft Constraint via LLM)
Before planning, the runner analyzes the task to categorize the intent and select required tools. It then dynamically generates a "Tool Constraints" appendix and injects it into the system prompt or the step execution prompts.
*Pros*: Universal, works with any LLM CLI, easy to implement in `runner.py`.
*Cons*: "Soft" constraint; a highly hallucinatory LLM might still attempt to use a restricted tool.

## Selected Approach: Dynamic Tool Profile Injection (Option 2)
For the MVP of Phase 57, we will implement **Dynamic Tool Profile Injection**:
1. **Tool Categories**: Define a set of known tool categories in `runner.py` (e.g., `file_read`, `file_write`, `shell_execution`, `git_operations`).
2. **Intent Analysis**: Add a new method `_analyze_tool_requirements(self) -> List[str]` called at the start of `planning_phase`. It queries the LLM to output a JSON array of strictly required tool categories based on the `task_description`.
3. **Constraint Enforcement**: Build a constraint string (e.g., `CRITICAL INSTRUCTION: For this task, you are STRICTLY LIMITED to the following tool categories: {selected_tools}. Do not use any other tools.`)
4. **Prompt Modification**: Inject this constraint string into the `prompt` used during `execute_step` and `planning_phase`.

## Implementation Strategy
- Modify `packages/orchestration/src/openclaw/autonomy/runner.py`.
- Add `_analyze_tool_requirements` method.
- Update `planning_phase` to call this method and store `self.active_tools`.
- Prepend the tool constraint warning to all prompts sent to `_invoke_cli`.
- Emit a new event `AutonomyToolsSelected(task_id, tools)` to inform the Orchestrator/L2 of the chosen toolset.
