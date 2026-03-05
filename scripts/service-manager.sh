#!/bin/bash
# OpenRepo Service Manager
# Manages various service types: next-dev, node, python, docker, make

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCRIPT_PID=$$
SCRIPT_PPID=$PPID

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if PID is this script or its parent (don't kill ourselves)
is_self_or_parent() {
    local pid="$1"
    if [ "$pid" = "$SCRIPT_PID" ] || [ "$pid" = "$SCRIPT_PPID" ]; then
        return 0
    fi
    # Check if it's a parent process (make, bash, etc. running this script)
    local ppid_check=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
    if [ "$ppid_check" = "$SCRIPT_PID" ] || [ "$ppid_check" = "$SCRIPT_PPID" ]; then
        return 0
    fi
    return 1
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
OpenRepo Service Manager

Usage: $(basename "$0") <command> [service-type]

Commands:
    stop    Stop services by type
    list    List running services
    kill    Force kill services by type (SIGKILL)
    clean   Stop services + clear caches

Service Types:
    all         All known service types
    next        Next.js dev servers
    node        All Node.js processes
    python      Python processes (uvicorn, python scripts)
    docker      Docker containers
    make        Make processes
    pnpm        PNPM/npm processes
    port:<n>    Process on specific port

Examples:
    $(basename "$0") stop all          # Stop all services
    $(basename "$0") stop next         # Stop Next.js dev servers
    $(basename "$0") stop port:6987    # Stop process on port 6987
    $(basename "$0") list              # Show all running services
    $(basename "$0") clean next        # Stop Next.js + clear cache

EOF
}

# Find processes by pattern
find_processes() {
    local pattern="$1"
    pgrep -f "$pattern" 2>/dev/null || true
}

# Get process details
get_process_info() {
    local pid="$1"
    ps -p "$pid" -o pid,ppid,cmd --no-headers 2>/dev/null || echo ""
}

# Stop Next.js dev servers
stop_next() {
    log_info "Stopping Next.js servers..."
    local pids=$(find_processes "next dev")
    # Also catch next-server processes
    local server_pids=$(find_processes "next-server")
    if [ -n "$server_pids" ]; then
        pids="$pids $server_pids"
    fi
    if [ -n "$pids" ]; then
        echo "$pids" | xargs -r kill -TERM 2>/dev/null || true
        sleep 1
        # Force kill if still running
        local remaining=$(find_processes "next dev")
        if [ -n "$remaining" ]; then
            echo "$remaining" | xargs -r kill -KILL 2>/dev/null || true
        fi
        log_success "Next.js servers stopped"
    else
        log_warn "No Next.js servers found"
    fi
}

# Stop Node.js processes
stop_node() {
    log_info "Stopping Node.js processes..."
    local pids=$(find_processes "node")
    if [ -n "$pids" ]; then
        # Exclude system node processes (vscode, etc)
        local to_kill=""
        while IFS= read -r pid; do
            local cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
            if [[ "$cmdline" == *"next"* ]] || [[ "$cmdline" == *"pnpm"* ]] || [[ "$cmdline" == *"dashboard"* ]]; then
                to_kill="$to_kill $pid"
            fi
        done <<< "$pids"
        
        if [ -n "$to_kill" ]; then
            echo "$to_kill" | xargs -r kill -TERM 2>/dev/null || true
            sleep 1
            log_success "Node.js processes stopped"
        else
            log_warn "No matching Node.js processes found"
        fi
    else
        log_warn "No Node.js processes found"
    fi
}

# Stop Python processes
stop_python() {
    log_info "Stopping Python processes..."
    local pids=$(find_processes "python3")
    if [ -n "$pids" ]; then
        # Only kill project-related Python processes
        local to_kill=""
        while IFS= read -r pid; do
            local cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
            if [[ "$cmdline" == *"openrepo"* ]] || [[ "$cmdline" == *"uvicorn"* ]] || [[ "$cmdline" == *"fastapi"* ]]; then
                to_kill="$to_kill $pid"
            fi
        done <<< "$pids"
        
        if [ -n "$to_kill" ]; then
            echo "$to_kill" | xargs -r kill -TERM 2>/dev/null || true
            sleep 1
            log_success "Python processes stopped"
        else
            log_warn "No matching Python processes found"
        fi
    else
        log_warn "No Python processes found"
    fi
}

# Stop Docker containers (optional - memU is infrastructure)
stop_docker() {
    log_info "Checking Docker containers..."
    if command -v docker &> /dev/null; then
        local containers=$(docker ps -q --filter "name=openclaw" 2>/dev/null)
        if [ -n "$containers" ]; then
            log_warn "OpenClaw containers running (memU). Use 'make memory-down' to stop infrastructure."
            docker ps --filter "name=openclaw" --format "  - {{.Names}} ({{.Status}})"
        else
            log_info "No OpenClaw containers running"
        fi
    else
        log_warn "Docker not available"
    fi
}

# Stop make processes
stop_make() {
    log_info "Stopping make processes..."
    local pids=$(find_processes "^make")
    local to_kill=""
    
    # Filter out this script and its parents
    while IFS= read -r pid; do
        [ -z "$pid" ] && continue
        if ! is_self_or_parent "$pid"; then
            to_kill="$to_kill $pid"
        fi
    done <<< "$pids"
    
    if [ -n "$to_kill" ]; then
        echo "$to_kill" | xargs -r kill -TERM 2>/dev/null || true
        sleep 1
        log_success "Make processes stopped"
    else
        log_warn "No make processes found (excluding current process)"
    fi
}

# Stop pnpm/npm processes
stop_pnpm() {
    log_info "Stopping pnpm/npm processes..."
    local pids=$(find_processes "pnpm")
    if [ -n "$pids" ]; then
        echo "$pids" | xargs -r kill -TERM 2>/dev/null || true
        sleep 1
        log_success "pnpm processes stopped"
    else
        log_warn "No pnpm processes found"
    fi
}

# Stop process on specific port
stop_port() {
    local port="$1"
    log_info "Stopping process on port $port..."
    
    if command -v lsof &> /dev/null; then
        local pid=$(lsof -t -i:$port 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            # Check if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
            log_success "Process on port $port stopped (PID: $pid)"
        else
            log_warn "No process found on port $port"
        fi
    else
        log_error "lsof not available"
    fi
}

# List all running services
list_services() {
    log_info "Listing running services..."
    echo ""
    
    echo "=== Next.js Processes ==="
    pgrep -f "next dev" -a 2>/dev/null || echo "  None"
    echo ""
    
    echo "=== Make Processes ==="
    pgrep -f "^make" -a 2>/dev/null || echo "  None"
    echo ""
    
    echo "=== Node Processes (project-related) ==="
    ps aux | grep -E "(next|pnpm|node.*dashboard)" | grep -v grep || echo "  None"
    echo ""
    
    echo "=== Python Processes (project-related) ==="
    ps aux | grep -E "python3.*openrepo" | grep -v grep || echo "  None"
    echo ""
    
    echo "=== Docker Containers ==="
    if command -v docker &> /dev/null; then
        docker ps --filter "name=openclaw" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  None"
    else
        echo "  Docker not available"
    fi
    echo ""
    
    echo "=== Active Ports ==="
    if command -v lsof &> /dev/null; then
        lsof -i -P -n | grep LISTEN | grep -E "(:6987|:3000|:8000|:8080)" || echo "  No project ports active"
    else
        echo "  lsof not available"
    fi
}

# Clear Next.js cache
clear_next_cache() {
    log_info "Clearing Next.js cache..."
    if [ -d "$PROJECT_ROOT/packages/dashboard/.next" ]; then
        rm -rf "$PROJECT_ROOT/packages/dashboard/.next"
        rm -f "$PROJECT_ROOT/packages/dashboard/tsconfig.tsbuildinfo"
        log_success "Next.js cache cleared"
    else
        log_warn "No Next.js cache found"
    fi
}

# Stop all dev services (not infrastructure)
stop_all() {
    log_info "Stopping all dev services..."
    stop_make
    stop_next
    stop_pnpm
    stop_python
    log_info "Note: Infrastructure (memU Docker) not stopped. Use 'make memory-down' if needed."
    log_success "All dev services stopped"
}

# Main command handler
COMMAND="${1:-}"
SERVICE="${2:-}"

case "$COMMAND" in
    stop)
        case "$SERVICE" in
            all) stop_all ;;
            next) stop_next ;;
            node) stop_node ;;
            python) stop_python ;;
            docker) stop_docker ;;
            make) stop_make ;;
            pnpm) stop_pnpm ;;
            port:*)
                port="${SERVICE#port:}"
                stop_port "$port"
                ;;
            *)
                log_error "Unknown service type: $SERVICE"
                show_help
                exit 1
                ;;
        esac
        ;;
    list)
        list_services
        ;;
    kill)
        # Force kill version
        log_warn "Force killing services..."
        case "$SERVICE" in
            all)
                pkill -9 -f "next dev" 2>/dev/null || true
                pkill -9 -f "^make" 2>/dev/null || true
                pkill -9 -f "pnpm" 2>/dev/null || true
                log_success "All services force-killed"
                ;;
            next) 
                pkill -9 -f "next dev" 2>/dev/null || true
                pkill -9 -f "next-server" 2>/dev/null || true
                ;;
            make) 
                # Don't kill the make process running this script
                for pid in $(pgrep -f "^make" 2>/dev/null); do
                    if ! is_self_or_parent "$pid"; then
                        kill -9 "$pid" 2>/dev/null || true
                    fi
                done
                ;;
            pnpm) pkill -9 -f "pnpm" 2>/dev/null || true ;;
            port:*)
                port="${SERVICE#port:}"
                pid=$(lsof -t -i:$port 2>/dev/null)
                [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true
                ;;
        esac
        ;;
    clean)
        case "$SERVICE" in
            next)
                stop_next
                clear_next_cache
                ;;
            all)
                stop_all
                clear_next_cache
                ;;
            *)
                log_error "Unknown service type for clean: $SERVICE"
                show_help
                exit 1
                ;;
        esac
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
