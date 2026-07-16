"""Premium KPI cards for the Enola NiceGUI dashboard.

Two visual variants:

* **Light / cream** (``kpi_grid``) — flat cards with a tinted icon
  badge, used by most pages (legacy hero, Regla 1 reliability, etc.).
* **Premium dark** (``premium_dark_card`` + family) — charcoal/plum
  background with gold accents, used by ``/inicio`` for the headline
  Resumen grid (Total Casos, Precisión RAG, Categorías Detectadas,
  Validación Humana).

The dark variant supports four inner-visualizations: a sparkline
(``chart="spark"``), a circular gauge (``chart="gauge"``), a category
list (``chart="list"``) and a progress bar with avatars
(``chart="progress"``).

All styles live in :mod:`src.ui.nicegui_app.theme`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from itertools import cycle

from nicegui import ui

from src.ui.nicegui_app import theme

_FADE_CLASSES = ("enola-fade-in", "enola-fade-in-1", "enola-fade-in-2", "enola-fade-in-3")
_PREMIUM_FADE_CLASSES = (
    "enola-fade-in",
    "enola-fade-in-1",
    "enola-fade-in-2",
    "enola-fade-in-3",
)


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
    """Render a row of ``columns`` light-theme KPI cards."""
    cards_list = list(cards)
    col_class = f"enola-grid--c{columns}" if 1 <= columns <= 4 else "enola-grid--c4"
    with ui.element("div").classes(f"w-full enola-grid {col_class}"):
        for card, fade_cls in zip(cards_list, cycle(_FADE_CLASSES)):
            _render_card(card, fade_class=fade_cls)


# =====================================================================
# Premium-dark cards
# =====================================================================


def _gauge_svg(pct: float, *, size: int = 96, stroke: int = 8) -> str:
    """Return an SVG snippet for a circular gauge at ``pct`` (0..100)."""
    pct = max(0.0, min(100.0, float(pct)))
    radius = (size - stroke) / 2
    circumference = 2 * math.pi * radius
    offset = circumference * (1 - pct / 100.0)
    return (
        f'<svg class="enola-kpi-dark__gauge-svg" viewBox="0 0 {size} {size}">'
        f'<circle class="enola-kpi-dark__gauge-track" cx="{size / 2}" cy="{size / 2}" '
        f'r="{radius}"></circle>'
        f'<circle class="enola-kpi-dark__gauge-fill" cx="{size / 2}" cy="{size / 2}" '
        f'r="{radius}" stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}"></circle>'
        "</svg>"
    )


def _sparkline_svg(points: list[float], *, width: int = 240, height: int = 48) -> str:
    """Return a smooth SVG sparkline through ``points`` (normalised)."""
    if not points or len(points) < 2:
        return ""
    lo, hi = min(points), max(points)
    span = max(hi - lo, 1e-9)
    n = len(points)
    step = width / (n - 1)
    coords = []
    for i, v in enumerate(points):
        x = i * step
        y = height - ((v - lo) / span) * (height - 6) - 3
        coords.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(coords)
    last_x = (n - 1) * step
    last_y = height - ((points[-1] - lo) / span) * (height - 6) - 3
    return (
        f'<svg class="enola-kpi-dark__spark" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none">'
        f'<polyline points="{polyline}" fill="none" stroke="var(--enola-brass)" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'filter="drop-shadow(0 0 4px rgba(191, 161, 129, 0.45))"></polyline>'
        f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="3" '
        f'fill="var(--enola-brass)"></circle>'
        "</svg>"
    )


def premium_dark_card(
    *,
    title: str,
    subtitle: str | None = None,
    value: str | None = None,
    sub: str | None = None,
    chart: str | None = None,
    gauge_pct: float | None = None,
    spark_points: list[float] | None = None,
    list_items: list[str] | None = None,
    progress_pct: float | None = None,
    avatars: list[str] | None = None,
    avatar_more: int | None = None,
    corner_icon: str | None = None,
    fade_class: str = "enola-fade-in",
) -> None:
    """Render a single premium-dark KPI card.

    Parameters mirror the four inner visualizations:

    * ``chart="spark"`` + ``spark_points`` — line chart with trailing dot.
    * ``chart="gauge"`` + ``gauge_pct`` — circular gauge (0..100).
    * ``chart="list"``  + ``list_items`` — bulleted category list.
    * ``chart="progress"`` + ``progress_pct`` + ``avatars`` — gold bar
      with reviewer avatars (use ``avatar_more`` for "+N" overflow).
    """
    with ui.element("div").classes(f"enola-kpi-dark {fade_class}"):
        if corner_icon:
            with ui.element("div").classes("enola-kpi-dark__corner"):
                ui.icon(corner_icon, size="14px").style("color: var(--enola-brass);")

        with ui.element("div").classes("enola-kpi-dark__label"):
            ui.label(title)
            if subtitle:
                ui.label(subtitle)

        if value:
            ui.label(value).classes("enola-kpi-dark__value")

        if chart == "spark" and spark_points:
            with ui.element("div").classes("enola-kpi-dark__chart"):
                ui.html(_sparkline_svg(spark_points), sanitize=False)

        if chart == "gauge" and gauge_pct is not None:
            with ui.element("div").classes("enola-kpi-dark__gauge"):
                ui.html(_gauge_svg(gauge_pct), sanitize=False)
                with ui.element("div").classes("enola-kpi-dark__gauge-text"):
                    ui.label(f"{int(round(gauge_pct))}%")

        if chart == "list" and list_items:
            items_html = "".join(f"<li>{item}</li>" for item in list_items)
            ui.html(
                f'<ul class="enola-kpi-dark__list">{items_html}</ul>',
                sanitize=False,
            )

        if chart == "progress" and progress_pct is not None:
            pct = max(0.0, min(100.0, progress_pct))
            with ui.element("div").classes("enola-kpi-dark__progress"):
                ui.html(
                    f'<div class="enola-kpi-dark__progress-fill" style="width: {pct:.1f}%;"></div>',
                    sanitize=False,
                )
            if avatars:
                with ui.element("div").classes("enola-kpi-dark__avatars"):
                    for initials in avatars[:5]:
                        ui.label(initials).classes("enola-kpi-dark__avatar")
                    if avatar_more and avatar_more > 0:
                        ui.label(f"+{avatar_more}").classes("enola-kpi-dark__avatar")

        if sub:
            ui.label(sub).classes("enola-kpi-dark__sub")


def premium_dark_grid(cards: Iterable[dict]) -> None:
    """Render a row of 4 premium-dark KPI cards.

    Each entry is forwarded to :func:`premium_dark_card` as kwargs.
    Cards are equal-width and fade in with a 60ms stagger.
    """
    cards_list = list(cards)
    with ui.element("div").classes("w-full enola-grid enola-grid--c4"):
        for card, fade_cls in zip(cards_list, cycle(_PREMIUM_FADE_CLASSES)):
            premium_dark_card(fade_class=fade_cls, **card)


def empty_state(
    icon: str,
    title: str,
    *,
    hint: str | None = None,
) -> None:
    """Render a premium placeholder for "nothing to show" cases."""
    with ui.element("div").classes("enola-empty"):
        ui.icon(icon, size="44px").style(f"color: {theme.BRASS_DEEP}; opacity: 0.85;")
        ui.label(title).classes("enola-empty-title")
        if hint:
            ui.label(hint).classes("text-sm mt-2").style(
                "color: var(--enola-charcoal-light); max-width: 50ch; "
                "margin-left: auto; margin-right: auto; line-height: 1.5;"
            )


__all__ = [
    "empty_state",
    "kpi_grid",
    "premium_dark_card",
    "premium_dark_grid",
]
