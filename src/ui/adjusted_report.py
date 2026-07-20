"""Adjusted-report helpers — merges analysis_results with human feedback.

These functions are pure (no I/O, no Streamlit) so they can be unit
tested. Both the landing page and the "Reportes" tab in ``app.py``
rely on ``build_adjusted_analysis`` so the public dashboard reflects
the human-reviewed truth instead of the raw LLM output.

Multi-label aware: the analyst can correct **one or more** labels per
analysis (see :mod:`src.ui.validacion` and
:mod:`src.analyzer.rag_classifier`). When the reviewer supplies a
multi-label override, the resulting row carries the full
``labels`` list and the primary (highest-severity) override is
mirrored into the legacy flat ``categoria``/``dimension``/
``justificacion`` fields so single-column consumers keep working.
"""

from __future__ import annotations

# Fields the human reviewer is allowed to override.  Keep this list in
# sync with the form in ``src/ui/validacion.py`` and the columns of
# ``AnalysisFeedbackModel``.
ADJUSTABLE_FIELDS: tuple[str, ...] = (
    "categoria",
    "dimension",
    "justificacion",
)


def _to_int(value: object) -> int | None:
    """Safely cast an ``object`` value to ``int``."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _iter_feedback(
    feedback: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Coerce feedback input into a list of plain dicts."""
    if not feedback:
        return []
    return list(feedback)


def _latest_feedback_per_analysis(
    feedback_rows: list[dict[str, object]],
) -> dict[int, dict[str, object]]:
    """Pick the most-recent feedback for each ``analysis_result_id``.

    If two rows share the same id, the one with the latest
    ``updated_at`` wins (lexicographic ISO-8601 sort is correct for
    our timestamps and keeps the function dependency-free).
    """
    latest: dict[int, dict[str, object]] = {}
    for row in feedback_rows:
        ar_id = _to_int(row.get("analysis_result_id"))
        if ar_id is None:
            continue
        existing = latest.get(ar_id)
        if existing is None or str(row.get("updated_at") or "") > str(
            existing.get("updated_at") or ""
        ):
            latest[ar_id] = row
    return latest


def _primary_override(labels: list[dict]) -> dict[str, object]:
    """Pick the primary override label (highest severity, ties broken by ``orden``)."""
    from src.analyzer.category_mapping import primary_label

    if not labels:
        return {}
    return primary_label(labels)


