#!/usr/bin/env python3
"""
Phase 16 Integration Fixes Verification Script.

Verifies that all 3 integration fixes and the deprecated constant removal
from Phase 16 Plan 01 are correctly implemented:

- CFG-02: project_id threading through snapshot functions
- CFG-06: staging branch detection delegates to _detect_default_branch
- CFG-04: $project_name consumed in soul-default.md
- Deprecated constant removal from orchestration/config.py
"""

import inspect
import string
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def verify_snapshot_project_id_threading() -> bool:
    """
    Verify that capture_semantic_snapshot and cleanup_old_snapshots
    require an explicit project_id parameter with no default.

    Checks:
    - Both functions have project_id parameter
    - project_id has no default value (inspect._empty)
    - Both function bodies contain get_snapshot_dir(project_id)
    """
    from openclaw.snapshot import capture_semantic_snapshot, cleanup_old_snapshots

    ok = True

    # Check capture_semantic_snapshot
    sig = inspect.signature(capture_semantic_snapshot)
    if "project_id" not in sig.parameters:
        print("[FAIL] snapshot project_id threading — capture_semantic_snapshot missing project_id param")
        ok = False
    elif sig.parameters["project_id"].default is not inspect.Parameter.empty:
        print("[FAIL] snapshot project_id threading — capture_semantic_snapshot.project_id has a default (should be required)")
        ok = False

    # Check cleanup_old_snapshots
    sig2 = inspect.signature(cleanup_old_snapshots)
    if "project_id" not in sig2.parameters:
        print("[FAIL] snapshot project_id threading — cleanup_old_snapshots missing project_id param")
        ok = False
    elif sig2.parameters["project_id"].default is not inspect.Parameter.empty:
        print("[FAIL] snapshot project_id threading — cleanup_old_snapshots.project_id has a default (should be required)")
        ok = False

    # Check source contains get_snapshot_dir(project_id) (not bare call)
    capture_src = inspect.getsource(capture_semantic_snapshot)
    if "get_snapshot_dir(project_id)" not in capture_src:
        print("[FAIL] snapshot project_id threading — capture_semantic_snapshot body does not call get_snapshot_dir(project_id)")
        ok = False

    cleanup_src = inspect.getsource(cleanup_old_snapshots)
    if "get_snapshot_dir(project_id)" not in cleanup_src:
        print("[FAIL] snapshot project_id threading — cleanup_old_snapshots body does not call get_snapshot_dir(project_id)")
        ok = False

    if ok:
        print("[PASS] snapshot project_id threading — capture_semantic_snapshot and cleanup_old_snapshots require explicit project_id")
    return ok


def verify_staging_branch_delegates_to_detect() -> bool:
    """
    Verify that create_staging_branch delegates to _detect_default_branch
    rather than containing an inline symbolic-ref block.

    Checks:
    - Source contains _detect_default_branch
    - Source does NOT contain symbolic-ref (no inline duplication)
    """
    from openclaw.snapshot import create_staging_branch

    src = inspect.getsource(create_staging_branch)
    ok = True

    if "_detect_default_branch" not in src:
        print("[FAIL] staging branch detection delegation — create_staging_branch does not call _detect_default_branch")
        ok = False

    if "symbolic-ref" in src:
        print("[FAIL] staging branch detection delegation — create_staging_branch contains inline symbolic-ref (should delegate instead)")
        ok = False

    if ok:
        print("[PASS] staging branch detection delegation — create_staging_branch delegates to _detect_default_branch")
    return ok


def verify_template_variable_consumption() -> bool:
    """
    Verify that soul-default.md contains $project_name and that
    string.Template.safe_substitute() correctly resolves it.

    Checks:
    - $project_name appears in the raw template
    - Rendered output contains the substituted test value
    - No unresolved $project_name remains in rendered output
    """
    from openclaw.soul_renderer import _find_project_root

    root = _find_project_root()
    template_path = root / "agents" / "_templates" / "soul-default.md"

    ok = True

    if not template_path.exists():
        print(f"[FAIL] template variable consumption — template not found: {template_path}")
        return False

    raw = template_path.read_text()

    if "$project_name" not in raw:
        print("[FAIL] template variable consumption — $project_name not found in soul-default.md")
        ok = False

    # Render with test values
    test_values = {
        "project_name": "TestProject_XYZ",
        "project_id": "test_xyz",
        "agent_name": "TestPM",
        "tier": "L2",
        "tech_stack_frontend": "React",
        "tech_stack_backend": "Python",
        "tech_stack_infra": "Docker",
        "workspace": "/test/workspace",
    }
    rendered = string.Template(raw).safe_substitute(test_values)

    if "TestProject_XYZ" not in rendered:
        print("[FAIL] template variable consumption — rendered output does not contain substituted project_name value")
        ok = False

    if "$project_name" in rendered:
        print("[FAIL] template variable consumption — unresolved $project_name remains in rendered output")
        ok = False

    if ok:
        print("[PASS] template variable consumption — $project_name found in soul-default.md and correctly substituted")
    return ok


def verify_deprecated_constants_removed() -> bool:
    """
    Verify that STATE_FILE and SNAPSHOT_DIR have been removed from
    orchestration/config.py, while LOCK_TIMEOUT and POLL_INTERVAL remain.
    Also confirms that import os and from pathlib lines are absent.

    Checks:
    - hasattr(config, 'STATE_FILE') is False
    - hasattr(config, 'SNAPSHOT_DIR') is False
    - hasattr(config, 'LOCK_TIMEOUT') is True
    - hasattr(config, 'POLL_INTERVAL') is True
    - config.py source has no 'import os' or 'from pathlib' lines
    """
    import openclaw.config as config

    ok = True

    if hasattr(config, "STATE_FILE"):
        print("[FAIL] deprecated constants removed — STATE_FILE still present in orchestration/config.py")
        ok = False

    if hasattr(config, "SNAPSHOT_DIR"):
        print("[FAIL] deprecated constants removed — SNAPSHOT_DIR still present in orchestration/config.py")
        ok = False

    if not hasattr(config, "LOCK_TIMEOUT"):
        print("[FAIL] deprecated constants removed — LOCK_TIMEOUT was over-deleted from orchestration/config.py")
        ok = False

    if not hasattr(config, "POLL_INTERVAL"):
        print("[FAIL] deprecated constants removed — POLL_INTERVAL was over-deleted from orchestration/config.py")
        ok = False

    # Check source for removed imports
    config_path = Path(__file__).parent.parent / "orchestration" / "config.py"
    config_src = config_path.read_text()

    if "import os" in config_src:
        print("[FAIL] deprecated constants removed — 'import os' still present in orchestration/config.py")
        ok = False

    if "from pathlib" in config_src:
        print("[FAIL] deprecated constants removed — 'from pathlib' still present in orchestration/config.py")
        ok = False

    if ok:
        print("[PASS] deprecated constants removed — STATE_FILE and SNAPSHOT_DIR absent; LOCK_TIMEOUT and POLL_INTERVAL retained; no dead imports")
    return ok


def main() -> int:
    """Run all Phase 16 integration fix verifications."""
    print("=== Phase 16 Integration Fixes Verification ===")
    print()

    results = [
        verify_snapshot_project_id_threading(),
        verify_staging_branch_delegates_to_detect(),
        verify_template_variable_consumption(),
        verify_deprecated_constants_removed(),
    ]

    print()
    if all(results):
        print("All 4 checks passed.")
        return 0
    else:
        failed = sum(1 for r in results if not r)
        print(f"{failed} check(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
