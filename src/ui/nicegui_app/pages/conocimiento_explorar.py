"""Explorar ChromaDB — visualizador de la colección (admin-only).

Migra la pestaña **🔍 Explorar base** del Streamlit ``src/ui/app.py``
a NiceGUI. Permite a los administradores:

* Ver KPIs de la colección (cantidad de chunks, fuentes, formato).
* Buscar por similitud semántica (``vector_store.search``) con un
  número de resultados ajustable (1..20).
* Listar las fuentes indexadas (cuántos chunks por archivo).
* Vista aleatoria / paginada de los chunks existentes.
* Borrado puntual de un chunk por su ID.

Protegida por :func:`auth.require_admin` porque expone los metadatos
internos que usa el RAGClassifier.
"""

from __future__ import annotations

import logging

from nicegui import ui

from src.config.settings import get_settings
from src.knowledge_base.vector_store import get_vector_store
from src.ui.nicegui_app import auth, theme
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)


def _settings():
    return get_settings()


def _store():
    settings = _settings()
    return get_vector_store(
        persist_directory=settings.knowledge_base.persist_directory,
        collection_name=settings.knowledge_base.collection_name,
    )


def _render_body() -> None:
    if not auth.current_user():
        ui.navigate.to("/login")
        return

    section_header(
        "Explorar ChromaDB",
        "Inspección de la colección vectorizada",
        subtitle=(
            "Buscá por similitud semántica, listá fuentes o muestreá "
            "chunks al azar. Los IDs y metadatos que veas acá son los "
            "mismos que el RAGClassifier consume en producción."
        ),
    )

    store = _store()
    try:
        store.create_collection()
        count = int(store.get_collection_stats().get("count", 0))
    except Exception as exc:  # noqa: BLE001
        logger.exception("No se pudo leer la colección")
        ui.label(f"Error al conectar con ChromaDB: {exc}").classes("text-base")
        return

    # --- KPIs ---
    with (
        ui.element("div")
        .classes("enola-panel enola-fade-in")
        .style(
            "display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); "
            "gap: 1rem; padding: 1.25rem 1.5rem;"
        )
    ):
        _kpi_tile("📦", "Total chunks", str(count), "en la colección")
        _kpi_tile(
            "💾",
            "Persistencia",
            _settings().knowledge_base.persist_directory,
            "directorio ChromaDB",
        )
        _kpi_tile("🏷️", "Colección", _settings().knowledge_base.collection_name, "activa")

    if count == 0:
        with ui.element("div").style(
            "padding: 2rem; border-radius: 1rem; "
            "background: rgba(191, 161, 129, 0.08); "
            "border: 1px dashed rgba(191, 161, 129, 0.35); "
            "text-align: center; margin-top: 1rem;"
        ):
            ui.label("La colección está vacía.").classes(
                "text-base font-semibold enola-display"
            ).style("color: var(--enola-plum);")
            ui.label(
                "Pasá por **Cargar conocimiento** para subir los primeros documentos."
            ).classes("text-sm mt-1").style("color: var(--enola-charcoal-light);")
        return

    # --- Search ---
    section_header("Búsqueda semántica", "Consultá la colección por texto libre")
    query = (
        ui.input(
            label="Buscar en la base de conocimiento",
            placeholder="Ej: violencia psicológica, ley 26485, manosfera...",
        )
        .props("outlined dense clearable")
        .classes("w-full")
    )
    n_results = ui.slider(min=1, max=20, value=5).props("label-always color=primary")

    state: dict = {"results": None, "sources": None, "random_sample": None}

    @ui.refreshable
    def _render_results() -> None:
        results = state["results"]
        if results is None:
            return
        if not results:
            ui.label("Sin resultados.").classes("text-sm italic").style(
                "color: var(--enola-charcoal-light);"
            )
            return
        ui.label(f"Se encontraron {len(results)} resultados.").classes(
            "text-sm font-semibold mt-2"
        ).style("color: var(--enola-plum); letter-spacing: -0.01em;")
        for i, r in enumerate(results):
            with (
                ui.element("div")
                .classes("enola-panel")
                .style("padding: 1rem 1.25rem; margin-top: 0.5rem;")
            ):
                with ui.row().classes("w-full items-center justify-between"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("tag", color=theme.PLUM)
                        ui.label(r["metadata"].get("source", "desconocido")).classes(
                            "text-sm font-semibold"
                        )
                        ui.label(f"#{i + 1}").classes("text-xs").style(
                            "color: var(--enola-charcoal-light);"
                        )
                    ui.label(f"distancia: {r['distance']:.4f}").classes("text-xs font-mono").style(
                        "color: var(--enola-brass-deep);"
                    )
                ui.markdown(r["text"]).classes("text-sm mt-2").style(
                    "color: var(--enola-charcoal); line-height: 1.55;"
                )
                ui.label(f"ID: {r['id']}").classes("text-xs mt-2").style(
                    "color: var(--enola-charcoal-light); font-family: var(--enola-font-mono);"
                )
                with ui.expansion("Metadatos", value=False).classes("w-full mt-1"):
                    ui.json(r["metadata"])

    def _do_search() -> None:
        q = (query.value or "").strip()
        if not q:
            ui.notify("Ingresá un texto para buscar.", type="warning", position="top")
            return
        try:
            results = store.search(q, n_results=int(n_results.value))
        except Exception as exc:  # noqa: BLE001
            logger.exception("search falló")
            ui.notify(f"Error al buscar: {exc}", type="negative", position="top")
            return
        state["results"] = results
        _render_results.refresh()

    with ui.row().classes("items-center gap-3 mt-2"):
        ui.button(
            "🔍 Buscar",
            icon="search",
            on_click=_do_search,
        ).props("color=primary unelevated").style("font-weight: 600;")
        ui.button(
            "Limpiar",
            icon="clear",
            on_click=lambda: _clear_results(state, _render_results),
        ).props("flat color=primary")

    _render_results()

    # --- Sources listing ---
    section_header("Fuentes", "Cantidad de chunks por archivo")

    @ui.refreshable
    def _render_sources() -> None:
        sources = state["sources"]
        if sources is None:
            return
        if not sources:
            ui.label("No hay fuentes indexadas.").classes("text-sm").style(
                "color: var(--enola-charcoal-light);"
            )
            return
        rows = sorted(sources.items(), key=lambda kv: (-kv[1], kv[0]))
        with ui.element("div").style(
            "display: grid; grid-template-columns: 1fr auto; gap: 0.25rem 1rem; "
            "padding: 0.75rem 1rem; border-radius: 0.625rem; "
            "background: rgba(191, 161, 129, 0.06);"
        ):
            for src, n in rows:
                ui.label(src).classes("text-sm").style("color: var(--enola-charcoal);")
                ui.label(f"{n} chunks").classes("text-xs font-mono").style(
                    "color: var(--enola-plum); font-weight: 600;"
                )

    def _list_sources() -> None:
        try:
            store.create_collection()
            if store.collection:
                all_data = store.collection.get()
                sources: dict[str, int] = {}
                for meta in all_data["metadatas"]:
                    src = meta.get("source", "desconocido")
                    sources[src] = sources.get(src, 0) + 1
                state["sources"] = sources
                _render_sources.refresh()
            else:
                ui.notify("La colección no está inicializada.", type="warning")
        except Exception as exc:  # noqa: BLE001
            logger.exception("list_sources falló")
            ui.notify(f"Error: {exc}", type="negative", position="top")

    ui.button(
        "📋 Listar fuentes",
        icon="list_alt",
        on_click=_list_sources,
    ).props("outline color=primary").style("font-weight: 500;")

    _render_sources()

    # --- Random sample ---
    section_header("Muestra aleatoria", "Inspeccioná un subconjunto al azar")
    sample_size = ui.slider(min=1, max=20, value=5).props("label-always color=primary")

    @ui.refreshable
    def _render_sample() -> None:
        sample = state["random_sample"]
        if sample is None:
            return
        if not sample["ids"]:
            ui.label("No hay documentos para mostrar.").classes("text-sm").style(
                "color: var(--enola-charcoal-light);"
            )
            return
        for i, doc_id in enumerate(sample["ids"]):
            with (
                ui.element("div")
                .classes("enola-panel")
                .style("padding: 1rem 1.25rem; margin-top: 0.5rem;")
            ):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(f"Documento #{i + 1}").classes("text-sm font-semibold").style(
                        "color: var(--enola-plum);"
                    )
                    ui.label(doc_id).classes("text-xs font-mono").style(
                        "color: var(--enola-charcoal-light);"
                    )
                text = sample["documents"][i]
                ui.markdown(text).classes("text-sm mt-2").style(
                    "color: var(--enola-charcoal); line-height: 1.5;"
                )
                with ui.expansion("Metadatos", value=False).classes("w-full mt-1"):
                    ui.json(sample["metadatas"][i])

    def _do_sample() -> None:
        try:
            store.create_collection()
            if store.collection:
                state["random_sample"] = store.collection.get(limit=int(sample_size.value))
                _render_sample.refresh()
            else:
                ui.notify("La colección no está inicializada.", type="warning")
        except Exception as exc:  # noqa: BLE001
            logger.exception("sample falló")
            ui.notify(f"Error: {exc}", type="negative", position="top")

    with ui.row().classes("items-center gap-3"):
        ui.button(
            "🎲 Generar muestra",
            icon="casino",
            on_click=_do_sample,
        ).props("outline color=primary").style("font-weight: 500;")

    _render_sample()


def _clear_results(state: dict, refreshable) -> None:
    """Limpiar los resultados de búsqueda."""
    state["results"] = None
    refreshable.refresh()


def _kpi_tile(icon: str, label: str, value: str, sub: str) -> None:
    with ui.element("div").style(
        "padding: 0.85rem 1rem; border-radius: 0.75rem; "
        "background: linear-gradient(135deg, rgba(107, 78, 113, 0.05) 0%, "
        "rgba(191, 161, 129, 0.08) 100%); "
        "border: 1px solid rgba(191, 161, 129, 0.20);"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon, size="18px").style(f"color: {theme.PLUM};")
            ui.label(label).classes("text-xs uppercase tracking-wider font-semibold").style(
                "color: var(--enola-brass-deep); letter-spacing: 0.12em;"
            )
        ui.label(value).classes("text-lg font-semibold mt-1 enola-display").style(
            "color: var(--enola-plum); line-height: 1.1;"
        )
        ui.label(sub).classes("text-xs").style(
            "color: var(--enola-charcoal-light); letter-spacing: 0.02em;"
        )


@ui.page("/conocimiento/explorar")
def page_conocimiento_explorar() -> None:
    """Explorador de ChromaDB — protegida con ``require_admin``."""
    if not auth.require_admin():
        return
    page_scaffold(
        "Explorar ChromaDB",
        subtitle="Visualizador de la colección vectorizada",
        current_path="/conocimiento/explorar",
        body=_render_body,
    )


__all__ = ["page_conocimiento_explorar"]
