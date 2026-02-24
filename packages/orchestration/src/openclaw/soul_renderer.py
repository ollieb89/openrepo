"""
SOUL Renderer Module

Generates L2 agent identity files (SOUL.md) from a default template
with variable substitution and per-project section-level overrides.
"""

import argparse
import string
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .project_config import load_project_config, _find_project_root


def parse_sections(text: str) -> Tuple[Dict[str, str], List[str]]:
    """
    Parse markdown into {section_name: section_text} dict and ordered list of names.
    
    Section text includes the ## header line and all content until the next ## header.
    Title line (# ...) is excluded — handled separately by the renderer.
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


def merge_sections(
    default_sections: Dict[str, str],
    default_order: List[str],
    override_sections: Dict[str, str],
    override_order: List[str]
) -> str:
    """
    Merge override sections into default sections.
    
    - Sections in override replace corresponding default sections
    - Sections in override not in default are appended at end
    - Sections in default not in override are kept unchanged
    - Result is normalized with exactly one trailing newline
    """
    # Start with all defaults, override replaces matching keys
    merged = {**default_sections}
    merged.update(override_sections)

    # Reconstruct in default order, then append novel override sections
    result_order = default_order.copy()
    for key in override_order:
        if key not in result_order:
            result_order.append(key)

    # Build body with normalized whitespace
    parts = []
    for key in result_order:
        if key in merged:
            parts.append(merged[key].rstrip("\n"))
    
    return "\n\n".join(parts) + "\n"


def build_variables(project_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Map project.json fields to template variable names.
    
    Variables:
    - project_name: from config["name"], fallback to config["id"]
    - project_id: from config["id"]
    - agent_name: from config["agent_display_name"], fallback to l2_pm agent ID
    - tier: hardcoded "L2"
    - tech_stack_*: from config["tech_stack"]
    - workspace: OpenClaw runtime workspace path (_find_project_root() / "workspace")
    """
    tech_stack = project_config.get("tech_stack", {})
    
    # Derive agent name: explicit display name or fallback to l2_pm agent ID
    agent_name = project_config.get("agent_display_name")
    if not agent_name:
        agents = project_config.get("agents", {})
        agent_name = agents.get("l2_pm", "")
    
    return {
        # project_name: consumed in soul-default.md HIERARCHY section (CFG-04)
        "project_name": project_config.get("name", project_config.get("id", "")),
        # project_id: available for override files; not consumed by soul-default.md
        "project_id": project_config.get("id", ""),
        # agent_name and tier: consumed in title line by render_soul() directly
        "agent_name": agent_name,
        "tier": "L2",
        # tech_stack_*: consumed in soul-default.md CORE GOVERNANCE section
        "tech_stack_frontend": tech_stack.get("frontend", ""),
        "tech_stack_backend": tech_stack.get("backend", ""),
        "tech_stack_infra": tech_stack.get("infra", ""),
        # workspace: consumed in soul-default.md HIERARCHY section
        "workspace": project_config.get("workspace", str(_find_project_root() / "workspace")),
    }


def render_soul(project_id: str) -> str:
    """
    Render a SOUL.md string for the given project.
    
    Process:
    1. Load project config
    2. Build substitution variables
    3. Load default template, apply variable substitution
    4. Parse default into sections
    5. If soul-override.md exists, load and substitute, parse into sections
    6. Merge override sections into default sections
    7. Generate title line from variables
    8. Return complete SOUL.md content normalized with single trailing newline
    """
    root = _find_project_root()
    config = load_project_config(project_id)
    variables = build_variables(config)

    # Load and substitute default template
    template_path = root / "agents" / "_templates" / "soul-default.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Default template not found: {template_path}")
    
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
    
    # Merge sections and build body
    body = merge_sections(default_sections, default_order, override_sections, override_order)
    
    # Combine with normalized trailing newline
    result = (title + "\n\n" + body).rstrip("\n") + "\n"
    return result


def write_soul(project_id: str, output_path: Optional[Path] = None, skip_if_exists: bool = False) -> Optional[Path]:
    """
    Render SOUL.md and write it to disk.

    If output_path is None, derive the default output path from the project config:
    agents/<l2_pm_id>/agent/SOUL.md (using config["agents"]["l2_pm"]).

    Creates parent directories if needed.

    Args:
        project_id: The project ID to render SOUL for.
        output_path: Custom output path. If None, derived from project config.
        skip_if_exists: If True and the output file already exists, return None
                        without writing. Use --force in CLI to override.

    Returns:
        Path: The path written to, or None if skip_if_exists=True and file exists.
    """
    config = load_project_config(project_id)

    # Determine output path
    if output_path is None:
        agents = config.get("agents", {})
        l2_pm_id = agents.get("l2_pm", project_id)
        output_path = _find_project_root() / "agents" / l2_pm_id / "agent" / "SOUL.md"

    # Skip if file already exists and skip_if_exists requested
    if skip_if_exists and output_path.exists():
        return None

    # Render content
    content = render_soul(project_id)

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    output_path.write_text(content)

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render SOUL.md for a project")
    parser.add_argument("--project", required=True, help="Project ID to render SOUL for")
    parser.add_argument("--write", action="store_true", help="Write the rendered SOUL.md to the agent directory")
    parser.add_argument("--output", type=Path, help="Custom output path (only used with --write)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing SOUL.md (default: skip if exists)")

    args = parser.parse_args()

    if args.write:
        output_path = write_soul(args.project, args.output, skip_if_exists=not args.force)
        if output_path is not None:
            print(f"Written to: {output_path}", file=sys.stderr)
        else:
            print(f"SOUL.md already exists. Use --force to overwrite.", file=sys.stderr)
    else:
        # Print to stdout
        print(render_soul(args.project), end="")
