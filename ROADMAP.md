# Roadmap

## Delivered in the initial release

- Typed FastAPI service, database migrations, and structured operational telemetry
- Validated document ingestion with background extraction, chunking, embedding, and indexing
- PostgreSQL lexical search, Qdrant vector search, reciprocal-rank fusion, and citations
- Optional grounded answer generation with search-only operation as the default
- Browser interface, project-authored evaluation corpus, and reproducible retrieval metrics
- Non-root container environment, clean-start smoke test, CI, dependency audit, and secret scan

## Next

- Add OCR and table-aware extraction while preserving page-level citation coordinates.
- Add an operator reconciliation command for partial relational/vector-store failures.
- Expand relevance judgments and evaluate rerankers and multilingual embedding models.
- Add authentication, workspace isolation, object storage, and rate limiting before any
  untrusted deployment.
