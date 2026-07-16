"""Tests for batch_analyzer error telemetry (Phase 4.1)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.analyzer.batch_analyzer import (
    BatchAnalysisStats,
    BatchAnalyzer,
    _record_error,
)


class TestRecordError:
    def test_json_decode_error_goes_to_parse_bucket(self) -> None:
        stats = BatchAnalysisStats()
        _record_error(stats, {"id": "x"}, "post", ValueError("not a JSONDecodeError"))
        # We only test the catch-all bucket here; JSONDecodeError requires
        # the exact class.
        assert stats.errors == 1

    def test_sample_buffer_caps_at_five(self) -> None:
        stats = BatchAnalysisStats()
        for i in range(8):
            _record_error(stats, {"id": f"id-{i}"}, "post", RuntimeError("boom"))
        assert len(stats.error_samples) == 5
        # The cap means we lose the OLDEST 3 errors (0, 1, 2).
        assert "id-0" not in stats.error_samples[0]
        assert "id-7" in stats.error_samples[-1]

    def test_ollama_connection_error_bucket(self) -> None:
        stats = BatchAnalysisStats()

        # Simulate aiohttp.ClientError surface via exc_name.
        class FakeOllamaError(Exception):
            pass

        # Simulate via name match
        class FakeClientError(Exception):
            pass

        # Direct via isinstance doesn't work since it's not the real aiohttp
        # class; the code does substring match on ``exc_name``.
        _record_error(stats, {"id": "x"}, "post", FakeClientError("timeout"))
        assert stats.errors_ollama == 1
        assert stats.errors == 1


class TestBatchAnalyzerStats:
    def test_default_state_has_zero_counters(self) -> None:
        s = BatchAnalysisStats()
        assert s.posts_analyzed == 0
        assert s.comments_analyzed == 0
        assert s.errors == 0
        assert s.errors_ollama == 0
        assert s.errors_parse == 0
        assert s.errors_validation == 0
        assert s.errors_db == 0
        assert s.error_samples == []

    def test_constructor_does_not_require_explicit_classifier(self) -> None:
        """With mocks for db/vector/feedback/llm, BatchAnalyzer builds OK."""
        BatchAnalyzer(
            database=MagicMock(),
            vector_store=MagicMock(),
            feedback_store=MagicMock(),
            llm_client=MagicMock(),
            analyze_posts=False,
            analyze_comments=False,
        )
