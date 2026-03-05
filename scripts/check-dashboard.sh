#!/bin/bash
# Dashboard Health Check and Setup Guide

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DASHBOARD_URL="http://localhost:6987/occc"
GATEWAY_URL="http://localhost:18789"
MEMU_URL="http://localhost:18791"

echo "======================================"
echo "OpenClaw Dashboard Health Check"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

check_port() {
    local port=$1
    local name=$2
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is running on port $port"
        return 0
    else
        echo -e "${RED}✗${NC} $name is NOT running on port $port"
        return 1
    fi
}

check_service() {
    local url=$1
    local name=$2
    local expected_code=${3:-200}
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✓${NC} $name is healthy ($response)"
        return 0
    else
        echo -e "${YELLOW}!${NC} $name returned HTTP $response"
        return 1
    fi
}

# Check processes
echo "Checking services..."
check_port 6987 "Dashboard (Next.js)"
check_port 18789 "OpenClaw Gateway"
check_port 18791 "memU (Memory Service)"
echo ""

# Check health endpoints
echo "Checking health endpoints..."

# Dashboard internal API
if curl -s http://localhost:6987/occc/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Dashboard API is responding"
else
    echo -e "${RED}✗${NC} Dashboard API is not responding"
fi

# memU health
if curl -s http://localhost:18791/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} memU is healthy"
else
    echo -e "${RED}✗${NC} memU is not healthy (run: make memory-up)"
fi

# Gateway health
gateway_response=$(curl -s http://localhost:18789/health 2>/dev/null)
if echo "$gateway_response" | grep -q "status.*ok"; then
    echo -e "${GREEN}✓${NC} Gateway is healthy"
elif echo "$gateway_response" | grep -q "ui:build"; then
    echo -e "${YELLOW}!${NC} Gateway is running but needs UI assets built"
else
    echo -e "${YELLOW}!${NC} Gateway check: $gateway_response"
fi

echo ""
echo "======================================"
echo "Setup Status"
echo "======================================"
echo ""

# Check auth token
if [ -f "$PROJECT_ROOT/packages/dashboard/.env.local" ]; then
    TOKEN=$(grep OPENCLAW_GATEWAY_TOKEN "$PROJECT_ROOT/packages/dashboard/.env.local" | cut -d= -f2)
    if [ -n "$TOKEN" ]; then
        echo -e "${GREEN}✓${NC} Auth token configured"
        echo ""
        echo "Dashboard URL: $DASHBOARD_URL"
        echo ""
        echo "If you see 'Failed to fetch' errors:"
        echo "1. Open $DASHBOARD_URL/login"
        echo "2. Enter this token:"
        echo "   ${TOKEN:0:20}..."
        echo ""
    else
        echo -e "${RED}✗${NC} Auth token not found in .env.local"
    fi
else
    echo -e "${RED}✗${NC} .env.local file not found"
fi

echo ""
echo "Quick Commands:"
echo "  make list-services     # Show all running services"
echo "  make stop-dashboard    # Stop the dashboard"
echo "  make memory-up         # Start memU service"
echo "  make memory-down       # Stop memU service"
echo ""
