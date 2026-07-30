# External Dependencies and Licences

The application is licensed under Apache-2.0. Exact package versions will be recorded in
`uv.lock` as each implementation slice is added.

## Runtime dependencies

| Dependency | Purpose | Licence consideration |
| --- | --- | --- |
| FastAPI and Pydantic | HTTP API and validation | MIT |
| Uvicorn | ASGI server | BSD-3-Clause |
| SQLAlchemy and Alembic | Persistence and migrations | MIT |
| Psycopg | PostgreSQL driver | LGPL-3.0-only |
| PostgreSQL | Metadata and lexical search | PostgreSQL Licence |
| Qdrant | Dense-vector retrieval | Apache-2.0 |
| Qdrant Python client | Vector-store adapter | MIT |
| FastEmbed | Local embedding inference | Apache-2.0 |
| BAAI/bge-small-en-v1.5 | Default English embedding model | MIT |
| Redis | Cache and background queue | Redis 8 offers AGPL-3.0 as an open-source option |
| RQ | Background job processing | BSD-2-Clause |
| pypdf | Text extraction from PDFs | BSD-3-Clause |
| markdown-it-py | Markdown parsing | MIT |
| structlog | Structured application logging | MIT or Apache-2.0 |
| prometheus-client | Request and worker metrics | Apache-2.0 |
| Jinja2 | Server-rendered interface | BSD-3-Clause |

Redis and Qdrant run as unmodified external services. The repository will reference their
upstream container images rather than redistributing modified service source.

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

Before publication, resolved Python licences will be reviewed from the lock file and container
images will be pinned to explicit versions. Demonstration documents and relevance judgements
will be project-authored and covered by the repository licence.
