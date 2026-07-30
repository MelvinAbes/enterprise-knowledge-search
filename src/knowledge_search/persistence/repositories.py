from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from knowledge_search.domain import (
    Chunk,
    Document,
    DocumentMediaType,
    DocumentStatus,
    IngestionJob,
    IngestionJobStatus,
    SourceLocator,
)
from knowledge_search.persistence.models import (
    ChunkRecord,
    CorpusRevisionRecord,
    DocumentRecord,
    IngestionJobRecord,
)


class SqlAlchemyDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: Document) -> None:
        self._session.add(_document_to_record(document))

    def get(self, document_id: UUID) -> Document | None:
        record = self._session.get(DocumentRecord, document_id)
        return None if record is None else _record_to_document(record)

    def get_by_hash(self, sha256: str) -> Document | None:
        statement = select(DocumentRecord).where(DocumentRecord.sha256 == sha256)
        record = self._session.scalar(statement)
        return None if record is None else _record_to_document(record)

    def list(self, *, offset: int = 0, limit: int = 50) -> list[Document]:
        statement: Select[tuple[DocumentRecord]] = (
            select(DocumentRecord)
            .order_by(DocumentRecord.created_at.desc(), DocumentRecord.id)
            .offset(offset)
            .limit(limit)
        )
        return [_record_to_document(record) for record in self._session.scalars(statement)]

    def save(self, document: Document) -> None:
        record = self._session.get(DocumentRecord, document.id)
        if record is None:
            raise LookupError(f"document {document.id} does not exist")
        record.original_filename = document.original_filename
        record.storage_key = document.storage_key
        record.media_type = document.media_type.value
        record.sha256 = document.sha256
        record.size_bytes = document.size_bytes
        record.status = document.status.value
        record.failure_code = document.failure_code
        record.updated_at = document.updated_at

    def delete(self, document_id: UUID) -> None:
        record = self._session.get(DocumentRecord, document_id)
        if record is not None:
            self._session.delete(record)


class SqlAlchemyChunkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(self, chunks: list[Chunk]) -> None:
        self._session.add_all(_chunk_to_record(chunk) for chunk in chunks)

    def list_for_document(self, document_id: UUID) -> list[Chunk]:
        statement = (
            select(ChunkRecord)
            .where(ChunkRecord.document_id == document_id)
            .order_by(ChunkRecord.ordinal)
        )
        return [_record_to_chunk(record) for record in self._session.scalars(statement)]

    def delete_for_document(self, document_id: UUID) -> None:
        statement = select(ChunkRecord).where(ChunkRecord.document_id == document_id)
        for record in self._session.scalars(statement):
            self._session.delete(record)


class SqlAlchemyIngestionJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: IngestionJob) -> None:
        self._session.add(_job_to_record(job))

    def get(self, job_id: UUID) -> IngestionJob | None:
        record = self._session.get(IngestionJobRecord, job_id)
        return None if record is None else _record_to_job(record)

    def save(self, job: IngestionJob) -> None:
        record = self._session.get(IngestionJobRecord, job.id)
        if record is None:
            raise LookupError(f"ingestion job {job.id} does not exist")
        record.status = job.status.value
        record.attempt_count = job.attempt_count
        record.failure_code = job.failure_code
        record.updated_at = job.updated_at
        record.started_at = job.started_at
        record.finished_at = job.finished_at


class SqlAlchemyCorpusRevisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def increment(self) -> int:
        record = self._session.get(CorpusRevisionRecord, 1, with_for_update=True)
        if record is None:
            raise LookupError("corpus revision singleton does not exist")
        record.revision += 1
        return record.revision

    def current(self) -> int:
        record = self._session.get(CorpusRevisionRecord, 1)
        if record is None:
            raise LookupError("corpus revision singleton does not exist")
        return record.revision


def _document_to_record(document: Document) -> DocumentRecord:
    return DocumentRecord(
        id=document.id,
        original_filename=document.original_filename,
        storage_key=document.storage_key,
        media_type=document.media_type.value,
        sha256=document.sha256,
        size_bytes=document.size_bytes,
        status=document.status.value,
        failure_code=document.failure_code,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _record_to_document(record: DocumentRecord) -> Document:
    return Document(
        id=record.id,
        original_filename=record.original_filename,
        storage_key=record.storage_key,
        media_type=DocumentMediaType(record.media_type),
        sha256=record.sha256,
        size_bytes=record.size_bytes,
        status=DocumentStatus(record.status),
        failure_code=record.failure_code,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _chunk_to_record(chunk: Chunk) -> ChunkRecord:
    return ChunkRecord(
        id=chunk.id,
        document_id=chunk.document_id,
        ordinal=chunk.ordinal,
        text=chunk.text,
        token_count=chunk.token_count,
        content_hash=chunk.content_hash,
        section_path=list(chunk.locator.section_path),
        page_number=chunk.locator.page_number,
        char_start=chunk.locator.char_start,
        char_end=chunk.locator.char_end,
    )


def _record_to_chunk(record: ChunkRecord) -> Chunk:
    return Chunk(
        id=record.id,
        document_id=record.document_id,
        ordinal=record.ordinal,
        text=record.text,
        token_count=record.token_count,
        content_hash=record.content_hash,
        locator=SourceLocator(
            section_path=tuple(record.section_path),
            page_number=record.page_number,
            char_start=record.char_start,
            char_end=record.char_end,
        ),
    )


def _job_to_record(job: IngestionJob) -> IngestionJobRecord:
    return IngestionJobRecord(
        id=job.id,
        document_id=job.document_id,
        status=job.status.value,
        attempt_count=job.attempt_count,
        failure_code=job.failure_code,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _record_to_job(record: IngestionJobRecord) -> IngestionJob:
    return IngestionJob(
        id=record.id,
        document_id=record.document_id,
        status=IngestionJobStatus(record.status),
        attempt_count=record.attempt_count,
        failure_code=record.failure_code,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
    )
