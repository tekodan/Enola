"""Estadística — Reglas 2, 3 y 4 del documento metodológico.

Página premium con la distribución de frecuencias (4 columnas
exactas), la moda con detección bimodal/multimodal y las
tabulaciones cruzadas (categoría × subdimensión / página / mes)
con porcentajes marginales de columna.
"""

from __future__ import annotations

import logging

from nicegui import ui

from src.report.metrics import render_metrics_report
from src.report.stats import compute_crosstabs, compute_frequency_distribution, compute_mode
from src.storage import get_database
from src.ui.adjusted_report import build_adjusted_analysis
from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.charts import (
    build_bar_categories,
    build_confusion_matrix_heatmap,
    build_crosstab_heatmap,
    build_mode_gauge,
    build_pie_violent_vs_nonviolent,
)
from src.ui.nicegui_app.components.kpi_card import kpi_grid
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold
from src.ui.utils import CATEGORIA_LABELS, filter_by_content_type

logger = logging.getLogger(__name__)


# --- Helpers ---------------------------------------------------------------


def _load_data():
    db = get_database()
    raw = db.get_analysis_results()
    feedback = db.list_feedback()
    analysis = build_adjusted_analysis(raw, feedback)
    posts = db.get_posts(limit=2000)
    pages = db.get_pages(limit=500)
    return analysis, posts, pages, feedback


def _page_lookup(pages, posts) -> dict[str, str]:
    """Build ``{post_id|page_id → page title}`` for crosstab lookups."""
    lookup: dict[str, str] = {}
    for p in pages or []:
        title = p.get("title") or "Sin título"
        for key in ("id", "page_id"):
            if p.get(key):
                lookup[p[key]] = title
    for p in posts or []:
        if p.get("page_id") and p["page_id"] not in lookup:
            lookup[p["page_id"]] = p.get("title") or "Sin título"
    return lookup


# --- Sub-renders ----------------------------------------------------------


def _render_regla2(subset: list[dict]) -> None:
    """Regla 2 — Distribución de frecuencias (4 columnas exactas).

    Se renderizan dos versiones en paralelo: por categoría (regla
    metodológica) y por subdimensión (drill-down). Las dos comparten
    la misma fórmula de Porcentaje Válido y Acumulado.
    """
    section_header(
        "Regla 2",
        "Distribución de frecuencias",
        subtitle=(
            "Porcentaje válido excluye CÓDIGO 99 y violencia común. "
            "Porcentaje acumulado suma de mayor a menor hasta 100%."
        ),
    )

    # --- Por categoría --------------------------------------------------
    ft_cat = compute_frequency_distribution(subset, categoria_labels=CATEGORIA_LABELS)
    ft_sub = compute_frequency_distribution(
        subset,
        level="subdimension",
        subdimension_labels=theme.SUBDIMENSION_LABELS,
    )

    kpi_grid(
        3,
        [
            {
                "label": "Válidos analizados",
                "value": str(ft_cat.total_validos),
                "icon": "fact_check",
                "sub": "Excluye CÓDIGO 99 / VIOLENCIA_COMUN",
            },
            {
                "label": "Excluidos",
                "value": str(ft_cat.n_excluidos),
                "icon": "block",
                "accent": theme.CHARCOAL_LIGHT,
                "sub": "Basura digital + violencia común",
            },
            {
                "label": "Categorías detectadas",
                "value": str(sum(1 for r in ft_cat.rows if r.frecuencia_absoluta > 0)),
                "icon": "category",
                "sub": "De las 6 canónicas VDG_*",
            },
        ],
    )

    with ui.element("div").classes("w-full mt-6"):
        ui.label("Por categoría").classes(
            "text-xs uppercase tracking-widest font-semibold mb-2"
        ).style("color: var(--enola-brass-deep);")
        ui.table(
            columns=[
                {"name": "categoria", "label": "Categoría", "field": "categoria", "align": "left"},
                {
                    "name": "frecuencia",
                    "label": "Frec. Absoluta",
                    "field": "frecuencia",
                    "align": "right",
                },
                {"name": "valido", "label": "% Válido", "field": "valido", "align": "right"},
                {
                    "name": "acumulado",
                    "label": "% Acumulado",
                    "field": "acumulado",
                    "align": "right",
                },
            ],
            rows=[
                {
                    "categoria": r.categoria_label,
                    "frecuencia": r.frecuencia_absoluta,
                    "valido": f"{r.porcentaje_valido:.2f}%",
                    "acumulado": f"{r.porcentaje_acumulado:.2f}%",
                }
                for r in ft_cat.rows
            ],
            row_key="categoria",
        ).classes("w-full")

    # --- Por subdimensión ------------------------------------------------
    with ui.element("div").classes("w-full mt-10"):
        ui.label("Por subdimensión (drill-down)").classes(
            "text-xs uppercase tracking-widest font-semibold mb-2"
        ).style("color: var(--enola-brass-deep);")
        ui.label(
            f"{sum(1 for r in ft_sub.rows if r.frecuencia_absoluta > 0)} de las "
            f"{len(theme.SUBDIMENSIONES_ORDENADAS)} subdimensiones canónicas "
            "presentes en la muestra."
        ).classes("text-xs mb-3").style("color: var(--enola-charcoal-light);")
        ui.table(
            columns=[
                {
                    "name": "categoria",
                    "label": "Subdimensión",
                    "field": "categoria",
                    "align": "left",
                },
                {
                    "name": "frecuencia",
                    "label": "Frec. Absoluta",
                    "field": "frecuencia",
                    "align": "right",
                },
                {"name": "valido", "label": "% Válido", "field": "valido", "align": "right"},
                {
                    "name": "acumulado",
                    "label": "% Acumulado",
                    "field": "acumulado",
                    "align": "right",
                },
            ],
            rows=[
                {
                    "categoria": r.categoria_label,
                    "frecuencia": r.frecuencia_absoluta,
                    "valido": f"{r.porcentaje_valido:.2f}%",
                    "acumulado": f"{r.porcentaje_acumulado:.2f}%",
                }
                for r in ft_sub.rows
            ],
            row_key="categoria",
        ).classes("w-full")


