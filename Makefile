UV ?= uv

.PHONY: sync format lint typecheck test test-unit test-integration check audit secret-scan migrate migration-check run worker

sync:
	$(UV) sync --all-groups

format:
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

lint:
	$(UV) run ruff format --check src tests
	$(UV) run ruff check src tests

typecheck:
	$(UV) run mypy src tests

test:
	$(UV) run pytest

test-unit:
	$(UV) run pytest -m "not integration"

test-integration:
	$(UV) run pytest -m integration

check: lint typecheck test

audit:
	$(UV) run pip-audit --skip-editable --progress-spinner off

secret-scan:
	gitleaks dir . --redact --no-banner

migrate:
	$(UV) run alembic upgrade head

migration-check:
	$(UV) run alembic check

run:
	$(UV) run uvicorn knowledge_search.main:app --reload \
		--host "$${EKS_HOST:-127.0.0.1}" \
		--port "$${EKS_PORT:-8000}"

worker:
	$(UV) run rq worker \
		--url "$${EKS_REDIS_URL:-redis://127.0.0.1:6379/0}" \
		--serializer json \
		"$${EKS_INGESTION_QUEUE_NAME:-document-ingestion}"
