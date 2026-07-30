# Design Decisions

## PostgreSQL lexical search and Qdrant vector search

PostgreSQL is selected for document metadata, chunk content, ingestion state, and full-text
retrieval. Qdrant stores dense embeddings. This makes the lexical behaviour inspectable in SQL
and gives each store a narrow responsibility.

The cost is dual-store consistency. PostgreSQL therefore remains authoritative, vectors use
stable chunk identifiers, and only ready documents can appear in results.

## Reciprocal-rank fusion

PostgreSQL text-rank values and vector similarity values have different distributions. Hybrid
ranking combines their result positions using reciprocal-rank fusion instead of assigning an
arbitrary shared scale. The candidate multiplier and fusion constant remain configurable for
evaluation.

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
service and is disabled by default. The optional adapter targets a configurable
chat-completions HTTP service, so the same boundary can reach a local server or an explicitly
configured remote provider. Evidence is numbered and treated as untrusted data, and the API
returns the retrieved sources alongside any answer. A generation outage does not prevent use
of the search endpoint.

## Minimal server-rendered interface

The interface uses Jinja templates, local CSS, and small JavaScript modules. This provides a
usable upload and search experience without introducing a second package manager or a separate
front-end deployment.

## Local file storage

Uploaded files are stored in a generated local data directory. A narrow storage
interface supports isolated tests and leaves room for object storage later. Object-storage
support itself is not part of the first release.

## Minimal runtime images

Build tooling stays in multi-stage builder images. The application runtime copies only Python,
the locked virtual environment, required shared libraries, migrations, and packaged
application code into a non-root distroless image. Qdrant follows the same pattern using its
official release binary and configuration, without the unused administration UI.

PostgreSQL runs its official entrypoint directly as the `postgres` user, and Redis uses a
pinned Alpine image. This makes the local environment less convenient to debug from inside a
container, but reduces runtime packages and avoids granting a service a shell it does not need.
