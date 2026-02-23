# Phase 12: SOUL Templating - Research

**Researched:** 2026-02-23
**Domain:** Python template rendering, markdown section merging, golden-baseline file generation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Template structure**
- Default template is a "generic L2 agent" — not PumplAI-specific
- PumplAI provides overrides to reproduce its current SOUL.md exactly
- New projects without overrides get the generic default with variables filled in
- Section structure at Claude's discretion (current 3-section pattern as starting point: HIERARCHY, CORE GOVERNANCE, BEHAVIORAL PROTOCOLS)
- Override granularity is at the ## section level — override replaces an entire section
- Title line (`# Soul: $agent_name ($tier)`) is auto-generated from variables, not overridable content

**Override merge behavior**
- Override file uses same markdown format as SOUL.md — partial file with ## section headers for sections being replaced
- Sections NOT in the override are kept from the default template (additive override model)
- New sections in the override (not in default template) are allowed and appended to output
- Variable substitution ($project_name, $tech_stack_*, etc.) happens in both default template and override files

### Claude's Discretion
- Exact section names and content of the generic default template
- Variable naming beyond $project_name and $tech_stack_* (contract details)
- How missing/undefined variables are handled
- Renderer invocation method (CLI command, function call, etc.)
- Where rendered output is written
- Error handling for malformed overrides

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-04 | SOUL.md default template with `$project_name` and `$tech_stack_*` substitution points | `string.Template.safe_substitute()` confirmed as the correct tool; variable mapping from project.json verified |
| CFG-05 | Projects can override SOUL.md with a custom file in `projects/<id>/soul-override.md` | Section-level merge algorithm designed; override location locked in CONTEXT.md specifics |
</phase_requirements>

## Summary

Phase 12 implements a SOUL.md renderer that produces agent identity files from a default template plus an optional per-project section-level override. The technology decision is already locked: Python's `string.Template.safe_substitute()` from the standard library (STATE.md: "SOUL templating via `string.Template.safe_substitute()` — not Jinja2, not installed, overkill"). No new dependencies are required.

The golden baseline requirement drives the design: the existing `agents/pumplai_pm/agent/SOUL.md` must be byte-for-byte reproducible from template + override. Analysis of the golden file shows it has three `##` sections. The CORE GOVERNANCE and BEHAVIORAL PROTOCOLS sections are fully reproducible from the default template with variable substitution from `project.json`'s `tech_stack` fields. The HIERARCHY section contains PumplAI-specific content (specific subordinate names, a PumplAI-specific superior sentence, a non-project-workspace path) that cannot come from variables alone — it must be provided via `projects/pumplai/soul-override.md` as a section replacement.

The renderer module belongs in `orchestration/soul_renderer.py`, consistent with the existing orchestration module pattern. It reads the default template from `agents/_templates/soul-default.md`, loads variables from project config, applies the optional `projects/<id>/soul-override.md`, runs substitution, and writes the rendered SOUL.md to the designated agent directory.

**Primary recommendation:** Implement a standalone `orchestration/soul_renderer.py` module with a `render_soul(project_id)` function and an optional CLI entry point, using `string.Template.safe_substitute()` for substitution and a section-keyed dict merge for override application.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `string.Template` | stdlib (Python 3.x) | Variable substitution in template text | Already decided (STATE.md); no external deps; `safe_substitute()` leaves unresolved `$var` intact instead of raising |
| `pathlib.Path` | stdlib | File path construction | Already used throughout all orchestration modules |
| `json` | stdlib | Load project.json for variable mapping | Already used throughout all orchestration modules |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `argparse` | stdlib | CLI entry point for renderer | When invoked as `python3 orchestration/soul_renderer.py --project pumplai` |
| `difflib` | stdlib | Golden baseline test — compute diff between rendered output and golden file | Only in tests/verification scripts |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `string.Template` | Jinja2 | Jinja2 is more powerful but not installed; `string.Template` is sufficient for this use case |
| `string.Template` | f-strings | f-strings require compile-time variable names; template files need runtime variable names |
| Section-keyed dict merge | Regex-based replacement | Dict merge is simpler, more predictable, and easier to test |

