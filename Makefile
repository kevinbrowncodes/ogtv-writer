# ==============================================================================
# Makefile — common developer tasks. Run `make` or `make help` to list them.
# ==============================================================================
PYTHON ?= python3
PORT ?= 8000
HOST ?= 127.0.0.1

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- Setup --------------------------------------------------------------------
.PHONY: install
install: ## Install Python (editable + dev) and Node dependencies
	$(PYTHON) -m pip install -e ".[dev]"
	npm install

.PHONY: setup
setup: install ## Full first-time setup: deps, browsers, CSS, seed data
	$(PYTHON) -m playwright install chromium
	$(MAKE) css
	$(MAKE) migrate
	$(MAKE) seed
	@echo "\n✅ Setup complete. Start the app with: make dev"

# --- Frontend (Tailwind) ------------------------------------------------------
.PHONY: css
css: ## Build the Tailwind CSS once (minified)
	npm run css:build

.PHONY: css-watch
css-watch: ## Rebuild Tailwind CSS on change (run in a second terminal)
	npm run css:dev

# --- Run ----------------------------------------------------------------------
.PHONY: dev
dev: ## Run the dev server with hot reload (also run `make css-watch` separately)
	$(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

.PHONY: dev-all
dev-all: ## Run Tailwind watch AND the dev server together
	npm run css:dev & $(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

.PHONY: run
run: ## Run the server without reload (production-like)
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

.PHONY: seed
seed: ## Create sample data (tags + scripts)
	$(PYTHON) -m scripts.seed

.PHONY: migrate
migrate: ## Apply migrations to head (adopts an existing pre-migration DB safely)
	$(PYTHON) -m app.migrations_runner

.PHONY: migration
migration: ## Autogenerate a migration: make migration m="describe change"
	alembic revision --autogenerate -m "$(m)"

# --- Quality ------------------------------------------------------------------
.PHONY: lint
lint: ## Lint with Ruff
	ruff check .

.PHONY: format
format: ## Auto-format with Ruff
	ruff format .
	ruff check --fix .

.PHONY: typecheck
typecheck: ## Static type-check with mypy
	mypy app

.PHONY: check
check: lint typecheck test ## Run lint + typecheck + tests

# --- Tests --------------------------------------------------------------------
.PHONY: test
test: ## Run unit + integration tests (fast)
	pytest

.PHONY: test-e2e
test-e2e: ## Run Playwright end-to-end tests
	pytest -m e2e

.PHONY: test-all
test-all: ## Run every test (unit + integration + e2e)
	pytest -m "e2e or not e2e"

# --- Docker -------------------------------------------------------------------
.PHONY: docker-build
docker-build: ## Build the Docker image
	docker build -t ogtv-writer .

.PHONY: docker-run
docker-run: ## Run the app via docker compose
	docker compose up --build

# --- Housekeeping -------------------------------------------------------------
.PHONY: clean
clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache test-results playwright-report
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f app/static/css/app.css
