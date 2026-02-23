#!/usr/bin/env python3
"""
Phase 14: Project CLI Verification

Verifies all 6 CLI requirements (CLI-01 through CLI-06) via subprocess calls
to orchestration/project_cli.py. Non-destructive: saves the original active_project,
creates temporary test projects, verifies behavior, and restores original state on exit.

Usage:
    python3 scripts/verify_phase14.py

Exit code 0 if all checks pass, 1 if any fail.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Project root relative to this script
ROOT = Path(__file__).parent.parent

# CLI entry point
CLI = str(ROOT / "orchestration" / "project_cli.py")

# Temporary test project IDs (all prefixed with verify14 for easy cleanup)
TEST_PROJECTS = ["verify14test", "verify14switch", "verify14tmpl", "verify14rm"]


def check(label: str, condition: bool) -> bool:
    """Print PASS/FAIL for a check and return the result."""
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


def run_cli(*args: str, capture: bool = True) -> subprocess.CompletedProcess:
    """Run project_cli.py with the given arguments, returning the completed process."""
    cmd = [sys.executable, CLI, *args]
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=str(ROOT),
    )


def get_active_project() -> str:
    """Read active_project from openclaw.json."""
    config_path = ROOT / "openclaw.json"
    with open(config_path) as f:
        data = json.load(f)
    return data.get("active_project", "")


def cleanup_test_projects() -> None:
    """Remove all verify14* project directories (best-effort)."""
    for pid in TEST_PROJECTS:
        project_dir = ROOT / "projects" / pid
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI-01: init creates project.json from flags
# ---------------------------------------------------------------------------

def verify_cli_01() -> bool:
    """CLI-01: init creates project.json from --id and --name flags."""
    pid = "verify14test"
    project_dir = ROOT / "projects" / pid

    # Clean up any leftover from a previous run
    if project_dir.exists():
        shutil.rmtree(project_dir)

    result = run_cli("init", "--id", pid, "--name", "Verify Test", "--force")
    if result.returncode != 0:
        print(f"  ERROR: init exited {result.returncode}: {result.stderr.strip()}")
        return check("CLI-01: init creates project.json from flags", False)

    manifest_path = project_dir / "project.json"
    if not manifest_path.exists():
        return check("CLI-01: project.json exists after init", False)

    # Validate JSON
    try:
        with open(manifest_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ERROR: project.json is not valid JSON: {e}")
        return check("CLI-01: project.json is valid JSON", False)

    # Check required fields
    required_fields = ["id", "name", "agent_display_name", "workspace", "tech_stack", "agents", "l3_overrides"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        print(f"  ERROR: project.json missing fields: {missing}")
        return check("CLI-01: project.json has all required fields", False)

    # Verify id and name match what we passed
    id_ok = data["id"] == pid
    name_ok = data["name"] == "Verify Test"

    result = id_ok and name_ok
    if not id_ok:
        print(f"  ERROR: id mismatch — expected '{pid}', got '{data['id']}'")
    if not name_ok:
        print(f"  ERROR: name mismatch — expected 'Verify Test', got '{data['name']}'")

    return check(
        "CLI-01: init creates project.json from flags (id, name, required fields present)",
        result,
    )


# ---------------------------------------------------------------------------
# CLI-02: list shows projects
# ---------------------------------------------------------------------------

def verify_cli_02() -> bool:
    """CLI-02: list shows existing projects with active marker."""
    result = run_cli("list")
    if result.returncode != 0:
        print(f"  ERROR: list exited {result.returncode}: {result.stderr.strip()}")
        return check("CLI-02: list shows projects", False)

    output = result.stdout

    has_pumplai = "pumplai" in output
    has_geriai = "geriai" in output
    # Active marker: exactly one line should have a trailing '*'
    active_lines = [line for line in output.splitlines() if line.rstrip().endswith("*")]
    has_active_marker = len(active_lines) >= 1

    if not has_pumplai:
        print("  ERROR: 'pumplai' not found in list output")
    if not has_geriai:
        print("  ERROR: 'geriai' not found in list output")
    if not has_active_marker:
        print("  ERROR: no active marker (*) found in list output")

    result_ok = has_pumplai and has_geriai and has_active_marker
    return check(
        "CLI-02: list shows pumplai and geriai with active (*) marker",
        result_ok,
    )


# ---------------------------------------------------------------------------
# CLI-03: switch updates active_project
# ---------------------------------------------------------------------------

def verify_cli_03() -> bool:
    """CLI-03: switch updates active_project in openclaw.json."""
    pid = "verify14switch"
    project_dir = ROOT / "projects" / pid

    # Save current active project (restored in finally block of main)
    if project_dir.exists():
        shutil.rmtree(project_dir)

    # Create test project
    r = run_cli("init", "--id", pid, "--name", "Switch Test", "--force")
    if r.returncode != 0:
        print(f"  ERROR: init failed: {r.stderr.strip()}")
        return check("CLI-03: switch updates active_project", False)

    # Switch to test project
    r = run_cli("switch", pid)
    if r.returncode != 0:
        print(f"  ERROR: switch failed: {r.stderr.strip()}")
        return check("CLI-03: switch updates active_project", False)

    # Verify openclaw.json was updated
    active = get_active_project()
    switched_ok = active == pid
    if not switched_ok:
        print(f"  ERROR: active_project == '{active}', expected '{pid}'")

    return check(
        "CLI-03: switch updates active_project in openclaw.json",
        switched_ok,
    )


# ---------------------------------------------------------------------------
# CLI-04: remove deletes project dir, blocks active removal
# ---------------------------------------------------------------------------

def verify_cli_04(original_active: str) -> bool:
    """CLI-04: remove deletes project dir and blocks active project removal."""
    pid = "verify14rm"
    project_dir = ROOT / "projects" / pid

    if project_dir.exists():
        shutil.rmtree(project_dir)

    # Create test project
    r = run_cli("init", "--id", pid, "--name", "Remove Test", "--force")
    if r.returncode != 0:
        print(f"  ERROR: init failed: {r.stderr.strip()}")
        return check("CLI-04: remove deletes project dir, blocks active removal", False)

    # Ensure verify14rm is not active — switch to a safe project
    # Switch to pumplai (known to exist) first so we can safely remove verify14rm
    r = run_cli("switch", "pumplai")
    if r.returncode != 0:
        print(f"  ERROR: could not switch away from verify14rm: {r.stderr.strip()}")
        return check("CLI-04: remove deletes project dir, blocks active removal", False)

    # Remove the test project
    r = run_cli("remove", pid, "--force")
    if r.returncode != 0:
        print(f"  ERROR: remove failed: {r.stderr.strip()}")
        return check("CLI-04: remove deletes project dir", False)

    dir_deleted = not project_dir.exists()
    if not dir_deleted:
        print(f"  ERROR: {project_dir} still exists after remove")

    # Test guard: try to remove the currently active project (pumplai)
    r = run_cli("remove", "pumplai", "--force")
    guard_blocked = r.returncode != 0
    if not guard_blocked:
        print("  ERROR: remove of active project should have been blocked (exit != 0)")
        # Note: if this somehow passed, pumplai is now gone — critical failure

    result_ok = dir_deleted and guard_blocked
    return check(
        "CLI-04: remove deletes project dir and blocks active project removal",
        result_ok,
    )


# ---------------------------------------------------------------------------
# CLI-05: init --template applies preset values
# ---------------------------------------------------------------------------

def verify_cli_05() -> bool:
    """CLI-05: init --template merges tech_stack preset values."""
    pid = "verify14tmpl"
    project_dir = ROOT / "projects" / pid

    if project_dir.exists():
        shutil.rmtree(project_dir)

    r = run_cli("init", "--id", pid, "--name", "Template Test", "--template", "fullstack", "--force")
    if r.returncode != 0:
        print(f"  ERROR: init --template failed: {r.stderr.strip()}")
        return check("CLI-05: init --template applies preset values", False)

    manifest_path = project_dir / "project.json"
    try:
        with open(manifest_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ERROR: cannot read project.json: {e}")
        return check("CLI-05: init --template applies preset values", False)

    tech_stack = data.get("tech_stack", {})
    frontend_ok = bool(tech_stack.get("frontend"))
    backend_ok = bool(tech_stack.get("backend"))

    # fullstack template should contain Next.js
    frontend_has_nextjs = "Next.js" in tech_stack.get("frontend", "")

    if not frontend_ok:
        print("  ERROR: tech_stack.frontend is empty after --template fullstack")
    if not backend_ok:
        print("  ERROR: tech_stack.backend is empty after --template fullstack")
    if not frontend_has_nextjs:
        print(f"  ERROR: expected 'Next.js' in frontend, got: {tech_stack.get('frontend')!r}")

    result_ok = frontend_ok and backend_ok and frontend_has_nextjs
    return check(
        "CLI-05: init --template fullstack sets tech_stack.frontend (Next.js) and backend",
        result_ok,
    )


# ---------------------------------------------------------------------------
# CLI-06: template presets exist in projects/_templates/
# ---------------------------------------------------------------------------

def verify_cli_06() -> bool:
    """CLI-06: Template preset JSON files exist and are structurally valid."""
    templates_dir = ROOT / "projects" / "_templates"
    expected_templates = ["fullstack", "backend", "ml-pipeline"]
    required_keys = ["tech_stack", "l3_overrides"]

    all_ok = True
    for name in expected_templates:
        path = templates_dir / f"{name}.json"
        if not path.exists():
            print(f"  ERROR: {path} does not exist")
            all_ok = False
            continue

        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ERROR: {path} is not valid JSON: {e}")
            all_ok = False
            continue

        # Must have _template field
        if "_template" not in data:
            print(f"  ERROR: {path} missing '_template' field")
            all_ok = False

        # Must have tech_stack and l3_overrides
        for key in required_keys:
            if key not in data:
                print(f"  ERROR: {path} missing '{key}' key")
                all_ok = False

    return check(
        "CLI-06: fullstack.json, backend.json, ml-pipeline.json exist with _template, "
        "tech_stack, l3_overrides",
        all_ok,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Run all Phase 14 CLI verifications."""
    print("Phase 14: Project CLI Verification")
    print("=" * 45)

    # Save original active project — restore in finally
    try:
        original_active = get_active_project()
    except Exception as e:
        print(f"WARNING: could not read original active_project: {e}")
        original_active = "pumplai"  # Safe fallback

    results = []

    try:
        results.append(verify_cli_01())
        results.append(verify_cli_02())
        results.append(verify_cli_03())
        results.append(verify_cli_04(original_active))
        results.append(verify_cli_05())
        results.append(verify_cli_06())
    finally:
        # Restore original active project
        try:
            restore_result = run_cli("switch", original_active)
            if restore_result.returncode != 0:
                # If original project was removed somehow, fall back to pumplai
                run_cli("switch", "pumplai")
        except Exception as e:
            print(f"WARNING: could not restore active project '{original_active}': {e}")

        # Clean up all test projects
        cleanup_test_projects()

    passed = sum(results)
    total = len(results)

    print("=" * 45)
    print(f"Result: {passed}/{total} checks passed")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
