import hashlib
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest

from knowledge_search.domain import DocumentMediaType
from knowledge_search.ingestion.errors import IngestionError, IngestionErrorCode
from knowledge_search.providers import LocalDocumentStore

DOCUMENT_ID = UUID("fe670ea5-4ba8-4da7-92b5-53d17984e94d")


def test_local_store_writes_generated_path_and_hash(tmp_path: Path) -> None:
    store = LocalDocumentStore(tmp_path)
    content = b"Original project-authored document."

    stored = store.save(
        document_id=DOCUMENT_ID,
        media_type=DocumentMediaType.TEXT,
        source=BytesIO(content),
        max_bytes=1_024,
    )

    assert stored.storage_key == f"{DOCUMENT_ID}/source.txt"
    assert stored.sha256 == hashlib.sha256(content).hexdigest()
    assert stored.size_bytes == len(content)
    with store.open(stored.storage_key) as source:
        assert source.read() == content


def test_local_store_removes_partial_file_when_limit_is_exceeded(tmp_path: Path) -> None:
    store = LocalDocumentStore(tmp_path)

    with pytest.raises(IngestionError) as captured:
        store.save(
            document_id=DOCUMENT_ID,
            media_type=DocumentMediaType.TEXT,
            source=BytesIO(b"too large"),
            max_bytes=3,
        )

    assert captured.value.code is IngestionErrorCode.FILE_TOO_LARGE
    assert list(tmp_path.iterdir()) == []


def test_local_store_rejects_empty_upload(tmp_path: Path) -> None:
    store = LocalDocumentStore(tmp_path)

    with pytest.raises(IngestionError) as captured:
        store.save(
            document_id=DOCUMENT_ID,
            media_type=DocumentMediaType.MARKDOWN,
            source=BytesIO(),
            max_bytes=1_024,
        )

    assert captured.value.code is IngestionErrorCode.EMPTY_UPLOAD


def test_local_store_rejects_path_traversal(tmp_path: Path) -> None:
    store = LocalDocumentStore(tmp_path)

    with pytest.raises(IngestionError) as captured, store.open("../outside.txt"):
        pass

    assert captured.value.code is IngestionErrorCode.INVALID_STORAGE_KEY


def test_local_store_deletes_document_and_empty_directory(tmp_path: Path) -> None:
    store = LocalDocumentStore(tmp_path)
    stored = store.save(
        document_id=DOCUMENT_ID,
        media_type=DocumentMediaType.PDF,
        source=BytesIO(b"%PDF-project-fixture"),
        max_bytes=1_024,
    )

    store.delete(stored.storage_key)

    assert list(tmp_path.iterdir()) == []
