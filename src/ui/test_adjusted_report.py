"""Unit tests for the pure helpers in ``src.ui.adjusted_report``."""

from __future__ import annotations

from src.ui.adjusted_report import (
    ADJUSTABLE_FIELDS,
    _is_violent_category,
    _is_violent_label,
    build_adjusted_analysis,
    compute_adjustment_breakdown,
    compute_validation_breakdown,
    join_feedback_with_analysis,
)


def _row(ar_id: int, *, cat: str = "VDG_VIOLENCIA_SIMBOLICA", dim: str | None = "1.1") -> dict:
    """Build an analysis_results-shaped dict."""
    return {
        "id": ar_id,
        "content_type": "post",
        "content_id": f"p{ar_id}",
        "categoria": cat,
        "dimension": dim,
        "severidad": "baja",
        "tiene_violencia": "true",
        "justificacion": "AI orig",
        "evidencia": "x",
    }


def _fb(ar_id: int, *, agrees: str, **kwargs: object) -> dict:
    """Build an analysis_feedback-shaped dict."""
    base: dict = {
        "analysis_result_id": ar_id,
        "agrees": agrees,
        "corrected_categoria": None,
        "corrected_dimension": None,
        "corrected_justificacion": None,
        "updated_at": "2024-01-01T00:00:00",
    }
    base.update(kwargs)
    return base


