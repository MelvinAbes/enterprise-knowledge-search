from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from knowledge_search.domain import Citation, DocumentMediaType, SourceLocator


class SearchMode(StrEnum):
    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class SearchFilters:
    document_ids: tuple[UUID, ...] = ()
    media_types: tuple[DocumentMediaType, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    chunk_id: UUID
    rank: int
    score: float

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("candidate rank must be greater than zero")


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    chunk_id: UUID
    score: float
    keyword_rank: int | None
    vector_rank: int | None


@dataclass(frozen=True, slots=True)
class SearchableChunk:
    id: UUID
    document_id: UUID
    text: str
    original_filename: str
    media_type: DocumentMediaType
    locator: SourceLocator


@dataclass(frozen=True, slots=True)
class SearchResult:
    score: float
    keyword_rank: int | None
    vector_rank: int | None
    media_type: DocumentMediaType
    citation: Citation
