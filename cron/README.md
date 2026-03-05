# OpenClaw Cron Automation System

A comprehensive cron automation system with central logging, reliable execution, and persistent failure detection.

> **Note:** Examples in this document use `$OPENCLAW_ROOT` to refer to your OpenClaw
> installation directory. Set this environment variable or replace it with the actual
> path (e.g., `/home/ob/Development/Tools/openrepo`).

## Features

### Core Components

1. **Central Cron Log Database (SQLite)**
   - `log-start`: Record job name, start time, return run ID
   - `log-end`: Record completion with status, duration, summary
   - `query`: Filter history by job name, status, date range
   - `should-run`: Idempotency check (skip if already succeeded today/this hour)
   - `cleanup-stale`: Auto-mark jobs stuck in "running" state for >2 hours as failed

2. **Cron Wrapper Script** (`cronwrap.sh`)
   - Signal traps (SIGTERM/SIGINT/SIGHUP) for clean shutdown
   - PID-based lockfile to prevent concurrent runs of the same job
   - Optional timeout support
   - Integrates with the cron log for start/end recording

3. **Job Configuration** (`jobs.json`)
   - Structured payloads with cron expressions
   - Notification delivery configuration
   - Environment variables and working directory
   - Idempotency and interval checks

4. **Reliability Features**
   - **Persistent failure detection**: Alert when same job fails 3+ times within 6 hours
   - **Health check**: Regular interval monitoring (every 30 minutes)
   - **Duplicate run prevention**: PID files ensure single execution
   - **Stale job cleanup**: Automatically runs on every new job start

## Quick Start

### 1. Add a Job

```bash
./cron/manager.py job add cleanup-logs "Log Cleanup" "find /logs -mtime +30 -delete" \
    --cron "0 2 * * 0" --tag maintenance --timeout 3600
```

### 2. List Jobs

```bash
./cron/manager.py job list
```

### 3. Generate Crontab

```bash
./cron/manager.py crontab
```

### 4. Install Crontab

```bash
./cron/manager.py crontab --install
```

### 5. Check Health

```bash
./cron/manager.py health check
```

## CLI Reference

### Manager CLI (`manager.py`)

Unified interface for all cron operations:

```bash
# Status overview
./cron/manager.py status

# Job management
./cron/manager.py job list
./cron/manager.py job add <id> <name> <command> --cron "0 * * * *"
./cron/manager.py job remove <id>
./cron/manager.py job run <id> [--force]
./cron/manager.py job enable <id>
./cron/manager.py job disable <id>

# Log operations
./cron/manager.py log query [--job <name>] [--status <status>] [--limit <n>]
./cron/manager.py log start <job_name> [--command <cmd>] [--pid <pid>]
./cron/manager.py log end <run_id> <status> [--summary <text>] [--exit-code <n>]
./cron/manager.py log should-run <job_name> [--interval daily|hourly|once]
./cron/manager.py log cleanup

# Health monitoring
./cron/manager.py health check [--format json|text] [--fail-on-alerts]
./cron/manager.py health job <id> [--format json|text]

# Crontab
./cron/manager.py crontab [--generate]
./cron/manager.py crontab --install
./cron/manager.py crontab --validate
```

### Cron Log CLI (`cronlog.py`)

Direct database operations:

```bash
# Start a job (returns run_id)
./cron/cronlog.py log-start <job_name> [--command <cmd>] [--pid <pid>]

# End a job
./cron/cronlog.py log-end <run_id> <success|failure|timeout|killed> \
    [--summary <text>] [--exit-code <n>]

# Query history
./cron/cronlog.py query [--job-name <name>] [--status <status>] \
    [--since <iso>] [--until <iso>] [--limit <n>]

# Check if job should run (idempotency)
./cron/cronlog.py should-run <job_name> [--interval once|hourly|daily]

# Cleanup stale jobs
./cron/cronlog.py cleanup-stale

# Detect persistent failures
./cron/cronlog.py detect-failures [--window-hours <n>] [--threshold <n>]

# Show statistics
./cron/cronlog.py stats [--job-name <name>] [--since <iso>]
```

### Cron Wrapper (`cronwrap.sh`)