class TestBuildAdjustedAnalysis:
    def test_no_feedback_returns_original_rows_with_flags(self):
        """When there's no feedback every row has ``adjusted_by_human=False``."""
        rows = [_row(1), _row(2)]
        out = build_adjusted_analysis(rows, [])
        assert len(out) == 2
        assert all(r["adjusted_by_human"] is False for r in out)
        assert all(r["has_feedback"] is False for r in out)
        assert out[0]["categoria"] == "VDG_VIOLENCIA_SIMBOLICA"

    def test_agreement_does_not_override(self):
        """Reviewer agreeing keeps the original analysis untouched."""
        rows = [_row(1)]
        fb = [_fb(1, agrees="true")]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["adjusted_by_human"] is False
        assert out[0]["has_feedback"] is True
        assert out[0]["categoria"] == "VDG_VIOLENCIA_SIMBOLICA"

    def test_disagreement_overrides_categoria_dimension_justificacion(self):
        """Disagreement + correction overrides all three fields."""
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                corrected_categoria="VDG_HOSTILIDAD_FEMINICIDIO",
                corrected_dimension="3.1",
                corrected_justificacion="corr",
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        r = out[0]
        assert r["adjusted_by_human"] is True
        assert r["categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert r["dimension"] == "3.1"
        assert r["justificacion"] == "corr"

    def test_disagreement_with_partial_override_only_overrides_set(self):
        """Only categoria corrected → dimension stays original."""
        rows = [_row(1)]
        fb = [_fb(1, agrees="false", corrected_categoria="VDG_MANOSFERA_ANTIFEMINISMO")]
        out = build_adjusted_analysis(rows, fb)
        r = out[0]
        assert r["adjusted_by_human"] is True
        assert r["categoria"] == "VDG_MANOSFERA_ANTIFEMINISMO"
        assert r["dimension"] == "1.1"  # unchanged
        assert r["justificacion"] == "AI orig"  # unchanged

    def test_disagreement_with_empty_overrides_flips_adjusted_to_false(self):
        """Disagreement with no override values → adjusted_by_human stays False."""
        rows = [_row(1)]
        fb = [_fb(1, agrees="false", reason="changed my mind")]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["adjusted_by_human"] is False
        assert out[0]["has_feedback"] is True

    def test_picks_latest_feedback_per_analysis(self):
        """Two feedback rows for the same id → most recent wins."""
        rows = [_row(1)]
        fb = [
            _fb(1, agrees="false", corrected_categoria="VDG_A", updated_at="2024-01-01T00:00:00"),
            _fb(1, agrees="false", corrected_categoria="VDG_B", updated_at="2024-02-01T00:00:00"),
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["categoria"] == "VDG_B"

    def test_rows_without_id_are_skipped_for_lookup_but_kept(self):
        """Rows without an id are kept but never receive overrides."""
        rows = [{"categoria": "VDG_X"}, _row(1)]
        fb = [_fb(1, agrees="false", corrected_categoria="VDG_Y")]
        out = build_adjusted_analysis(rows, fb)
        assert len(out) == 2
        assert out[0]["categoria"] == "VDG_X"
        assert out[0]["adjusted_by_human"] is False
        assert out[1]["categoria"] == "VDG_Y"
        assert out[1]["adjusted_by_human"] is True


class TestAdjustmentBreakdown:
    def test_empty_input_returns_zero(self):
        result = compute_adjustment_breakdown([])
        assert result["total"] == 0
        assert result["adjusted_pct"] == 0.0
        assert result["autonomous_pct"] == 0.0

    def test_breakdown_sums_to_100(self):
        rows: list[dict[str, object]] = [
            {"adjusted_by_human": True},
            {"adjusted_by_human": True},
            {"adjusted_by_human": False},
        ]
        result = compute_adjustment_breakdown(rows)
        assert result["total"] == 3
        assert result["adjusted_count"] == 2
        # 66.7 adjusted, 33.3 autonomous
        assert result["adjusted_pct"] == 66.7
        assert result["autonomous_pct"] == 33.3

    def test_all_adjusted(self):
        rows: list[dict[str, object]] = [
            {"adjusted_by_human": True},
            {"adjusted_by_human": True},
        ]
        result = compute_adjustment_breakdown(rows)
        assert result["adjusted_pct"] == 100.0
        assert result["autonomous_pct"] == 0.0


class TestJoinFeedbackWithAnalysis:
    def test_flattens_row_for_ui(self):
        joined = [
            {
                "id": 1,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "el texto",
                "agrees": "false",
                "reason": "mal",
                "original_categoria": "A",
                "original_dimension": "1.1",
                "original_justificacion": "j1",
                "corrected_categoria": "B",
                "corrected_dimension": "2.1",
                "corrected_justificacion": "j2",
                "feedback": {"indexed_in_chromadb": "true"},
                "updated_at": "2024-02-01",
            }
        ]
        out = join_feedback_with_analysis(joined)
        assert len(out) == 1
        row = out[0]
        assert row["analysis_id"] == 1
        assert row["original_categoria"] == "A"
        assert row["corrected_categoria"] == "B"
        assert row["indexed_in_chromadb"] == "true"
        assert row["text_snapshot"] == "el texto"

    def test_truncates_text_snapshot(self):
        joined: list[dict[str, object]] = [{"text_snapshot": "x" * 500, "feedback": {}, "id": 1}]
        out = join_feedback_with_analysis(joined)
        snap = out[0]["text_snapshot"]
        assert isinstance(snap, str)
        assert len(snap) == 200


def test_adjustable_fields_match_form_contract():
    """Guardrail: ADJUSTABLE_FIELDS is the single source of truth for the form."""
    assert "categoria" in ADJUSTABLE_FIELDS


class TestBuildAdjustedAnalysisMultiLabel:
    """Multi-label aware: when the feedback carries a ``labels`` list,
    it replaces the analysis ``labels`` and the primary (highest
    severity) label is mirrored into the flat fields."""

    def test_multi_label_override_replaces_labels(self):
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                labels=[
                    {
                        "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                        "dimension": "2.1",
                        "severidad": "media",
                        "justificacion": "reclasificado",
                    },
                    {
                        "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                        "dimension": "3.1",
                        "severidad": "alta",
                        "justificacion": "agregado",
                    },
                ],
                corrected_categoria="VDG_HOSTILIDAD_FEMINICIDIO",
                corrected_dimension="3.1",
                corrected_justificacion="agregado",
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["adjusted_by_human"] is True
        assert len(out[0]["labels"]) == 2
        # Primary (highest severity) mirrored to the flat columns.
        assert out[0]["categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert out[0]["dimension"] == "3.1"
        assert out[0]["justificacion"] == "agregado"

    def test_legacy_single_label_override_still_works(self):
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                corrected_categoria="VDG_COSIFICACION_SLUTSHAMING",
                corrected_dimension="2.2",
                corrected_justificacion="zorra",
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["categoria"] == "VDG_COSIFICACION_SLUTSHAMING"
        assert out[0]["dimension"] == "2.2"
        assert out[0]["justificacion"] == "zorra"

    def test_multi_label_override_with_no_legacy_fields(self):
        """Reviewer only used the multi-label form → still applies."""
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                labels=[
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.2",
                        "severidad": "media",
                        "justificacion": "nueva",
                    }
                ],
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["categoria"] == "VDG_VIOLENCIA_SIMBOLICA"
        assert out[0]["dimension"] == "1.2"
        assert out[0]["justificacion"] == "nueva"

    assert "dimension" in ADJUSTABLE_FIELDS
    assert "justificacion" in ADJUSTABLE_FIELDS


class TestTieneViolenciaPropagation:
    """Regla 6 (metrics) requires ``tiene_violencia`` to track the
    reviewer's verdict. Previously a string ``"false"`` (truthy in
    Python) was treated as ``True`` and a category-6 salvaguarda was
    hard-coded as non-violent, producing 17 false negatives out of 57
    feedback rows. These tests pin the correct behaviour."""

    def test_override_to_violent_category_flips_tiene_violencia_true(self):
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                corrected_categoria="VDG_COSIFICACION_SLUTSHAMING",
                corrected_dimension="2.3",
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["tiene_violencia"] == "true"

    def test_override_to_ninguna_flips_tiene_violencia_false(self):
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                corrected_categoria="ninguna",
                corrected_dimension=None,
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["tiene_violencia"] == "false"

    def test_multi_label_override_violent_propagates_true(self):
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                labels=[
                    {
                        "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                        "dimension": "2.3",
                        "severidad": "media",
                    }
                ],
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["tiene_violencia"] == "true"

    def test_salvaguarda_6_3_with_fpp_true_cancels_violence(self):
        """Cat 6.3 with ``es_falso_positivo_probable=true`` is the
        reviewer's signal that the detection is a denouncement, quote
        or endogrupal re-appropriation — NOT actual violence."""
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                labels=[
                    {
                        "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                        "dimension": "6.3",
                        "severidad": "baja",
                        "es_falso_positivo_probable": "true",
                    }
                ],
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["tiene_violencia"] == "false"

    def test_salvaguarda_6_3_with_fpp_false_remains_violent(self):
        """Cat 6.3 with ``es_falso_positivo_probable=false`` is a real
        salvaguarda hit (the reviewer kept the detection)."""
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                labels=[
                    {
                        "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                        "dimension": "6.3",
                        "severidad": "alta",
                        "es_falso_positivo_probable": "false",
                    }
                ],
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["tiene_violencia"] == "true"

    def test_salvaguarda_6_1_and_6_2_are_violent(self):
        """Cat 6.1 (micromachismos) and 6.2 (humor hostil) ARE violence
        regardless of the salvaguarda flag."""
        for dim in ("6.1", "6.2"):
            rows = [_row(1)]
            fb = [
                _fb(
                    1,
                    agrees="false",
                    labels=[
                        {
                            "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                            "dimension": dim,
                            "severidad": "media",
                            "es_falso_positivo_probable": "true",
                        }
                    ],
                )
            ]
            out = build_adjusted_analysis(rows, fb)
            assert out[0]["tiene_violencia"] == "true", f"dim={dim}"

    def test_fpp_string_false_does_not_cancel_violence(self):
        """Regression: bool('false') == True. The string 'false' must
        be coerced to False before being used as a verdict."""
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                labels=[
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.1",
                        "severidad": "media",
                        "es_falso_positivo_probable": "false",
                    }
                ],
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        assert out[0]["tiene_violencia"] == "true"

    def test_fpp_string_true_only_cancels_cat6_dim63(self):
        """Symmetric: ``fpp='true'`` string coerces to ``True``, but the
        salvaguarda cancellation only applies to cat 6.3 — a
        ``VDG_VIOLENCIA_SIMBOLICA`` label with ``fpp=true`` is still
        violence (the flag only makes sense for cat 6 sub-dim 6.3)."""
        rows = [_row(1)]
        fb = [
            _fb(
                1,
                agrees="false",
                labels=[
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.1",
                        "severidad": "media",
                        "es_falso_positivo_probable": "true",
                    }
                ],
            )
        ]
        out = build_adjusted_analysis(rows, fb)
        # NOT cancelled because it's not cat 6 / 6.3.
        assert out[0]["tiene_violencia"] == "true"


