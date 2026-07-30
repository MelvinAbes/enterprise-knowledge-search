UV ?= uv

.PHONY: sync format lint typecheck test test-unit test-integration check audit secret-scan migrate migration-check run worker seed evaluate

sync:
	$(UV) sync --all-groups

format:
	$(UV) run ruff format src tests scripts
	$(UV) run ruff check --fix src tests scripts

lint:
	$(UV) run ruff format --check src tests scripts
	$(UV) run ruff check src tests scripts

typecheck:
	$(UV) run mypy src tests scripts

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

seed:
	$(UV) run python scripts/generate_demo_pdf.py
	$(UV) run python scripts/load_demo_data.py \
		--api-url "$${API_URL:-http://127.0.0.1:8000}"

evaluate:
	$(UV) run python scripts/evaluate_retrieval.py \
		--api-url "$${API_URL:-http://127.0.0.1:8000}" \
		--mode "$${MODE:-hybrid}" \
		--limit "$${LIMIT:-5}"
