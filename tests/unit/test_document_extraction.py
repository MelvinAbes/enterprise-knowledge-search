from io import BytesIO

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from knowledge_search.ingestion.errors import IngestionError, IngestionErrorCode
from knowledge_search.ingestion.extraction import MarkdownExtractor, PdfExtractor, TextExtractor


def create_pdf(*page_texts: str) -> BytesIO:
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4, invariant=1)
    for text in page_texts:
        if text:
            canvas.drawString(72, 780, text)
        canvas.showPage()
    canvas.save()
    buffer.seek(0)
    return buffer


def test_text_extractor_accepts_utf8_byte_order_mark() -> None:
    sections = TextExtractor().extract(BytesIO(b"\xef\xbb\xbfRetention policy"))

    assert len(sections) == 1
    assert sections[0].text == "Retention policy"


def test_text_extractor_rejects_non_utf8_input() -> None:
    with pytest.raises(IngestionError) as captured:
        TextExtractor().extract(BytesIO(b"\xff\xfe\x00\x00"))

    assert captured.value.code is IngestionErrorCode.INVALID_TEXT_ENCODING


def test_markdown_extractor_preserves_heading_hierarchy() -> None:
    source = BytesIO(
        b"""Introduction before headings.

# Operations

General guidance.

## Backups

Retain backups for thirty days.

```text
# This is code, not a heading
```

## Recovery

Test recovery every month.
"""
    )

    sections = MarkdownExtractor().extract(source)

    assert [section.section_path for section in sections] == [
        (),
        ("Operations",),
        ("Operations", "Backups"),
        ("Operations", "Recovery"),
    ]
    assert "# This is code, not a heading" in sections[2].text


def test_markdown_extractor_skips_heading_only_sections() -> None:
    source = BytesIO(
        b"""# Operations

## Backups

Retain backups for thirty days.
"""
    )

    sections = MarkdownExtractor().extract(source)

    assert [section.section_path for section in sections] == [
        ("Operations", "Backups"),
    ]
    assert sections[0].text.startswith("Backups\n")


def test_pdf_extractor_returns_page_locators() -> None:
    sections = PdfExtractor(max_pages=5).extract(
        create_pdf("Backup retention is thirty days.", "Recovery tests run monthly.")
    )

    assert [section.page_number for section in sections] == [1, 2]
    assert "Backup retention" in sections[0].text
    assert "Recovery tests" in sections[1].text


def test_pdf_extractor_enforces_page_limit() -> None:
    with pytest.raises(IngestionError) as captured:
        PdfExtractor(max_pages=1).extract(create_pdf("Page one", "Page two"))

    assert captured.value.code is IngestionErrorCode.PDF_PAGE_LIMIT_EXCEEDED


def test_pdf_extractor_rejects_invalid_pdf() -> None:
    with pytest.raises(IngestionError) as captured:
        PdfExtractor(max_pages=5).extract(BytesIO(b"not a pdf"))

    assert captured.value.code is IngestionErrorCode.INVALID_PDF


def test_pdf_extractor_rejects_image_only_or_blank_pdf() -> None:
    with pytest.raises(IngestionError) as captured:
        PdfExtractor(max_pages=5).extract(create_pdf(""))

    assert captured.value.code is IngestionErrorCode.NO_EXTRACTABLE_TEXT
