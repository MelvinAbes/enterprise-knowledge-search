UV ?= uv

.PHONY: sync format lint typecheck test check audit secret-scan run

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

check: lint typecheck test

audit:
	$(UV) run pip-audit --skip-editable --progress-spinner off

secret-scan:
	gitleaks dir . --redact --no-banner

run:
	$(UV) run uvicorn knowledge_search.main:app --reload \
		--host "$${EKS_HOST:-127.0.0.1}" \
		--port "$${EKS_PORT:-8000}"
