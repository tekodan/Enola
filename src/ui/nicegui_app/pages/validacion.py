"""Validación humana de análisis — página NiceGUI premium.

Replica, con el sistema de design 'Tinta y Rosa', la pestaña Streamlit
``✅ Validación`` de ``src/ui/app.py``. El flujo:

1. KPIs de estado del feedback (totales, acuerdos, correcciones,
   pendientes de indexar).
2. Panel ChromaDB con botón **🚀 Indexar pendientes**.
3. Filtros (tipo / estado / sólo violentos) + lista de análisis.
4. Para cada fila, formulario multi-etiqueta (hasta
   :data:`src.analyzer.category_mapping.MAX_LABELS` categorias) con dos
   acciones:
   * **💾 Guardar** — upsert en SQLite.
   * **💾+🔎 Guardar e indexar** — upsert + push a ChromaDB
     (``feedback_corrections``) si la review fue una corrección
     (``agrees="false"``).

Las correcciones indexadas viven en ChromaDB con metadata de trazabilidad
(``user_id``, ``added_by_username``, ``added_at``) para que el
:class:`~src.analyzer.rag_classifier.RAGClassifier` las recupere como
few-shots y la IA aprenda implícitamente de cada revisión.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from nicegui import ui

from src.analyzer.category_mapping import (
    MAX_LABELS,
    SUBDIMENSIONES_POR_CATEGORIA,
    Severity,
)
from src.config.settings import get_settings
from src.knowledge_base.feedback_store import get_feedback_store
from src.storage import get_database
from src.ui import validacion as val_helpers
from src.ui.adjusted_report import build_adjusted_analysis
from src.ui.nicegui_app import auth, theme
from src.ui.nicegui_app.components.kpi_card import kpi_grid
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold
from src.ui.utils import label_for

logger = logging.getLogger(__name__)


# --- Page entry --------------------------------------------------------------


@ui.page("/validacion")
def page_validacion() -> None:
    """Validation tab — replaces the Streamlit ``✅ Validación`` page."""
    page_scaffold(
        "Validación humana",
        subtitle=(
            "Revisá los análisis y empujá correcciones a ChromaDB para "
            "que la IA aprenda de los errores confirmados."
        ),
        current_path="/validacion",
        body=_render_body,
    )


# --- Data loading -----------------------------------------------------------


def _load_data() -> tuple[list[dict], dict[str, str]]:
    """Read analyses + feedback + posts-text-lookup from the database."""
    db = get_database()
    raw_analysis = db.get_analysis_results()
    feedback_rows = db.list_feedback()
    analysis = build_adjusted_analysis(raw_analysis, feedback_rows)
    posts = db.get_posts(limit=5000)

    text_by_id: dict[str, str] = {}
    for p in posts or []:
        pid = p.get("id")
        if pid is not None:
            text_by_id[pid] = p.get("text") or ""
    return analysis, text_by_id


def _feedback_store():
    """Return a configured :class:`FeedbackStore` (settings-based)."""
    settings = get_settings()
    return get_feedback_store(
        persist_directory=settings.knowledge_base.persist_directory,
        collection_name=settings.knowledge_base.feedback_collection_name,
    )


# --- KPI + ChromaDB panels --------------------------------------------------


def _render_kpis(analysis: list[dict]) -> None:
    db = get_database()
    stats = db.get_stats()
    n_total = stats.get("feedback_count", 0)
    n_agree = stats.get("feedback_agreement_count", 0)
    n_disagree = stats.get("feedback_disagreement_count", 0)
    n_pending = stats.get("feedback_pending_index_count", 0)

    n_pending_rows = sum(
        1
        for a in analysis
        if a.get("tiene_violencia") in ("true", "false") and not a.get("has_feedback")
    )

    try:
        n_indexed = _feedback_store().get_count()
    except Exception:  # noqa: BLE001
        n_indexed = 0

    kpi_grid(
        5,
        [
            {
                "label": "Análisis pendientes",
                "value": str(n_pending_rows),
                "icon": "pending_actions",
                "sub": "Sin feedback aún",
            },
            {
                "label": "Total revisiones",
                "value": str(n_total),
                "icon": "task_alt",
                "sub": f"{n_agree} acuerdo · {n_disagree} corregidas",
            },
            {
                "label": "Acuerdo",
                "value": str(n_agree),
                "icon": "thumb_up",
                "accent": theme.RELIABILITY_OK,
            },
            {
                "label": "Corregidas",
                "value": str(n_disagree),
                "icon": "edit_note",
                "accent": theme.BRASS_DEEP,
            },
            {
                "label": "Indexadas en ChromaDB",
                "value": str(n_indexed),
                "icon": "search",
                "sub": (f"{n_pending} pendientes" if n_pending else "Todo indexado"),
            },
        ],
    )


def _render_chromadb_panel() -> None:
    section_header(
        "ChromaDB",
        "Colección `feedback_corrections`",
        subtitle=(
            "Push en lote de las correcciones confirmadas para que el "
            "RAGClassifier las inyecte como few-shots en el prompt."
        ),
    )
    fb_store = _feedback_store()
    try:
        n_total = fb_store.get_count()
    except Exception:  # noqa: BLE001
        n_total = 0
    ui.label(f"Correcciones indexadas actualmente: **{n_total}**").classes("text-sm")

    status = ui.column().classes("w-full mt-2")

    def _run_index() -> None:
        status.clear()
        with status:
            ui.label("Indexando…").classes("text-sm enola-display")
        db = get_database()
        pending = db.list_feedback(only_pending_index=True)
        if not pending:
            with status:
                status.clear()
                ui.label("No hay correcciones pendientes de indexar.").classes("text-sm")
            return
        ok = 0
        errors: list[str] = []
        # Index sequentially to keep ChromaDB thread-safety intact.
        for p in pending:
            user_obj = {}
            uid = p.get("reviewer_user_id")
            if uid:
                u = db.find_user_by_id(int(uid))
                if u:
                    user_obj = u
            try:
                original_text = p.get("text_snapshot") or db.get_original_text(
                    p.get("content_type") or "post",
                    p.get("content_id") or "",
                )
                if not original_text:
                    continue
                analysis_row = db.get_analysis_result_by_content(
                    p.get("content_type") or "post",
                    p.get("content_id") or "",
                )
                original_cat = (analysis_row or {}).get("categoria")
                cid = fb_store.add_correction(
                    feedback_id=p["id"],
                    text=original_text,
                    corrected_categoria=p.get("corrected_categoria") or original_cat or "ninguna",
                    corrected_dimension=p.get("corrected_dimension"),
                    corrected_justificacion=p.get("corrected_justificacion")
                    or "Revisado por humano",
                    original_categoria=original_cat,
                    content_type=p.get("content_type") or "post",
                    content_id=p.get("content_id") or "",
                    reason=p.get("reason"),
                    id=p.get("chromadb_id"),
                    user_id=user_obj.get("id"),
                    added_by_username=user_obj.get("username"),
                )
                db.mark_feedback_indexed(p["id"], cid)
                ok += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"#{p.get('id')}: {exc}")
                logger.exception("Error indexando feedback %s", p.get("id"))
        status.clear()
        with status:
            ui.label(f"✅ {ok} correcciones indexadas en ChromaDB.").classes("text-sm")
            if errors:
                with ui.expansion(f"⚠ {len(errors)} errores", value=False):
                    for err in errors:
                        ui.label(err).classes("text-xs")

    ui.button(
        "🚀 Indexar correcciones pendientes",
        on_click=_run_index,
        icon="play_arrow",
    ).props("color=primary unelevated").classes("mt-3")


# --- Filters -----------------------------------------------------------------


def _render_filters(state: dict, *, on_filter_change: Callable[[], None]) -> ui.element:
    """Render filter controls; bind them to ``state`` so callbacks see updates."""

    container = ui.column().classes("w-full")

    def _build() -> None:
        container.clear()
        with container:
            with ui.row().classes("w-full gap-4 items-end flex-wrap"):
                ui.select(
                    options={"all": "Todos", "post": "Posts", "comment": "Comments"},
                    value=state.get("content_type", "all"),
                    label="Tipo",
                    on_change=lambda e: (
                        state.update({"content_type": e.value if e.value else "all"}),
                        on_filter_change(),
                    ),
                ).props("outlined dense").classes("w-40")

                ui.select(
                    options={
                        "all": "Todos",
                        "pending": "Pendientes",
                        "agreed": "Acuerdo",
                        "disagreed": "Corregidos",
                    },
                    value=state.get("review_state", "pending"),
                    label="Estado",
                    on_change=lambda e: (
                        state.update({"review_state": e.value if e.value else "pending"}),
                        on_filter_change(),
                    ),
                ).props("outlined dense").classes("w-44")

                ui.switch(
                    "Solo violentos",
                    value=bool(state.get("only_violent", False)),
                    on_change=lambda e: (
                        state.update({"only_violent": bool(e.value)}),
                        on_filter_change(),
                    ),
                )

                def _refresh() -> None:
                    state["_refresh_token"] = state.get("_refresh_token", 0) + 1
                    on_filter_change()

                ui.button(
                    "Refrescar",
                    on_click=_refresh,
                    icon="refresh",
                ).props("outline")

    _build()
    return container


# --- Form state per analysis row -------------------------------------------


class _RowFormState:
    """Mutable state for one analysis row's feedback form."""

    def __init__(self, ar_id: int, existing_fb: dict | None) -> None:
        self.ar_id = ar_id
        self.agrees: str | None = None  # "yes" | "no"
        self.reason: str = ""
        self.reviewer: str = ""  # not editable — autocompleted
        self.on_refresh: Callable[[], None] | None = None  # set by caller
        self.on_save_success: Callable[[], None] | None = None  # post-save hook
        existing_labels: list[dict] = list((existing_fb or {}).get("labels") or [])
        if not existing_labels and (existing_fb or {}).get("corrected_categoria"):
            existing_labels = [
                {
                    "categoria": (existing_fb or {}).get("corrected_categoria"),
                    "dimension": (existing_fb or {}).get("corrected_dimension"),
                    "severidad": "media",
                    "justificacion": (existing_fb or {}).get("corrected_justificacion") or "",
                }
            ]
        if not existing_labels:
            existing_labels = [{"categoria": "", "dimension": "", "severidad": "media"}]
        # Each row starts with sensible defaults so that the UI can render
        # right away (the first row always exists).
        self.labels = existing_labels[:MAX_LABELS]
        self.feedback_msg: str | None = None
        self.feedback_kind: str = "info"  # "info" | "ok" | "error"
        if existing_fb:
            self.agrees = (
                "yes"
                if str(existing_fb.get("agrees", "")).lower() == "true"
                else ("no" if str(existing_fb.get("agrees", "")).lower() == "false" else None)
            )
            self.reason = str(existing_fb.get("reason") or "")

    def add_label(self) -> None:
        if len(self.labels) >= MAX_LABELS:
            return
        self.labels.append({"categoria": "", "dimension": "", "severidad": "media"})
        self._bump()

    def drop_last_label(self) -> None:
        if len(self.labels) <= 1:
            return
        self.labels.pop()
        self._bump()

    def _bump(self) -> None:
        """No-op kept for backwards compatibility — the form uses
        ``on_refresh`` callbacks now, not token bumps."""
        pass


