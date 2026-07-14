"""Inicio — premium landing page.

Composes the hero banner, the headline KPI grid and the Regla 1
reliability banner. All data flows from the SQLite database via the
existing ``build_adjusted_analysis`` pipeline — no business logic
changes, just a premium presentation.
"""

from __future__ import annotations

import logging

from nicegui import ui

from src.report.reliability import ReliabilityReport, calcular_valores_perdidos
from src.storage import get_database
from src.ui.adjusted_report import build_adjusted_analysis, compute_adjustment_breakdown
from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.kpi_card import kpi_grid
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)


@ui.page("/")
def _root_redirect() -> None:
    """Root path — redirect to the landing page."""
    ui.navigate.to("/inicio")


@ui.page("/inicio")
def page_inicio() -> None:
    """Premium landing — hero, KPIs, Regla 1 reliability banner.

    Public page (no auth gate): the landing is the same for logged-in
    reviewers and anonymous visitors. Logging in unlocks the rest of
    the navigation and the validation tab.
    """
    page_scaffold(
        "Enola Investigadora Digital",
        subtitle="Detección de violencia de género digital con RAG",
        current_path="/inicio",
        body=render_inicio_body,
        requires_auth=False,
    )


# --- Data loading ------------------------------------------------------------


def _load_data() -> tuple[list[dict], dict, ReliabilityReport]:
    """Pull everything the Inicio page needs in one shot."""
    db = get_database()
    raw_analysis = db.get_analysis_results()
    feedback_rows = db.list_feedback()

    analysis = build_adjusted_analysis(raw_analysis, feedback_rows)
    adjustment = compute_adjustment_breakdown(analysis)
    reliability = calcular_valores_perdidos(analysis)
    return analysis, adjustment, reliability


# --- Components --------------------------------------------------------------


def render_hero() -> None:
    """The premium hero — gradient plum with rose radial accents."""
    with ui.element("div").classes("enola-hero"):
        ui.label("TFM 2026 · Universidad de Granada").classes("enola-hero-badge")
        ui.label("Enola Investigadora Digital").classes("enola-display")
        ui.label(
            "Sistema RAG de detección de violencia de género digital en Facebook. "
            "Inspirado en Enola Holmes, analiza conversaciones con una taxonomía "
            "canónica de 6 categorías y 18 subdimensiones, asistida por Ollama "
            "y ChromaDB, con validación humana en el circuito."
        )


def render_kpis(analysis: list[dict], adjustment: dict) -> None:
    """Render the six headline KPI cards.

    Uses the existing data shape from the legacy landing but with the
    premium card component.
    """
    total = len(analysis)
    violent_count = sum(1 for a in analysis if str(a.get("tiene_violencia") or "") == "true")
    violent_pct = round(violent_count / total * 100.0, 1) if total else 0.0
    adjusted_pct = adjustment.get("adjusted_pct", 0.0)
    autonomous_pct = adjustment.get("autonomous_pct", 0.0)
    adjusted_count = adjustment.get("adjusted_count", 0)

    cards = [
        {
            "label": "Análisis totales",
            "value": f"{total:,}".replace(",", "."),
            "icon": "description",
            "sub": "Filas en analysis_results",
        },
        {
            "label": "% con violencia",
            "value": f"{violent_pct}%",
            "icon": "warning",
            "accent": theme.RELIABILITY_CRITICA,
            "sub": f"{violent_count} contenidos clasificados como violentos",
        },
        {
            "label": "% Ajustado por humanos",
            "value": f"{adjusted_pct}%",
            "icon": "person",
            "accent": theme.PLUM,
            "sub": f"{adjusted_count} revisiones del equipo",
        },
        {
            "label": "% Autónomo",
            "value": f"{autonomous_pct}%",
            "icon": "smart_toy",
            "accent": theme.BRASS,
            "sub": "Sólo clasificación de la IA",
        },
    ]
    kpi_grid(4, cards)

    # Secondary row: 3 cards centred.
    db = get_database()
    stats = db.get_stats()
    categories = 6  # canonical taxonomy
    kpi_grid(
        3,
        [
            {
                "label": "Categorías canónicas",
                "value": str(categories),
                "icon": "category",
                "sub": "Taxonomía cerrada VDG_*",
            },
            {
                "label": "Subdimensiones canónicas",
                "value": str(len(theme.SUBDIMENSIONES_ORDENADAS)),
                "icon": "workspaces",
                "sub": "3 variantes por categoría",
            },
            {
                "label": "Páginas scrapeadas",
                "value": str(stats.get("pages", 0)),
                "icon": "public",
                "sub": "Fuentes de Facebook analizadas",
            },
        ],
    )


def _render_reliability_alert(report: ReliabilityReport) -> None:
    """Render the Regla 1 alert with semantic colors."""
    alert_cls = (
        "enola-alert enola-alert--critica"
        if report.nivel == "critica"
        else "enola-alert enola-alert--preventiva"
        if report.nivel == "preventiva"
        else "enola-alert enola-alert--ok"
    )
    icon_name = (
        "report"
        if report.nivel == "ok"
        else "priority_high"
        if report.nivel == "preventiva"
        else "error"
    )
    icon_color = theme.reliability_color(report.nivel)

    with ui.element("div").classes(alert_cls):
        with ui.element("div").style(
            "width: 36px; height: 36px; border-radius: 50%; "
            f"background: {icon_color}1f; color: {icon_color}; "
            "display: flex; align-items: center; justify-content: center; flex-shrink: 0;"
        ):
            ui.icon(icon_name, size="20px")
        with ui.column().classes("gap-0 flex-1"):
            ui.label(f"Nivel de alerta: {report.nivel.upper()}").classes(
                "text-xs uppercase font-semibold tracking-widest"
            ).style(f"color: {icon_color};")
            ui.label(report.mensaje).classes("text-sm leading-snug").style(
                "color: var(--enola-charcoal);"
            )


