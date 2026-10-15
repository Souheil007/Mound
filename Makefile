.PHONY: help infra infra-down dev lint test db-migrate db-downgrade clean

help:
	@echo "Mound Developer Commands:"
	@echo "  make infra        - Start PostgreSQL (pgvector) and Redis containers"
	@echo "  make infra-down   - Stop infrastructure containers"
	@echo "  make dev          - Start backend in reload mode"
	@echo "  make lint         - Run ruff linter on backend"
	@echo "  make test         - Run pytest test suite"
	@echo "  make db-migrate   - Run Alembic migrations to latest head"
	@echo "  make db-downgrade - Downgrade latest Alembic migration"
	@echo "  make clean        - Remove Python cache files and build artifacts"

infra:
	docker compose -f docker/docker-compose.yml up -d

infra-down:
	docker compose -f docker/docker-compose.yml down

dev:
	cd apps/backend && uv run uvicorn app.main:app --reload --port 8000

lint:
	cd apps/backend && uv run ruff check .
	cd apps/backend && uv run ruff format --check .

test:
	cd apps/backend && uv run pytest -v

db-migrate:
	cd apps/backend && uv run alembic upgrade head

db-downgrade:
	cd apps/backend && uv run alembic downgrade -1

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
