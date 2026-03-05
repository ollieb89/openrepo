#!/usr/bin/env python3
"""
Health checker for cron automation system.

Runs on a regular interval (e.g., every 30 minutes) to:
- Detect persistent failures (3+ failures within 6-hour window)
- Send alerts for failing jobs
- Check overall system health
- Report job statistics
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from cronlog import CronLog, FailurePattern


# Default configuration
DEFAULT_INTERVAL_MINUTES = 30
DEFAULT_FAILURE_WINDOW_HOURS = 6
DEFAULT_FAILURE_THRESHOLD = 3


class HealthCheckError(Exception):
    """Base exception for health check errors."""
    pass


class HealthChecker:
    """Health checker for cron automation system."""

    def __init__(
        self,
        log: Optional[CronLog] = None,
        failure_window_hours: int = DEFAULT_FAILURE_WINDOW_HOURS,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD
    ):
        self.log = log or CronLog()
        self.failure_window_hours = failure_window_hours
        self.failure_threshold = failure_threshold
        self.alerts: List[Dict[str, Any]] = []

    def check_persistent_failures(self) -> List[FailurePattern]:
        """
        Detect jobs with persistent failures.

        Returns:
            List of failure patterns that exceed the threshold
        """
        patterns = self.log.detect_persistent_failures(
            window_hours=self.failure_window_hours,
            threshold=self.failure_threshold
        )

        for pattern in patterns:
            self.alerts.append({
                "type": "persistent_failure",
                "severity": "error",
                "job_name": pattern.job_name,
                "message": (
                    f"Job '{pattern.job_name}' has failed {pattern.failure_count} times "
                    f"within {pattern.window_hours} hours"
                ),
                "details": {
                    "failure_count": pattern.failure_count,
                    "first_failure": pattern.first_failure_at.isoformat(),
                    "last_failure": pattern.last_failure_at.isoformat()
                },
                "timestamp": datetime.now().isoformat()
            })

        return patterns

    def check_stale_jobs(self) -> int:
        """
        Check for and cleanup stale jobs.

        Returns:
            Number of stale jobs found
        """
        count = self.log.cleanup_stale()

        if count > 0:
            self.alerts.append({
                "type": "stale_jobs",
                "severity": "warning",
                "message": f"Found and marked {count} stale job(s) as failed",
                "count": count,
                "timestamp": datetime.now().isoformat()
            })

        return count

    def check_job_health(self, job_name: str) -> Dict[str, Any]:
        """
        Check health of a specific job.

        Args:
            job_name: Name of the job to check

        Returns:
            Health status dictionary
        """
        since = datetime.now() - timedelta(hours=24)
        stats = self.log.get_stats(since=since, job_name=job_name)

        total = stats.get("total_runs", 0)
        by_status = stats.get("by_status", {})

        failures = by_status.get("failure", {}).get("count", 0)
        successes = by_status.get("success", {}).get("count", 0)
        running = by_status.get("running", {}).get("count", 0)
        timeouts = by_status.get("timeout", {}).get("count", 0)
        killed = by_status.get("killed", {}).get("count", 0)

        # Calculate success rate
        completed = successes + failures + timeouts + killed
        success_rate = (successes / completed * 100) if completed > 0 else 0

        # Determine health status
        if total == 0:
            health_status = "unknown"
        elif success_rate >= 95:
            health_status = "healthy"
        elif success_rate >= 80:
            health_status = "degraded"
        else:
            health_status = "unhealthy"

        return {
            "job_name": job_name,
            "health_status": health_status,
            "success_rate": round(success_rate, 2),
            "total_runs_24h": total,
            "successes": successes,
            "failures": failures,
            "timeouts": timeouts,
            "killed": killed,
            "running": running,
            "checked_at": datetime.now().isoformat()
        }

    def run_full_check(self) -> Dict[str, Any]:
        """
        Run all health checks.

        Returns:
            Complete health report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        # Check for stale jobs
        stale_count = self.check_stale_jobs()
        report["checks"]["stale_jobs"] = {
            "found": stale_count,
            "status": "warning" if stale_count > 0 else "ok"
        }

        # Check for persistent failures
        failures = self.check_persistent_failures()
        report["checks"]["persistent_failures"] = {
            "found": len(failures),
            "jobs": [p.job_name for p in failures],
            "status": "error" if failures else "ok"
        }

        # Get overall stats
        stats = self.log.get_stats(since=datetime.now() - timedelta(hours=24))
        report["checks"]["overall_stats"] = stats

        # Summary
        has_errors = any(a["severity"] == "error" for a in self.alerts)
        has_warnings = any(a["severity"] == "warning" for a in self.alerts)

        if has_errors:
            report["summary"] = "errors"
        elif has_warnings:
            report["summary"] = "warnings"
        else:
            report["summary"] = "healthy"

        report["alerts"] = self.alerts

        return report

    def notify(self, report: Dict[str, Any], webhook_url: Optional[str] = None) -> bool:
        """
        Send notifications for alerts.

        Args:
            report: Health report containing alerts
            webhook_url: Optional webhook URL for notifications

        Returns:
            True if notifications were sent successfully
        """
        alerts = report.get("alerts", [])

        if not alerts:
            return True

        # Print alerts to stdout (for cron mail / logging)
        for alert in alerts:
            severity = alert["severity"].upper()
            print(f"[{severity}] {alert['message']}", file=sys.stderr)

        # TODO: Implement webhook notifications, email, etc.
        # For now, alerts are logged and can be picked up by monitoring

        return True


