#!/usr/bin/env python3
"""
Phase 13: Multi-Project Runtime Verification

Verifies all 6 MPR requirements plus the entrypoint guard via static code
inspection. No Docker required — tests validate the code structure.

Usage:
    python3 scripts/verify_phase13.py

Exit code 0 if all checks pass, 1 if any fail.
"""

import re
import sys
from pathlib import Path

# Project root relative to this script
ROOT = Path(__file__).parent.parent


def check(label: str, condition: bool) -> bool:
    """Print PASS/FAIL for a check and return the result."""
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


def verify_mpr01() -> bool:
    """MPR-01: spawn.py adds openclaw.project label."""
    src = (ROOT / "skills" / "spawn_specialist" / "spawn.py").read_text()
    return check(
        "MPR-01: openclaw.project label in spawn.py",
        '"openclaw.project"' in src,
    )


def verify_mpr02() -> bool:
    """MPR-02: Container names prefixed with project ID."""
    src = (ROOT / "skills" / "spawn_specialist" / "spawn.py").read_text()
    # Pattern: openclaw-{something with project}-l3-{task}
    pattern_found = bool(re.search(r'openclaw-.*project.*-l3-', src))
    return check(
        "MPR-02: Namespaced container name pattern (openclaw-{project}-l3-{task})",
        pattern_found,
    )


def verify_mpr03() -> bool:
    """MPR-03: pool.py resolves state file per-project."""
    sys.path.insert(0, str(ROOT))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pool", ROOT / "skills" / "spawn_specialist" / "pool.py"
        )
        # Read source only (no import — avoids docker dependency)
        src = (ROOT / "skills" / "spawn_specialist" / "pool.py").read_text()

        # L3ContainerPool.__init__ must have project_id param
        has_project_id_in_init = bool(
            re.search(r'def __init__\s*\(.*project_id', src)
        )

        # State file must be resolved via get_state_path(self.project_id)
        has_per_project_state = "get_state_path(self.project_id)" in src

        # PoolRegistry class must exist with get_pool method
        has_pool_registry = "class PoolRegistry" in src
        has_get_pool = "def get_pool" in src

        result = (
            has_project_id_in_init
            and has_per_project_state
            and has_pool_registry
            and has_get_pool
        )
        return check(
            "MPR-03: pool.py resolves state file per-project (project_id in __init__, "
            "get_state_path(self.project_id), PoolRegistry.get_pool)",
            result,
        )
    except Exception as e:
        print(f"  ERROR: {e}")
        return check("MPR-03: pool.py per-project state resolution", False)


def verify_mpr04() -> bool:
    """MPR-04: monitor.py accepts --project flag."""
    src = (ROOT / "orchestration" / "monitor.py").read_text()

    has_project_arg = "'--project'" in src or '"--project"' in src
    has_discover_fn = "_discover_projects" in src
    has_project_column = "PROJECT" in src

    result = has_project_arg and has_discover_fn and has_project_column
    return check(
        "MPR-04: monitor.py --project flag, _discover_projects(), PROJECT column header",
        result,
    )


def verify_mpr05() -> bool:
    """MPR-05: spawn.py injects OPENCLAW_PROJECT env var."""
    src = (ROOT / "skills" / "spawn_specialist" / "spawn.py").read_text()
    return check(
        "MPR-05: OPENCLAW_PROJECT env var injected in spawn.py",
        '"OPENCLAW_PROJECT"' in src,
    )


def verify_mpr06() -> bool:
    """MPR-06: active_project resolution is env-var-first."""
    src = (ROOT / "skills" / "spawn_specialist" / "spawn.py").read_text()

    # spawn_l3_specialist must have project_id with default None
    has_project_id_param = bool(
        re.search(r'def spawn_l3_specialist\s*\([^)]*project_id\s*[=:][^,)]*None', src)
    )

    # _validate_project_id must be called in function body
    has_validate_call = "_validate_project_id" in src

    # get_active_project_id must be used as fallback (appears in source)
    has_active_project_fallback = "get_active_project_id" in src

    result = has_project_id_param and has_validate_call and has_active_project_fallback
    return check(
        "MPR-06: spawn_l3_specialist has project_id=None, _validate_project_id called, "
        "get_active_project_id as fallback",
        result,
    )


def verify_entrypoint_guard() -> bool:
    """Bonus: entrypoint.sh has OPENCLAW_PROJECT guard."""
    entrypoint = ROOT / "docker" / "l3-specialist" / "entrypoint.sh"
    if not entrypoint.exists():
        return check("Bonus: entrypoint.sh OPENCLAW_PROJECT guard", False)
    src = entrypoint.read_text()
    return check(
        "Bonus: entrypoint.sh references OPENCLAW_PROJECT",
        "OPENCLAW_PROJECT" in src,
    )


def main() -> int:
    """Run all Phase 13 MPR verifications."""
    print("Phase 13: Multi-Project Runtime Verification")
    print("=" * 45)

    results = [
        verify_mpr01(),
        verify_mpr02(),
        verify_mpr03(),
        verify_mpr04(),
        verify_mpr05(),
        verify_mpr06(),
        verify_entrypoint_guard(),
    ]

    passed = sum(results)
    total = len(results)

    print("=" * 45)
    print(f"Result: {passed}/{total} checks passed")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
