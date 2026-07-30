import hashlib
import re
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from knowledge_search.domain import Chunk, SourceLocator
from knowledge_search.ingestion.models import NormalizedSection

TOKEN_PATTERN = re.compile(r"\w+(?:[-'][\w]+)*|[^\w\s]", re.UNICODE)


@dataclass(frozen=True, slots=True)
class TextWindow:
    text: str
    token_count: int
    char_start: int
    char_end: int


class DocumentChunker(Protocol):
    def chunk(self, document_id: UUID, sections: list[NormalizedSection]) -> list[Chunk]: ...


def _windows(text: str, *, size: int, overlap: int) -> list[TextWindow]:
    matches = list(TOKEN_PATTERN.finditer(text))
    if not matches:
        return []

    windows: list[TextWindow] = []
    step = size - overlap
    token_start = 0
    while token_start < len(matches):
        token_end = min(token_start + size, len(matches))
        char_start = matches[token_start].start()
        char_end = matches[token_end - 1].end()
        windows.append(
            TextWindow(
                text=text[char_start:char_end].strip(),
                token_count=token_end - token_start,
                char_start=char_start,
                char_end=char_end,
            )
        )
        if token_end == len(matches):
            break
        token_start += step
    return windows


def _create_chunk(
    *,
    document_id: UUID,
    ordinal: int,
    window: TextWindow,
    locator: SourceLocator,
) -> Chunk:
    content_hash = hashlib.sha256(window.text.encode("utf-8")).hexdigest()
    return Chunk.create(
        document_id=document_id,
        ordinal=ordinal,
        text=window.text,
        token_count=window.token_count,
        content_hash=content_hash,
        locator=locator,
    )


class FixedWindowChunker:
    def __init__(self, *, size: int, overlap: int) -> None:
        _validate_window_configuration(size=size, overlap=overlap)
        self._size = size
        self._overlap = overlap

    def chunk(self, document_id: UUID, sections: list[NormalizedSection]) -> list[Chunk]:
        full_text = "\n\n".join(section.text for section in sections)
        chunks: list[Chunk] = []
        for ordinal, window in enumerate(
            _windows(full_text, size=self._size, overlap=self._overlap)
        ):
            source_section = _section_at_offset(sections, window.char_start)
            chunks.append(
                _create_chunk(
                    document_id=document_id,
                    ordinal=ordinal,
                    window=window,
                    locator=SourceLocator(
                        section_path=source_section.locator.section_path,
                        page_number=source_section.locator.page_number,
                        char_start=window.char_start,
                        char_end=window.char_end,
                    ),
                )
            )
        return chunks


class SectionAwareChunker:
    def __init__(self, *, size: int, overlap: int) -> None:
        _validate_window_configuration(size=size, overlap=overlap)
        self._size = size
        self._overlap = overlap

    def chunk(self, document_id: UUID, sections: list[NormalizedSection]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section in sections:
            for window in _windows(section.text, size=self._size, overlap=self._overlap):
                chunks.append(
                    _create_chunk(
                        document_id=document_id,
                        ordinal=len(chunks),
                        window=window,
                        locator=SourceLocator(
                            section_path=section.locator.section_path,
                            page_number=section.locator.page_number,
                            char_start=section.locator.char_start + window.char_start,
                            char_end=section.locator.char_start + window.char_end,
                        ),
                    )
                )
        return chunks


def _section_at_offset(
    sections: list[NormalizedSection],
    char_offset: int,
) -> NormalizedSection:
    for section in reversed(sections):
        if char_offset >= section.locator.char_start:
            return section
    raise ValueError("no source section exists for chunk offset")


def _validate_window_configuration(*, size: int, overlap: int) -> None:
    if size < 1:
        raise ValueError("chunk size must be greater than zero")
    if overlap < 0:
        raise ValueError("chunk overlap must not be negative")
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")
