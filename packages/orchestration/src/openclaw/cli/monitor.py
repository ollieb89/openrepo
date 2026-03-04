"""
CLI Monitoring Tool - Real-time visibility into L3 activity.

This module provides a CLI interface for human operators to monitor L3 specialist
activity in real-time. It's the Phase 3 substitute for the Phase 4 dashboard.

Usage:
    python3 orchestration/monitor.py tail [--interval 1.0] [--project <id>]
    python3 orchestration/monitor.py status [--project <id>]
    python3 orchestration/monitor.py task <task_id> [--project <id>]
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import docker

from openclaw.state_engine import JarvisState
from openclaw.config import (
    DEFAULT_POOL_MAX_CONCURRENT,
    DEFAULT_POOL_MODE,
    DEFAULT_POOL_OVERFLOW_POLICY,
    POLL_INTERVAL,
    POLL_INTERVAL_ACTIVE,
    POLL_INTERVAL_IDLE,
    ensure_gateway,
    is_bootstrap_mode,
    get_project_root,
    get_state_path,
)
from openclaw.logging import get_logger
from openclaw.project_config import get_pool_config


logger = get_logger('monitor')


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# Standard 8-color ANSI — works in all terminals (per locked decision)
PROJECT_COLORS = [
    '\033[92m',  # Green
    '\033[94m',  # Blue
    '\033[95m',  # Magenta
    '\033[96m',  # Cyan
    '\033[93m',  # Yellow
    '\033[91m',  # Red
]


def get_project_color(project_id: str, project_list: list) -> str:
    """Deterministic color for a project based on its position in the known project list."""
    idx = project_list.index(project_id) if project_id in project_list else 0
    return PROJECT_COLORS[idx % len(PROJECT_COLORS)]


def _count_active_l3_containers() -> int:
    """Return count of running openclaw-managed L3 containers.

    Used by tail_state() to determine whether to use POLL_INTERVAL_ACTIVE or
    POLL_INTERVAL_IDLE. Fails open: returns 0 (idle) on any Docker error so the
    monitor continues running even when Docker is unavailable.

    Query: containers with label 'openclaw.managed=true' and status 'running'.
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(
            filters={"label": "openclaw.managed=true", "status": "running"}
        )
        return len(containers)
    except Exception as exc:
        logger.warning(
            "Docker query failed in adaptive poll — assuming idle",
            extra={"error": str(exc)},
        )
        return 0


def _discover_projects(project_filter: Optional[str] = None) -> List[Tuple[str, Path]]:
    """Return list of (project_id, state_file_path) tuples.

    Enumerates projects/ directory. Skips directories starting with '_'.
    If project_filter is set, returns only that project.
    State files that don't exist yet are included (exists=False) so
    caller can decide whether to skip or show 'No tasks'.
    """
    projects_dir = get_project_root() / "projects"
    results: List[Tuple[str, Path]] = []
    if not projects_dir.exists():
        return results
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if project_filter and entry.name != project_filter:
            continue
        state_file = get_state_path(entry.name)
        results.append((entry.name, state_file))
    return results


def format_timestamp(ts: float) -> str:
    """Format Unix timestamp as readable datetime."""
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def get_status_color(status: str) -> str:
    """Get ANSI color code for task status."""
    status_colors = {
        'completed': Colors.GREEN,
        'failed': Colors.RED,
        'rejected': Colors.RED,
        'in_progress': Colors.YELLOW,
        'testing': Colors.YELLOW,
        'starting': Colors.CYAN,
        'pending': Colors.BLUE,
    }
    return status_colors.get(status, Colors.RESET)