# --- One analysis row UI -----------------------------------------------------


def _render_feedback_form(
    row: dict,
    text_lookup: dict[str, str],
    user: dict,
    on_change=lambda: None,
    on_save_success: Callable[[], None] | None = None,
) -> None:
    """Render the feedback form for a single analysis row.

    Three regions:

    * **AI classification panel** (static, only repaints when row changes).
    * **Verdict + save buttons** (refreshable; depends on ``state.agrees``
      + ``state.feedback_msg``).
    * **Multi-label editor** (refreshable; only visible when
      ``state.agrees == "no"``).

    Re-renders use small ``ui.refreshable`` blocks rather than
    ``container.clear()`` so the user's bindings survive verdict changes.

    ``on_save_success`` is called after a successful save so the caller
    can close the modal and refresh the listing.
    """
    ar_id = row["id"]
    db = get_database()
    existing_fb = row.get("feedback_row") or db.get_feedback_for_analysis(ar_id)
    state = _RowFormState(ar_id, existing_fb)
    state.on_save_success = on_save_success

    # --- Static header: original text + AI classification --------------------
    content_type = row.get("content_type") or "post"
    content_id = row.get("content_id") or ""
    original = (
        row.get("text_snapshot")
        or text_lookup.get(content_id)
        or db.get_original_text(content_type, content_id)
    )
    if not original:
        original = f"(Texto original no disponible — ID {content_id})"
    with ui.element("div").style(
        "padding: 0.75rem 1rem; border-left: 3px solid var(--enola-brass); "
        "background: rgba(191, 161, 129, 0.08); border-radius: 0.5rem;"
    ):
        ui.label("Texto original:").classes(
            "text-xs uppercase tracking-widest font-semibold"
        ).style("color: var(--enola-charcoal-light);")
        ui.label(original[:1000] + ("…" if len(original) > 1000 else "")).classes("text-sm mt-1")

    ai_labels = list(row.get("labels") or [])
    with ui.element("div").style(
        "padding: 0.75rem 1rem; border-radius: 0.5rem; "
        "background: rgba(107, 78, 113, 0.06); "
        "border: 1px solid rgba(107, 78, 113, 0.18);"
    ):
        ui.label("🤖 Clasificación de la IA").classes(
            "text-xs uppercase tracking-widest font-semibold"
        ).style("color: var(--enola-plum);")
        if ai_labels:
            for i, lbl in enumerate(ai_labels, start=1):
                sev = (lbl.get("severidad") or "ninguna").capitalize()
                ui.label(
                    f"#{i} — {label_for(lbl.get('categoria'))} / "
                    f"{lbl.get('dimension') or '—'} · {sev}"
                ).classes("text-sm mt-1")
        else:
            cat = label_for(row.get("categoria") or "—")
            ui.label(f"Categoría: {cat}").classes("text-sm")
            ui.label(f"Violencia: {row.get('tiene_violencia') or '—'}").classes("text-sm")

    # --- Refreshable verdict + form region --------------------------------
    # Use @ui.refreshable so changing the verdict or label count only
    # repaints the affected sub-tree. ``state.on_refresh`` triggers the
    # repaint; selectors bind their values to ``state`` so user typing
    # survives re-renders.
    @ui.refreshable
    def verdict_region():
        _render_verdict_section(state, row, user)

    state.on_refresh = verdict_region.refresh
    verdict_region()


