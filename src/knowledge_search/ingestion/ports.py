from contextlib import AbstractContextManager
from typing import BinaryIO, Protocol
from uuid import UUID

from knowledge_search.domain import DocumentMediaType
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
