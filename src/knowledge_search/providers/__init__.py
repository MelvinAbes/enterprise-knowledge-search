"""Concrete external-service adapters."""

from knowledge_search.providers.embeddings import FastEmbedProvider
from knowledge_search.providers.local_files import LocalDocumentStore
from knowledge_search.providers.qdrant_index import QdrantVectorIndex
from knowledge_search.providers.redis_queue import RedisIngestionQueue

__all__ = [
    "FastEmbedProvider",
    "LocalDocumentStore",
    "QdrantVectorIndex",
    "RedisIngestionQueue",
]