def _radio_to_agrees(value: str) -> str | None:
    """Map the radio display label to the short ``state.agrees`` token."""
    if value == "Sí, coincido":
        return "yes"
    if value == "No, corregir":
        return "no"
    return None


def _agrees_to_radio(value: str | None) -> str | None:
    """Inverse of :func:`_radio_to_agrees` — for ``bind_value`` round-trip."""
    if value == "yes":
        return "Sí, coincido"
    if value == "no":
        return "No, corregir"
    return None


def _render_verdict_section(
    state: _RowFormState,
    row: dict,
    user: dict,
) -> None:
    """Render the verdict radio + conditional form + save buttons."""
    ui.label("Tu revisión:").classes("text-xs uppercase tracking-widest font-semibold").style(
        "color: var(--enola-brass-deep);"
    )

    # Use bind_value so the radio's selected option round-trips into
    # ``state.agrees`` — no manual ``on_value_change`` plumbing needed.
    # ``ui.ref`` doesn't exist in NiceGUI 3.6 — we use a single-element
    # dict as a JS-friendly mutable ref.
    radio_value: dict = {"value": _agrees_to_radio(state.agrees)}
    with ui.row().classes("gap-4"):

        def _on_radio_change(e) -> None:
            new_value = e.value if hasattr(e, "value") else e
            state.agrees = _radio_to_agrees(new_value)
            state.feedback_msg = None
            state.feedback_kind = "info"
            radio_value["value"] = new_value
            if state.on_refresh is not None:
                state.on_refresh()

        ui.radio(
            ["Sí, coincido", "No, corregir"],
            value=radio_value["value"],
            on_change=_on_radio_change,
        ).props("inline")

    if state.agrees == "no":
        _render_correction_form(state)

    _render_save_buttons(state, row, user)

    if state.feedback_msg:
        color = {
            "ok": theme.RELIABILITY_OK,
            "error": theme.RELIABILITY_CRITICA,
            "info": theme.CHARCOAL_LIGHT,
        }.get(state.feedback_kind, theme.CHARCOAL_LIGHT)
        ui.label(state.feedback_msg).classes("text-sm mt-2").style(f"color: {color};")


