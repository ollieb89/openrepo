# Phase 57 Context: Context-Aware Tool Selection

## Objectives
Implement AUTO-03: Context-aware tool selection based on task intent for L3 agents.

## Current State
- The L3 Autonomy Runner currently initiates `claude-code` or `codex` using a static system prompt (`soul_file`) and standard CLI arguments.
- It has no explicit mechanism to filter or select specific tools (e.g., restricting `bash` usage if the task is purely documentation, or ensuring `docker` is available only if the task requires container management).
- Tool selection is implicitly handled by the LLM, without formal boundaries or explicit "context-aware" loading before execution.

## Requirements (AUTO-03)
- The autonomy framework must analyze the `task_description` or intent before/during the planning phase to determine which tools are strictly necessary.
- Tool boundaries must be enforced or explicitly injected into the execution context.
- Provide a clear mapping between task intent (e.g., "code_modification", "search_and_summarize") and tool allowances.

## Scope
- Expanding the L3 autonomy runner to dynamically build a tool allowance list.
- Modifying the CLI runtime invocation to explicitly include/exclude tools, or passing the tool selection list in the system prompt.
- **Out of Scope**: Building entirely new tools. We are orchestrating existing tool access based on context.
