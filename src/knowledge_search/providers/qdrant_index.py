from uuid import UUID

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException

from knowledge_search.domain import Chunk
from knowledge_search.ingestion.errors import VectorIndexError


class QdrantVectorIndex:
    def __init__(
        self,
        *,
        url: str,
        collection_name: str,
        client: QdrantClient | None = None,
    ) -> None:
        self._client = client or QdrantClient(
            url=url,
            timeout=10,
            check_compatibility=False,
        )
        self._collection_name = collection_name

    def ensure_collection(self, *, dimensions: int) -> None:
        try:
            if self._client.collection_exists(self._collection_name):
                collection = self._client.get_collection(self._collection_name)
                vectors = collection.config.params.vectors
                if not isinstance(vectors, models.VectorParams) or vectors.size != dimensions:
                    raise VectorIndexError(
                        "Existing Qdrant collection has incompatible vector dimensions."
                    )
                return

            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=models.VectorParams(
                    size=dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
            self._client.create_payload_index(
                collection_name=self._collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.UUID,
            )
        except (ApiException, ResponseHandlingException) as error:
            raise VectorIndexError("Qdrant collection setup failed.") from error

    def upsert(self, *, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise VectorIndexError("Chunk and vector counts do not match.")
        points = [
            models.PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "document_id": str(chunk.document_id),
                    "ordinal": chunk.ordinal,
                    "section_path": list(chunk.locator.section_path),
                    "page_number": chunk.locator.page_number,
                    "content_hash": chunk.content_hash,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        try:
            self._client.upsert(
                collection_name=self._collection_name,
                points=points,
                wait=True,
            )
        except (ApiException, ResponseHandlingException) as error:
            raise VectorIndexError("Qdrant vector upsert failed.") from error

    def delete_document(self, document_id: UUID) -> None:
        try:
            if not self._client.collection_exists(self._collection_name):
                return
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id)),
                        )
                    ]
                ),
                wait=True,
            )
        except (ApiException, ResponseHandlingException) as error:
            raise VectorIndexError("Qdrant document cleanup failed.") from error

    def is_ready(self) -> bool:
        try:
            self._client.get_collections()
        except (ApiException, ResponseHandlingException):
            return False
        return True
