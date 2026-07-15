"""IA & Confiabilidad — Regla 6 del documento metodológico.

Página premium con la matriz de confusión (VP/VN/FP/FN) y las tres
métricas de rendimiento (Precisión, Sensibilidad, F1-Score) usando
sklearn. La verdad terreno proviene de ``analysis_feedback`` —
``agrees=true`` confirma la predicción de la IA; ``agrees=false``
con ``corrected_categoria`` aporta el override humano.
"""

from __future__ import annotations

import logging

from nicegui import ui

from src.report.metrics import render_metrics_report
from src.storage import get_database
from src.ui.adjusted_report import build_adjusted_analysis
from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.charts import build_confusion_matrix_heatmap
from src.ui.nicegui_app.components.kpi_card import kpi_grid
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)


def _load():
    db = get_database()
    raw = db.get_analysis_results()
    feedback = db.list_feedback()
    analysis = build_adjusted_analysis(raw, feedback)
    return analysis, feedback


def _render_body() -> None:
    section_header(
        "Regla 6",
        "Confiabilidad y validez del instrumento (IA)",
        subtitle=(
            "Matriz de confusión y métricas de rendimiento (Precisión, "
            "Sensibilidad, F1-Score) calculadas con sklearn sobre la "
            "verdad terreno provista por el revisor humano."
        ),
    )

    try:
        analysis, feedback = _load()
    except Exception as exc:
        logger.exception("Failed to load metrics: %s", exc)
        ui.label("No se pudo cargar la base de datos.").classes("text-base")
        return

    if not feedback:
        with ui.element("div").style(
            "padding: 2.5rem 2rem; border-radius: 0.875rem; "
            "background: rgba(191, 161, 129, 0.08); "
            "border: 1px solid rgba(191, 161, 129, 0.30); "
            "color: var(--enola-charcoal); text-align: center;"
        ):
            with ui.element("div").style(
                "width: 64px; height: 64px; border-radius: 16px; margin: 0 auto 1rem; "
                f"background: linear-gradient(135deg, {theme.PLUM} 0%, "
                f"{theme.ROSE} 100%); "
                "display: flex; align-items: center; justify-content: center; "
                f"box-shadow: 0 6px 16px -6px {theme.PLUM}55;"
            ):
                ui.icon("psychology", size="30px").style(f"color: {theme.CREAM};")
            ui.label("Sin feedback humano todavía").classes(
                "text-lg font-semibold enola-display"
            ).style(f"color: {theme.PLUM}; letter-spacing: -0.015em;")
            ui.label(
                "Marcá análisis en la pestaña **Validación** de "
                "`streamlit run src/ui/app.py` para alimentar estas "
                "métricas."
            ).classes("text-sm mt-2").style(
                "color: var(--enola-charcoal-light); line-height: 1.6; max-width: 50ch; "
                "margin-left: auto; margin-right: auto;"
            )
        return

    # Build a lookup of analysis rows by id so the metrics module can
    # recover the AI's prediction for each feedback row.
    lookup: dict = {}
    for a in analysis:
        aid = a.get("id")
        if aid is not None:
            lookup[aid] = a

    report = render_metrics_report(feedback, analysis_lookup=lookup)
    cm_dict = report["confusion_matrix"]
    metrics = report["metrics"]

    # --- Top KPIs: soporte + métricas ---
    kpi_grid(
        4,
        [
            {
                "label": "Soporte (n)",
                "value": str(metrics["Soporte"]),
                "icon": "inventory_2",
                "sub": "Análisis con feedback humano",
            },
            {
                "label": "Precisión",
                "value": f"{metrics['Precisión'] * 100:.1f}%",
                "icon": "target",
                "accent": theme.PLUM,
                "sub": "VP / (VP + FP)",
            },
            {
                "label": "Sensibilidad (Recall)",
                "value": f"{metrics['Sensibilidad (Recall)'] * 100:.1f}%",
                "icon": "radar",
                "accent": theme.ROSE,
                "sub": "VP / (VP + FN)",
            },
            {
                "label": "F1-Score",
                "value": f"{metrics['F1-Score'] * 100:.1f}%",
                "icon": "balance",
                "accent": theme.BRASS,
                "sub": "Media armónica P / S",
            },
        ],
    )

    # --- Confusion matrix: heatmap + counts ---
    section_header(
        "Paso 6.1",
        "Matriz de confusión",
        subtitle="Verdaderos/Falsos Positivos/Negativos a nivel binario (con vs sin violencia).",
    )

    with ui.element("div").classes("w-full grid gap-6").style("grid-template-columns: 2fr 1fr;"):
        # Left: heatmap
        with ui.element("div"):
            ui.plotly(
                build_confusion_matrix_heatmap(
                    vp=cm_dict["VP"],
                    vn=cm_dict["VN"],
                    fp=cm_dict["FP"],
                    fn=cm_dict["FN"],
                )
            ).classes("w-full")

        # Right: 2x2 mini-grid of counts
        with ui.element("div"):
            kpi_grid(
                2,
                [
                    {
                        "label": "Verdaderos Positivos",
                        "value": str(cm_dict["VP"]),
                        "icon": "check_circle",
                        "accent": theme.RELIABILITY_OK,
                        "sub": "IA y humano coinciden: violencia",
                    },
                    {
                        "label": "Verdaderos Negativos",
                        "value": str(cm_dict["VN"]),
                        "icon": "check_circle_outline",
                        "accent": theme.RELIABILITY_OK,
                        "sub": "IA y humano coinciden: no violencia",
                    },
                    {
                        "label": "Falsos Positivos",
                        "value": str(cm_dict["FP"]),
                        "icon": "error",
                        "accent": theme.RELIABILITY_CRITICA,
                        "sub": "IA marcó violencia, humano dijo que no",
                    },
                    {
                        "label": "Falsos Negativos",
                        "value": str(cm_dict["FN"]),
                        "icon": "warning",
                        "accent": theme.RELIABILITY_PREVENTIVA,
                        "sub": "IA no marcó, humano dijo violencia",
                    },
                ],
            )

    # --- Paso 6.3 — Reporte de validación ---
    section_header(
        "Paso 6.3",
        "Reporte de validación del instrumento",
        subtitle=(
            "Estas métricas certifican que los resultados descriptivos "
            "provienen de un instrumento válido y confiable."
        ),
    )

    # Plain-language interpretation
    with ui.element("div").style(
        "padding: 1.75rem 2rem; border-radius: 1rem; "
        "background: linear-gradient(135deg, rgba(107, 78, 113, 0.06) 0%, "
        "rgba(192, 132, 151, 0.10) 100%); "
        "border-left: 4px solid var(--enola-plum); "
        "color: var(--enola-charcoal); line-height: 1.65;"
    ):
        ui.label("Lectura interpretativa").classes(
            "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow mb-3"
        ).style("display: inline-flex;")

        prec = metrics["Precisión"] * 100
        rec = metrics["Sensibilidad (Recall)"] * 100
        f1 = metrics["F1-Score"] * 100
        soporte = metrics["Soporte"]

        if soporte == 0:
            texto = "Sin muestra evaluada — marcá análisis en Validación."
        elif f1 >= 80:
            texto = (
                f"**Excelente rendimiento.** Con un F1-Score de {f1:.1f}%, el "
                f"instrumento discrimina correctamente la presencia de "
                f"violencia en {soporte} casos revisados. "
                f"Precisión {prec:.1f}% y Sensibilidad {rec:.1f}%."
            )
        elif f1 >= 60:
            texto = (
                f"**Rendimiento aceptable.** F1-Score de {f1:.1f}% sobre "
                f"{soporte} casos. Precisión {prec:.1f}% (qué tan confiables "
                f"son las alarmas), Sensibilidad {rec:.1f}% (qué tanta "
                f"violencia real se detecta). Revisar las áreas donde la "
                f"métrica cae para calibrar el prompt."
            )
        else:
            texto = (
                f"**Rendimiento bajo.** F1-Score de {f1:.1f}% sobre "
                f"{soporte} casos. Precisión {prec:.1f}%, Sensibilidad "
                f"{rec:.1f}%. Se recomienda ampliar la muestra de feedback "
                f"y revisar los falsos positivos/negativos para entender "
                f"los sesgos del clasificador."
            )

        ui.label(texto).classes("text-sm leading-relaxed")

    # Breakdown of feedback agreements / disagreements
    total = len(feedback)
    agrees_count = sum(1 for f in feedback if str(f.get("agrees") or "").lower() == "true")
    disagrees = total - agrees_count

    section_header(
        "Resumen",
        "Acuerdos y desacuerdos del feedback humano",
        subtitle="Distribución de acuerdos y desacuerdos con el clasificador.",
    )

    kpi_grid(
        2,
        [
            {
                "label": "Acuerdos (agrees=true)",
                "value": str(agrees_count),
                "icon": "thumb_up",
                "accent": theme.RELIABILITY_OK,
                "sub": f"{agrees_count / total * 100:.1f}% del total" if total else "—",
            },
            {
                "label": "Desacuerdos (agrees=false)",
                "value": str(disagrees),
                "icon": "thumb_down",
                "accent": theme.BRASS,
                "sub": f"{disagrees / total * 100:.1f}% del total" if total else "—",
            },
        ],
    )


@ui.page("/ia")
def page_ia() -> None:
    page_scaffold(
        "IA & Confiabilidad",
        subtitle="Regla 6 — matriz de confusión y métricas de la IA",
        current_path="/ia",
        body=_render_body,
        requires_auth=False,
    )
