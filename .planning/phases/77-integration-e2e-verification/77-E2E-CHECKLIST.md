# Phase 77: Integration E2E Verification Checklist

Manual verification steps for INTG-01 success criteria requiring a live system.

## Prerequisites

- [ ] Docker running (`docker ps` succeeds)
- [ ] Gateway running (`curl http://localhost:18789/health` returns 200)
- [ ] Dashboard running (`make dashboard` → http://localhost:6987)
- [ ] memU service running (`make memory-health`)
- [ ] At least one project configured (`openclaw-project list`)

## INTG-01 Criterion 1: L1 dispatch → L3 task appears within 5 seconds

Steps:
1. Open dashboard at http://localhost:6987
2. Issue a directive at L1:
   ```bash
   openclaw agent --agent clawdia_prime --message "Write a hello world Python script"
   ```
3. Watch the dashboard task board
4. [ ] L3 task appears within 5 seconds of directive

## INTG-01 Criterion 2: L3 live output stream visible

Steps:
1. Click on the newly appeared L3 task row in the task board
2. [ ] Terminal panel opens showing live container output
3. [ ] Output auto-scrolls as new lines arrive

## INTG-01 Criterion 3: Post-completion metrics + timeline

After the L3 task completes:
1. Navigate to the Metrics page in the dashboard
2. [ ] Completed task count in metrics reflects the finished task
3. [ ] Pipeline timeline row shows: L1 dispatch → L2 decomposition → L3 execution
4. [ ] Each segment has a timestamp and duration label

## INTG-01 Criterion 4: Event stream completeness

Monitor events during a full task run (dashboard devtools, Network tab → SSE endpoint → EventStream):
- [ ] `task.created` event appears
- [ ] `task.started` event appears
- [ ] `task.output` events appear (multiple)
- [ ] `task.completed` event appears
- [ ] No gap between events (all arrive within 2s of actual state transition)

## Sign-Off

Date: ___________
Verified by: ___________
Notes: ___________
