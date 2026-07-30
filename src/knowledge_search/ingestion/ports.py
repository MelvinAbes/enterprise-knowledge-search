from contextlib import AbstractContextManager
from typing import BinaryIO, Protocol
from uuid import UUID

from knowledge_search.domain import Document, DocumentMediaType
from knowledge_search.domain.documents import Chunk
from knowledge_search.ingestion.models import ExtractedSection, StoredDocument


class DocumentStore(Protocol):
    def save(
        self,
        *,
        document_id: UUID,
        media_type: DocumentMediaType,
        source: BinaryIO,
        max_bytes: int,
    ) -> StoredDocument: ...

    def open(self, storage_key: str) -> AbstractContextManager[BinaryIO]: ...

    def delete(self, storage_key: str) -> None: ...


class DocumentExtractor(Protocol):
    def extract(self, source: BinaryIO) -> list[ExtractedSection]: ...


class IngestionQueue(Protocol):
    def enqueue(self, job_id: UUID) -> None: ...

    def cancel(self, job_id: UUID) -> None: ...

    def is_ready(self) -> bool: ...


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class VectorIndex(Protocol):
    def ensure_collection(self, *, dimensions: int) -> None: ...

    def upsert(
        self,
        *,
        document: Document,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None: ...

    def delete_document(self, document_id: UUID) -> None: ...

    def is_ready(self) -> bool: ...
