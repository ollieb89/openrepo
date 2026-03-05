.PHONY: help dev test lint dashboard memory clean memory-health \
        submodule-init submodule-update \
        openclaw-install openclaw-build openclaw-link openclaw-skills \
        setup dev-all dev-dashboard dev-services \
        docker-base docker-sandbox-base docker-sandbox-common docker-l3 docker-all \
        stop stop-all stop-dashboard stop-services list-services kill-port

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

dashboard: ## Start dashboard dev server (port 6987) — auto-sets OPENCLAW_ROOT to repo root
	@export OPENCLAW_ROOT="$(CURDIR)"; \
	echo "Starting dashboard with OPENCLAW_ROOT=$$OPENCLAW_ROOT"; \
	cd packages/dashboard && pnpm install && pnpm run dev

dev-dashboard: dashboard ## Start OCCC dashboard (port 6987)

dev-services: ## Start all background services (memU + OCCC dashboard + OpenClaw link)
	@echo "Starting memU..."
	$(MAKE) memory-up
	@echo "Starting OCCC dashboard on :6987..."
	@export OPENCLAW_ROOT="$(CURDIR)"; \
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

docker-base: ## Build openclaw base image
	docker build -t openclaw-base:bookworm-slim docker/base/

docker-sandbox-base: ## Build openclaw sandbox base image
	cd openclaw && docker build -f Dockerfile.sandbox -t openclaw-sandbox:bookworm-slim .

docker-sandbox-common: docker-sandbox-base ## Build openclaw sandbox-common image (full runtime stack)
	cd openclaw && docker build -f Dockerfile.sandbox-common -t openclaw-sandbox-common:bookworm-slim .

docker-l3: docker-base ## Build L3 specialist container image (depends on base image)
	docker build -t openclaw-l3-specialist:latest docker/l3-specialist/

docker-all: docker-base docker-sandbox-base docker-sandbox-common docker-l3 ## Build the full Docker image chain

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

# --- Service Management ---

stop: ## Stop services (use: make stop [next|node|python|docker|make|all])
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		$(MAKE) stop-dashboard; \
	else \
		./scripts/service-manager.sh stop $(filter-out $@,$(MAKECMDGOALS)); \
	fi

stop-all: ## Stop all services
	./scripts/service-manager.sh stop all

stop-dashboard: ## Stop Next.js dashboard
	./scripts/service-manager.sh stop next
	./scripts/service-manager.sh stop port:6987

stop-services: ## Stop all background services (memU + dashboard)
	$(MAKE) memory-down
	$(MAKE) stop-dashboard

list-services: ## List all running project services
	./scripts/service-manager.sh list

kill-port: ## Kill process on specific port (use: make kill-port PORT=6987)
	@if [ -z "$(PORT)" ]; then \
		echo "Usage: make kill-port PORT=6987"; \
		exit 1; \
	fi
	./scripts/service-manager.sh kill port:$(PORT)

# Catch-all for stop arguments
%:
	@:
