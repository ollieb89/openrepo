.PHONY: help dev test lint dashboard memory clean memory-health \
        submodule-init submodule-update \
        openclaw-install openclaw-build openclaw-link openclaw-skills \
        setup dev-all dev-dashboard dev-services

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Python (orchestration) ---

dev: ## Install orchestration package in dev mode
	cd packages/orchestration && uv pip install -e ".[dev]"

test: ## Run all Python tests
	cd packages/orchestration && uv run pytest tests/ -v

lint: ## Lint Python code
	uv run ruff check packages/orchestration/src/

# --- Dashboard (Next.js) ---

dashboard: ## Start dashboard dev server (port 6987) — OPENCLAW_ROOT must be exported
	@if [ -z "$$OPENCLAW_ROOT" ]; then \
		echo "ERROR: OPENCLAW_ROOT is not set. The dashboard requires this to locate suggest.py and soul-suggestions.json."; \
		echo "  Run: export OPENCLAW_ROOT=$$HOME/.openclaw"; \
		exit 1; \
	fi
	cd packages/dashboard && pnpm install && pnpm run dev

dev-dashboard: dashboard ## Start OCCC dashboard (port 6987)

dev-services: ## Start all background services (memU + OCCC dashboard + OpenClaw link)
	@echo "Starting memU..."
	$(MAKE) memory-up
	@echo "Starting OCCC dashboard on :6987..."
	@if [ -z "$$OPENCLAW_ROOT" ]; then \
		echo "WARN: OPENCLAW_ROOT not set. Dashboard may fail. Run: export OPENCLAW_ROOT=$$HOME/.openclaw"; \
	fi
	cd packages/dashboard && pnpm install && pnpm run dev &
	@echo "All services started. OpenClaw gateway available on :18789 (OCCC on :6987, memU on :18791)"

dashboard-build: ## Build dashboard for production
	cd packages/dashboard && pnpm run build

# --- Memory (memU) ---

memory-up: ## Start memU service via Docker Compose
	cd docker/memory && docker compose up -d

memory-down: ## Stop memU service
	cd docker/memory && docker compose down

memory-health: ## Check memU service health (port 18791; override via MEMU_API_URL)
	@url="$${MEMU_API_URL:-http://localhost:18791}"; \
	curl -sf "$$url/health" > /dev/null 2>&1 \
		&& echo "memU service: healthy" \
		|| echo "memU service: not running (start with 'make memory-up')"

# --- Docker ---

docker-l3: ## Build L3 specialist container image
	docker build -t openclaw-l3-specialist:latest docker/l3-specialist/

# --- Submodule Management ---

submodule-init: ## Initialize and update git submodules
	git submodule update --init --recursive

submodule-update: ## Pull latest from openclaw submodule remote
	cd openclaw && git fetch origin && git checkout origin/main
	@echo "Remember to commit the submodule pointer: git add openclaw && git commit"

# --- OpenClaw Runtime ---

openclaw-install: ## Install openclaw runtime dependencies
	cd openclaw && pnpm install --frozen-lockfile

openclaw-build: ## Build the openclaw runtime
	cd openclaw && pnpm build

openclaw-link: ## Make 'openclaw' CLI available on PATH (via pnpm link)
	cd openclaw && pnpm link --global

openclaw-skills: ## List skills (uses repo openclaw.json so root skills appear)
	OPENCLAW_CONFIG_PATH="$(CURDIR)/openclaw.json" openclaw skills list

# --- Unified Setup ---

setup: submodule-init openclaw-install openclaw-build openclaw-link dev ## Full workspace setup from scratch
	@echo "Setup complete. 'openclaw' CLI is on PATH. Orchestration package installed."

# --- Unified Dev ---

dev-all: dev ## Start all dev services (orchestration + dashboard)
	@echo "Orchestration installed. Run 'make dashboard' in another terminal for OCCC."

# --- Cleanup ---

clean: ## Remove build artifacts and caches
	find packages/ -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find packages/ -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find packages/ -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
