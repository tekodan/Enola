"""Unit tests for discovery module."""

from unittest.mock import MagicMock

import pytest

from src.discovery.page_discovery import (
    ControversialGroup,
    PageDiscovery,
    RelatedPage,
)
from src.discovery.similarity import SimilarityEngine, compute_similarity


class TestRelatedPage:
    """Tests for RelatedPage model."""

    def test_create_related_page_minimal(self):
        """Test creating related page with minimal data."""
        page = RelatedPage(id="page-123")
        assert page.id == "page-123"
        assert page.name == ""
        assert page.similarity_score == 0.0

    def test_create_related_page_full(self):
        """Test creating related page with all fields."""
        page = RelatedPage(
            id="page-123",
            name="Pagina Relacionada",
            url="https://facebook.com/page-rel",
            likes=5000,
            similarity_score=0.85,
            discovered_from="https://facebook.com/page-seed",
            category="Entretenimiento",
        )

        assert page.id == "page-123"
        assert page.name == "Pagina Relacionada"
        assert page.similarity_score == 0.85
        assert page.discovered_from == "https://facebook.com/page-seed"

    def test_similarity_score_validation(self):
        """Test similarity score must be between 0 and 1."""
        page = RelatedPage(id="test", similarity_score=0.5)
        assert page.similarity_score == 0.5

        with pytest.raises(Exception):
            RelatedPage(id="test", similarity_score=1.5)

        with pytest.raises(Exception):
            RelatedPage(id="test", similarity_score=-0.1)


class TestControversialGroup:
    """Tests for ControversialGroup model."""

    def test_create_group_minimal(self):
        """Test creating group with minimal data."""
        group = ControversialGroup(id="group-123")
        assert group.id == "group-123"
        assert group.name == ""
        assert group.members == 0

    def test_create_group_full(self):
        """Test creating group with all fields."""
        group = ControversialGroup(
            id="group-123",
            name="Grupo Polemico",
            url="https://facebook.com/groups/polemico",
            members=10000,
            keywords_matched=["política", "debate"],
            privacy="public",
        )

        assert group.name == "Grupo Polemico"
        assert group.members == 10000
        assert len(group.keywords_matched) == 2


