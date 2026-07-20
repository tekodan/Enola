"""Unit tests for the label-diff helper."""

from __future__ import annotations

from src.ui.nicegui_app.components.diff import (
    compute_label_diff,
    has_changes,
)


class TestComputeLabelDiff:
    def test_empty_inputs(self):
        assert compute_label_diff([], []) == []

    def test_none_inputs(self):
        assert compute_label_diff(None, None) == []

    def test_identical_inputs_are_all_kept(self):
        labels = [{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}]
        out = compute_label_diff(labels, labels)
        assert len(out) == 1
        assert out[0]["op"] == "kept"
        assert out[0]["cat"] == "VDG_VIOLENCIA_SIMBOLICA"
        assert out[0]["dim"] == "1.1"

    def test_added_label(self):
        ai = [{"categoria": "A", "dimension": "1"}]
        corr = [
            {"categoria": "A", "dimension": "1"},
            {"categoria": "B", "dimension": "2"},
        ]
        out = compute_label_diff(ai, corr)
        ops = {entry["op"] for entry in out}
        assert "kept" in ops
        assert "added" in ops

    def test_removed_label(self):
        ai = [
            {"categoria": "A", "dimension": "1"},
            {"categoria": "B", "dimension": "2"},
        ]
        corr = [{"categoria": "A", "dimension": "1"}]
        out = compute_label_diff(ai, corr)
        removed = [e for e in out if e["op"] == "removed"]
        assert len(removed) == 1
        assert removed[0]["cat"] == "B"

    def test_changed_dimension(self):
        ai = [{"categoria": "A", "dimension": "1"}]
        corr = [{"categoria": "A", "dimension": "2"}]
        out = compute_label_diff(ai, corr)
        assert len(out) == 1
        assert out[0]["op"] == "changed"
        assert out[0]["cat"] == "A"
        assert out[0]["dim"] == "2"
        assert out[0]["ai_dim"] == "1"

    def test_omitted_dimension_treated_as_empty(self):
        ai = [{"categoria": "A"}]
        corr = [{"categoria": "A", "dimension": "1"}]
        out = compute_label_diff(ai, corr)
        # "A" with no dim is treated as the dim-less "A"; adding a
        # dim is an "added" label.
        assert out[0]["op"] == "added"
        assert out[0]["cat"] == "A"
        assert out[0]["dim"] == "1"

    def test_blank_label_dropped(self):
        ai = [{"categoria": "", "dimension": "x"}]
        corr = []
        assert compute_label_diff(ai, corr) == []

    def test_result_is_sorted(self):
        ai = [{"categoria": "B", "dimension": "2"}]
        corr = [
            {"categoria": "A", "dimension": "1"},
            {"categoria": "B", "dimension": "2"},
            {"categoria": "C", "dimension": "3"},
        ]
        out = compute_label_diff(ai, corr)
        # kept first, then added (sorted).
        assert [e["op"] for e in out] == ["kept", "added", "added"]
        assert out[1]["cat"] == "A"
        assert out[2]["cat"] == "C"


class TestHasChanges:
    def test_empty_diff_has_no_changes(self):
        assert has_changes([]) is False

    def test_only_kept_has_no_changes(self):
        diff = [{"op": "kept", "cat": "A", "dim": "1"}]
        assert has_changes(diff) is False

    def test_added_counts_as_change(self):
        diff = [{"op": "added", "cat": "A", "dim": "1"}]
        assert has_changes(diff) is True

    def test_removed_counts_as_change(self):
        diff = [{"op": "removed", "cat": "A", "dim": "1"}]
        assert has_changes(diff) is True

    def test_changed_counts_as_change(self):
        diff = [{"op": "changed", "cat": "A", "dim": "1", "ai_dim": "2"}]
        assert has_changes(diff) is True
