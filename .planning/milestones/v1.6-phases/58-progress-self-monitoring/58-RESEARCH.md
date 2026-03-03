# Phase 58 Research: Progress Self-Monitoring

## Objective
Implement AUTO-04: Allow the L3 agent to detect when a step has deviated (via heuristics), pause to reflect via an LLM call, and dynamically insert recovery steps into its execution plan while keeping the confidence score low until the recovery is proven.

## Heuristics Analysis (Hybrid Approach)
We need a `_detect_deviation(success, output, duration)` function that returns `True` if:
1. **Explicit Failure**: `success` is False (i.e. empty output or crash).
2. **Error Density**: The output contains a high frequency of error keywords (e.g., `error`, `exception`, `traceback`).
3. **Time-based**: The step duration exceeds a configured limit (e.g., 180 seconds) without explicit completion.

## Course Correction Mechanics
Currently, `runner.py` executes a hardcoded 1-time fallback retry loop when a step fails. We will replace this with a dynamic replanning approach:
1. **Reflection Prompt**: Query the CLI runtime with the context of the failed step and its output. Ask for a root-cause analysis and exactly 1-2 logical recovery steps formatted as a JSON array.
2. **Dynamic Insertion**: Instead of retrying the failed step, we mark it as failed and bypassed. We take the new `recovery_steps` and splice them into the `steps` array immediately after the current index:
   `steps = steps[:current_step_idx + 1] + recovery_steps + steps[current_step_idx + 1:]`
3. **Loop Protection**: We do not need a new infinite-loop counter. Every failed step or failed recovery step naturally deducts from `self.confidence_score` (-0.3). If recovery fails repeatedly, confidence will quickly drop below `AUTONOMY_CONFIDENCE_THRESHOLD` (0.4), triggering the standard escalation loop and suspending execution. This satisfies the "Prove Recovery First" requirement perfectly.

## Event Telemetry
We will introduce a new event in `events.py`:
`EVENT_COURSE_CORRECTION = "autonomy.course_correction"`
Mapped to `AutonomyCourseCorrection`, capturing:
- `task_id`
- `deviated_step` (the original step payload)
- `recovery_steps` (the new steps being inserted)

## Implementation Plan Strategy
1. **Events Module**: Add `AutonomyCourseCorrection`.
2. **Runner Module**:
   - Add `_detect_deviation` heuristic logic.
   - Add `_reflect_and_correct` LLM call.
   - Refactor the failure block inside `execution_phase` to utilize the new course correction flow instead of the static retry.
3. **Tests**: Verify `_detect_deviation` correctly parses error densities and timeouts. Ensure `execution_phase` correctly splices lists and continues.