Reliable job execution wrapper:

```bash
./cron/cronwrap.sh -n <job_name> [-t <timeout>] -- <command> [args...]

Options:
  -n, --name NAME         Job name (required, used for logging/locking)
  -t, --timeout SECONDS   Maximum execution time (0 = no timeout)
  -l, --lock-dir DIR      Directory for PID lock files
  -v, --verbose           Enable verbose output
  -h, --help              Show help
```

### Health Checker (`healthcheck.py`)

System health monitoring:

```bash
# Full health check
./cron/healthcheck.py [--format json|text] [--fail-on-alerts]

# Check specific job
./cron/healthcheck.py --check-job <job_id> [--format json|text]

# Webhook notifications
./cron/healthcheck.py --webhook-url <url>
```

### Scheduler (`scheduler.py`)

Job configuration management:

```bash
# List jobs
./cron/scheduler.py list [--enabled-only] [--format table|json]

# Add job
./cron/scheduler.py add <id> <name> <command> --cron "0 * * * *" \
    [--timeout <n>] [--description <text>] [--tag <tag>]

# Remove job
./cron/scheduler.py remove <id>

# Generate crontab
./cron/scheduler.py crontab [--install] [--user]

# Validate
./cron/scheduler.py validate
```

## Job Configuration Schema

Jobs are defined in `jobs.json`:

```json
{
  "id": "unique-job-id",
  "name": "Human Readable Name",
  "enabled": true,
  "command": "/path/to/command",
  "args": ["arg1", "arg2"],
  "schedule": {
    "cron": "0 2 * * *",
    "timezone": "UTC",
    "skip_if_running": true,
    "idempotent": true,
    "interval_check": "daily"
  },
  "timeout": 3600,
  "working_dir": "/path/to/workdir",
  "environment": {"VAR": "value"},
  "notifications": {
    "enabled": true,
    "on_success": false,
    "on_failure": true,
    "channels": ["log"],
    "webhook_url": null
  },
  "log_output": true,
  "description": "What this job does",
  "tags": ["maintenance", "backup"]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique job identifier |
| `name` | string | Human-readable name |
| `enabled` | boolean | Whether job is active |
| `command` | string | Command to execute |
| `args` | array | Command arguments |
| `schedule.cron` | string | 5-field cron expression |
| `schedule.timezone` | string | Timezone for scheduling |
| `schedule.skip_if_running` | boolean | Prevent concurrent runs via lock |
| `schedule.idempotent` | boolean | Use should-run check |
| `schedule.interval_check` | string | Idempotency interval |
| `timeout` | integer | Max execution time in seconds |
| `working_dir` | string | Working directory |
| `environment` | object | Environment variables |
| `notifications.enabled` | boolean | Enable notifications |
| `notifications.on_success` | boolean | Notify on success |
| `notifications.on_failure` | boolean | Notify on failure |
| `notifications.channels` | array | Notification channels |
| `log_output` | boolean | Log command output |
| `description` | string | Job description |
| `tags` | array | Job categorization |

## Reliability Features

### 1. Duplicate Run Prevention

The wrapper script uses PID files to prevent concurrent execution:

```bash
./cron/cronwrap.sh -n backup -- /usr/local/bin/backup.sh
# Second concurrent run will exit with code 2
```

### 2. Idempotency Checks

Jobs can be configured to skip if already succeeded:

```bash
# Check if job should run based on last success
./cron/cronlog.py should-run daily-backup --interval daily
# Returns exit code 1 if already succeeded today
```

### 3. Stale Job Detection

Jobs stuck in "running" state for >2 hours are auto-marked as stale:

```bash
./cron/cronlog.py cleanup-stale
```

### 4. Persistent Failure Detection

Alerts when a job fails 3+ times within 6 hours:

```bash
./cron/cronlog.py detect-failures
# Or via health check
./cron/healthcheck.py --fail-on-alerts
```

### 5. Signal Handling

The wrapper properly handles signals for clean shutdown:
- SIGTERM: Graceful termination
- SIGINT: Interrupt (Ctrl+C)
- SIGHUP: Hangup

## Database Schema

The SQLite database (`logs/cron.db`) contains:

```sql
CREATE TABLE cron_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status TEXT NOT NULL,  -- running|success|failure|timeout|killed|stale
    duration_ms INTEGER,
    summary TEXT,
    pid INTEGER,
    exit_code INTEGER,
    command TEXT
);
```

Indexed fields: `job_name`, `status`, `started_at`

## Examples

### Example 1: Database Backup Job

```bash
# Add the job
./cron/manager.py job add db-backup "Database Backup" \
    "/usr/local/bin/pg_dump" \
    --cron "0 3 * * *" \
    --timeout 1800 \
    --description "Daily database backup" \
    --tag backup