def _render_correction_form(state: _RowFormState) -> None:
    """Render the multi-label correction form when ``state.agrees == 'no'``.

    Each label row is self-contained and mutates the row dict in place
    via the ``state`` reference. ``state.on_refresh()`` is called to
    re-render after add/drop operations.
    """
    with ui.element("div").style(
        "margin-top: 0.75rem; padding: 1rem; "
        "border: 1px solid rgba(107, 78, 113, 0.30); "
        "border-left: 4px solid var(--enola-plum); "
        "border-radius: 0.5rem; "
        "background: rgba(107, 78, 113, 0.04);"
    ):
        ui.label("✏️ Corrección").classes("text-xs uppercase tracking-widest font-semibold").style(
            "color: var(--enola-plum);"
        )

        ui.label(
            "Indicá las categorías correctas. Hasta 5 etiquetas; cada "
            "una guarda la justificación y la evidencia textual."
        ).classes("text-xs mt-1 mb-3").style("color: var(--enola-charcoal-light);")

        # Per-form "why" reason.
        reason_input = (
            ui.input(
                label="¿Por qué no coincidís? (opcional)",
                value=state.reason,
            )
            .props("outlined dense")
            .classes("w-full")
        )

        def _on_reason_change(e) -> None:
            state.reason = e.value if e.value is not None else ""

        reason_input.on_value_change(_on_reason_change)

        if not state.labels:
            state.labels = [{"categoria": "", "dimension": "", "severidad": "media"}]

        for idx, lbl in enumerate(state.labels):
            _render_label_row(idx, lbl)

        with ui.row().classes("gap-2 mt-3"):

            def _add() -> None:
                state.add_label()
                if state.on_refresh is not None:
                    state.on_refresh()

            def _drop() -> None:
                state.drop_last_label()
                if state.on_refresh is not None:
                    state.on_refresh()

            ui.button(
                "➕ Agregar etiqueta",
                icon="add",
                on_click=_add,
            ).props("outline size=sm").set_enabled(len(state.labels) < MAX_LABELS)
            ui.button(
                "➖ Quitar última",
                icon="remove",
                on_click=_drop,
            ).props("outline size=sm").set_enabled(len(state.labels) > 1)


