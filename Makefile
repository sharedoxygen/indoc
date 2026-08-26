# inDoc SaaS Platform - Production-Ready Makefile
# Version: 2.0
# Date: 2025-10-13
#
# Following inDoc AI Prompt Engineering Guide principles:
# - No duplication: Single source of truth for each operation
# - Data integrity: Proper dependency management
# - Clear documentation: Self-documenting targets

.PHONY: help dev saas saas-local saas-prod install build test clean migrate \
	start stop stop-dev stop-saas stop-dev-processes saas-stop restart health status \
	logs monitor ps \
	conda-env conda-install local-e2e local-stop \
	test-backend test-frontend e2e-test seed-data \
	db-shell db-backup format lint \
	publish-worktree-ensure

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
COMPOSE_SAAS_PORTS:=docker-compose.saas-ports.yml
PUBLISH_BRANCH?=publish
PUBLISH_WORKTREE:=$(ROOT_DIR)/.worktrees/publish
STACK_MODE_FILE:=$(TMP_DIR)/stack.mode
STACK_MODE_SH:=$(ROOT_DIR)/scripts/dev/stack_mode.sh
PUBLISH_WORKTREE_SH:=$(ROOT_DIR)/scripts/dev/publish_worktree.sh
DOCKER_PATH:=/Applications/Docker.app/Contents/Resources/bin
export PATH:=$(DOCKER_PATH):$(PATH)
export TMP_DIR
export STACK_MODE_FILE
export PUBLISH_WORKTREE
export PUBLISH_BRANCH

# Port namespaces (exclusive modes — only one stack at a time)
DEV_API_PORT?=8001
DEV_FE_PORT?=5193
SAAS_API_PORT?=8011
SAAS_FE_PORT?=5293
export DEV_API_PORT
export SAAS_API_PORT

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# Compose against publish worktree (saas only). Fixed project name so stop matches containers.
COMPOSE_PROJECT_NAME?=indoc
export COMPOSE_PROJECT_NAME
COMPOSE_SAAS=docker compose --project-name $(COMPOSE_PROJECT_NAME) \
	--project-directory $(PUBLISH_WORKTREE) \
	--env-file $(ROOT_DIR)/.env \
	-f $(PUBLISH_WORKTREE)/$(COMPOSE_DEV) \
	-f $(ROOT_DIR)/$(COMPOSE_SAAS_PORTS)

##@ Help

help: ## Display this help message
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  inDoc SaaS Platform - Makefile Commands$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Development (Full Stack)

