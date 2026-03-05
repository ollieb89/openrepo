#!/usr/bin/env python3
"""
Cron job scheduler configuration and management for the agent framework.

Manages job definitions with structured payloads that include:
- Cron expression and scheduling
- Cron logging integration
- Notification delivery configuration
- Agent framework integration
"""

import json
import sys
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field, asdict


# Paths
CRON_DIR = Path(__file__).parent
JOBS_CONFIG_PATH = CRON_DIR / "jobs.json"
CRONTAB_HEADER = """
# OpenClaw Cron Jobs - Auto-generated
# Generated: {timestamp}
# DO NOT EDIT MANUALLY - Use cron/scheduler.py instead

SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
CRONWRAP={cronwrap}
CRONLOG={cronlog}

""".strip()


@dataclass
class NotificationConfig:
    """Notification configuration for a job."""
    enabled: bool = True
    on_success: bool = False
    on_failure: bool = True
    channels: List[str] = field(default_factory=lambda: ["log"])
    webhook_url: Optional[str] = None


@dataclass
class JobSchedule:
    """Schedule configuration for a job."""
    cron: str  # Standard cron expression (5 fields)
    timezone: str = "UTC"
    skip_if_running: bool = True
    idempotent: bool = True  # Use should-run check
    interval_check: Literal["once", "hourly", "daily"] = "daily"


@dataclass
class CronJob:
    """
    Structured payload for a cron job with full integration.
    """
    id: str
    name: str
    enabled: bool = True
    command: str = ""
    args: List[str] = field(default_factory=list)
    schedule: JobSchedule = field(default_factory=lambda: JobSchedule(cron="0 0 * * *"))
    timeout: int = 0  # 0 = no timeout
    working_dir: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    log_output: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_crontab_entry(self) -> str:
        """Convert job to crontab entry format."""
        if not self.enabled:
            return f"# {self.id} (disabled)"

        # Build the command with cronwrap
        cmd_parts = ["$CRONWRAP", "-n", self.id]

        if self.timeout > 0:
            cmd_parts.extend(["-t", str(self.timeout)])

        # Add idempotency check if enabled
        if self.schedule.idempotent:
            check_cmd = f"$CRONLOG should-run {self.id} --interval {self.schedule.interval_check} && "
        else:
            check_cmd = ""

        # Build the actual command with proper shell escaping
        actual_cmd = shlex.quote(self.command)
        if self.args:
            actual_cmd += " " + " ".join(shlex.quote(a) for a in self.args)

        # Working directory
        if self.working_dir:
            actual_cmd = f"cd {shlex.quote(self.working_dir)} && {actual_cmd}"

        # Environment variables
        env_prefix = ""
        for key, value in self.environment.items():
            env_prefix += f'{shlex.quote(key)}={shlex.quote(value)} '

        if env_prefix:
            actual_cmd = f"{env_prefix}{actual_cmd}"

        cmd_parts.extend(["--", actual_cmd])

        full_cmd = f"{check_cmd}{' '.join(cmd_parts)}"

        # Build comment
        comment = f"# {self.name}"
        if self.description:
            comment += f" - {self.description}"

        return f"{self.schedule.cron} {full_cmd} {comment}"


