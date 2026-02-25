.PHONY: help dev test lint dashboard memory clean

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
	cd packages/dashboard && bun install && bun run dev

dashboard-build: ## Build dashboard for production
	cd packages/dashboard && bun run build

# --- Memory (memU) ---

memory-up: ## Start memU service via Docker Compose
	cd docker/memory && docker compose up -d

memory-down: ## Stop memU service
	cd docker/memory && docker compose down

# --- Docker ---

docker-l3: ## Build L3 specialist container image
	docker build -t openclaw-l3-specialist:latest docker/l3-specialist/

# --- Cleanup ---

clean: ## Remove build artifacts and caches
	find packages/ -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find packages/ -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find packages/ -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
