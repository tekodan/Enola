"""Conocimiento — taxonomía canónica y comunidad.

Página premium con:

* Stats de la base de conocimiento (carpetas, archivos, tamaño).
* Descarga ZIP de la taxonomía canónica (6 categorías, 18
  subdimensiones, glosario de manosfera, etc.).
* Pipeline de la herramienta (scraping → embeddings → clasificación
  → persistencia).
* CTA al repositorio GitHub para colaboración abierta.
"""

from __future__ import annotations

import logging

from nicegui import ui

from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.kpi_card import kpi_grid
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold
from src.ui.utils import (
    GITHUB_FORK_URL,
    GITHUB_REPO_URL,
    build_knowledge_zip,
    knowledge_summary,
    knowledge_zip_filename,
)

logger = logging.getLogger(__name__)


def _render_body() -> None:
    # --- Hero ---
    with ui.element("div").classes("enola-hero"):
        ui.label("TFM 2026 · Universidad de Granada").classes("enola-hero-badge")
        ui.label("Conocimiento & Comunidad").classes("enola-display")
        ui.label(
            "Taxonomía canónica de violencia de género digital y código "
            "abierto para reproducir y extender el análisis."
        )

    # --- Knowledge base KPIs ---
    section_header(
        "Base de conocimiento",
        "Taxonomía canónica (6 categorías, 18 subdimensiones)",
        subtitle=(
            "El sistema RAG indexa esta base en ChromaDB para fundamentar "
            "cada clasificación. La descarga incluye glosario, definiciones "
            "operativas y patrones de la manosfera."
        ),
    )

    try:
        summary = knowledge_summary()
    except Exception as exc:
        logger.exception("Failed to read knowledge dir: %s", exc)
        summary = {"files": 0, "size_bytes": 0}

    size_kb = round((summary.get("size_bytes") or 0) / 1024.0, 1)

    kpi_grid(
        3,
        [
            {
                "label": "Documentos",
                "value": str(summary.get("files", 0)),
                "icon": "description",
                "sub": "Archivos .md indexados",
            },
            {
                "label": "Tamaño total",
                "value": f"{size_kb} KB",
                "icon": "cloud_download",
                "sub": "Base de conocimiento",
            },
            {
                "label": "Categorías",
                "value": "6",
                "icon": "category",
                "accent": theme.PLUM,
                "sub": "Taxonomía cerrada VDG_*",
            },
        ],
    )

    # --- Download ZIP card ---
    with ui.element("div").classes("w-full mt-6"):
        with ui.element("div").style(
            "padding: 2rem 2.5rem; border-radius: 1rem; "
            "background: linear-gradient(135deg, rgba(107, 78, 113, 0.06), "
            "rgba(192, 132, 151, 0.08)); "
            "border: 1px solid rgba(191, 161, 129, 0.35); "
            "display: flex; align-items: center; justify-content: space-between; "
            "gap: 1.5rem; flex-wrap: wrap;"
        ):
            with ui.column().classes("gap-1"):
                ui.label("📥 Descargar taxonomía completa").classes("enola-display text-lg").style(
                    "color: var(--enola-plum);"
                )
                ui.label(
                    "ZIP con los .md de la base de conocimiento (incluye "
                    "glosario de manosfera, definiciones operativas y "
                    "patrones por categoría)."
                ).classes("text-sm").style("color: var(--enola-charcoal-light); max-width: 60ch;")
            try:
                zip_bytes = build_knowledge_zip()
            except Exception as exc:
                logger.exception("Failed to build zip: %s", exc)
                zip_bytes = b""

            if zip_bytes:
                # ui.download() returns None (it's a void command, not a
                # visual element), so we wrap it in a styled button.
                ui.button(
                    "Descargar .zip",
                    icon="download",
                    on_click=lambda: ui.download(
                        zip_bytes,
                        filename=knowledge_zip_filename(),
                        media_type="application/zip",
                    ),
                ).props("color=primary size=lg").style("font-weight: 500;")
            else:
                ui.label("(Directorio knowledge no disponible)").classes("text-sm italic").style(
                    "color: var(--enola-charcoal-light);"
                )

    # --- About the methodology ---
    section_header(
        "Sobre la herramienta",
        "Pipeline del instrumento",
        subtitle=(
            "Cinco etapas desacopladas — cada componente es "
            "independiente y testeable. La metodología sigue a "
            "Hernández-Sampieri y Mendoza Torres (2018)."
        ),
    )

    steps = [
        {
            "n": "1",
            "title": "Scraping",
            "body": (
                "ScrapeGraphAI extrae posts y comentarios de páginas "
                "públicas de Facebook en formato markdown estructurado."
            ),
            "icon": "cloud_circle",
        },
        {
            "n": "2",
            "title": "Preprocesamiento",
            "body": (
                "Limpieza, normalización y segmentación del texto. "
                "Filas vacías o ilegibles se marcan con el sentinel "
                "CÓDIGO 99 (basura digital)."
            ),
            "icon": "cleaning_services",
        },
        {
            "n": "3",
            "title": "Embeddings",
            "body": (
                "nomic-embed-text vectoriza cada texto y ChromaDB indexa "
                "tanto la taxonomía canónica como el feedback humano."
            ),
            "icon": "data_object",
        },
        {
            "n": "4",
            "title": "Clasificación",
            "body": (
                "RAGClassifier (Ollama + LangChain) clasifica contra "
                "6 categorías VDG_* y 18 subdimensiones, con prompt "
                "que incluye el filtro de violencia común."
            ),
            "icon": "psychology",
        },
        {
            "n": "5",
            "title": "Persistencia + métricas",
            "body": (
                "SQLite almacena análisis + feedback. Los módulos "
                "``src/report/`` computan las 6 reglas metodológicas "
                "(frecuencias, moda, crosstabs, matriz de confusión)."
            ),
            "icon": "storage",
        },
    ]

    with ui.column().classes("w-full gap-3"):
        for step in steps:
            with ui.element("div").style(
                "padding: 1.25rem 1.5rem; "
                "border-radius: 0.875rem; "
                "background: var(--enola-cream); "
                "border: 1px solid rgba(191, 161, 129, 0.18); "
                "display: flex; align-items: flex-start; gap: 1.25rem;"
            ):
                # Number badge
                with ui.element("div").style(
                    "width: 56px; height: 56px; border-radius: 50%; "
                    f"background: {theme.PLUM}; color: {theme.CREAM}; "
                    "display: flex; align-items: center; justify-content: center; "
                    "font-family: var(--enola-font-display); "
                    "font-size: 1.5rem; flex-shrink: 0;"
                ):
                    ui.label(step["n"])
                with ui.column().classes("gap-1 flex-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(step["icon"], size="18px").style(f"color: {theme.BRASS_DEEP};")
                        ui.label(step["title"]).classes(
                            "text-base font-semibold enola-display"
                        ).style("color: var(--enola-plum);")
                    ui.label(step["body"]).classes("text-sm leading-relaxed").style(
                        "color: var(--enola-charcoal);"
                    )

    # --- Open source / collaboration ---
    section_header(
        "Comunidad",
        "Código abierto",
        subtitle=(
            "El proyecto es reproducible y extensible. Si trabajás en "
            "investigación de ciberviolencia o querés adaptar la "
            "taxonomía a otro contexto, abrí un issue o fork."
        ),
    )

    with ui.element("div").style(
        "padding: 2rem 2.5rem; border-radius: 1rem; "
        "background: rgba(191, 161, 129, 0.10); "
        "border-left: 3px solid var(--enola-brass);"
    ):
        with ui.column().classes("gap-3"):
            ui.label(
                "Investigación reproducible: stack Python 3.12 + "
                "ScrapeGraphAI + Ollama + ChromaDB + LangChain + SQLite + "
                "Streamlit + NiceGUI + sklearn. Sin dependencias externas "
                "de pago."
            ).classes("text-sm leading-relaxed").style("color: var(--enola-charcoal);")
            ui.label(
                "Stack: · Python 3.12 · ScrapeGraphAI · Ollama · ChromaDB · "
                "LangChain · SQLite · Streamlit · NiceGUI · sklearn · "
                "Plotly"
            ).classes("text-xs").style(
                "color: var(--enola-charcoal-light); font-family: var(--enola-font-mono);"
            )

        with ui.row().classes("gap-3 mt-4 flex-wrap"):
            ui.button(
                "⭐ Ver repo en GitHub",
                icon="star",
                on_click=lambda: ui.navigate.to(GITHUB_REPO_URL, new_tab=True),
            ).props("color=primary outline")
            ui.button(
                "🔀 Fork",
                icon="fork_right",
                on_click=lambda: ui.navigate.to(GITHUB_FORK_URL, new_tab=True),
            ).props("color=primary outline")

    # --- About this app ---
    section_header(
        "Créditos",
        "Investigadora · Tutora",
    )

    with ui.element("div").classes("w-full grid gap-4").style("grid-template-columns: 1fr 1fr;"):
        with ui.element("div").style(
            "padding: 1.5rem 1.75rem; border-radius: 0.875rem; "
            "background: var(--enola-blush); "
            "border-left: 3px solid var(--enola-rose);"
        ):
            ui.label("🔬 Investigadora").classes(
                "text-xs uppercase tracking-widest font-semibold"
            ).style("color: var(--enola-brass-deep); margin-bottom: 0.5rem;")
            ui.label("Kimberly Michell Luna Eraso").classes(
                "text-lg font-semibold enola-display"
            ).style("color: var(--enola-plum);")
            ui.label("TFM · Máster Interuniversitario en Cultura de Paz").classes("text-sm").style(
                "color: var(--enola-charcoal-light); margin-top: 0.5rem;"
            )

        with ui.element("div").style(
            "padding: 1.5rem 1.75rem; border-radius: 0.875rem; "
            "background: rgba(191, 161, 129, 0.10); "
            "border-left: 3px solid var(--enola-brass);"
        ):
            ui.label("🎓 Tutora de proyecto").classes(
                "text-xs uppercase tracking-widest font-semibold"
            ).style("color: var(--enola-brass-deep); margin-bottom: 0.5rem;")
            ui.label("María del Mar García Vita").classes(
                "text-lg font-semibold enola-display"
            ).style("color: var(--enola-plum);")
            ui.label("Universidad de Granada").classes("text-sm").style(
                "color: var(--enola-charcoal-light); margin-top: 0.5rem;"
            )


@ui.page("/conocimiento")
def page_conocimiento() -> None:
    page_scaffold(
        "Conocimiento",
        subtitle="Taxonomía canónica y comunidad",
        current_path="/conocimiento",
        body=_render_body,
    )