def _render_regla3(subset: list[dict]) -> None:
    """Regla 3 — Moda con detección bimodal/multimodal.

    Se renderizan dos versiones en paralelo: por categoría (regla
    metodológica) y por subdimensión (drill-down). Cada bloque lleva
    su gauge + tabla + texto descriptivo del Paso 3.4.
    """
    section_header(
        "Regla 3",
        "Moda — medida de tendencia central",
        subtitle=(
            "Para variables nominales (sin orden) la única medida "
            "válida es la moda. Detección bimodal/multimodal cuando "
            "dos o más categorías comparten la frecuencia máxima."
        ),
    )

    mode_cat = compute_mode(subset, categoria_labels=CATEGORIA_LABELS)
    mode_sub = compute_mode(
        subset,
        level="subdimension",
        subdimension_labels=theme.SUBDIMENSION_LABELS,
    )

    # --- Por categoría --------------------------------------------------
    ui.label("Por categoría").classes("text-xs uppercase tracking-widest font-semibold mb-3").style(
        "color: var(--enola-brass-deep);"
    )

    if not mode_cat.modas:
        ui.label("Sin etiquetas de violencia detectadas — no se puede calcular la moda.").classes(
            "text-base"
        )
    else:
        _render_mode_block(mode_cat, CATEGORIA_LABELS, "categoría")

    # --- Por subdimensión ------------------------------------------------
    with ui.element("div").classes("w-full mt-10"):
        ui.label("Por subdimensión (drill-down)").classes(
            "text-xs uppercase tracking-widest font-semibold mb-3"
        ).style("color: var(--enola-brass-deep);")
        if not mode_sub.modas:
            ui.label("Sin subdimensiones detectadas — no se puede calcular la moda.").classes(
                "text-base"
            )
        else:
            _render_mode_block(mode_sub, theme.SUBDIMENSION_LABELS, "subdimensión")