**Installation:** No installation required — all stdlib.

## Architecture Patterns

### Recommended Project Structure

```
orchestration/
├── soul_renderer.py       # Renderer module: render_soul(), parse_sections(), merge_sections()
agents/
└── _templates/
    └── soul-default.md    # Generic L2 agent default SOUL template
projects/
└── pumplai/
    ├── project.json       # Variables source: project_name, tech_stack.*, workspace, agents.*
    └── soul-override.md   # PumplAI HIERARCHY section override (for golden baseline)
```

### Pattern 1: safe_substitute with explicit variable mapping

**What:** Build a flat dict of all substitution variables from project.json fields and a known variable name contract, then call `string.Template(text).safe_substitute(variables)`.

**When to use:** Always — `safe_substitute()` leaves unresolved `$var` intact (no KeyError), which is the correct behavior for undefined variables at Claude's discretion.

**Example:**
```python
# Source: Python stdlib string.Template documentation
import string

def build_variables(project_config: dict) -> dict:
    """Map project.json fields to template variable names."""
    tech_stack = project_config.get("tech_stack", {})
    agents = project_config.get("agents", {})
    return {
        "project_name": project_config.get("name", project_config.get("id", "")),
        "agent_name": _format_agent_name(project_config),
        "tier": "L2",
        "tech_stack_frontend": tech_stack.get("frontend", ""),
        "tech_stack_backend": tech_stack.get("backend", ""),
        "tech_stack_infra": tech_stack.get("infra", ""),
        "workspace": project_config.get("workspace", ""),
    }

def render_text(text: str, variables: dict) -> str:
    return string.Template(text).safe_substitute(variables)
```

### Pattern 2: Section-keyed dict merge for override

**What:** Parse both the default template and the override file into a dict of `{section_name: section_text}`, merge by replacing keys from the override, then reassemble in default template order (appending novel override sections at the end).

**When to use:** Every render call — this is the core merge algorithm.

**Example:**
```python
def parse_sections(text: str) -> dict:
    """
    Parse a markdown file into {section_name: full_section_text} dict.

    Section text includes the ## header line and all content until the next ## header.
    Title line (# ...) is excluded — handled separately.
    """
    sections = {}
    order = []
    current_key = None
    current_lines = []

    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            if current_key is not None:
                sections[current_key] = "".join(current_lines)
            current_key = line[3:].strip()
            order.append(current_key)
            current_lines = [line]
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "".join(current_lines)

    return sections, order


def merge_sections(default_sections: dict, default_order: list,
                   override_sections: dict, override_order: list) -> str:
    """
    Merge override sections into default sections.

    - Sections in override replace corresponding default sections
    - Sections in override not in default are appended at end
    - Sections in default not in override are kept unchanged
    """
    merged = {**default_sections}  # start with all defaults
    merged.update(override_sections)  # override replaces matching keys

    # Reconstruct in default order, then append novel override sections
    result_order = default_order.copy()
    for key in override_order:
        if key not in result_order:
            result_order.append(key)

    return "\n".join(merged[key].rstrip("\n") for key in result_order if key in merged) + "\n"
```

### Pattern 3: Title line generation (not in template body)

**What:** The title line `# Soul: $agent_name ($tier)` is auto-generated and prepended before section content, not parsed as a section. This is per the locked decision.

