#!/usr/bin/env python3
"""
Central cron log database (SQLite) for job tracking and reliability.

Provides:
- log-start: record job start, return run ID
- log-end: record completion with status, duration, summary
- query: filter history by job name, status, date range
- should-run: idempotency check (skip if already succeeded today/this hour)
- cleanup-stale: auto-mark jobs stuck in "running" state for >2 hours as failed
"""

import sqlite3
import json
import shlex
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Literal
from contextlib import contextmanager
from pathlib import Path


# Database path - stored in logs directory alongside other operational data
DB_PATH = Path(__file__).parent.parent / "logs" / "cron.db"

# Constants
RUNNING_TIMEOUT_MINUTES = 120  # 2 hours
FAILURE_WINDOW_HOURS = 6
FAILURE_THRESHOLD = 3


@dataclass
class CronRun:
    """Represents a single cron job execution."""
    id: int
    job_name: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: Literal["running", "success", "failure", "timeout", "killed", "stale"]
    duration_ms: Optional[int]
    summary: Optional[str]
    pid: Optional[int]
    exit_code: Optional[int]
    command: Optional[str]


@dataclass
class FailurePattern:
    """Represents a persistent failure pattern for alerting."""
    job_name: str
    failure_count: int
    first_failure_at: datetime
    last_failure_at: datetime
    window_hours: int


class CronLogError(Exception):
    """Base exception for cron log operations."""
    pass