dev: ## Start full development stack (local processes, hot reload)
	@$(STACK_MODE_SH) assert-can-start dev
	@$(MAKE) conda-install
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  🚀 Starting Full Development Stack (current working tree)$(NC)"
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
	@if ! nc -z localhost 6379 2>/dev/null; then \
		echo "$(RED)❌ Redis not running on localhost:6379$(NC)"; \
		echo "$(YELLOW)   Start Redis first (brew services start redis)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Redis running (localhost:6379)$(NC)"
	@echo ""
	@echo "$(YELLOW)Stack Configuration:$(NC)"
	@echo "   • Mode:       dev (exclusive)"
	@echo "   • Source:     primary working tree ($$(git -C $(ROOT_DIR) rev-parse --abbrev-ref HEAD) @ $$(git -C $(ROOT_DIR) rev-parse --short HEAD))"
	@echo "   • Backend:    Local (conda) :$(DEV_API_PORT) - Hot Reload"
	@echo "   • Frontend:   Local (vite) :$(DEV_FE_PORT) - Hot Reload"
	@echo "   • Celery:     Local (conda)"
	@echo "   • Services:   Docker (ES, Qdrant, Monitoring)"
	@echo "   • Database:   PostgreSQL @ localhost:5432 (bare metal)"
	@echo "   • Cache:      Redis @ localhost:6379 (bare metal)"
	@echo ""
	@echo "$(YELLOW)Cleaning old dev processes...$(NC)"
	@$(MAKE) stop-dev-processes
	@sleep 2
	@echo "$(GREEN)✅ Clean$(NC)"
	@echo ""
	@echo "$(BLUE)Starting Docker services...$(NC)"
	@docker compose --project-name $(COMPOSE_PROJECT_NAME) -f $(ROOT_DIR)/$(COMPOSE_DEV) up -d elasticsearch qdrant prometheus grafana
	@echo "$(YELLOW)⏳ Waiting for services (10 seconds)...$(NC)"
	@sleep 10
	@mkdir -p $(TMP_DIR)
	@echo ""
	@echo "$(BLUE)Starting application processes...$(NC)"
	@cd app && nohup $(CONDA_RUN) sh -c 'export PYTHONPATH=$$PWD/..:$$PYTHONPATH && uvicorn main:app --host 0.0.0.0 --port $(DEV_API_PORT) --reload' > $(TMP_DIR)/backend.out 2>&1 & echo $$! > $(TMP_DIR)/backend.pid
	@echo "$(GREEN)✓$(NC) Backend starting on :$(DEV_API_PORT)..."
	@sleep 3
	@nohup $(CONDA_RUN) celery -A app.core.celery_app worker --pool=solo --loglevel=info --queues=celery,document_processing,search_indexing,llm_processing > $(TMP_DIR)/celery_worker.out 2>&1 & echo $$! > $(TMP_DIR)/celery_worker.pid
	@echo "$(GREEN)✓$(NC) Celery worker starting..."
	@sleep 1
	@nohup $(CONDA_RUN) celery -A app.core.celery_app beat --loglevel=info > $(TMP_DIR)/celery_beat.out 2>&1 & echo $$! > $(TMP_DIR)/celery_beat.pid
	@echo "$(GREEN)✓$(NC) Celery beat starting..."
	@sleep 1
	@cd frontend && nohup npm run dev -- --port $(DEV_FE_PORT) > $(TMP_DIR)/frontend.out 2>&1 & echo $$! > $(TMP_DIR)/frontend.pid
	@echo "$(GREEN)✓$(NC) Frontend starting on :$(DEV_FE_PORT)..."
	@sleep 5
	@$(STACK_MODE_SH) write dev "$$(git -C $(ROOT_DIR) rev-parse HEAD)"
	@echo ""
	@echo "$(GREEN)✨ Development stack ready!$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(BLUE)📍 Access Points (dev):$(NC)"
	@echo "   • Frontend:    http://localhost:$(DEV_FE_PORT)"
	@echo "   • API:         http://localhost:$(DEV_API_PORT)"
	@echo "   • API Docs:    http://localhost:$(DEV_API_PORT)/api/v1/docs"
	@echo "   • Grafana:     http://localhost:3030 (admin/admin)"
	@echo "   • Prometheus:  http://localhost:9090"
	@echo ""
	@echo "$(YELLOW)🛑 To stop: make stop$(NC)"
	@echo ""

