"""
CLI interface for Swarm Query skill.

Usage:
    python -m agents.clawdia_prime.skills.swarm_query overview
    python -m agents.clawdia_prime.skills.swarm_query status --project main
    python -m agents.clawdia_prime.skills.swarm_query stalled --threshold 30
    python -m agents.clawdia_prime.skills.swarm_query health
"""

import argparse
import sys
from datetime import datetime
from typing import Optional

from .query import SwarmQuery


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def format_timestamp(ts: Optional[float]) -> str:
    """Format Unix timestamp as readable datetime."""
    if not ts:
        return "Never"
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def format_duration(minutes: float) -> str:
    """Format minutes as human-readable duration."""
    if minutes < 1:
        return f"{int(minutes * 60)}s"
    elif minutes < 60:
        return f"{int(minutes)}m"
    else:
        return f"{int(minutes / 60)}h {int(minutes % 60)}m"


def health_color(score: float) -> str:
    """Get color for health score."""
    if score >= 0.7:
        return Colors.GREEN
    elif score >= 0.4:
        return Colors.YELLOW
    else:
        return Colors.RED


def status_color(status: str) -> str:
    """Get color for task status."""
    colors = {
        'completed': Colors.GREEN,
        'failed': Colors.RED,
        'rejected': Colors.RED,
        'in_progress': Colors.YELLOW,
        'testing': Colors.YELLOW,
        'starting': Colors.CYAN,
        'pending': Colors.BLUE,
    }
    return colors.get(status, Colors.RESET)


def cmd_overview(args):
    """Show swarm overview across all projects."""
    query = SwarmQuery()
    overview = query.get_swarm_overview()
    
    print(f"{Colors.BOLD}OpenClaw Swarm Overview{Colors.RESET}")
    print(f"Projects monitored: {len(overview.projects)}")
    print(f"Total tasks: {overview.total_tasks}")
    print(f"  {Colors.YELLOW}Active:{Colors.RESET} {overview.total_active}")
    print(f"  {Colors.BLUE}Queued:{Colors.RESET} {overview.total_queued}")
    print(f"  {Colors.GREEN}Completed:{Colors.RESET} {overview.total_completed}")
    print(f"  {Colors.RED}Failed:{Colors.RESET} {overview.total_failed}")
    
    if overview.bottleneck_projects:
        print(f"\n{Colors.RED}{Colors.BOLD}Bottlenecks detected:{Colors.RESET}")
        for proj in overview.bottleneck_projects:
            print(f"  ⚠️  {proj}")
    else:
        print(f"\n{Colors.GREEN}No bottlenecks detected{Colors.RESET}")
    
    # Project detail table
    if overview.projects:
        print(f"\n{Colors.BOLD}{'Project':<15} {'Health':<8} {'Active':<8} {'Queued':<8} {'Failed':<8} {'Containers':<10} {'Last Activity'}{Colors.RESET}")
        print("-" * 90)
        
        for proj in sorted(overview.projects, key=lambda p: p.health_score):
            health_str = f"{health_color(proj.health_score)}{proj.health_score:.1f}{Colors.RESET}"
            last_act = format_duration((datetime.now().timestamp() - proj.last_activity) / 60) if proj.last_activity else "Never"
            
            print(f"{proj.project_id:<15} {health_str:<15} {proj.active_tasks:<8} {proj.queued_tasks:<8} {proj.failed_tasks:<8} {proj.l3_containers_running:<10} {last_act}")
    
    print()
    return 0


def cmd_status(args):
    """Show detailed status for a specific project."""
    if not args.project:
        print(f"{Colors.RED}Error: --project required{Colors.RESET}", file=sys.stderr)
        return 1
    
    query = SwarmQuery()
    snapshot = query.get_project_status(args.project, use_cache=False)
    
    if not snapshot:
        print(f"{Colors.RED}Project '{args.project}' not found or has no state{Colors.RESET}")
        return 1
    
    print(f"{Colors.BOLD}Project: {snapshot.project_id}{Colors.RESET}")
    
    health_str = f"{health_color(snapshot.health_score)}{snapshot.health_score:.2f}{Colors.RESET}"
    print(f"Health Score: {health_str}")
    print(f"L3 Containers Running: {snapshot.l3_containers_running}")
    print(f"Last Activity: {format_timestamp(snapshot.last_activity)}")
    
    print(f"\n{Colors.BOLD}Task Summary:{Colors.RESET}")
    print(f"  Active: {snapshot.active_tasks}")
    print(f"  Queued: {snapshot.queued_tasks}")
    print(f"  Completed: {snapshot.completed_tasks}")
    print(f"  Failed: {snapshot.failed_tasks}")
    print(f"  Total: {len(snapshot.tasks)}")
    
    if snapshot.tasks:
        print(f"\n{Colors.BOLD}{'Task ID':<20} {'Status':<15} {'Skill':<12} {'Updated':<12} {'Activity'}{Colors.RESET}")
        print("-" * 80)
        
        # Sort by updated_at (most recent first)
        sorted_tasks = sorted(snapshot.tasks.values(), key=lambda t: t.updated_at, reverse=True)
        
        for task in sorted_tasks[:20]:  # Limit to 20 most recent
            status_colored = f"{status_color(task.status)}{task.status:<15}{Colors.RESET}"
            updated_ago = format_duration(task.minutes_since_update) + " ago"
            
            print(f"{task.task_id:<20} {status_colored} {task.skill_hint:<12} {updated_ago:<12} {task.activity_count}")
        
        if len(snapshot.tasks) > 20:
            print(f"\n... and {len(snapshot.tasks) - 20} more tasks")
    
    # Show stalled tasks if any
    stalled = snapshot.get_stalled_tasks(threshold_minutes=30)
    if stalled:
        print(f"\n{Colors.RED}{Colors.BOLD}Stalled Tasks (>30m no activity):{Colors.RESET}")
        for task in stalled:
            print(f"  ⚠️  {task.task_id} ({format_duration(task.minutes_since_update)} inactive)")
    
    print()
    return 0