**Example:**
```python
def render_soul(project_id: str) -> str:
    config = load_project_config(project_id)
    variables = build_variables(config)

    # 1. Load and substitute default template
    template_path = _find_project_root() / "agents" / "_templates" / "soul-default.md"
    default_text = render_text(template_path.read_text(), variables)

    # 2. Parse default into sections (title line stripped separately)
    default_sections, default_order = parse_sections(default_text)

    # 3. Load override if present
    override_path = _find_project_root() / "projects" / project_id / "soul-override.md"
    override_sections, override_order = {}, []
    if override_path.exists():
        override_text = render_text(override_path.read_text(), variables)
        override_sections, override_order = parse_sections(override_text)

    # 4. Merge and assemble
    title = string.Template("# Soul: $agent_name ($tier)").safe_substitute(variables)
    body = merge_sections(default_sections, default_order, override_sections, override_order)
    return title + "\n\n" + body
```

### Anti-Patterns to Avoid

- **Parsing section headers with regex across the full file:** Use line-by-line iteration instead; regex multiline patterns with `##` are fragile when section content contains `##` in code blocks.
- **Using `string.Template.substitute()` instead of `safe_substitute()`:** `substitute()` raises `KeyError` on undefined variables; `safe_substitute()` leaves them intact, which is the correct behavior since undefined variables signal missing config rather than a crash.
- **Writing rendered output to `agents/<id>/agent/SOUL.md` during tests:** The golden baseline test should compare rendered string to the file's content, not overwrite the file.
- **Storing the override at `projects/<id>/SOUL.md`:** Requirements (CFG-05 as clarified in CONTEXT.md specifics) lock the override path to `projects/<id>/soul-override.md`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Variable substitution | Custom `{{var}}` regex replacement | `string.Template.safe_substitute()` | Handles edge cases: literal `$$`, identifiers with underscores, graceful missing-variable handling |
| File diff for golden baseline test | Custom line-diff loop | `difflib.unified_diff()` or `diff -u` in subprocess | Produces human-readable diff output with correct line numbers |