stop-dev-processes: ## Internal: stop local dev app processes only
	@# Kill recorded wrappers + process groups (uvicorn --reload orphans otherwise survive)
	@for f in backend celery_worker celery_beat frontend; do \
		if [ -f $(TMP_DIR)/$$f.pid ]; then \
			pid=`tr -d '[:space:]' < $(TMP_DIR)/$$f.pid`; \
			if [ -n "$$pid" ]; then \
				kill -TERM -$$pid 2>/dev/null || true; \
				kill -TERM $$pid 2>/dev/null || true; \
			fi; \
		fi; \
	done
	@sleep 1
	@for f in backend celery_worker celery_beat frontend; do \
		if [ -f $(TMP_DIR)/$$f.pid ]; then \
			pid=`tr -d '[:space:]' < $(TMP_DIR)/$$f.pid`; \
			if [ -n "$$pid" ]; then \
				kill -KILL -$$pid 2>/dev/null || true; \
				kill -KILL $$pid 2>/dev/null || true; \
			fi; \
		fi; \
	done
	@pkill -9 -f "uvicorn main:app" 2>/dev/null || true
	@pkill -9 -f "vite.*$(DEV_FE_PORT)" 2>/dev/null || true
	@pkill -9 -f "celery -A app.core.celery_app worker" 2>/dev/null || true
	@pkill -9 -f "celery -A app.core.celery_app beat" 2>/dev/null || true
	@pkill -9 -f "conda run -n $(ENV_NAME).*uvicorn" 2>/dev/null || true
	@pkill -9 -f "conda run -n $(ENV_NAME).*celery" 2>/dev/null || true
	@# Free exclusive ports: reload workers are multiprocessing forks (cmdline ≠ uvicorn)
	@$(STACK_MODE_SH) free-port $(DEV_API_PORT)
	@$(STACK_MODE_SH) free-port $(DEV_FE_PORT)
	@rm -f $(TMP_DIR)/*.pid $(TMP_DIR)/*.out 2>/dev/null || true

stop-dev: stop-dev-processes ## Stop development stack (local procs + primary compose)
	@echo "$(YELLOW)🛑 Stopping development stack...$(NC)"
	@docker compose --project-name $(COMPOSE_PROJECT_NAME) -f $(ROOT_DIR)/$(COMPOSE_DEV) down 2>/dev/null || true
	@$(STACK_MODE_SH) free-port $(DEV_API_PORT)
	@$(STACK_MODE_SH) free-port $(DEV_FE_PORT)
	@$(STACK_MODE_SH) clear
	@if $(STACK_MODE_SH) port-in-use $(DEV_API_PORT); then \
		echo "$(RED)❌ Port :$(DEV_API_PORT) still in use after stop:$(NC)"; \
		$(STACK_MODE_SH) port-holders $(DEV_API_PORT); \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Development stack stopped$(NC)"

stop-saas: ## Stop saas stack (publish worktree compose only)
	@echo "$(YELLOW)🛑 Stopping saas stack (publish worktree)...$(NC)"
	@if [ -f $(ROOT_DIR)/.env ] && [ -d $(PUBLISH_WORKTREE) ]; then \
		ln -sfn $(ROOT_DIR)/.env $(PUBLISH_WORKTREE)/.env; \
		$(COMPOSE_SAAS) down 2>/dev/null || true; \
	fi
	@docker compose --project-name $(COMPOSE_PROJECT_NAME) -f $(ROOT_DIR)/$(COMPOSE_DEV) down 2>/dev/null || true
	@for c in indoc-backend indoc-celery-worker indoc-celery-beat indoc-flower \
		indoc-elasticsearch indoc-qdrant indoc-prometheus indoc-grafana; do \
		docker rm -f $$c 2>/dev/null || true; \
	done
	@$(STACK_MODE_SH) free-port $(SAAS_API_PORT)
	@$(STACK_MODE_SH) clear
	@echo "$(GREEN)✅ SaaS stack stopped$(NC)"

stop: ## Stop the active stack (dev or saas); clears mode lock
	@echo "$(YELLOW)[$$(date '+%Y-%m-%d %H:%M:%S')] Stopping stack$(NC)"
	@mode="$$($(STACK_MODE_SH) detect)"; \
	echo "$(YELLOW)🛑 Stopping stack (detected: $$mode)...$(NC)"; \
	case "$$mode" in \
		saas) $(MAKE) stop-saas ;; \
		dev) $(MAKE) stop-dev ;; \
		stale:*) $(MAKE) stop-dev-processes; $(MAKE) stop-saas; $(STACK_MODE_SH) clear ;; \
		none) $(MAKE) stop-dev-processes; $(MAKE) stop-saas; $(STACK_MODE_SH) clear; echo "$(GREEN)✅ Nothing live (cleaned leftovers)$(NC)" ;; \
		*) $(MAKE) stop-dev-processes; $(MAKE) stop-saas; $(STACK_MODE_SH) clear ;; \
	esac
	@echo "$(GREEN)[$$(date '+%Y-%m-%d %H:%M:%S')] Stop complete$(NC)"

celery-cleanup: ## Clean up local Celery workers (dev)
	@pkill -f "celery.*worker" 2>/dev/null || true
	@pkill -f "celery.*beat" 2>/dev/null || true
	@rm -f $(TMP_DIR)/celery_worker.pid $(TMP_DIR)/celery_beat.pid 2>/dev/null || true

##@ SaaS Platform (Production Simulation)

publish-worktree-ensure: ## Ensure .worktrees/publish tracks local publish branch
	@$(PUBLISH_WORKTREE_SH) ensure >/dev/null

saas: saas-local ## Start SaaS from local publish branch (docker compose)

saas-local: ## Simulate SaaS from publish worktree (exclusive vs make dev)
	@$(STACK_MODE_SH) assert-can-start saas
	@$(MAKE) publish-worktree-ensure
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  🚀 Starting SaaS Stack (local '$(PUBLISH_BRANCH)' worktree)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@if [ ! -f $(ROOT_DIR)/.env ]; then \
		echo "$(RED)❌ Missing $(ROOT_DIR)/.env (required for saas compose)$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📋 Prerequisites Check:$(NC)"
	@if ! docker info > /dev/null 2>&1; then \
		echo "$(RED)❌ Docker is not running. Start Docker Desktop first.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Docker running$(NC)"
	@if ! nc -z localhost 5432 2>/dev/null; then \
		echo "$(RED)❌ PostgreSQL not running on localhost:5432$(NC)"; \
		echo "$(YELLOW)   Start PostgreSQL first (brew services start postgresql@17)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ PostgreSQL running (localhost:5432)$(NC)"
	@if ! nc -z localhost 6379 2>/dev/null; then \
		echo "$(RED)❌ Redis not running on localhost:6379$(NC)"; \
		echo "$(YELLOW)   Start Redis first (brew services start redis)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Redis running (localhost:6379)$(NC)"
	@PUBLISH_SHA="$$(git -C $(PUBLISH_WORKTREE) rev-parse HEAD)"; \
	echo "$(GREEN)✅ Source: $(PUBLISH_BRANCH) @ $$PUBLISH_SHA$(NC)"; \
	echo "   Worktree: $(PUBLISH_WORKTREE)"; \
	ln -sfn $(ROOT_DIR)/.env $(PUBLISH_WORKTREE)/.env; \
	mkdir -p $(PUBLISH_WORKTREE)/data/uploads $(ROOT_DIR)/tmp; \
	echo ""; \
	echo "$(BLUE)🐳 Starting Docker services from publish worktree:$(NC)"; \
	echo "   • Backend API :$(SAAS_API_PORT) (host; container :8000)"; \
	echo "   • Frontend    :$(SAAS_FE_PORT) reserved (not in compose; API-focused saas)"; \
	echo "   • ES / Qdrant / Prometheus / Grafana / Celery"; \
	echo ""; \
	echo "$(YELLOW)⚠️  PostgreSQL + Redis run OUTSIDE Docker (bare metal)$(NC)"; \
	echo ""; \
	$(COMPOSE_SAAS) up -d --build; \
	echo ""; \
	echo "$(YELLOW)⏳ Waiting for services (30 seconds)...$(NC)"; \
	sleep 30; \
	echo ""; \
	$(MAKE) saas-health; \
	$(STACK_MODE_SH) write saas "$$PUBLISH_SHA"; \
	echo ""; \
	echo "$(GREEN)✨ SaaS stack running from publish$(NC)"; \
	echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"; \
	echo ""; \
	echo "$(BLUE)📍 Access Points (saas):$(NC)"; \
	echo "   • Backend API:       http://localhost:$(SAAS_API_PORT)"; \
	echo "   • API Docs:          http://localhost:$(SAAS_API_PORT)/api/v1/docs"; \
	echo "   • Frontend port:     $(SAAS_FE_PORT) (reserved; not started by compose)"; \
	echo "   • Grafana:           http://localhost:3030 (admin/admin)"; \
	echo "   • Prometheus:        http://localhost:9090"; \
	echo "   • Qdrant Dashboard:  http://localhost:6333/dashboard"; \
	echo ""; \
	echo "$(YELLOW)💾 Database:$(NC) PostgreSQL @ localhost:5432 (bare metal)"; \
	echo "$(YELLOW)📦 Cache:$(NC)    Redis @ localhost:6379 (bare metal)"; \
	echo ""; \
	echo "$(BLUE)📝 Default Credentials:$(NC)"; \
	echo "   • Admin:  admin / AdminSecure123!"; \
	echo ""; \
	echo "$(YELLOW)🛑 To stop: make stop$(NC)"; \
	echo ""

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

saas-stop: stop-saas ## Stop saas stack only (publish worktree compose)

saas-stop-prod: ## Stop production SaaS platform
	@echo "$(YELLOW)🛑 Stopping production SaaS platform...$(NC)"
	@docker compose -f $(COMPOSE_PROD) down
	@echo "$(GREEN)✅ Production SaaS platform stopped$(NC)"

saas-health: ## Check health of SaaS services (saas port namespace)
	@echo "$(BLUE)🔍 Checking SaaS service health...$(NC)"
	@printf "PostgreSQL: "; pg_isready -h localhost -p 5432 >/dev/null 2>&1 && echo "$(GREEN)✅ bare metal$(NC)" || echo "$(RED)❌$(NC)"
	@printf "Redis:      "; redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q PONG && echo "$(GREEN)✅ bare metal$(NC)" || echo "$(RED)❌$(NC)"
	@printf "Elasticsearch: "; curl -sf http://localhost:9200/_cluster/health >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(YELLOW)⚠️$(NC)"
	@printf "Qdrant:     "; curl -sf http://localhost:6333/healthz >/dev/null && echo "$(GREEN)✅$(NC)" || echo "$(YELLOW)⚠️$(NC)"
	@printf "Backend:    "; curl -sf http://localhost:$(SAAS_API_PORT)/ >/dev/null && echo "$(GREEN)✅ :$(SAAS_API_PORT)$(NC)" || echo "$(YELLOW)⚠️ :$(SAAS_API_PORT)$(NC)"
	@printf "Frontend:   "; curl -sfI http://localhost:$(SAAS_FE_PORT) >/dev/null && echo "$(GREEN)✅ :$(SAAS_FE_PORT)$(NC)" || echo "$(YELLOW)⚠️ :$(SAAS_FE_PORT) (not in compose)$(NC)"

status: ## Show active stack mode, source SHA, ports, health
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  inDoc stack status$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@detected="$$($(STACK_MODE_SH) detect)"; \
	echo "Detected:  $$detected"; \
	if [ -f "$(STACK_MODE_FILE)" ]; then \
		echo "Lock file: $(STACK_MODE_FILE)"; \
		grep -E '^(MODE|SHA|STARTED_AT|DEV_API_PORT|SAAS_API_PORT)=' "$(STACK_MODE_FILE)" || true; \
	else \
		echo "Lock file: (none)"; \
	fi; \
	echo ""; \
	echo "$(YELLOW)Port namespaces$(NC)"; \
	echo "  dev  API/FE: $(DEV_API_PORT) / $(DEV_FE_PORT)"; \
	echo "  saas API/FE: $(SAAS_API_PORT) / $(SAAS_FE_PORT)"; \
	echo ""; \
	echo "$(YELLOW)Source$(NC)"; \
	echo "  primary: $$(git -C $(ROOT_DIR) rev-parse --abbrev-ref HEAD) @ $$(git -C $(ROOT_DIR) rev-parse --short HEAD)"; \
	if git -C $(ROOT_DIR) show-ref --verify --quiet refs/heads/$(PUBLISH_BRANCH); then \
		echo "  publish: $(PUBLISH_BRANCH) @ $$(git -C $(ROOT_DIR) rev-parse --short refs/heads/$(PUBLISH_BRANCH))"; \
	else \
		echo "  publish: (missing local branch)"; \
	fi; \
	if [ -d "$(PUBLISH_WORKTREE)" ]; then \
		echo "  worktree: $(PUBLISH_WORKTREE) @ $$(git -C $(PUBLISH_WORKTREE) rev-parse --short HEAD 2>/dev/null || echo '?')"; \
	else \
		echo "  worktree: (not created)"; \
	fi; \
	echo ""; \
	echo "$(YELLOW)Health$(NC)"; \
	printf "  PostgreSQL: "; pg_isready -h localhost -p 5432 >/dev/null 2>&1 && echo "$(GREEN)ok$(NC)" || echo "$(RED)down$(NC)"; \
	printf "  Redis:      "; redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q PONG && echo "$(GREEN)ok$(NC)" || echo "$(RED)down$(NC)"; \
	printf "  Dev API:    "; curl -sf http://localhost:$(DEV_API_PORT)/ >/dev/null && echo "$(GREEN)up :$(DEV_API_PORT)$(NC)" || echo "down :$(DEV_API_PORT)"; \
	printf "  SaaS API:   "; curl -sf http://localhost:$(SAAS_API_PORT)/ >/dev/null && echo "$(GREEN)up :$(SAAS_API_PORT)$(NC)" || echo "down :$(SAAS_API_PORT)"; \
	printf "  Dev FE:     "; curl -sfI http://localhost:$(DEV_FE_PORT) >/dev/null && echo "$(GREEN)up :$(DEV_FE_PORT)$(NC)" || echo "down :$(DEV_FE_PORT)"; \
	echo ""

saas-health-prod: ## Check health of production SaaS services
	@echo "$(BLUE)🔍 Checking production SaaS service health...$(NC)"
	@echo -n "PostgreSQL: "; pg_isready -h localhost -p 5432 >/dev/null 2>&1 && echo "$(GREEN)✅ external$(NC)" || echo "$(RED)❌$(NC)"
	@echo -n "Redis:      "; redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q PONG && echo "$(GREEN)✅ external$(NC)" || echo "$(RED)❌$(NC)"
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
	@echo "$(BLUE)Ensuring dependencies (quiet)...$(NC)"
	@cd app && $(CONDA_RUN) python -m pip install -q -r ../requirements.txt
	@cd frontend && npm install --silent --no-fund --no-audit
	@echo "$(GREEN)✅ Dependencies ready$(NC)"

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

db-shell: ## Open PostgreSQL shell (external/bare-metal; requires POSTGRES_PASSWORD)
	@if [ -z "$$POSTGRES_PASSWORD" ]; then echo "$(RED)POSTGRES_PASSWORD is required$(NC)"; exit 1; fi
	@echo "$(BLUE)Opening PostgreSQL shell (host :5432 / indoc)...$(NC)"
	@psql "postgresql://$${POSTGRES_USER:-indoc_user}:$${POSTGRES_PASSWORD}@$${POSTGRES_HOST:-127.0.0.1}:$${POSTGRES_PORT:-5432}/$${POSTGRES_DB:-indoc}"

db-backup: ## Backup database to backups/ directory (external/bare-metal; requires POSTGRES_PASSWORD)
	@if [ -z "$$POSTGRES_PASSWORD" ]; then echo "$(RED)POSTGRES_PASSWORD is required$(NC)"; exit 1; fi
	@echo "$(BLUE)Backing up database (host :5432 / indoc)...$(NC)"
	@mkdir -p backups
	@pg_dump "postgresql://$${POSTGRES_USER:-indoc_user}:$${POSTGRES_PASSWORD}@$${POSTGRES_HOST:-127.0.0.1}:$${POSTGRES_PORT:-5432}/$${POSTGRES_DB:-indoc}" > backups/indoc_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Database backed up to backups/$(NC)"

db-isolate: ## Ensure local Postgres/Redis isolation (requires POSTGRES_SUPER_PASSWORD)
	@if [ -z "$$POSTGRES_SUPER_PASSWORD" ]; then echo "$(RED)POSTGRES_SUPER_PASSWORD is required$(NC)"; exit 1; fi
	@echo "$(BLUE)Applying bare-metal DB isolation...$(NC)"
	@psql "postgresql://postgres:$${POSTGRES_SUPER_PASSWORD}@127.0.0.1:5432/postgres" -v ON_ERROR_STOP=1 -f scripts/setup/ensure_baremetal_isolation.sql
	@redis-cli -n 2 ping | grep -q PONG && echo "$(GREEN)✅ Redis DB 2 reachable$(NC)" || echo "$(RED)❌ Redis DB 2 not reachable$(NC)"
	@echo "$(GREEN)✅ Isolation ready (indoc / indoc_user; Redis /2)$(NC)"

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

start: ## Alias for 'make dev' (start development)
	@echo "$(BLUE)[$$(date '+%Y-%m-%d %H:%M:%S')] Starting development stack$(NC)"
	@$(MAKE) dev
	@echo "$(GREEN)[$$(date '+%Y-%m-%d %H:%M:%S')] Start complete$(NC)"
