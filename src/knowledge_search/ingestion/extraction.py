from typing import BinaryIO

from markdown_it import MarkdownIt
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from knowledge_search.domain import DocumentMediaType
from knowledge_search.ingestion.errors import IngestionError, IngestionErrorCode
from knowledge_search.ingestion.models import ExtractedSection
from knowledge_search.ingestion.ports import DocumentExtractor


def _read_utf8(source: BinaryIO) -> str:
    source.seek(0)
    raw_content = source.read()
    try:
        return raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise IngestionError(
            IngestionErrorCode.INVALID_TEXT_ENCODING,
            "Document text must use UTF-8 encoding.",
        ) from error


class TextExtractor:
    def extract(self, source: BinaryIO) -> list[ExtractedSection]:
        text = _read_utf8(source)
        if not text.strip():
            raise IngestionError(
                IngestionErrorCode.NO_EXTRACTABLE_TEXT,
                "The document does not contain extractable text.",
            )
        return [ExtractedSection(text=text)]


class MarkdownExtractor:
    def __init__(self) -> None:
        self._parser = MarkdownIt("commonmark")

    def extract(self, source: BinaryIO) -> list[ExtractedSection]:
        text = _read_utf8(source)
        if not text.strip():
            raise IngestionError(
                IngestionErrorCode.NO_EXTRACTABLE_TEXT,
                "The document does not contain extractable text.",
            )

        lines = text.splitlines(keepends=True)
        tokens = self._parser.parse(text)
        headings: list[tuple[int, int, str]] = []
        for index, token in enumerate(tokens):
            if token.type != "heading_open" or token.map is None:
                continue
            inline_token = tokens[index + 1]
            level = int(token.tag.removeprefix("h"))
            heading = inline_token.content.strip()
            if heading:
                headings.append((token.map[0], level, heading))

        if not headings:
            return [ExtractedSection(text=text)]

        sections: list[ExtractedSection] = []
        first_heading_line = headings[0][0]
        preamble = "".join(lines[:first_heading_line])
        if preamble.strip():
            sections.append(ExtractedSection(text=preamble))

        heading_stack: list[tuple[int, str]] = []
        for position, (line_number, level, heading) in enumerate(headings):
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading))

            next_line = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
            body = "".join(lines[line_number + 1 : next_line])
            section_text = f"{heading}\n{body}"
            if section_text.strip():
                sections.append(
                    ExtractedSection(
                        text=section_text,
                        section_path=tuple(item[1] for item in heading_stack),
                    )
                )

        return sections


class PdfExtractor:
    def __init__(self, *, max_pages: int) -> None:
        self._max_pages = max_pages

    def extract(self, source: BinaryIO) -> list[ExtractedSection]:
        source.seek(0)
        try:
            reader = PdfReader(source, strict=False)
        except (PdfReadError, ValueError) as error:
            raise IngestionError(
                IngestionErrorCode.INVALID_PDF,
                "The PDF cannot be parsed.",
            ) from error

        if reader.is_encrypted:
            raise IngestionError(
                IngestionErrorCode.ENCRYPTED_PDF,
                "Encrypted PDFs are not supported.",
            )
        if len(reader.pages) > self._max_pages:
            raise IngestionError(
                IngestionErrorCode.PDF_PAGE_LIMIT_EXCEEDED,
                f"PDF exceeds the configured limit of {self._max_pages} pages.",
            )

        sections: list[ExtractedSection] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except (KeyError, TypeError, ValueError) as error:
                raise IngestionError(
                    IngestionErrorCode.INVALID_PDF,
                    f"PDF page {page_number} cannot be parsed.",
                ) from error
            if page_text.strip():
                sections.append(
                    ExtractedSection(
                        text=page_text,
                        page_number=page_number,
                    )
                )

        if not sections:
            raise IngestionError(
                IngestionErrorCode.NO_EXTRACTABLE_TEXT,
                "The PDF does not contain extractable text.",
            )
        return sections


class DocumentExtractorRegistry:
    def __init__(
        self,
        *,
        text: DocumentExtractor,
        markdown: DocumentExtractor,
        pdf: DocumentExtractor,
    ) -> None:
        self._extractors = {
            DocumentMediaType.TEXT: text,
            DocumentMediaType.MARKDOWN: markdown,
            DocumentMediaType.PDF: pdf,
        }

    def get(self, media_type: DocumentMediaType) -> DocumentExtractor:
        try:
            return self._extractors[media_type]
        except KeyError as error:
            raise IngestionError(
                IngestionErrorCode.UNSUPPORTED_MEDIA_TYPE,
                f"Unsupported document media type: {media_type}.",
            ) from error
