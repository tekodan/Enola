"""Plotly chart builders for the Enola NiceGUI dashboard.

Replaces the Altair chart builders from the legacy Streamlit landing.
Plotly gives us interactive tooltips, export-to-PNG, zoom, and a much
richer aesthetic — at the cost of being heavier than Altair.

Each builder returns a configured ``plotly.graph_objects.Figure``
ready to be mounted via ``ui.plotly(fig)``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import plotly.graph_objects as go

from src.ui.nicegui_app import theme
from src.ui.utils import CATEGORIAS_ORDENADAS

# --- shared helpers ----------------------------------------------------------


_PALETTE_LIGHT = {
    "bg": theme.CREAM,
    "ink": theme.CHARCOAL,
    "muted": theme.CHARCOAL_LIGHT,
    "grid": "rgba(58, 49, 66, 0.07)",
    "axis_line": "rgba(58, 49, 66, 0.18)",
}

_PALETTE_DARK = {
    "bg": theme.INK,
    "ink": "rgba(250, 246, 240, 0.92)",
    "muted": "rgba(250, 246, 240, 0.55)",
    "grid": "rgba(250, 246, 240, 0.08)",
    "axis_line": "rgba(250, 246, 240, 0.18)",
}


def _palette(dark: bool) -> dict[str, str]:
    return _PALETTE_DARK if dark else _PALETTE_LIGHT


def _apply_common_layout(
    fig: go.Figure,
    *,
    title: str | None = None,
    dark: bool = False,
    height: int = 380,
    margin: dict | None = None,
) -> go.Figure:
    pal = _palette(dark)
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family=theme.FONT_DISPLAY, size=18, color=pal["ink"]),
            x=0.02,
            xanchor="left",
        )
        if title
        else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=theme.FONT_UI, color=pal["ink"], size=12),
        height=height,
        margin=margin or dict(l=40, r=24, t=48 if title else 24, b=40),
        hoverlabel=dict(
            bgcolor=pal["ink"],
            font=dict(family=theme.FONT_UI, color=pal["bg"], size=12),
            bordercolor=pal["muted"],
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.22,
            xanchor="left",
            x=0,
            font=dict(family=theme.FONT_UI, color=pal["muted"], size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def _style_axes(
    fig: go.Figure,
    pal: dict[str, str],
    *,
    show_grid: bool = True,
    categorical_y: bool = False,
) -> None:
    grid = pal["grid"] if show_grid else "rgba(0,0,0,0)"
    fig.update_xaxes(
        showgrid=show_grid,
        gridcolor=grid,
        zeroline=False,
        showline=True,
        linecolor=pal["axis_line"],
        linewidth=1,
        tickfont=dict(family=theme.FONT_UI, color=pal["muted"], size=11),
    )
    yaxis_kwargs: dict = dict(
        showgrid=show_grid,
        gridcolor=grid,
        zeroline=False,
        showline=not categorical_y,
        linecolor=pal["axis_line"],
        linewidth=1,
        tickfont=dict(family=theme.FONT_UI, color=pal["muted"], size=11),
    )
    if categorical_y:
        yaxis_kwargs["categoryorder"] = "total descending"
    fig.update_yaxes(**yaxis_kwargs)


# --- chart builders ----------------------------------------------------------


def build_pie_violent_vs_nonviolent(
    results: Sequence[dict],
    *,
    dark: bool = False,
) -> go.Figure:
    """Donut chart: violentos vs. no violentos vs. clasificados.

    Basura digital and violencia-común rows count as "Sin violencia"
    (their ``tiene_violencia`` flag is ``false`` because the pre-filter
    short-circuited them).
    """
    counts = Counter(a.get("tiene_violencia") for a in results)
    violent = counts.get("true", 0)
    non_violent = counts.get("false", 0)
    other = len(results) - violent - non_violent

    labels = ["Con violencia", "Sin violencia"]
    values = [violent, non_violent]
    colors = [theme.RELIABILITY_CRITICA, theme.RELIABILITY_OK]
    if other:
        labels.append("Sin clasificar")
        values.append(other)
        colors.append(theme.CHARCOAL_LIGHT)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors, line=dict(color="rgba(0,0,0,0)", width=2)),
                textinfo="percent",
                textposition="outside",
                textfont=dict(family=theme.FONT_DISPLAY, size=14),
                hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
                pull=[0.02, 0, 0],
            )
        ]
    )
    fig.update_traces(sort=False, direction="clockwise")
    fig.update_layout(
        annotations=[
            dict(
                text=f"<b>{sum(values)}</b><br><span style='font-size:11px; "
                f"color:{_palette(dark)['muted']}'>contenidos</span>",
                x=0.5,
                y=0.5,
                font=dict(family=theme.FONT_DISPLAY, size=22, color=_palette(dark)["ink"]),
                showarrow=False,
            )
        ]
    )
    return _apply_common_layout(fig, title="Violentos vs. No violentos", dark=dark)


def _count_categories(results: Sequence[dict]) -> Counter[str]:
    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
    counts: Counter[str] = Counter()
    for a in results:
        if a.get("tiene_violencia") != "true":
            continue
        if a.get("exclusion_label") in _exclusion:
            continue
        labels = a.get("labels") or []
        if labels:
            for lbl in labels:
                cat = lbl.get("categoria") or "ninguna"
                if not cat or cat == "ninguna":
                    continue
                counts[cat] += 1
        else:
            cat = a.get("categoria", "ninguna")
            if cat and cat != "ninguna":
                counts[cat] += 1
    return counts


def _count_subdimensions(results: Sequence[dict], categoria: str | None = None) -> Counter[str]:
    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
    counts: Counter[str] = Counter()
    for a in results:
        if a.get("tiene_violencia") != "true":
            continue
        if a.get("exclusion_label") in _exclusion:
            continue
        labels = a.get("labels") or []
        if labels:
            for lbl in labels:
                cat = lbl.get("categoria") or "ninguna"
                dim = lbl.get("dimension")
                if not cat or cat == "ninguna" or not dim:
                    continue
                if categoria and cat != categoria:
                    continue
                counts[dim] += 1
        else:
            cat = a.get("categoria", "ninguna")
            dim = a.get("dimension")
            if not cat or cat == "ninguna" or not dim:
                continue
            if categoria and cat != categoria:
                continue
            counts[dim] += 1
    return counts


def _bar_figure(
    rows: list[tuple[str, int, str, str]],
    *,
    title: str,
    dark: bool,
    height: int,
    extra_customdata_col: int = 3,
) -> go.Figure:
    """Build the horizontal bar layout shared by category and subdimension views.

    Each ``row`` is ``(label, count, color, secondary_customdata)``. When
    ``extra_customdata_col`` is set, the secondary value is exposed in
    Plotly's ``customdata`` array alongside the count so click handlers
    can recover category codes without re-parsing the label.
    """
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    colors = [r[2] for r in rows]
    extras = [r[extra_customdata_col] for r in rows]

    total = sum(values)
    pcts = [(v / total * 100.0) if total else 0.0 for v in values]

    customdata: list[list[object]] = [[v, e] for v, e in zip(values, extras)]

    fig = go.Figure(
        data=[
            go.Bar(
                x=pcts,
                y=labels,
                orientation="h",
                marker=dict(
                    color=colors,
                    line=dict(color="rgba(0,0,0,0)", width=0),
                ),
                text=[f"<b>{v}</b>  ·  {p:.1f}%" for v, p in zip(values, pcts)],
                textposition="outside",
                textfont=dict(family=theme.FONT_UI, size=11, color=_palette(dark)["ink"]),
                hovertemplate=("<b>%{y}</b><br>%{x:.1f}% (n=%{customdata[0]})<extra></extra>"),
                customdata=customdata,
                cliponaxis=False,
            )
        ]
    )
    pal = _palette(dark)
    _style_axes(fig, pal, categorical_y=True)
    fig.update_xaxes(
        title=dict(
            text="% sobre violencia válida",
            font=dict(family=theme.FONT_UI, size=11, color=pal["muted"]),
        ),
        range=[0, max(pcts) * 1.25 if pcts else 1],
    )
    return _apply_common_layout(fig, title=title, dark=dark, height=height)


def build_bar_categories(
    results: Sequence[dict],
    *,
    dark: bool = False,
    level: str = "categoria",
    categoria_padre: str | None = None,
) -> go.Figure:
    """Horizontal bar chart de categorías o subdimensiones, descendente.

    ``level='categoria'`` (default) produce 6 barras con paleta
    ``CATEGORIA_COLORS``. ``level='subdimension'`` produce hasta 18
    barras con paleta ``SUBDIMENSION_COLORS``, agrupadas por jerarquía
    de categoría padre. Si se pasa ``categoria_padre`` con
    ``level='subdimension'`` se filtran los conteos a esa categoría.
    Excluye basura-digital y violencia-común del denominador (Regla 2
    — Porcentaje Válido).
    """
    if level == "categoria":
        counts = _count_categories(results)
        universo = list(CATEGORIAS_ORDENADAS)
        title = "Distribución por categoría"
        height = 380
    else:
        counts = _count_subdimensions(results, categoria=categoria_padre)
        universo = list(theme.SUBDIMENSIONES_ORDENADAS)
        if categoria_padre:
            title = (
                f"Subdimensiones · {theme.CATEGORIA_LABELS.get(categoria_padre, categoria_padre)}"
            )
            universo = [
                d for d in universo if theme.categoria_de_subdimension(d) == categoria_padre
            ]
        else:
            title = "Distribución por subdimensión"
        height = 360

    def _label_for(code: str) -> str:
        if level == "categoria":
            return theme.CATEGORIA_LABELS.get(code, code)
        return theme.SUBDIMENSION_LABELS.get(code, code)

    def _color_for(code: str) -> str:
        if level == "categoria":
            return theme.CATEGORIA_COLORS.get(code, theme.CHARCOAL_LIGHT)
        return theme.SUBDIMENSION_COLORS.get(code, theme.CHARCOAL_LIGHT)

    rows: list[tuple[str, int, str, str]] = []
    seen: set[str] = set()
    for code in universo:
        n = int(counts.get(code, 0))
        rows.append((_label_for(code), n, _color_for(code), code))
        seen.add(code)
    for code, n in counts.items():
        if code in seen:
            continue
        rows.append((_label_for(code), int(n), _color_for(code), code))
    rows.sort(key=lambda x: -x[1])

    if not rows:
        return _bar_figure(
            [("(sin datos)", 0, theme.CHARCOAL_LIGHT, "")],
            title=title,
            dark=dark,
            height=height,
        )

    return _bar_figure(rows, title=title, dark=dark, height=height)


def build_crosstab_heatmap(
    filas: Sequence[str],
    columnas: Sequence[str],
    frecuencias: Sequence[Sequence[int]],
    *,
    title: str = "Crosstab",
    dark: bool = False,
) -> go.Figure:
    """Heatmap for ``categoria × dimensión`` (Regla 4).

    Cell colors interpolate from cream to plum so that high-frequency
    cells glow without the harshness of a red palette.
    """
    text = [[str(v) for v in fila] for fila in frecuencias]
    fig = go.Figure(
        data=go.Heatmap(
            z=frecuencias,
            x=list(columnas),
            y=list(filas),
            text=text,
            texttemplate="%{text}",
            textfont=dict(family=theme.FONT_UI, size=11),
            colorscale=[
                [0.0, theme.CREAM],
                [0.5, theme.ROSE_SOFT],
                [1.0, theme.PLUM],
            ],
            colorbar=dict(
                title=dict(
                    text="n",
                    font=dict(family=theme.FONT_UI, color=_palette(dark)["muted"], size=11),
                ),
                tickfont=dict(family=theme.FONT_UI, color=_palette(dark)["muted"], size=10),
                thickness=12,
                len=0.85,
            ),
            hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>n = %{z}<extra></extra>",
        )
    )
    pal = _palette(dark)
    _style_axes(fig, pal, show_grid=False)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="top")
    return _apply_common_layout(fig, title=title, dark=dark, height=420)


def build_confusion_matrix_heatmap(
    *,
    vp: int,
    vn: int,
    fp: int,
    fn: int,
    dark: bool = False,
) -> go.Figure:
    """2×2 heatmap for the Regla 6 confusion matrix.

    Rows = Real (ground truth), Columns = Predicho. Diagonal cells
    glow plum (correct), off-diagonal cells glow burgundy (errors).
    """
    matrix = [
        [vp, fn],
        [fp, vn],
    ]
    labels = [["VP", "FN"], ["FP", "VN"]]
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=["Pred: Sí (violencia)", "Pred: No"],
            y=["Real: Sí (violencia)", "Real: No"],
            text=labels,
            texttemplate="<b>%{text}</b><br>n = %{z}",
            textfont=dict(family=theme.FONT_DISPLAY, size=14, color=theme.CREAM),
            colorscale=[
                [0.0, theme.BRASS],
                [0.5, theme.ROSE],
                [1.0, theme.PLUM],
            ],
            colorbar=dict(
                title=dict(text="n", font=dict(family=theme.FONT_UI, size=11)),
                thickness=12,
                len=0.85,
            ),
            hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>n = %{z}<extra></extra>",
            showscale=False,
            zmin=0,
            zmax=max(vp + vn + fp + fn, 1),
        )
    )
    pal = _palette(dark)
    _style_axes(fig, pal, show_grid=False)
    fig.update_yaxes(autorange="reversed")
    return _apply_common_layout(
        fig,
        title="Matriz de confusión",
        dark=dark,
        height=320,
        margin=dict(l=160, r=24, t=48, b=24),
    )


def build_mode_gauge(value_pct: float, *, dark: bool = False) -> go.Figure:
    """Radial gauge for the modal-category share.

    Useful as a visual anchor for Regla 3 — the mode percentage of
    the leading category.
    """
    pal = _palette(dark)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value_pct,
            number=dict(
                suffix="%",
                font=dict(family=theme.FONT_DISPLAY, size=36, color=pal["ink"]),
            ),
            gauge=dict(
                axis=dict(
                    range=[0, 100],
                    tickfont=dict(family=theme.FONT_UI, color=pal["muted"], size=10),
                ),
                bar=dict(color=theme.PLUM, thickness=0.4),
                bgcolor="rgba(0,0,0,0)",
                steps=[
                    dict(range=[0, value_pct], color=theme.ROSE_SOFT),
                    dict(range=[value_pct, 100], color="rgba(0,0,0,0)"),
                ],
            ),
        )
    )
    return _apply_common_layout(fig, dark=dark, height=260, margin=dict(l=20, r=20, t=20, b=20))


__all__ = [
    "build_pie_violent_vs_nonviolent",
    "build_bar_categories",
    "build_crosstab_heatmap",
    "build_confusion_matrix_heatmap",
    "build_mode_gauge",
]
