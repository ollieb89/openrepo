#!/usr/bin/env python3
"""
Unified cron manager CLI for OpenClaw.

Provides a single entry point for all cron operations:
- Job management (add, remove, list, edit)
- Execution logging (start, end, query)
- Health monitoring (check, alerts)
- Crontab generation and installation
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Optional

# Ensure we can import sibling modules
sys.path.insert(0, str(Path(__file__).parent))

from cronlog import CronLog, CronLogError
from healthcheck import HealthChecker, format_report
from scheduler import JobScheduler, CronJob, JobSchedule, NotificationConfig


class CronManager:
    """Unified cron manager for OpenClaw."""

    def __init__(self):
        self.log = CronLog()
        self.scheduler = JobScheduler()
        self.health = HealthChecker(self.log)

    def status(self) -> dict:
        """Get overall cron system status."""
        from datetime import datetime, timedelta

        stats = self.log.get_stats(since=datetime.now() - timedelta(days=7))

        return {
            "jobs_configured": len(self.scheduler.jobs),
            "jobs_enabled": len(self.scheduler.list_jobs(enabled_only=True)),
            "database": str(self.log.db_path),
            "total_runs_7d": stats.get("total_runs", 0),
            "by_status": stats.get("by_status", {})
        }

    def run_job(self, job_id: str, force: bool = False) -> int:
        """
        Execute a job directly (for testing/manual runs).

        Args:
            job_id: ID of the job to run
            force: Run even if idempotency check would skip

        Returns:
            Exit code from the job
        """
        job = self.scheduler.get_job(job_id)
        if not job:
            print(f"Job not found: {job_id}", file=sys.stderr)
            return 1

        if not job.enabled:
            print(f"Job is disabled: {job_id}", file=sys.stderr)
            return 1

        # Check idempotency
        if not force and job.schedule.idempotent:
            if not self.log.should_run(job_id, job.schedule.interval_check):
                print(f"Job '{job_id}' already ran successfully this {job.schedule.interval_check}")
                return 0

        # Build command
        import subprocess

        cmd = [job.command] + job.args

        # Log start
        run_id = self.log.log_start(job_id, " ".join(cmd))
        print(f"Started job {job_id} (run_id: {run_id})")

        try:
            # Execute with timeout (add small buffer for overhead)
            timeout_seconds = job.timeout if job.timeout > 0 else None
            result = subprocess.run(
                cmd,
                cwd=job.working_dir,
                env={**os.environ, **job.environment},
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            # Determine status
            if result.returncode == 0:
                status = "success"
            else:
                status = "failure"

            # Log end
            summary = f"Exit code: {result.returncode}"
            if result.stdout:
                summary += f", Output: {result.stdout[:200]}"

            self.log.log_end(run_id, status, summary, result.returncode)

            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            print(f"Job {job_id} completed: {status}")
            return result.returncode

        except subprocess.TimeoutExpired:
            self.log.log_end(run_id, "timeout", f"Timed out after {job.timeout}s")
            print(f"Job {job_id} timed out", file=sys.stderr)
            return 124

        except Exception as e:
            self.log.log_end(run_id, "failure", str(e))
            print(f"Job {job_id} failed: {e}", file=sys.stderr)
            return 1


def main():
    manager = CronManager()

    parser = argparse.ArgumentParser(
        prog="cron-manager",
        description="OpenClaw Cron Manager - Unified CLI for cron automation"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Show cron system status")

    # Job commands
    job_parser = subparsers.add_parser("job", help="Job management")
    job_subparsers = job_parser.add_subparsers(dest="job_cmd", help="Job commands")

    # job list
    job_list = job_subparsers.add_parser("list", help="List jobs")
    job_list.add_argument("--enabled-only", action="store_true")
    job_list.add_argument("--format", choices=["table", "json"], default="table")

    # job add
    job_add = job_subparsers.add_parser("add", help="Add a job")
    job_add.add_argument("id", help="Job ID")
    job_add.add_argument("name", help="Job name")
    job_add.add_argument("command", help="Command to run")
    job_add.add_argument("--cron", required=True, help="Cron expression")
    job_add.add_argument("--timeout", type=int, default=0)
    job_add.add_argument("--description", default="")
    job_add.add_argument("--tag", action="append", dest="tags", default=[])
    job_add.add_argument("--no-idempotent", action="store_true")

    # job remove
    job_remove = job_subparsers.add_parser("remove", help="Remove a job")
    job_remove.add_argument("id", help="Job ID")

    # job run
    job_run = job_subparsers.add_parser("run", help="Run a job manually")
    job_run.add_argument("id", help="Job ID")
    job_run.add_argument("--force", action="store_true", help="Skip idempotency check")

    # job enable/disable
    job_enable = job_subparsers.add_parser("enable", help="Enable a job")
    job_enable.add_argument("id", help="Job ID")
    job_disable = job_subparsers.add_parser("disable", help="Disable a job")
    job_disable.add_argument("id", help="Job ID")

    # Log commands
    log_parser = subparsers.add_parser("log", help="Log operations")
    log_subparsers = log_parser.add_subparsers(dest="log_cmd", help="Log commands")

    # log query
    log_query = log_subparsers.add_parser("query", help="Query logs")
    log_query.add_argument("--job", help="Filter by job name")
    log_query.add_argument("--status", choices=["running", "success", "failure", "timeout", "killed", "stale"])
    log_query.add_argument("--since", help="Since timestamp (ISO)")
    log_query.add_argument("--limit", type=int, default=50)
    log_query.add_argument("--format", choices=["table", "json"], default="table")

    # log start/end (for wrapper script integration)
    log_start = log_subparsers.add_parser("start", help="Log job start")
    log_start.add_argument("job_name", help="Job name")
    log_start.add_argument("--command", help="Command being run")
    log_start.add_argument("--pid", type=int, help="Process ID")

    log_end = log_subparsers.add_parser("end", help="Log job end")
    log_end.add_argument("run_id", type=int, help="Run ID from start")
    log_end.add_argument("status", choices=["success", "failure", "timeout", "killed"])
    log_end.add_argument("--summary", default="")
    log_end.add_argument("--exit-code", type=int)

    # log should-run
    log_should = log_subparsers.add_parser("should-run", help="Check if job should run")
    log_should.add_argument("job_name", help="Job name")
    log_should.add_argument("--interval", choices=["once", "hourly", "daily"], default="daily")

    # log cleanup
    log_subparsers.add_parser("cleanup", help="Mark stale jobs as failed")

    # Health commands
    health_parser = subparsers.add_parser("health", help="Health monitoring")
    health_subparsers = health_parser.add_subparsers(dest="health_cmd", help="Health commands")

    # health check
    health_check = health_subparsers.add_parser("check", help="Run health check")
    health_check.add_argument("--format", choices=["text", "json"], default="text")
    health_check.add_argument("--fail-on-alerts", action="store_true")

    # health job
    health_job = health_subparsers.add_parser("job", help="Check specific job health")
    health_job.add_argument("id", help="Job ID")
    health_job.add_argument("--format", choices=["text", "json"], default="text")

    # Crontab commands
    crontab_parser = subparsers.add_parser("crontab", help="Crontab management")
    crontab_parser.add_argument("--generate", action="store_true", help="Generate crontab")
    crontab_parser.add_argument("--install", action="store_true", help="Install crontab")
    crontab_parser.add_argument("--validate", action="store_true", help="Validate jobs")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "status":
            status = manager.status()
            print(f"Cron System Status")
            print(f"==================")
            print(f"Jobs Configured: {status['jobs_configured']}")
            print(f"Jobs Enabled: {status['jobs_enabled']}")
            print(f"Database: {status['database']}")
            print(f"Runs (7d): {status['total_runs_7d']}")
            if status['by_status']:
                breakdown = ', '.join(f"{k}: {v.get('count', 0)}" for k, v in status['by_status'].items())
                print(f"Breakdown: {breakdown}")

        elif args.command == "job":
            if not args.job_cmd:
                job_parser.print_help()
                sys.exit(1)

            if args.job_cmd == "list":
                jobs = manager.scheduler.list_jobs(enabled_only=args.enabled_only)
                if args.format == "json":
                    print(json.dumps([{
                        "id": j.id,
                        "name": j.name,
                        "enabled": j.enabled,
                        "cron": j.schedule.cron,
                        "command": j.command
                    } for j in jobs], indent=2))
                else:
                    print(f"{'ID':<20} {'Name':<30} {'Cron':<15} {'Status'}")
                    print("-" * 70)
                    for job in jobs:
                        status = "enabled" if job.enabled else "disabled"
                        print(f"{job.id:<20} {job.name:<30} {job.schedule.cron:<15} {status}")

            elif args.job_cmd == "add":
                job = CronJob(
                    id=args.id,
                    name=args.name,
                    command=args.command,
                    schedule=JobSchedule(
                        cron=args.cron,
                        idempotent=not args.no_idempotent
                    ),
                    timeout=args.timeout,
                    description=args.description,
                    tags=args.tags
                )
                manager.scheduler.add_job(job)
                print(f"Added job: {args.id}")

            elif args.job_cmd == "remove":
                if manager.scheduler.remove_job(args.id):
                    print(f"Removed job: {args.id}")
                else:
                    print(f"Job not found: {args.id}", file=sys.stderr)
                    sys.exit(1)

            elif args.job_cmd == "run":
                exit_code = manager.run_job(args.id, force=args.force)
                sys.exit(exit_code)

            elif args.job_cmd == "enable":
                job = manager.scheduler.get_job(args.id)
                if job:
                    job.enabled = True
                    manager.scheduler._save_config()
                    print(f"Enabled job: {args.id}")
                else:
                    print(f"Job not found: {args.id}", file=sys.stderr)
                    sys.exit(1)

            elif args.job_cmd == "disable":
                job = manager.scheduler.get_job(args.id)
                if job:
                    job.enabled = False
                    manager.scheduler._save_config()
                    print(f"Disabled job: {args.id}")
                else:
                    print(f"Job not found: {args.id}", file=sys.stderr)
                    sys.exit(1)

        elif args.command == "log":
            if not args.log_cmd:
                log_parser.print_help()
                sys.exit(1)

            if args.log_cmd == "query":
                from datetime import datetime
                since = datetime.fromisoformat(args.since) if args.since else None
                runs = manager.log.query(
                    job_name=args.job,
                    status=args.status,
                    since=since,
                    limit=args.limit
                )

                if args.format == "json":
                    print(json.dumps([{
                        "id": r.id,
                        "job": r.job_name,
                        "status": r.status,
                        "started": r.started_at.isoformat(),
                        "ended": r.ended_at.isoformat() if r.ended_at else None,
                        "duration_ms": r.duration_ms,
                        "summary": r.summary
                    } for r in runs], indent=2))
                else:
                    print(f"{'ID':<6} {'Job':<20} {'Status':<10} {'Started':<20} {'Duration'}")
                    print("-" * 80)
                    for r in runs:
                        started = r.started_at.strftime("%Y-%m-%d %H:%M")
                        duration = f"{r.duration_ms}ms" if r.duration_ms else "-"
                        print(f"{r.id:<6} {r.job_name:<20} {r.status:<10} {started:<20} {duration}")

            elif args.log_cmd == "start":
                run_id = manager.log.log_start(args.job_name, args.command, args.pid)
                print(run_id)

            elif args.log_cmd == "end":
                manager.log.log_end(args.run_id, args.status, args.summary, args.exit_code)
                print(f"Logged end: run {args.run_id} = {args.status}")

            elif args.log_cmd == "should-run":
                should = manager.log.should_run(args.job_name, args.interval)
                print("yes" if should else "no")
                sys.exit(0 if should else 1)

            elif args.log_cmd == "cleanup":
                count = manager.log.cleanup_stale()
                print(f"Marked {count} stale jobs as failed")

        elif args.command == "health":
            if not args.health_cmd:
                health_parser.print_help()
                sys.exit(1)

            if args.health_cmd == "check":
                report = manager.health.run_full_check()

                if args.format == "json":
                    print(json.dumps(report, indent=2))
                else:
                    print(format_report(report))

                if args.fail_on_alerts and report.get("alerts"):
                    sys.exit(1)

            elif args.health_cmd == "job":
                result = manager.health.check_job_health(args.id)
                if args.format == "json":
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Job: {result['job_name']}")
                    print(f"Health: {result['health_status']}")
                    print(f"Success Rate: {result['success_rate']}%")
                    print(f"Runs (24h): {result['total_runs_24h']}")

        elif args.command == "crontab":
            if args.validate:
                errors = manager.scheduler.validate_jobs()
                if errors:
                    print("Validation errors:", file=sys.stderr)
                    for error in errors:
                        print(f"  {error['job_id']}: {', '.join(error['errors'])}")
                    sys.exit(1)
                else:
                    print("All jobs valid")

            elif args.install:
                if manager.scheduler.install_crontab():
                    print("Crontab installed")
                else:
                    print("Failed to install crontab", file=sys.stderr)
                    sys.exit(1)
            else:
                print(manager.scheduler.generate_crontab())

    except CronLogError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
