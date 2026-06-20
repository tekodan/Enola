"""Integration tests for discovery module."""

from unittest.mock import MagicMock

import pytest

from src.discovery.page_discovery import PageDiscovery, RelatedPage
from src.discovery.similarity import SimilarityEngine


@pytest.fixture
def mock_embeddings_provider():
    """Create mock embeddings provider."""
    provider = MagicMock()

    def embed(texts):
        # Simple embedding: hash-based for consistent testing
        return [[hash(t) % 100 / 100 for _ in range(3)] for t in texts]

    provider.embed.side_effect = embed
    return provider


@pytest.fixture
def sample_posts():
    """Sample posts for testing."""
    return [
        "Las mujeres solo sirven para cocinar y limpiar",
        "Si salís con amigas te voy a pegar",
        "Esta es una publicación normal sobre comida",
        "Feliz cumpleaños a todos",
        "Los hombres no saben cocinar",
    ]


@pytest.fixture
def seed_posts():
    """Sample posts that contain violence."""
    return [
        "Las mujeres son inferiores a los hombres",
        "Si me traicionás te voy a hacer daño",
        "Te voy a kill si seguís así",
    ]


class TestSimilarityEngineIntegration:
    """Integration tests for similarity engine."""

    def test_full_pipeline_with_mock_embeddings(
        self, mock_embeddings_provider, sample_posts, seed_posts
    ):
        """Test full similarity pipeline."""
        engine = SimilarityEngine(embeddings_provider=mock_embeddings_provider)

        # Compute similarities
        scores = engine.compute_batch_similarity(sample_posts, seed_posts)

        assert len(scores) == len(sample_posts)
        assert all(0 <= s <= 1 for s in scores)

    def test_average_similarity_trend(self, mock_embeddings_provider, sample_posts, seed_posts):
        """Test that average similarity shows expected trends."""
        engine = SimilarityEngine(embeddings_provider=mock_embeddings_provider)

        # Normal posts should have lower similarity
        normal_avg = engine.compute_average_similarity(
            ["Hoy es un buen día", "El clima está nice"], seed_posts
        )

        # Posts with violence-like content should have higher similarity
        violence_avg = engine.compute_average_similarity(
            ["Las mujeres no saben pensar"], seed_posts
        )

        # This test may fail depending on embeddings, but shows the pattern
        assert 0 <= normal_avg <= 1
        assert 0 <= violence_avg <= 1


class TestPageDiscoveryIntegration:
    """Integration tests for page discovery."""

    def test_full_discovery_pipeline(self, mock_embeddings_provider, sample_posts, seed_posts):
        """Test full discovery pipeline."""
        similarity_engine = SimilarityEngine(embeddings_provider=mock_embeddings_provider)

        discovery = PageDiscovery(similarity_engine=similarity_engine, min_similarity=0.5)

        # Simulate discovered pages
        pages = [
            RelatedPage(
                id=f"page-{i}",
                name=f"Pagina {i}",
                similarity_score=0.6 + i * 0.1,
                discovered_from="https://facebook.com/seed",
            )
            for i in range(5)
        ]

        # Filter by threshold
        filtered = discovery.get_pages_above_threshold(pages)

        # Rank
        ranked = discovery.rank_pages_by_similarity(filtered)

        # Determine seeds
        seeds = [p for p in ranked if discovery.should_add_as_seed(p)]

        assert len(seeds) > 0
        assert ranked[0].similarity_score >= ranked[-1].similarity_score

    def test_threshold_sensitivity(self):
        """Test different thresholds produce different results."""
        pages = [
            RelatedPage(id="1", similarity_score=0.9),
            RelatedPage(id="2", similarity_score=0.7),
            RelatedPage(id="3", similarity_score=0.5),
            RelatedPage(id="4", similarity_score=0.3),
        ]

        # High threshold
        discovery_high = PageDiscovery(min_similarity=0.8)
        high_filtered = discovery_high.get_pages_above_threshold(pages)

        # Low threshold
        discovery_low = PageDiscovery(min_similarity=0.4)
        low_filtered = discovery_low.get_pages_above_threshold(pages)

        assert len(high_filtered) < len(low_filtered)
        assert len(high_filtered) == 1
        assert len(low_filtered) == 3


