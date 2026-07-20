"""Keyboard action dispatcher for the /validacion page.

This module bridges the platform-agnostic key registry in
:mod:`src.ui.nicegui_app.keys` to the runtime NiceGUI keyboard
listener. The wiring is intentionally tiny:

* :class:`ReviewerActionBus` is a tiny singleton-ish object that
  holds the page-level callbacks (next row, previous row, open modal,
  save feedback, etc.).
* :func:`install_review_shortcuts` registers the global listener
  once per page render and translates the key name into a bus call.

The bus pattern keeps the action logic testable: unit tests can
instantiate the bus and call its methods directly without booting
NiceGUI. The NiceGUI integration is exercised by the page smoke
tests.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from src.ui.nicegui_app.keys import VALIDATION_BINDINGS, is_typing_target

logger = logging.getLogger(__name__)


@dataclass
class ReviewerActionBus:
    """Holds the action callbacks the keyboard dispatcher invokes.

    The bus is intentionally narrow: it doesn't know about the
    NiceGUI widgets, only the side effects. Wiring the callbacks
    happens in :func:`_render_body` (the page) where widget handles
    are in scope.
    """

    next_row: Callable[[], None] | None = None
    prev_row: Callable[[], None] | None = None
    open_row: Callable[[], None] | None = None
    agree: Callable[[], None] | None = None
    reject: Callable[[], None] | None = None
    save: Callable[[], None] | None = None
    close_modal: Callable[[], None] | None = None
    show_help: Callable[[], None] | None = None
    toast: Callable[[str, str], None] | None = None

    def dispatch(self, token: str) -> bool:
        """Invoke the action for ``token``. Return True if dispatched."""
        actions = {
            "reviewer.next": self.next_row,
            "reviewer.prev": self.prev_row,
            "reviewer.open": self.open_row,
            "reviewer.agree": self.agree,
            "reviewer.reject": self.reject,
            "reviewer.save": self.save,
            "reviewer.close": self.close_modal,
            "reviewer.help": self.show_help,
        }
        action = actions.get(token)
        if action is None:
            return False
        try:
            action()
        except Exception:  # noqa: BLE001
            logger.exception("Keyboard action %s failed", token)
            return False
        return True


def install_review_shortcuts(
    bus: ReviewerActionBus,
    *,
    ignore: tuple[str, ...] = ("input", "select", "button", "textarea"),
) -> None:
    """Register one :class:`ui.keyboard` listener per binding.

    ``ignore`` matches NiceGUI's ``Keyboard.ignore`` semantics — events
    whose target tag is in the list are not dispatched. The default
    list mirrors the platform default; tests can pass an empty tuple
    to force-dispatch (used in synthetic JS events).
    """
    for binding in VALIDATION_BINDINGS:
        _install_one(bus, binding, ignore=ignore)


def _install_one(
    bus: ReviewerActionBus,
    binding: object,
    *,
    ignore: tuple[str, ...],
) -> None:
    token = getattr(binding, "token", "")

    def _handler(e: object) -> None:
        action = getattr(e, "action", None)
        if action is not None and getattr(action, "keyup", False):
            return
        if action is not None and getattr(action, "repeat", False):
            return
        # Try the JS event shape first (target.tagName from KeyEventArgs).
        target = getattr(e, "target", None)
        if target is not None:
            tag = getattr(target, "tagName", None)
            if tag and is_typing_target(tag):
                return
        bus.dispatch(token)

    ui.keyboard(
        on_key=_handler,
    ).props(f"ignore={list(ignore)}")


__all__ = ["ReviewerActionBus", "install_review_shortcuts"]
