# Multi-Agent Coordination Patterns

## Pattern 1: Parallel Fan-Out

Dispatch N independent tasks concurrently, collect results.

```bash
# Dispatch in parallel (background)
openclaw agent --agent pm --message "Task A" --json > /tmp/task_a.json &
openclaw agent --agent pm --message "Task B" --json > /tmp/task_b.json &
openclaw agent --agent pm --message "Task C" --json > /tmp/task_c.json &
wait

# Aggregate
jq -s '.' /tmp/task_*.json
```

Use when tasks are independent and results can be merged afterward.

## Pattern 2: Sequential Chain

Output of task N becomes input to task N+1.

```bash
RESULT=$(openclaw agent --agent pm --message "Research X" --json | jq -r '.text')
openclaw agent --agent pm --message "Implement based on: $RESULT"
```

Use for research → implementation → testing pipelines.

## Pattern 3: Fan-Out with Review Gate

Spawn parallel L3s, then L2 reviews all before merging.

```
L2 spawns L3-A (feature), L3-B (tests) in parallel
  ↓
Both complete → awaiting_review
  ↓
L2 reviews A diff: tests pass? → merge A
L2 reviews B diff: coverage OK? → merge B
  ↓
L2 runs integration → final validation
```

## Pattern 4: Conditional Branching

L2 decides next step based on L3 outcome.

```python
result = await spawn_l3_specialist(task_description="Try approach A", ...)
if result.status == "completed":
    # proceed with approach A
    next_task = "Build on top of approach A result"
else:
    # fallback to approach B
    next_task = "Implement approach B from scratch"
await spawn_l3_specialist(task_description=next_task, ...)
```

## Pattern 5: Supervisor Loop

L2 runs L3 in a loop until quality gate passes.

```python
attempts = 0
while attempts < 3:
    result = await spawn_l3_specialist(task_description=task, ...)
    if passes_quality_gate(result):
        break
    attempts += 1
    task = f"Previous attempt failed: {result.error}. Retry with fix."
```

## Anti-Patterns to Avoid

- **Race on state file**: never write `workspace-state.json` without acquiring `fcntl.flock()`
- **Bypassing pool**: never spawn L3 without `PoolRegistry.acquire()` — resource exhaustion risk
- **Shell interpolation in directives**: always use `execFileSync` with array args
- **Monolithic tasks**: split work into independently verifiable chunks for better L3 success rates