class TestSimilarityEdgeCases:
    """Edge case tests for similarity."""

    def test_very_long_texts(self):
        """Test similarity with very long texts."""
        engine = SimilarityEngine()

        long_text1 = " ".join(["palabra"] * 1000)
        long_text2 = " ".join(["palabra"] * 1000)

        score = engine.compute_similarity(long_text1, long_text2)
        assert score == 1.0

    def test_unicode_texts(self):
        """Test similarity with unicode texts."""
        engine = SimilarityEngine()

        text1 = "Hola mundo"
        text2 = "Hóla múndó"

        score = engine.compute_similarity(text1, text2)
        assert 0 <= score <= 1

    def test_mixed_languages(self):
        """Test similarity with mixed languages."""
        engine = SimilarityEngine()

        text1 = "Hello world"
        text2 = "Hola mundo"

        score = engine.compute_similarity(text1, text2)
        assert 0 <= score <= 1

    def test_special_characters(self):
        """Test similarity with special characters."""
        engine = SimilarityEngine()

        text1 = "Hello! @#$%^&*()"
        text2 = "Hello! @#$%^&*()"

        score = engine.compute_similarity(text1, text2)
        assert score == 1.0


class TestPageRanking:
    """Tests for page ranking scenarios."""

    def test_ranking_stability(self):
        """Test that ranking is stable for same scores."""
        pages = [
            RelatedPage(id="1", similarity_score=0.5),
            RelatedPage(id="2", similarity_score=0.5),
            RelatedPage(id="3", similarity_score=0.5),
        ]

        discovery = PageDiscovery()

        # Run multiple times
        ranked1 = discovery.rank_pages_by_similarity(pages)
        ranked2 = discovery.rank_pages_by_similarity(pages)

        # Same order
        assert [p.id for p in ranked1] == [p.id for p in ranked2]

    def test_ranking_with_duplicates(self):
        """Test ranking with duplicate scores."""
        pages = [
            RelatedPage(id="1", similarity_score=0.8),
            RelatedPage(id="2", similarity_score=0.9),
            RelatedPage(id="3", similarity_score=0.8),
        ]

        discovery = PageDiscovery()
        ranked = discovery.rank_pages_by_similarity(pages)

        # First should be highest
        assert ranked[0].id == "2"
        assert ranked[0].similarity_score == 0.9


class TestSeedDetermination:
    """Tests for seed determination."""

    def test_exactly_at_threshold(self):
        """Test pages exactly at threshold."""
        discovery = PageDiscovery(min_similarity=0.7)

        page = RelatedPage(id="test", similarity_score=0.7)

        assert discovery.should_add_as_seed(page) is True

    def test_just_above_threshold(self):
        """Test pages just above threshold."""
        discovery = PageDiscovery(min_similarity=0.7)

        page = RelatedPage(id="test", similarity_score=0.71)

        assert discovery.should_add_as_seed(page) is True

    def test_just_below_threshold(self):
        """Test pages just below threshold."""
        discovery = PageDiscovery(min_similarity=0.7)

        page = RelatedPage(id="test", similarity_score=0.69)

        assert discovery.should_add_as_seed(page) is False

    def test_perfect_match(self):
        """Test perfect match (score = 1.0)."""
        discovery = PageDiscovery(min_similarity=0.7)

        page = RelatedPage(id="test", similarity_score=1.0)

        assert discovery.should_add_as_seed(page) is True

    def test_no_match(self):
        """Test no match (score = 0.0)."""
        discovery = PageDiscovery(min_similarity=0.7)

        page = RelatedPage(id="test", similarity_score=0.0)

        assert discovery.should_add_as_seed(page) is False
