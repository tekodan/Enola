"""Premium KPI cards for the Enola NiceGUI dashboard.

Replace Streamlit's flat ``st.metric`` with cards that:

* Carry a Phosphor/Quasar icon in a tinted badge.
* Render the value in display serif (Lora).
* Optionally show a sub-line (e.g. "12 de 100 registros").
* Have a subtle hover lift + accent rail defined in
  :mod:`src.ui.nicegui_app.theme`.
* Animate in with a subtle fade-up so the grid settles gracefully.

Usage::

    kpi_grid(4, [
        {"label": "Análisis totales", "value": "1.234", "icon": "description"},
        {"label": "% con violencia", "value": "37,5%", "icon": "warning",
         "accent": "#9D4E5B"},
        ...
    ])
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import cycle

from nicegui import ui

from src.ui.nicegui_app import theme

_FADE_CLASSES = ("enola-fade-in", "enola-fade-in-1", "enola-fade-in-2", "enola-fade-in-3")


def _render_card(card: dict, *, fade_class: str) -> None:
    label = card["label"]
    value = card["value"]
    icon = card.get("icon")
    sub = card.get("sub")
    accent = card.get("accent") or theme.PLUM

    with ui.element("div").classes(f"enola-kpi {fade_class}"):
        with ui.row().classes("w-full items-start justify-between gap-3"):
            ui.label(label).classes("enola-kpi-label")
            if icon:
                with (
                    ui.element("div")
                    .classes("enola-kpi-icon")
                    .style(f"background: {accent}1f; color: {accent};")
                ):
                    ui.icon(icon, size="18px")
        ui.label(value).classes("enola-kpi-value")
        if sub:
            ui.label(sub).classes("enola-kpi-sub")


def kpi_grid(columns: int, cards: Iterable[dict]) -> None:
    """Render a row of ``columns`` KPI cards.

    Each card is a dict with keys ``label``, ``value``, and optional
    ``icon``, ``sub``, ``accent``. Cards are equal-width inside the
    grid; pass 3-4 for the most balanced layout. The grid fades in
    each card with a 60ms stagger so it doesn't pop at once.

    On mobile the grid collapses to fewer columns via the
    ``enola-grid--c<N>`` class (CSS handles the responsive pass).
    """
    cards_list = list(cards)
    col_class = f"enola-grid--c{columns}" if 1 <= columns <= 4 else "enola-grid--c4"
    with ui.element("div").classes(f"w-full enola-grid {col_class}"):
        for card, fade_cls in zip(cards_list, cycle(_FADE_CLASSES)):
            _render_card(card, fade_class=fade_cls)


def empty_state(
    icon: str,
    title: str,
    *,
    hint: str | None = None,
) -> None:
    """Render a premium placeholder for "nothing to show" cases.

    Uses the new ``.enola-empty`` token defined in :mod:`theme`. The
    optional hint is rendered below the title in muted text.
    """
    with ui.element("div").classes("enola-empty"):
        ui.icon(icon, size="44px").style(f"color: {theme.BRASS_DEEP}; opacity: 0.85;")
        ui.label(title).classes("enola-empty-title")
        if hint:
            ui.label(hint).classes("text-sm mt-2").style(
                "color: var(--enola-charcoal-light); max-width: 50ch; "
                "margin-left: auto; margin-right: auto; line-height: 1.5;"
            )
