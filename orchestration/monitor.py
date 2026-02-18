"""
CLI Monitoring Tool - Real-time visibility into L3 activity.

This module provides a CLI interface for human operators to monitor L3 specialist
activity in real-time. It's the Phase 3 substitute for the Phase 4 dashboard.

Usage:
    python3 orchestration/monitor.py tail [--interval 1.0]
    python3 orchestration/monitor.py status
    python3 orchestration/monitor.py task <task_id>
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set

# Handle both module import and direct execution
try:
    from .state_engine import JarvisState
    from .config import STATE_FILE, POLL_INTERVAL
except ImportError:
    # Direct execution - add parent dir to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from orchestration.state_engine import JarvisState
    from orchestration.config import STATE_FILE, POLL_INTERVAL


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


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


def tail_state(state_file_path: str, interval: float = 1.0) -> None:
    """
    Continuously poll workspace-state.json and stream new activity.
    
    Polls at specified interval (default 1s), detects changes, and prints
    new activity log entries with color-coded status.
    
    Args:
        state_file_path: Path to workspace-state.json
        interval: Polling interval in seconds (default: 1.0)
    """
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


def show_status(state_file_path: str) -> None:
    """
    One-shot display of current L3 state.
    
    Shows all tasks with status, skill_hint, timestamps, and active container count.
    
    Args:
        state_file_path: Path to workspace-state.json
    """
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


def show_task_detail(state_file_path: str, task_id: str) -> None:
    """
    Show full activity log for a specific task.
    
    Includes all timestamped entries and task metadata.
    
    Args:
        state_file_path: Path to workspace-state.json
        task_id: The task identifier
    """
    js = JarvisState(Path(state_file_path))
    
    try:
        task_data = js.read_task(task_id)
        
        if not task_data:
            print(f"{Colors.RED}Task {task_id} not found{Colors.RESET}")
            sys.exit(1)
        
        # Print task header
        status = task_data.get('status', 'unknown')
        status_color = get_status_color(status)
        
        print(f"{Colors.BOLD}Task Details: {task_id}{Colors.RESET}")
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
        
    except Exception as e:
        print(f"{Colors.RED}Error reading task: {e}{Colors.RESET}", file=sys.stderr)
        sys.exit(1)


def main():
    """CLI entrypoint for OpenClaw L3 Monitor."""
    parser = argparse.ArgumentParser(
        description='OpenClaw L3 Monitor - Real-time visibility into L3 specialist activity',
        formatter_class=argparse.RawDescriptionHelpFormatter
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
        '--state-file',
        type=str,
        default=str(STATE_FILE),
        help='Path to workspace-state.json'
    )
    
    # status command
    status_parser = subparsers.add_parser(
        'status',
        help='Show current L3 status (one-shot)'
    )
    status_parser.add_argument(
        '--state-file',
        type=str,
        default=str(STATE_FILE),
        help='Path to workspace-state.json'
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
        default=str(STATE_FILE),
        help='Path to workspace-state.json'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to appropriate function
    if args.command == 'tail':
        tail_state(args.state_file, args.interval)
    elif args.command == 'status':
        show_status(args.state_file)
    elif args.command == 'task':
        show_task_detail(args.state_file, args.task_id)


if __name__ == '__main__':
    main()
