"""Embeddings module for post similarity."""

from typing import Protocol

import numpy as np


class EmbeddingsProvider(Protocol):
    """Protocol for embeddings provider."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...


class PostEmbeddings:
    """Manager for post embeddings and similarity."""

    def __init__(self, embeddings_provider: EmbeddingsProvider | None = None):
        """Initialize post embeddings manager.

        Args:
            embeddings_provider: Provider for generating embeddings
        """
        self.embeddings_provider = embeddings_provider
        self.embeddings_cache = {}

    def create_embedding(self, text: str) -> list[float] | None:
        """Create embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None
        """
        if self.embeddings_provider is None:
            return None

        if text in self.embeddings_cache:
            return self.embeddings_cache[text]

        embeddings = self.embeddings_provider.embed([text])
        if embeddings:
            embedding = embeddings[0]
            self.embeddings_cache[text] = embedding
            return embedding

        return None

    def create_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Create embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if self.embeddings_provider is None:
            return []

        # Filter out cached texts
        texts_to_embed = [t for t in texts if t not in self.embeddings_cache]

        if texts_to_embed:
            new_embeddings = self.embeddings_provider.embed(texts_to_embed)
            for text, embedding in zip(texts_to_embed, new_embeddings):
                self.embeddings_cache[text] = embedding

        return [self.embeddings_cache[t] for t in texts]

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        emb1 = self.create_embedding(text1)
        emb2 = self.create_embedding(text2)

        if emb1 is None or emb2 is None:
            return 0.0

        return self._cosine_similarity(emb1, emb2)

    def compute_batch_similarity(self, texts: list[str], reference_texts: list[str]) -> list[float]:
        """Compute similarity between texts and references.

        Args:
            texts: Texts to compare
            reference_texts: Reference texts

        Returns:
            List of maximum similarity scores
        """
        if not texts or not reference_texts:
            return []

        text_embeddings = self.create_embeddings_batch(texts)
        ref_embeddings = self.create_embeddings_batch(reference_texts)

        if not text_embeddings or not ref_embeddings:
            return [0.0] * len(texts)

        similarities = []
        for te in text_embeddings:
            max_sim = max(self._cosine_similarity(te, re) for re in ref_embeddings)
            similarities.append(max_sim)

        return similarities

    def compute_average_similarity(self, texts: list[str], reference_texts: list[str]) -> float:
        """Compute average similarity.

        Args:
            texts: Texts to compare
            reference_texts: Reference texts

        Returns:
            Average similarity score
        """
        if not texts:
            return 0.0

        similarities = self.compute_batch_similarity(texts, reference_texts)
        return sum(similarities) / len(similarities) if similarities else 0.0

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity."""
        if not vec1 or not vec2:
            return 0.0

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(v1, v2) / (norm1 * norm2))

    def clear_cache(self) -> None:
        """Clear embeddings cache."""
        self.embeddings_cache.clear()