def format_report(report: Dict[str, Any]) -> str:
    """Format health report for human reading."""
    lines = [
        "=" * 60,
        "CRON HEALTH CHECK REPORT",
        f"Generated: {report['timestamp']}",
        "=" * 60,
        ""
    ]

    # Overall status
    summary = report.get("summary", "unknown")
    status_emoji = {"healthy": "✓", "warnings": "⚠", "errors": "✗"}.get(summary, "?")
    lines.append(f"Overall Status: {status_emoji} {summary.upper()}")
    lines.append("")

    # Alerts
    alerts = report.get("alerts", [])
    if alerts:
        lines.append("ALERTS:")
        for alert in alerts:
            severity = alert["severity"].upper()
            lines.append(f"  [{severity}] {alert['message']}")
        lines.append("")

    # Stale jobs
    stale = report["checks"].get("stale_jobs", {})
    lines.append(f"Stale Jobs: {stale.get('found', 0)}")

    # Persistent failures
    failures = report["checks"].get("persistent_failures", {})
    lines.append(f"Persistent Failures: {failures.get('found', 0)}")
    if failures.get("jobs"):
        for job in failures["jobs"]:
            lines.append(f"  - {job}")

    # Stats
    stats = report["checks"].get("overall_stats", {})
    lines.append("")
    lines.append("24-Hour Statistics:")
    lines.append(f"  Total Runs: {stats.get('total_runs', 0)}")

    by_status = stats.get("by_status", {})
    for status, data in by_status.items():
        lines.append(f"  {status.capitalize()}: {data.get('count', 0)}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cron health checker")
    parser.add_argument("--check-job", help="Check specific job health")
    parser.add_argument("--webhook-url", help="Webhook URL for notifications")
    parser.add_argument("--format", choices=["json", "text"], default="text",
                        help="Output format")
    parser.add_argument("--fail-on-alerts", action="store_true",
                        help="Exit with error code if alerts found")

    args = parser.parse_args()

    checker = HealthChecker()

    try:
        if args.check_job:
            result = checker.check_job_health(args.check_job)
            if args.format == "json":
                print(json.dumps(result, indent=2))
            else:
                print(f"Job: {result['job_name']}")
                print(f"Status: {result['health_status']}")
                print(f"Success Rate: {result['success_rate']}%")
                print(f"Runs (24h): {result['total_runs_24h']}")
        else:
            report = checker.run_full_check()
            checker.notify(report, args.webhook_url)

            if args.format == "json":
                print(json.dumps(report, indent=2))
            else:
                print(format_report(report))

            if args.fail_on_alerts and report.get("alerts"):
                sys.exit(1)

    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        sys.exit(1)