class CronLog:
    """Central cron log database for job tracking and reliability."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database directory and schema exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def log_start(
        self,
        job_name: str,
        command: Optional[str] = None,
        pid: Optional[int] = None,
        cleanup: bool = True
    ) -> int:
        """
        Record the start of a job execution.

        Args:
            job_name: Unique identifier for the job
            command: The command being executed (optional)
            pid: Process ID of the running job (optional)
            cleanup: Whether to run stale cleanup (default: True)

        Returns:
            run_id: Unique identifier for this execution
        """
        # Auto-cleanup stale jobs before starting new ones
        if cleanup:
            self.cleanup_stale()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cron_runs (job_name, started_at, status, command, pid)
                VALUES (?, ?, 'running', ?, ?)
                """,
                (job_name, datetime.now(), command, pid)
            )
            return cursor.lastrowid

    def log_end(
        self,
        run_id: int,
        status: Literal["success", "failure", "timeout", "killed"],
        summary: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> None:
        """
        Record the completion of a job execution.

        Args:
            run_id: The run ID returned by log_start
            status: Final status of the job
            summary: Brief summary of the result (optional)
            exit_code: Process exit code (optional)
        """
        ended_at = datetime.now()

        with self._connect() as conn:
            # Get start time to calculate duration
            row = conn.execute(
                "SELECT started_at FROM cron_runs WHERE id = ?",
                (run_id,)
            ).fetchone()

            if not row:
                raise CronLogError(f"Run ID {run_id} not found")

            started_at = row["started_at"]
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at)

            duration_ms = int((ended_at - started_at).total_seconds() * 1000)

            conn.execute(
                """
                UPDATE cron_runs
                SET ended_at = ?, status = ?, duration_ms = ?, summary = ?, exit_code = ?
                WHERE id = ?
                """,
                (ended_at, status, duration_ms, summary, exit_code, run_id)
            )

    def query(
        self,
        job_name: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CronRun]:
        """
        Query job execution history with filters.

        Args:
            job_name: Filter by job name (optional)
            status: Filter by status (optional)
            since: Filter runs after this time (optional)
            until: Filter runs before this time (optional)
            limit: Maximum number of results (default 100)
            offset: Pagination offset (default 0)

        Returns:
            List of matching CronRun records
        """
        conditions = []
        params = []

        if job_name:
            conditions.append("job_name = ?")
            params.append(job_name)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if since:
            conditions.append("started_at >= ?")
            params.append(since)
        if until:
            conditions.append("started_at <= ?")
            params.append(until)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM cron_runs
                {where_clause}
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset]
            )

            return [self._row_to_run(row) for row in cursor.fetchall()]

    def get_last_run(self, job_name: str) -> Optional[CronRun]:
        """Get the most recent run for a specific job."""
        runs = self.query(job_name=job_name, limit=1)
        return runs[0] if runs else None

    def should_run(
        self,
        job_name: str,
        interval: Literal["once", "hourly", "daily"] = "daily"
    ) -> bool:
        """
        Idempotency check - determine if job should run based on last success.

        Args:
            job_name: Name of the job to check
            interval: How often the job should run (once/hourly/daily)

        Returns:
            True if job should run, False if it already succeeded in this interval
        """
        last_run = self.get_last_run(job_name)

        if not last_run or last_run.status != "success":
            return True

        now = datetime.now()
        last_success = last_run.ended_at or last_run.started_at

        if isinstance(last_success, str):
            last_success = datetime.fromisoformat(last_success)

        if interval == "once":
            return False  # Already succeeded once
        elif interval == "hourly":
            # Check if we're in a different hour
            return (now.year, now.month, now.day, now.hour) != \
                   (last_success.year, last_success.month, last_success.day, last_success.hour)
        elif interval == "daily":
            # Check if we're on a different day
            return (now.year, now.month, now.day) != \
                   (last_success.year, last_success.month, last_success.day)
        else:
            return True

    def cleanup_stale(self, timeout_minutes: int = RUNNING_TIMEOUT_MINUTES) -> int:
        """
        Mark jobs stuck in "running" state as stale.

        Args:
            timeout_minutes: How long a job can be running before marked stale

        Returns:
            Number of stale jobs marked
        """
        cutoff = datetime.now() - timedelta(minutes=timeout_minutes)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE cron_runs
                SET status = 'stale', ended_at = started_at
                WHERE status = 'running' AND started_at < ?
                """,
                (cutoff,)
            )
            return cursor.rowcount

    def detect_persistent_failures(
        self,
        window_hours: int = FAILURE_WINDOW_HOURS,
        threshold: int = FAILURE_THRESHOLD
    ) -> List[FailurePattern]:
        """
        Detect jobs that have failed multiple times within a time window.

        Args:
            window_hours: Time window to look for failures
            threshold: Number of failures to trigger alert

        Returns:
            List of jobs with persistent failure patterns
        """
        since = datetime.now() - timedelta(hours=window_hours)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT
                    job_name,
                    COUNT(*) as failure_count,
                    MIN(started_at) as first_failure_at,
                    MAX(started_at) as last_failure_at
                FROM cron_runs
                WHERE status = 'failure' AND started_at >= ?
                GROUP BY job_name
                HAVING failure_count >= ?
                ORDER BY failure_count DESC
                """,
                (since, threshold)
            )

            patterns = []
            for row in cursor.fetchall():
                first_at = row["first_failure_at"]
                last_at = row["last_failure_at"]
                if isinstance(first_at, str):
                    first_at = datetime.fromisoformat(first_at)
                if isinstance(last_at, str):
                    last_at = datetime.fromisoformat(last_at)
                patterns.append(FailurePattern(
                    job_name=row["job_name"],
                    failure_count=row["failure_count"],
                    first_failure_at=first_at,
                    last_failure_at=last_at,
                    window_hours=window_hours
                ))
            return patterns

    def get_stats(
        self,
        since: Optional[datetime] = None,
        job_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get execution statistics."""
        since = since or datetime.now() - timedelta(days=7)

        conditions = ["started_at >= ?"]
        params = [since]

        if job_name:
            conditions.append("job_name = ?")
            params.append(job_name)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                SELECT
                    status,
                    COUNT(*) as count,
                    AVG(duration_ms) as avg_duration,
                    MIN(duration_ms) as min_duration,
                    MAX(duration_ms) as max_duration
                FROM cron_runs
                {where_clause}
                GROUP BY status
                """,
                params
            )

            stats = {
                "by_status": {},
                "total_runs": 0,
                "period": {"since": since.isoformat(), "until": datetime.now().isoformat()}
            }

            for row in cursor.fetchall():
                status = row["status"]
                count = row["count"]
                stats["by_status"][status] = {
                    "count": count,
                    "avg_duration_ms": row["avg_duration"],
                    "min_duration_ms": row["min_duration"],
                    "max_duration_ms": row["max_duration"]
                }
                stats["total_runs"] += count

            return stats

    def _row_to_run(self, row: sqlite3.Row) -> CronRun:
        """Convert a database row to a CronRun object."""
        started_at = row["started_at"]
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)

        ended_at = row["ended_at"]
        if isinstance(ended_at, str):
            ended_at = datetime.fromisoformat(ended_at) if ended_at else None

        return CronRun(
            id=row["id"],
            job_name=row["job_name"],
            started_at=started_at,
            ended_at=ended_at,
            status=row["status"],
            duration_ms=row["duration_ms"],
            summary=row["summary"],
            pid=row["pid"],
            exit_code=row["exit_code"],
            command=row["command"]
        )


