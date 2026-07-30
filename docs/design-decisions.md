# Design Decisions

## PostgreSQL lexical search and Qdrant vector search

PostgreSQL is selected for document metadata, chunk content, ingestion state, and full-text
retrieval. Qdrant stores dense embeddings. This makes the lexical behaviour inspectable in SQL
and gives each store a narrow responsibility.

The cost is dual-store consistency. PostgreSQL therefore remains authoritative, vectors use
stable chunk identifiers, and only ready documents can appear in results.

## Reciprocal-rank fusion

PostgreSQL text-rank values and vector similarity values have different distributions. Hybrid
ranking will combine their result positions using reciprocal-rank fusion instead of assigning
an arbitrary shared scale. Evaluation data will later determine weights and candidate limits.

## Background ingestion

Extraction and embedding can take longer than an HTTP request should remain open. Uploads
therefore create an ingestion job and return `202 Accepted`. A separate worker performs the
pipeline and records visible status transitions.

RQ is intentionally smaller than a general distributed workflow platform for this first
release. Queue messages use JSON and contain identifiers only. More complex scheduling is not
currently justified.

## Source-aware chunking

The content-preparation pipeline offers fixed-window and section-aware strategies. Both use
overlapping token windows, but section-aware chunking prevents a chunk from crossing a Markdown
heading or PDF page boundary. Fixed-window chunking is useful as a retrieval-evaluation
baseline. Character offsets refer to the normalized document stream, while heading paths and
PDF page numbers remain the primary citation locators.

## Local embeddings by default

The default embedding adapter uses the small English BGE model through ONNX-based inference.
This supports semantic retrieval without paid credentials and keeps the model behind a narrow
interface. The trade-off is an initial model download, local CPU cost, and limited multilingual
quality.

## Optional answer generation

Retrieval and citations form the core product. Answer generation is a separate application
service and is disabled by default. The first optional adapter will target a locally hosted
model service. A generation outage must not prevent document search.

## Minimal server-rendered interface

The interface will use Jinja templates, local CSS, and small JavaScript modules. This provides a
usable upload and search experience without introducing a second package manager or a separate
front-end deployment.

## Local file storage

Uploaded files will initially be stored in a generated local data directory. A narrow storage
interface supports isolated tests and leaves room for object storage later. Object-storage
support itself is not part of the first release.