def _plural_es(noun: str) -> str:
    """Devuelve el plural canónico del sustantivo usado en los labels.

    Evita la concatenación naïve ``noun + "s"`` que rompe "subdimensión" →
    "subdimensións". Para sustantivos desconocidos cae al comportamiento
    anterior (apenas añadir ``"s"``) para no introducir regresiones.
    """
    plurales = {
        "categoría": "Categorías",
        "subdimensión": "Subdimensiones",
    }
    return plurales.get(noun, noun.capitalize() + "s")


def _render_mode_block(mode, label_map: dict[str, str], noun: str) -> None:
    """Render gauge + tabla + texto del Paso 3.4 para un ModeResult."""
    leading_pct = max(mode.frecuencias.values()) / max(sum(mode.frecuencias.values()), 1) * 100.0
    plural = _plural_es(noun)

    with ui.element("div").classes("w-full grid gap-6").style("grid-template-columns: 1fr 2fr;"):
        with ui.element("div"):
            ui.plotly(build_mode_gauge(leading_pct)).classes("w-full")

        with ui.column().classes("gap-4"):
            if mode.es_multimodal:
                cualif = "bimodal" if len(mode.modas) == 2 else "multimodal"
                ui.label(f"⚠ Distribución {cualif} — {len(mode.modas)} {plural} empatan.").classes(
                    "text-base font-semibold"
                ).style(f"color: {theme.BRASS_DEEP};")
            nombres = [label_map.get(m, m) for m in mode.modas]
            ui.label(f"**{plural} modales:** " + ", ".join(f"*{n}*" for n in nombres)).classes(
                "text-sm"
            ).style("color: var(--enola-charcoal);")

            ui.table(
                columns=[
                    {"name": "cat", "label": noun.capitalize(), "field": "cat", "align": "left"},
                    {"name": "n", "label": "Frecuencia", "field": "n", "align": "right"},
                ],
                rows=[
                    {"cat": label_map.get(c, c), "n": n}
                    for c, n in sorted(mode.frecuencias.items(), key=lambda x: -x[1])
                ],
                row_key="cat",
            ).classes("w-full")

    with ui.element("div").style(
        "margin-top: 1.5rem; padding: 1.25rem 1.5rem; "
        "border-radius: 0.875rem; "
        "background: rgba(191, 161, 129, 0.10); "
        "border-left: 3px solid var(--enola-brass); "
        "font-family: var(--enola-font-display); "
        "font-style: italic; font-size: 1.02rem; "
        "color: var(--enola-charcoal); line-height: 1.55;"
    ):
        ui.label(mode.texto_descriptivo)


def _render_regla4(
    analysis: list[dict],
    posts: list[dict],
    pages: list[dict],
) -> None:
    """Regla 4 — Tabulaciones cruzadas."""
    section_header(
        "Regla 4",
        "Análisis bivariado — tablas de contingencia",
        subtitle=(
            "Cruce de la variable dependiente (categoría) contra "
            "variables independientes (subdimensión, página, mes). "
            "Porcentajes marginales de columna."
        ),
    )

    lookup = _page_lookup(pages, posts)

    with ui.tabs().classes("w-full") as tabs:
        tab_subdim = ui.tab("Categoría × Subdimensión")
        tab_pagina = ui.tab("Categoría × Página")
        tab_fecha = ui.tab("Categoría × Mes")
    with ui.tab_panels(tabs).classes("w-full"):
        with ui.tab_panel(tab_subdim):
            _render_crosstab_panel(
                analysis,
                dimension="subdimension",
                title="Categoría × Subdimensión",
            )
        with ui.tab_panel(tab_pagina):
            _render_crosstab_panel(
                analysis,
                dimension="pagina",
                title="Categoría × Página",
                posts=posts,
                page_lookup=lookup,
            )
        with ui.tab_panel(tab_fecha):
            _render_crosstab_panel(
                analysis,
                dimension="fecha",
                title="Categoría × Mes",
                posts=posts,
            )


