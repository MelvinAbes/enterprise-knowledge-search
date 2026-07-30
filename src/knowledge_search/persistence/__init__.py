"""PostgreSQL persistence adapters."""

from knowledge_search.persistence.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyCorpusRevisionRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionJobRepository,
)
from knowledge_search.persistence.session import PostgresSessionFactory

__all__ = [
    "PostgresSessionFactory",
    "SqlAlchemyChunkRepository",
    "SqlAlchemyCorpusRevisionRepository",
    "SqlAlchemyDocumentRepository",
    "SqlAlchemyIngestionJobRepository",
]
