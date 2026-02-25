# Review Patterns by Agent Type

## L3_CODE Review Criteria

**Always check:**
- Does the implementation match the task description exactly?
- Are there any hardcoded credentials, secrets, or tokens?
- Are error cases handled (not just happy path)?
- Does the code follow the project's tech stack conventions?
- Are new dependencies justified and minimal?

**Architecture signals:**
- No circular imports or dependency inversions
- Functions/classes are single-responsibility
- No dead code or debug artifacts committed

**Auto-approve candidates:**
- Small, focused changes (<100 lines)
- Pure refactors with identical behavior
- Documentation-only updates

## L3_TEST Review Criteria

**Always check:**
- Do tests actually assert what they claim?
- Are edge cases covered (empty input, None, boundary values)?
- Are tests independent (no shared mutable state)?
- Do fixtures clean up after themselves?

**Coverage signals:**
- New code paths are tested
- Error paths are tested, not just success paths
- Tests run in under 30s total

## L3_REVIEW Review Criteria (meta-review)

**Always check:**
- Is the review actionable (specific line references)?
- Does the review distinguish blocking vs non-blocking issues?
- Are security issues flagged clearly?
- Is the verdict (approve/reject/needs_changes) explicit?

## Common Rejection Reasons

| Reason | Category |
|--------|----------|
| Task not completed as specified | Correctness |
| Tests added but don't test the right thing | Quality |
| Magic numbers / hardcoded values | Maintainability |
| Unrelated files modified | Scope creep |
| Commit message doesn't describe change | Convention |
| Missing error handling for obvious cases | Correctness |
| Import of production secrets | Security |
| L3 committed to main instead of staging branch | Process |

## Re-Task After Rejection

When rejecting, create a new task with:
```python
new_task_description = f"""
Previous attempt ({task_id}) was rejected for: {rejection_reason}

Original task: {original_task_description}

Correction needed: {specific_fix}

Important: Do NOT repeat the previous approach. Instead: {corrected_approach}
"""
```

Include concrete examples of what was wrong and what "done" looks like.