def _render_crosstab_panel(
    analysis: list[dict],
    *,
    dimension: str,
    title: str,
    posts: list[dict] | None = None,
    page_lookup: dict[str, str] | None = None,
) -> None:
    """Render a single crosstab (frequencies + percentages + heatmap)."""
    try:
        ct = compute_crosstabs(
            analysis,
            dimension=dimension,
            posts=posts,
            page_lookup=page_lookup,
            categoria_labels=CATEGORIA_LABELS,
        )
    except ValueError:
        ui.label(f"Subdimensión desconocida: {dimension}").classes("text-base")
        return

    if not ct.filas:
        ui.info("Sin datos válidos para este cruce.")
        return

    with ui.element("div").classes("w-full grid gap-6").style("grid-template-columns: 1fr 1fr;"):
        # Frequencies table
        with ui.element("div"):
            ui.label("Frecuencias observadas (n)").classes(
                "text-xs uppercase tracking-widest font-semibold mb-2"
            ).style("color: var(--enola-brass-deep);")
            ui.table(
                columns=[{"name": "row", "label": "Categoría", "field": "row", "align": "left"}]
                + [
                    {"name": col, "label": col, "field": col, "align": "right"}
                    for col in ct.columnas
                ],
                rows=[
                    {
                        "row": f,
                        **{ct.columnas[j]: ct.frecuencias[i][j] for j in range(len(ct.columnas))},
                    }
                    for i, f in enumerate(ct.filas)
                ],
                row_key="row",
            ).classes("w-full")

        # Percentages table
        with ui.element("div"):
            ui.label("Porcentajes marginales de columna (%)").classes(
                "text-xs uppercase tracking-widest font-semibold mb-2"
            ).style("color: var(--enola-brass-deep);")
            ui.table(
                columns=[{"name": "row", "label": "Categoría", "field": "row", "align": "left"}]
                + [
                    {"name": col, "label": col, "field": col, "align": "right"}
                    for col in ct.columnas
                ],
                rows=[
                    {
                        "row": f,
                        **{
                            ct.columnas[j]: f"{ct.porcentajes_marginales_columna[i][j]:.1f}%"
                            for j in range(len(ct.columnas))
                        },
                    }
                    for i, f in enumerate(ct.filas)
                ],
                row_key="row",
            ).classes("w-full")

    # Heatmap
    with ui.element("div").classes("w-full mt-6"):
        ui.plotly(
            build_crosstab_heatmap(ct.filas, ct.columnas, ct.frecuencias, title=title)
        ).classes("w-full")

    # Alerta de patrón (Paso 4.4)
    if ct.alerta_patron:
        with ui.element("div").style(
            "margin-top: 1.5rem; padding: 1rem 1.25rem; "
            "border-radius: 0.875rem; "
            "background: rgba(192, 132, 151, 0.10); "
            "border-left: 3px solid var(--enola-rose); "
            "color: var(--enola-charcoal);"
        ):
            ui.label("🎯 Patrón relacional detectado").classes(
                "text-xs uppercase tracking-widest font-semibold mb-1"
            ).style("color: var(--enola-plum);")
            ui.label(ct.alerta_patron).classes("text-sm leading-snug")


# --- Charts row (overview) ------------------------------------------------