**Key insight:** The section-merge algorithm is simple enough to hand-roll (it's 20 lines of Python), but the substitution layer must not be hand-rolled — `string.Template` handles the `$$` escape, identifier boundary detection, and `safe_substitute` semantics correctly.

## Common Pitfalls

### Pitfall 1: workspace path mismatch breaks golden baseline

**What goes wrong:** The `agents/pumplai_pm/agent/SOUL.md` golden file contains `/home/ollie/.openclaw/workspace` (the OpenClaw runtime workspace), but `projects/pumplai/project.json` has `workspace: /home/ollie/Development/Projects/pumplai` (the PumplAI application codebase). These are two different paths. If you try to source `$workspace` from `project.json`, the rendered HIERARCHY section won't match the golden baseline.

**Why it happens:** The SOUL.md `workspace` line describes the L2 agent's operational workspace (where it reads/writes OpenClaw state), not the application codebase being developed.

**How to avoid:** The HIERARCHY section for PumplAI must come from `soul-override.md` which contains the literal `/home/ollie/.openclaw/workspace` path (or a `$openclaw_workspace` variable mapped to the OpenClaw root workspace). The default template's HIERARCHY section can use `$workspace` mapped to the OpenClaw runtime workspace directory, not the project's application workspace.

**Warning signs:** Golden baseline diff is non-empty only in the HIERARCHY section's Scope line.

### Pitfall 2: Trailing newline mismatches cause non-empty golden diff

**What goes wrong:** The rendered output has a different number of trailing newlines than the golden file (e.g., one trailing `\n` vs two). The diff shows only `\ No newline at end of file` or an extra blank line.

**Why it happens:** Markdown editors, template authors, and `str.rstrip()` all handle trailing whitespace differently. The golden file ends with exactly one `\n` after the last bullet.

**How to avoid:** Normalize trailing whitespace in the renderer: `rendered.rstrip("\n") + "\n"`. Confirm the golden file also ends with exactly one `\n` (it does — verified: `"..escalate to ClawdiaPrime.\n"`).

**Warning signs:** `diff` output shows only `\ No newline at end of file` or `+` with just blank lines.

### Pitfall 3: Section parser misidentifies headers inside code blocks

**What goes wrong:** A `##` at the start of a line inside a fenced code block (` ``` `) is parsed as a section header, splitting the section incorrectly.

**Why it happens:** Simple line-by-line `startswith("## ")` matching doesn't track fenced-code state.

**How to avoid:** For SOUL.md content (prose identity files), code blocks are not expected. The current golden file has none. Document this assumption and add a lint check in the renderer if the template/override contains triple-backtick fences.

**Warning signs:** Section count is higher than expected; section content is truncated.

### Pitfall 4: soul-override.md for PumplAI must exactly reproduce HIERARCHY section

**What goes wrong:** The override HIERARCHY section has subtle differences from the golden file (different punctuation, missing "All major project decisions..." sentence, wrong subordinate names).

**Why it happens:** The override file is written by hand and diverges from the golden file.

**How to avoid:** The override file is created as part of this phase with content derived directly from the existing `agents/pumplai_pm/agent/SOUL.md` HIERARCHY section. After creation, run `diff <(python3 -c "render and print") agents/pumplai_pm/agent/SOUL.md` to confirm zero diff before marking the phase complete.

**Warning signs:** Golden baseline test reports diff lines in the HIERARCHY section.

### Pitfall 5: Variable name collision with markdown content

**What goes wrong:** Template content contains patterns like `$HOME`, `$USER`, or other shell-like `$identifier` strings that are not intended as template variables. `safe_substitute()` replaces them if they appear in the variables dict.

**Why it happens:** SOUL files could reference environment paths or shell variables in prose.

**How to avoid:** Use `safe_substitute()` (not `substitute()`), and keep the variable dict small and explicit. Do not pass `os.environ` or any broad dict. The golden file analysis shows no unintended `$` patterns.

**Warning signs:** Rendered output has unexpected substitutions in path strings.

## Code Examples

### Full renderer skeleton

```python
# orchestration/soul_renderer.py
import json
import string
from pathlib import Path
from typing import Optional

# Re-use existing project_config helpers
from orchestration.project_config import load_project_config, _find_project_root


def build_variables(project_config: dict) -> dict:
    """Map project.json fields to template variable names."""
    tech_stack = project_config.get("tech_stack", {})
    return {
        "project_name": project_config.get("name", project_config.get("id", "")),
        "project_id": project_config.get("id", ""),
        "agent_name": _derive_agent_name(project_config),
        "tier": "L2",
        "tech_stack_frontend": tech_stack.get("frontend", ""),
        "tech_stack_backend": tech_stack.get("backend", ""),
        "tech_stack_infra": tech_stack.get("infra", ""),
        "workspace": _derive_openclaw_workspace(),
    }


def _derive_openclaw_workspace() -> str:
    """Return the OpenClaw runtime workspace path."""
    return str(_find_project_root() / "workspace")


def _derive_agent_name(project_config: dict) -> str:
    """Derive the agent name for the title line."""
    # Use agents.l2_pm agent ID from config, formatted to title case
    # e.g., "pumplai_pm" -> "PumplAI_PM" requires override; default: capitalize
    return project_config.get("name", project_config.get("id", "")).replace("_", " ").title()


def parse_sections(text: str):
    """Parse markdown into ({name: section_text}, [ordered_names])."""
    sections = {}
    order = []
    current_key = None
    current_lines = []

    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            if current_key is not None:
                sections[current_key] = "".join(current_lines)
            current_key = line[3:].strip()
            order.append(current_key)
            current_lines = [line]
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "".join(current_lines)

    return sections, order


def merge_sections(default_sections, default_order, override_sections, override_order):
    """Merge override into default sections; append novel override sections."""
    merged = {**default_sections}
    merged.update(override_sections)

    result_order = default_order.copy()
    for key in override_order:
        if key not in result_order:
            result_order.append(key)

    parts = []
    for key in result_order:
        if key in merged:
            parts.append(merged[key].rstrip("\n"))
    return "\n\n".join(parts) + "\n"


def render_soul(project_id: str) -> str:
    """Render a SOUL.md string for the given project."""
    root = _find_project_root()
    config = load_project_config(project_id)
    variables = build_variables(config)

    # Load default template
    template_path = root / "agents" / "_templates" / "soul-default.md"
    default_text = string.Template(template_path.read_text()).safe_substitute(variables)
    default_sections, default_order = parse_sections(default_text)

    # Load override if present
    override_path = root / "projects" / project_id / "soul-override.md"
    override_sections, override_order = {}, []
    if override_path.exists():
        override_text = string.Template(override_path.read_text()).safe_substitute(variables)
        override_sections, override_order = parse_sections(override_text)

    # Build title line
    title = string.Template("# Soul: $agent_name ($tier)").safe_substitute(variables)
    body = merge_sections(default_sections, default_order, override_sections, override_order)
    return title + "\n\n" + body
```

### Default template content (soul-default.md)

```markdown
## HIERARCHY
- **Superior:** Reports to the L1 Strategic Orchestrator. All major project decisions must align with L1 strategic plans.
- **Subordinates:** Supervises L3 Worker containers.
- **Scope:** Primary authority over the `$workspace` workspace.

## CORE GOVERNANCE
1. **TACTICAL TRANSLATION:** Receive L1 goals and break them down into multi-step worker tasks.
2. **STRICT TECH STACK:**
   - **Frontend:** $tech_stack_frontend.
   - **Backend:** $tech_stack_backend.
   - **Infrastructure:** $tech_stack_infra.
3. **QUALITY GATE:** Review and verify all L3 output before reporting completion to L1.

## BEHAVIORAL PROTOCOLS
- **Resourceful Execution:** Use available tools to explore the workspace and validate implementations.
- **Contextual Integrity:** Ensure all changes are documented in the project's local memory or `MEMORY.md`.
- **Escalation:** If a task violates strategic vision or hits a major architectural blocker, escalate to L1.
```

**Note:** The title line (`# Soul: ...`) is NOT in the template file — it is generated by the renderer from `$agent_name` and `$tier` variables and prepended.

### PumplAI soul-override.md content

```markdown
## HIERARCHY
- **Superior:** Reports to **ClawdiaPrime (L1)**. All major project decisions must align with L1 strategic plans.
- **Subordinates:** Supervises **nextjs_pm** and **python_backend_worker** (L3 Workers).
- **Scope:** Primary authority over the `/home/ollie/.openclaw/workspace` workspace.
```

**Note:** This override replaces only the HIERARCHY section. CORE GOVERNANCE and BEHAVIORAL PROTOCOLS come from the default template with variable substitution applied. The specific workspace path `/home/ollie/.openclaw/workspace` is hardcoded in the override (not sourced from `project.json.workspace`) because the two paths differ — see Pitfall 1.

Alternatively, the override can use `$workspace` if the renderer maps `$workspace` to `_find_project_root() / "workspace"`, making it portable across machines.

### Golden baseline verification script

```python
# Usage: python3 scripts/verify_soul_golden.py
import sys
from pathlib import Path
import difflib

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestration.soul_renderer import render_soul

golden_path = Path("agents/pumplai_pm/agent/SOUL.md")
golden = golden_path.read_text()
rendered = render_soul("pumplai")

if golden == rendered:
    print("PASS: golden baseline diff is empty")
    sys.exit(0)
else:
    diff = list(difflib.unified_diff(
        golden.splitlines(keepends=True),
        rendered.splitlines(keepends=True),
        fromfile="golden",
        tofile="rendered",
    ))
    print("FAIL: non-empty diff:")
    print("".join(diff))
    sys.exit(1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded SOUL.md per agent | Template + override with variable substitution | Phase 12 (this phase) | New projects get identity at init time without manually writing SOUL.md |
| PumplAI-specific SOUL.md | Generic default template + PumplAI override | Phase 12 | Same rendered output for PumplAI; generic default for new projects |

**Deprecated/outdated:**
- Hardcoded `agents/pumplai_pm/agent/SOUL.md`: Remains as the golden baseline reference but is now generated by the renderer (not manually maintained going forward).

## Open Questions

1. **Agent name derivation for the title line**
   - What we know: title must be `# Soul: PumplAI_PM (L2)` for golden baseline
   - What's unclear: `project.json.name` is "PumplAI" (no underscore, no `_PM` suffix); `config.json.name` is "PumplAI_PM - Domain Project Manager" (too long); no clean field maps to "PumplAI_PM"
   - Recommendation: Add an `agent_name` field to `project.json` (or derive it as `{project_id}_pm` → "pumplai_pm" → format as "PumplAI_PM"). Simplest approach: the soul-override.md receives `$agent_name` as a variable but the title line is auto-generated by the renderer using the L2 agent ID from `project.json.agents.l2_pm` field ("pumplai_pm") formatted to title case. The title would be `# Soul: pumplai_pm (L2)` from the default path — which won't match the golden. **Resolution:** Add an explicit `agent_display_name` field to `project.json` for the pumplai project (`"PumplAI_PM"`), OR accept that the title line for the golden baseline is reproduced by having `agent_name` as a variable set in the override/project config. This is Claude's discretion to resolve in planning.

2. **Renderer write target: where does rendered SOUL.md go?**
   - What we know: golden baseline is at `agents/pumplai_pm/agent/SOUL.md`; the phase goal says "rendered output" but doesn't specify write location
   - What's unclear: Does `render_soul()` write a file, or return a string? Who calls it to write?
   - Recommendation: `render_soul()` returns a string. A separate `write_soul(project_id, output_path)` or CLI option handles file writing. For Phase 12, writing to `agents/<l2_pm_id>/agent/SOUL.md` makes sense as the canonical output path; Phase 14 (project init CLI) will call the renderer to write on `openclaw project init`.

3. **Handling of `$tech_stack_infra` variable name**
   - What we know: `project.json` tech_stack field is `"infra"`, variable name would be `tech_stack_infra`
   - What's unclear: The requirement text says `$tech_stack_*` — is `infra` the right suffix vs `infrastructure`?
   - Recommendation: Use `tech_stack_infra` to match the `project.json` key exactly. Simpler and consistent.

## Sources

### Primary (HIGH confidence)
- Python stdlib `string` module — `string.Template`, `safe_substitute()`, `$$` escape, identifier regex `[_a-z][_a-z0-9]*` (case-insensitive) verified by live testing in this session
- `/home/ollie/.openclaw/agents/pumplai_pm/agent/SOUL.md` — golden baseline content verified by reading file
- `/home/ollie/.openclaw/projects/pumplai/project.json` — variable source verified: tech_stack.frontend, tech_stack.backend, tech_stack.infra confirmed
- `/home/ollie/.openclaw/.planning/STATE.md` — locked technology decision: `string.Template.safe_substitute()` confirmed
- `/home/ollie/.openclaw/.planning/phases/12-soul-templating/12-CONTEXT.md` — all locked decisions and override mechanics

### Secondary (MEDIUM confidence)
- Live prototype testing in this research session: section parser, variable substitution, golden baseline reconstruction all validated in Python 3 interpreter

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, locked decision from STATE.md, live-tested
- Architecture: HIGH — section parser and merge algorithm prototyped and verified in session
- Pitfalls: HIGH — workspace path mismatch discovered by direct comparison of `project.json.workspace` vs golden `SOUL.md` content; trailing newline verified against actual file content

**Research date:** 2026-02-23
**Valid until:** 2026-04-23 (stable domain — Python stdlib; no external dependencies)