def _coerce_bool(value: object) -> bool:
    """Strict bool coercion — :func:`bool` treats the string ``"false"`` as truthy.

    Accepts booleans, ints/floats (0 → False) and string literals
    (``"true"`` / ``"false"`` / ``"yes"`` / ``"si"`` / ``"sí"`` /
    ``"1"``).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "si", "sí"}
    return False


def _is_violent_label(label: dict | None) -> bool:
    """Decide whether a single override label carries violence.

    The category alone is **not** enough: ``VDG_SALVAGUARDA_FALSO_POSITIVO``
    (cat 6) contains micromachismos (6.1) and humor hostil (6.2) which
    ARE violence. Only the **salvaguarda sub-dimension** (6.3) flagged
    as ``es_falso_positivo_probable=true`` cancels the alert — i.e. the
    reviewer is signalling that the candidate detection is a denouncement,
    quote, or endogrupal re-appropriation, not actual violence.
    """
    if not label:
        return False
    cat = str(label.get("categoria") or "")
    if not cat or cat.upper() == "NINGUNA":
        return False
    if cat.upper() == "VDG_SALVAGUARDA_FALSO_POSITIVO":
        dim = str(label.get("dimension") or "")
        if dim == "6.3" and _coerce_bool(label.get("es_falso_positivo_probable")):
            return False
    return True


def _is_violent_category(cat: str) -> bool:
    """Backward-compatible wrapper: True iff ``cat`` represents violence.

    Used by callers that only have a category string (no dimension /
    false-positive flag). Returns ``True`` for all 6 canonical VDG
    categories — including cat 6 (control de resistencia / salvaguarda),
    since cat 6.1 / 6.2 *are* violence. Use :func:`_is_violent_label`
    when the full label is available, because cat 6.3 with
    ``es_falso_positivo_probable=true`` is the one case that should
    NOT count as violence.
    """
    if not cat:
        return True
    if cat.upper() == "NINGUNA":
        return False
    return True


def build_adjusted_analysis(
    analysis_rows: list[dict[str, object]] | None,
    feedback_rows: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Return a list of analysis rows with human corrections applied.

    For each analysis row whose id appears in ``feedback_rows`` with
    ``agrees='false'``:

    - If the feedback carries a multi-label ``labels`` list, that list
      replaces the analysis ``labels`` field and the primary override
      (highest severity) is mirrored into the legacy flat
      ``categoria``/``dimension``/``justificacion`` fields.
    - Otherwise the legacy single-label fields in :data:`ADJUSTABLE_FIELDS`
      are overwritten by the matching ``corrected_*`` value.

    Each returned row has two extra keys:

    - ``adjusted_by_human``: ``True`` if any field was overridden.
    - ``has_feedback``: ``True`` if any feedback row exists for the id
      (whether the reviewer agreed or not).

    ``analysis_results`` rows are never modified — only this derived
    view.
    """
    rows: list[dict[str, object]] = list(analysis_rows or [])
    by_id = _latest_feedback_per_analysis(_iter_feedback(feedback_rows))

    adjusted: list[dict[str, object]] = []
    for row in rows:
        out: dict[str, object] = dict(row)
        ar_id = _to_int(row.get("id"))
        fb = by_id.get(ar_id) if ar_id is not None else None

        if fb is None:
            out["adjusted_by_human"] = False
            out["has_feedback"] = False
            adjusted.append(out)
            continue

        out["has_feedback"] = True
        if str(fb.get("agrees") or "").lower() != "false":
            # Reviewer agreed — keep original analysis untouched.
            out["adjusted_by_human"] = False
            adjusted.append(out)
            continue

        # CODIGO_99 / VIOLENCIA_COMUN rows are immutable — the reviewer
        # cannot "correct" trash digital or violence without gender bias.
        if row.get("exclusion_label"):
            out["adjusted_by_human"] = False
            adjusted.append(out)
            continue

        # Reviewer disagreed — apply overrides.
        override_labels = list(fb.get("labels") or [])
        changed = False

        if override_labels:
            out["labels"] = override_labels
            primary = _primary_override(override_labels)
            out["categoria"] = primary.get("categoria") or out.get("categoria")
            if primary.get("dimension"):
                out["dimension"] = primary["dimension"]
            if primary.get("justificacion"):
                out["justificacion"] = primary["justificacion"]
            changed = True

            out["tiene_violencia"] = "true" if _is_violent_label(primary) else "false"
        else:
            # Legacy single-label fallback.
            corrected_cat = fb.get("corrected_categoria")
            corrected_dim = fb.get("corrected_dimension")
            if corrected_cat:
                out["categoria"] = corrected_cat
                changed = True
            if corrected_dim:
                out["dimension"] = corrected_dim
                changed = True
            if fb.get("corrected_justificacion"):
                out["justificacion"] = fb["corrected_justificacion"]
                changed = True

            out["tiene_violencia"] = (
                "true" if _is_violent_category(str(corrected_cat or "")) else "false"
            )

        out["adjusted_by_human"] = changed
        adjusted.append(out)

    return adjusted


