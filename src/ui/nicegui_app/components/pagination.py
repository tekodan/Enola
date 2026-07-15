"""Pagination control component for the /validacion page.

Renders a compact "Página X de Y · Z filas · [anterior] [siguiente]"
bar with a page-size selector. Pure NiceGUI on top of the pure-Python
:func:`paginate` helper from :mod:`listing_state`.

The component does NOT own state — callers pass in the current
:class:`ListingState` and an ``on_change`` callback. The new state is
produced via :meth:`ListingState.with_updates`.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.listing_state import (
    PAGE_SIZE_CHOICES,
    ListingState,
)


def render_pagination(
    *,
    state: ListingState,
    total_rows: int,
    on_change: Callable[[ListingState], None],
) -> None:
    """Render a pagination bar — no-op when there's only one page.

    Args:
        state: Current listing state (read-only — we derive a new one).
        total_rows: Total rows AFTER filters are applied (before pagination).
        on_change: Callback invoked with the new state. The page should
            update its ``listing_state`` reference and re-render.
    """
    if total_rows == 0:
        return
    total_pages = max(1, (total_rows + state.page_size - 1) // state.page_size)
    if total_pages <= 1:
        return

    with (
        ui.element("div")
        .classes("w-full enola-pagination")
        .style(
            "display: flex; flex-wrap: wrap; gap: 0.75rem; "
            "align-items: center; justify-content: space-between; "
            "padding: 0.65rem 0.85rem; "
            "background: rgba(191, 161, 129, 0.06); "
            "border: 1px solid rgba(191, 161, 129, 0.18); "
            "border-radius: 0.5rem; "
            "margin-top: 0.75rem;"
        )
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("list", size="16px").style(f"color: {theme.PLUM};")
            ui.label(f"{total_rows} filas").classes("text-xs font-semibold").style(
                f"color: {theme.CHARCOAL}; letter-spacing: 0.02em;"
            )
            ui.label(f"· Página {state.page} de {total_pages}").classes("text-xs").style(
                f"color: {theme.CHARCOAL_LIGHT}; letter-spacing: 0.02em;"
            )

        with ui.row().classes("items-center gap-2"):
            ui.label("Por página:").classes("text-xs").style(
                f"color: {theme.CHARCOAL_LIGHT}; letter-spacing: 0.02em;"
            )
            ui.select(
                options={str(s): str(s) for s in PAGE_SIZE_CHOICES},
                value=str(state.page_size),
                on_change=lambda e: _emit(state.with_updates(page_size=int(e.value)), on_change),
            ).props("outlined dense").classes("w-20")

            ui.button(
                icon="chevron_left",
                on_click=lambda: _emit(state.with_updates(page=max(1, state.page - 1)), on_change),
            ).props("flat dense round").set_enabled(state.page > 1)

            ui.button(
                icon="chevron_right",
                on_click=lambda: _emit(
                    state.with_updates(page=min(total_pages, state.page + 1)),
                    on_change,
                ),
            ).props("flat dense round").set_enabled(state.page < total_pages)


def _emit(new_state: ListingState, on_change: Callable[[ListingState], None]) -> None:
    """Invoke the callback — separated for closure cleanliness."""
    on_change(new_state)


__all__ = ["render_pagination"]
