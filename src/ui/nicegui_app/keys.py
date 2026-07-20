"""Keyboard shortcut registry for the Enola NiceGUI app.

Centralising the bindings here gives us:

* A single place to look up "what does J do?" — scattered
  ``ui.keyboard`` calls in pages become opaque.
* Stable binding strings that can be unit-tested (no NiceGUI boot
  required).
* Discoverability — :func:`describe_bindings` returns a list of
  ``(key, description)`` pairs suitable for a "?" help dialog.

Bindings map to action tokens (short, uppercase strings like
``"reviewer.next"``). Page code maps tokens to callables — keeps the
keys layer independent of the page state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyBinding:
    """One row of the shortcut table."""

    key: str
    token: str
    description: str


# Validación page bindings. These are kept lowercase to match the
# physical key the user presses (case-insensitive match is the caller's
# responsibility, but the strings here are the canonical labels).
VALIDATION_BINDINGS: tuple[KeyBinding, ...] = (
    KeyBinding("j", "reviewer.next", "Siguiente fila (↓)"),
    KeyBinding("k", "reviewer.prev", "Fila anterior (↑)"),
    KeyBinding("a", "reviewer.agree", "Marcar como de acuerdo"),
    KeyBinding("r", "reviewer.reject", "Marcar para corregir"),
    KeyBinding("s", "reviewer.save", "Guardar feedback"),
    KeyBinding("Escape", "reviewer.close", "Cerrar modal / cancelar"),
    KeyBinding("?", "reviewer.help", "Mostrar atajos"),
)


def binding_for(key: str) -> KeyBinding | None:
    """Return the binding whose ``key`` matches ``key`` (case-insensitive).

    Returns ``None`` when the key isn't bound. ``"Escape"``, ``"Esc"``
    and ``"esc"`` all match the escape binding; same for ``"?"`` /
    ``"Shift+/"`` style aliases.
    """
    if not key:
        return None
    candidate = key.strip().lower()
    if candidate in {"esc", "escape"}:
        candidate = "escape"
    elif candidate in {"?", "shift+/"}:
        candidate = "?"
    for binding in VALIDATION_BINDINGS:
        if binding.key.lower() == candidate:
            return binding
    return None


def describe_bindings() -> list[tuple[str, str]]:
    """Return ``[(key, description), ...]`` ordered for display."""
    return [(b.key, b.description) for b in VALIDATION_BINDINGS]


def is_typing_target(tag: str | None) -> bool:
    """Return ``True`` if the event target is a typing-capable element.

    Used to gate global shortcuts so they don't fire while the user is
    editing a textarea / select. The check is conservative — better to
    miss a shortcut than to interrupt typing.
    """
    if not tag:
        return False
    return tag.upper() in {"INPUT", "TEXTAREA", "SELECT"}


__all__ = [
    "VALIDATION_BINDINGS",
    "KeyBinding",
    "binding_for",
    "describe_bindings",
    "is_typing_target",
]
