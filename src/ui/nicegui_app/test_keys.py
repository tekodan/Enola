"""Unit tests for the keyboard shortcut registry."""

from __future__ import annotations

import pytest

from src.ui.nicegui_app.keys import (
    VALIDATION_BINDINGS,
    binding_for,
    describe_bindings,
    is_typing_target,
)


class TestBindingFor:
    def test_lowercase_match(self):
        assert binding_for("j") is not None
        assert binding_for("j").token == "reviewer.next"

    def test_uppercase_match(self):
        assert binding_for("K") is not None
        assert binding_for("K").token == "reviewer.prev"

    def test_escape_is_case_insensitive(self):
        assert binding_for("Escape") is not None
        assert binding_for("Escape").token == "reviewer.close"
        assert binding_for("esc") is not None
        assert binding_for("esc").token == "reviewer.close"

    def test_unknown_key_returns_none(self):
        assert binding_for("z") is None
        assert binding_for("") is None

    def test_help_binding(self):
        assert binding_for("?") is not None
        assert binding_for("?").token == "reviewer.help"


class TestDescribeBindings:
    def test_returns_pairs(self):
        pairs = describe_bindings()
        assert isinstance(pairs, list)
        assert all(len(p) == 2 for p in pairs)
        assert all(isinstance(p[0], str) and isinstance(p[1], str) for p in pairs)

    def test_pairs_cover_documented_actions(self):
        tokens = {b.token for b in VALIDATION_BINDINGS}
        assert "reviewer.next" in tokens
        assert "reviewer.agree" in tokens
        assert "reviewer.reject" in tokens
        assert "reviewer.save" in tokens
        assert "reviewer.close" in tokens


class TestIsTypingTarget:
    @pytest.mark.parametrize(
        "tag",
        ["INPUT", "TEXTAREA", "SELECT", "input", "TextArea", "select"],
    )
    def test_typing_tags_are_detected(self, tag):
        assert is_typing_target(tag) is True

    @pytest.mark.parametrize("tag", ["DIV", "BUTTON", "A", "BODY", None, "", "SPAN"])
    def test_non_typing_tags_are_allowed(self, tag):
        assert is_typing_target(tag) is False
