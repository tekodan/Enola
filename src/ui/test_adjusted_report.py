"""Unit tests for the pure helpers in ``src.ui.adjusted_report``."""

from __future__ import annotations

from src.ui.adjusted_report import (
    ADJUSTABLE_FIELDS,
    build_adjusted_analysis,
    compute_adjustment_breakdown,
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
