# Phase 56 Research: Confidence-Based Escalation Logic

## Objectives
Implement AUTO-02: L3 agents autonomously determining when to escalate based on confidence drops. Provide a mechanism for the agent to pause, notify the orchestrator, and wait for manual intervention or L2 direction.

## Current State Analysis
1. **L3 Autonomy Runner (`runner.py`)**:
   - Currently, if a step fails during the `execution_phase`, it performs a single fallback retry.
   - If the retry fails, it escalates directly to `BLOCKED`, updates the `JarvisState`, calls `on_task_failed` hook, and exits the process (`sys.exit(1)`).
   - There is no concept of a gradual `confidence_score` or varying thresholds.
   - It terminates rather than pausing.

2. **Event Bus (`events.py`)**:
   - Defines `AutonomyConfidenceUpdated` and `AutonomyEscalationTriggered` event classes.
   - Includes logic to debounce confidence updates.
   - These events are currently defined but not emitted by the `runner.py`.

3. **Spawn Configuration (`spawn.py`)**:
   - Injects `AUTONOMY_ENABLED` and `AUTONOMY_MAX_RETRIES` environment variables.
   - No threshold environment variables exist yet.

## Architectural Design

### 1. Confidence Score Tracking
- Introduce a `ConfidenceTracker` class or logic inside `AutonomyRunner`.
- **Initial Score**: 1.0 (100%).
- **Deduction Factors** (based on `56-CONTEXT.md`):
  - **Repeated Step Failure**: -0.3 per consecutive failure.
  - **Tool Execution Errors**: -0.15 per tool failure (e.g., parsing `stderr` or detecting syntax error keywords).
  - **Unclear Requirements**: If the LLM generates output containing phrases like "I cannot proceed", "I need more context", or "unclear", immediately deduct -0.5.
- Emit `AutonomyConfidenceUpdated` on every change.

### 2. Threshold Configuration
- Read `AUTONOMY_CONFIDENCE_THRESHOLD` environment variable (default: `0.4`).
- Read `AUTONOMY_SKILL_THRESHOLDS` environment variable (JSON string, e.g., `{"bash": 0.6}`).
- If the current action involves a specific tool/skill, apply the specific threshold.

### 3. Escalation Trigger & Pause
- When `score < threshold`, the runner transitions to `ESCALATING`.
- Emits `AutonomyEscalationTriggered(reason="Confidence dropped below threshold: 0.3 < 0.4", confidence=0.3)`.
- **Indefinite Pause Mechanism**:
  - Instead of `sys.exit(1)`, enter an `asyncio.Event().wait()` loop.
  - Listen for an "unpause" signal. This can be implemented by periodically polling a `control.json` file in the workspace state directory (`/workspace/.openclaw/{project}/task-{task_id}-control.json`), or by subscribing to an `AutonomyResume` event on the bus. For simplicity and robustness across container boundaries, a local file-based sentinel (e.g., `unpause.txt` or `resume` flag in `workspace-state.json`) is recommended.

### 4. Notification Mechanism
- The `events.py` bus propagates the `AutonomyEscalationTriggered` event to the host (since it maps to the underlying OpenClaw event bus).
- The Orchestrator/L2 (running on the host) will listen to this event.
- *Implementation detail:* For this phase, we will add a subscriber in the orchestration daemon (e.g., in `hooks.py` or a new `notifications.py` module) that logs a high-priority alert or simulates a Telegram ping, satisfying the "Direct Ping" requirement.

## Recommended Implementation Plan
1. **Plan 56-01: Confidence Scoring & Environment Settings**
   - Update `spawn.py` to inject `AUTONOMY_CONFIDENCE_THRESHOLD` and `AUTONOMY_SKILL_THRESHOLDS`.
   - Update `runner.py` to calculate and maintain confidence score based on failures and outputs.
   - Emit `AutonomyConfidenceUpdated`.

2. **Plan 56-02: Escalation, Pause, and Notification**
   - Implement threshold checks in `runner.py`.
   - On threshold breach, emit `AutonomyEscalationTriggered`.
   - Implement indefinite pause loop polling for an unpause signal (e.g., checking a file or `JarvisState` flag).
   - Add a listener on the host side (e.g., in `hooks.py`) to handle `AutonomyEscalationTriggered` and simulate/send the direct ping notification.