class JobScheduler:
    """Manages cron job configurations and crontab generation."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or JOBS_CONFIG_PATH
        self.jobs: List[CronJob] = []
        self._load_config()

    def _load_config(self) -> None:
        """Load job configuration from JSON."""
        if not self.config_path.exists():
            self.jobs = []
            return

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            self.jobs = []
            for job_data in data.get("jobs", []):
                # Parse nested structures
                schedule_data = job_data.pop("schedule", {})
                notification_data = job_data.pop("notifications", {})

                schedule = JobSchedule(**schedule_data)
                notifications = NotificationConfig(**notification_data)

                self.jobs.append(CronJob(
                    schedule=schedule,
                    notifications=notifications,
                    **job_data
                ))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Invalid jobs config: {e}")

    def _save_config(self) -> None:
        """Save job configuration to JSON, preserving schema."""
        # Load existing to preserve schema
        existing_data = {}
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        data = {
            "version": existing_data.get("version", 1),
            "schema": existing_data.get("schema", {}),
            "updated_at": datetime.now().isoformat(),
            "jobs": []
        }

        for job in self.jobs:
            job_dict = asdict(job)
            data["jobs"].append(job_dict)

        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_job(self, job: CronJob) -> None:
        """Add a new job."""
        # Remove existing job with same ID
        self.jobs = [j for j in self.jobs if j.id != job.id]
        self.jobs.append(job)
        self._save_config()

    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID."""
        original_count = len(self.jobs)
        self.jobs = [j for j in self.jobs if j.id != job_id]
        if len(self.jobs) < original_count:
            self._save_config()
            return True
        return False

    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get a job by ID."""
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def list_jobs(self, enabled_only: bool = False) -> List[CronJob]:
        """List all jobs."""
        if enabled_only:
            return [j for j in self.jobs if j.enabled]
        return self.jobs

    def generate_crontab(self) -> str:
        """Generate crontab content from job configurations."""
        lines = [
            CRONTAB_HEADER.format(
                timestamp=datetime.now().isoformat(),
                cronwrap=CRON_DIR / "cronwrap.sh",
                cronlog=CRON_DIR / "cronlog.py"
            ),
            ""
        ]

        # Group jobs by tag for organization
        untagged_jobs = [j for j in self.jobs if not j.tags]
        tagged_jobs = [j for j in self.jobs if j.tags]

        # Add untagged jobs first
        if untagged_jobs:
            lines.append("# General Jobs")
            lines.append("")
            for job in untagged_jobs:
                lines.append(job.to_crontab_entry())
            lines.append("")

        # Group tagged jobs
        tags = set()
        for job in tagged_jobs:
            tags.update(job.tags)

        for tag in sorted(tags):
            lines.append(f"# {tag.upper()} Jobs")
            lines.append("")
            for job in tagged_jobs:
                if tag in job.tags:
                    lines.append(job.to_crontab_entry())
            lines.append("")

        # Add health check job
        lines.append("# Health Check - runs every 30 minutes")
        lines.append("*/30 * * * * $CRONLOG cleanup-stale > /dev/null 2>&1")
        lines.append("")

        return "\n".join(lines)

    def install_crontab(self, user: bool = True) -> bool:
        """
        Install the generated crontab.

        Args:
            user: Install for current user (vs system-wide)

        Returns:
            True if successful
        """
        crontab_content = self.generate_crontab()

        try:
            if user:
                # Install for current user
                result = subprocess.run(
                    ["crontab", "-"],
                    input=crontab_content,
                    capture_output=True,
                    text=True
                )
            else:
                # System-wide (requires root)
                result = subprocess.run(
                    ["tee", "/etc/cron.d/openclaw"],
                    input=crontab_content,
                    capture_output=True,
                    text=True
                )

            if result.returncode != 0:
                print(f"Error installing crontab: {result.stderr}", file=sys.stderr)
                return False

            return True
        except FileNotFoundError:
            print("crontab command not found", file=sys.stderr)
            return False

    def validate_jobs(self) -> List[Dict[str, Any]]:
        """Validate all job configurations and return errors."""
        errors = []

        for job in self.jobs:
            job_errors = []

            if not job.id:
                job_errors.append("Missing job ID")
            if not job.name:
                job_errors.append("Missing job name")
            if not job.command:
                job_errors.append("Missing command")
            if not job.schedule.cron:
                job_errors.append("Missing cron expression")

            # Validate cron expression format (basic check)
            cron_parts = job.schedule.cron.split()
            if len(cron_parts) != 5:
                job_errors.append(f"Invalid cron expression: {job.schedule.cron}")

            if job_errors:
                errors.append({
                    "job_id": job.id or "unknown",
                    "errors": job_errors
                })

        return errors


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cron job scheduler")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list
    list_parser = subparsers.add_parser("list", help="List jobs")
    list_parser.add_argument("--enabled-only", action="store_true")
    list_parser.add_argument("--format", choices=["table", "json"], default="table")

    # add
    add_parser = subparsers.add_parser("add", help="Add a job")
    add_parser.add_argument("id", help="Job ID")
    add_parser.add_argument("name", help="Job name")
    add_parser.add_argument("command", help="Command to run")
    add_parser.add_argument("--cron", required=True, help="Cron expression")
    add_parser.add_argument("--timeout", type=int, default=0, help="Timeout in seconds")
    add_parser.add_argument("--description", help="Job description")
    add_parser.add_argument("--tag", action="append", dest="tags", help="Job tag")
    add_parser.add_argument("--no-idempotent", action="store_true", help="Disable idempotency check")

    # remove
    remove_parser = subparsers.add_parser("remove", help="Remove a job")
    remove_parser.add_argument("id", help="Job ID")

    # crontab
    crontab_parser = subparsers.add_parser("crontab", help="Generate crontab")
    crontab_parser.add_argument("--install", action="store_true", help="Install crontab")
    crontab_parser.add_argument("--user", action="store_true", default=True, help="User crontab")

    # validate
    subparsers.add_parser("validate", help="Validate job configurations")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    scheduler = JobScheduler()

    if args.command == "list":
        jobs = scheduler.list_jobs(enabled_only=args.enabled_only)

        if args.format == "json":
            print(json.dumps([asdict(j) for j in jobs], indent=2))
        else:
            print(f"{'ID':<20} {'Name':<30} {'Cron':<15} {'Status'}")
            print("-" * 70)
            for job in jobs:
                status = "enabled" if job.enabled else "disabled"
                print(f"{job.id:<20} {job.name:<30} {job.schedule.cron:<15} {status}")

    elif args.command == "add":
        job = CronJob(
            id=args.id,
            name=args.name,
            command=args.command,
            schedule=JobSchedule(
                cron=args.cron,
                idempotent=not args.no_idempotent
            ),
            timeout=args.timeout,
            description=args.description or "",
            tags=args.tags or []
        )
        scheduler.add_job(job)
        print(f"Added job: {args.id}")

    elif args.command == "remove":
        if scheduler.remove_job(args.id):
            print(f"Removed job: {args.id}")
        else:
            print(f"Job not found: {args.id}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "crontab":
        if args.install:
            if scheduler.install_crontab(user=args.user):
                print("Crontab installed successfully")
            else:
                print("Failed to install crontab", file=sys.stderr)
                sys.exit(1)
        else:
            print(scheduler.generate_crontab())

    elif args.command == "validate":
        errors = scheduler.validate_jobs()
        if errors:
            print("Validation errors:", file=sys.stderr)
            for error in errors:
                print(f"  Job '{error['job_id']}':")
                for e in error["errors"]:
                    print(f"    - {e}")
            sys.exit(1)
        else:
            print("All jobs are valid")