class TestIsViolentLabel:
    """Direct unit tests for ``_is_violent_label`` and
    ``_is_violent_category`` so the salvage logic is locked down."""

    def test_six_canonical_categories_are_violent(self):
        for cat in (
            "VDG_VIOLENCIA_SIMBOLICA",
            "VDG_COSIFICACION_SLUTSHAMING",
            "VDG_HOSTILIDAD_FEMINICIDIO",
            "VDG_MANOSFERA_ANTIFEMINISMO",
            "VDG_DESACREDITACION_ACTIVISTAS",
            "VDG_SALVAGUARDA_FALSO_POSITIVO",
        ):
            assert _is_violent_category(cat) is True, cat

    def test_ninguna_is_not_violent(self):
        assert _is_violent_category("ninguna") is False
        assert _is_violent_category("") is True  # legacy default

    def test_legacy_wrapper_does_not_consult_dimension(self):
        """The legacy ``_is_violent_category`` is a category-only check;
        ``_is_violent_label`` is the granular version that consults
        dimension + fpp. Cat 6 IS violent at the wrapper level."""
        assert _is_violent_category("VDG_SALVAGUARDA_FALSO_POSITIVO") is True

    def test_label_six_three_with_fpp_true_is_not_violent(self):
        assert (
            _is_violent_label(
                {
                    "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                    "dimension": "6.3",
                    "es_falso_positivo_probable": "true",
                }
            )
            is False
        )

    def test_label_six_three_with_fpp_false_is_violent(self):
        assert (
            _is_violent_label(
                {
                    "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                    "dimension": "6.3",
                    "es_falso_positivo_probable": "false",
                }
            )
            is True
        )

    def test_label_six_one_or_six_two_always_violent(self):
        for dim in ("6.1", "6.2"):
            assert (
                _is_violent_label(
                    {
                        "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                        "dimension": dim,
                        "es_falso_positivo_probable": "true",
                    }
                )
                is True
            ), dim


