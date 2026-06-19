.DEFAULT_GOAL := help

# ---- Environment ----
.PHONY: env
env: ## Create .env from .env.example if it does not exist
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	@test -f .env && echo ".env is present"

# ---- Docker infra (postgres, redis, clickhouse) ----
.PHONY: up
up: ## Start infra services in the background
	docker compose up -d postgres redis clickhouse

.PHONY: down
down: ## Stop infra services
	docker compose down

.PHONY: ps
ps: ## Show running compose services
	docker compose ps

.PHONY: logs
logs: ## Tail logs for all infra services
	docker compose logs -f postgres redis clickhouse

.PHONY: restart
restart: down up ## Restart infra services

.PHONY: nuke
nuke: ## Stop services and DELETE all data volumes
	docker compose down -v

# ---- Health checks ----
.PHONY: health
health: ## Check that infra services respond
	@echo "Postgres:"   && docker exec stagehand-postgres pg_isready -U $${POSTGRES_USER:-stagehand} || true
	@echo "Redis:"      && docker exec stagehand-redis redis-cli ping || true
	@echo "ClickHouse:" && curl -s http://localhost:8123/ping || true
	@echo ""

# ---- Help ----
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
