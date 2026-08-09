"""Local deterministic embeddings and source-aware semantic retrieval."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .models import DocumentChunk, RetrievedEvidence


class DeterministicEmbeddingProvider:
    """Produce stable normalized vectors without a model or network dependency."""

    async def embed(self, text: str) -> list[float]:
        """Map token hashes into a small deterministic vector."""
        vector = [0.0] * 32
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % len(vector)
            vector[index] += 1.0 if digest[2] % 2 else -1.0
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / magnitude for value in vector]


@dataclass(frozen=True, slots=True)
class _StoredChunk:
    chunk: DocumentChunk
    vector: list[float]


class InMemoryVectorStore:
    """Store chunks and rank them using cosine similarity."""

    def __init__(self) -> None:
        self._chunks: list[_StoredChunk] = []

    def add(self, chunk: DocumentChunk, vector: list[float]) -> None:
        """Insert or replace a chunk by its stable identifier."""
        self._chunks = [stored for stored in self._chunks if stored.chunk.id != chunk.id]
        self._chunks.append(_StoredChunk(chunk, list(vector)))

    def search(self, vector: list[float], limit: int = 5) -> list[RetrievedEvidence]:
        """Return highest-scoring evidence while preserving source metadata."""
        if limit < 1:
            return []
        ranked = sorted(
            (RetrievedEvidence(stored.chunk, self._dot(vector, stored.vector)) for stored in self._chunks),
            key=lambda item: item.score,
            reverse=True,
        )
        return ranked[:limit]

    @staticmethod
    def _dot(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right))


class TopicRetriever:
    """Embed a topic and retrieve the smallest relevant context set."""

    def __init__(self, embedder: DeterministicEmbeddingProvider, store: InMemoryVectorStore) -> None:
        self.embedder = embedder
        self.store = store

    async def index(self, chunks: list[DocumentChunk]) -> None:
        """Index source chunks through the configured embedding capability."""
        for chunk in chunks:
            self.store.add(chunk, await self.embedder.embed(chunk.text))

    async def retrieve(self, topic: str, limit: int = 5) -> list[RetrievedEvidence]:
        """Retrieve attributed evidence for the current interview topic."""
        if not topic.strip():
            return []
        return self.store.search(await self.embedder.embed(topic), limit)
