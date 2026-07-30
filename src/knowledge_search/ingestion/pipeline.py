from typing import BinaryIO

from knowledge_search.config import Settings
from knowledge_search.domain import Chunk, Document, SourceLocator
from knowledge_search.ingestion.chunking import (
    DocumentChunker,
    FixedWindowChunker,
    SectionAwareChunker,
)
from knowledge_search.ingestion.errors import IngestionError, IngestionErrorCode
from knowledge_search.ingestion.extraction import (
    DocumentExtractorRegistry,
    MarkdownExtractor,
    PdfExtractor,
    TextExtractor,
)
from knowledge_search.ingestion.models import ExtractedSection, NormalizedSection
from knowledge_search.ingestion.normalization import normalize_document_text


class DocumentContentPreparer:
    def __init__(
        self,
        *,
        extractors: DocumentExtractorRegistry,
        chunker: DocumentChunker,
    ) -> None:
        self._extractors = extractors
        self._chunker = chunker

    def prepare(self, document: Document, source: BinaryIO) -> list[Chunk]:
        extracted_sections = self._extractors.get(document.media_type).extract(source)
        normalized_sections = _normalize_sections(extracted_sections)
        chunks = self._chunker.chunk(document.id, normalized_sections)
        if not chunks:
            raise IngestionError(
                IngestionErrorCode.NO_EXTRACTABLE_TEXT,
                "The document does not contain text that can be indexed.",
            )
        return chunks


def create_content_preparer(settings: Settings) -> DocumentContentPreparer:
    chunker: DocumentChunker
    if settings.chunking_strategy == "fixed_window":
        chunker = FixedWindowChunker(
            size=settings.chunk_size_tokens,
            overlap=settings.chunk_overlap_tokens,
        )
    else:
        chunker = SectionAwareChunker(
            size=settings.chunk_size_tokens,
            overlap=settings.chunk_overlap_tokens,
        )
    return DocumentContentPreparer(
        extractors=DocumentExtractorRegistry(
            text=TextExtractor(),
            markdown=MarkdownExtractor(),
            pdf=PdfExtractor(max_pages=settings.max_pdf_pages),
        ),
        chunker=chunker,
    )


def _normalize_sections(sections: list[ExtractedSection]) -> list[NormalizedSection]:
    normalized_sections: list[NormalizedSection] = []
    cursor = 0
    for section in sections:
        text = normalize_document_text(section.text)
        if not text:
            continue
        normalized_sections.append(
            NormalizedSection(
                text=text,
                locator=SourceLocator(
                    section_path=section.section_path,
                    page_number=section.page_number,
                    char_start=cursor,
                    char_end=cursor + len(text),
                ),
            )
        )
        cursor += len(text) + 2

    if not normalized_sections:
        raise IngestionError(
            IngestionErrorCode.NO_EXTRACTABLE_TEXT,
            "The document does not contain extractable text.",
        )
    return normalized_sections
