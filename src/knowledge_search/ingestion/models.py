from dataclasses import dataclass

from knowledge_search.domain import SourceLocator
from knowledge_search.domain.documents import DomainValidationError


@dataclass(frozen=True, slots=True)
class ExtractedSection:
    text: str
    section_path: tuple[str, ...] = ()
    page_number: int | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise DomainValidationError("extracted section text must not be blank")
        if self.page_number is not None and self.page_number < 1:
            raise DomainValidationError("extracted page number must be greater than zero")


@dataclass(frozen=True, slots=True)
class NormalizedSection:
    text: str
    locator: SourceLocator


@dataclass(frozen=True, slots=True)
class StoredDocument:
    storage_key: str
    sha256: str
    size_bytes: int
