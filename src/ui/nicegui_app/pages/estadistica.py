"""Estadística — Reglas 2, 3 y 4 del documento metodológico.

Página premium con la distribución de frecuencias (4 columnas
exactas), la moda con detección bimodal/multimodal y las
tabulaciones cruzadas (categoría × subdimensión / página / mes)
con porcentajes marginales de columna.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime

from nicegui import ui

from src.report.metrics import render_metrics_report
from src.report.reliability import ReliabilityReport, calcular_valores_perdidos
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
from src.ui.nicegui_app.pages.inicio import render_regla1
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


# --- CSV Export ------------------------------------------------------------


def _build_stats_csv(
    analysis: list[dict],
    posts: list[dict],
    pages: list[dict],
    feedback: list[dict],
) -> bytes:
    """Genera un CSV con todas las reglas estatísticas."""
    output = io.StringIO()
    writer = csv.writer(output)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    writer.writerow([f"ESTADÍSTICAS — Generado: {now}"])
    writer.writerow([])

    lookup = _page_lookup(pages, posts)

    # --- Regla 1: Reporte de fiabilidad --------------------------------
    reliability = calcular_valores_perdidos(analysis)
    writer.writerow(["--- REGLA 1: REPORTE DE FIABILIDAD ---"])
    writer.writerow([])
    writer.writerow(["Total de análisis", reliability.total])
    writer.writerow(["% Basura digital (CÓDIGO 99)", reliability.pct_basura])
    writer.writerow(["% Violencia común", reliability.pct_violencia_comun])
    writer.writerow(["Nivel de alerta", reliability.nivel])
    writer.writerow(["Mensaje", reliability.mensaje])
    writer.writerow([])
    writer.writerow(["Detalle de códigos de basura digital"])
    writer.writerow(["Código", "Cantidad"])
    for codigo, cant in sorted(reliability.detalle_basura_codigos.items(), key=lambda x: -x[1]):
        writer.writerow([codigo, cant])
    writer.writerow([])

    # --- Regla 2: Frecuencia por categoría -------------------------------
    writer.writerow(["--- REGLA 2: DISTRIBUCIÓN DE FRECUENCIAS ---"])
    writer.writerow([])

    for level, level_label in [("categoria", "Categoría"), ("subdimension", "Subdimensión")]:
        if level == "categoria":
            ft = compute_frequency_distribution(analysis, categoria_labels=CATEGORIA_LABELS)
        else:
            ft = compute_frequency_distribution(
                analysis,
                level="subdimension",
                subdimension_labels=theme.SUBDIMENSION_LABELS,
            )

        writer.writerow([f"[Por {level_label}]"])
        writer.writerow(["Código", level_label, "Frecuencia Absoluta", "% Válido", "% Acumulado"])
        for r in ft.rows:
            writer.writerow(
                [
                    r.categoria,
                    r.categoria_label,
                    r.frecuencia_absoluta,
                    round(r.porcentaje_valido, 2),
                    round(r.porcentaje_acumulado, 2),
                ]
            )
        writer.writerow([])
        writer.writerow([f"Total válidos: {ft.total_validos}"])
        writer.writerow([f"Excluidos (basura digital + violencia común): {ft.n_excluidos}"])
        writer.writerow([])

    # --- Regla 3: Moda -----------------------------------------------------
    writer.writerow(["--- REGLA 3: MODA ---"])
    writer.writerow([])

    for level, level_label in [("categoria", "Categoría"), ("subdimension", "Subdimensión")]:
        if level == "categoria":
            mode = compute_mode(analysis, categoria_labels=CATEGORIA_LABELS)
            label_map = CATEGORIA_LABELS
        else:
            mode = compute_mode(
                analysis, level="subdimension", subdimension_labels=theme.SUBDIMENSION_LABELS
            )
            label_map = theme.SUBDIMENSION_LABELS

        writer.writerow([f"[Por {level_label}]"])
        if not mode.modas:
            writer.writerow(["Sin etiquetas de violencia detectadas"])
        else:
            writer.writerow(
                [f"Categoría(s) modal(es): {', '.join(label_map.get(m, m) for m in mode.modas)}"]
            )
            writer.writerow([f"Bimodal/Multimodal: {'Sí' if mode.es_multimodal else 'No'}"])
            writer.writerow([])
            writer.writerow([level_label.capitalize(), "Frecuencia", "Es Modal"])
            for cat, freq in sorted(mode.frecuencias.items(), key=lambda x: -x[1]):
                writer.writerow(
                    [label_map.get(cat, cat), freq, "Sí" if cat in mode.modas else "No"]
                )
            writer.writerow([])
            writer.writerow(["Texto descriptivo:"])
            writer.writerow([mode.texto_descriptivo])
        writer.writerow([])

    # --- Regla 5: Drill-down por categoría (todas las subdimensiones) --
    writer.writerow(["--- REGLA 5: DRILL-DOWN POR CATEGORÍA ---"])
    writer.writerow([])
    writer.writerow(
        [
            "Categoría",
            "Código Categoría",
            "Subdimensión",
            "Código Subdimensión",
            "Frecuencia",
        ]
    )

    from collections import Counter

    from src.analyzer.category_mapping import SUBDIMENSIONES_POR_CATEGORIA as SUFDIMS_POR_CAT

    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
    dim_counts: Counter[str] = Counter()
    for a in analysis:
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
                dim_counts[dim] += 1
        else:
            cat = a.get("categoria", "ninguna")
            dim = a.get("dimension")
            if not cat or cat == "ninguna" or not dim:
                continue
            dim_counts[dim] += 1

    for cat_code in theme.CATEGORIA_LABELS.keys():
        cat_label = theme.CATEGORIA_LABELS[cat_code]
        cat_dims = SUFDIMS_POR_CAT.get(cat_code, [])
        for dim_code in cat_dims:
            dim_label = theme.SUBDIMENSION_LABELS.get(dim_code, dim_code)
            freq = dim_counts.get(dim_code, 0)
            writer.writerow([cat_label, cat_code, dim_label, dim_code, freq])
        if not cat_dims:
            writer.writerow([cat_label, cat_code, "(sin subdimensiones)", "", 0])

    writer.writerow([])

    # --- Regla 4: Análisis Bivariado --------------------------------------
    writer.writerow(["--- REGLA 4: ANÁLISIS BIVARIADO ---"])
    writer.writerow([])

    for dimension, dim_label in [
        ("subdimension", "Categoría × Subdimensión"),
        ("pagina", "Categoría × Página"),
        ("fecha", "Categoría × Mes"),
    ]:
        ct_kwargs: dict = {"dimension": dimension, "categoria_labels": CATEGORIA_LABELS}
        if dimension == "pagina":
            ct_kwargs["posts"] = posts
            ct_kwargs["page_lookup"] = lookup
        elif dimension == "fecha":
            ct_kwargs["posts"] = posts

        try:
            ct = compute_crosstabs(analysis, **ct_kwargs)
        except ValueError:
            writer.writerow([f"{dim_label}: Sin datos válidos"])
            writer.writerow([])
            continue

        if not ct.filas:
            writer.writerow([f"{dim_label}: Sin datos válidos"])
            writer.writerow([])
            continue

        writer.writerow([f"[{dim_label}]"])
        writer.writerow([])
        writer.writerow(["-- Frecuencias observadas (n) --"])
        writer.writerow(["Categoría"] + list(ct.columnas))
        for i, fila in enumerate(ct.filas):
            writer.writerow([fila] + ct.frecuencias[i])

        writer.writerow([])
        writer.writerow(["-- Porcentajes marginales de columna (%) --"])
        writer.writerow(["Categoría"] + list(ct.columnas))
        for i, fila in enumerate(ct.filas):
            row_pcts = [f"{p:.1f}%" for p in ct.porcentajes_marginales_columna[i]]
            writer.writerow([fila] + row_pcts)

        if ct.alerta_patron:
            writer.writerow([])
            writer.writerow([f"Patrón detectado: {ct.alerta_patron}"])

        writer.writerow([])

    # --- Regla 6: Métricas IA --------------------------------------------
    writer.writerow(["--- REGLA 6: MÉTRICAS DE LA IA ---"])
    writer.writerow([])

    if not feedback:
        writer.writerow(["Sin feedback humano para calcular métricas"])
    else:
        analysis_lookup = {a.get("id"): a for a in analysis if a.get("id") is not None}
        report = render_metrics_report(feedback, analysis_lookup=analysis_lookup)
        cm = report["confusion_matrix"]
        metrics = report["metrics"]

        writer.writerow(["Matriz de confusión"])
        writer.writerow(["", "Pred: Violencia", "Pred: No violencia"])
        writer.writerow(["Real: Violencia", cm["VP"], cm["FN"]])
        writer.writerow(["Real: No violencia", cm["FP"], cm["VN"]])
        writer.writerow([])
        writer.writerow(["Métricas de rendimiento"])
        writer.writerow(["Precisión", f"{metrics['Precisión'] * 100:.1f}%"])
        writer.writerow(["Sensibilidad (Recall)", f"{metrics['Sensibilidad (Recall)'] * 100:.1f}%"])
        writer.writerow(["F1-Score", f"{metrics['F1-Score'] * 100:.1f}%"])
        writer.writerow(["Soporte (n)", metrics["Soporte"]])

    return output.getvalue().encode("utf-8")


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
            "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
        ).style("display: inline-flex;")
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
            "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
        ).style("display: inline-flex;")
        ui.label(
            f"{sum(1 for r in ft_sub.rows if r.frecuencia_absoluta > 0)} de las "
            f"{len(theme.SUBDIMENSIONES_ORDENADAS)} subdimensiones canónicas "
            "presentes en la muestra."
        ).classes("text-xs mb-3").style(
            "color: var(--enola-charcoal-light); letter-spacing: 0.02em;"
        )
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
                with ui.element("div").style(
                    "padding: 0.75rem 1rem; border-radius: 0.625rem; "
                    "background: rgba(191, 161, 129, 0.12); "
                    "border-left: 3px solid var(--enola-brass); "
                    "display: flex; align-items: center; gap: 0.6rem;"
                ):
                    ui.icon("insights", size="18px").style(f"color: {theme.BRASS_DEEP};")
                    ui.label(
                        f"Distribución {cualif} — {len(mode.modas)} {plural} empatan."
                    ).classes("text-sm font-semibold").style(
                        f"color: {theme.BRASS_DEEP}; letter-spacing: 0.005em;"
                    )
            nombres = [label_map.get(m, m) for m in mode.modas]
            ui.html(
                f"<b>{plural} modales:</b> " + ", ".join(f"<i>{n}</i>" for n in nombres)
            ).classes("text-sm").style("color: var(--enola-charcoal);")

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

    with ui.element("div").classes("enola-quote mt-6"):
        ui.label(mode.texto_descriptivo)
        ui.html(
            "— <span style='font-style: normal;'>Lectura descriptiva · Paso 3.4</span>",
            sanitize=False,
        ).style(
            "color: var(--enola-charcoal-light); margin-top: 0.85rem; "
            "font-family: var(--enola-font-ui); font-size: 0.75rem; "
            "letter-spacing: 0.12em; text-transform: uppercase; "
            "font-weight: 600;"
        )


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
        ui.notify("Sin datos válidos para este cruce.", type="info")
        return

    n_cols = len(ct.columnas)
    use_horizontal_layout = n_cols <= 8

    if use_horizontal_layout:
        table_container = ui.element("div").classes("w-full grid gap-6")
        table_container.style("grid-template-columns: 1fr 1fr;")
    else:
        table_container = ui.column().classes("w-full gap-6")

    with table_container:
        with ui.element("div").style("overflow-x: auto;"):
            ui.label("Frecuencias observadas (n)").classes(
                "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
            ).style("display: inline-flex;")
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

        with ui.element("div").style("overflow-x: auto;"):
            ui.label("Porcentajes marginales de columna (%)").classes(
                "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
            ).style("display: inline-flex;")
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
            "margin-top: 1.5rem; padding: 1.1rem 1.35rem; "
            "border-radius: 0.875rem; "
            "background: linear-gradient(135deg, rgba(192, 132, 151, 0.10), "
            "rgba(107, 78, 113, 0.06)); "
            "border-left: 3px solid var(--enola-rose); "
            "color: var(--enola-charcoal); "
            "display: flex; align-items: flex-start; gap: 0.85rem;"
        ):
            ui.icon("target", size="20px").style(
                f"color: {theme.PLUM}; flex-shrink: 0; margin-top: 1px;"
            )
            with ui.column().classes("gap-1"):
                ui.label("🎯 Patrón relacional detectado").classes(
                    "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow"
                ).style("display: inline-flex; margin-bottom: 0.15rem;")
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
            "Gráfica circular tricotómica (violentos · no violentos · "
            "basura digital CÓDIGO 99) y barras jerarquizadas en orden "
            "descendente. Hacé click en una categoría para ver el "
            "drill-down de sus subdimensiones."
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
                    "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow"
                ).style("display: inline-flex;")

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
                .classes("w-full enola-panel")
                .style("border-left: 4px solid " + cat_color + "; padding: 1.25rem 1.5rem;")
            ):
                with ui.row().classes("w-full items-center justify-between gap-3"):
                    with ui.column().classes("gap-0"):
                        ui.label("Drill-down").classes(
                            "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow"
                        ).style("display: inline-flex; margin-bottom: 0.2rem;")
                        ui.label(cat_label).classes("text-xl font-semibold enola-display").style(
                            f"color: {theme.PLUM}; letter-spacing: -0.015em;"
                        )
                    with ui.column().classes("gap-1 items-end"):
                        ui.label(
                            f"{n_categoria} etiqueta{'s' if n_categoria != 1 else ''} · "
                            f"{len(dims)} subdimensiones canónicas"
                        ).classes("text-xs").style(
                            "color: var(--enola-charcoal-light); letter-spacing: 0.02em;"
                        )
                        ui.button(
                            "↩ Volver a categorías",
                            icon="arrow_back",
                            on_click=lambda: _render_drilldown_unset(),
                        ).props("flat dense size=sm").style("color: var(--enola-charcoal-light);")

                if n_categoria == 0:
                    ui.label(
                        "Esta categoría no tiene etiquetas de violencia en la muestra actual."
                    ).classes("text-sm mt-3").style(
                        "color: var(--enola-charcoal-light); font-style: italic;"
                    )
                    return

                ui.plotly(
                    build_bar_categories(
                        subset,
                        level="subdimension",
                        categoria_padre=codigo_cat,
                    )
                ).classes("w-full mt-4")

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
            "padding: 1.75rem 2rem; border-radius: 0.875rem; "
            "background: rgba(191, 161, 129, 0.08); "
            "border-left: 3px solid var(--enola-brass); "
            "color: var(--enola-charcoal); "
            "display: flex; align-items: flex-start; gap: 1rem;"
        ):
            ui.icon("info", size="22px").style(
                f"color: {theme.BRASS_DEEP}; flex-shrink: 0; margin-top: 2px;"
            )
            with ui.column().classes("gap-1"):
                ui.label("Sin feedback humano todavía").classes("text-base font-semibold").style(
                    f"color: {theme.PLUM}; letter-spacing: -0.005em;"
                )
                ui.label(
                    "Marcá análisis como de acuerdo / corregidos en la "
                    "pestaña **Validación** para alimentar la matriz de "
                    "confusión y las métricas de rendimiento."
                ).classes("text-sm").style("line-height: 1.5;")
        return

    lookup: dict = {a.get("id"): a for a in analysis if a.get("id") is not None}
    report = render_metrics_report(feedback, analysis_lookup=lookup)
    cm_dict = report["confusion_matrix"]
    metrics = report["metrics"]

    # --- Definiciones de los 4 valores de la matriz ---------------------
    with ui.element("div").style(
        "padding: 1.5rem 1.75rem; border-radius: 0.875rem; "
        "background: linear-gradient(135deg, rgba(107, 78, 113, 0.05) 0%, "
        "rgba(191, 161, 129, 0.10) 100%); "
        "border-left: 3px solid var(--enola-plum); "
        "color: var(--enola-charcoal); line-height: 1.6;"
    ):
        ui.label("Matriz de confusión · definiciones").classes(
            "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
        ).style("display: inline-flex;")

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
        "background: rgba(191, 161, 129, 0.08); "
        "border-left: 3px solid var(--enola-brass); "
        "color: var(--enola-charcoal); line-height: 1.6;"
    ):
        ui.label("Fórmulas de rendimiento").classes(
            "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
        ).style("display: inline-flex;")

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
                "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
            ).style("display: inline-flex;")
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
                "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
            ).style("display: inline-flex;")
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
        subtitle="Reglas 1 a 6 del marco metodológico",
        current_path="/estadistica",
        body=_render_body,
        requires_auth=False,
    )


def _render_body() -> None:
    try:
        analysis, posts, pages, feedback = _load_data()
    except Exception as exc:
        logger.exception("Failed to load data: %s", exc)
        ui.label("No se pudo cargar la base de datos.").classes("text-base")
        return

    with ui.column().classes("w-full gap-8"):
        with ui.row().classes("w-full items-end justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-0"):
                ui.label("Estadísticas descriptivas").classes(
                    "text-2xl font-semibold enola-display"
                ).style("color: var(--enola-plum); letter-spacing: -0.02em;")
                ui.label("Una pestaña por regla del marco metodológico (Regla 1 a 6).").classes(
                    "text-sm"
                ).style("color: var(--enola-charcoal-light); letter-spacing: 0.02em;")
            ui.button(
                "📥 Descargar CSV",
                icon="download",
                on_click=lambda: _download_csv(analysis, posts, pages, feedback),
            ).props("outline color=primary").style("font-weight: 500;")

        # Regla 1 needs the full (unfiltered) dataset because basura
        # digital is one of its denominators. We compute it once here
        # so the Regla 1 tab can render it without re-querying.
        reliability: ReliabilityReport = calcular_valores_perdidos(analysis)

        # --- Content-type selector (Todos / Posts / Comments) -----------
        # Drives the subset used by Regla 2, 3, 4 y 5. Regla 1 y 6
        # always operate on the full dataset.
        content_type_value: dict[str, str] = {"v": "all"}

        def _on_type_change(e) -> None:
            content_type_value["v"] = e.value
            _rerender_tabs()

        with ui.row().classes("w-full items-center justify-between gap-4 flex-wrap"):
            with ui.row().classes("items-center gap-3"):
                ui.label("Tipo de contenido").classes("text-sm font-semibold").style(
                    "color: var(--enola-charcoal); letter-spacing: 0.005em;"
                )
                ui.toggle(
                    {"all": "Todos", "post": "Posts", "comment": "Comments"},
                    value="all",
                    on_change=_on_type_change,
                ).props("rounded spread").style("border: 1px solid rgba(191, 161, 129, 0.30);")

        # --- Tabs container (one per regla) ----------------------------
        tabs_holder = ui.column().classes("w-full gap-8")

        def _rerender_tabs() -> None:
            tabs_holder.clear()
            subset = filter_by_content_type(analysis, content_type_value["v"])
            if not subset:
                subset = analysis
            with tabs_holder:
                _render_rules_tabs(
                    analysis=analysis,
                    subset=subset,
                    posts=posts,
                    pages=pages,
                    feedback=feedback,
                    reliability=reliability,
                )

        _rerender_tabs()


def _render_rules_tabs(
    *,
    analysis: list[dict],
    subset: list[dict],
    posts: list[dict],
    pages: list[dict],
    feedback: list[dict],
    reliability: ReliabilityReport,
) -> None:
    """Render the six Regla tabs (Regla 1 → 6) in a single QTabs widget.

    Each tab contains the canonical presentation of its rule. The
    subset (``Todos | Posts | Comments``) only affects Reglas 2, 3 y 5
    — Regla 1 uses the full dataset (basura digital is part of its
    denominator), Regla 4 uses the full dataset (crosstabs need the
    complete population to compute column marginals) and Regla 6 uses
    the feedback table directly.
    """
    with ui.tabs().classes("w-full").props("align=justify") as tabs:
        tab1 = ui.tab("Regla 1 — Valores perdidos")
        tab2 = ui.tab("Regla 2 — Frecuencias")
        tab3 = ui.tab("Regla 3 — Moda")
        tab4 = ui.tab("Regla 4 — Bivariado")
        tab5 = ui.tab("Regla 5 — Visualización")
        tab6 = ui.tab("Regla 6 — Métricas IA")

    with ui.tab_panels(tabs, value=tab5).classes("w-full"):
        with ui.tab_panel(tab1):
            render_regla1(reliability)
        with ui.tab_panel(tab2):
            _render_regla2(subset)
        with ui.tab_panel(tab3):
            _render_regla3(subset)
        with ui.tab_panel(tab4):
            _render_regla4(analysis, posts, pages)
        with ui.tab_panel(tab5):
            _render_charts_overview(subset)
        with ui.tab_panel(tab6):
            _render_regla6(analysis, feedback)


def _download_csv(
    analysis: list[dict],
    posts: list[dict],
    pages: list[dict],
    feedback: list[dict],
) -> None:
    try:
        csv_bytes = _build_stats_csv(analysis, posts, pages, feedback)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ui.download(csv_bytes, f"estadisticas_enola_{timestamp}.csv")
    except Exception as exc:
        logger.exception("Error generating CSV: %s", exc)
        ui.notify(f"Error al generar CSV: {exc}", type="negative")