def _render_charts_overview(subset: list[dict]) -> None:
    """The pie + bar chart overview (Regla 5.2 + 5.3).

    El bar chart muestra las 6 categorías canónicas. Al hacer click en
    una barra, debajo se renderiza la drill-down con sus 3
    subdimensiones (Regla 5 — drill-down multi-granularidad).
    """
    from src.analyzer.category_mapping import SUBDIMENSIONES_POR_CATEGORIA

    section_header(
        "Regla 5",
        "Visualización de resultados",
        subtitle=(
            "Gráfica circular dicotómica (violentos vs no violentos) y "
            "barras jerarquizadas en orden descendente. Hacé click en "
            "una categoría para ver el drill-down de sus subdimensiones."
        ),
    )

    bar_container_row = (
        ui.element("div").classes("w-full grid gap-4").style("grid-template-columns: 1fr 1fr;")
    )
    drilldown_col = ui.column().classes("w-full gap-3 mt-4")

    with bar_container_row:
        with ui.element("div"):
            ui.plotly(build_pie_violent_vs_nonviolent(subset)).classes("w-full")
        with ui.element("div"):
            with ui.column().classes("w-full gap-3"):
                ui.label("Distribución por categoría").classes(
                    "text-xs uppercase tracking-widest font-semibold"
                ).style("color: var(--enola-brass-deep);")

                bar_plot = ui.plotly(build_bar_categories(subset, level="categoria")).classes(
                    "w-full"
                )

    def _render_drilldown(codigo_cat: str) -> None:
        drilldown_col.clear()
        with drilldown_col:
            cat_label = theme.CATEGORIA_LABELS.get(codigo_cat, codigo_cat)
            cat_color = theme.CATEGORIA_COLORS.get(codigo_cat, theme.CHARCOAL_LIGHT)
            dims = SUBDIMENSIONES_POR_CATEGORIA.get(codigo_cat, [])
            n_categoria = sum(_count_for_categoria(subset, codigo_cat) for _ in [None])
            with (
                ui.element("div")
                .classes("w-full")
                .style(
                    "border: 1px solid rgba(191, 161, 129, 0.30); "
                    "border-left: 4px solid " + cat_color + "; "
                    "border-radius: 0.75rem; "
                    "padding: 1rem 1.25rem; "
                    "background: rgba(250, 246, 240, 0.55);"
                )
            ):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(f"🔍 Drill-down · {cat_label}").classes(
                        "text-base font-semibold enola-display"
                    )
                    ui.label(
                        f"{n_categoria} etiqueta{'s' if n_categoria != 1 else ''} · "
                        f"{len(dims)} subdimensiones canónicas"
                    ).classes("text-xs").style("color: var(--enola-charcoal-light);")
                    ui.button(
                        "↩ Volver a categorías",
                        on_click=lambda: _render_drilldown_unset(),
                    ).props("flat dense").style("color: var(--enola-charcoal-light);")

                if n_categoria == 0:
                    ui.label(
                        "Esta categoría no tiene etiquetas de violencia en la muestra actual."
                    ).classes("text-sm mt-2").style(
                        "color: var(--enola-charcoal-light); font-style: italic;"
                    )
                    return

                ui.plotly(
                    build_bar_categories(
                        subset,
                        level="subdimension",
                        categoria_padre=codigo_cat,
                    )
                ).classes("w-full mt-3")

    def _render_drilldown_unset() -> None:
        drilldown_col.clear()

    def _count_for_categoria(rows: list[dict], codigo_cat: str) -> int:
        from collections import Counter

        _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
        c: Counter[str] = Counter()
        for a in rows:
            if a.get("tiene_violencia") != "true":
                continue
            if a.get("exclusion_label") in _exclusion:
                continue
            labels = a.get("labels") or []
            if labels:
                for lbl in labels:
                    cat = lbl.get("categoria") or "ninguna"
                    if cat == codigo_cat:
                        c[cat] += 1
            else:
                if a.get("categoria") == codigo_cat:
                    c[codigo_cat] += 1
        return c.get(codigo_cat, 0)

    def _on_plotly_click(e: object) -> None:
        try:
            args = getattr(e, "args", None) or {}
            points = args.get("points") or []
        except Exception:
            logger.exception("No se pudo leer el evento plotly_click")
            return
        if not points:
            return
        customdata = points[0].get("customdata") or []
        if not customdata or len(customdata) < 2:
            return
        codigo_cat = str(customdata[1])
        if not codigo_cat or codigo_cat not in theme.CATEGORIA_LABELS:
            return
        _render_drilldown(codigo_cat)

    bar_plot.on("plotly_click", _on_plotly_click)


# --- Regla 6 — Métricas de la IA ------------------------------------------


