"""Audit / traceability helpers for the validation UI.

Two consumers:

* :func:`format_audit_text` — pure-Python string formatter used by
  the unit tests and by ``render_audit_chip`` itself.
* :func:`render_audit_chip` — NiceGUI widget that draws a small
  "revisado por @user · hace 2h" chip in the listing and modal.

The chip is reusable across pages — anywhere a feedback row is shown
to a reviewer (listado, modal, future per-post view).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from nicegui import ui

from src.ui.nicegui_app import theme

_RELATIVE_THRESHOLDS: tuple[tuple[int, int], ...] = (
    (60, 1),
    (3600, 60),
    (86400, 3600),
    (86400 * 30, 86400),
    (86400 * 365, 86400 * 30),
)


def _parse_iso(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _format_relative(delta_seconds: float) -> str:
    """Return a Spanish short relative-time string.

    Examples: ``"hace 5 min"``, ``"hace 2 h"``, ``"hace 3 d"``,
    ``"hace 2 meses"``, ``"hace 1 año"``, ``"recién"``.
    """
    if delta_seconds < 30:
        return "recién"
    if delta_seconds < 60:
        return f"hace {int(delta_seconds)} s"

    for upper_bound, divisor in _RELATIVE_THRESHOLDS:
        if delta_seconds < upper_bound:
            value = max(1, int(delta_seconds // divisor))
            if divisor == 60:
                return f"hace {value} min"
            if divisor == 3600:
                return f"hace {value} h"
            if divisor == 86400:
                return f"hace {value} d"
            if divisor == 86400 * 30:
                return "hace 1 mes" if value == 1 else f"hace {value} meses"
            return f"hace {value} días"

    years = max(1, int(delta_seconds // (86400 * 365)))
    return "hace 1 año" if years == 1 else f"hace {years} años"


def format_audit_text(
    feedback_row: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> str:
    """Return a short audit label for a feedback row, or empty string.

    Empty string is returned for ``None`` rows (no feedback yet) or
    rows missing both ``updated_at`` and ``created_at`` timestamps —
    callers can use ``if audit_text:`` to gate the chip.
    """
    if not feedback_row:
        return ""

    username = feedback_row.get("reviewer_username") or feedback_row.get("reviewer") or "?"

    ts = _parse_iso(feedback_row.get("updated_at")) or _parse_iso(feedback_row.get("created_at"))
    if ts is None:
        return f"@{username}"

    ref = now or datetime.now(UTC)
    delta = max(0.0, (ref - ts).total_seconds())
    return f"@{username} · {_format_relative(delta)}"


def render_audit_chip(feedback_row: dict[str, Any] | None) -> None:
    """Render the audit chip — no-op when there's no feedback row."""
    text = format_audit_text(feedback_row)
    if not text:
        return
    ui.label(text).classes("text-xs").style(
        f"color: {theme.CHARCOAL_LIGHT}; font-style: italic; letter-spacing: 0.01em;"
    )


__all__ = ["format_audit_text", "render_audit_chip"]
