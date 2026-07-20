"""Inline-edit cell component for the validation listing.

Renders a cell that toggles between a read-only label and an editable
``ui.select`` when clicked. The cell captures a single
``(categoria, dimension)`` override — for multi-label feedback the
reviewer still has to open the full modal.

Pure NiceGUI on top of :func:`src.ui.validacion.categoria_choices` /
:func:`dimension_options_for` so the dropdowns use the same canonical
set as the modal form.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from src.analyzer.category_mapping import (
    SUBDIMENSIONES_POR_CATEGORIA,
    Severity,
)
from src.ui import validacion as val_helpers
from src.ui.nicegui_app import theme
from src.ui.utils import label_for


def render_inline_edit_cell(
    *,
    row: dict,
    on_save: Callable[[str, str, str], None],
) -> None:
    """Render an inline-editable categoría cell.

    The cell starts in *display* mode showing the AI's category. Clicking
    it switches to *edit* mode with a ``ui.select``. Selecting a value
    invokes ``on_save(categoria, dimension, severidad)`` where
    ``dimension`` and ``severidad`` default to the existing row values.

    Args:
        row: The analysis row dict (must have ``categoria``,
            ``dimension``, ``severidad``).
        on_save: Callback fired with the new category tuple.
    """
    cell = ui.element("td").style(
        "padding: 0.3rem 0.5rem; text-align: left; vertical-align: middle;"
    )
    with cell:
        container = ui.element("div")

        current_cat = str(row.get("categoria") or "") or "—"
        current_dim = str(row.get("dimension") or "") or "—"
        current_sev = str(row.get("severidad") or "ninguna").lower()

        def _render_display_mode() -> None:
            container.clear()
            with container:
                with ui.row().classes("items-center gap-1"):
                    ui.label(label_for(current_cat)).classes("text-sm font-medium").style(
                        f"color: {theme.PLUM};"
                    )
                    ui.icon(
                        "edit",
                        size="14px",
                    ).style(f"color: {theme.CHARCOAL_LIGHT}; opacity: 0.55;")

                def _enter_edit() -> None:
                    _render_edit_mode()

                ui.tooltip("Click para editar").classes("text-xs")
                cell.on("click", _enter_edit)

        def _render_edit_mode() -> None:
            container.clear()
            with container:
                with ui.row().classes("items-center gap-1 no-wrap"):
                    cat_select = (
                        ui.select(
                            options=val_helpers.categoria_choices(),
                            value=current_cat,
                        )
                        .props("outlined dense")
                        .classes("min-w-56")
                    )

                    dim_select = (
                        ui.select(
                            options=val_helpers.dimension_options_for(current_cat),
                            value=current_dim,
                        )
                        .props("outlined dense")
                        .classes("min-w-40")
                    )

                    sev_select = (
                        ui.select(
                            options=[s.value for s in Severity],
                            value=current_sev
                            if current_sev in {s.value for s in Severity}
                            else "ninguna",
                        )
                        .props("outlined dense")
                        .classes("w-24")
                    )

                    def _on_cat_change(e) -> None:
                        new_cat = e.value if e.value is not None else ""
                        valid_dims = SUBDIMENSIONES_POR_CATEGORIA.get(new_cat, [])
                        dim_select.set_options(val_helpers.dimension_options_for(new_cat))
                        if dim_select.value and dim_select.value not in valid_dims:
                            dim_select.set_value("")

                    cat_select.on_value_change(_on_cat_change)

                    def _confirm() -> None:
                        new_cat = cat_select.value or ""
                        new_dim = dim_select.value or ""
                        new_sev = sev_select.value or "ninguna"
                        if not new_cat:
                            ui.notify("Categoría requerida", type="warning")
                            return
                        if new_dim and not val_helpers.is_valid_categoria_for_dimension(
                            new_cat, new_dim
                        ):
                            ui.notify(
                                f"La dimensión {new_dim} no corresponde a {new_cat}",
                                type="warning",
                            )
                            return
                        # Mutate the row in place — the page reads
                        # these values on save.
                        row["categoria"] = new_cat
                        row["dimension"] = new_dim or None
                        row["severidad"] = new_sev
                        nonlocal current_cat, current_dim, current_sev
                        current_cat = new_cat
                        current_dim = new_dim or "—"
                        current_sev = new_sev
                        on_save(new_cat, new_dim or "", new_sev)
                        _render_display_mode()

                    def _cancel() -> None:
                        _render_display_mode()

                    ui.button(
                        icon="check",
                        on_click=_confirm,
                    ).props("flat dense round size=sm color=positive")

                    ui.button(
                        icon="close",
                        on_click=_cancel,
                    ).props("flat dense round size=sm")

        _render_display_mode()


__all__ = ["render_inline_edit_cell"]