def tail_state(
    state_file_path: Optional[str] = None,
    interval: float = 1.0,
    project_filter: Optional[str] = None,
) -> None:
    """
    Continuously poll workspace-state.json and stream new activity.

    Polls at specified interval (default 1s), detects changes, and prints
    new activity log entries with color-coded status and project column.

    Args:
        state_file_path: Legacy single-file path (backward compat). If provided,
                         uses only that file. If None, discovers projects.
        interval: Polling interval in seconds (default: 1.0)
        project_filter: Filter output to a specific project ID
    """
    # Legacy single-file mode (backward compat)
    if state_file_path is not None:
        _tail_single_file(state_file_path, interval)
        return

    # Multi-project mode
    projects = _discover_projects(project_filter)
    project_ids = [p[0] for p in projects]

    if project_filter:
        header = f"Tailing Activity (project: {project_filter})"
    else:
        header = "Tailing Activity (all projects)"

    print(f"{Colors.BOLD}OpenClaw L3 Monitor - {header}{Colors.RESET}")
    print(f"Polling interval: {interval}s")
    print(f"Press Ctrl+C to stop\n")

    # Track seen activity entries per (project_id, task_id)
    seen_entries: Dict[str, Dict[str, int]] = {}
    last_statuses: Dict[str, Dict[str, str]] = {}

    # Session-scoped JarvisState instances keyed by project_id.
    # Created once per project so the Phase 21 mtime-based in-memory cache
    # provides hits between poll cycles instead of cold-starting every iteration.
    js_instances: Dict[str, JarvisState] = {}
    for proj_id, state_file in projects:
        if state_file.exists():
            js_instances[proj_id] = JarvisState(state_file)

    try:
        while True:
            for proj_id, state_file in projects:
                # Lazy creation: handle projects whose state file did not exist
                # at tail start but appeared later, or were previously removed.
                if proj_id not in js_instances:
                    if not state_file.exists():
                        continue
                    js_instances[proj_id] = JarvisState(state_file)
                js = js_instances[proj_id]

                project_color = get_project_color(proj_id, project_ids)
                proj_prefix = f"{project_color}{proj_id}{Colors.RESET}"

                try:
                    state = js.read_state()
                    tasks = state.get('tasks', {})

                    if proj_id not in seen_entries:
                        seen_entries[proj_id] = {}
                        last_statuses[proj_id] = {}

                    for task_id, task_data in tasks.items():
                        status = task_data.get('status', 'unknown')
                        activity_log = task_data.get('activity_log', [])

                        # Initialize tracking for new tasks
                        if task_id not in seen_entries[proj_id]:
                            seen_entries[proj_id][task_id] = 0
                            last_statuses[proj_id][task_id] = status

                        # Check for status transitions
                        if last_statuses[proj_id][task_id] != status:
                            status_color = get_status_color(status)
                            print(
                                f"[{proj_prefix}] {Colors.CYAN}[STATUS]{Colors.RESET} "
                                f"{Colors.BOLD}{task_id}{Colors.RESET} "
                                f"{last_statuses[proj_id][task_id]} → "
                                f"{status_color}{status}{Colors.RESET}"
                            )
                            last_statuses[proj_id][task_id] = status

                        # Print new activity entries
                        new_entries = activity_log[seen_entries[proj_id][task_id]:]
                        for entry in new_entries:
                            timestamp = entry.get('timestamp', time.time())
                            entry_status = entry.get('status', status)
                            entry_text = entry.get('entry', '')

                            status_color = get_status_color(entry_status)
                            formatted_time = format_timestamp(timestamp)

                            print(
                                f"[{proj_prefix}] [{formatted_time}] "
                                f"[{Colors.BOLD}{task_id}{Colors.RESET}] "
                                f"[{status_color}{entry_status}{Colors.RESET}] {entry_text}"
                            )

                        # Update seen count
                        seen_entries[proj_id][task_id] = len(activity_log)

                except Exception as e:
                    print(
                        f"[{proj_prefix}] {Colors.RED}Error reading state: {e}{Colors.RESET}",
                        file=sys.stderr,
                    )
                    # Evict the cached instance so it will be re-created if the
                    # state file comes back (e.g., after project re-initialisation).
                    js_instances.pop(proj_id, None)

            logger.debug(
                "poll cycle complete",
                extra={"projects_polled": len(projects), "instances_cached": len(js_instances)},
            )
            # Adaptive poll interval (OBS-05):
            # Short interval when L3 containers are active, long interval when idle.
            # Docker query is per-cycle — up to 30s lag on idle→active transition is acceptable.
            _active_count = _count_active_l3_containers()
            _sleep_sec = POLL_INTERVAL_ACTIVE if _active_count > 0 else POLL_INTERVAL_IDLE
            logger.debug(
                "adaptive poll sleep",
                extra={"active_containers": _active_count, "sleep_interval": _sleep_sec},
            )
            time.sleep(_sleep_sec)

    except KeyboardInterrupt:
        print(f"\n{Colors.BOLD}Monitor stopped{Colors.RESET}")


