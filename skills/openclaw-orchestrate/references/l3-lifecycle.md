# L3 Container Lifecycle

## Full Task Flow

```
L2 issues task
  │
  ├─ 1. Pool acquire (semaphore)
  ├─ 2. Retrieve memories from memU
  ├─ 3. Build augmented SOUL
  ├─ 4. Write soul-<task_id>.md
  ├─ 5. Create git branch l3/task-{task_id}
  ├─ 6. Start Docker container
  │       openclaw-{project}-l3-{task_id}
  ├─ 7. State → in_progress
  │       (triggers MEMORY.md injection)
  ├─ 8. L3 executes task on branch
  ├─ 9. L3 commits work
  ├─ 10. Container exits
  ├─ 11. State → awaiting_review
  │
  └─ L2 reviews diff
        ├─ approve → git merge --no-ff → state: completed
        │            memory extraction triggered
        └─ reject  → branch deleted → state: rejected
                     memory extraction triggered
```

## State Transitions

| From | To | Trigger |
|------|----|---------|
| pending | in_progress | L2 spawns container |
| in_progress | awaiting_review | container exits 0 |
| in_progress | failed | container exits non-0 / timeout |
| awaiting_review | completed | L2 approves merge |
| awaiting_review | rejected | L2 rejects diff |

## Memory Extraction (Terminal States)

On `completed`, `failed`, or `rejected`, `memory_extractor.py` formats learnings by agent type:
- `L3_CODE` → implementation patterns and gotchas
- `L3_TEST` → test strategies and edge cases
- `L3_REVIEW` → review checklists and quality signals

## Timeout Handling

Default agent runtime timeout: 600s. Override per-task:
```python
await spawn_l3_specialist(..., timeout_seconds=900)
```

On timeout, container is killed, state → `failed`, memory extraction fires.
