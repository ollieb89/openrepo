#!/bin/bash
# Start OCCC Dashboard with proper environment setup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Export required environment variables
export OPENCLAW_ROOT="${OPENCLAW_ROOT:-$PROJECT_ROOT}"

echo "======================================"
echo "Starting OCCC Dashboard"
echo "======================================"
echo "OPENCLAW_ROOT: $OPENCLAW_ROOT"
echo "Dashboard URL: http://localhost:6987/occc"
echo ""

# Verify required paths exist
if [ ! -d "$OPENCLAW_ROOT/projects" ]; then
    echo "⚠️  Warning: $OPENCLAW_ROOT/projects not found"
fi

if [ ! -f "$OPENCLAW_ROOT/packages/orchestration/src/openclaw/cli/suggest.py" ]; then
    echo "⚠️  Warning: suggest.py not found at expected path"
fi

# Kill any existing process on port 6987
echo "Checking for existing processes on port 6987..."
npx kill-port 6987 2>/dev/null || true

# Change to dashboard directory and start
cd "$PROJECT_ROOT/packages/dashboard"

# Clear Next.js cache if needed (optional, add --clean flag)
if [ "$1" = "--clean" ]; then
    echo "Clearing Next.js cache..."
    rm -rf .next tsconfig.tsbuildinfo
fi

echo "Installing dependencies..."
pnpm install

echo ""
echo "Starting Next.js dev server..."
echo "======================================"
pnpm dev
