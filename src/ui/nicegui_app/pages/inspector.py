"""Inspector — drill-down premium de un análisis.

Permite explorar contenido analizado: posts o comments. Muestra el
texto original, las etiquetas detectadas (multi-label), el estado del
feedback humano y métricas de severidad/dimensión. Tabla con todos
los análisis para navegar.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from nicegui import ui

from src.storage import get_database
from src.ui.adjusted_report import build_adjusted_analysis
from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.kpi_card import empty_state, kpi_grid
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)


# --- Helpers ---------------------------------------------------------------


_SEVERITY_EMOJI = {
    "alta": "🔴",
    "media": "🟡",
    "baja": "🟢",
    "ninguna": "⚪",
}


def _severity_color(sev: str | None) -> str:
    return {
        "alta": "#9D4E5B",
        "media": "#BFA181",
        "baja": "#C08497",
        "ninguna": "#6B5E73",
    }.get((sev or "ninguna").lower(), "#6B5E73")


def _label_dict(label: dict) -> dict[str, Any]:
    return {
        "n": label.get("orden", ""),
        "categoria": label.get("categoria") or "—",
        "dimension": label.get("dimension") or "—",
        "severidad": label.get("severidad") or "ninguna",
        "sev_emoji": _SEVERITY_EMOJI.get(label.get("severidad"), "⚪"),
        "confianza": label.get("confianza"),
        "justificacion": (label.get("justificacion") or "")[:200],
        "evidencia": (label.get("evidencia") or "")[:200],
    }


# --- Data -----------------------------------------------------------------


def _load():
    db = get_database()
    raw = db.get_analysis_results()
    feedback = db.list_feedback()
    posts = db.get_posts(limit=2000)
    analysis = build_adjusted_analysis(raw, feedback)

    text_by_id: dict = {}
    for p in posts or []:
        pid = p.get("id")
        if pid is not None:
            text_by_id[pid] = p.get("text") or ""

    return analysis, text_by_id, feedback


def _build_table_rows(items: list[dict], filter_type: str) -> list[dict]:
    rows = []
    for r in items:
        if r.get("exclusion_label"):
            continue
        if filter_type != "all" and r.get("content_type") != filter_type:
            continue
        sev = r.get("severidad") or "ninguna"
        rows.append(
            {
                "id": r.get("id"),
                "tipo": r.get("content_type") or "—",
                "cat": r.get("categoria") or "—",
                "dim": r.get("dimension") or "—",
                "sev": f"{_SEVERITY_EMOJI.get(sev, '⚪')} {sev}",
                "fuente": "🧑 humano" if r.get("adjusted_by_human") else "🤖 IA",
                "feedback": "✅" if r.get("has_feedback") else "—",
            }
        )
    return rows


# --- Renderers -----------------------------------------------------------


def _render_detail(
    selected_id: int | None,
    analysis: list[dict],
    text_by_id: dict,
    feedback: list[dict],
) -> None:
    """Render the detail panel for the selected analysis row."""
    if selected_id is None:
        empty_state(
            "arrow_upward",
            "Seleccioná un análisis arriba",
            hint="Hacé click en una fila de la tabla para ver el detalle completo.",
        )
        return

    row = next((r for r in analysis if r.get("id") == selected_id), None)
    if not row:
        ui.label(f"Análisis #{selected_id} no encontrado.").classes("text-base")
        return

    # Find the original text
    content_id = row.get("content_id") or row.get("post_id") or row.get("comment_id")
    original_text = ""
    if content_id is not None:
        original_text = text_by_id.get(content_id, "") or ""
    if not original_text:
        original_text = row.get("evidencia") or ""
    if len(original_text) > 1500:
        original_text = original_text[:1500] + "..."

    labels = row.get("labels") or []
    primary_cat = row.get("categoria") or "ninguna"
    primary_dim = row.get("dimension") or "—"
    sev = row.get("severidad") or "ninguna"

    section_header(
        f"Análisis #{selected_id}",
        f"{row.get('content_type', '—').capitalize()} · {primary_cat}",
    )

    kpi_grid(
        4,
        [
            {
                "label": "Categoría primaria",
                "value": primary_cat,
                "icon": "category",
                "accent": theme.PLUM,
            },
            {
                "label": "Subdimensión primaria",
                "value": primary_dim,
                "icon": "tag",
            },
            {
                "label": "Severidad global",
                "value": f"{_SEVERITY_EMOJI.get(sev, '⚪')} {sev.upper()}",
                "icon": "priority_high",
                "accent": _severity_color(sev),
            },
            {
                "label": "Etiquetas detectadas",
                "value": str(len(labels)) if labels else "1",
                "icon": "label",
                "sub": "Multi-label",
            },
        ],
    )

    # Source badge
    with ui.element("div").classes("w-full mt-6"):
        if row.get("adjusted_by_human"):
            ui.label(
                "🧑 Esta categoría/dimensión/justificación fue corregida "
                "por un humano. El reporte refleja la versión ajustada."
            ).classes("text-sm").style(
                "padding: 0.75rem 1rem; "
                "background: rgba(107, 78, 113, 0.08); "
                "border-left: 3px solid var(--enola-plum); "
                "border-radius: 0.5rem;"
            )
        elif row.get("has_feedback"):
            ui.label("🤖 Análisis aún sin revisión humana (sólo etiquetado por la IA).").classes(
                "text-sm"
            ).style(
                "padding: 0.75rem 1rem; "
                "background: rgba(191, 161, 129, 0.08); "
                "border-left: 3px solid var(--enola-brass); "
                "border-radius: 0.5rem;"
            )

    # Original text
    if original_text:
        section_header(
            "Texto original",
            f"{row.get('content_type', '—').capitalize()} #{content_id}",
        )
        with ui.element("div").style(
            "padding: 1.25rem 1.5rem; "
            "border-radius: 0.875rem; "
            "background: var(--enola-cream); "
            "border: 1px solid rgba(191, 161, 129, 0.25); "
            "font-family: var(--enola-font-mono); "
            "font-size: 0.92rem; line-height: 1.6; "
            "color: var(--enola-charcoal); "
            "white-space: pre-wrap; "
            "max-height: 400px; overflow-y: auto;"
        ):
            ui.label(original_text)

    # Labels (multi-label)
    if labels:
        section_header(
            "Etiquetas detectadas",
            f"{len(labels)} clasificación(es)",
        )
        with ui.column().classes("w-full gap-3"):
            for lbl in labels:
                row_data = _label_dict(lbl)
                with ui.element("div").style(
                    "padding: 1rem 1.25rem; border-radius: 0.875rem; "
                    "background: var(--enola-blush); "
                    "border: 1px solid rgba(192, 132, 151, 0.18);"
                ):
                    with ui.row().classes("w-full items-center gap-3 mb-2 flex-wrap"):
                        ui.label(f"#{row_data['n']}").classes("text-xs font-mono").style(
                            "color: var(--enola-brass-deep); "
                            "background: var(--enola-cream); "
                            "padding: 0.15rem 0.5rem; border-radius: 999px;"
                        )
                        ui.label(row_data["categoria"]).classes(
                            "text-sm font-semibold enola-display"
                        ).style("color: var(--enola-plum);")
                        ui.label("·").style("color: var(--enola-charcoal-light);")
                        ui.label(row_data["dimension"]).classes("text-sm").style(
                            "color: var(--enola-charcoal);"
                        )
                        ui.element("div").style("flex: 1;")
                        with ui.element("div").style(
                            "padding: 0.15rem 0.65rem; "
                            "border-radius: 999px; "
                            f"background: {_severity_color(row_data['severidad'])}1a; "
                            f"color: {_severity_color(row_data['severidad'])}; "
                            "font-size: 0.72rem; "
                            "letter-spacing: 0.06em; "
                            "font-weight: 600; "
                            "text-transform: uppercase;"
                        ):
                            ui.label(f"{row_data['sev_emoji']} {row_data['severidad']}")
                    if row_data["confianza"] is not None:
                        ui.label(f"Confianza: {row_data['confianza']:.2f}").classes(
                            "text-xs"
                        ).style("color: var(--enola-charcoal-light); margin-bottom: 0.5rem;")
                    if row_data["justificacion"]:
                        ui.label("Justificación:").classes(
                            "text-xs uppercase tracking-widest font-semibold"
                        ).style("color: var(--enola-brass-deep); margin-bottom: 0.25rem;")
                        ui.label(row_data["justificacion"]).classes(
                            "text-sm leading-relaxed"
                        ).style("color: var(--enola-charcoal);")
                    if row_data["evidencia"]:
                        ui.label("Evidencia:").classes(
                            "text-xs uppercase tracking-widest font-semibold mt-2"
                        ).style("color: var(--enola-brass-deep); margin-bottom: 0.25rem;")
                        ui.label(row_data["evidencia"]).classes("text-sm leading-relaxed").style(
                            "color: var(--enola-charcoal); font-style: italic;"
                        )
    else:
        with ui.element("div").classes("w-full mt-4"):
            with ui.expansion("📋 Detalle completo del análisis", icon="expand_more").classes(
                "w-full"
            ):
                if row.get("justificacion"):
                    ui.label("Justificación:").classes(
                        "text-xs uppercase tracking-widest font-semibold"
                    ).style("color: var(--enola-brass-deep);")
                    ui.label(row["justificacion"]).classes("text-sm leading-relaxed").style(
                        "color: var(--enola-charcoal);"
                    )
                if row.get("evidencia"):
                    ui.label("Evidencia:").classes(
                        "text-xs uppercase tracking-widest font-semibold mt-2"
                    ).style("color: var(--enola-brass-deep);")
                    ui.label(row["evidencia"]).classes("text-sm leading-relaxed").style(
                        "color: var(--enola-charcoal); font-style: italic;"
                    )
                if row.get("regla_disparada"):
                    ui.label("Regla disparada:").classes(
                        "text-xs uppercase tracking-widest font-semibold mt-2"
                    ).style("color: var(--enola-brass-deep);")
                    ui.label(str(row["regla_disparada"])).classes("text-sm")
                if row.get("marcadores_detectados"):
                    ui.label("Marcadores detectados:").classes(
                        "text-xs uppercase tracking-widest font-semibold mt-2"
                    ).style("color: var(--enola-brass-deep);")
                    ui.label(str(row["marcadores_detectados"])).classes("text-sm")

    # Feedback on this analysis
    fb_for_row = [f for f in feedback if f.get("analysis_result_id") == selected_id]
    if fb_for_row:
        section_header(
            "Feedback humano",
            f"{len(fb_for_row)} revisión(es)",
        )
        for fb in fb_for_row:
            agrees_val = str(fb.get("agrees") or "").lower() == "true"
            with ui.element("div").style(
                "padding: 1rem 1.25rem; border-radius: 0.875rem; "
                f"background: {'rgba(143, 166, 142, 0.10)' if agrees_val else 'rgba(191, 161, 129, 0.12)'}; "
                f"border-left: 3px solid {theme.RELIABILITY_OK if agrees_val else theme.BRASS};"
            ):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ui.label("✅ De acuerdo" if agrees_val else "⚠️ Corregido").classes(
                        "text-sm font-semibold"
                    ).style(f"color: {theme.RELIABILITY_OK if agrees_val else theme.BRASS_DEEP};")
                    if fb.get("reviewer"):
                        ui.label(f"· por {fb['reviewer']}").classes("text-xs").style(
                            "color: var(--enola-charcoal-light);"
                        )
                if not agrees_val:
                    if fb.get("corrected_categoria"):
                        ui.label(f"Categoría corregida: {fb['corrected_categoria']}").classes(
                            "text-sm"
                        )
                    if fb.get("corrected_dimension"):
                        ui.label(f"Subdimensión corregida: {fb['corrected_dimension']}").classes(
                            "text-sm"
                        )
                    if fb.get("reason"):
                        ui.label(f"Razón: {fb['reason']}").classes(
                            "text-sm leading-relaxed mt-2"
                        ).style("color: var(--enola-charcoal);")


# --- CSV Export ----------------------------------------------------------


def _build_csv(analysis: list[dict], text_by_id: dict) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writerow(["id", "tipo", "id_contenido", "texto", "clasificaciones"])
    for r in analysis:
        content_id = r.get("content_id") or r.get("post_id") or r.get("comment_id")
        texto = (
            text_by_id.get(content_id, "") or r.get("evidencia") or ""
            if content_id
            else r.get("evidencia") or ""
        )
        labels = r.get("labels") or []
        if labels:
            parts = [
                f"{label.get('categoria') or '—'}|{label.get('dimension') or '—'}|{label.get('severidad') or 'ninguna'}"
                for label in labels
            ]
            clasificaciones = "||".join(parts)
        else:
            cat = r.get("categoria") or "—"
            dim = r.get("dimension") or "—"
            sev = r.get("severidad") or "ninguna"
            clasificaciones = f"{cat}|{dim}|{sev}"
        writer.writerow(
            [r.get("id"), r.get("content_type") or "—", content_id or "", texto, clasificaciones]
        )
    return output.getvalue().encode("utf-8")


# --- Page entry ----------------------------------------------------------


# Module-level state holder. NiceGUI's @ui.refreshable works only on
# functions defined at module scope; using it inside the page body
# confuses the LSP and (worse) creates a new refreshable per request.
_INSPECTOR_STATE: dict = {
    "analysis": [],
    "text_by_id": {},
    "feedback": [],
    "selected_id": None,
}


@ui.refreshable
def _inspector_detail_panel() -> None:
    """Refreshable detail panel — re-rendered on selection change."""
    _render_detail(
        _INSPECTOR_STATE.get("selected_id"),
        _INSPECTOR_STATE["analysis"],
        _INSPECTOR_STATE["text_by_id"],
        _INSPECTOR_STATE["feedback"],
    )


@ui.page("/inspector")
def page_inspector() -> None:
    page_scaffold(
        "Inspector",
        subtitle="Drill-down de contenido analizado",
        current_path="/inspector",
        body=_render_body,
        requires_auth=False,
    )


def _render_body() -> None:
    try:
        analysis, text_by_id, feedback = _load()
    except Exception as exc:
        logger.exception("Failed to load inspector data: %s", exc)
        ui.label("No se pudo cargar la base de datos.").classes("text-base")
        return

    _INSPECTOR_STATE["analysis"] = analysis
    _INSPECTOR_STATE["text_by_id"] = text_by_id
    _INSPECTOR_STATE["feedback"] = feedback
    _INSPECTOR_STATE["selected_id"] = None

    if not analysis:
        empty_state(
            "inbox",
            "No hay análisis todavía",
            hint=(
                "Corré el análisis + clasificador "
                "(`streamlit run src/ui/app.py`) para generar análisis."
            ),
        )
        return

    total = len(analysis)
    basura_count = sum(1 for r in analysis if str(r.get("exclusion_label") or "") == "CODIGO_99")
    comun_count = sum(
        1 for r in analysis if str(r.get("exclusion_label") or "") == "VIOLENCIA_COMUN"
    )
    net_total = max(total - basura_count - comun_count, 0)
    violent = sum(
        1
        for r in analysis
        if str(r.get("tiene_violencia") or "") == "true"
        and str(r.get("exclusion_label") or "") not in {"CODIGO_99", "VIOLENCIA_COMUN"}
    )
    excluded = sum(
        1 for r in analysis if (r.get("exclusion_label") or "") in {"CODIGO_99", "VIOLENCIA_COMUN"}
    )
    feedback_count = sum(1 for r in analysis if r.get("has_feedback"))

    kpi_grid(
        4,
        [
            {
                "label": "Análisis disponibles",
                "value": str(net_total),
                "icon": "inventory_2",
                "sub": (
                    f"De {total} filas · {basura_count} basura digital + {comun_count} viol. común"
                    if basura_count or comun_count
                    else "Filas en analysis_results"
                ),
            },
            {
                "label": "Con violencia",
                "value": str(violent),
                "icon": "warning",
                "accent": theme.RELIABILITY_CRITICA,
                "sub": (f"{violent / net_total * 100:.1f}% del neto" if net_total else "—"),
            },
            {
                "label": "Excluidos (CÓDIGO 99 / común)",
                "value": str(excluded),
                "icon": "block",
                "accent": theme.CHARCOAL_LIGHT,
                "sub": "Basura digital + violencia común",
            },
            {
                "label": "Con feedback humano",
                "value": str(feedback_count),
                "icon": "person",
                "accent": theme.PLUM,
                "sub": (f"{feedback_count / net_total * 100:.1f}% revisado" if net_total else "—"),
            },
        ],
    )

    section_header(
        "Explorador",
        "Inspector de contenido analizado",
        subtitle=(
            "Filtrá por tipo de contenido y seleccioná un análisis "
            "para ver el detalle: texto original, etiquetas detectadas y feedback humano."
        ),
    )

    with ui.row().classes("w-full items-center gap-4 mb-2"):
        ui.label("Filtrar por:").classes("text-sm font-semibold").style(
            "color: var(--enola-charcoal-light);"
        )

        def _sort_key(r: dict) -> int:
            rid = r.get("id")
            return int(rid) if isinstance(rid, (int, float)) else 0

        sorted_analysis = sorted(analysis, key=_sort_key, reverse=True)
        display = sorted_analysis[:100]

        filter_state = {"content_type": "all"}

        def _on_filter_change(value: str) -> None:
            filter_state["content_type"] = value
            table.rows = _build_table_rows(display, value)
            table.update()

        ui.toggle(
            {"all": "Todos", "post": "Posts", "comment": "Comentarios"},
            value="all",
            on_change=lambda e: _on_filter_change(e.value),
        ).props("spread no-caps")

        def _download_csv() -> None:
            ui.download(
                _build_csv(analysis, text_by_id),
                filename="inspector_analisis.csv",
            )

        ui.button(
            "⬇ CSV",
            on_click=_download_csv,
            icon="download",
        ).props("flat size=sm color=primary").style(f"color: {theme.PLUM}; font-weight: 500;")

    def _on_select(event) -> None:
        sel = event.selection
        if not sel:
            return
        first = sel[0] if isinstance(sel, list) else sel
        aid = first.get("id") if isinstance(first, dict) else None
        if aid is None:
            return
        _INSPECTOR_STATE["selected_id"] = aid
        _inspector_detail_panel.refresh()

    table = ui.table(
        columns=[
            {"name": "id", "label": "ID", "field": "id", "align": "right"},
            {"name": "tipo", "label": "Tipo", "field": "tipo", "align": "left"},
            {"name": "cat", "label": "Categoría", "field": "cat", "align": "left"},
            {"name": "dim", "label": "Subdimensión", "field": "dim", "align": "left"},
            {"name": "sev", "label": "Severidad", "field": "sev", "align": "left"},
            {"name": "fuente", "label": "Fuente", "field": "fuente", "align": "left"},
            {"name": "feedback", "label": "Feedback", "field": "feedback", "align": "center"},
        ],
        rows=_build_table_rows(display, "all"),
        row_key="id",
        pagination=20,
        on_select=lambda e: _on_select(e),
    ).classes("w-full")

    _inspector_detail_panel()