# Database schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS cron_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failure', 'timeout', 'killed', 'stale')),
    duration_ms INTEGER,
    summary TEXT,
    pid INTEGER,
    exit_code INTEGER,
    command TEXT
);

CREATE INDEX IF NOT EXISTS idx_cron_runs_job_name ON cron_runs(job_name);
CREATE INDEX IF NOT EXISTS idx_cron_runs_status ON cron_runs(status);
CREATE INDEX IF NOT EXISTS idx_cron_runs_started_at ON cron_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_cron_runs_composite ON cron_runs(job_name, status, started_at);
"""


# CLI interface for direct usage
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Cron log database CLI")
    subparsers = parser.add_subparsers(dest="cmd", help="Commands")

    # log-start
    start_parser = subparsers.add_parser("log-start", help="Record job start")
    start_parser.add_argument("job_name", help="Job name")
    start_parser.add_argument("--command", dest="cmd_str", help="Command being executed")
    start_parser.add_argument("--pid", type=int, help="Process ID")

    # log-end
    end_parser = subparsers.add_parser("log-end", help="Record job end")
    end_parser.add_argument("run_id", type=int, help="Run ID from log-start")
    end_parser.add_argument("status", choices=["success", "failure", "timeout", "killed"], help="Final status")
    end_parser.add_argument("--summary", help="Result summary")
    end_parser.add_argument("--exit-code", type=int, help="Exit code")

    # query
    query_parser = subparsers.add_parser("query", help="Query job history")
    query_parser.add_argument("--job-name", help="Filter by job name")
    query_parser.add_argument("--status", help="Filter by status")
    query_parser.add_argument("--since", help="Filter since timestamp (ISO format)")
    query_parser.add_argument("--until", help="Filter until timestamp (ISO format)")
    query_parser.add_argument("--limit", type=int, default=100, help="Limit results")

    # should-run
    should_run_parser = subparsers.add_parser("should-run", help="Check if job should run")
    should_run_parser.add_argument("job_name", help="Job name")
    should_run_parser.add_argument("--interval", choices=["once", "hourly", "daily"], default="daily", help="Interval")

    # cleanup-stale
    subparsers.add_parser("cleanup-stale", help="Mark stale jobs as failed")

    # detect-failures
    failures_parser = subparsers.add_parser("detect-failures", help="Detect persistent failures")
    failures_parser.add_argument("--window-hours", type=int, default=FAILURE_WINDOW_HOURS, help="Time window")
    failures_parser.add_argument("--threshold", type=int, default=FAILURE_THRESHOLD, help="Failure threshold")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--job-name", help="Filter by job name")
    stats_parser.add_argument("--since", help="Since timestamp (ISO format)")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    log = CronLog()

    try:
        if args.cmd == "log-start":
            run_id = log.log_start(args.job_name, args.cmd_str, args.pid)
            print(run_id)

        elif args.cmd == "log-end":
            log.log_end(args.run_id, args.status, args.summary, args.exit_code)
            print(f"Run {args.run_id} marked as {args.status}")

        elif args.cmd == "query":
            since = datetime.fromisoformat(args.since) if args.since else None
            until = datetime.fromisoformat(args.until) if args.until else None
            runs = log.query(args.job_name, args.status, since, until, args.limit)
            for run in runs:
                print(json.dumps(asdict(run), indent=2, default=str))

        elif args.cmd == "should-run":
            should = log.should_run(args.job_name, args.interval)
            print("yes" if should else "no")
            sys.exit(0 if should else 1)

        elif args.cmd == "cleanup-stale":
            count = log.cleanup_stale()
            print(f"Marked {count} stale jobs as failed")

        elif args.cmd == "detect-failures":
            patterns = log.detect_persistent_failures(args.window_hours, args.threshold)
            if patterns:
                for p in patterns:
                    print(f"ALERT: Job '{p.job_name}' failed {p.failure_count} times in {p.window_hours}h")
                sys.exit(1)
            else:
                print("No persistent failures detected")

        elif args.cmd == "stats":
            since = datetime.fromisoformat(args.since) if args.since else None
            stats = log.get_stats(since, args.job_name)
            print(json.dumps(stats, indent=2, default=str))

    except CronLogError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
