# Roadmap

## Foundation

- Typed application configuration and API lifecycle
- Formatting, linting, static analysis, tests, and continuous integration
- Architecture and requirements documentation

## Document ingestion

- Validated PDF, Markdown, and text uploads
- Extraction, normalization, configurable chunking, and duplicate detection
- Background indexing with retryable document states

## Retrieval and answers

- PostgreSQL full-text and Qdrant vector retrieval
- Reciprocal-rank fusion, filtering, and source citations
- Optional locally hosted answer generation

## Interface and evaluation

- Document upload, status, and search views
- Project-authored evaluation corpus and relevance judgements
- Reproducible retrieval metrics and failure analysis

## Delivery quality

- Containerized local environment and API smoke tests
- Dependency, image, and secret checks
- Verified documentation and screenshots from the running application