class TestPageDiscovery:
    """Tests for PageDiscovery class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        discovery = PageDiscovery()

        assert discovery.scraper is None
        assert discovery.similarity_engine is None
        assert discovery.min_similarity == 0.7
        assert discovery.max_pages == 20

    def test_init_custom(self):
        """Test initialization with custom values."""
        scraper = MagicMock()
        similarity_engine = MagicMock()

        discovery = PageDiscovery(
            scraper=scraper, similarity_engine=similarity_engine, min_similarity=0.8, max_pages=50
        )

        assert discovery.scraper == scraper
        assert discovery.similarity_engine == similarity_engine
        assert discovery.min_similarity == 0.8
        assert discovery.max_pages == 50

    def test_get_pages_above_threshold(self):
        """Test filtering pages above threshold."""
        discovery = PageDiscovery(min_similarity=0.7)

        pages = [
            RelatedPage(id="1", similarity_score=0.9),
            RelatedPage(id="2", similarity_score=0.6),
            RelatedPage(id="3", similarity_score=0.8),
            RelatedPage(id="4", similarity_score=0.5),
        ]

        filtered = discovery.get_pages_above_threshold(pages)

        assert len(filtered) == 2
        assert all(p.similarity_score >= 0.7 for p in filtered)

    def test_rank_pages_by_similarity(self):
        """Test ranking pages by similarity."""
        discovery = PageDiscovery()

        pages = [
            RelatedPage(id="1", similarity_score=0.5),
            RelatedPage(id="2", similarity_score=0.9),
            RelatedPage(id="3", similarity_score=0.7),
        ]

        ranked = discovery.rank_pages_by_similarity(pages)

        assert ranked[0].id == "2"
        assert ranked[1].id == "3"
        assert ranked[2].id == "1"

    def test_should_add_as_seed(self):
        """Test seed determination."""
        discovery = PageDiscovery(min_similarity=0.7)

        page_above = RelatedPage(id="1", similarity_score=0.85)
        page_below = RelatedPage(id="2", similarity_score=0.5)
        page_exact = RelatedPage(id="3", similarity_score=0.7)

        assert discovery.should_add_as_seed(page_above) is True
        assert discovery.should_add_as_seed(page_below) is False
        assert discovery.should_add_as_seed(page_exact) is True


class TestSimilarityEngine:
    """Tests for SimilarityEngine class."""

    def test_init(self):
        """Test initialization."""
        engine = SimilarityEngine()
        assert engine.embeddings_provider is None

    def test_compute_similarity_fallback(self):
        """Test similarity computation without embeddings."""
        engine = SimilarityEngine()

        # Same text
        score = engine.compute_similarity("hola mundo", "hola mundo")
        assert score == 1.0

        # No overlap
        score = engine.compute_similarity("hola", "mundo")
        assert score == 0.0

    def test_compute_similarity_with_embeddings(self):
        """Test similarity with mock embeddings."""

        # Use side_effect so each call returns different embeddings
        def embed_side_effect(texts):
            return [[hash(t) % 100 / 100 for _ in range(3)] for t in texts]

        mock_provider = MagicMock()
        mock_provider.embed.side_effect = embed_side_effect

        engine = SimilarityEngine(embeddings_provider=mock_provider)

        # Similar texts should have some similarity
        score = engine.compute_similarity("text1", "text1")
        assert abs(score - 1.0) < 0.001

        # Different texts should have lower similarity
        score = engine.compute_similarity("text1", "text2")
        assert 0 <= score <= 1

    def test_compute_batch_similarity(self):
        """Test batch similarity computation."""
        engine = SimilarityEngine()

        texts = ["hola mundo", "buenos dias"]
        references = ["hola", "adios"]

        scores = engine.compute_batch_similarity(texts, references)

        assert len(scores) == 2
        assert all(0 <= s <= 1 for s in scores)

    def test_compute_average_similarity(self):
        """Test average similarity computation."""
        engine = SimilarityEngine()

        texts = ["hola mundo", "buenos dias"]
        references = ["hola", "mundo"]

        avg = engine.compute_average_similarity(texts, references)

        assert 0 <= avg <= 1

    def test_cosine_similarity_static(self):
        """Test cosine similarity calculation."""
        # Identical vectors
        score = SimilarityEngine._cosine_similarity([1, 0], [1, 0])
        assert score == 1.0

        # Orthogonal vectors
        score = SimilarityEngine._cosine_similarity([1, 0], [0, 1])
        assert score == 0.0

        # Partial similarity
        score = SimilarityEngine._cosine_similarity([1, 1], [1, 0])
        assert 0.6 < score < 0.8

    def test_word_overlap_similarity(self):
        """Test word overlap similarity."""
        # Identical
        score = SimilarityEngine._word_overlap_similarity("hola mundo", "hola mundo")
        assert score == 1.0

        # Partial overlap
        score = SimilarityEngine._word_overlap_similarity("hola mundo", "hola")
        assert 0 < score < 1

        # No overlap
        score = SimilarityEngine._word_overlap_similarity("hola", "mundo")
        assert score == 0.0

    def test_empty_texts(self):
        """Test handling of empty texts."""
        engine = SimilarityEngine()

        score = engine.compute_similarity("", "")
        assert score == 0.0

        score = engine.compute_similarity("hola", "")
        assert score == 0.0

        scores = engine.compute_batch_similarity([], ["hola"])
        assert scores == []


def test_compute_similarity_function():
    """Test convenience function."""
    score = compute_similarity("hola mundo", "hola")
    assert 0 < score <= 1
