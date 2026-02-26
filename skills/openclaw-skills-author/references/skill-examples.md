# Skill Examples

## Example 1: Simple Informational Skill

```markdown
---
name: project-conventions
description: Project coding conventions, PR rules, and branch naming. Use when creating PRs, naming branches, or following team standards.
---

# Project Conventions

## Branch Naming
- `feature/TICKET-description`
- `fix/TICKET-description`
- `docs/description`

## Commit Messages
Follow conventional commits: `type(scope): description`
Types: feat, fix, docs, refactor, test, chore

## PR Rules
- Max 400 lines changed per PR
- Must include tests for new features
- Link ticket in PR description
```

## Example 2: Tool-Gated Skill with API Key

```markdown
---
name: image-gen
description: Generate images via Replicate API. Use when asked to create, generate, or draw images. Triggers for: "generate image", "create a picture", "draw", "image of".
metadata: {"openclaw": {"emoji": "🎨", "requires": {"env": ["REPLICATE_API_KEY"]}, "primaryEnv": "REPLICATE_API_KEY"}}
---

# Image Generation

Use the Replicate API to generate images.

API Key is in env as `REPLICATE_API_KEY`.

## Quick Example

\`\`\`python
import replicate
output = replicate.run("stability-ai/sdxl:...", input={"prompt": "..."})
\`\`\`

## Model Options
- `stability-ai/sdxl` — best quality, slow
- `stability-ai/stable-diffusion` — fast, good quality
```

## Example 3: Script-Based Skill

```markdown
---
name: pdf-tools
description: Extract text from PDFs, rotate pages, merge/split PDF files. Triggers for: "pdf", "extract text from", "rotate pdf", "merge pdfs".
metadata: {"openclaw": {"requires": {"bins": ["pdftotext", "pdftk"]}, "install": [{"id": "brew", "kind": "brew", "formula": "poppler", "bins": ["pdftotext"]}, {"id": "brew-pdftk", "kind": "brew", "formula": "pdftk-java", "bins": ["pdftk"]}]}}
---

# PDF Tools

## Extract Text
\`\`\`bash
python3 {baseDir}/scripts/extract_text.py <input.pdf> [output.txt]
\`\`\`

## Rotate Pages
\`\`\`bash
python3 {baseDir}/scripts/rotate.py <input.pdf> <degrees> <output.pdf>
# degrees: 90, 180, 270
\`\`\`

## Merge PDFs
\`\`\`bash
pdftk file1.pdf file2.pdf cat output merged.pdf
\`\`\`
```

## Example 4: Command-Dispatch Skill (Direct Tool)

```markdown
---
name: quick-note
description: Instantly save a note to today's memory log. /quick-note <text>
user-invocable: true
command-dispatch: tool
command-tool: memory_write
command-arg-mode: raw
metadata: {"openclaw": {"emoji": "📝"}}
---

Saves the note directly to today's memory file without going through the model.
```

## Example 5: Multi-Agent Workflow Skill

```markdown
---
name: code-review-workflow
description: Run a full L2→L3 code review workflow. Spawns an L3_REVIEW container to review a diff and returns structured feedback. Use when asked to review a PR, audit code changes, or perform automated review.
metadata: {"openclaw": {"requires": {"bins": ["docker"], "env": ["OPENCLAW_PROJECT_ID"]}}}
---

# Code Review Workflow

1. Get the diff to review (branch name or git range)
2. Spawn L3_REVIEW container via skills/spawn/spawn.py with agent_type="L3_REVIEW"
3. Pass diff as TASK_DESCRIPTION
4. Wait for completion and read output from state engine
5. Return structured feedback: summary, issues, suggestions, verdict

## Invocation

\`\`\`python
from skills.spawn.spawn import spawn_l3_specialist

result = await spawn_l3_specialist(
    task_id=f"review-{branch_name}",
    task_description=f"Review diff on branch {branch_name}. Focus: correctness, security, style.",
    project_id=os.environ["OPENCLAW_PROJECT_ID"],
    agent_type="L3_REVIEW"
)
\`\`\`
```
