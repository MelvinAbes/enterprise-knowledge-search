from uuid import UUID

from sqlalchemy import desc, func, select

from knowledge_search.domain import DocumentMediaType, SourceLocator
from knowledge_search.persistence.models import ChunkRecord, DocumentRecord
from knowledge_search.persistence.session import PostgresSessionFactory
from knowledge_search.retrieval.models import (
    RetrievalCandidate,
    SearchableChunk,
    SearchFilters,
)


class PostgresSearchRepository:
    def __init__(self, sessions: PostgresSessionFactory) -> None:
        self._sessions = sessions

    def keyword_candidates(
        self,
        *,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> list[RetrievalCandidate]:
        ts_query = func.websearch_to_tsquery("english", query)
        rank = func.ts_rank_cd(ChunkRecord.search_vector, ts_query).label("rank")
        statement = (
            select(ChunkRecord.id, rank)
            .join(DocumentRecord, DocumentRecord.id == ChunkRecord.document_id)
            .where(
                DocumentRecord.status == "ready",
                ChunkRecord.search_vector.op("@@")(ts_query),
            )
        )
        if filters.document_ids:
            statement = statement.where(DocumentRecord.id.in_(filters.document_ids))
        if filters.media_types:
            statement = statement.where(
                DocumentRecord.media_type.in_(
                    media_type.value for media_type in filters.media_types
                )
            )
        statement = statement.order_by(desc(rank), ChunkRecord.id).limit(limit)

        with self._sessions.transaction() as session:
            rows = session.execute(statement).all()
        return [
            RetrievalCandidate(
                chunk_id=row.id,
                rank=position,
                score=float(row.rank),
            )
            for position, row in enumerate(rows, start=1)
        ]

    def load_chunks(self, chunk_ids: list[UUID]) -> dict[UUID, SearchableChunk]:
        if not chunk_ids:
            return {}
        statement = (
            select(ChunkRecord, DocumentRecord)
            .join(DocumentRecord, DocumentRecord.id == ChunkRecord.document_id)
            .where(
                ChunkRecord.id.in_(chunk_ids),
                DocumentRecord.status == "ready",
            )
        )
        with self._sessions.transaction() as session:
            rows = session.execute(statement).all()
        return {
            chunk.id: SearchableChunk(
                id=chunk.id,
                document_id=chunk.document_id,
                text=chunk.text,
                original_filename=document.original_filename,
                media_type=DocumentMediaType(document.media_type),
                locator=SourceLocator(
                    section_path=tuple(chunk.section_path),
                    page_number=chunk.page_number,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                ),
            )
            for chunk, document in rows
        }
