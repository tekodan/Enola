"""Unit tests for the audit chip helper.

These cover :func:`format_audit_text` (pure-Python). The NiceGUI
renderer :func:`render_audit_chip` is exercised through the page-level
smoke tests in ``test_validacion.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.ui.nicegui_app.components.audit_chip import (
    _format_relative,
    format_audit_text,
)


class TestFormatRelative:
    def test_fresh_timestamp_is_ahora(self):
        assert _format_relative(0) == "recién"

    def test_sub_minute_shows_seconds(self):
        assert _format_relative(45) == "hace 45 s"

    def test_minutes(self):
        assert _format_relative(60) == "hace 1 min"
        assert _format_relative(60 * 5) == "hace 5 min"
        assert _format_relative(60 * 59) == "hace 59 min"

    def test_hours(self):
        assert _format_relative(3600) == "hace 1 h"
        assert _format_relative(3600 * 5) == "hace 5 h"

    def test_days(self):
        assert _format_relative(86400) == "hace 1 d"
        assert _format_relative(86400 * 3) == "hace 3 d"

    def test_months(self):
        assert _format_relative(86400 * 30) == "hace 1 mes"
        assert _format_relative(86400 * 60) == "hace 2 meses"

    def test_years(self):
        assert _format_relative(86400 * 365) == "hace 1 año"
        assert _format_relative(86400 * 365 * 2) == "hace 2 años"

    def test_negative_clamped_to_zero(self):
        assert _format_relative(-100) == "recién"


class TestFormatAuditText:
    NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)

    def _row(self, **overrides):
        base = {
            "reviewer_username": "kim",
            "updated_at": (self.NOW - timedelta(hours=2)).isoformat(),
        }
        base.update(overrides)
        return base

    def test_none_returns_empty_string(self):
        assert format_audit_text(None, now=self.NOW) == ""

    def test_empty_dict_returns_empty_string(self):
        assert format_audit_text({}, now=self.NOW) == ""

    def test_basic_row(self):
        assert format_audit_text(self._row(), now=self.NOW) == "@kim · hace 2 h"

    def test_falls_back_to_reviewer_field(self):
        row = {"reviewer": "ana", "updated_at": self.NOW.isoformat()}
        assert format_audit_text(row, now=self.NOW) == "@ana · recién"

    def test_falls_back_to_created_at(self):
        row = {
            "reviewer_username": "lu",
            "created_at": (self.NOW - timedelta(days=3)).isoformat(),
        }
        assert format_audit_text(row, now=self.NOW) == "@lu · hace 3 d"

    def test_missing_timestamps_returns_username_only(self):
        row = {"reviewer_username": "mar"}
        assert format_audit_text(row, now=self.NOW) == "@mar"

    def test_naive_datetime_is_treated_as_utc(self):
        naive = (self.NOW - timedelta(hours=1)).replace(tzinfo=None)
        row = {"reviewer_username": "p", "updated_at": naive.isoformat()}
        assert format_audit_text(row, now=self.NOW) == "@p · hace 1 h"

    def test_invalid_timestamp_returns_username_only(self):
        row = {"reviewer_username": "x", "updated_at": "not-a-date"}
        assert format_audit_text(row, now=self.NOW) == "@x"

    def test_question_mark_for_missing_username(self):
        row = {"updated_at": self.NOW.isoformat()}
        assert format_audit_text(row, now=self.NOW) == "@? · recién"
