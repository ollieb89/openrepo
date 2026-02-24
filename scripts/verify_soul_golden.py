#!/usr/bin/env python3
"""
Golden baseline verification script for SOUL renderer.

Verifies that:
1. PumplAI SOUL.md matches the golden baseline byte-for-byte
2. New projects without overrides get complete SOUL from defaults
"""

import difflib
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.soul_renderer import render_soul, build_variables
from openclaw.project_config import load_project_config


def verify_pumplai_golden() -> bool:
    """Verify PumplAI rendered SOUL matches golden baseline."""
    golden_path = Path("agents/pumplai_pm/agent/SOUL.md")
    golden = golden_path.read_text()
    rendered = render_soul("pumplai")

    if golden == rendered:
        print("PASS: golden baseline diff is empty")
        return True
    else:
        diff = list(difflib.unified_diff(
            golden.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile="golden",
            tofile="rendered",
        ))
        print("FAIL: golden baseline mismatch")
        print("".join(diff))
        return False


def verify_new_project_without_override() -> bool:
    """Verify new projects without override get complete SOUL from defaults."""
    # Create a minimal test project config (no override file)
    test_config = {
        "id": "test_new_project",
        "name": "Test New Project",
        "agent_display_name": "TestPM",
        "tech_stack": {
            "frontend": "React, TypeScript",
            "backend": "Python, FastAPI",
            "infra": "Docker, AWS"
        },
        "agents": {
            "l2_pm": "test_pm"
        }
    }

    # Build variables as render_soul would
    variables = build_variables(test_config)

    # Import render internals to test without file I/O
    import string
    from openclaw.soul_renderer import parse_sections, merge_sections, _find_project_root

    # Load and substitute default template
    template_path = _find_project_root() / "agents" / "_templates" / "soul-default.md"
    default_text = string.Template(template_path.read_text()).safe_substitute(variables)
    default_sections, default_order = parse_sections(default_text)

    # No override file - should use defaults only
    title = string.Template("# Soul: $agent_name ($tier)").safe_substitute(variables)
    body = merge_sections(default_sections, default_order, {}, [])
    result = (title + "\n\n" + body).rstrip("\n") + "\n"

    # Verify result
    checks = [
        ("# Soul: TestPM (L2)" in result, "Title line correct"),
        ("## HIERARCHY" in result, "Has HIERARCHY section"),
        ("## CORE GOVERNANCE" in result, "Has CORE GOVERNANCE section"),
        ("## BEHAVIORAL PROTOCOLS" in result, "Has BEHAVIORAL PROTOCOLS section"),
        ("React, TypeScript" in result, "Frontend tech stack substituted"),
        ("Python, FastAPI" in result, "Backend tech stack substituted"),
        ("Docker, AWS" in result, "Infra tech stack substituted"),
        ("$project_name" not in result, "No unresolved variables"),
        ("$tech_stack" not in result, "No unresolved tech_stack variables"),
    ]

    all_passed = True
    for check, description in checks:
        if check:
            print(f"  PASS: {description}")
        else:
            print(f"  FAIL: {description}")
            all_passed = False

    if all_passed:
        print("PASS: new-project-without-override scenario works")
    else:
        print("FAIL: new-project-without-override scenario failed")

    return all_passed


def main() -> int:
    """Run all verifications."""
    print("=== PumplAI Golden Baseline Verification ===")
    pumplai_ok = verify_pumplai_golden()
    print()

    print("=== New Project Without Override Verification ===")
    new_project_ok = verify_new_project_without_override()
    print()

    if pumplai_ok and new_project_ok:
        print("All verifications passed!")
        return 0
    else:
        print("Some verifications failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
