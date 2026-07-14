"""Premium KPI cards for the Enola NiceGUI dashboard.

Replace Streamlit's flat ``st.metric`` with cards that:

* Carry a Phosphor/Quasar icon in a tinted badge.
* Render the value in display serif (Lora).
* Optionally show a sub-line (e.g. "12 de 100 registros").
* Have a subtle hover lift (defined in :mod:`src.ui.nicegui_app.theme`).

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

from nicegui import ui

from src.ui.nicegui_app import theme


def _render_card(card: dict) -> None:
    label = card["label"]
    value = card["value"]
    icon = card.get("icon")
    sub = card.get("sub")
    accent = card.get("accent") or theme.PLUM

    with ui.element("div").classes("enola-kpi"):
        with ui.row().classes("w-full items-start justify-between gap-3"):
            ui.label(label).classes("enola-kpi-label")
            if icon:
                with ui.element("div").style(
                    "width: 32px; height: 32px; border-radius: 8px; "
                    f"background: {accent}1a; color: {accent}; "
                    "display: flex; align-items: center; justify-content: center;"
                ):
                    ui.icon(icon, size="16px")
        ui.label(value).classes("enola-kpi-value")
        if sub:
            ui.label(sub).classes("enola-kpi-sub")


def kpi_grid(columns: int, cards: Iterable[dict]) -> None:
    """Render a row of ``columns`` KPI cards.

    Each card is a dict with keys ``label``, ``value``, and optional
    ``icon``, ``sub``, ``accent``. Cards are equal-width inside the
    grid; pass 3-4 for the most balanced layout.
    """
    cards_list = list(cards)
    with (
        ui.element("div")
        .classes("w-full grid gap-4")
        .style(f"grid-template-columns: repeat({columns}, minmax(0, 1fr));")
    ):
        for card in cards_list:
            _render_card(card)