def _tail_single_file(state_file_path: str, interval: float = 1.0) -> None:
    """Legacy single-file tail mode for backward compatibility."""
    js = JarvisState(Path(state_file_path))

    # Track seen activity entries per task
    seen_entries: Dict[str, int] = {}
    last_statuses: Dict[str, str] = {}

    print(f"{Colors.BOLD}OpenClaw L3 Monitor - Tailing Activity{Colors.RESET}")
    print(f"Polling interval: {interval}s")
    print(f"Press Ctrl+C to stop\n")

    try:
        while True:
            try:
                state = js.read_state()
                tasks = state.get('tasks', {})

                for task_id, task_data in tasks.items():
                    status = task_data.get('status', 'unknown')
                    activity_log = task_data.get('activity_log', [])

                    # Initialize tracking for new tasks
                    if task_id not in seen_entries:
                        seen_entries[task_id] = 0
                        last_statuses[task_id] = status

                    # Check for status transitions
                    if last_statuses[task_id] != status:
                        status_color = get_status_color(status)
                        print(f"{Colors.CYAN}[STATUS]{Colors.RESET} {Colors.BOLD}{task_id}{Colors.RESET} "
                              f"{last_statuses[task_id]} → {status_color}{status}{Colors.RESET}")
                        last_statuses[task_id] = status

                    # Print new activity entries
                    new_entries = activity_log[seen_entries[task_id]:]
                    for entry in new_entries:
                        timestamp = entry.get('timestamp', time.time())
                        entry_status = entry.get('status', status)
                        entry_text = entry.get('entry', '')

                        status_color = get_status_color(entry_status)
                        formatted_time = format_timestamp(timestamp)

                        print(f"[{formatted_time}] [{Colors.BOLD}{task_id}{Colors.RESET}] "
                              f"[{status_color}{entry_status}{Colors.RESET}] {entry_text}")

                    # Update seen count
                    seen_entries[task_id] = len(activity_log)

                # Sleep until next poll
                time.sleep(interval)

            except Exception as e:
                print(f"{Colors.RED}Error reading state: {e}{Colors.RESET}", file=sys.stderr)
                time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n{Colors.BOLD}Monitor stopped{Colors.RESET}")


def show_status(
    state_file_path: Optional[str] = None,
    project_filter: Optional[str] = None,
) -> None:
    """
    One-shot display of current L3 state across all projects.

    Shows all tasks with project, status, skill_hint, timestamps, and active
    container count per project.

    Args:
        state_file_path: Legacy single-file path (backward compat).
        project_filter: Filter output to a specific project ID
    """
    # Legacy single-file mode
    if state_file_path is not None:
        _show_status_single_file(state_file_path)
        return

    projects = _discover_projects(project_filter)
    project_ids = [p[0] for p in projects]

    # Aggregate tasks across all projects
    all_tasks: List[Tuple[str, str, Any]] = []  # (project_id, task_id, task_data)
    active_statuses = {'in_progress', 'starting', 'testing'}
    active_per_project: Dict[str, int] = {}

    for proj_id, state_file in projects:
        if not state_file.exists():
            continue
        try:
            # One-shot call — JarvisState created per project per invocation (no cross-call cache needed)
            js = JarvisState(state_file)
            state = js.read_state()
            tasks = state.get('tasks', {})
            count = sum(1 for t in tasks.values() if t.get('status') in active_statuses)
            active_per_project[proj_id] = count
            for task_id, task_data in tasks.items():
                all_tasks.append((proj_id, task_id, task_data))
        except Exception as e:
            print(f"{Colors.RED}Error reading state for {proj_id}: {e}{Colors.RESET}", file=sys.stderr)

    if not all_tasks:
        print(f"{Colors.YELLOW}No tasks found{Colors.RESET}")
        return

    # Print header
    print(f"{Colors.BOLD}OpenClaw L3 Status{Colors.RESET}")
    if active_per_project:
        active_summary = ", ".join(
            f"{proj} {cnt}/3" for proj, cnt in sorted(active_per_project.items())
        )
        print(f"Active containers: {Colors.CYAN}{active_summary}{Colors.RESET}")
    else:
        print(f"Active containers: {Colors.CYAN}0{Colors.RESET}")
    print(f"Total tasks: {len(all_tasks)}\n")

    # Print table header
    print(
        f"{Colors.BOLD}"
        f"{'PROJECT':<15} {'TASK ID':<20} {'STATUS':<15} {'SKILL':<10} "
        f"{'CREATED':<20} {'LAST ACTIVITY'}"
        f"{Colors.RESET}"
    )
    print("-" * 115)

    # Sort tasks by created_at (newest first)
    sorted_tasks = sorted(
        all_tasks,
        key=lambda x: x[2].get('created_at', 0),
        reverse=True,
    )

    for proj_id, task_id, task_data in sorted_tasks:
        status = task_data.get('status', 'unknown')
        skill_hint = task_data.get('skill_hint', 'N/A')
        created_at = task_data.get('created_at', 0)
        activity_log = task_data.get('activity_log', [])

        # Get last activity entry
        last_activity = 'No activity'
        if activity_log:
            last_entry = activity_log[-1]
            last_activity = last_entry.get('entry', 'N/A')[:50]  # Truncate

        # Format timestamps
        created_str = format_timestamp(created_at) if created_at else 'N/A'

        # Color code status
        status_color = get_status_color(status)
        colored_status = f"{status_color}{status:<15}{Colors.RESET}"

        # Color code project
        project_color = get_project_color(proj_id, project_ids)
        colored_project = f"{project_color}{proj_id:<15}{Colors.RESET}"

        print(f"{colored_project} {task_id:<20} {colored_status} {skill_hint:<10} {created_str:<20} {last_activity}")

    print()


