from enum import StrEnum
from uuid import UUID


class IngestionErrorCode(StrEnum):
    EMPTY_UPLOAD = "empty_upload"
    FILE_TOO_LARGE = "file_too_large"
    INVALID_FILENAME = "invalid_filename"
    INVALID_STORAGE_KEY = "invalid_storage_key"
    MEDIA_TYPE_MISMATCH = "media_type_mismatch"
    STORAGE_CONFLICT = "storage_conflict"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    INVALID_TEXT_ENCODING = "invalid_text_encoding"
    INVALID_PDF = "invalid_pdf"
    ENCRYPTED_PDF = "encrypted_pdf"
    PDF_PAGE_LIMIT_EXCEEDED = "pdf_page_limit_exceeded"
    NO_EXTRACTABLE_TEXT = "no_extractable_text"


class IngestionError(Exception):
    def __init__(self, code: IngestionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class QueueDispatchError(Exception):
    def __init__(
        self,
        message: str,
        *,
        document_id: UUID | None = None,
        job_id: UUID | None = None,
    ) -> None:
        super().__init__(message)
        self.document_id = document_id
        self.job_id = job_id


class EmbeddingError(Exception):
    pass


class VectorIndexError(Exception):
    pass