def _render_label_row(row_idx: int, lbl: dict) -> None:
    """Render a single label row in the multi-label editor.

    The row holds direct widget references (``cat_select``, ``dim_select``
    …) so the categoria handler can update the dimension dropdown's
    options in place via ``set_options`` without destroying the row.
    Re-rendering the whole row on every categoria change created a
    race condition where the next click hit a stale widget.
    """
    with ui.element("div").style(
        "border: 1px solid rgba(191, 161, 129, 0.28); "
        "border-radius: 0.5rem; padding: 0.85rem 1rem; "
        "background: var(--enola-cream); margin-top: 0.5rem;"
    ):
        ui.label(f"Etiqueta #{row_idx + 1}").classes("text-xs font-semibold mb-2").style(
            "color: var(--enola-brass-deep); letter-spacing: 0.08em;"
        )

        with ui.row().classes("w-full gap-3 items-start flex-wrap"):
            cat_select = (
                ui.select(
                    options=val_helpers.categoria_choices(),
                    value=lbl.get("categoria") or "",
                    label="Categoría",
                )
                .props("outlined dense")
                .classes("min-w-64")
            )

            dim_select = (
                ui.select(
                    options=val_helpers.dimension_options_for(str(lbl.get("categoria") or "")),
                    value=lbl.get("dimension") or "",
                    label="Subdimensión",
                )
                .props("outlined dense")
                .classes("min-w-56")
            )

            sev_select = (
                ui.select(
                    options=[s.value for s in Severity],
                    value=lbl.get("severidad") or "media",
                    label="Severidad",
                )
                .props("outlined dense")
                .classes("w-32")
            )

            fpp_switch = ui.switch(
                "Falso positivo probable",
                value=bool(lbl.get("es_falso_positivo_probable")),
            )

            def _on_cat_change(e) -> None:
                new_cat = e.value if e.value is not None else ""
                lbl["categoria"] = new_cat
                valid = SUBDIMENSIONES_POR_CATEGORIA.get(new_cat, [])
                # If the previously-selected dimension is no longer
                # valid, reset it.
                if lbl.get("dimension") and lbl["dimension"] not in valid:
                    lbl["dimension"] = ""
                # Update the dimension dropdown's options in place —
                # much faster than refreshing the whole row, and avoids
                # a race condition where the next click hits a stale
                # widget that's about to be destroyed.
                dim_select.set_options(val_helpers.dimension_options_for(new_cat))
                dim_select.set_value(lbl.get("dimension") or "")

            def _on_dim_change(e) -> None:
                lbl["dimension"] = e.value if e.value is not None else ""

            def _on_sev_change(e) -> None:
                lbl["severidad"] = e.value if e.value else "media"

            def _on_fpp_change(e) -> None:
                lbl["es_falso_positivo_probable"] = bool(e.value)

            cat_select.on_value_change(_on_cat_change)
            dim_select.on_value_change(_on_dim_change)
            sev_select.on_value_change(_on_sev_change)
            fpp_switch.on_value_change(_on_fpp_change)

        just_input = (
            ui.input(
                label="Justificación",
                value=str(lbl.get("justificacion") or ""),
            )
            .props("outlined dense")
            .classes("w-full mt-2")
        )

        def _on_just_change(e) -> None:
            lbl["justificacion"] = e.value if e.value is not None else ""

        just_input.on_value_change(_on_just_change)

        evid_input = (
            ui.input(
                label="Evidencia (cita textual)",
                value=str(lbl.get("evidencia") or ""),
            )
            .props("outlined dense")
            .classes("w-full mt-2")
        )

        def _on_evid_change(e) -> None:
            lbl["evidencia"] = e.value if e.value is not None else ""

        evid_input.on_value_change(_on_evid_change)


def _render_save_buttons(
    state: _RowFormState,
    row: dict,
    user: dict,
) -> None:
    """Render the two CTAs, gated on whether the form is submittable."""
    if state.agrees not in ("yes", "no"):
        ui.label("Elegí «Sí, coincido» o «No, corregir» para habilitar el guardado.").classes(
            "text-xs mt-2"
        ).style("color: var(--enola-charcoal-light); font-style: italic;")
        with ui.row().classes("gap-2 mt-3"):
            ui.button("💾 Guardar feedback", icon="save").props("color=primary outline disable")
            ui.button("💾+🔎 Guardar e indexar en ChromaDB", icon="cloud_upload").props("disable")
        return

    with ui.row().classes("gap-2 mt-3"):

        def _save_only() -> None:
            if not _validate_form(state):
                if state.on_refresh is not None:
                    state.on_refresh()
                return
            _persist_feedback(state=state, row=row, user=user, push_chromadb=False)
            if state.on_refresh is not None:
                state.on_refresh()
            if state.on_save_success is not None:
                state.on_save_success()

        def _save_and_index() -> None:
            if not _validate_form(state):
                if state.on_refresh is not None:
                    state.on_refresh()
                return
            _persist_feedback(state=state, row=row, user=user, push_chromadb=True)
            if state.on_refresh is not None:
                state.on_refresh()
            if state.on_save_success is not None:
                state.on_save_success()

        ui.button("💾 Guardar feedback", icon="save", on_click=_save_only).props(
            "color=primary outline"
        )

        idx_btn = ui.button(
            "💾+🔎 Guardar e indexar en ChromaDB",
            icon="cloud_upload",
            on_click=_save_and_index,
        )
        # Index only makes sense when correcting — agreeing with the IA
        # is already a "no correction" event.
        if state.agrees != "no":
            idx_btn.props("disable")


def _validate_form(state: _RowFormState) -> bool:
    """Cross-row validation: every categoria+dimension must be coherent.

    Empty labels (no categoria) are **skipped** — the user adds a new
    blank row to fill in, and only completed labels are persisted
    (see ``_persist_feedback``). At least one completed label is
    required when disagreeing with the IA.
    """
    if state.agrees == "no":
        completed = [lbl for lbl in state.labels if lbl.get("categoria")]
        if not completed:
            state.feedback_msg = (
                "❌ Necesitás al menos una etiqueta con categoría antes de guardar."
            )
            state.feedback_kind = "error"
            return False
        for lbl in completed:
            cat = str(lbl["categoria"])
            dim = str(lbl.get("dimension") or "")
            if dim and not val_helpers.is_valid_categoria_for_dimension(cat, dim):
                state.feedback_msg = f"❌ La dimensión {dim} no corresponde a {cat}."
                state.feedback_kind = "error"
                return False
    return True


