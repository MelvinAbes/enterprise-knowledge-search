# Implementation Checklist

## Design and foundation

- [x] Define functional and non-functional requirements.
- [x] Record architecture and major trade-offs.
- [x] Identify principal dependencies and licence considerations.
- [x] Initialize typed FastAPI application.
- [x] Configure formatting, linting, static analysis, tests, and continuous integration.
- [x] Add structured problem-detail error responses.
- [x] Add request correlation and structured logging.

## Ingestion

- [x] Add document, chunk, and ingestion-job models.
- [x] Add the initial PostgreSQL migration.
- [x] Validate streamed PDF, Markdown, and text uploads.
- [x] Implement safe local file storage with size limits and SHA-256 hashing.
- [x] Reject duplicate content during document registration.
- [x] Implement format-specific extraction and normalization.
- [x] Implement fixed-window and section-aware chunking.
- [x] Queue jobs using identifier-only JSON payloads.
- [x] Add deterministic chunk identifiers and idempotent lifecycle transitions.
- [x] Generate local embeddings and upsert Qdrant points.
- [x] Add recoverable document deletion across relational, vector, and file storage.

## Retrieval and answers

- [x] Implement PostgreSQL full-text search.
- [x] Implement Qdrant vector search.
- [x] Implement reciprocal-rank fusion and filters.
- [x] Assemble document, section, page, and chunk citations.
- [x] Add revision-aware query and result caching.
- [x] Add disabled and configurable HTTP answer-generation adapters.

## Interface and evaluation

- [ ] Add document upload and status views.
- [ ] Add keyword, vector, and hybrid search views.
- [ ] Create project-authored sample documents and relevance judgements.
- [ ] Report Recall@k, MRR, and NDCG without unsupported thresholds.
- [ ] Capture screenshots from the functioning application.

## Quality and publication

- [x] Add real PostgreSQL migration and repository integration tests.
- [x] Add adapter tests for Qdrant and a container integration test for Redis.
- [ ] Add API smoke tests through Docker Compose.
- [ ] Run dependency and container vulnerability scans.
- [ ] Verify setup instructions in a clean environment.
- [ ] Run a secret scan and repository-language review.
- [ ] Create private interview notes outside the repository.
- [ ] Present the final tree, checks, metadata, and commits for approval.