class TestValidationBreakdown:
    """Landing KPI 'Estado de Validación Humana' was previously wired to
    ``compute_adjustment_breakdown`` — which only counts *disagreements*
    (``adjusted_by_human=True``). The card therefore under-reported the
    actual human-review coverage: 21/69 instead of 57/69 in production.
    :func:`compute_validation_breakdown` is the correct denominator —
    agreement OR disagreement = validation completed."""

    def test_empty_input_returns_zero(self):
        result = compute_validation_breakdown([])
        assert result["total"] == 0
        assert result["validated_count"] == 0
        assert result["agreed_count"] == 0
        assert result["disagreed_count"] == 0
        assert result["pending_count"] == 0
        assert result["validated_pct"] == 0.0
        assert result["pending_pct"] == 0.0

    def test_only_disagreements_equals_adjusted(self):
        """When every row was corrected, validated == adjusted."""
        rows: list[dict[str, object]] = [
            {"has_feedback": True, "adjusted_by_human": True},
            {"has_feedback": True, "adjusted_by_human": True},
            {"has_feedback": False, "adjusted_by_human": False},
        ]
        result = compute_validation_breakdown(rows)
        assert result["validated_count"] == 2
        assert result["disagreed_count"] == 2
        assert result["agreed_count"] == 0
        assert result["pending_count"] == 1
        assert result["validated_pct"] == 66.7
        assert result["pending_pct"] == 33.3

    def test_agreement_plus_disagreement_counts_as_validated(self):
        """Regression: agreement (agrees=true) was being IGNORED by the
        landing card when only ``compute_adjustment_breakdown`` was used.
        Now both flows count toward ``validated_pct``."""
        rows: list[dict[str, object]] = [
            {"has_feedback": True, "adjusted_by_human": True},  # disagree
            {"has_feedback": True, "adjusted_by_human": False},  # agree
            {"has_feedback": True, "adjusted_by_human": False},  # agree
            {"has_feedback": False, "adjusted_by_human": False},  # pending
        ]
        result = compute_validation_breakdown(rows)
        assert result["validated_count"] == 3
        assert result["agreed_count"] == 2
        assert result["disagreed_count"] == 1
        assert result["pending_count"] == 1
        assert result["validated_pct"] == 75.0
        assert result["pending_pct"] == 25.0

    def test_adjusted_breakdown_is_narrower_than_validation(self):
        """``adjusted_pct`` ≤ ``validated_pct`` always."""
        rows: list[dict[str, object]] = [
            {"has_feedback": True, "adjusted_by_human": True},
            {"has_feedback": True, "adjusted_by_human": False},
            {"has_feedback": False, "adjusted_by_human": False},
        ]
        adjusted = compute_adjustment_breakdown(rows)
        validation = compute_validation_breakdown(rows)
        assert adjusted["adjusted_pct"] <= validation["validated_pct"]
        assert adjusted["adjusted_count"] == 1
        assert validation["validated_count"] == 2

    def test_validation_breakdown_sums_to_total(self):
        rows: list[dict[str, object]] = [
            {"has_feedback": True, "adjusted_by_human": True},
            {"has_feedback": True, "adjusted_by_human": False},
            {"has_feedback": False, "adjusted_by_human": False},
            {"has_feedback": False, "adjusted_by_human": False},
        ]
        result = compute_validation_breakdown(rows)
        assert (
            result["agreed_count"] + result["disagreed_count"] + result["pending_count"]
        ) == result["total"]