def _persist_feedback(
    *,
    state: _RowFormState,
    row: dict,
    user: dict,
    push_chromadb: bool,
) -> None:
    """Write the feedback into SQLite (and optionally ChromaDB)."""
    db = get_database()
    agrees_yes = state.agrees == "yes"

    reason = state.reason if state.agrees == "no" else None

    # Build the corrected_labels list — only meaningful when the reviewer
    # disagrees and provided >=1 valid categoria. Empty otherwise.
    corrected_labels: list[dict] = []
    if not agrees_yes:
        for lbl in state.labels:
            if not lbl.get("categoria"):
                continue
            corrected_labels.append(
                {
                    "categoria": lbl.get("categoria"),
                    "dimension": lbl.get("dimension") or None,
                    "severidad": lbl.get("severidad") or "ninguna",
                    "es_falso_positivo_probable": bool(lbl.get("es_falso_positivo_probable")),
                    "justificacion": lbl.get("justificacion") or "",
                    "evidencia": lbl.get("evidencia") or "",
                }
            )

    payload = val_helpers.build_feedback_payload(
        analysis_result_id=row["id"],
        content_type=row.get("content_type") or "post",
        content_id=row.get("content_id") or "",
        text_snapshot=row.get("text_snapshot") or "",
        agrees=agrees_yes,
        reason=reason,
        reviewer=user.get("username"),
        corrected_labels=corrected_labels,
    )
    payload["reviewer_user_id"] = user.get("id")
    payload["reviewer_username"] = user.get("username")
    try:
        new_fb_id = db.save_feedback(payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("save_feedback failed")
        state.feedback_msg = f"❌ Error guardando feedback: {exc}"
        state.feedback_kind = "error"
        return

    state.feedback_msg = "✅ Feedback guardado en SQLite."
    state.feedback_kind = "ok"

    # ChromaDB push only when the reviewer disagreed AND the user hit
    # "save & index".
    if push_chromadb and not agrees_yes:
        try:
            fb_store = _feedback_store()
            cid = fb_store.add_correction(
                feedback_id=new_fb_id,
                text=payload["text_snapshot"]
                or db.get_original_text(payload["content_type"], payload["content_id"]),
                corrected_categoria=payload.get("corrected_categoria")
                or (corrected_labels[0]["categoria"] if corrected_labels else "ninguna"),
                corrected_dimension=payload.get("corrected_dimension"),
                corrected_justificacion=payload.get("corrected_justificacion")
                or "Revisado por humano",
                original_categoria=row.get("categoria"),
                content_type=payload["content_type"],
                content_id=payload["content_id"],
                reason=reason,
                corrected_labels=corrected_labels or None,
                user_id=user.get("id"),
                added_by_username=user.get("username"),
            )
            db.mark_feedback_indexed(new_fb_id, cid)
            who = user.get("username") or "?"
            state.feedback_msg = f"✅ Guardado + indexado por @{who}."
        except Exception as exc:  # noqa: BLE001
            logger.exception("ChromaDB index failed")
            state.feedback_msg = f"⚠ Guardado en SQLite pero falló el push a ChromaDB: {exc}"
            state.feedback_kind = "error"


# --- Page body ---------------------------------------------------------------


def _render_body() -> None:
    user = auth.current_user()
    if not user:
        # Safety net — page_scaffold should have redirected.
        ui.navigate.to("/login")
        return

    try:
        analysis, text_lookup = _load_data()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load data")
        ui.label(f"No se pudo cargar la base de datos: {exc}").classes("text-base")
        return

    _render_kpis(analysis)

    with ui.element("div").style("height: 1rem;"):
        pass

    with ui.expansion("🔧 Colección `feedback_corrections` (ChromaDB)").classes("w-full"):
        _render_chromadb_panel()

    section_header(
        "Análisis pendientes",
        "Revisá y corregí las salidas de la IA",
        subtitle=(
            "Filtros por tipo / estado / sólo violentos. Cada fila del "
            "listado incluye la corrección multi-etiqueta — la "
            "indexación en ChromaDB es opcional pero te permite entrenar "
            "implícitamente el RAGClassifier."
        ),
    )

    # Filters + listing — wrapped in a refreshable so changing filters
    # rebuilds the listing.
    filter_state: dict = {
        "content_type": "all",
        "review_state": "pending",
        "only_violent": False,
        "_refresh_token": 0,
    }

    @ui.refreshable
    def _render_listing() -> None:
        analysis_now, text_lookup_now = _load_data()
        _render_listing_inner(
            analysis_now,
            text_lookup_now,
            user,
            filter_state,
            on_after_save=lambda: _render_listing.refresh(),  # type: ignore[arg-type]
        )

    _render_filters(filter_state, on_filter_change=_render_listing.refresh)  # type: ignore[arg-type]

    _render_listing()


def _render_listing_inner(
    analysis: list[dict],
    text_lookup: dict[str, str],
    user: dict,
    filter_state: dict,
    on_after_save: Callable[[], None] | None = None,
) -> None:
    """Render a compact review table with one "📝 Revisar" button per row.

    Each row is a clickable summary; clicking the button opens a modal
    with the full feedback form (text + AI classification + multi-label
    editor + save buttons). The modal is dismissible via the close X
    button or "Cancelar" — saves happen inside the modal and dismiss
    automatically. After save, ``on_after_save`` is called so the
    caller can refresh the list (mark row as indexed, etc.).
    """
    feedback_lookup: dict[int, dict] = {}
    for fb in get_database().list_feedback() or []:
        ar_id = fb.get("analysis_result_id")
        if isinstance(ar_id, int):
            feedback_lookup[ar_id] = fb

    rows = val_helpers.filter_analysis_for_validation(
        analysis,
        list(feedback_lookup.values()),
        content_type=None
        if filter_state.get("content_type", "all") == "all"
        else filter_state["content_type"],
        review_state=filter_state.get("review_state", "all"),
        only_violent=bool(filter_state.get("only_violent", False)),
    )

    if not rows:
        ui.label("No hay análisis con los filtros seleccionados.").classes("text-sm").style(
            "color: var(--enola-charcoal-light); font-style: italic;"
        )
        return

    ui.label(f"{len(rows)} filas mostradas.").classes("text-xs mb-2").style(
        "color: var(--enola-charcoal-light);"
    )

    # Modal lives at page level so it can be opened from any row button.
    modal = _build_review_modal(text_lookup, user, on_after_save)

    # Modal lives at page level so it can be opened from any row button.
    modal = _build_review_modal(text_lookup, user, on_after_save)

    # Real HTML <table> with table-layout: auto so long categoria
    # names like "Cosificación / Slut-shaming" don't break the layout
    # (CSS Grid with fixed columns forces truncation or wrap).
    _render_review_table(rows=rows, modal=modal, text_lookup=text_lookup)


def _render_review_table(rows: list[dict], modal: Any, text_lookup: dict[str, str]) -> None:
    """Render the validation table as a real ``<table>`` element.

    Reviewed rows get a pale-green/red background and a ✅ badge in
    the *Estado* column so the reviewer can tell at a glance what's
    done and what isn't.
    """
    feedback_lookup: dict[int, dict] = {}
    for fb in get_database().list_feedback() or []:
        ar_id = fb.get("analysis_result_id")
        if isinstance(ar_id, int):
            feedback_lookup[ar_id] = fb

    with ui.element("div").style(
        "overflow-x: auto; "
        "border: 1px solid rgba(191, 161, 129, 0.30); "
        "border-radius: 0.5rem; "
        "background: var(--enola-cream);"
    ):
        with ui.element("table").style(
            "width: 100%; "
            "min-width: 880px; "
            "border-collapse: separate; "
            "border-spacing: 0; "
            "font-size: 0.875rem;"
        ):
            # Header row
            with ui.element("thead"):
                with ui.element("tr").style(
                    "background: linear-gradient(180deg, rgba(107, 78, 113, 0.10), rgba(107, 78, 113, 0.04));"
                ):
                    for header_text, align in (
                        ("Tipo", "left"),
                        ("ID", "left"),
                        ("Categoría IA", "left"),
                        ("Subdimensión", "left"),
                        ("Estado", "left"),
                        ("Acción", "center"),
                    ):
                        with ui.element("th").style(
                            f"padding: 0.65rem 0.85rem; "
                            f"text-align: {align}; "
                            f"font-weight: 600; "
                            f"font-size: 0.7rem; "
                            f"letter-spacing: 0.08em; "
                            f"text-transform: uppercase; "
                            f"color: var(--enola-charcoal-light); "
                            f"border-bottom: 2px solid var(--enola-brass); "
                            f"white-space: nowrap;"
                        ):
                            ui.label(header_text)

            with ui.element("tbody"):
                for row in rows:
                    row_id = row.get("id")
                    content_id = str(row.get("content_id") or "")
                    cat_label = label_for(row.get("categoria") or "—")
                    dim = row.get("dimension") or "—"
                    fb = row.get("feedback_row") or feedback_lookup.get(row_id) or {}
                    reviewed = bool(fb.get("id"))
                    reviewer = fb.get("reviewer_username") or ""

                    # Tint by review state.
                    if reviewed and fb.get("agrees") == "true":
                        row_bg = "#e8f5e9"  # agreed — pale green
                    elif reviewed and fb.get("agrees") == "false":
                        row_bg = "#fdecea"  # corrected — pale red
                    else:
                        row_bg = "transparent"

                    if reviewed:
                        estado_text = f"✅ Revisado por @{reviewer}" if reviewer else "✅ Revisado"
                    else:
                        estado_text = "⏳ Pendiente"

                    content_type_icon = "💬" if row.get("content_type") == "comment" else "📄"

                    with ui.element("tr").style(
                        f"background: {row_bg}; border-bottom: 1px solid rgba(191, 161, 129, 0.18);"
                    ):
                        with ui.element("td").style(
                            "padding: 0.55rem 0.85rem; text-align: left; font-size: 0.95rem;"
                        ):
                            ui.label(content_type_icon)
                        with ui.element("td").style(
                            "padding: 0.55rem 0.85rem; "
                            "text-align: left; "
                            "font-family: monospace; "
                            "font-size: 0.75rem; "
                            "color: var(--enola-charcoal-light); "
                            "white-space: nowrap;"
                        ):
                            short_id = content_id[:24] + ("…" if len(content_id) > 24 else "")
                            ui.label(short_id)
                        with ui.element("td").style(
                            "padding: 0.55rem 0.85rem; "
                            "text-align: left; "
                            "font-weight: 500; "
                            "color: var(--enola-plum); "
                            "white-space: nowrap;"
                        ):
                            ui.label(cat_label)
                        with ui.element("td").style(
                            "padding: 0.55rem 0.85rem; "
                            "text-align: left; "
                            "font-family: monospace; "
                            "font-size: 0.75rem; "
                            "color: var(--enola-charcoal-light); "
                            "white-space: nowrap;"
                        ):
                            ui.label(f"`{dim}`")
                        with ui.element("td").style(
                            "padding: 0.55rem 0.85rem; "
                            "text-align: left; "
                            "font-size: 0.8rem; "
                            "white-space: nowrap;"
                        ):
                            ui.label(estado_text)
                        with ui.element("td").style(
                            "padding: 0.45rem 0.85rem; text-align: center;"
                        ):

                            def _open(_r=row) -> None:
                                _open_modal_for_row(
                                    modal,
                                    _r,
                                    text_lookup,
                                    auth.current_user() or {"id": None, "username": "?"},
                                )

                            (
                                ui.button(
                                    "📝 Revisar",
                                    icon="edit",
                                    on_click=_open,
                                )
                                .props("outline color=primary size=sm")
                                .style("min-width: 110px;")
                            )


def _build_review_modal(
    text_lookup: dict[str, str],
    user: dict,
    on_after_save: Callable[[], None] | None,
) -> Any:
    """Construct the (initially closed) review modal.

    The modal body is implemented as a ``@ui.refreshable`` so each
    ``open_for_row`` call repaints with the chosen row's data. Closing
    dismisses; saving also dismisses and runs ``on_after_save``.
    """
    modal = ui.dialog().props("persistent")

    current_row_ref: dict[str, Any] = {"row": None}

    def _open(row: dict) -> None:
        current_row_ref["row"] = row
        body.refresh()
        modal.open()

    with modal, ui.card().classes("w-full max-w-4xl").style("max-height: 90vh; overflow-y: auto;"):
        with ui.element("div").classes("w-full flex items-center justify-between mb-3"):
            ui.label("📝 Revisar análisis").classes("text-xl font-semibold enola-display").style(
                "color: var(--enola-plum);"
            )
            ui.button(
                icon="close",
                on_click=lambda: (body.refresh(), modal.close()),
            ).props("flat round dense")

        @ui.refreshable
        def body() -> None:
            row = current_row_ref["row"]
            if not row:
                ui.label("Sin análisis seleccionado.").classes("text-sm")
                return
            _render_modal_body(row, text_lookup, user, modal, on_after_save)

        body()

    # Expose open_for_row via a wrapper we attach to the dialog object
    # so callers don't need to know the inner closure name.
    modal._open_for_row = _open  # type: ignore[attr-defined]
    return modal


def _open_modal_for_row(modal: Any, row: dict, *args: Any, **kwargs: Any) -> None:
    """Open the modal pre-populated with ``row``."""
    modal._open_for_row(row)  # type: ignore[attr-defined]


def _render_modal_body(
    row: dict,
    text_lookup: dict[str, str],
    user: dict,
    modal: Any,
    on_after_save: Callable[[], None] | None,
) -> None:
    """Render the modal contents: header strip + form."""
    content_type = str(row.get("content_type") or "?").upper()
    content_id = str(row.get("content_id") or "?")
    cat_label = label_for(row.get("categoria") or "—")
    dim = row.get("dimension") or "—"
    sev = row.get("severidad") or "—"

    # Header strip — type + ID + AI summary
    with ui.element("div").style(
        "padding: 0.75rem 1rem; border-radius: 0.5rem; "
        "background: rgba(107, 78, 113, 0.06); "
        "border-left: 3px solid var(--enola-plum); "
        "margin-bottom: 1rem;"
    ):
        with ui.row().classes("items-center gap-3 flex-wrap"):
            ui.label(f"{content_type}").classes(
                "text-xs font-bold uppercase tracking-widest"
            ).style("color: var(--enola-plum);")
            ui.label(content_id).classes("text-xs").style(
                "color: var(--enola-charcoal-light); font-family: monospace;"
            )
        ui.label(f"IA: {cat_label} / {dim} · severidad {sev}").classes("text-sm mt-1").style(
            "color: var(--enola-charcoal);"
        )

    # Form — same widget tree as the legacy expansion view, but framed
    # inside a clean column instead of an expansion. We pass an
    # ``on_save_success`` hook so the save buttons can dismiss the
    # modal and refresh the listing once the row is persisted.
    with ui.column().classes("w-full"):

        def _on_save_done() -> None:
            modal.close()
            if on_after_save is not None:
                on_after_save()

        _render_feedback_form(
            row=row,
            text_lookup=text_lookup,
            user=user,
            on_change=lambda: None,
            on_save_success=_on_save_done,
        )


__all__ = ["page_validacion"]
