from uuid import UUID

import pytest
from qdrant_client import QdrantClient

from knowledge_search.domain import Chunk, SourceLocator
from knowledge_search.providers import QdrantVectorIndex


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

    with pytest.warns(UserWarning, match="Payload indexes have no effect"):
        index.ensure_collection(dimensions=3)
    index.upsert(chunks=[chunk], vectors=[[0.2, 0.3, 0.4]])

    assert client.count("test_chunks", exact=True).count == 1

    index.delete_document(document_id)

    assert client.count("test_chunks", exact=True).count == 0
