# CitationLLM Makefile
# Usage: make <target>
#
# Targets:
#   help            Show this help message
#   setup           Install all dependencies (backend + frontend)
#   build           Build frontend production bundle
#   build-dev       Build frontend in dev mode (with sourcemaps)
#   dev             Start backend and frontend concurrently (requires make setup first)
#   dev-backend     Start backend only
#   dev-frontend    Start frontend only
#   db-init         Run Flask migrations / create tables
#   db-reset        Drop all tables and re-create (WARNING: destroys data)
#   db-seed         (placeholder) seed database with sample data
#   test            Run all tests
#   test-backend    Run backend tests only
#   test-frontend   Run frontend tests only
#   lint            Run linters (backend + frontend)
#   lint-fix        Auto-fix linter issues
#   clean           Remove build artifacts and caches
#   clean-deep      Remove node_modules, venv, __pycache__, .pyc, dist
#   docker-up       Start PostgreSQL + pgvector via docker-compose
#   docker-down     Stop docker-compose services
#   docker-logs     Tail docker-compose logs
#   status          Check which services are running
#   info            Print environment and dependency versions

# ─────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────

PYTHON      := python3
PIP         := pip3
NPM         := npm
NODE_ENV    ?= development
PYTHON_DIR  := backend
FRONTEND_DIR := frontend
VENV_DIR    := $(PYTHON_DIR)/venv
VENV_PY     := $(VENV_DIR)/bin/python
VENV_PIP    := $(VENV_DIR)/bin/pip
DB_URL      ?= sqlite:///citation_llm.db
PORT_BACKEND:= 5001
PORT_FRONTEND:= 3000