def _render_basura_breakdown(report: ReliabilityReport) -> None:
    """Render the basura-digital codigos breakdown as small badges."""
    if not report.detalle_basura_codigos:
        return
    with ui.element("div").classes("w-full mt-4"):
        ui.label("Detalle de códigos de basura digital").classes(
            "text-xs uppercase tracking-widest font-semibold"
        ).style("color: var(--enola-brass-deep); margin-bottom: 0.5rem;")
        with ui.row().classes("gap-2 flex-wrap"):
            for codigo, cant in sorted(
                report.detalle_basura_codigos.items(),
                key=lambda x: -x[1],
            ):
                with ui.element("div").style(
                    "padding: 0.35rem 0.75rem; border-radius: 999px; "
                    "background: rgba(192, 132, 151, 0.12); "
                    "border: 1px solid rgba(192, 132, 151, 0.3); "
                    "color: var(--enola-plum); "
                    "font-family: var(--enola-font-mono); "
                    "font-size: 0.75rem;"
                ):
                    ui.label(f"{codigo}: {cant}")


def render_reliability_section(report: ReliabilityReport) -> None:
    """Render the Regla 1 reliability section (3 mini KPIs + alert)."""
    section_header(
        "Regla 1",
        "Reporte de fiabilidad",
        subtitle=(
            "Detección de valores perdidos (CÓDIGO 99) y violencia común "
            "sin sesgo de género. Hernández-Sampieri y Mendoza Torres (2018)."
        ),
    )

    kpi_grid(
        3,
        [
            {
                "label": "Total de análisis",
                "value": f"{report.total:,}".replace(",", "."),
                "icon": "database",
                "sub": "Filas evaluadas",
            },
            {
                "label": "% Basura digital (CÓDIGO 99)",
                "value": f"{report.pct_basura}%",
                "icon": "delete_sweep",
                "accent": theme.RELIABILITY_CRITICA,
                "sub": f"{report.n_basura_digital} de {report.total} registros",
            },
            {
                "label": "% Violencia común (sin sesgo)",
                "value": f"{report.pct_violencia_comun}%",
                "icon": "block",
                "accent": theme.CHARCOAL_LIGHT,
                "sub": f"{report.n_violencia_comun} de {report.total} registros",
            },
        ],
    )

    with ui.element("div").classes("w-full mt-6"):
        _render_reliability_alert(report)
        _render_basura_breakdown(report)


def render_intro_quote() -> None:
    """Editorial quote — the detective-girl touch."""
    with ui.element("div").style(
        "padding: 1.25rem 1.5rem; border-radius: 0.875rem; "
        "background: rgba(191, 161, 129, 0.10); "
        "border-left: 3px solid var(--enola-brass); "
        "font-family: var(--enola-font-display); "
        "font-style: italic; font-size: 1.05rem; "
        "color: var(--enola-charcoal); "
        "line-height: 1.5; "
        "max-width: 70ch;"
    ):
        ui.label(
            "\u201cLa violencia de género digital no se mide solo en likes "
            "y reportes: se mide en la intención pragmática del discurso, "
            "en quién ataca, por qué y con qué palabras.\u201d"
        )
        ui.label("— Marco metodológico, Regla de exclusión").classes(
            "text-xs not-italic mt-2"
        ).style("color: var(--enola-charcoal-light); letter-spacing: 0.05em;")


# --- Page entry --------------------------------------------------------------


def render_inicio_body() -> None:
    """Render the Inicio page body. Called by the page_scaffold wrapper."""
    with ui.column().classes("w-full gap-8"):
        render_hero()

        try:
            analysis, adjustment, reliability = _load_data()
        except Exception as exc:  # pragma: no cover - DB may not be seeded
            logger.exception("Failed to load landing data: %s", exc)
            ui.label(
                "No se pudo cargar la base de datos. Asegurate de que el "
                "scraper haya corrido al menos una vez."
            ).classes("text-base")
            return

        # Row 1 — KPI grid
        section_header(
            "Resumen",
            "Indicadores clave del análisis",
            subtitle=("Métricas principales calculadas sobre el dataset ajustado por humanos."),
        )
        render_kpis(analysis, adjustment)

        # Editorial interlude
        render_intro_quote()

        # Regla 1 reliability section
        render_reliability_section(reliability)

        # Friendly CTA pointing to the rest of the app
        with ui.element("div").style(
            "padding: 1.5rem 2rem; border-radius: 1rem; "
            "background: linear-gradient(135deg, rgba(107, 78, 113, 0.06), "
            "rgba(192, 132, 151, 0.08)); "
            "border: 1px solid rgba(191, 161, 129, 0.25); "
            "display: flex; align-items: center; justify-content: space-between; "
            "gap: 1.5rem; flex-wrap: wrap;"
        ):
            with ui.column().classes("gap-1"):
                ui.label("¿Querés profundizar?").classes("enola-display text-lg")
                ui.label(
                    "Explorá las pestañas del menú lateral: estadística "
                    "completa, métricas de la IA, inspector por contenido "
                    "y la base de conocimiento."
                ).classes("text-sm").style("color: var(--enola-charcoal-light); max-width: 60ch;")
            with ui.row().classes("gap-2"):
                ui.button(
                    "Estadística",
                    icon="insights",
                    on_click=lambda: ui.navigate.to("/estadistica"),
                ).props("color=primary outline")
                ui.button(
                    "IA & Confiabilidad",
                    icon="psychology",
                    on_click=lambda: ui.navigate.to("/ia"),
                ).props("color=primary")
