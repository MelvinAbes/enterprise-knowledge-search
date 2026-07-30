from uuid import UUID


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"Document {document_id} was not found.")
        self.document_id = document_id


class IngestionJobNotFoundError(Exception):
    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Ingestion job {job_id} was not found.")
        self.job_id = job_id


class DuplicateDocumentError(Exception):
    def __init__(self, existing_document_id: UUID) -> None:
        super().__init__("A document with the same content already exists.")
        self.existing_document_id = existing_document_id


class DocumentDeletionConflictError(RuntimeError):
    def __init__(self, document_id: UUID, status: str) -> None:
        super().__init__(f"Document {document_id} cannot be deleted while its status is {status}.")
        self.document_id = document_id
        self.status = status


class DocumentCleanupError(RuntimeError):
    pass
