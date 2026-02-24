#!/usr/bin/env python3
"""
Migrate workspace state to per-project path convention.

Usage:
    python3 orchestration/migrate_state.py [--project pumplai]

This command is IDEMPOTENT — safe to run multiple times.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestration.state_engine import JarvisState
from orchestration.project_config import get_state_path, get_snapshot_dir, _find_project_root

IN_FLIGHT_STATUSES = {'spawned', 'running', 'in_progress', 'starting', 'testing'}


def main():
    parser = argparse.ArgumentParser(description="Migrate OpenClaw state to per-project paths")
    parser.add_argument("--project", default="pumplai", help="Project ID (default: pumplai)")
    args = parser.parse_args()

    project_root = _find_project_root()
    old_path = project_root / "workspace" / ".openclaw" / "workspace-state.json"
    new_path = get_state_path(args.project)

    # Check if already migrated
    if not old_path.exists():
        if new_path.exists():
            print(f"Already migrated. State file at: {new_path}")
            return 0
        else:
            print(f"No state file found at old path: {old_path}")
            print(f"Creating empty state at new path: {new_path}")
            # Create empty state at new location
            new_path.parent.mkdir(parents=True, exist_ok=True)
            JarvisState(new_path)._ensure_state_file()
            return 0

    # Read and inspect old state
    js = JarvisState(old_path)
    state = js.read_state()
    tasks = state.get("tasks", {})

    # Guard: check for in-flight tasks
    blocking_tasks = [
        tid for tid, tdata in tasks.items()
        if tdata.get("status") in IN_FLIGHT_STATUSES
    ]
    if blocking_tasks:
        print("ERROR: Cannot migrate while tasks are in-flight.")
        print("Blocking tasks:")
        for tid in blocking_tasks:
            status = tasks[tid].get("status", "unknown")
            print(f"  - {tid} ({status})")
        print("Wait for all tasks to complete or fail, then run migration again.")
        return 1

    # Print before/after summary
    print(f"Migration plan:")
    print(f"  Old state file: {old_path}")
    print(f"  New state file: {new_path}")
    if tasks:
        print(f"  Tasks to migrate: {len(tasks)}")
        for tid, tdata in tasks.items():
            print(f"    - {tid} ({tdata.get('status', 'unknown')})")
    else:
        print("  Tasks to migrate: 0 (empty state)")
    print()

    # Create backup
    backup_dir = project_root / "workspace" / ".openclaw" / ".backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / "workspace-state.json.bak"
    shutil.copy2(old_path, backup_path)
    print(f"Backed up to: {backup_path}")

    # Create new directory and copy state
    new_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old_path, new_path)
    print(f"Copied state to: {new_path}")

    # Verify copy integrity
    with open(new_path) as f:
        verify = json.load(f)
    assert len(verify.get("tasks", {})) == len(tasks), "Task count mismatch after copy"

    # Migrate snapshots if they exist
    old_snapshots = project_root / "workspace" / ".openclaw" / "snapshots"
    if old_snapshots.exists() and old_snapshots.is_dir():
        new_snapshots = get_snapshot_dir(args.project)
        if old_snapshots.iterdir():
            shutil.copytree(old_snapshots, new_snapshots, dirs_exist_ok=True)
            print(f"Migrated snapshots: {old_snapshots} -> {new_snapshots}")

    # Hard cutover: replace old file with sentinel
    sentinel = {
        "migrated": True,
        "new_path": str(new_path),
        "error": (
            f"This state file has been migrated to {new_path}. "
            "Update callers to use project_config.get_state_path()."
        )
    }
    with open(old_path, 'w') as f:
        json.dump(sentinel, f, indent=2)
    print(f"Old path sentineled: {old_path}")

    print()
    print("Migration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
