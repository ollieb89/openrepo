# Phase 58 Validation Strategy: Progress Self-Monitoring

## 1. Test Infrastructure Needed
- Standard `pytest` framework within `test_runner.py`.
- Mocking for `_invoke_cli` to simulate the reflection response returning recovery steps.

## 2. Verification Map

| Requirement | Test Method | Success Criteria |
|-------------|-------------|------------------|
| Deviation Detection | Unit Test | `_detect_deviation` returns `True` if `success=False`, if `duration > 180`, or if error keywords exceed threshold. |
| Reflection Parsing | Unit Test | `_reflect_and_correct` successfully parses a JSON array of steps from LLM output, or returns `[]` on invalid format. |
| Course Correction Event | Unit Test | `AutonomyCourseCorrection` event is successfully emitted during execution phase when a deviation is handled. |
| Dynamic Step Insertion | Unit Test | `execution_phase` correctly splices the recovered steps into the plan list and executes them sequentially. |
| Infinite Loop Protection | Unit Test | Repeated course correction failures trigger natural confidence escalation and `_escalation_pause_loop()`. |

## 3. Sign-off Criteria
- All unit tests pass.
- No regressions in normal planning or un-deviated execution paths.
- The `AutonomyCourseCorrection` event is verifiable in the Orchestrator event bus.