# Run manually (for testing)
./cron/manager.py job run db-backup

# Check status
./cron/manager.py log query --job db-backup --limit 5
```

### Example 2: Health Monitoring

```bash
# Add health check job to run every 30 minutes
./cron/manager.py job add health-monitor "Health Monitor" \
    "python3 $OPENCLAW_ROOT/cron/healthcheck.py --fail-on-alerts" \
    --cron "*/30 * * * *" \
    --timeout 60

# Run health check manually
./cron/manager.py health check
```

### Example 3: Log Cleanup

```bash
# Add weekly log cleanup
./cron/manager.py job add cleanup "Log Cleanup" \
    "find /var/log/openclaw -name '*.log' -mtime +30 -delete" \
    --cron "0 2 * * 0" \
    --tag maintenance

# Check if job should run (idempotency)
./cron/manager.py log should-run cleanup --interval once
```

### Example 4: Direct Wrapper Usage

```bash
# Using cronwrap directly in crontab
* * * * * $OPENCLAW_ROOT/cron/cronwrap.sh \
    -n my-job -t 300 -- /path/to/script.sh

# Or with idempotency check
* * * * * $OPENCLAW_ROOT/cron/cronlog.py should-run my-job \
    && $OPENCLAW_ROOT/cron/cronwrap.sh -n my-job -- /path/to/script.sh
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CRONWRAP_LOCK_DIR` | PID lock directory | `/tmp/cronwrap` |
| `CRONWRAP_LOG_DB` | SQLite database path | `../logs/cron.db` |
| `CRONWRAP_VERBOSE` | Enable verbose output | `0` |

## Exit Codes

### Wrapper Script (`cronwrap.sh`)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Job already running (lock) |
| 124 | Timeout |
| 130 | Killed by signal |

### CLI Tools

| Code | Meaning |
|------|---------|
| 0 | Success / Should run |
| 1 | Error / Should not run (idempotency) |
| 2 | Persistent failures detected |

## Testing

Run the test suite:

```bash
# Test database operations
python3 -c "from cron.cronlog import CronLog; l = CronLog(); print(l.get_stats())"

# Test wrapper with a simple command
./cron/cronwrap.sh -n test-job -v -- echo "Hello World"

# Test health check
./cron/healthcheck.py

# Validate job configuration
./cron/manager.py crontab --validate
```

## Troubleshooting

### Job not running

1. Check if job is enabled: `./cron/manager.py job list`
2. Check logs: `./cron/manager.py log query --job <id>`
3. Check idempotency: `./cron/manager.py log should-run <id>`
4. Check for locks: `ls /tmp/cronwrap/`

### Duplicate runs

1. Verify `skip_if_running: true` in job config
2. Check lock directory: `ls -la $CRONWRAP_LOCK_DIR`
3. Clear stale locks: `rm /tmp/cronwrap/<job_id>.pid`

### Database issues

1. Check database exists: `ls -la logs/cron.db`
2. Verify permissions
3. Test query: `./cron/cronlog.py query --limit 1`

## Integration with Agent Framework

The cron system integrates with the OpenClaw agent framework:

1. Jobs are configured in `cron/jobs.json`
2. The scheduler generates crontab entries
3. Wrapper ensures reliable execution with logging
4. Health checker reports to agent monitoring
5. Persistent failures trigger agent alerts

Example agent notification payload:

```json
{
  "type": "persistent_failure",
  "severity": "error",
  "job_name": "backup-database",
  "message": "Job 'backup-database' has failed 5 times within 6 hours",
  "timestamp": "2026-03-02T21:00:00Z"
}
```
