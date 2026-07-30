"""PostgreSQL persistence adapters."""

from knowledge_search.persistence.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyCorpusRevisionRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionJobRepository,
)
from knowledge_search.persistence.search import PostgresSearchRepository
from knowledge_search.persistence.session import PostgresSessionFactory

__all__ = [
    "PostgresSearchRepository",
    "PostgresSessionFactory",
    "SqlAlchemyChunkRepository",
    "SqlAlchemyCorpusRevisionRepository",
    "SqlAlchemyDocumentRepository",
    "SqlAlchemyIngestionJobRepository",
]
