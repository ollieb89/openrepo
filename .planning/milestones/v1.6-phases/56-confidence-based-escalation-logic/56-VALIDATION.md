# Phase 56 Validation Strategy: Confidence-Based Escalation Logic

## 1. Test Infrastructure Needed
- Pytest framework (already available).
- Mocking for `AutonomyEventBus` and `JarvisState` (already used in `test_runner.py`).
- Mocking for the `asyncio` pause loop to prevent test hanging while verifying the pause behavior.

## 2. Verification Map

| Requirement | Test Method | Success Criteria |
|-------------|-------------|------------------|
| Confidence tracking calculates correctly | Unit Test | Confidence score drops by exactly 0.3 on step failure and 0.15 on tool error keywords. |
| Escalation triggers on threshold breach | Unit Test | `AutonomyEscalationTriggered` event is emitted when score < threshold. |
| Container pauses on escalation | Unit Test | Runner enters the polling loop for unpause signal instead of calling `sys.exit(1)`. |
| Unpause resumes execution | Unit Test | Modifying the sentinel unpause file breaks the pause loop and resumes/terminates execution safely. |
| Configuration injection | Integration | `spawn.py` correctly passes `AUTONOMY_CONFIDENCE_THRESHOLD` and skill thresholds to the L3 container environment. |
| Orchestrator Notification | Integration | Host-side event listener catches `AutonomyEscalationTriggered` and executes the notification callback/log. |

## 3. Manual Verifications
1. **Triggering Escalation:** Spawn an L3 task with a deliberately impossible objective (e.g., "Run a non-existent command 5 times").
2. **Observing Pause:** Use `docker ps` to verify the container remains running (paused) rather than exiting.
3. **Observing Notification:** Check the orchestrator/L2 daemon logs to see the simulated "Telegram Direct Ping" alert containing the escalation reason and confidence score.
4. **Testing Unpause:** Manually write the unpause signal to the task's state file or unpause sentinel, and observe the container resuming or safely terminating.

## 4. Sign-off Criteria
- All unit and integration tests pass.
- A live container successfully self-escalates, emits the notification, and waits indefinitely without crashing.
