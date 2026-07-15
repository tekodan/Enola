"""Cargar conocimiento — upload de documentos a ChromaDB (admin-only).

Migra la pestaña **📤 Cargar documentos** del Streamlit
``src/ui/app.py`` a NiceGUI. Protegida por :func:`auth.require_admin`
porque poblar/limpiar la colección afecta al RAGClassifier end-to-end.

Funcionalidades expuestas:

* Métricas de la colección (cantidad de documentos, persistencia).
* Carga simultánea de varios archivos (``.md`` / ``.txt`` / ``.pdf``)
  con preview del contenido antes de subir.
* Tags opcionales y modo "reemplazar" (borra chunks previos del mismo
  ``source`` antes de insertar).
* Botón de reseteo (vacía la colección).
* Resumen final de la operación con chunks agregados y total actual.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from nicegui import ui

from src.config.settings import get_settings
from src.knowledge_base.pdf_processor import PDFProcessor
from src.knowledge_base.text_processor import process_text
from src.knowledge_base.vector_store import get_vector_store
from src.ui.nicegui_app import auth, theme
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf"}
MAX_FILE_SIZE_MB = 20


def _collection_count() -> int:
    """Devolver la cantidad actual de chunks en la colección."""
    try:
        store = get_vector_store(
            persist_directory=_settings().knowledge_base.persist_directory,
            collection_name=_settings().knowledge_base.collection_name,
        )
        store.create_collection()
        return int(store.get_collection_stats().get("count", 0))
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo leer el conteo de la colección")
        return 0


def _settings():
    return get_settings()


def _render_body() -> None:
    user = auth.current_user()
    if not user:
        ui.navigate.to("/login")
        return

    settings = _settings()
    store = get_vector_store(
        persist_directory=settings.knowledge_base.persist_directory,
        collection_name=settings.knowledge_base.collection_name,
    )

    section_header(
        "Cargar conocimiento",
        "Indexá documentos en ChromaDB",
        subtitle=(
            "Subí archivos Markdown, PDF o texto plano con marcos "
            "teóricos sobre violencia de género. El clasificador RAG "
            "los usa como contexto en cada clasificación."
        ),
    )

    # --- KPIs / estado ---
    with (
        ui.element("div")
        .classes("enola-panel enola-fade-in")
        .style(
            "display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); "
            "gap: 1rem; padding: 1.25rem 1.5rem;"
        )
    ):
        count_label = _kpi_tile("📦", "Documentos", "—", "en la colección")
        _kpi_tile(
            "💾",
            "Persistencia",
            settings.knowledge_base.persist_directory,
            "ChromaDB",
        )
        _kpi_tile(
            "⚙️",
            "Chunk size",
            f"{settings.knowledge_base.chunk_size} / {settings.knowledge_base.chunk_overlap}",
            "overlap",
        )

    def _refresh_count() -> None:
        count_label.text = str(_collection_count())
        _refresh_count.refresh_count = _collection_count()  # type: ignore[attr-defined]

    _refresh_count()

    # --- Action toolbar ---
    with ui.row().classes("items-center gap-3 mt-3 flex-wrap"):
        replace_mode = (
            ui.checkbox(
                "Reemplazar documentos existentes",
                value=False,
            )
            .props("dense")
            .style("color: var(--enola-charcoal);")
        )
        tags_input = (
            ui.input(
                label="Tags (opcional)",
                placeholder="ley, violencia, psicológica",
            )
            .props("outlined dense")
            .classes("min-w-[260px]")
        )
        ui.button(
            "🔄 Refrescar contador",
            icon="refresh",
            on_click=_refresh_count,
        ).props("outline color=primary dense")
        ui.button(
            "🗑️ Vaciar colección",
            icon="delete_sweep",
            on_click=lambda: _confirm_reset(store, _refresh_count),
        ).props("outline color=negative dense")

    # --- Uploader ---
    state: dict = {
        "files": [],  # list of dicts {name, content, size}
        "last_summary": None,
    }

    def _on_upload(e) -> None:
        # NiceGUI upload handler signature: e.name, e.content (bytes)
        name = getattr(e, " name", "?")
        content = getattr(e, "content", b"")
        size = len(content) if content else 0
        if size > MAX_FILE_SIZE_MB * 1024 * 1024:
            ui.notify(
                f"'{name}' excede {MAX_FILE_SIZE_MB} MB — descartado.",
                type="warning",
                position="top",
            )
            return
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            ui.notify(
                f"'{name}' — extensión no soportada ({ext}).",
                type="warning",
                position="top",
            )
            return
        # Decode for preview; for PDFs store raw bytes for later processing.
        try:
            text_preview = (
                content.decode("utf-8", errors="replace") if ext != ".pdf" else "[PDF binario]"
            )
        except Exception:  # noqa: BLE001
            text_preview = "[contenido no legible]"
        state["files"].append(
            {
                "name": name,
                "ext": ext,
                "content": content,
                "size": size,
                "preview": text_preview[:600],
            }
        )
        _render_preview.refresh()

    @ui.refreshable
    def _render_preview() -> None:
        files = state["files"]
        if not files:
            with ui.element("div").style(
                "padding: 1.25rem; border: 1px dashed rgba(191, 161, 129, 0.45); "
                "border-radius: 0.75rem; text-align: center; "
                "color: var(--enola-charcoal-light);"
            ):
                ui.label("📂 Todavía no subiste archivos. Usá el botón de abajo.").classes(
                    "text-sm"
                )
            return
        with ui.element("div").classes("w-full"):
            ui.label(f"Archivos listos para subir: {len(files)}").classes(
                "text-sm font-semibold mt-2"
            ).style("color: var(--enola-plum); letter-spacing: -0.01em;")
            for idx, f in enumerate(files):
                with (
                    ui.element("div")
                    .classes("enola-panel")
                    .style("padding: 1rem 1.25rem; margin-top: 0.5rem;")
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon(
                                "description" if f["ext"] in {".md", ".txt"} else "picture_as_pdf",
                                color=theme.PLUM,
                            )
                            ui.label(f["name"]).classes("text-sm font-semibold")
                            ui.label(f"({f['size'] / 1024:.1f} KB)").classes("text-xs").style(
                                "color: var(--enola-charcoal-light);"
                            )
                        ui.button(
                            "Quitar",
                            icon="close",
                            on_click=lambda i=idx: _remove(i),
                        ).props("flat dense size=sm color=negative")
                    if f["ext"] != ".pdf":
                        with ui.element("pre").style(
                            "background: rgba(191, 161, 129, 0.10); "
                            "padding: 0.75rem; border-radius: 0.5rem; "
                            "font-family: var(--enola-font-mono); font-size: 0.78rem; "
                            "max-height: 220px; overflow: auto; margin-top: 0.5rem;"
                        ):
                            ui.label(f["preview"])

    def _remove(idx: int) -> None:
        if 0 <= idx < len(state["files"]):
            state["files"].pop(idx)
        _render_preview.refresh()

    _render_preview()

    # --- Uploader control ---
    with ui.row().classes("items-center gap-3 mt-4 flex-wrap"):
        ui.upload(
            label="Seleccionar archivos",
            on_upload=_on_upload,
            multiple=True,
            auto_upload=True,
        ).props(f"accept={','.join(ALLOWED_EXTENSIONS)} color=primary outline").classes(
            "min-w-[260px]"
        )

        ui.button(
            "🚀 Subir a ChromaDB",
            icon="cloud_upload",
            on_click=lambda: _do_upload(
                state, replace_mode.value, tags_input.value or "", store, _refresh_count
            ),
        ).props("color=primary unelevated").style(
            f"background: linear-gradient(135deg, {theme.PLUM} 0%, "
            f"{theme.PLUM_DEEP} 100%); color: {theme.CREAM}; font-weight: 600;"
        )

        ui.button(
            "Limpiar selección",
            icon="clear_all",
            on_click=lambda: _clear(state),
        ).props("flat color=primary")

    # --- Result summary ---
    if state["last_summary"]:
        _render_summary(state["last_summary"])

    # --- Footer note ---
    with ui.element("div").style(
        "margin-top: 1.5rem; padding: 1rem 1.25rem; border-radius: 0.625rem; "
        "background: rgba(191, 161, 129, 0.10); "
        "border-left: 3px solid var(--enola-brass);"
    ):
        ui.label(
            "ℹ️ Esta página es exclusiva para administradores. "
            "Los cambios impactan directamente al RAGClassifier — "
            "revisá los chunks antes de indexar."
        ).classes("text-xs").style("color: var(--enola-charcoal); line-height: 1.5;")


def _kpi_tile(icon: str, label: str, value: str, sub: str):
    """Render a single KPI tile and return the value label for updates."""
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
        value_label = (
            ui.label(value)
            .classes("text-lg font-semibold mt-1 enola-display")
            .style("color: var(--enola-plum); line-height: 1.1;")
        )
        ui.label(sub).classes("text-xs").style(
            "color: var(--enola-charcoal-light); letter-spacing: 0.02em;"
        )
    return value_label


def _render_summary(summary: dict) -> None:
    with ui.element("div").style(
        "margin-top: 1rem; padding: 1rem 1.25rem; border-radius: 0.75rem; "
        "background: rgba(107, 78, 113, 0.06); "
        "border-left: 4px solid var(--enola-plum);"
    ):
        ui.label("📋 Resumen de la última operación").classes("text-sm font-semibold").style(
            "color: var(--enola-plum); letter-spacing: -0.01em;"
        )
        for k, v in summary.items():
            ui.label(f"  · {k}: {v}").classes("text-xs").style(
                "color: var(--enola-charcoal); font-family: var(--enola-font-mono);"
            )


def _confirm_reset(store, on_done) -> None:
    """Pop-up de confirmación para vaciar la colección."""
    with (
        ui.dialog() as dialog,
        ui.card().style(
            "min-width: 360px; padding: 1.5rem; "
            "background: var(--enola-cream); border-radius: 1rem;"
        ),
    ):
        ui.label("¿Vaciar la colección de ChromaDB?").classes(
            "text-base font-semibold enola-display"
        ).style("color: var(--enola-plum);")
        ui.label(
            "Esta acción borra todos los chunks vectorizados. "
            "Vas a tener que re-subir la base de conocimiento."
        ).classes("text-sm mt-2").style("color: var(--enola-charcoal); line-height: 1.5;")
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancelar", on_click=dialog.close).props("flat color=primary")
            ui.button(
                "Sí, vaciar",
                icon="delete_forever",
                on_click=lambda: _do_reset(store, dialog, on_done),
            ).props("color=negative unelevated")
    dialog.open()


def _do_reset(store, dialog, on_done) -> None:
    try:
        store.create_collection()
        store.delete_collection()
        ui.notify("Colección borrada", type="positive", position="top")
        on_done()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reset falló")
        ui.notify(f"Error al vaciar: {exc}", type="negative", position="top")
    finally:
        dialog.close()


def _clear(state: dict) -> None:
    state["files"].clear()


def _do_upload(
    state: dict,
    replace: bool,
    tags_raw: str,
    store,
    on_done,
) -> None:
    files = state["files"]
    if not files:
        ui.notify("No hay archivos para subir.", type="warning", position="top")
        return
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

    settings = _settings()
    chunk_size = settings.knowledge_base.chunk_size
    chunk_overlap = settings.knowledge_base.chunk_overlap

    progress = (
        ui.linear_progress(value=0, show_value=False)
        .props("color=primary rounded")
        .style("margin-top: 1rem;")
    )
    status = (
        ui.label("Iniciando...")
        .classes("text-xs mt-1")
        .style("color: var(--enola-charcoal-light);")
    )

    added = 0
    errors: list[str] = []

    for idx, f in enumerate(files):
        status.text = f"Procesando {f['name']} ({idx + 1}/{len(files)})..."
        ext = f["ext"]
        name = f["name"]

        try:
            if replace:
                store.create_collection()
                if store.collection:
                    existing_ids = store.collection.get(where={"source": name})["ids"]
                    if existing_ids:
                        store.collection.delete(ids=existing_ids)

            if ext == ".pdf":
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(f["content"])
                    tmp_path = tmp.name
                try:
                    pdf_proc = PDFProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                    docs = pdf_proc.process_document(tmp_path, source_name=name)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
            else:
                raw = (
                    f["content"].decode("utf-8", errors="replace")
                    if isinstance(f["content"], (bytes, bytearray))
                    else str(f["content"])
                )
                fmt = "md" if ext == ".md" else "txt"
                docs = process_text(
                    content=raw,
                    source=name,
                    file_format=fmt,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )

            if not docs:
                errors.append(f"{name}: sin chunks extraíbles")
                continue

            if tags:
                for doc in docs:
                    doc["metadata"]["tags"] = ",".join(tags)

            store.create_collection()
            store.add_documents(
                documents=[d["text"] for d in docs],
                metadatas=[d["metadata"] for d in docs],
            )
            added += len(docs)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Upload falló para %s", name)
            errors.append(f"{name}: {exc}")
        finally:
            progress.value = (idx + 1) / len(files)

    on_done()
    summary = {
        "archivos_procesados": len(files),
        "chunks_agregados": added,
        "modo": "reemplazar" if replace else "agregar",
        "tags": ", ".join(tags) if tags else "(ninguno)",
        "total_coleccion": _collection_count(),
        "errores": "; ".join(errors) if errors else "(ninguno)",
    }
    state["last_summary"] = summary
    progress.value = 1.0
    status.text = f"✅ {added} chunks agregados de {len(files)} archivos."
    if added > 0:
        ui.notify(
            f"✅ {added} chunks agregados a ChromaDB.",
            type="positive",
            position="top",
        )
    if errors:
        ui.notify(
            f"⚠ {len(errors)} archivo(s) con error.",
            type="warning",
            position="top",
        )
    state["files"].clear()


@ui.page("/conocimiento/cargar")
def page_conocimiento_cargar() -> None:
    """Upload page — protegida con ``require_admin``."""
    if not auth.require_admin():
        return
    page_scaffold(
        "Cargar conocimiento",
        subtitle="Indexar documentos en ChromaDB",
        current_path="/conocimiento/cargar",
        body=_render_body,
    )


__all__ = ["page_conocimiento_cargar"]
