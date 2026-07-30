# Requirements

## Problem statement

Teams accumulate operational and technical knowledge in PDF, Markdown, and text documents.
Users need to find both exact terminology and semantically related passages, then verify the
result against a clear source location. The service must provide useful retrieval without
requiring answer generation or paid credentials.

## Functional requirements

### Document ingestion

- Accept PDF, Markdown, and plain-text uploads through a REST API and web form.
- Stream uploads with configurable size limits and an allow-list of supported formats.
- Compute a content hash and reject or reuse duplicate uploads predictably.
- Extract page and heading structure where the source format provides it.
- Normalize text without discarding source locations needed for citations.
- Support fixed-window and section-aware chunking with configurable size and overlap.
- Generate dense embeddings with a local default model.
- Store document state and chunk metadata in PostgreSQL.
- Store searchable vectors in Qdrant.
- Expose queued, processing, ready, and failed ingestion states.

### Retrieval

- Support keyword, vector, and hybrid modes.
- Filter by document and media type.
- Combine lexical and vector rankings using an explicit, testable algorithm.
- Return a stable chunk identifier, excerpt, document name, section path, and page when known.
- Exclude documents that are not ready.
- Cache repeatable work without serving results from an older corpus revision.

### Answers

- Keep answer generation separate from retrieval.
- Operate with generation disabled by default.
- Support an optional locally hosted provider through a configuration-selected adapter.
- Restrict generated answers to retrieved evidence and return the supporting citations.
- Preserve search availability when generation is unavailable.

### Operations and interface

- Provide liveness, dependency-aware readiness, and request metrics endpoints.
- Produce structured logs with request and job correlation identifiers.
- Expose OpenAPI documentation and representative request examples.
- Provide a clean document-upload, status, and search interface.
- Provide a reproducible evaluation command and project-authored relevance data.

## Non-functional requirements

- Use typed Python with strict static analysis.
- Validate configuration at startup and inputs at service boundaries.
- Apply database schema changes through migrations.
- Make worker retries idempotent.
- Avoid logging document content or sensitive configuration.
- Run unit, integration, and API tests in continuous integration.
- Support a complete local environment through Docker Compose.
- Lock Python dependencies and pin service images before publication.
- Run dependency, container, and secret checks before publication.

## Acceptance criteria

- A supported document can be uploaded, indexed, searched, cited, and deleted through the API.
- The same evaluation query can be run in keyword, vector, and hybrid modes.
- Hybrid ranking is deterministic for identical inputs and index state.
- Search works when answer generation is disabled.
- A corrupt or unsupported document produces a safe failure without leaving it searchable.
- Reprocessing an interrupted job does not create duplicate chunks or vector points.
- Readiness reports unavailable required dependencies.
- The documented clean setup and smoke-test flow succeeds.

## Initial exclusions

- OCR and image understanding
- Authentication, authorization, and multitenancy
- Untrusted public deployment
- Distributed object storage
- Document editing or collaborative authoring
- Claims about scale, latency, or retrieval quality without measured evidence
