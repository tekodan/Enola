"""Similarity engine for computing content similarity."""

from typing import Protocol

import numpy as np


class EmbeddingsProvider(Protocol):
    """Protocol for embeddings provider."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...


class SimilarityEngine:
    """Engine for computing similarity between content."""

    def __init__(self, embeddings_provider: EmbeddingsProvider | None = None):
        """Initialize similarity engine.

        Args:
            embeddings_provider: Provider for generating embeddings
        """
        self.embeddings_provider = embeddings_provider

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0 and 1
        """
        if self.embeddings_provider is None:
            # Fallback: simple word overlap
            return self._word_overlap_similarity(text1, text2)

        embeddings = self.embeddings_provider.embed([text1, text2])
        return self._cosine_similarity(embeddings[0], embeddings[1])

    def compute_batch_similarity(self, texts: list[str], reference_texts: list[str]) -> list[float]:
        """Compute similarity between texts and reference texts.

        Args:
            texts: Texts to compare
            reference_texts: Reference texts to compare against

        Returns:
            List of similarity scores
        """
        if not texts or not reference_texts:
            return []

        if self.embeddings_provider is None:
            # Fallback: word overlap
            return [
                max(self._word_overlap_similarity(t, rt) for rt in reference_texts) for t in texts
            ]

        all_texts = texts + reference_texts
        embeddings = self.embeddings_provider.embed(all_texts)

        text_embeddings = embeddings[: len(texts)]
        ref_embeddings = embeddings[len(texts) :]

        similarities = []
        for te in text_embeddings:
            max_sim = max(self._cosine_similarity(te, re) for re in ref_embeddings)
            similarities.append(max_sim)

        return similarities

    def compute_average_similarity(self, texts: list[str], reference_texts: list[str]) -> float:
        """Compute average similarity between texts and references.

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
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        sim = float(np.dot(v1, v2) / (norm1 * norm2))
        # Clamp to [0, 1] to handle floating point errors
        return max(0.0, min(1.0, sim))

    @staticmethod
    def _word_overlap_similarity(text1: str, text2: str) -> float:
        """Compute simple word overlap similarity."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0


def compute_similarity(text1: str, text2: str) -> float:
    """Convenience function for computing similarity."""
    engine = SimilarityEngine()
    return engine.compute_similarity(text1, text2)
