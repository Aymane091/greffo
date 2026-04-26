.PHONY: help infra-up infra-down dev-front dev-api dev-worker \
        test-front test-e2e test-back test-security \
        lint format migrate-new migrate-up migrate-down \
        build-front build-api test-db-create

API_DIR = apps/api

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## — Infra locale ————————————————————————————————————————

infra-up: ## Lance Postgres, Redis, MinIO
	docker compose up -d

infra-down: ## Arrête les services locaux
	docker compose down

## — Dev —————————————————————————————————————————————————

dev-front: ## Front Next.js sur :3000
	pnpm --filter web dev

dev-api: ## API FastAPI sur :8000 (hot reload)
	cd $(API_DIR) && uv run uvicorn src.main:app --reload --port 8000

dev-worker: ## Worker ARQ (transcription)
	cd $(API_DIR) && uv run arq src.workers.WorkerSettings

## — Tests ———————————————————————————————————————————————

test-db-create: ## Crée la DB de test greffo_test (à lancer une seule fois)
	createdb -O greffo greffo_test 2>/dev/null || true
	cd $(API_DIR) && TEST_DATABASE_URL=postgresql+asyncpg://greffo@localhost:5432/greffo_test \
		uv run alembic upgrade head

test-front: ## Tests unitaires front (Vitest)
	pnpm --filter web test

test-e2e: ## Tests E2E Playwright
	pnpm --filter web test:e2e

test-back: ## Tests back (pytest)
	cd $(API_DIR) && uv run pytest

test-security: ## Tests sécurité + isolation tenant
	cd $(API_DIR) && uv run pytest tests/security/

## — Lint / Format ———————————————————————————————————————

lint: ## Lint front + back
	pnpm lint
	cd $(API_DIR) && uv run ruff check .

format: ## Format front + back
	pnpm format
	cd $(API_DIR) && uv run ruff format .

## — DB Migrations ———————————————————————————————————————

migrate-new: ## Nouvelle migration  (usage: make migrate-new m="description")
	cd $(API_DIR) && uv run alembic revision --autogenerate -m "$(m)"

migrate-up: ## Applique toutes les migrations
	cd $(API_DIR) && uv run alembic upgrade head

migrate-down: ## Rollback d'une migration
	cd $(API_DIR) && uv run alembic downgrade -1

## — Build ————————————————————————————————————————————————

build-front: ## Build Next.js production
	pnpm --filter web build

build-api: ## Build image Docker API
	docker build -t greffo-api -f $(API_DIR)/Dockerfile .