def _show_status_single_file(state_file_path: str) -> None:
    """Legacy single-file status mode for backward compatibility."""
    js = JarvisState(Path(state_file_path))

    try:
        state = js.read_state()
        tasks = state.get('tasks', {})

        if not tasks:
            print(f"{Colors.YELLOW}No tasks found{Colors.RESET}")
            return

        # Count active containers
        active_statuses = {'in_progress', 'starting', 'testing'}
        active_count = sum(1 for task in tasks.values()
                          if task.get('status') in active_statuses)

        # Print header
        print(f"{Colors.BOLD}OpenClaw L3 Status{Colors.RESET}")
        print(f"Active containers: {Colors.CYAN}{active_count}{Colors.RESET}/3")
        print(f"Total tasks: {len(tasks)}\n")

        # Print table header
        print(f"{Colors.BOLD}{'TASK ID':<20} {'STATUS':<15} {'SKILL':<10} {'CREATED':<20} {'LAST ACTIVITY'}{Colors.RESET}")
        print("-" * 100)

        # Sort tasks by created_at (newest first)
        sorted_tasks = sorted(
            tasks.items(),
            key=lambda x: x[1].get('created_at', 0),
            reverse=True
        )

        for task_id, task_data in sorted_tasks:
            status = task_data.get('status', 'unknown')
            skill_hint = task_data.get('skill_hint', 'N/A')
            created_at = task_data.get('created_at', 0)
            activity_log = task_data.get('activity_log', [])

            # Get last activity entry
            last_activity = 'No activity'
            if activity_log:
                last_entry = activity_log[-1]
                last_activity = last_entry.get('entry', 'N/A')[:50]  # Truncate

            # Format timestamps
            created_str = format_timestamp(created_at) if created_at else 'N/A'

            # Color code status
            status_color = get_status_color(status)
            colored_status = f"{status_color}{status:<15}{Colors.RESET}"

            print(f"{task_id:<20} {colored_status} {skill_hint:<10} {created_str:<20} {last_activity}")

        print()

    except Exception as e:
        print(f"{Colors.RED}Error reading state: {e}{Colors.RESET}", file=sys.stderr)
        sys.exit(1)


def show_task_detail(
    task_id: str,
    state_file_path: Optional[str] = None,
    project_filter: Optional[str] = None,
) -> None:
    """
    Show full activity log for a specific task.

    Searches all projects for the task_id. If found in multiple projects,
    reports ambiguity and asks user to specify --project.

    Args:
        task_id: The task identifier
        state_file_path: Legacy single-file path (backward compat).
        project_filter: Restrict search to this project ID
    """
    # Legacy single-file mode
    if state_file_path is not None:
        _show_task_detail_single_file(state_file_path, task_id)
        return

    projects = _discover_projects(project_filter)
    project_ids = [p[0] for p in projects]

    # Search all project state files
    matches: List[Tuple[str, Any]] = []  # (project_id, task_data)

    for proj_id, state_file in projects:
        if not state_file.exists():
            continue
        try:
            # One-shot call — JarvisState created per project per invocation (no cross-call cache needed)
            js = JarvisState(state_file)
            task_data = js.read_task(task_id)
            if task_data:
                matches.append((proj_id, task_data))
        except Exception:
            pass

    if not matches:
        print(f"{Colors.RED}Task {task_id} not found{Colors.RESET}")
        sys.exit(1)

    if len(matches) > 1:
        print(f"{Colors.YELLOW}Task ID found in multiple projects:{Colors.RESET}")
        for proj_id, task_data in matches:
            status = task_data.get('status', 'unknown')
            status_color = get_status_color(status)
            print(f"  {proj_id}: {status_color}{status}{Colors.RESET}")
        print("Use --project to specify.")
        sys.exit(1)

    # Exactly one match
    found_proj_id, task_data = matches[0]
    _print_task_detail(task_id, task_data, project_id=found_proj_id)


