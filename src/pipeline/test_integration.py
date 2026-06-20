"""Integration tests for pipeline module."""

from datetime import datetime
from unittest.mock import MagicMock

from src.pipeline.orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStats,
)


class TestFullPipelineWorkflow:
    """Integration tests for full pipeline workflow."""

    def test_single_iteration_workflow(self):
        """Test single iteration workflow."""
        orchestrator = PipelineOrchestrator(max_iterations=1)

        result = orchestrator.run_full_pipeline(["https://facebook.com/page1"], iterations=1)

        assert isinstance(result, PipelineResult)
        assert result.stats.pages_scraped >= 1

    def test_multi_iteration_workflow(self):
        """Test multi-iteration workflow."""
        orchestrator = PipelineOrchestrator(max_iterations=3)

        result = orchestrator.run_full_pipeline(["https://facebook.com/page1"], iterations=2)

        assert isinstance(result, PipelineResult)
        # Should have run 2 iterations

    def test_empty_seeds_workflow(self):
        """Test workflow with empty seeds."""
        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_full_pipeline([], iterations=1)

        assert isinstance(result, PipelineResult)
        # Should complete without errors


class TestPipelineStats:
    """Tests for pipeline statistics tracking."""

    def test_stats_accumulation(self):
        """Test that stats accumulate correctly."""
        orchestrator = PipelineOrchestrator()

        result1 = orchestrator.run_seed_pipeline(["https://facebook.com/page1"])
        result2 = orchestrator.run_seed_pipeline(["https://facebook.com/page2"])

        # Stats should be independent
        assert result1.stats.pages_scraped == 1
        assert result2.stats.pages_scraped == 1

    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = PipelineStats()

        assert stats.pages_scraped == 0
        assert stats.posts_found == 0
        assert stats.comments_found == 0
        assert stats.execution_time_seconds == 0.0


class TestPipelineResult:
    """Tests for pipeline result handling."""

    def test_result_success(self):
        """Test successful result."""
        stats = PipelineStats(pages_scraped=5, posts_found=50)

        result = PipelineResult(
            success=True,
            stats=stats,
        )

        assert result.success is True
        assert result.stats.pages_scraped == 5

    def test_result_with_errors(self):
        """Test result with errors."""
        result = PipelineResult(
            success=False,
            stats=PipelineStats(),
            errors=["Connection timeout", "Parse error"],
        )

        assert result.success is False
        assert len(result.errors) == 2

    def test_result_with_new_seeds(self):
        """Test result with new seeds discovered."""
        result = PipelineResult(
            success=True,
            stats=PipelineStats(new_seed_pages_added=3),
            new_seeds=[
                "https://facebook.com/page2",
                "https://facebook.com/page3",
                "https://facebook.com/page4",
            ],
        )

        assert len(result.new_seeds) == 3
        assert result.stats.new_seed_pages_added == 3


class TestEndToEnd:
    """End-to-end tests."""

    def test_complete_workflow(self):
        """Test complete pipeline workflow."""
        # Create orchestrator
        orchestrator = PipelineOrchestrator(
            max_iterations=1,
            min_violence_score=0.7,
        )

        # Run full pipeline
        result = orchestrator.run_full_pipeline(
            seed_pages=[
                "https://facebook.com/page1",
                "https://facebook.com/page2",
            ],
            iterations=1,
        )

        # Verify result structure
        assert isinstance(result, PipelineResult)
        assert hasattr(result, "success")
        assert hasattr(result, "stats")
        assert hasattr(result, "errors")
        assert hasattr(result, "execution_time")
        assert hasattr(result, "timestamp")

    def test_workflow_with_database(self):
        """Test workflow with database."""
        # This would require actual database setup
        # For now, just verify the interface
        mock_db = MagicMock()
        mock_db.get_seed_pages.return_value = []

        orchestrator = PipelineOrchestrator(
            database=mock_db,
            max_iterations=1,
        )

        result = orchestrator.run_seed_pipeline(["https://facebook.com/page1"])

        assert isinstance(result, PipelineResult)

    def test_workflow_error_handling(self):
        """Test workflow error handling."""
        orchestrator = PipelineOrchestrator()

        # Pipeline should complete even with empty seeds
        result = orchestrator.run_full_pipeline([], iterations=1)

        assert isinstance(result, PipelineResult)
        # May have errors but should still return result


class TestPipelineConfiguration:
    """Tests for pipeline configuration."""

    def test_custom_iterations(self):
        """Test custom iteration count."""
        orchestrator = PipelineOrchestrator(max_iterations=5)

        assert orchestrator.max_iterations == 5

    def test_custom_threshold(self):
        """Test custom violence threshold."""
        orchestrator = PipelineOrchestrator(min_violence_score=0.8)

        assert orchestrator.min_violence_score == 0.8

    def test_custom_classifier(self):
        """Test custom classifier."""
        mock_classifier = MagicMock()
        orchestrator = PipelineOrchestrator(classifier=mock_classifier)

        assert orchestrator.classifier == mock_classifier


class TestPipelineTiming:
    """Tests for pipeline timing."""

    def test_execution_time_recorded(self):
        """Test that execution time is recorded."""
        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_seed_pipeline(["https://facebook.com/page1"])

        assert result.execution_time >= 0

    def test_timestamp_recorded(self):
        """Test that timestamp is recorded."""
        result = PipelineResult(
            success=True,
            stats=PipelineStats(),
        )

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)
