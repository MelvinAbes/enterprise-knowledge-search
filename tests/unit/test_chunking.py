from io import BytesIO
from uuid import UUID

from pydantic import SecretStr

from knowledge_search.config import Settings
from knowledge_search.domain import Document, DocumentMediaType, SourceLocator
from knowledge_search.ingestion.chunking import FixedWindowChunker, SectionAwareChunker
from knowledge_search.ingestion.extraction import (
    DocumentExtractorRegistry,
    MarkdownExtractor,
    PdfExtractor,
    TextExtractor,
)
from knowledge_search.ingestion.models import NormalizedSection
from knowledge_search.ingestion.pipeline import DocumentContentPreparer, create_content_preparer

DOCUMENT_ID = UUID("93e12f7d-1f34-4c76-9b9e-e2a937686262")


def test_section_aware_chunker_preserves_section_and_overlap() -> None:
    section = NormalizedSection(
        text="alpha beta gamma delta epsilon zeta",
        locator=SourceLocator(
            section_path=("Operations",),
            char_start=10,
            char_end=45,
        ),
    )

    chunks = SectionAwareChunker(size=4, overlap=2).chunk(DOCUMENT_ID, [section])

    assert [chunk.text for chunk in chunks] == [
        "alpha beta gamma delta",
        "gamma delta epsilon zeta",
    ]
    assert [chunk.token_count for chunk in chunks] == [4, 4]
    assert all(chunk.locator.section_path == ("Operations",) for chunk in chunks)
    assert chunks[0].locator.char_start == 10
    assert chunks[1].locator.char_start > chunks[0].locator.char_start


def test_fixed_window_chunker_can_span_sections() -> None:
    sections = [
        NormalizedSection(
            text="alpha beta",
            locator=SourceLocator(section_path=("First",), char_start=0, char_end=10),
        ),
        NormalizedSection(
            text="gamma delta",
            locator=SourceLocator(section_path=("Second",), char_start=12, char_end=23),
        ),
    ]

    chunks = FixedWindowChunker(size=3, overlap=0).chunk(DOCUMENT_ID, sections)

    assert chunks[0].text == "alpha beta\n\ngamma"
    assert chunks[0].locator.section_path == ("First",)
    assert chunks[1].locator.section_path == ("Second",)


def test_content_preparer_extracts_normalizes_and_chunks_markdown() -> None:
    document = Document.create(
        document_id=DOCUMENT_ID,
        original_filename="operations.md",
        storage_key=f"{DOCUMENT_ID}/source.md",
        media_type=DocumentMediaType.MARKDOWN,
        sha256="d" * 64,
        size_bytes=128,
    )
    extractors = DocumentExtractorRegistry(
        text=TextExtractor(),
        markdown=MarkdownExtractor(),
        pdf=PdfExtractor(max_pages=5),
    )
    preparer = DocumentContentPreparer(
        extractors=extractors,
        chunker=SectionAwareChunker(size=20, overlap=5),
    )

    chunks = preparer.prepare(
        document,
        BytesIO(
            b"""# Operations

Use daily backups.\r

## Recovery

Test recovery monthly.\r
"""
        ),
    )

    assert len(chunks) == 2
    assert chunks[0].locator.section_path == ("Operations",)
    assert chunks[1].locator.section_path == ("Operations", "Recovery")
    assert "\r" not in chunks[0].text
    assert chunks[0].id != chunks[1].id


def test_content_preparer_uses_configured_fixed_window_strategy() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+psycopg://user:test@localhost/database"),
        chunking_strategy="fixed_window",
        chunk_size_tokens=20,
        chunk_overlap_tokens=0,
    )
    document = Document.create(
        document_id=DOCUMENT_ID,
        original_filename="operations.md",
        storage_key=f"{DOCUMENT_ID}/source.md",
        media_type=DocumentMediaType.MARKDOWN,
        sha256="e" * 64,
        size_bytes=128,
    )

    chunks = create_content_preparer(settings).prepare(
        document,
        BytesIO(b"# Backups\nRetain daily copies.\n\n# Recovery\nTest recovery monthly."),
    )

    assert len(chunks) == 1
    assert "Backups" in chunks[0].text
    assert "Recovery" in chunks[0].text
