"""Unit tests for the review progress estimator."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta

from src.ui.nicegui_app.components.progress import (
    ProgressState,
    compute_progress,
    compute_reviewed_count,
    format_eta,
    load_state,
    save_state,
)


class TestComputeReviewedCount:
    def test_empty_listing(self):
        assert compute_reviewed_count([]) == (0, 0)

    def test_mixed_rows(self):
        rows = [
            {"feedback_row": {"id": 1}},
            {"feedback_row": None},
            {"feedback_row": {}},
            {"feedback_row": {"id": 2}},
        ]
        reviewed, total = compute_reviewed_count(rows)
        assert total == 4
        assert reviewed == 2


class TestComputeProgress:
    def test_empty_returns_one(self):
        assert compute_progress(0, 0) == 1.0

    def test_partial(self):
        assert compute_progress(3, 10) == 0.3

    def test_full(self):
        assert compute_progress(10, 10) == 1.0

    def test_clamps_to_unit_range(self):
        assert compute_progress(15, 10) == 1.0
        assert compute_progress(-1, 10) == 0.0


class TestFormatEta:
    def test_unknown(self):
        assert format_eta(None) == "—"

    def test_zero(self):
        assert format_eta(0) == "Listo"

    def test_seconds(self):
        assert format_eta(30) == "<1 min"

    def test_minutes(self):
        assert format_eta(60) == "~1 min"
        assert format_eta(60 * 5) == "~5 min"
        assert format_eta(60 * 59) == "~59 min"

    def test_hours(self):
        assert format_eta(3600) == "~1 h"
        assert format_eta(3600 * 3) == "~3 h"

    def test_days(self):
        assert format_eta(86400) == "~1 d"
        assert format_eta(86400 * 5) == "~5 d"

    def test_nan_and_inf(self):
        assert format_eta(float("nan")) == "—"
        assert format_eta(float("inf")) == "—"


class TestProgressState:
    def test_initial_eta_is_none(self):
        ps = ProgressState()
        assert ps.estimate_seconds_remaining(5) is None

    def test_first_sample_does_not_yield_eta(self):
        ps = ProgressState()
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        assert ps.estimate_seconds_remaining(5) is None

    def test_two_samples_produce_eta(self):
        ps = ProgressState()
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 30, tzinfo=UTC))
        eta = ps.estimate_seconds_remaining(10)
        assert eta is not None
        assert 290 <= eta <= 310  # 30s × 10 reviews

    def test_ema_blends_old_and_new(self):
        ps = ProgressState(ema_alpha=0.5)
        ps.ema_seconds = 60.0
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        # First sample: no previous → ema stays at 60.
        ps.record_review(now=datetime(2026, 7, 15, 12, 1, 30, tzinfo=UTC))
        # Second sample: 90s gap blended with prior 60s → 0.5*90 + 0.5*60 = 75.
        assert ps.ema_seconds is not None
        assert ps.ema_seconds == 75.0

    def test_ema_initializes_to_first_gap(self):
        ps = ProgressState(ema_alpha=0.5)
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 45, tzinfo=UTC))
        assert ps.ema_seconds == 45.0

    def test_samples_bounded_to_window(self):
        ps = ProgressState()
        for i in range(20):
            ps.record_review(now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC) + timedelta(seconds=i))
        assert len(ps.samples) == 10

    def test_zero_pending_returns_none(self):
        ps = ProgressState()
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 30, tzinfo=UTC))
        assert ps.estimate_seconds_remaining(0) is None


class TestStorageRoundTrip:
    def test_load_none_returns_fresh_state(self):
        ps = load_state(None)
        assert ps.samples == deque()
        assert ps.ema_seconds is None

    def test_load_missing_key_returns_fresh_state(self):
        ps = load_state({})
        assert ps.samples == deque()

    def test_round_trip_preserves_state(self):
        storage: dict = {}
        ps = ProgressState()
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        ps.record_review(now=datetime(2026, 7, 15, 12, 0, 30, tzinfo=UTC))
        save_state(storage, ps)
        restored = load_state(storage)
        assert restored.ema_seconds == ps.ema_seconds
        assert list(restored.samples) == list(ps.samples)

    def test_save_to_none_is_noop(self):
        ps = ProgressState()
        save_state(None, ps)
