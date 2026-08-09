# inDoc SaaS Platform - Production-Ready Makefile
# Version: 2.0
# Date: 2025-10-13
#
# Following inDoc AI Prompt Engineering Guide principles:
# - No duplication: Single source of truth for each operation
# - Data integrity: Proper dependency management
# - Clear documentation: Self-documenting targets

.PHONY: help dev saas saas-local saas-prod install build test clean migrate \
	start stop restart health logs monitor ps \
	conda-env conda-install local-e2e local-stop \
	test-backend test-frontend e2e-test seed-data \
	db-shell db-backup format lint

# Default target
.DEFAULT_GOAL := help

# Environment
CONDA?=conda
ENV_NAME?=indoc
CONDA_RUN=$(CONDA) run -n $(ENV_NAME)
ROOT_DIR:=$(CURDIR)
TMP_DIR:=$(ROOT_DIR)/tmp
COMPOSE_DEV:=docker-compose.yml
COMPOSE_PROD:=docker-compose.production.yml

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

##@ Help

help: ## Display this help message
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  inDoc SaaS Platform - Makefile Commands$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Development (Full Stack)

dev: conda-install celery-cleanup ## Start full development stack (local processes, hot reload)
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  🚀 Starting Full Development Stack (Everything Needed)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)📋 Prerequisites Check:$(NC)"
	@if ! docker info > /dev/null 2>&1; then \
		echo "$(RED)❌ Docker not running. Start Docker Desktop first.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Docker running$(NC)"
	@if ! nc -z localhost 5432 2>/dev/null; then \
		echo "$(RED)❌ PostgreSQL not running on localhost:5432$(NC)"; \
		echo "$(YELLOW)   Start PostgreSQL first (brew services start postgresql)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ PostgreSQL running (localhost:5432)$(NC)"
	@echo ""
	@echo "$(YELLOW)Stack Configuration:$(NC)"
	@echo "   • Backend:    Local (conda) - Hot Reload ✅"
	@echo "   • Frontend:   Local (vite) - Hot Reload ✅"
	@echo "   • Celery:     Local (conda) - Debug Mode ✅"
	@echo "   • Services:   Docker (ES, Qdrant, Redis, Monitoring)"
	@echo "   • Database:   PostgreSQL @ localhost:5432 (external)"
	@echo ""
	@echo "$(YELLOW)Cleaning old processes...$(NC)"
	@pkill -9 -f "uvicorn main:app" 2>/dev/null || true
	@pkill -9 -f "vite.*5173" 2>/dev/null || true
	@pkill -9 -f "celery -A app.core.celery_app worker" 2>/dev/null || true
	@pkill -9 -f "celery -A app.core.celery_app beat" 2>/dev/null || true
	@pkill -9 -f "conda run.*celery" 2>/dev/null || true
	@pkill -9 -f "conda run.*uvicorn" 2>/dev/null || true
	@rm -f $(TMP_DIR)/*.pid $(TMP_DIR)/*.out 2>/dev/null || true
	@sleep 3
	@echo "$(GREEN)✅ Clean$(NC)"
	@echo ""
	@echo "$(BLUE)Starting Docker services...$(NC)"
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose up -d elasticsearch qdrant redis prometheus grafana
	@echo "$(YELLOW)⏳ Waiting for services (10 seconds)...$(NC)"
	@sleep 10
	@mkdir -p $(TMP_DIR)
	@echo ""
	@echo "$(BLUE)Starting application processes...$(NC)"
	@cd app && nohup $(CONDA_RUN) sh -c 'export PYTHONPATH=$$PWD/..:$$PYTHONPATH && uvicorn main:app --host 0.0.0.0 --port 8000 --reload' > ../$(TMP_DIR)/backend.out 2>&1 & echo $$! > ../$(TMP_DIR)/backend.pid
	@echo "$(GREEN)✓$(NC) Backend starting..."
	@sleep 3
	@nohup $(CONDA_RUN) celery -A app.core.celery_app worker --pool=solo --loglevel=info --queues=celery,document_processing,search_indexing,llm_processing > $(TMP_DIR)/celery_worker.out 2>&1 & echo $$! > $(TMP_DIR)/celery_worker.pid
	@echo "$(GREEN)✓$(NC) Celery worker starting..."
	@sleep 1
	@nohup $(CONDA_RUN) celery -A app.core.celery_app beat --loglevel=info > $(TMP_DIR)/celery_beat.out 2>&1 & echo $$! > $(TMP_DIR)/celery_beat.pid
	@echo "$(GREEN)✓$(NC) Celery beat starting..."
	@sleep 1
	@cd frontend && nohup npm run dev -- --port 5173 > ../$(TMP_DIR)/frontend.out 2>&1 & echo $$! > ../$(TMP_DIR)/frontend.pid
	@echo "$(GREEN)✓$(NC) Frontend starting..."
	@sleep 5
	@echo ""
	@echo "$(GREEN)✨ Development stack ready!$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(BLUE)📍 Access Points:$(NC)"
	@echo "   • Frontend:    http://localhost:5173"
	@echo "   • API:         http://localhost:8000"
	@echo "   • API Docs:    http://localhost:8000/api/v1/docs"
	@echo "   • Grafana:     http://localhost:3030 (admin/admin)"
	@echo "   • Prometheus:  http://localhost:9090"
	@echo ""
	@echo "$(YELLOW)🛑 To stop: make stop$(NC)"
	@echo ""

stop: celery-cleanup ## Stop all processes (works for both dev and saas)
	@echo "$(YELLOW)🛑 Stopping all processes...$(NC)"
	@# Kill by PID files first (graceful)
	@if [ -f $(TMP_DIR)/backend.pid ]; then kill `cat $(TMP_DIR)/backend.pid` 2>/dev/null || true; fi
	@if [ -f $(TMP_DIR)/celery_worker.pid ]; then kill `cat $(TMP_DIR)/celery_worker.pid` 2>/dev/null || true; fi
	@if [ -f $(TMP_DIR)/celery_beat.pid ]; then kill `cat $(TMP_DIR)/celery_beat.pid` 2>/dev/null || true; fi
	@if [ -f $(TMP_DIR)/frontend.pid ]; then kill `cat $(TMP_DIR)/frontend.pid` 2>/dev/null || true; fi
	@sleep 2
	@# Force kill by process name (aggressive)
	@pkill -9 -f "uvicorn main:app" 2>/dev/null || true
	@pkill -9 -f "vite.*5173" 2>/dev/null || true
	@pkill -9 -f "celery -A app.core.celery_app worker" 2>/dev/null || true
	@pkill -9 -f "celery -A app.core.celery_app beat" 2>/dev/null || true
	@pkill -9 -f "conda run.*celery" 2>/dev/null || true
	@pkill -9 -f "conda run.*uvicorn" 2>/dev/null || true
	@pkill -9 -f "conda run.*vite" 2>/dev/null || true
	@# Clean up PID and log files
	@rm -f $(TMP_DIR)/*.pid $(TMP_DIR)/*.out 2>/dev/null || true
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose down 2>/dev/null || true
	@echo "$(GREEN)✅ All processes stopped$(NC)"

celery-cleanup: ## Clean up Celery workers
	@pkill -f "celery.*worker" 2>/dev/null || true
	@pkill -f "celery.*beat" 2>/dev/null || true
	@rm -f $(TMP_DIR)/celery_worker.pid $(TMP_DIR)/celery_beat.pid 2>/dev/null || true

##@ SaaS Platform (Production Simulation)

saas: saas-local ## Start full SaaS platform locally (default: docker-compose)

saas-local: ## Simulate production SaaS locally with Docker Compose
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  🚀 Starting Full SaaS Stack (Production Simulation)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)📋 Prerequisites Check:$(NC)"
	@if ! docker info > /dev/null 2>&1; then \
		echo "$(RED)❌ Docker is not running. Start Docker Desktop first.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Docker running$(NC)"
	@if ! nc -z localhost 5432 2>/dev/null; then \
		echo "$(RED)❌ PostgreSQL not running on localhost:5432$(NC)"; \
		echo "$(YELLOW)   Start PostgreSQL first (outside Docker as planned)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ PostgreSQL running (localhost:5432)$(NC)"
	@echo ""
	@echo "$(BLUE)🐳 Starting Docker services:$(NC)"
	@echo "   • Redis (cache)"
	@echo "   • Elasticsearch (keyword search)"
	@echo "   • Qdrant (vector search)"
	@echo "   • Prometheus & Grafana (monitoring)"
	@echo ""
	@echo "$(YELLOW)⚠️  PostgreSQL runs OUTSIDE Docker (localhost:5432)$(NC)"
	@echo ""
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose -f $(COMPOSE_DEV) up -d
	@echo ""
	@echo "$(YELLOW)⏳ Waiting for services (30 seconds)...$(NC)"
	@sleep 30
	@echo ""
	@$(MAKE) saas-health
	@echo ""
	@echo "$(GREEN)✨ Full SaaS Stack Running!$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(BLUE)📍 Access Points:$(NC)"
	@echo "   • Frontend:          http://localhost:5173"
	@echo "   • Backend API:       http://localhost:8000"
	@echo "   • API Docs:          http://localhost:8000/api/v1/docs"
	@echo "   • Grafana:           http://localhost:3030 (admin/admin)"
	@echo "   • Prometheus:        http://localhost:9090"
	@echo "   • Qdrant Dashboard:  http://localhost:6333/dashboard"
	@echo ""
	@echo "$(YELLOW)💾 Database:$(NC) PostgreSQL @ localhost:5432 (external)"
	@echo ""
	@echo "$(BLUE)📝 Default Credentials:$(NC)"
	@echo "   • Admin:  admin / Admin123!"
	@echo ""
	@echo "$(YELLOW)🛑 To stop: make stop$(NC)"
	@echo ""

saas-prod: ## Deploy production SaaS with full stack (docker-compose.production.yml)
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  🚀 Starting inDoc SaaS Platform (Production Configuration)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)⚠️  This uses production configuration with:$(NC)"
	@echo "   - HashiCorp Vault (secrets management)"
	@echo "   - Nginx reverse proxy"
	@echo "   - Fluent Bit & Loki (log aggregation)"
	@echo "   - Jaeger (distributed tracing)"
	@echo "   - Production-grade security & monitoring"
	@echo ""
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)🐳 Starting production stack...$(NC)"; \
		export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose -f $(COMPOSE_PROD) up -d; \
		sleep 45; \
		$(MAKE) saas-health-prod; \
		echo ""; \
		echo "$(GREEN)✨ Production SaaS Platform running!$(NC)"; \
		echo "$(BLUE)Access Points:$(NC)"; \
		echo "   • Application:  http://localhost (via Nginx)"; \
		echo "   • API Docs:     http://localhost/api/v1/docs"; \
		echo "   • Grafana:      http://localhost:3030"; \
		echo "   • Jaeger UI:    http://localhost:16686"; \
		echo ""; \
		echo "$(YELLOW)🛑 To stop: make saas-stop-prod$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled.$(NC)"; \
	fi

saas-stop: ## Alias for 'make stop' (stops all services)
	@$(MAKE) stop

saas-stop-prod: ## Stop production SaaS platform
	@echo "$(YELLOW)🛑 Stopping production SaaS platform...$(NC)"
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose -f $(COMPOSE_PROD) down
	@echo "$(GREEN)✅ Production SaaS platform stopped$(NC)"

saas-health: ## Check health of SaaS services
	@echo "$(BLUE)🔍 Checking SaaS service health...$(NC)"
	@echo -n "PostgreSQL: "; docker compose exec -T db pg_isready -U indoc_user 2>/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(RED)❌$(NC)"
	@echo -n "Redis:      "; docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && echo "$(GREEN)✅$(NC)" || echo "$(RED)❌$(NC)"
	@echo -n "Elasticsearch: "; curl -sf http://localhost:9200/_cluster/health >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(YELLOW)⚠️$(NC)"
	@echo -n "Qdrant:     "; curl -sf http://localhost:6333/healthz >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(YELLOW)⚠️$(NC)"
	@echo -n "Backend:    "; curl -sf http://localhost:8000/ >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(YELLOW)⚠️$(NC)"
	@echo -n "Frontend:   "; curl -sfI http://localhost:5173 >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(YELLOW)⚠️$(NC)"

saas-health-prod: ## Check health of production SaaS services
	@echo "$(BLUE)🔍 Checking production SaaS service health...$(NC)"
	@echo -n "PostgreSQL: "; docker compose -f $(COMPOSE_PROD) exec -T db pg_isready -U indoc_user 2>/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(RED)❌$(NC)"
	@echo -n "Redis:      "; docker compose -f $(COMPOSE_PROD) exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && echo "$(GREEN)✅$(NC)" || echo "$(RED)❌$(NC)"
	@echo -n "Vault:      "; curl -sf http://localhost:8200/v1/sys/health >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(RED)❌$(NC)"
	@echo -n "Nginx:      "; curl -sfI http://localhost >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(RED)❌$(NC)"
	@echo -n "Jaeger:     "; curl -sf http://localhost:16686 >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(YELLOW)⚠️$(NC)"

##@ Dependencies & Setup

conda-env: ## Create conda environment 'indoc' (python 3.11)
	@echo "$(BLUE)Ensuring conda environment '$(ENV_NAME)' exists...$(NC)"
	@which $(CONDA) >/dev/null 2>&1 || { echo "$(RED)conda not found in PATH$(NC)"; exit 1; }
	@$(CONDA) env list | grep -E "^$(ENV_NAME)\s" >/dev/null 2>&1 || \
		$(CONDA) create -y -n $(ENV_NAME) python=3.11
	@echo "$(GREEN)✅ Conda environment ready: $(ENV_NAME)$(NC)"

conda-install: conda-env ## Install dependencies in conda environment
	@echo "$(BLUE)Installing backend dependencies into conda env...$(NC)"
	@cd app && $(CONDA_RUN) python -m pip install -r ../requirements.txt
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@cd frontend && npm install
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

install: conda-install ## Alias for conda-install

##@ Build & Deploy

build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose build
	@echo "$(GREEN)✅ Images built$(NC)"

build-prod: ## Build production Docker images
	@echo "$(BLUE)Building production images...$(NC)"
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker buildx bake -f docker-bake.hcl
	@echo "$(GREEN)✅ Production images built$(NC)"

build-frontend: conda-install ## Build frontend for production
	@echo "$(BLUE)Building frontend (vite)...$(NC)"
	@cd frontend && npm run build
	@echo "$(GREEN)✅ Frontend built (dist/)$(NC)"

##@ Database

migrate: ## Run database migrations (requires running DB)
	@echo "$(BLUE)Running database migrations...$(NC)"
	@$(CONDA_RUN) sh -c 'cd app && export PYTHONPATH=$$PWD/..:$$PYTHONPATH && alembic upgrade head'
	@echo "$(GREEN)✅ Migrations complete$(NC)"

db-shell: ## Open PostgreSQL shell
	@echo "$(BLUE)Opening PostgreSQL shell...$(NC)"
	@docker compose exec db psql -U indoc_user -d indoc

db-backup: ## Backup database to backups/ directory
	@echo "$(BLUE)Backing up database...$(NC)"
	@mkdir -p backups
	@docker compose exec -T db pg_dump -U indoc_user indoc > backups/indoc_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Database backed up to backups/$(NC)"

##@ Testing

test: test-backend test-frontend ## Run all tests

test-backend: conda-install ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	@cd app && $(CONDA_RUN) sh -c 'export PYTHONPATH=$$PWD/..:$$PYTHONPATH && pytest -v'

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@cd frontend && npm test

e2e-test: conda-install ## Run comprehensive E2E tests
	@echo "$(BLUE)Running E2E tests...$(NC)"
	@$(CONDA_RUN) python tools/e2e_test_runner.py
	@echo "$(GREEN)✅ E2E tests complete$(NC)"

seed-data: conda-install ## Generate seed data for testing
	@echo "$(BLUE)Generating seed data...$(NC)"
	@$(CONDA_RUN) python tools/seed_data_generator.py
	@echo "$(GREEN)✅ Seed data generated$(NC)"

##@ Monitoring & Operations

health: ## Check service health
	@$(MAKE) saas-health

logs: ## View Docker service logs
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose logs -f --tail=100

logs-local: ## View local process logs
	@echo "$(BLUE)Tailing local app logs (Ctrl+C to stop)...$(NC)"
	@tail -n 50 -f $(TMP_DIR)/*.out 2>/dev/null || echo "No log files in $(TMP_DIR)"

ps: ## Show running Docker services
	@echo "$(BLUE)Running Docker services:$(NC)"
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose ps

ps-local: ## Show local process PIDs
	@echo "$(BLUE)Local process PIDs:$(NC)"
	@for f in backend celery_worker celery_beat frontend; do \
		if [ -f $(TMP_DIR)/$$f.pid ]; then \
			printf "%-15s %s\n" "$$f" "`cat $(TMP_DIR)/$$f.pid`"; \
		else \
			printf "%-15s %s\n" "$$f" "(not running)"; \
		fi; \
	  done

monitor: ## Open monitoring dashboards
	@echo "$(BLUE)Opening monitoring dashboards...$(NC)"
	@open http://localhost:3030 2>/dev/null || xdg-open http://localhost:3030 2>/dev/null || echo "Grafana: http://localhost:3030"
	@open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 2>/dev/null || echo "Prometheus: http://localhost:9090"

##@ Bulk Upload & Seeding

bulk-upload: ## Bulk upload seed documents (usage: make bulk-upload SOURCE=/path/to/docs)
	@if [ -z "$(SOURCE)" ]; then \
		echo "$(RED)ERROR: SOURCE path required$(NC)"; \
		echo "$(YELLOW)Usage: make bulk-upload SOURCE=/path/to/seed/documents$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Starting bulk upload from: $(SOURCE)$(NC)"
	@$(CONDA_RUN) python tools/bulk_seed_upload.py --source $(SOURCE)

bulk-upload-dry-run: ## Test bulk upload without actually uploading (usage: make bulk-upload-dry-run SOURCE=/path)
	@if [ -z "$(SOURCE)" ]; then \
		echo "$(RED)ERROR: SOURCE path required$(NC)"; \
		echo "$(YELLOW)Usage: make bulk-upload-dry-run SOURCE=/path/to/seed/documents$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)DRY RUN: Simulating bulk upload from: $(SOURCE)$(NC)"
	@$(CONDA_RUN) python tools/bulk_seed_upload.py --source $(SOURCE) --dry-run

bulk-upload-managers: ## Bulk upload to managers only (usage: make bulk-upload-managers SOURCE=/path)
	@if [ -z "$(SOURCE)" ]; then \
		echo "$(RED)ERROR: SOURCE path required$(NC)"; \
		echo "$(YELLOW)Usage: make bulk-upload-managers SOURCE=/path/to/seed/documents$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Uploading to MANAGERS only from: $(SOURCE)$(NC)"
	@$(CONDA_RUN) python tools/bulk_seed_upload.py --source $(SOURCE) --managers-only

bulk-upload-analysts: ## Bulk upload to analysts only (usage: make bulk-upload-analysts SOURCE=/path)
	@if [ -z "$(SOURCE)" ]; then \
		echo "$(RED)ERROR: SOURCE path required$(NC)"; \
		echo "$(YELLOW)Usage: make bulk-upload-analysts SOURCE=/path/to/seed/documents$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Uploading to ANALYSTS only from: $(SOURCE)$(NC)"
	@$(CONDA_RUN) python tools/bulk_seed_upload.py --source $(SOURCE) --analysts-only

##@ Maintenance

clean: ## Clean up containers, volumes, and build artifacts
	@echo "$(RED)Cleaning up everything...$(NC)"
	@export PATH="/Applications/Docker.app/Contents/Resources/bin:$$PATH" && docker compose down -v
	@rm -rf app/__pycache__ app/**/__pycache__
	@rm -rf frontend/node_modules frontend/dist
	@rm -rf $(TMP_DIR)/*.pid $(TMP_DIR)/*.out
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

format: ## Format code (black, isort)
	@echo "$(BLUE)Formatting code...$(NC)"
	@cd app && $(CONDA_RUN) sh -c 'black . && isort .'
	@echo "$(GREEN)✅ Code formatted$(NC)"

lint: ## Lint code (flake8, mypy)
	@echo "$(BLUE)Linting code...$(NC)"
	@cd app && $(CONDA_RUN) sh -c 'flake8 . && mypy .'
	@echo "$(GREEN)✅ Linting complete$(NC)"

restart: stop dev ## Restart development stack

start: dev ## Alias for 'make dev' (start development)
