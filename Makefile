COMPOSE := docker compose

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@echo ""
	@echo "Beancount Bot — Docker Commands"
	@echo "================================"
	@echo ""
	@echo "  make setup      Copy .env.example → .env (first-time setup)"
	@echo "  make build      Build all Docker images"
	@echo "  make up         Build + migrate + start all services"
	@echo "  make down       Stop all services"
	@echo "  make restart    Restart all services"
	@echo "  make migrate    Run database migrations"
	@echo "  make logs       Tail logs for all services"
	@echo "  make ps         Show service status"
	@echo "  make clean      Stop services and remove all volumes (destructive)"
	@echo ""
	@echo "  make logs-backend   Tail backend logs"
	@echo "  make logs-worker    Tail worker logs"
	@echo "  make logs-frontend  Tail frontend logs"
	@echo ""
	@echo "  make shell-backend  Open shell in backend container"
	@echo "  make shell-worker   Open shell in worker container"
	@echo "  make shell-db       Open psql in postgres container"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

.PHONY: setup
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — edit it and set ANTHROPIC_API_KEY"; \
	else \
		echo ".env already exists, skipping"; \
	fi

# ── Build ─────────────────────────────────────────────────────────────────────

.PHONY: build
build:
	$(COMPOSE) build

# ── Start ─────────────────────────────────────────────────────────────────────

.PHONY: up
up:
	@echo ">>> Building images..."
	$(COMPOSE) build
	@echo ">>> Starting infrastructure (postgres, redis)..."
	$(COMPOSE) up -d postgres redis
	@echo ">>> Waiting for postgres to be healthy..."
	$(COMPOSE) run --rm migrate
	@echo ">>> Starting application services..."
	$(COMPOSE) up -d backend worker frontend
	@echo ""
	@echo "All services are running:"
	@echo "  Frontend  →  http://localhost:3000"
	@echo "  Backend   →  http://localhost:8000"
	@echo "  API Docs  →  http://localhost:8000/docs"
	@echo ""

# ── Stop ──────────────────────────────────────────────────────────────────────

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: restart
restart:
	$(COMPOSE) restart backend worker frontend

# ── Migrations ────────────────────────────────────────────────────────────────

.PHONY: migrate
migrate:
	$(COMPOSE) run --rm migrate

# ── Logs ──────────────────────────────────────────────────────────────────────

.PHONY: logs
logs:
	$(COMPOSE) logs -f

logs-%:
	$(COMPOSE) logs -f $*

# ── Status ────────────────────────────────────────────────────────────────────

.PHONY: ps
ps:
	$(COMPOSE) ps

# ── Shell access ──────────────────────────────────────────────────────────────

shell-%:
	$(COMPOSE) exec $* sh

.PHONY: shell-db
shell-db:
	$(COMPOSE) exec postgres psql -U postgres -d beancount_bot

# ── Clean ─────────────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	@echo "WARNING: This will delete all containers and volumes (database data will be lost)."
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(COMPOSE) down -v --remove-orphans
	@echo "Cleaned."
