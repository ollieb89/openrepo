---
name: openclaw-review
description: "L2 diff review workflow in OpenClaw. Use when reviewing L3 work on a staging branch, capturing snapshots of L3 output, making merge or reject decisions, writing post-review memory, or setting up the review skill. Triggers for: \"review L3 work\", \"review diff\", \"merge branch\", \"reject branch\", \"l3/task branch\", \"openclaw snapshot\", \"L2 review\", \"diff review\", \"code review L3\", \"awaiting review\"."
metadata:
  openclaw:
    emoji: "✅"
    category: "orchestration-core"
---

# L2 Diff Review Workflow

L3 work lands on `l3/task-{task_id}` branches. L2 reviews the diff before merging or rejecting.

## Review Flow

```
Task status: awaiting_review
      ↓
1. Capture snapshot (diff + state)
      ↓
2. Read diff and validate
      ↓
3. Decision: approve or reject
      ↓
4. Merge (--no-ff) or delete branch
      ↓
5. Update task state → completed / rejected
      ↓
6. Memory extraction fires automatically
```

## Capture Snapshot

```python
from openclaw.snapshot import capture_snapshot

snapshot = capture_snapshot(
    project_id="pumplai",
    task_id="task-abc123",
    workspace_path="$HOME/Development/Projects/pumplai"
)
# snapshot.diff — full git diff
# snapshot.files_changed — list of changed files
# snapshot.commits — list of L3 commits
# snapshot.state — current workspace state
```

## Review Diff Manually

```bash
cd /path/to/workspace
git diff main l3/task-{task_id}
git log main..l3/task-{task_id} --oneline
```

## Merge (Approve)

```bash
cd /path/to/workspace
git merge --no-ff l3/task-{task_id} -m "L2 review: approve task-{task_id}"
```

Then update state:
```python
from openclaw.state_engine import StateEngine

engine = StateEngine(project_id, workspace_path)
engine.transition(task_id, "completed", reviewer_notes="Approved: clean implementation")
```

## Reject

```bash
cd /path/to/workspace
git branch -d l3/task-{task_id}
```

Then update state:
```python
engine.transition(task_id, "rejected", reviewer_notes="Rejected: {reason}")
```

On rejection, L2 should create a new task with corrected instructions.

## Review Checklist

Before approving, verify:
- [ ] All acceptance criteria met
- [ ] No secrets or credentials committed
- [ ] Tests pass (if applicable)
- [ ] No unrelated file changes
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with main

## Skills Integration

The `review` skill at `skills/review/` provides the L2 review tool. Key functions:
```python
from skills.review.review import ReviewSkill

reviewer = ReviewSkill(project_id, workspace_path)
result = reviewer.review_task(task_id)
# result.recommendation: "approve" | "reject" | "needs_changes"
# result.issues: list of findings
# result.notes: review summary
```

See [references/review-patterns.md](references/review-patterns.md) for criteria by agent type and common rejection reasons.
