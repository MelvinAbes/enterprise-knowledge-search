import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from knowledge_search.domain import DocumentMediaType
from knowledge_search.ingestion.errors import IngestionError, IngestionErrorCode
from knowledge_search.ingestion.models import StoredDocument

MEDIA_SUFFIXES = {
    DocumentMediaType.PDF: ".pdf",
    DocumentMediaType.MARKDOWN: ".md",
    DocumentMediaType.TEXT: ".txt",
}
COPY_BUFFER_BYTES = 64 * 1024


class LocalDocumentStore:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        *,
        document_id: UUID,
        media_type: DocumentMediaType,
        source: BinaryIO,
        max_bytes: int,
    ) -> StoredDocument:
        suffix = MEDIA_SUFFIXES[media_type]
        storage_key = f"{document_id}/source{suffix}"
        target = self._resolve_key(storage_key)
        partial = target.with_suffix(f"{target.suffix}.uploading")
        try:
            target.parent.mkdir(parents=True, exist_ok=False)
        except FileExistsError as error:
            raise IngestionError(
                IngestionErrorCode.STORAGE_CONFLICT,
                "A stored document already exists for this identifier.",
            ) from error

        digest = hashlib.sha256()
        size_bytes = 0
        source.seek(0)
        try:
            with partial.open("xb") as destination:
                while block := source.read(COPY_BUFFER_BYTES):
                    size_bytes += len(block)
                    if size_bytes > max_bytes:
                        raise IngestionError(
                            IngestionErrorCode.FILE_TOO_LARGE,
                            f"Document exceeds the configured limit of {max_bytes} bytes.",
                        )
                    digest.update(block)
                    destination.write(block)
                destination.flush()
                os.fsync(destination.fileno())

            if size_bytes == 0:
                raise IngestionError(
                    IngestionErrorCode.EMPTY_UPLOAD,
                    "The uploaded document is empty.",
                )
            partial.replace(target)
        except Exception:
            partial.unlink(missing_ok=True)
            with suppress(OSError):
                target.parent.rmdir()
            raise

        return StoredDocument(
            storage_key=storage_key,
            sha256=digest.hexdigest(),
            size_bytes=size_bytes,
        )

    @contextmanager
    def open(self, storage_key: str) -> Iterator[BinaryIO]:
        path = self._resolve_key(storage_key)
        with path.open("rb") as source:
            yield source

    def delete(self, storage_key: str) -> None:
        path = self._resolve_key(storage_key)
        path.unlink(missing_ok=True)
        with suppress(OSError):
            path.parent.rmdir()

    def _resolve_key(self, storage_key: str) -> Path:
        candidate = (self._root / storage_key).resolve()
        if not candidate.is_relative_to(self._root) or candidate == self._root:
            raise IngestionError(
                IngestionErrorCode.INVALID_STORAGE_KEY,
                "Document storage key is invalid.",
            )
        return candidate
