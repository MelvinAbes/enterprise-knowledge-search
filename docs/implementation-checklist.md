# Implementation Checklist

## Design and foundation

- [x] Define functional and non-functional requirements.
- [x] Record architecture and major trade-offs.
- [x] Identify principal dependencies and licence considerations.
- [x] Initialize typed FastAPI application.
- [x] Configure formatting, linting, static analysis, tests, and continuous integration.
- [ ] Add structured problem-detail error responses.
- [ ] Add request correlation and structured logging.

## Ingestion

- [x] Add document, chunk, and ingestion-job models.
- [x] Add the initial PostgreSQL migration.
- [ ] Validate streamed PDF, Markdown, and text uploads.
- [ ] Implement safe local file storage and SHA-256 duplicate detection.
- [ ] Implement format-specific extraction and normalization.
- [ ] Implement fixed-window and section-aware chunking.
- [ ] Queue jobs using identifier-only JSON payloads.
- [x] Add deterministic chunk identifiers and idempotent lifecycle transitions.
- [ ] Generate local embeddings and upsert Qdrant points.

## Retrieval and answers

- [ ] Implement PostgreSQL full-text search.
- [ ] Implement Qdrant vector search.
- [ ] Implement reciprocal-rank fusion and filters.
- [ ] Assemble document, section, page, and chunk citations.
- [ ] Add revision-aware query and result caching.
- [ ] Add disabled and locally hosted answer-generation adapters.

## Interface and evaluation

- [ ] Add document upload and status views.
- [ ] Add keyword, vector, and hybrid search views.
- [ ] Create project-authored sample documents and relevance judgements.
- [ ] Report Recall@k, MRR, and NDCG without unsupported thresholds.
- [ ] Capture screenshots from the functioning application.

## Quality and publication

- [x] Add real PostgreSQL migration and repository integration tests.
- [ ] Add integration tests for Qdrant and Redis.
- [ ] Add API smoke tests through Docker Compose.
- [ ] Run dependency and container vulnerability scans.
- [ ] Verify setup instructions in a clean environment.
- [ ] Run a secret scan and repository-language review.
- [ ] Create private interview notes outside the repository.
- [ ] Present the final tree, checks, metadata, and commits for approval.
