"""Editor Markdown — CRUD sobre ``knowledge/*.md`` (admin-only).

Permite a los administradores ver el árbol de archivos ``.md`` de la
base de conocimiento, abrir uno para editarlo en vivo (con preview
markdown en tiempo real), crear archivos nuevos y borrar los
existentes. Respaldado por :mod:`src.knowledge_base.knowledge_files`,
que valida rutas y crea un ``.bak`` automático en cada edición.

Layout: dos columnas — izquierda lista de archivos + búsqueda, derecha
editor (``textarea`` monoespaciado) y preview renderizado con
``ui.markdown``. La barra superior tiene los CTAs de guardar /
descartar / crear / borrar.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from nicegui import ui

from src.knowledge_base import knowledge_files as kf
from src.ui.nicegui_app import auth, theme
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)


def _new_state() -> dict:
    return {
        "files": [],
        "selected": None,
        "original_content": "",
        "editor_content": "",
        "search": "",
    }


def _render_body() -> None:
    if not auth.current_user():
        ui.navigate.to("/login")
        return

    section_header(
        "Editor Markdown",
        "Modificá los archivos .md del directorio knowledge/",
        subtitle=(
            "Editor con preview en vivo. Cada guardado crea un backup "
            "automático (.bak). Solo accesible para administradores."
        ),
    )

    state = _new_state()
    _reload_files(state)

    # Containers referenced by closures — declared up-front so closures
    # can refresh them without forward references.
    tree_container: dict = {"el": None, "refresh": None}
    editor_container: dict = {"el": None, "render": None}

    def _refresh_all() -> None:
        """Refresh both the file tree and the editor pane."""
        if tree_container["refresh"] is not None:
            tree_container["refresh"]()
        if editor_container["render"] is not None:
            editor_container["render"]()

    # --- Toolbar ---
    with ui.row().classes("items-center gap-3 mt-2 flex-wrap"):
        ui.button(
            "🆕 Crear archivo",
            icon="note_add",
            on_click=lambda: _open_create_dialog(state, _refresh_all),
        ).props("color=primary unelevated").style("font-weight: 600;")
        ui.button(
            "🔄 Refrescar árbol",
            icon="refresh",
            on_click=lambda: _refresh_all(),
        ).props("outline color=primary")

    with (
        ui.element("div")
        .classes("w-full grid gap-4 mt-4")
        .style("grid-template-columns: minmax(260px, 320px) 1fr;")
    ):
        # --- LEFT: file tree ---
        with (
            ui.element("div")
            .classes("enola-panel")
            .style("padding: 1rem 1.25rem; max-height: 70vh; overflow-y: auto;")
        ):
            search_input = (
                ui.input(label="Buscar", placeholder="nombre.md")
                .props("outlined dense clearable")
                .classes("w-full")
            )

            @ui.refreshable
            def _render_tree() -> None:
                files = state["files"]
                if not files:
                    ui.label("No hay archivos .md en knowledge/.").classes("text-sm italic").style(
                        "color: var(--enola-charcoal-light);"
                    )
                    return
                q = (state.get("search") or "").strip().lower()
                filtered = [f for f in files if q in f.rel_path.lower()] if q else files

                root = kf._resolve_root(None)
                grouped: dict[str, list] = {}
                for entry in filtered:
                    try:
                        folder_label = entry.abs_path.parent.relative_to(root).as_posix()
                    except ValueError:
                        folder_label = "(raíz)"
                    if folder_label == ".":
                        folder_label = "(raíz)"
                    grouped.setdefault(folder_label, []).append(entry)

                for folder in sorted(grouped.keys()):
                    ui.label(f"📁 {folder}").classes("text-xs uppercase font-semibold mt-2").style(
                        "color: var(--enola-brass-deep); letter-spacing: 0.12em;"
                    )
                    for entry in grouped[folder]:
                        is_active = state["selected"] == entry.rel_path
                        with (
                            ui.element("div")
                            .classes(
                                "enola-file-row" + (" enola-file-row--active" if is_active else "")
                            )
                            .props("clickable")
                            .style(
                                "padding: 0.5rem 0.75rem; margin-top: 0.25rem; "
                                "border-radius: 0.5rem; cursor: pointer; "
                                "display: flex; justify-content: space-between; "
                                "align-items: center; gap: 0.5rem; "
                                "background: "
                                + ("rgba(107, 78, 113, 0.10)" if is_active else "transparent")
                                + ";"
                            )
                            .on(
                                "click",
                                lambda e, r=entry.rel_path: _select_file(state, r, _refresh_all),
                            )
                        ):
                            with ui.column().classes("gap-0 flex-1"):
                                ui.label(entry.rel_path).classes("text-sm font-medium").style(
                                    "color: "
                                    + (theme.PLUM if is_active else "var(--enola-charcoal)")
                                    + ";"
                                )
                                ui.label(
                                    f"{entry.size_bytes} B · {entry.modified_at[:16]}"
                                ).classes("text-xs").style("color: var(--enola-charcoal-light);")

            def _on_search(e) -> None:
                state["search"] = e.value or ""
                _render_tree.refresh()

            search_input.on_value_change(_on_search)
            tree_container["refresh"] = _render_tree.refresh
            _render_tree()

        # --- RIGHT: editor + preview ---
        editor_box = (
            ui.element("div")
            .classes("enola-panel")
            .style("padding: 1rem 1.5rem; min-height: 70vh;")
        )
        editor_container["el"] = editor_box

        def _render_editor_pane() -> None:
            editor_box.clear()
            with editor_box:
                _render_editor(state, _refresh_all)

        editor_container["render"] = _render_editor_pane
        _render_editor_pane()


def _reload_files(state: dict) -> None:
    try:
        state["files"] = kf.list_markdown_files()
    except Exception as exc:  # noqa: BLE001
        logger.exception("No se pudo listar knowledge/")
        state["files"] = []
        ui.notify(f"Error listando archivos: {exc}", type="negative", position="top")


def _select_file(state: dict, rel_path: str, refresh_all: Callable[[], None]) -> None:
    if state["selected"] and state["editor_content"] != state["original_content"]:
        if not _confirm_discard():
            return
    try:
        content = kf.read_markdown_file(rel_path)
    except Exception as exc:  # noqa: BLE001
        ui.notify(f"No se pudo abrir '{rel_path}': {exc}", type="negative", position="top")
        return
    state["selected"] = rel_path
    state["original_content"] = content
    state["editor_content"] = content
    refresh_all()


def _confirm_discard() -> bool:
    """Avisar al usuario y bloquear el cambio hasta que guarde o descarte."""
    ui.notify(
        "Tenés cambios sin guardar. Guardá o descartá antes de cambiar de archivo.",
        type="warning",
        position="top",
    )
    return False


def _render_editor(state: dict, refresh_all: Callable[[], None]) -> None:
    """Render the right pane: header + editor + live preview."""
    if not state["selected"]:
        with ui.element("div").style(
            "padding: 3rem 2rem; text-align: center; "
            "color: var(--enola-charcoal-light); "
            "background: rgba(191, 161, 129, 0.06); "
            "border-radius: 0.75rem; border: 1px dashed rgba(191, 161, 129, 0.35);"
        ):
            ui.icon("menu_book", size="40px").style(f"color: {theme.PLUM}; margin-bottom: 0.75rem;")
            ui.label("Seleccioná un archivo de la izquierda para editarlo.").classes(
                "text-sm"
            ).style("font-style: italic;")
        return

    # --- Header (filename + CTAs) ---
    with ui.row().classes("w-full items-center justify-between flex-wrap gap-2"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("description", color=theme.PLUM)
            ui.label(state["selected"]).classes("text-sm font-semibold").style(
                "color: var(--enola-plum); letter-spacing: -0.01em;"
            )

        status_label = (
            ui.label("")
            .classes("text-xs")
            .style("color: var(--enola-charcoal-light); font-style: italic;")
        )

        save_btn = (
            ui.button(
                "💾 Guardar",
                icon="save",
                on_click=lambda: _save(state, refresh_all, _show_save_buttons_cb),
            )
            .props("color=primary unelevated")
            .style("font-weight: 600;")
        )
        discard_btn = ui.button(
            "↶ Descartar",
            icon="undo",
            on_click=lambda: _discard(state, _show_save_buttons_cb),
        ).props("outline color=primary")
        ui.button(
            "🗑️ Borrar",
            icon="delete",
            on_click=lambda: _open_delete_dialog(state, refresh_all),
        ).props("outline color=negative")

    def _show_save_buttons_cb() -> None:
        dirty = state["editor_content"] != state["original_content"]
        save_btn.enabled = dirty
        discard_btn.enabled = dirty
        if dirty:
            status_label.text = "✏️ Cambios sin guardar."
        else:
            status_label.text = f"✅ {state['selected']} (sin cambios)"

    _show_save_buttons_cb()

    # --- Editor + preview split ---
    with (
        ui.element("div").classes("w-full grid gap-3 mt-3").style("grid-template-columns: 1fr 1fr;")
    ):
        editor = (
            ui.textarea(value=state["editor_content"])
            .props("outlined dense autogrow")
            .classes("w-full")
            .style(
                "min-height: 60vh; font-family: var(--enola-font-mono); "
                "font-size: 0.85rem; line-height: 1.55;"
            )
        )
        preview_box = ui.element("div").style(
            "padding: 1rem 1.25rem; border: 1px solid rgba(191, 161, 129, 0.30); "
            "border-radius: 0.5rem; background: rgba(255, 255, 255, 0.50); "
            "min-height: 60vh; overflow-y: auto; max-height: 70vh;"
        )

        def _render_preview() -> None:
            preview_box.clear()
            with preview_box:
                if state["editor_content"].strip():
                    ui.markdown(state["editor_content"]).classes("enola-markdown")
                else:
                    ui.label("(vacío)").classes("text-sm italic").style(
                        "color: var(--enola-charcoal-light);"
                    )

        def _on_change(e) -> None:
            state["editor_content"] = e.value or ""
            _render_preview()
            _show_save_buttons_cb()

        editor.on_value_change(_on_change)
        _render_preview()


def _save(state: dict, refresh_all: Callable[[], None], show_save_cb) -> None:
    rel = state["selected"]
    if not rel:
        return
    try:
        kf.write_markdown_file(rel, state["editor_content"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Save falló para %s", rel)
        ui.notify(f"Error al guardar: {exc}", type="negative", position="top")
        return
    state["original_content"] = state["editor_content"]
    ui.notify(f"✅ Guardado: {rel}", type="positive", position="top")
    refresh_all()
    show_save_cb()


def _discard(state: dict, show_save_cb) -> None:
    state["editor_content"] = state["original_content"]
    ui.notify("Cambios descartados.", type="info", position="top")
    show_save_cb()


def _open_create_dialog(state: dict, refresh_all: Callable[[], None]) -> None:
    with (
        ui.dialog() as dialog,
        ui.card().style(
            "min-width: 420px; padding: 1.5rem;background: var(--enola-cream); border-radius: 1rem;"
        ),
    ):
        ui.label("Crear archivo .md").classes("text-base font-semibold enola-display").style(
            "color: var(--enola-plum);"
        )
        ui.label(
            "Podés usar una ruta con subcarpetas (p.ej. "
            "`glosario/nuevo-termino.md`) o un nombre simple."
        ).classes("text-xs mt-1").style("color: var(--enola-charcoal-light);")
        name_input = (
            ui.input(
                label="Ruta relativa",
                placeholder="glosario/nuevo.md",
            )
            .props("outlined dense")
            .classes("w-full mt-3")
        )
        content_input = (
            ui.textarea(label="Contenido inicial (opcional)")
            .props("outlined dense")
            .classes("w-full mt-2")
            .style("min-height: 140px; font-family: var(--enola-font-mono);")
        )

        def _do_create() -> None:
            rel = (name_input.value or "").strip()
            if not rel:
                ui.notify("Indicá un nombre de archivo.", type="warning", position="top")
                return
            try:
                kf.create_markdown_file(rel, content_input.value or "")
            except Exception as exc:  # noqa: BLE001
                ui.notify(f"No se pudo crear: {exc}", type="negative", position="top")
                return
            ui.notify(f"✅ Creado: {rel}", type="positive", position="top")
            _reload_files(state)
            state["selected"] = rel
            state["original_content"] = content_input.value or ""
            state["editor_content"] = content_input.value or ""
            dialog.close()
            refresh_all()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancelar", on_click=dialog.close).props("flat color=primary")
            ui.button(
                "Crear",
                icon="add",
                on_click=_do_create,
            ).props("color=primary unelevated")

    dialog.open()


def _open_delete_dialog(state: dict, refresh_all: Callable[[], None]) -> None:
    rel = state["selected"]
    if not rel:
        return
    with (
        ui.dialog() as dialog,
        ui.card().style(
            "min-width: 380px; padding: 1.5rem;background: var(--enola-cream); border-radius: 1rem;"
        ),
    ):
        ui.label(f"¿Borrar '{rel}'?").classes("text-base font-semibold enola-display").style(
            "color: var(--enola-plum);"
        )
        ui.label(
            "Esta acción no se puede deshacer (queda un .bak por si "
            "necesitás recuperarlo manualmente)."
        ).classes("text-sm mt-2").style("color: var(--enola-charcoal); line-height: 1.5;")

        def _do_delete() -> None:
            try:
                kf.delete_markdown_file(rel)
            except Exception as exc:  # noqa: BLE001
                ui.notify(f"No se pudo borrar: {exc}", type="negative", position="top")
                return
            ui.notify(f"🗑️ Borrado: {rel}", type="positive", position="top")
            state["selected"] = None
            state["original_content"] = ""
            state["editor_content"] = ""
            _reload_files(state)
            dialog.close()
            refresh_all()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancelar", on_click=dialog.close).props("flat color=primary")
            ui.button(
                "Sí, borrar",
                icon="delete_forever",
                on_click=_do_delete,
            ).props("color=negative unelevated")

    dialog.open()


@ui.page("/conocimiento/editor")
def page_conocimiento_editor() -> None:
    """Editor Markdown — protegido con ``require_admin``."""
    if not auth.require_admin():
        return
    page_scaffold(
        "Editor Markdown",
        subtitle="Modificar archivos .md de knowledge/",
        current_path="/conocimiento/editor",
        body=_render_body,
    )


__all__ = ["page_conocimiento_editor"]
