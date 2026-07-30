# External Dependencies and Licences

The application is licensed under Apache-2.0. Exact Python versions and hashes are recorded in
`uv.lock`. Container bases and services use immutable image digests.

## Runtime dependencies

| Dependency | Purpose | Licence consideration |
| --- | --- | --- |
| FastAPI and Pydantic | HTTP API and validation | MIT |
| HTTPX | Optional answer-provider HTTP client | BSD-3-Clause |
| Uvicorn | ASGI server | BSD-3-Clause |
| SQLAlchemy and Alembic | Persistence and migrations | MIT |
| Psycopg | PostgreSQL driver | LGPL-3.0-only |
| PostgreSQL | Metadata and lexical search | PostgreSQL Licence |
| Qdrant | Dense-vector retrieval | Apache-2.0 |
| Qdrant Python client | Vector-store adapter | MIT |
| FastEmbed | Local embedding inference | Apache-2.0 |
| BAAI/bge-small-en-v1.5 | Default English embedding model | MIT |
| Redis 7.2 | Cache and background queue | BSD-3-Clause |
| redis-py | Redis client | MIT |
| RQ | Background job processing | BSD-2-Clause |
| pypdf | Text extraction from PDFs | BSD-3-Clause |
| markdown-it-py | Markdown parsing | MIT |
| structlog | Structured application logging | MIT or Apache-2.0 |
| prometheus-client | Request and worker metrics | Apache-2.0 |
| Jinja2 | Server-rendered interface | BSD-3-Clause |

The Compose environment uses PostgreSQL 17.10, Redis 7.2.15, and Qdrant 1.18.3. PostgreSQL
receives current Alpine package updates and runs directly as its service user. The Qdrant
runtime copies the official release binary, configuration, and software bill of materials into
a minimal non-root image; its separate administration UI is not included.

## Development dependencies

| Dependency | Purpose |
| --- | --- |
| pytest | Automated tests |
| ReportLab | Deterministic PDF fixtures and demonstration-document generation |
| Ruff | Formatting and linting |
| mypy | Static type analysis |
| pip-audit | Python dependency vulnerability checks |
| Gitleaks | Secret scanning before pushes |
| Trivy | Container image vulnerability checks |

Resolved Python licences were reviewed from the lock file, and container sources are pinned to
explicit versions and digests. Demonstration documents and relevance judgments are
project-authored and covered by the repository licence.
