"""Pure helpers for the human-feedback validation UI.

These functions are side-effect free so they can be unit-tested without
Streamlit. The tab in ``app.py`` consumes the helpers and layers the
``st.*`` calls on top.

Multi-label aware: feedback overrides can carry **one or more**
:class:`LabelAssignment`-shaped dicts via ``corrected_labels`` in
:func:`build_feedback_payload`. Legacy single-label overrides
(``corrected_categoria``/``corrected_dimension``/
``corrected_justificacion``) are still accepted and internally wrapped
into a one-element list for backwards compatibility.
"""

from __future__ import annotations

from src.analyzer.category_mapping import (
    CATEGORIAS_ORDENADAS,
    DESCRIPCION_SUBDIMENSION,
    MAX_LABELS,
    SUBDIMENSIONES_POR_CATEGORIA,
    Categoria,
)
from src.analyzer.exclusion_filter import EXCLUSION_BASURA_DIGITAL, EXCLUSION_VIOLENCIA_COMUN

# Categories the reviewer can pick — "ninguna" is intentionally excluded
# (the override only happens when disagrees=True with a real correction).
CATEGORIA_CHOICES: tuple[str, ...] = tuple(CATEGORIAS_ORDENADAS)


def categoria_choices() -> dict[str, str]:
    """Return ``{value: label}`` pairs for the categoria selectbox.

    NiceGUI 3.14 ``ui.select`` only accepts a ``dict`` (or a flat list of
    strings) as ``options`` — the ``[(label, value), ...]`` tuple form
    raises ``ValueError: Invalid value: ...`` and silently breaks the
    surrounding widget tree.
    """
    from src.ui.utils import label_for

    choices: dict[str, str] = {}
    for code in CATEGORIA_CHOICES:
        choices[code] = label_for(code)
    choices[""] = "(Sin categoría — borrar override)"
    return choices


def dimension_options_for(categoria: str) -> dict[str, str]:
    """Return ``{value: label}`` pairs of valid dimensions for ``categoria``.

    The label format is ``"<code> — <description>"``. Returns only the
    "(Sin dimensión)" pair if ``categoria`` is empty/``ninguna``.
    """
    if not categoria or categoria == Categoria.NINGUNA.value:
        return {"": "(Sin dimensión)"}

    dims = SUBDIMENSIONES_POR_CATEGORIA.get(categoria, [])
    choices: dict[str, str] = {d: f"{d} — {DESCRIPCION_SUBDIMENSION.get(d, '')}" for d in dims}
    choices[""] = "(Sin dimensión)"
    return choices


def is_valid_categoria_for_dimension(categoria: str, dimension: str) -> bool:
    """Return True if ``dimension`` is in the valid set for ``categoria``."""
    if not categoria:
        return not dimension
    if categoria == Categoria.NINGUNA.value:
        return not dimension
    valid = SUBDIMENSIONES_POR_CATEGORIA.get(categoria, [])
    if not dimension:
        return True
    return dimension in valid


