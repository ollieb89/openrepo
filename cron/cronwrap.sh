#!/usr/bin/env bash
#
# Cron Wrapper Script
# Provides reliable job execution with signal handling, locking, and logging.
#
# Usage: cronwrap.sh [options] -- <command> [args...]
#
# Options:
#   -n, --name NAME         Job name (required, used for logging and locking)
#   -t, --timeout SECONDS   Maximum execution time (0 = no timeout)
#   -l, --lock-dir DIR      Directory for PID lock files (default: /tmp/cronwrap)
#   -v, --verbose           Enable verbose output
#   -h, --help              Show this help message
#
# Environment:
#   CRONWRAP_LOCK_DIR       Default lock directory
#   CRONWRAP_LOG_DB         Path to SQLite database (default: ../logs/cron.db)
#   CRONWRAP_VERBOSE        Enable verbose mode
#
# Example:
#   cronwrap.sh -n "backup-database" -t 300 -- /usr/local/bin/backup.sh
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_DIR="${CRONWRAP_LOCK_DIR:-/tmp/cronwrap}"
LOG_DB="${CRONWRAP_LOG_DB:-${SCRIPT_DIR}/../logs/cron.db}"
VERBOSE="${CRONWRAP_VERBOSE:-0}"

# Job configuration
JOB_NAME=""
TIMEOUT=0
COMMAND=()

# Runtime state
RUN_ID=""
PID_FILE=""
START_TIME=""
CHILD_PID=""
TIMED_OUT=0
KILLED=0