class TestLandingKPIsWiring:
    """Lock down the wiring between the landing page KPIs and the
    underlying data sources. These tests assert *what numbers should
    be shown*, not just that the helpers exist.

    Regression: the previous landing page showed:
      - 'Precisión del Modelo RAG' = agrees/total (~61%) — wrong metric.
      - 'Estado de Validación Humana' = adjusted/total (~30%) — wrong
        denominator.
    """

    def test_rag_precision_pct_returns_sklearn_precision(self):
        from src.ui.nicegui_app.pages.inicio import _rag_precision_pct

        # metrics payload mirrors the dict shape produced by
        # src.report.metrics.render_metrics_report.
        metrics = {
            "Precisión": 1.0,
            "Sensibilidad (Recall)": 0.94,
            "F1-Score": 0.97,
            "Soporte": 57,
        }
        assert _rag_precision_pct(metrics) == 100.0

    def test_rag_precision_pct_falls_back_when_metrics_missing(self):
        from src.ui.nicegui_app.pages.inicio import _rag_precision_pct

        assert _rag_precision_pct({}) == 0.0
        assert _rag_precision_pct({"Precisión": None}) == 0.0
        # Not a number — fallback.
        assert _rag_precision_pct({"Precisión": "n/a"}) == 0.0

    def test_precision_subtitle_names_the_metric(self):
        """Subtitle must mention the formal definition (VP / (VP + FP))
        so users don't read it as the AI-vs-human agreement ratio."""
        from src.ui.nicegui_app.pages.inicio import _precision_subtitle

        # No feedback yet.
        assert "feedback" in _precision_subtitle({}, total=69).lower()
        # With feedback.
        out = _precision_subtitle({"Precisión": 1.0, "Soporte": 57}, total=69)
        assert "VP / (VP + FP)" in out
        assert "57" in out
        assert "82.6%" in out  # 57/69 coverage

    def test_validation_subtitle_includes_breakdown(self):
        from src.ui.nicegui_app.pages.inicio import _validation_subtitle

        validation = {
            "validated_count": 57,
            "agreed_count": 36,
            "disagreed_count": 21,
            "pending_count": 12,
            "total": 69,
        }
        out = _validation_subtitle(validation, adjusted_count=21)
        assert "57 revisados" in out
        assert "36 de acuerdo" in out
        assert "21 corregidos" in out
        assert "12 pendientes" in out
        assert "69" in out

    def test_validation_subtitle_empty_dataset(self):
        from src.ui.nicegui_app.pages.inicio import _validation_subtitle

        out = _validation_subtitle(
            {
                "validated_count": 0,
                "agreed_count": 0,
                "disagreed_count": 0,
                "pending_count": 0,
                "total": 0,
            },
            adjusted_count=0,
        )
        assert "Sin análisis" in out