def _empty_to_none(value: object) -> object:
    """Normalise empty strings from ``st.*`` widgets to ``None``."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return value


def normalize_label_row(row: dict[str, object]) -> dict[str, object] | None:
    """Normalize a single label-row dict from the multi-label UI.

    Returns the cleaned dict or ``None`` if the row is empty/invalid
    (e.g. categoria outside the canonical closed set, or empty).
    Empty strings become ``None``; the marcadores list is always a
    list of stripped strings; severidad is mapped to the canonical
    lower-case word or ``"ninguna"`` if unknown; the dimension is
    validated against the categoria and dropped if mismatched.
    """
    from src.analyzer.category_mapping import (
        Categoria,
        map_gravedad,
        normalize_dimension,
    )
    from src.analyzer.violence_types import Severity

    if not isinstance(row, dict):
        return None
    cat = _empty_to_none(row.get("categoria"))
    if not cat:
        return None
    if cat not in {c.value for c in Categoria}:
        return None
    dim_raw = _empty_to_none(row.get("dimension"))
    dim = normalize_dimension(str(cat), dim_raw) if dim_raw else None
    sev_raw = row.get("severidad") or "ninguna"
    try:
        sev_enum = Severity(str(sev_raw).strip().lower())
    except ValueError:
        sev_enum = map_gravedad(sev_raw)
    marcadores_raw = row.get("marcadores_detectados") or []
    if isinstance(marcadores_raw, str):
        marcadores: list[str] = [m.strip() for m in marcadores_raw.split(",") if m.strip()]
    elif isinstance(marcadores_raw, list):
        marcadores = [str(m).strip() for m in marcadores_raw if m]
    else:
        marcadores = []
    fpp_raw = row.get("es_falso_positivo_probable", False)
    if isinstance(fpp_raw, str):
        es_fpp = fpp_raw.strip().lower() in {"true", "1", "yes", "si", "sí"}
    else:
        es_fpp = bool(fpp_raw)
    return {
        "categoria": str(cat),
        "dimension": dim,
        "severidad": sev_enum.value,
        "justificacion": str(row.get("justificacion") or ""),
        "evidencia": str(row.get("evidencia") or ""),
        "regla_disparada": _empty_to_none(row.get("regla_disparada")),
        "marcadores_detectados": marcadores,
        "confianza": row.get("confianza"),
        "score_ajuste": row.get("score_ajuste"),
        "es_falso_positivo_probable": es_fpp,
    }


def build_feedback_payload(
    *,
    analysis_result_id: int | str,
    content_type: str,
    content_id: str,
    text_snapshot: str,
    agrees: bool,
    reason: str | None = None,
    corrected_categoria: str | None = None,
    corrected_dimension: str | None = None,
    corrected_justificacion: str | None = None,
    reviewer: str | None = None,
    corrected_labels: list[dict] | None = None,
) -> dict[str, object]:
    """Build the dict payload accepted by ``Database.save_feedback``.

    Empty strings from text inputs are normalised to ``None`` so
    SQLAlchemy stores NULL rather than empty strings.

    Multi-label aware: when ``corrected_labels`` is provided AND the
    reviewer disagrees, the list is normalized via
    :func:`normalize_label_row` and passed to the database which writes
    it to the ``analysis_feedback_labels`` side table. The flat
    ``corrected_*`` columns are populated from the **primary** label
    for backwards compatibility with the landing/reports consumers.

    For single-label callers (legacy UI) the trio
    (``corrected_categoria``/``corrected_dimension``/
    ``corrected_justificacion``) is wrapped into a one-element
    ``corrected_labels`` list so the same downstream path runs.
    """
    if not agrees:
        if corrected_labels is None:
            # Wrap the legacy single-label fields into a one-element list.
            if corrected_categoria:
                corrected_labels = [
                    {
                        "categoria": corrected_categoria,
                        "dimension": corrected_dimension,
                        "justificacion": corrected_justificacion or "",
                    }
                ]
            else:
                corrected_labels = []

        # Normalize and dedupe.
        normalized: list[dict] = []
        seen: set[tuple[str, object]] = set()
        for row in corrected_labels:
            clean = normalize_label_row(row)
            if clean is None:
                continue
            cat = clean.get("categoria")
            dim = clean.get("dimension")
            key = (str(cat), dim if dim is None else str(dim))
            if key in seen:
                continue
            seen.add(key)
            normalized.append(clean)
            if len(normalized) >= MAX_LABELS:
                break

        if normalized:
            sev_order = {"alta": 3, "media": 2, "baja": 1, "ninguna": 0}
            primary = max(normalized, key=lambda lbl: sev_order.get(str(lbl.get("severidad")), 0))
        else:
            primary = {
                "categoria": None,
                "dimension": None,
                "justificacion": None,
            }
    else:
        normalized = []
        primary = {
            "categoria": None,
            "dimension": None,
            "justificacion": None,
        }

    return {
        "analysis_result_id": int(analysis_result_id),
        "content_type": content_type,
        "content_id": content_id,
        "text_snapshot": text_snapshot or "",
        "agrees": "true" if agrees else "false",
        "reason": _empty_to_none(reason),
        "corrected_categoria": primary.get("categoria"),
        "corrected_dimension": primary.get("dimension"),
        "corrected_justificacion": primary.get("justificacion"),
        "reviewer": _empty_to_none(reviewer),
        "corrected_labels": normalized,
    }


def feedback_status_label(row: dict[str, object]) -> str:
    """Human label for the feedback status column."""
    agrees = str(row.get("agrees") or "").lower()
    if agrees == "true":
        return "✅ De acuerdo"
    if agrees == "false":
        return "❌ Corregido"
    return "⏳ Pendiente"


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def filter_analysis_for_validation(
    analysis_rows: list[dict[str, object]],
    feedback_rows: list[dict[str, object]],
    *,
    content_type: str | None = None,
    review_state: str = "all",  # "all" / "pending" / "agreed" / "disagreed"
    only_violent: bool = False,
) -> list[dict[str, object]]:
    """Merge analysis rows with their feedback status and apply filters.

    Args:
        analysis_rows: Output of ``Database.get_analysis_results``.
        feedback_rows: Output of ``Database.list_feedback``.
        content_type: ``"post"``, ``"comment"`` or ``None`` for both.
        review_state: One of ``"all"``, ``"pending"``, ``"agreed"``,
            ``"disagreed"``.
        only_violent: If True, keep only rows with
            ``tiene_violencia == "true"``.

    Returns:
        Filtered list of dicts with two extra keys: ``feedback_status``
        (``"pending"`` | ``"agreed"`` | ``"disagreed"``) and
        ``feedback_row`` (the feedback dict or ``None``).
    """
    fb_by_id: dict[int, dict[str, object]] = {}
    for fb_row in feedback_rows or []:
        ar_id = _safe_int(fb_row.get("analysis_result_id"))
        if ar_id is None:
            continue
        fb_by_id[ar_id] = fb_row

    out: list[dict[str, object]] = []
    for row in analysis_rows or []:
        ar_id = _safe_int(row.get("id"))
        if ar_id is None:
            continue

        if content_type and row.get("content_type") != content_type:
            continue
        if row.get("exclusion_label") in {
            EXCLUSION_BASURA_DIGITAL,
            EXCLUSION_VIOLENCIA_COMUN,
        }:
            continue
        if only_violent and str(row.get("tiene_violencia")) != "true":
            continue

        fb_match: dict[str, object] | None = fb_by_id.get(ar_id)
        fb: dict[str, object] | None
        if fb_match is None:
            status = "pending"
            fb = None
        elif str(fb_match.get("agrees") or "").lower() == "true":
            status = "agreed"
            fb = fb_match
        else:
            status = "disagreed"
            fb = fb_match

        if review_state != "all" and status != review_state:
            continue

        new_row: dict[str, object] = dict(row)
        new_row["feedback_status"] = status
        new_row["feedback_row"] = fb
        out.append(new_row)

    return out


__all__ = [
    "CATEGORIA_CHOICES",
    "MAX_LABELS",
    "build_feedback_payload",
    "categoria_choices",
    "dimension_options_for",
    "feedback_status_label",
    "filter_analysis_for_validation",
    "is_valid_categoria_for_dimension",
    "normalize_label_row",
]