def _render_regla6(analysis: list[dict], feedback: list[dict]) -> None:
    """Regla 6 — Matriz de confusión + fórmulas de rendimiento.

    Documenta las definiciones operativas de los 4 valores de la matriz
    y las tres fórmulas de evaluación (Sensibilidad, Precisión, F1) sobre
    la verdad terreno provista por el revisor humano en
    ``analysis_feedback``. Confirma que la IA funciona contrastando sus
    predicciones con las anotaciones manuales.
    """
    section_header(
        "Regla 6",
        "Métricas de la IA — matriz de confusión y rendimiento",
        subtitle=(
            "Evaluación del clasificador automático contrastado con el "
            "revisor humano. Muestra que la IA funciona correctamente y "
            "cuantifica su margen de error."
        ),
    )

    if not feedback:
        with ui.element("div").style(
            "padding: 1.5rem 1.75rem; border-radius: 0.875rem; "
            "background: rgba(191, 161, 129, 0.08); "
            "border-left: 3px solid var(--enola-brass); "
            "color: var(--enola-charcoal);"
        ):
            ui.label("Sin feedback humano todavía").classes("text-base font-semibold mb-2").style(
                "color: var(--enola-plum);"
            )
            ui.label(
                "Marcá análisis como de acuerdo / corregidos en la "
                "pestaña **Validación** para alimentar la matriz de "
                "confusión y las métricas de rendimiento."
            ).classes("text-sm")
        return

    lookup: dict = {a.get("id"): a for a in analysis if a.get("id") is not None}
    report = render_metrics_report(feedback, analysis_lookup=lookup)
    cm_dict = report["confusion_matrix"]
    metrics = report["metrics"]

    # --- Definiciones de los 4 valores de la matriz ---------------------
    with ui.element("div").style(
        "padding: 1.5rem 1.75rem; border-radius: 0.875rem; "
        "background: linear-gradient(135deg, rgba(107, 78, 113, 0.05), "
        "rgba(191, 161, 129, 0.08)); "
        "border-left: 3px solid var(--enola-plum); "
        "color: var(--enola-charcoal); line-height: 1.55;"
    ):
        ui.label("Matriz de confusión — definiciones").classes(
            "text-xs uppercase tracking-widest font-semibold mb-3"
        ).style("color: var(--enola-brass-deep);")

        ui.html(
            "<p style='margin: 0 0 0.6rem 0;'><b>Verdaderos Positivos (VP).</b> "
            "El caso real era <i>violencia</i> y la máquina lo aceptó como violencia.</p>"
            "<p style='margin: 0 0 0.6rem 0;'><b>Verdaderos Negativos (VN).</b> "
            "El caso real era <i>no violencia</i> y la máquina lo aceptó como no violencia.</p>"
            "<p style='margin: 0 0 0.6rem 0;'><b>Falsos Positivos (FP).</b> "
            "El caso real era <i>no violencia</i> pero la máquina se equivocó "
            "diciendo que era violencia.</p>"
            "<p style='margin: 0;'><b>Falsos Negativos (FN).</b> "
            "El caso real era <i>violencia</i> pero la máquina se equivocó "
            "diciendo que era no violencia.</p>"
        ).classes("text-sm")

    # --- Fórmulas de rendimiento ----------------------------------------
    with ui.element("div").style(
        "padding: 1.5rem 1.75rem; border-radius: 0.875rem; "
        "background: rgba(191, 161, 129, 0.06); "
        "border-left: 3px solid var(--enola-brass); "
        "color: var(--enola-charcoal); line-height: 1.55;"
    ):
        ui.label("Fórmulas de rendimiento").classes(
            "text-xs uppercase tracking-widest font-semibold mb-3"
        ).style("color: var(--enola-brass-deep);")

        ui.html(
            "<p style='margin: 0 0 0.6rem 0;'><b>1. Sensibilidad (Recall).</b> "
            "Mide la proporción de casos positivos correctamente identificados "
            "por la máquina.</p>"
            "<p style='margin: 0 0 0.6rem 0.4rem; font-family: monospace;'>"
            "Sensibilidad = VP / (VP + FN)</p>"
            "<p style='margin: 0 0 0.6rem 0;'><b>2. Precisión.</b> Mide el "
            "número de elementos identificados correctamente sobre el total "
            "de clasificaciones positivas emitidas por la máquina.</p>"
            "<p style='margin: 0 0 0.6rem 0.4rem; font-family: monospace;'>"
            "Precisión = VP / (VP + FP)</p>"
            "<p style='margin: 0 0 0.6rem 0;'><b>3. F1-Score.</b> Medida "
            "armónica que unifica precisión y sensibilidad en un solo valor "
            "para evaluar la exactitud global y el margen de error.</p>"
            "<p style='margin: 0 0 0 0.4rem; font-family: monospace;'>"
            "F1 = 2 · (Precisión · Sensibilidad) / (Precisión + Sensibilidad)</p>"
        ).classes("text-sm")

    # --- Valores calculados ---------------------------------------------
    kpi_grid(
        4,
        [
            {
                "label": "Verdaderos Positivos",
                "value": str(cm_dict["VP"]),
                "icon": "check_circle",
                "accent": theme.RELIABILITY_OK,
                "sub": "Real=violencia, IA=violencia",
            },
            {
                "label": "Verdaderos Negativos",
                "value": str(cm_dict["VN"]),
                "icon": "check_circle_outline",
                "accent": theme.RELIABILITY_OK,
                "sub": "Real=no violencia, IA=no violencia",
            },
            {
                "label": "Falsos Positivos",
                "value": str(cm_dict["FP"]),
                "icon": "error",
                "accent": theme.RELIABILITY_CRITICA,
                "sub": "Real=no violencia, IA=violencia",
            },
            {
                "label": "Falsos Negativos",
                "value": str(cm_dict["FN"]),
                "icon": "warning",
                "accent": theme.RELIABILITY_PREVENTIVA,
                "sub": "Real=violencia, IA=no violencia",
            },
        ],
    )

    with (
        ui.element("div").classes("w-full mt-6 grid gap-6").style("grid-template-columns: 1fr 1fr;")
    ):
        with ui.element("div"):
            ui.label("Matriz de confusión (heatmap)").classes(
                "text-xs uppercase tracking-widest font-semibold mb-2"
            ).style("color: var(--enola-brass-deep);")
            ui.plotly(
                build_confusion_matrix_heatmap(
                    vp=cm_dict["VP"],
                    vn=cm_dict["VN"],
                    fp=cm_dict["FP"],
                    fn=cm_dict["FN"],
                )
            ).classes("w-full")

        with ui.element("div"):
            ui.label("Métricas de rendimiento").classes(
                "text-xs uppercase tracking-widest font-semibold mb-2"
            ).style("color: var(--enola-brass-deep);")
            kpi_grid(
                1,
                [
                    {
                        "label": "Precisión  =  VP / (VP + FP)",
                        "value": f"{metrics['Precisión'] * 100:.1f}%",
                        "icon": "target",
                        "accent": theme.PLUM,
                        "sub": "De lo que la IA marcó como violencia, cuánto era real",
                    },
                    {
                        "label": "Sensibilidad (Recall)  =  VP / (VP + FN)",
                        "value": f"{metrics['Sensibilidad (Recall)'] * 100:.1f}%",
                        "icon": "radar",
                        "accent": theme.ROSE,
                        "sub": "De la violencia real, cuánto detectó la IA",
                    },
                    {
                        "label": "F1-Score  =  2·P·S / (P + S)",
                        "value": f"{metrics['F1-Score'] * 100:.1f}%",
                        "icon": "balance",
                        "accent": theme.BRASS,
                        "sub": "Exactitud global de la IA",
                    },
                    {
                        "label": "Soporte (n)",
                        "value": str(metrics["Soporte"]),
                        "icon": "inventory_2",
                        "sub": "Casos evaluados",
                    },
                ],
            )


# --- Page entry ----------------------------------------------------------


@ui.page("/estadistica")
def page_estadistica() -> None:
    page_scaffold(
        "Estadística descriptiva",
        subtitle="Reglas 2, 3, 4 y 6 del marco metodológico",
        current_path="/estadistica",
        body=_render_body,
    )


def _render_body() -> None:
    try:
        analysis, posts, pages, feedback = _load_data()
    except Exception as exc:
        logger.exception("Failed to load data: %s", exc)
        ui.label("No se pudo cargar la base de datos.").classes("text-base")
        return

    # Default to "all" content type for the headline charts
    subset = filter_by_content_type(analysis, "all")
    if not subset:
        subset = analysis

    with ui.column().classes("w-full gap-8"):
        _render_charts_overview(subset)
        _render_regla2(subset)
        _render_regla3(subset)
        _render_regla4(analysis, posts, pages)
        _render_regla6(analysis, feedback)