def _print_task_detail(task_id: str, task_data: Any, project_id: Optional[str] = None) -> None:
    """Print full task detail from task_data dict."""
    status = task_data.get('status', 'unknown')
    status_color = get_status_color(status)

    print(f"{Colors.BOLD}Task Details: {task_id}{Colors.RESET}")
    if project_id:
        print(f"Project: {project_id}")
    print(f"Status: {status_color}{status}{Colors.RESET}")
    print(f"Skill: {task_data.get('skill_hint', 'N/A')}")

    created_at = task_data.get('created_at', 0)
    updated_at = task_data.get('updated_at', 0)
    print(f"Created: {format_timestamp(created_at) if created_at else 'N/A'}")
    print(f"Updated: {format_timestamp(updated_at) if updated_at else 'N/A'}")

    # Print metadata
    metadata = task_data.get('metadata', {})
    if metadata:
        print(f"\nMetadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

    # Print activity log
    activity_log = task_data.get('activity_log', [])
    print(f"\n{Colors.BOLD}Activity Log ({len(activity_log)} entries):{Colors.RESET}")

    if not activity_log:
        print(f"{Colors.YELLOW}No activity recorded{Colors.RESET}")
    else:
        print()
        for entry in activity_log:
            timestamp = entry.get('timestamp', 0)
            entry_status = entry.get('status', 'unknown')
            entry_text = entry.get('entry', '')

            formatted_time = format_timestamp(timestamp)
            status_color = get_status_color(entry_status)

            print(f"[{formatted_time}] [{status_color}{entry_status:<12}{Colors.RESET}] {entry_text}")

    print()


def _show_task_detail_single_file(state_file_path: str, task_id: str) -> None:
    """Legacy single-file task detail mode for backward compatibility."""
    js = JarvisState(Path(state_file_path))

    try:
        task_data = js.read_task(task_id)

        if not task_data:
            print(f"{Colors.RED}Task {task_id} not found{Colors.RESET}")
            sys.exit(1)

        _print_task_detail(task_id, task_data)

    except Exception as e:
        print(f"{Colors.RED}Error reading task: {e}{Colors.RESET}", file=sys.stderr)
        sys.exit(1)


def show_pool_utilization(project_filter: Optional[str] = None) -> None:
    """
    Display per-project pool utilization computed on-the-fly from state data.

    Reads workspace-state.json for each project and aggregates task counts by
    status. Saturation percentage is color-coded: green (0-33%), yellow (34-66%),
    red (67-100%).

    Args:
        project_filter: If set, show only this project. If None, show all.
    """
    projects = _discover_projects(project_filter)

    active_statuses = {'in_progress', 'starting', 'testing'}
    pending_statuses = {'pending'}
    terminal_statuses = {'completed'}
    failed_statuses = {'failed', 'timeout'}

    rows = []
    total_active = 0
    total_queued = 0
    total_completed = 0
    total_failed = 0

    for proj_id, state_file in projects:
        # Read per-project pool config (max_concurrent, pool_mode, overflow_policy)
        logger.debug(
            "Reading pool config for monitor display",
            extra={"project_id": proj_id},
        )
        try:
            pool_cfg = get_pool_config(proj_id)
            proj_max_concurrent = pool_cfg["max_concurrent"]
            proj_pool_mode = pool_cfg["pool_mode"]
            proj_overflow_policy = pool_cfg["overflow_policy"]
        except Exception:
            proj_max_concurrent = DEFAULT_POOL_MAX_CONCURRENT
            proj_pool_mode = DEFAULT_POOL_MODE
            proj_overflow_policy = DEFAULT_POOL_OVERFLOW_POLICY

        if not state_file.exists():
            # Include project with zeroes — it exists but no tasks yet
            rows.append({
                "project_id": proj_id,
                "active": 0,
                "queued": 0,
                "completed": 0,
                "failed": 0,
                "max_concurrent": proj_max_concurrent,
                "pool_mode": proj_pool_mode,
                "overflow_policy": proj_overflow_policy,
                "saturation_pct": 0.0,
            })
            continue

        try:
            # One-shot call — JarvisState created per project per invocation (no cross-call cache needed)
            js = JarvisState(state_file)
            state = js.read_state()
            tasks = state.get('tasks', {})

            active = sum(1 for t in tasks.values() if t.get('status') in active_statuses)
            queued = sum(1 for t in tasks.values() if t.get('status') in pending_statuses)
            completed = sum(1 for t in tasks.values() if t.get('status') in terminal_statuses)
            failed = sum(1 for t in tasks.values() if t.get('status') in failed_statuses)
            saturation_pct = round((active / proj_max_concurrent) * 100, 1)

            rows.append({
                "project_id": proj_id,
                "active": active,
                "queued": queued,
                "completed": completed,
                "failed": failed,
                "max_concurrent": proj_max_concurrent,
                "pool_mode": proj_pool_mode,
                "overflow_policy": proj_overflow_policy,
                "saturation_pct": saturation_pct,
            })

            total_active += active
            total_queued += queued
            total_completed += completed
            total_failed += failed

        except Exception as e:
            print(f"{Colors.RED}Error reading state for {proj_id}: {e}{Colors.RESET}", file=sys.stderr)

    if not rows:
        print(f"{Colors.YELLOW}No tasks found{Colors.RESET}")
        return

    def saturation_color(pct: float) -> str:
        if pct <= 33.0:
            return Colors.GREEN
        elif pct <= 66.0:
            return Colors.YELLOW
        return Colors.RED

    # Print header
    print(f"{Colors.BOLD}OpenClaw Pool Utilization{Colors.RESET}")
    if project_filter:
        print(f"Project: {project_filter}\n")
    else:
        print()

    header = (
        f"{Colors.BOLD}"
        f"{'PROJECT':<18} {'MAX':<5} {'MODE':<10} {'OVERFLOW':<10} "
        f"{'ACTIVE':<8} {'QUEUED':<8} {'COMPLETED':<12} {'FAILED':<8} {'SATURATION'}"
        f"{Colors.RESET}"
    )
    print(header)
    print("-" * 105)

    for row in rows:
        pct = row["saturation_pct"]
        sat_color = saturation_color(pct)
        saturation_str = f"{sat_color}{pct:>5.1f}%{Colors.RESET}"

        print(
            f"{row['project_id']:<18} "
            f"{row['max_concurrent']:<5} "
            f"{row['pool_mode']:<10} "
            f"{row['overflow_policy']:<10} "
            f"{row['active']:<8} "
            f"{row['queued']:<8} "
            f"{row['completed']:<12} "
            f"{row['failed']:<8} "
            f"{saturation_str}"
        )

    # Summary line for multi-project view
    if project_filter is None and len(rows) > 1:
        print("-" * 105)
        total_max = sum(r["max_concurrent"] for r in rows)
        total_pct = round((total_active / total_max) * 100, 1) if total_max > 0 else 0.0
        sat_color = saturation_color(total_pct)
        total_saturation_str = f"{sat_color}{total_pct:>5.1f}%{Colors.RESET}"
        print(
            f"{'TOTAL':<18} "
            f"{total_max:<5} "
            f"{'—':<10} "
            f"{'—':<10} "
            f"{total_active:<8} "
            f"{total_queued:<8} "
            f"{total_completed:<12} "
            f"{total_failed:<8} "
            f"{total_saturation_str}"
        )

    print()



import asyncio
from openclaw.events.bridge import ensure_event_bridge
from openclaw.events.transport import get_socket_path
from openclaw.events.protocol import OrchestratorEvent

async def tail_events(project_id: str = None):
    """Stream events in real-time via the shared event bridge."""
    print(f"{Colors.BLUE}Streaming live events...{Colors.RESET}")

    # Ensure the shared bridge server is running
    started = ensure_event_bridge()
    if not started:
        print(f"{Colors.RED}Warning: Event bridge could not be started. Events may not be available.{Colors.RESET}")

    socket_path = get_socket_path()

    def render_event(event: OrchestratorEvent) -> None:
        if project_id and event.project_id != project_id:
            return

        color = Colors.BLUE
        if 'error' in event.type.value or 'failed' in event.type.value:
            color = Colors.RED
        elif 'completed' in event.type.value:
            color = Colors.GREEN

        task_str = f" [Task: {event.task_id}]" if event.task_id else ""
        print(f"[{event.timestamp:.2f}] {color}{event.type.value}{Colors.RESET}{task_str} Domain: {event.domain.value} Payload: {event.payload}")

    try:
        reader, writer = await asyncio.open_unix_connection(socket_path)
        print(f"{Colors.GREEN}Connected to event socket: {socket_path}{Colors.RESET}")
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    event = OrchestratorEvent.from_json(line.decode('utf-8').strip())
                    render_event(event)
                except Exception as e:
                    print(f"{Colors.RED}Error parsing event: {e}{Colors.RESET}")
        except KeyboardInterrupt:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    except (FileNotFoundError, ConnectionRefusedError) as e:
        print(f"{Colors.RED}Could not connect to event socket ({socket_path}): {e}{Colors.RESET}")
    except KeyboardInterrupt:
        pass


def run_tail_events(project_id: str = None):
    asyncio.run(tail_events(project_id))

def main():
    """CLI entrypoint for OpenClaw L3 Monitor."""
    parser = argparse.ArgumentParser(
        description='OpenClaw L3 Monitor - Real-time visibility into L3 specialist activity',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--bootstrap',
        action='store_true',
        help='Run without gateway (setup/diagnostic mode). Sets OPENCLAW_BOOTSTRAP=1.',
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # tail command
    tail_parser = subparsers.add_parser(
        'tail',
        help='Stream L3 activity in real-time'
    )
    tail_parser.add_argument(
        '--interval',
        type=float,
        default=POLL_INTERVAL,
        help=f'Polling interval in seconds (default: {POLL_INTERVAL})'
    )

    tail_parser.add_argument(
        '--events',
        action='store_true',
        help='Stream via cross-runtime event bridge instead of polling'
    )
    tail_parser.add_argument(
        '--state-file',
        type=str,
        default=None,
        help='Path to workspace-state.json (legacy single-file mode)'
    )

    # status command
    status_parser = subparsers.add_parser(
        'status',
        help='Show current L3 status (one-shot)'
    )
    status_parser.add_argument(
        '--state-file',
        type=str,
        default=None,
        help='Path to workspace-state.json (legacy single-file mode)'
    )

    # task command
    task_parser = subparsers.add_parser(
        'task',
        help='Show detailed task information'
    )
    task_parser.add_argument(
        'task_id',
        type=str,
        help='Task ID to display'
    )
    task_parser.add_argument(
        '--state-file',
        type=str,
        default=None,
        help='Path to workspace-state.json (legacy single-file mode)'
    )

    # pool command
    pool_parser = subparsers.add_parser(
        'pool',
        help='Show pool utilization per project'
    )

    # Add --project to all subcommands
    for sub in [tail_parser, status_parser, task_parser, pool_parser]:
        sub.add_argument(
            '--project',
            type=str,
            default=None,
            help='Filter output by project ID (default: show all projects)'
        )

    args = parser.parse_args()

    # Apply bootstrap flag before any command dispatch
    if args.bootstrap:
        import os as _os
        _os.environ["OPENCLAW_BOOTSTRAP"] = "1"

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Legacy single-file fallback: if --state-file is explicitly set,
    # pass it through for backward compat. Otherwise, use multi-project discovery.
    state_file = getattr(args, 'state_file', None)

    # Dispatch to appropriate function
    if args.command == 'tail':
        if getattr(args, 'events', False):
            # Event streaming requires the gateway bridge — check health at startup
            ensure_gateway()
            run_tail_events(project_id=args.project)
        else:
            tail_state(
                state_file_path=state_file,
                interval=args.interval,
                project_filter=args.project,
            )
    elif args.command == 'status':
        show_status(
            state_file_path=state_file,
            project_filter=args.project,
        )
    elif args.command == 'task':
        show_task_detail(
            task_id=args.task_id,
            state_file_path=state_file,
            project_filter=args.project,
        )
    elif args.command == 'pool':
        show_pool_utilization(project_filter=args.project)


if __name__ == '__main__':
    main()
