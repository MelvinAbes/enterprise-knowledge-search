from pathlib import Path
from typing import Any

import pytest

from knowledge_search.providers.embeddings import FastEmbedProvider


class TextEmbeddingStub:
    instances = 0

    def __init__(self, **_: Any) -> None:
        type(self).instances += 1

    def embed(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        assert batch_size == 64
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_embedding_model_is_loaded_once_on_first_inference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    TextEmbeddingStub.instances = 0
    monkeypatch.setattr(
        "knowledge_search.providers.embeddings.TextEmbedding",
        TextEmbeddingStub,
    )
    provider = FastEmbedProvider(
        model_name="test-model",
        dimensions=3,
        cache_path=tmp_path,
    )

    assert TextEmbeddingStub.instances == 0

    first = provider.embed_documents(["first"])
    second = provider.embed_documents(["second"])

    assert first[0] == pytest.approx([0.1, 0.2, 0.3])
    assert second[0] == pytest.approx([0.1, 0.2, 0.3])
    assert TextEmbeddingStub.instances == 1