def compute_adjustment_breakdown(
    adjusted_rows: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Return the % of analysis rows adjusted by humans vs autonomous.

    Args:
        adjusted_rows: Output of :func:`build_adjusted_analysis`.

    Returns:
        Dictionary with keys ``adjusted_pct``, ``autonomous_pct`` and
        ``total``. Sums to 100 (rounded to 1 decimal).

        ``adjusted_count`` counts only rows where the reviewer
        **disagreed** (``adjusted_by_human=True``). For the broader
        question "how many rows have been validated by a human at all"
        (agreement OR disagreement), use :func:`compute_validation_breakdown`.
    """
    rows = list(adjusted_rows or [])
    total = len(rows)
    if total == 0:
        return {"adjusted_pct": 0.0, "autonomous_pct": 0.0, "total": 0}

    adjusted = sum(1 for r in rows if r.get("adjusted_by_human"))
    adjusted_pct = round(adjusted / total * 100.0, 1)
    return {
        "adjusted_pct": adjusted_pct,
        "autonomous_pct": round(100.0 - adjusted_pct, 1),
        "total": total,
        "adjusted_count": adjusted,
    }


def compute_validation_breakdown(
    adjusted_rows: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Return the share of rows that have any human feedback (agree/disagree).

    Args:
        adjusted_rows: Output of :func:`build_adjusted_analysis`.

    Returns:
        Dictionary with keys ``validated_pct`` (rows with feedback,
        agreed OR disagreed, relative to the net analysisable total),
        ``pending_pct`` (rows awaiting human review), ``validated_count``,
        ``agreed_count``, ``disagreed_count``, ``pending_count`` and
        ``total`` (original count) + ``net_total`` (excluding basura
        digital and violencia común per Reglas 2-5).

    This is the right breakdown for KPIs that ask "¿qué porcentaje del
    dataset fue revisado por humanos?", as opposed to the narrower
    :func:`compute_adjustment_breakdown` which only counts rows where
    the reviewer *disagreed* with the AI (i.e. applied a correction).
    """
    rows = list(adjusted_rows or [])
    total = len(rows)
    if total == 0:
        return {
            "validated_pct": 0.0,
            "pending_pct": 0.0,
            "validated_count": 0,
            "agreed_count": 0,
            "disagreed_count": 0,
            "pending_count": 0,
            "total": 0,
            "net_total": 0,
        }

    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}

    def _is_excluded(r: dict) -> bool:
        return (r.get("exclusion_label") or "") in _exclusion

    analysable = [r for r in rows if not _is_excluded(r)]
    net_total = len(analysable)

    agreed = sum(1 for r in analysable if r.get("has_feedback") and not r.get("adjusted_by_human"))
    disagreed = sum(1 for r in analysable if r.get("adjusted_by_human"))
    validated = agreed + disagreed
    pending = net_total - validated
    validated_pct = round(validated / net_total * 100.0, 1) if net_total else 0.0
    return {
        "validated_pct": validated_pct,
        "pending_pct": round(100.0 - validated_pct, 1),
        "validated_count": validated,
        "agreed_count": agreed,
        "disagreed_count": disagreed,
        "pending_count": pending,
        "total": total,
        "net_total": net_total,
    }


def join_feedback_with_analysis(
    feedback_joined: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Return comparison rows for the 'Análisis corregidos' sub-section.

    ``feedback_joined`` is the output of
    :meth:`Database.get_feedback_joined_with_analysis` — it already
    contains both sides. This helper flattens/normalizes so the UI
    can render a clean side-by-side table.
    """
    rows: list[dict[str, object]] = []
    for r in feedback_joined or []:
        fb_meta = r.get("feedback")
        fb_dict: dict[str, object] = fb_meta if isinstance(fb_meta, dict) else {}
        rows.append(
            {
                "analysis_id": r.get("id"),
                "content_type": r.get("content_type"),
                "content_id": r.get("content_id"),
                "text_snapshot": (str(r.get("text_snapshot") or ""))[:200],
                "agrees": r.get("agrees"),
                "reason": r.get("reason"),
                "original_categoria": r.get("original_categoria"),
                "original_dimension": r.get("original_dimension"),
                "original_justificacion": r.get("original_justificacion"),
                "corrected_categoria": r.get("corrected_categoria"),
                "corrected_dimension": r.get("corrected_dimension"),
                "corrected_justificacion": r.get("corrected_justificacion"),
                "indexed_in_chromadb": fb_dict.get("indexed_in_chromadb"),
                "updated_at": r.get("updated_at"),
            }
        )
    return rows


__all__ = [
    "ADJUSTABLE_FIELDS",
    "build_adjusted_analysis",
    "compute_adjustment_breakdown",
    "join_feedback_with_analysis",
]
