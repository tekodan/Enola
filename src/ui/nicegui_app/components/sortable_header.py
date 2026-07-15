"""Sortable table header component for the /validacion page.

Renders a clickable ``<th>`` that toggles between ascending and
descending order. The current sort state is reflected visually with
an arrow (▲/▼) so the reviewer always knows the active direction.

The component is pure-Python over NiceGUI: it returns a NiceGUI
``ui.element`` and accepts an ``on_change`` callback fired with the
new ``(sort_key, sort_dir)`` tuple. The component does NOT mutate
state on its own — callers pass the resulting values back into their
:class:`ListingState` and refresh the listing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from src.ui.nicegui_app import theme


@dataclass(frozen=True)
class SortSpec:
    """Active sort descriptor — what the header shows + emits."""

    key: str
    direction: str  # "asc" | "desc"
    label: str


_SORT_ARROWS = {"asc": "▲", "desc": "▼"}


def render_sortable_header(
    *,
    label: str,
    sort_key: str,
    active_key: str,
    active_dir: str,
    on_change: Callable[[str, str], None],
    align: str = "left",
) -> None:
    """Render one sortable column header inside a ``<thead>``.

    Clicking the header toggles direction if it's the active column,
    otherwise it switches to ascending on the new key. The visual
    arrow + bold weight communicates active state.

    Args:
        label: Display text (already uppercased by the caller).
        sort_key: Identifier this header emits when clicked.
        active_key: Currently active sort key (page-level).
        active_dir: Currently active sort direction.
        on_change: Callback invoked with ``(sort_key, new_dir)``.
        align: ``"left"`` / ``"center"`` / ``"right"``.
    """
    is_active = sort_key == active_key
    arrow = _SORT_ARROWS.get(active_dir, "") if is_active else ""
    weight = "700" if is_active else "600"
    color = theme.PLUM if is_active else theme.CHARCOAL_LIGHT

    def _handle_click() -> None:
        if is_active:
            new_dir = "desc" if active_dir == "asc" else "asc"
        else:
            new_dir = "asc"
        on_change(sort_key, new_dir)

    btn = ui.button(on_click=_handle_click).props("flat dense no-caps").classes("enola-sort-header")
    btn.style(
        f"padding: 0.55rem 0.85rem; width: 100%; "
        f"justify-content: {('flex-end' if align == 'right' else 'flex-start' if align == 'left' else 'center')}; "
        f"color: {color}; font-weight: {weight}; font-size: 0.7rem; "
        "letter-spacing: 0.08em; text-transform: uppercase; "
        "background: transparent;"
    )
    with btn:
        with ui.row().classes("items-center gap-1 no-wrap"):
            ui.label(label)
            if arrow:
                ui.label(arrow).classes("text-xs").style(f"color: {theme.PLUM}; font-weight: 700;")


__all__ = ["SortSpec", "render_sortable_header"]
