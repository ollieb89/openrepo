# Phase 12: Soul Templating - Summary

## Delivered

- `orchestration/soul_renderer.py` - Renderer module with 4 public functions
- `agents/_templates/soul-default.md` - Generic L2 agent default template
- `projects/pumplai/soul-override.md` - PumplAI HIERARCHY and BEHAVIORAL PROTOCOLS section overrides
- Updated `projects/pumplai/project.json` with `agent_display_name`

## API

```python
from orchestration.soul_renderer import render_soul

# Render SOUL.md content for a project
soul_content = render_soul('pumplai')

# Lower-level functions
from orchestration.soul_renderer import parse_sections, merge_sections, build_variables
```

## Golden Baseline

`render_soul('pumplai')` produces byte-for-byte identical output to `agents/pumplai_pm/agent/SOUL.md`.

## Variable Contract

Template variables available:
- `$project_name` - Project display name
- `$project_id` - Project ID
- `$agent_name` - From `agent_display_name` or `agents.l2_pm`
- `$tier` - Always "L2"
- `$tech_stack_frontend` - From `tech_stack.frontend`
- `$tech_stack_backend` - From `tech_stack.backend`
- `$tech_stack_infra` - From `tech_stack.infra`
- `$workspace` - OpenClaw runtime workspace path

## Override Mechanism

Create `projects/<id>/soul-override.md` with `## Section` headers to override
corresponding sections from the default template. New sections are appended.
Sections in the override replace default sections with the same name.