def cmd_stalled(args):
    """Find stalled tasks across all projects."""
    threshold = args.threshold
    query = SwarmQuery()
    stalled_by_project = query.find_stalled_tasks(threshold_minutes=threshold)
    
    if not stalled_by_project:
        print(f"{Colors.GREEN}No stalled tasks found (threshold: {threshold}m){Colors.RESET}")
        return 0
    
    total_stalled = sum(len(tasks) for tasks in stalled_by_project.values())
    print(f"{Colors.YELLOW}{Colors.BOLD}Found {total_stalled} stalled tasks across {len(stalled_by_project)} projects:{Colors.RESET}")
    print(f"(Threshold: {threshold} minutes without activity)\n")
    
    for project_id, tasks in stalled_by_project.items():
        print(f"{Colors.BOLD}{project_id}:{Colors.RESET}")
        for task in tasks:
            inactive_time = format_duration(task.minutes_since_update)
            print(f"  {Colors.RED}•{Colors.RESET} {task.task_id}")
            print(f"    Status: {task.status}, Skill: {task.skill_hint}")
            print(f"    Inactive for: {inactive_time}")
            if task.last_entry:
                print(f"    Last entry: {task.last_entry[:60]}...")
        print()
    
    return 0


def cmd_health(args):
    """Show health scores for all projects."""
    query = SwarmQuery()
    overview = query.get_swarm_overview()
    
    if not overview.projects:
        print(f"{Colors.YELLOW}No projects found{Colors.RESET}")
        return 0
    
    print(f"{Colors.BOLD}Project Health Scores{Colors.RESET}")
    print(f"(1.0 = perfect, 0.0 = critical)\n")
    
    # Sort by health score (worst first)
    sorted_projects = sorted(overview.projects, key=lambda p: p.health_score)
    
    for proj in sorted_projects:
        health_colored = f"{health_color(proj.health_score)}{proj.health_score:.2f}{Colors.RESET}"
        status_icon = "🟢" if proj.health_score >= 0.7 else "🟡" if proj.health_score >= 0.4 else "🔴"
        
        print(f"{status_icon} {proj.project_id:<15} {health_colored}", end="")
        
        # Show factors affecting health
        factors = []
        if proj.active_tasks >= 3:
            factors.append(f"at capacity ({proj.active_tasks} active)")
        if proj.queued_tasks > 5:
            factors.append(f"backlog ({proj.queued_tasks} queued)")
        if proj.failed_tasks > 0:
            factors.append(f"{proj.failed_tasks} failures")
        stalled = len(proj.get_stalled_tasks())
        if stalled > 0:
            factors.append(f"{stalled} stalled")
        
        if factors:
            print(f"  [{', '.join(factors)}]")
        else:
            print("  [healthy]")
    
    print()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Swarm Query - L1 visibility into OpenClaw swarm state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s overview              # Show swarm-wide summary
  %(prog)s status --project main # Detailed view of one project
  %(prog)s stalled --threshold 30 # Find tasks stuck for 30+ minutes
  %(prog)s health                # Health scores for all projects
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # overview command
    overview_parser = subparsers.add_parser('overview', help='Show swarm overview')
    
    # status command
    status_parser = subparsers.add_parser('status', help='Show project details')
    status_parser.add_argument('--project', '-p', required=True, help='Project ID')
    
    # stalled command
    stalled_parser = subparsers.add_parser('stalled', help='Find stalled tasks')
    stalled_parser.add_argument(
        '--threshold', '-t', 
        type=float, 
        default=30.0,
        help='Inactivity threshold in minutes (default: 30)'
    )
    
    # health command
    health_parser = subparsers.add_parser('health', help='Show health scores')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Dispatch to command handler
    commands = {
        'overview': cmd_overview,
        'status': cmd_status,
        'stalled': cmd_stalled,
        'health': cmd_health,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
