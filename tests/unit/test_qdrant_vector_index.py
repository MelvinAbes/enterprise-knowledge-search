from uuid import UUID

import pytest
from qdrant_client import QdrantClient

from knowledge_search.domain import (
    Chunk,
    Document,
    DocumentMediaType,
    SourceLocator,
)
from knowledge_search.providers import QdrantVectorIndex
from knowledge_search.retrieval import SearchFilters


def test_qdrant_adapter_creates_upserts_and_deletes_document_vectors() -> None:
    client = QdrantClient(location=":memory:")
    index = QdrantVectorIndex(
        url="http://unused",
        collection_name="test_chunks",
        client=client,
    )
    document_id = UUID("f06f833d-c080-4ff8-bb55-a13505cc9241")
    chunk = Chunk.create(
        document_id=document_id,
        ordinal=0,
        text="Database backups are retained for thirty days.",
        token_count=8,
        content_hash="a" * 64,
        locator=SourceLocator(section_path=("Operations", "Backups")),
    )
    document = Document.create(
        document_id=document_id,
        original_filename="operations.md",
        storage_key=f"{document_id}/source.md",
        media_type=DocumentMediaType.MARKDOWN,
        sha256="b" * 64,
        size_bytes=100,
    )

    with pytest.warns(UserWarning, match="Payload indexes have no effect"):
        index.ensure_collection(dimensions=3)
    index.upsert(
        document=document,
        chunks=[chunk],
        vectors=[[0.2, 0.3, 0.4]],
    )

    assert client.count("test_chunks", exact=True).count == 1
    candidates = index.search(
        vector=[0.2, 0.3, 0.4],
        limit=5,
        filters=SearchFilters(media_types=(DocumentMediaType.MARKDOWN,)),
    )
    excluded = index.search(
        vector=[0.2, 0.3, 0.4],
        limit=5,
        filters=SearchFilters(media_types=(DocumentMediaType.PDF,)),
    )
    assert [candidate.chunk_id for candidate in candidates] == [chunk.id]
    assert excluded == []

    index.delete_document(document_id)

    assert client.count("test_chunks", exact=True).count == 0
