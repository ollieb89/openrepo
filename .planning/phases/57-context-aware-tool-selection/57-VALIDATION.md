# Phase 57 Validation Strategy: Context-Aware Tool Selection

## 1. Test Infrastructure Needed
- Pytest framework (already active in `test_runner.py`).
- Mocking for `_invoke_cli` to simulate the LLM's response during the tool analysis phase.

## 2. Verification Map

| Requirement | Test Method | Success Criteria |
|-------------|-------------|------------------|
| Intent Analysis Parsing | Unit Test | `_analyze_tool_requirements` successfully parses a JSON array of tool categories from the LLM output. |
| Intent Analysis Fallback | Unit Test | If the LLM returns invalid JSON or no array, it falls back safely to `["all"]`. |
| Prompt Injection (Planning) | Unit Test | The prompt sent to `planning_phase` includes the explicit constraint string containing the selected tools. |
| Prompt Injection (Execution) | Unit Test | The prompt sent to `execute_step` includes the explicit constraint string. |
| Event Emission | Unit Test | `AutonomyToolsSelected` event is successfully emitted containing the array of selected tools. |

## 3. Manual Verifications
1. **Tool Restriction Observation**: Spawn an L3 container for a pure documentation task. Inspect the orchestrator logs to confirm the `AutonomyToolsSelected` event lists only file reading/writing tools, excluding `shell_execution`.
2. **Execution Integrity**: Confirm that the overall task still completes successfully despite the injected prompt constraints.

## 4. Sign-off Criteria
- All unit tests pass.
- No regressions in `planning_phase` or `execution_phase` behavior when no constraints are required.
- The `AutonomyToolsSelected` event is verifiable in the Orchestrator event bus.