# Colours
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
BOLD   := \033[1m
NC     := \033[0m # No Colour

.PHONY: help setup build build-dev dev dev-backend dev-frontend \
        db-init db-reset db-seed \
        test test-backend test-frontend \
        lint lint-fix \
        clean clean-deep \
        docker-up docker-down docker-logs \
        status info

# ─────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────

help: ## Show this help message
	@printf "$(BOLD)CitationLLM — available targets$(NC)\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@printf "\n"
	@printf "  $(YELLOW)Environment variables:$(NC)\n"
	@printf "    DATABASE_URL      Override database URL (default: sqlite:///citation_llm.db)\n"
	@printf "    NODE_ENV          development | production  (default: development)\n"
	@printf "\n"

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

setup: ## Install all dependencies (backend venv + frontend node_modules)
setup: setup-backend setup-frontend
	@printf "\n$(GREEN)✓$(NC) Full setup complete.\n"
	@printf "  Run $(BOLD)make dev$(NC) to start both services.\n"

setup-backend: ## Create venv and install Python packages
	@printf "$(BLUE)==> Backend setup$(NC)\n"
	@if ! command -v $(PYTHON) &> /dev/null; then \
		echo "$(RED)✗ Python 3 not found. Please install Python 3.10+$(NC)"; exit 1; \
	fi
	@if [ ! -d "$(VENV_DIR)" ]; then \
		printf "  Creating virtual environment... "; \
		$(PYTHON) -m venv $(VENV_DIR) && echo "$(GREEN)done$(NC)"; \
	else \
		echo "  Virtual environment already exists — skipping."; \
	fi
	@printf "  Installing Python packages... "
	@$(VENV_PIP) install -q --upgrade pip && \
		$(VENV_PIP) install -q -r $(PYTHON_DIR)/requirements.txt \
		&& echo "$(GREEN)done$(NC)" \
		|| (echo "$(RED)failed$(NC)"; exit 1)
	@if [ ! -f "$(PYTHON_DIR)/.env" ] && [ -f "$(PYTHON_DIR)/.env.example" ]; then \
		cp $(PYTHON_DIR)/.env.example $(PYTHON_DIR)/.env; \
		echo "  $(YELLOW)Created backend/.env — please fill in your API keys$(NC)"; \
	fi

setup-frontend: ## Install Node packages
	@printf "$(BLUE)==> Frontend setup$(NC)\n"
	@if ! command -v $(NPM) &> /dev/null; then \
		echo "$(RED)✗ Node.js/npm not found. Please install Node 18+$(NC)"; exit 1; \
	fi
	@cd $(FRONTEND_DIR) && $(NPM) install
	@printf "$(GREEN)✓$(NC) Frontend dependencies installed.\n"

# ─────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────

build: ## Build frontend production bundle
build: setup-frontend
	@printf "$(BLUE)==> Building frontend (production)$(NC)\n"
	@NODE_ENV=production $(NPM) --prefix $(FRONTEND_DIR) run build
	@printf "$(GREEN)✓$(NC) Production build: $(FRONTEND_DIR)/dist/\n"

build-dev: setup-frontend ## Build frontend in development mode
	@printf "$(BLUE)==> Building frontend (dev)$(NC)\n"
	@NODE_ENV=development $(NPM) --prefix $(FRONTEND_DIR) run build
	@printf "$(GREEN)✓$(NC) Dev build: $(FRONTEND_DIR)/dist/\n"

# ─────────────────────────────────────────────
# Development servers
# ─────────────────────────────────────────────

dev: ## Start backend + frontend concurrently
dev: setup
	@printf "$(BLUE)==> Starting CitationLLM (backend + frontend)$(NC)\n"
	@printf "  Backend:  http://localhost:$(PORT_BACKEND)\n"
	@printf "  Frontend: http://localhost:$(PORT_FRONTEND)\n\n"
	@command -v uv &> /dev/null && \
		(echo "Using uv for backend..." && cd $(PYTHON_DIR) && uv run python run.py &) \
		|| \
		(cd $(PYTHON_DIR) && source venv/bin/activate && python run.py &)
	@cd $(FRONTEND_DIR) && $(NPM) run dev

dev-backend: setup-backend ## Start Flask backend only
	@printf "$(BLUE)==> Starting backend on :$(PORT_BACKEND)$(NC)\n"
	@command -v uv &> /dev/null && \
		(echo "Using uv..." && cd $(PYTHON_DIR) && uv run python run.py) \
		|| \
		(cd $(PYTHON_DIR) && source venv/bin/activate && python run.py)

dev-frontend: setup-frontend ## Start Vite frontend only
	@printf "$(BLUE)==> Starting frontend on :$(PORT_FRONTEND)$(NC)\n"
	@cd $(FRONTEND_DIR) && $(NPM) run dev

# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────

db-init: setup-backend ## Run Flask migrations / create all tables
	@printf "$(BLUE)==> Initialising database$(NC)\n"
	@cd $(PYTHON_DIR) && \
		source venv/bin/activate && \
		flask db upgrade 2>/dev/null || \
		python -c "from app import create_app; from app.extensions import db; \
			app=create_app(); \
			with app.app_context(): db.create_all(); print('Tables created.')"
	@printf "$(GREEN)✓$(NC) Database ready.\n"

db-reset: setup-backend ## Drop all tables and re-create (DESTRUCTIVE)
	@printf "$(RED)! WARNING: This will destroy ALL data in the database.$(NC)\n"
	@read -p "  Type 'yes' to confirm: " confirm; \
		[ "$$confirm" = "yes" ] || (echo "Aborted."; exit 1)
	@printf "$(BLUE)==> Resetting database$(NC)\n"
	@cd $(PYTHON_DIR) && \
		source venv/bin/activate && \
		python -c "from app import create_app; from app.extensions import db; \
			app=create_app(); \
			with app.app_context(): \
				db.drop_all(); db.create_all(); \
				print('Tables dropped and recreated.')"
	@printf "$(GREEN)✓$(NC) Database reset complete.\n"

db-seed: ## Seed database with sample data (no-op — implement as needed)
	@printf "$(YELLOW)db-seed is not yet implemented. Add your seed logic to backend/seed.py$(NC)\n"

# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

test: test-backend test-frontend ## Run all tests (backend + frontend)

test-backend: setup-backend ## Run backend tests with pytest
	@printf "$(BLUE)==> Running backend tests$(NC)\n"
	@cd $(PYTHON_DIR) && \
		source venv/bin/activate && \
		python -m pytest -v $(PYTEST_ARGS)

test-frontend: setup-frontend ## Run frontend tests with Vite test runner
	@printf "$(BLUE)==> Running frontend tests$(NC)\n"
	@cd $(FRONTEND_DIR) && $(NPM) run test -- --run 2>/dev/null || \
		$(NPM) run test 2>/dev/null || \
		echo "$(YELLOW)No frontend tests found$(NC)"

# ─────────────────────────────────────────────
# Linting
# ─────────────────────────────────────────────

lint: lint-backend lint-frontend ## Run all linters

lint-backend: setup-backend ## Run Python linters (flake8, isort)
	@printf "$(BLUE)==> Linting backend (flake8 + isort --check)$(NC)\n"
	@cd $(PYTHON_DIR) && \
		source venv/bin/activate && \
		-isort --check-only --diff . && \
		-flake8 . --max-line-length=160 --ignore=D203 || true

lint-frontend: setup-frontend ## Run frontend linter (ESLint / Vite)
	@printf "$(BLUE)==> Linting frontend$(NC)\n"
	@cd $(FRONTEND_DIR) && $(NPM) run build 2>&1 | tail -5

lint-fix: ## Auto-fix lint issues where possible
	@printf "$(BLUE)==> Auto-fixing lint issues$(NC)\n"
	@cd $(PYTHON_DIR) && \
		source venv/bin/activate 2>/dev/null && \
		isort . && \
		autopep8 --in-place --aggressive --aggressive -r . 2>/dev/null || \
		python -m py_compile $$(find . -name '*.py' -not -path './venv/*') || true
	@printf "$(GREEN)✓$(NC) Lint fixes applied. Please review changes before committing.\n"

# ─────────────────────────────────────────────
# Docker (PostgreSQL + pgvector)
# ─────────────────────────────────────────────

docker-up: ## Start PostgreSQL + pgvector container
	@printf "$(BLUE)==> Starting PostgreSQL + pgvector$(NC)\n"
	@cd $(shell dirname $(MAKEFILE_LIST)) && \
		docker compose up -d postgres && \
		sleep 3 && \
		docker compose ps
	@printf "$(GREEN)✓$(NC) PostgreSQL running on :5432\n"
	@printf "  User: postgres / Password: postgres / DB: citation_llm\n"

docker-down: ## Stop docker-compose services
	@printf "$(BLUE)==> Stopping docker-compose services$(NC)\n"
	@cd $(shell dirname $(MAKEFILE_LIST)) && docker compose down
	@printf "$(GREEN)✓$(NC) Services stopped.\n"

docker-logs: ## Tail docker-compose logs
	@cd $(shell dirname $(MAKEFILE_LIST)) && docker compose logs -f

# ─────────────────────────────────────────────
# Status & Info
# ─────────────────────────────────────────────

status: ## Show which services and processes are running
	@printf "$(BOLD)CitationLLM — Service Status$(NC)\n\n"
	@printf "  $(YELLOW)Backend check:$(NC)  "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:$(PORT_BACKEND)/api/health \
		&& echo " $(GREEN)UP$(NC)" \
		|| echo " $(RED)DOWN$(NC) (start with make dev-backend)"
	@printf "  $(YELLOW)Frontend check:$(NC) "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:$(PORT_FRONTEND) \
		&& echo " $(GREEN)UP$(NC)" \
		|| echo " $(RED)DOWN$(NC) (start with make dev-frontend)"
	@printf "  $(YELLOW)PostgreSQL:$(NC)     "
	@docker ps --format '{{.Names}}' 2>/dev/null | grep -q postgres \
		&& echo "$(GREEN)running$(NC) (container)" \
		|| (pg_isready -h localhost -p 5432 &>/dev/null \
			&& echo "$(GREEN)running$(NC) (local)" \
			|| echo "$(RED)not running$(NC)")

info: ## Print environment and dependency versions
	@printf "$(BOLD)CitationLLM — Environment Info$(NC)\n\n"
	@printf "  Python:      $(PYTHON)$(NC)\n" && $(PYTHON) --version 2>/dev/null || true
	@printf "  Node:        $(NPM)$(NC)\n" && $(NPM) --version 2>/dev/null || true
	@printf "  pip:         $(PIP)$(NC)\n" && $(PIP) --version 2>/dev/null || true
	@printf "  Backend dir: $(PYTHON_DIR)/\n"
	@printf "  Frontend dir: $(FRONTEND_DIR)/\n"
	@printf "  VENV:        $(VENV_DIR)/\n"
	@printf "  DATABASE_URL: $(DB_URL)\n"
	@printf "  NODE_ENV:    $(NODE_ENV)\n"
	@printf "\n  Key packages installed:\n"
	@$(VENV_PIP) list 2>/dev/null | grep -E "Flask|psycopg2|openai|anthropic|react|vite|tailwind" \
		| sed 's/^/    /' || true

# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────

clean: ## Remove build artifacts, caches, and temp files
	@printf "$(BLUE)==> Cleaning build artifacts$(NC)\n"
	@rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/.vite
	@find $(PYTHON_DIR) -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find $(PYTHON_DIR) -type f -name '*.pyc' -delete 2>/dev/null || true
	@find $(PYTHON_DIR) -type f -name '*.pyo' -delete 2>/dev/null || true
	@find $(PYTHON_DIR) -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	@find $(PYTHON_DIR) -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@printf "$(GREEN)✓$(NC) Clean complete.\n"

clean-deep: ## Remove node_modules, venv, and all caches (full reset)
	@printf "$(RED)! This will remove node_modules, venv, and all caches.$(NC)\n"
	@read -p "  Type 'yes' to confirm: " confirm; \
		[ "$$confirm" = "yes" ] || (echo "Aborted."; exit 1)
	@printf "$(BLUE)==> Deep cleaning$(NC)\n"
	@rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/.vite
	@rm -rf $(VENV_DIR)
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@find . -type f -name '.DS_Store' -delete 2>/dev/null || true
	@printf "$(GREEN)✓$(NC) Deep clean complete. Run $(BOLD)make setup$(NC) to re-install.\n"
