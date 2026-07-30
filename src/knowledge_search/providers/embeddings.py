from pathlib import Path

from fastembed import TextEmbedding

from knowledge_search.ingestion.errors import EmbeddingError


class FastEmbedProvider:
    def __init__(
        self,
        *,
        model_name: str,
        dimensions: int,
        cache_path: Path,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_path),
            lazy_load=True,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = [
                [float(value) for value in vector]
                for vector in self._model.embed(texts, batch_size=64)
            ]
        except Exception as error:
            raise EmbeddingError("Local embedding inference failed.") from error

        if len(vectors) != len(texts):
            raise EmbeddingError("Embedding provider returned an unexpected vector count.")
        if any(len(vector) != self._dimensions for vector in vectors):
            raise EmbeddingError("Embedding dimensions do not match the configured collection.")
        return vectors
