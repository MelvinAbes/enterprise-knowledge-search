from uuid import UUID

from knowledge_search.application.ingestion import IngestionJobProcessor
from knowledge_search.config import get_settings
from knowledge_search.ingestion import create_content_preparer
from knowledge_search.persistence import PostgresSessionFactory
from knowledge_search.providers import (
    FastEmbedProvider,
    LocalDocumentStore,
    QdrantVectorIndex,
)


def process_ingestion_job(job_id: str) -> None:
    settings = get_settings()
    sessions = PostgresSessionFactory(settings.database_url)
    processor = IngestionJobProcessor(
        sessions=sessions,
        store=LocalDocumentStore(settings.document_storage_path),
        content_preparer=create_content_preparer(settings),
        embeddings=FastEmbedProvider(
            model_name=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            cache_path=settings.model_cache_path,
        ),
        vector_index=QdrantVectorIndex(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
        ),
    )
    try:
        processor.process(UUID(job_id))
    finally:
        sessions.dispose()
