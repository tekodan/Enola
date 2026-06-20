"""Unit tests for pipeline module."""

from dataclasses import asdict
from unittest.mock import MagicMock

from src.pipeline.orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStats,
    run_full_pipeline,
)


class TestPipelineStats:
    """Tests for PipelineStats."""

    def test_create_default(self):
        """Test creating with defaults."""
        stats = PipelineStats()

        assert stats.pages_scraped == 0
        assert stats.posts_found == 0
        assert stats.comments_found == 0
        assert stats.execution_time_seconds == 0.0

    def test_create_full(self):
        """Test creating with all values."""
        stats = PipelineStats(
            pages_scraped=5,
            posts_found=100,
            comments_found=500,
            posts_classified=100,
            comments_classified=500,
            violence_detected_posts=20,
            violence_detected_comments=50,
            new_pages_discovered=10,
            new_seed_pages_added=5,
            execution_time_seconds=120.5,
        )

        assert stats.pages_scraped == 5
        assert stats.posts_found == 100
        assert stats.violence_detected_posts == 20

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = PipelineStats(pages_scraped=5)
        data = asdict(stats)

        assert data["pages_scraped"] == 5


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_create_success(self):
        """Test creating successful result."""
        stats = PipelineStats(pages_scraped=5)

        result = PipelineResult(
            success=True,
            stats=stats,
        )

        assert result.success is True
        assert result.stats.pages_scraped == 5
        assert result.errors == []
        assert result.new_seeds == []

    def test_create_with_errors(self):
        """Test creating result with errors."""
        result = PipelineResult(
            success=False,
            stats=PipelineStats(),
            errors=["Error 1", "Error 2"],
        )

        assert result.success is False
        assert len(result.errors) == 2

    def test_create_with_new_seeds(self):
        """Test creating result with new seeds."""
        result = PipelineResult(
            success=True,
            stats=PipelineStats(new_seed_pages_added=3),
            new_seeds=[
                "https://facebook.com/page1",
                "https://facebook.com/page2",
            ],
        )

        assert len(result.new_seeds) == 2
        assert result.stats.new_seed_pages_added == 3


class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        orchestrator = PipelineOrchestrator()

        assert orchestrator.database is None
        assert orchestrator.scraper is None
        assert orchestrator.classifier is not None
        assert orchestrator.max_iterations == 3
        assert orchestrator.min_violence_score == 0.7

    def test_init_custom(self):
        """Test initialization with custom values."""
        mock_db = MagicMock()
        mock_scraper = MagicMock()
        mock_classifier = MagicMock()

        orchestrator = PipelineOrchestrator(
            database=mock_db,
            scraper=mock_scraper,
            classifier=mock_classifier,
            max_iterations=5,
            min_violence_score=0.8,
        )

        assert orchestrator.database == mock_db
        assert orchestrator.scraper == mock_scraper
        assert orchestrator.max_iterations == 5

    def test_run_seed_pipeline_no_scraper(self):
        """Test running seed pipeline without scraper."""
        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_seed_pipeline(["https://facebook.com/page1"])

        assert result.success is True
        assert result.stats.pages_scraped == 1
        assert result.stats.posts_found == 0  # No scraper

    def test_run_seed_pipeline_with_mock(self):
        """Test running seed pipeline with mocked scraper."""
        mock_scraper = MagicMock()
        mock_scraper.scrape_page_sync.return_value = []

        orchestrator = PipelineOrchestrator(scraper=mock_scraper)

        result = orchestrator.run_seed_pipeline(["https://facebook.com/page1"])

        assert result.success is True
        assert mock_scraper.scrape_page_sync.called

    def test_run_discovery_pipeline_no_db(self):
        """Test running discovery without database."""
        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_discovery_pipeline()

        assert result.success is False
        assert "No database configured" in result.errors

    def test_run_discovery_pipeline_with_mock_db(self):
        """Test running discovery with mock database."""
        mock_db = MagicMock()
        mock_db.get_seed_pages.return_value = [
            {"url": "https://facebook.com/page1", "name": "Page 1"}
        ]

        orchestrator = PipelineOrchestrator(database=mock_db)

        result = orchestrator.run_discovery_pipeline()

        assert result.success is True

    def test_run_full_pipeline(self):
        """Test running full pipeline."""
        orchestrator = PipelineOrchestrator(
            max_iterations=2,
        )

        result = orchestrator.run_full_pipeline(["https://facebook.com/page1"], iterations=2)

        assert isinstance(result, PipelineResult)
        assert result.execution_time > 0


class TestRunFullPipeline:
    """Tests for run_full_pipeline function."""

    def test_function_with_defaults(self):
        """Test function with default values."""
        result = run_full_pipeline(seed_pages=["https://facebook.com/page1"], max_iterations=1)

        assert isinstance(result, PipelineResult)

    def test_function_with_all_params(self):
        """Test function with all parameters."""
        mock_db = MagicMock()
        mock_classifier = MagicMock()

        result = run_full_pipeline(
            seed_pages=["https://facebook.com/page1"],
            database=mock_db,
            classifier=mock_classifier,
            max_iterations=2,
        )

        assert isinstance(result, PipelineResult)
        assert result.success is True
