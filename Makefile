UV ?= uv
TRIVY_IMAGE ?= aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f

.PHONY: sync format lint typecheck test test-unit test-integration check audit secret-scan migrate migration-check run worker compose-validate container-build container-scan compose-up compose-down smoke seed evaluate

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
	$(UV) run python -m knowledge_search.worker.main

compose-validate:
	docker compose config --quiet

container-build:
	docker compose build

container-scan:
	mkdir -p .cache/trivy
	docker run --rm \
		--volume /var/run/docker.sock:/var/run/docker.sock \
		--volume "$(CURDIR)/.cache/trivy:/root/.cache/" \
		$(TRIVY_IMAGE) image --severity HIGH,CRITICAL --scanners vuln \
		enterprise-knowledge-search:local
	docker run --rm \
		--volume /var/run/docker.sock:/var/run/docker.sock \
		--volume "$(CURDIR)/.cache/trivy:/root/.cache/" \
		$(TRIVY_IMAGE) image --severity HIGH,CRITICAL --scanners vuln \
		enterprise-knowledge-search-postgres:local
	docker run --rm \
		--volume /var/run/docker.sock:/var/run/docker.sock \
		--volume "$(CURDIR)/.cache/trivy:/root/.cache/" \
		$(TRIVY_IMAGE) image --severity HIGH,CRITICAL --scanners vuln \
		redis:7.2.15-alpine3.21@sha256:05a97a479bc73de66f087dc05b569010772880f778cc8671fa6b8aadee32e5c6
	docker run --rm \
		--volume /var/run/docker.sock:/var/run/docker.sock \
		--volume "$(CURDIR)/.cache/trivy:/root/.cache/" \
		$(TRIVY_IMAGE) image --severity HIGH,CRITICAL --scanners vuln \
		enterprise-knowledge-search-qdrant:local

compose-up:
	docker compose up --build --wait

compose-down:
	docker compose down

smoke:
	$(UV) run python scripts/smoke_test.py

seed:
	$(UV) run python scripts/generate_demo_pdf.py
	$(UV) run python scripts/load_demo_data.py \
		--api-url "$${API_URL:-http://127.0.0.1:8000}"

evaluate:
	$(UV) run python scripts/evaluate_retrieval.py \
		--api-url "$${API_URL:-http://127.0.0.1:8000}" \
		--mode "$${MODE:-hybrid}" \
		--limit "$${LIMIT:-5}"