# Colors for terminal output (only if stderr is a tty)
if [[ -t 2 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Logging functions
log_info() {
    if [[ "$VERBOSE" == "1" ]]; then
        echo -e "${GREEN}[INFO]${NC} $*" >&2
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Show usage information
usage() {
    sed -n '4,22p' "$0" | sed 's/^# //'
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--name)
                JOB_NAME="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -l|--lock-dir)
                LOCK_DIR="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --)
                shift
                COMMAND=("$@")
                break
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$JOB_NAME" ]]; then
        log_error "Job name is required (--name)"
        usage
        exit 1
    fi

    if [[ ${#COMMAND[@]} -eq 0 ]]; then
        log_error "Command is required (use -- before command)"
        usage
        exit 1
    fi
}

# Acquire lock using PID file
acquire_lock() {
    mkdir -p "$LOCK_DIR"
    PID_FILE="${LOCK_DIR}/${JOB_NAME}.pid"

    if [[ -f "$PID_FILE" ]]; then
        local old_pid
        old_pid=$(cat "$PID_FILE" 2>/dev/null) || true

        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            log_error "Job '$JOB_NAME' is already running (PID: $old_pid)"
            exit 2
        else
            log_warn "Removing stale lock file for '$JOB_NAME' (old PID: $old_pid)"
            rm -f "$PID_FILE"
        fi
    fi

    echo $$ > "$PID_FILE"
    log_info "Acquired lock: $PID_FILE"
}

# Release lock
release_lock() {
    if [[ -n "$PID_FILE" && -f "$PID_FILE" ]]; then
        rm -f "$PID_FILE"
        log_info "Released lock: $PID_FILE"
    fi
}

# Log job start to database
log_start() {
    local cmd_str
    local output
    cmd_str="${COMMAND[*]}"

    if [[ -f "$SCRIPT_DIR/cronlog.py" ]]; then
        output=$(python3 "$SCRIPT_DIR/cronlog.py" log-start "$JOB_NAME" --command "$cmd_str" --pid $$ 2>&1) || {
            log_warn "Failed to log job start: $output"
            RUN_ID=""
            return
        }
        # Extract just the numeric run_id (last line, ignoring warnings)
        RUN_ID=$(echo "$output" | tail -1 | tr -d '[:space:]')
        if [[ -n "$RUN_ID" && "$RUN_ID" =~ ^[0-9]+$ ]]; then
            log_info "Logged start: run_id=$RUN_ID"
        else
            log_warn "Invalid run_id from cronlog, output was: $output"
            RUN_ID=""
        fi
    else
        log_warn "cronlog.py not found, database logging disabled"
        RUN_ID=""
    fi
}

# Log job end to database
log_end() {
    local status="$1"
    local summary="${2:-}"
    local exit_code="${3:-}"

    if [[ -f "$SCRIPT_DIR/cronlog.py" && -n "$RUN_ID" && "$RUN_ID" =~ ^[0-9]+$ ]]; then
        python3 "$SCRIPT_DIR/cronlog.py" log-end "$RUN_ID" "$status" \
            --summary "$summary" \
            --exit-code "$exit_code" 2>/dev/null || true
        log_info "Logged end: status=$status, exit_code=$exit_code"
    else
        log_info "Skipping log-end (no valid run_id)"
    fi
}

# Signal handlers
cleanup() {
    local signal="$1"
    log_warn "Received signal: $signal"
    KILLED=1

    # Kill child process if running
    if [[ -n "$CHILD_PID" ]] && kill -0 "$CHILD_PID" 2>/dev/null; then
        log_info "Terminating child process: $CHILD_PID"
        kill -TERM "$CHILD_PID" 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if kill -0 "$CHILD_PID" 2>/dev/null; then
            kill -KILL "$CHILD_PID" 2>/dev/null || true
        fi
    fi

    release_lock
}

# Timeout handler
timeout_handler() {
    log_warn "Job timed out after ${TIMEOUT}s"
    TIMED_OUT=1

    if [[ -n "$CHILD_PID" ]] && kill -0 "$CHILD_PID" 2>/dev/null; then
        log_info "Sending SIGTERM to child process"
        kill -TERM "$CHILD_PID" 2>/dev/null || true
        sleep 5
        # Force kill if still running
        if kill -0 "$CHILD_PID" 2>/dev/null; then
            log_warn "Force killing child process"
            kill -KILL "$CHILD_PID" 2>/dev/null || true
        fi
    fi
}

# Setup signal traps
setup_traps() {
    trap 'cleanup SIGTERM' SIGTERM
    trap 'cleanup SIGINT' SIGINT
    trap 'cleanup SIGHUP' SIGHUP
}

# Execute command with optional timeout
execute_command() {
    local exit_code=0

    log_info "Executing: ${COMMAND[*]}"
    START_TIME=$(date +%s)

    if [[ "$TIMEOUT" -gt 0 ]]; then
        log_info "Timeout set: ${TIMEOUT}s"

        # Start command in background
        "${COMMAND[@]}" &
        CHILD_PID=$!

        # Setup timeout watchdog
        (
            sleep "$TIMEOUT"
            if kill -0 $$ 2>/dev/null; then
                kill -USR1 $$ 2>/dev/null || true
            fi
        ) &
        local watchdog_pid=$!

        # Setup USR1 handler for timeout
        trap 'timeout_handler' SIGUSR1

        # Wait for child
        wait "$CHILD_PID" 2>/dev/null || true
        exit_code=$?

        # Kill watchdog
        kill "$watchdog_pid" 2>/dev/null || true
        wait "$watchdog_pid" 2>/dev/null || true
    else
        # No timeout - run directly
        "${COMMAND[@]}" &
        CHILD_PID=$!
        wait "$CHILD_PID"
        exit_code=$?
    fi

    return $exit_code
}

# Calculate duration
calculate_duration() {
    local end_time=$(date +%s)
    echo $((end_time - START_TIME))
}

# Format duration for human reading
format_duration() {
    local seconds="$1"
    if [[ $seconds -lt 60 ]]; then
        echo "${seconds}s"
    elif [[ $seconds -lt 3600 ]]; then
        local mins=$((seconds / 60))
        local secs=$((seconds % 60))
        echo "${mins}m ${secs}s"
    else
        local hours=$((seconds / 3600))
        local mins=$(((seconds % 3600) / 60))
        echo "${hours}h ${mins}m"
    fi
}

# Main execution
main() {
    parse_args "$@"
    setup_traps
    acquire_lock

    # Log start
    log_start

    # Execute command
    local exit_code=0
    local status="success"
    local summary=""

    # Execute and capture exit code (don't use 'if !' due to set -e)
    execute_command || exit_code=$?

    local duration
    duration=$(calculate_duration)

    # Determine final status
    if [[ "$TIMED_OUT" == "1" ]]; then
        status="timeout"
        summary="Job timed out after $(format_duration $duration)"
        exit_code=124
    elif [[ "$KILLED" == "1" ]]; then
        status="killed"
        summary="Job terminated by signal"
        exit_code=130
    elif [[ "$exit_code" -ne 0 ]]; then
        status="failure"
        summary="Job failed with exit code $exit_code after $(format_duration $duration)"
    else
        summary="Job completed successfully in $(format_duration $duration)"
    fi

    # Log end
    log_end "$status" "$summary" "$exit_code"

    # Final output
    if [[ "$VERBOSE" == "1" || "$status" != "success" ]]; then
        echo "[$JOB_NAME] $summary" >&2
    fi

    # Cleanup
    release_lock

    exit "$exit_code"
}

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
