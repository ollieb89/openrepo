# SKILL: PumplAI Delegation
**Description:** Primary delegation logic for ClawdiaPrime to route tasks to PumplAI_PM.

## Logic
1. Validate task context (ensures it pertains to PumplAI).
2. Serialize context into `task_packet.json`.
3. Invoke the `pumplai_pm` agent:
   ```bash
   openclaw agent --to pumplai_pm --deliver --message "$(cat task_packet.json)"
```
4. Await response and verify semantic snapshot integrity.

## Tools
- `agentToAgent` (simulated via `openclaw agent`)
- `fs`
