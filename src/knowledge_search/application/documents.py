from dataclasses import dataclass
from pathlib import PurePath
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from knowledge_search.application.errors import (
    DocumentCleanupError,
    DocumentDeletionConflictError,
    DocumentNotFoundError,
    DuplicateDocumentError,
    IngestionJobNotFoundError,
)
from knowledge_search.domain import (
    Document,
    DocumentMediaType,
    DocumentStatus,
    IngestionJob,
)
from knowledge_search.ingestion.errors import (
    IngestionError,
    IngestionErrorCode,
    QueueDispatchError,
    VectorIndexError,
)
from knowledge_search.ingestion.ports import DocumentStore, IngestionQueue, VectorIndex
from knowledge_search.persistence import (
    PostgresSessionFactory,
    SqlAlchemyCorpusRevisionRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionJobRepository,
)

ALLOWED_EXTENSIONS = {
    DocumentMediaType.PDF: frozenset({".pdf"}),
    DocumentMediaType.MARKDOWN: frozenset({".md", ".markdown"}),
    DocumentMediaType.TEXT: frozenset({".txt"}),
}


@dataclass(frozen=True, slots=True)
class DocumentSubmission:
    document: Document
    job: IngestionJob


class DocumentSubmissionService:
    def __init__(
        self,
        *,
        sessions: PostgresSessionFactory,
        store: DocumentStore,
        queue: IngestionQueue,
        max_upload_bytes: int,
    ) -> None:
        self._sessions = sessions
        self._store = store
        self._queue = queue
        self._max_upload_bytes = max_upload_bytes

    def submit(
        self,
        *,
        filename: str,
        content_type: str | None,
        source: BinaryIO,
    ) -> DocumentSubmission:
        safe_filename = _validate_filename(filename)
        media_type = _validate_media_type(safe_filename, content_type)
        document_id = uuid4()
        stored = self._store.save(
            document_id=document_id,
            media_type=media_type,
            source=source,
            max_bytes=self._max_upload_bytes,
        )
        document = Document.create(
            document_id=document_id,
            original_filename=safe_filename,
            storage_key=stored.storage_key,
            media_type=media_type,
            sha256=stored.sha256,
            size_bytes=stored.size_bytes,
        ).queue()
        job = IngestionJob.create(document_id=document.id)

        try:
            with self._sessions.transaction() as session:
                document_repository = SqlAlchemyDocumentRepository(session)
                existing = document_repository.get_by_hash(document.sha256)
                if existing is not None:
                    raise DuplicateDocumentError(existing.id)
                document_repository.add(document)
                SqlAlchemyIngestionJobRepository(session).add(job)
        except IntegrityError as error:
            self._store.delete(stored.storage_key)
            with self._sessions.transaction() as session:
                existing = SqlAlchemyDocumentRepository(session).get_by_hash(document.sha256)
            if existing is not None:
                raise DuplicateDocumentError(existing.id) from error
            raise
        except Exception:
            self._store.delete(stored.storage_key)
            raise

        try:
            self._queue.enqueue(job.id)
        except QueueDispatchError as error:
            self._mark_dispatch_failed(document.id, job.id)
            raise QueueDispatchError(
                str(error),
                document_id=document.id,
                job_id=job.id,
            ) from error

        return DocumentSubmission(document=document, job=job)

    def _mark_dispatch_failed(self, document_id: UUID, job_id: UUID) -> None:
        with self._sessions.transaction() as session:
            document_repository = SqlAlchemyDocumentRepository(session)
            job_repository = SqlAlchemyIngestionJobRepository(session)
            document = document_repository.get(document_id)
            job = job_repository.get(job_id)
            if document is None or job is None:
                return
            document_repository.save(document.mark_failed("queue_unavailable"))
            job_repository.save(job.fail("queue_unavailable"))


class DocumentQueries:
    def __init__(self, sessions: PostgresSessionFactory) -> None:
        self._sessions = sessions

    def get_document(self, document_id: UUID) -> Document:
        with self._sessions.transaction() as session:
            document = SqlAlchemyDocumentRepository(session).get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    def list_documents(self, *, offset: int, limit: int) -> list[Document]:
        with self._sessions.transaction() as session:
            return SqlAlchemyDocumentRepository(session).list(offset=offset, limit=limit)

    def get_job(self, job_id: UUID) -> IngestionJob:
        with self._sessions.transaction() as session:
            job = SqlAlchemyIngestionJobRepository(session).get(job_id)
        if job is None:
            raise IngestionJobNotFoundError(job_id)
        return job


class DocumentDeletionService:
    def __init__(
        self,
        *,
        sessions: PostgresSessionFactory,
        store: DocumentStore,
        queue: IngestionQueue,
        vector_index: VectorIndex,
    ) -> None:
        self._sessions = sessions
        self._store = store
        self._queue = queue
        self._vector_index = vector_index

    def delete(self, document_id: UUID) -> None:
        with self._sessions.transaction() as session:
            repository = SqlAlchemyDocumentRepository(session)
            job_repository = SqlAlchemyIngestionJobRepository(session)
            document = repository.get(document_id)
            if document is None:
                raise DocumentNotFoundError(document_id)
            if document.status is not DocumentStatus.DELETING:
                if document.status not in {
                    DocumentStatus.READY,
                    DocumentStatus.FAILED,
                }:
                    raise DocumentDeletionConflictError(
                        document.id,
                        document.status.value,
                    )
                document = document.mark_deleting()
                repository.save(document)
                SqlAlchemyCorpusRevisionRepository(session).increment()
            job_ids = [job.id for job in job_repository.list_for_document(document.id)]

        try:
            for job_id in job_ids:
                self._queue.cancel(job_id)
        except QueueDispatchError as error:
            raise DocumentCleanupError("Queued ingestion cleanup failed.") from error
        try:
            self._vector_index.delete_document(document.id)
        except VectorIndexError as error:
            raise DocumentCleanupError("Vector document cleanup failed.") from error
        try:
            self._store.delete(document.storage_key)
        except OSError as error:
            raise DocumentCleanupError("Stored document cleanup failed.") from error

        with self._sessions.transaction() as session:
            SqlAlchemyDocumentRepository(session).delete(document.id)


def _validate_filename(filename: str) -> str:
    if (
        not filename
        or len(filename) > 255
        or filename != filename.strip()
        or "/" in filename
        or "\\" in filename
        or any(ord(character) < 32 for character in filename)
    ):
        raise IngestionError(
            IngestionErrorCode.INVALID_FILENAME,
            "Document filename is invalid.",
        )
    return filename


def _validate_media_type(filename: str, content_type: str | None) -> DocumentMediaType:
    normalized_type = (content_type or "").partition(";")[0].strip().lower()
    try:
        media_type = DocumentMediaType(normalized_type)
    except ValueError as error:
        raise IngestionError(
            IngestionErrorCode.UNSUPPORTED_MEDIA_TYPE,
            "Supported media types are PDF, Markdown, and plain text.",
        ) from error

    extension = PurePath(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS[media_type]:
        raise IngestionError(
            IngestionErrorCode.MEDIA_TYPE_MISMATCH,
            "Filename extension does not match the declared media type.",
        )
    return media_type
