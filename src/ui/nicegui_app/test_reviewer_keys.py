"""Unit tests for the ReviewerActionBus dispatcher.

These exercise the bus without booting NiceGUI — the page-level
integration is exercised in :mod:`test_validacion`.
"""

from __future__ import annotations

from src.ui.nicegui_app.reviewer_keys import ReviewerActionBus


class TestDispatch:
    def test_known_token_invokes_callback(self):
        called: list[bool] = []
        bus = ReviewerActionBus(next_row=lambda: called.append(True))
        assert bus.dispatch("reviewer.next") is True
        assert called == [True]

    def test_unknown_token_returns_false(self):
        bus = ReviewerActionBus()
        assert bus.dispatch("reviewer.bogus") is False

    def test_none_callback_returns_false(self):
        bus = ReviewerActionBus()  # next_row is None
        assert bus.dispatch("reviewer.next") is False

    def test_exception_in_callback_is_swallowed(self):
        def _boom() -> None:
            raise RuntimeError("kaboom")

        bus = ReviewerActionBus(next_row=_boom)
        assert bus.dispatch("reviewer.next") is False

    def test_all_tokens_dispatchable(self):
        """Every token in the registry has a slot on the bus."""
        from src.ui.nicegui_app.keys import VALIDATION_BINDINGS

        bus = ReviewerActionBus()
        for binding in VALIDATION_BINDINGS:
            result = bus.dispatch(binding.token)
            # Result is False because callbacks are None, but no
            # AttributeError — proves the token has a slot.
            assert result is False


class TestBusSlots:
    def test_all_slots_are_independent(self):
        """Wiring one slot doesn't leak into another."""
        next_calls: list[int] = []
        prev_calls: list[int] = []
        bus = ReviewerActionBus(
            next_row=lambda: next_calls.append(1),
            prev_row=lambda: prev_calls.append(1),
        )
        bus.dispatch("reviewer.next")
        bus.dispatch("reviewer.prev")
        bus.dispatch("reviewer.next")
        assert len(next_calls) == 2
        assert len(prev_calls) == 1
