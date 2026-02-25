# SOUL Template Injection Reference

## Template Files

| File | Purpose |
|------|---------|
| `soul-default.md` | Base SOUL for all L3 containers |
| `projects/{project_id}/soul-override.md` | Per-project SOUL customization |
| `data/{project_id}/soul-{task_id}.md` | Final augmented SOUL (generated at spawn time) |

## `$variable` Placeholders (safe_substitute)

OpenClaw uses `string.Template.safe_substitute()` — unknown variables left as-is (no KeyError).

Available placeholders in SOUL templates:

| Placeholder | Value |
|-------------|-------|
| `$PROJECT_ID` | project identifier |
| `$TASK_ID` | task identifier |
| `$TASK_DESCRIPTION` | the task being executed |
| `$AGENT_TYPE` | L3_CODE, L3_TEST, or L3_REVIEW |
| `$WORKSPACE_PATH` | mounted workspace path |
| `$MEMORY_CONTEXT` | pre-fetched memories (2000 char cap) |
| `$PROJECT_TECH_STACK` | from project.json tech_stack |
| `$PROJECT_CONVENTIONS` | from project.json conventions |

## Memory Context Format

```
## Relevant Memories

[memory excerpt 1]
---
[memory excerpt 2]
---
(capped at 2000 characters total)
```

If memU is unavailable, `$MEMORY_CONTEXT` is replaced with empty string (graceful degradation).

## Override Example (`soul-override.md`)

```markdown
## Project-Specific Rules for $PROJECT_ID

- Always use TypeScript strict mode
- Follow conventional commits
- Never touch `src/legacy/` without explicit approval
- $MEMORY_CONTEXT
```

## Augmentation Logic

```python
def _build_augmented_soul(default_soul, override_soul, memory_context, task_vars):
    base = Template(default_soul).safe_substitute(task_vars)
    if override_soul:
        override = Template(override_soul).safe_substitute(task_vars)
        return f"{base}\n\n{override}"
    return base
```
