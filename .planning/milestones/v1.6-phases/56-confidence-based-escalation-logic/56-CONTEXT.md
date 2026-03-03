# Phase 56 Context: Confidence-Based Escalation Logic

This document captures the design decisions and constraints for implementing AUTO-02: agents self-escalating based on confidence thresholds.

## 1. Threshold Configuration
**Decision:** Global default threshold with per-skill overrides.
**Reasoning:** We need a sensible default for general agent operations, but certain high-risk tools (like shell execution) should have a tighter tolerance for failure, triggering escalation faster than safer operations (like reading files).

## 2. Notification Mechanism
**Decision:** EventBus emission (`AutonomyStateChanged(ESCALATING)`) combined with a Direct Ping (e.g., Telegram integration).
**Reasoning:** Emitting an event ensures the dashboard and internal state machines stay synchronized, while the direct ping ensures human operators or L2 agents are immediately aware of the blockage.

## 3. Confidence Factors
**Decision:** The primary factors causing severe confidence drops will be:
- Repeated Task Failures (trying the same step and failing continuously).
- Unclear Requirements (the agent's context or initial plan is too ambiguous).
- Tool Execution Errors (repeatedly getting tool/syntax errors).
**Reasoning:** These three factors accurately represent the state where an LLM is "stuck in a loop" or fundamentally lacks the context to proceed, which requires human/L2 intervention.

## 4. Escalation Timeout
**Decision:** Pause Indefinitely.
**Reasoning:** If an escalation is ignored, the L3 container should pause its execution loop and wait for an external `unpause` or termination command from the Orchestrator. This prevents runaway token usage while keeping the exact context alive for debugging.

## Next Steps
These constraints will inform the detailed technical plans for Phase 56, defining how the `runner.py` calculates confidence, detects failure loops, pauses execution, and triggers the `spawn.py` notification layer.
