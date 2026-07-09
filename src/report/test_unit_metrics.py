"""Unit tests for the reliability/validity metrics module (Regla 6)."""

from src.report.metrics import (
    compute_confusion_matrix,
    compute_reliability_metrics,
    render_metrics_report,
)


def _analysis(id_, *, tiene: bool, cat: str = "ninguna", exclusion=None):
    return {
        "id": id_,
        "tiene_violencia": "true" if tiene else "false",
        "categoria": cat,
        "exclusion_label": exclusion,
    }


def _fb(ar_id, *, agrees, corrected_cat=None):
    return {
        "analysis_result_id": ar_id,
        "agrees": agrees,
        "corrected_categoria": corrected_cat,
    }


class TestComputeConfusionMatrix:
    """Paso 6.1 — VP, VN, FP, FN."""

    def test_perfect_match(self):
        """All agrees='true' on correct predictions → all TP/TN."""
        analysis = {
            1: _analysis(1, tiene=True, cat="VDG_HOSTILIDAD_FEMINICIDIO"),
            2: _analysis(2, tiene=False),
        }
        feedback = [_fb(1, agrees="true"), _fb(2, agrees="true")]
        cm = compute_confusion_matrix(feedback, analysis_lookup=analysis)
        # When agrees='true' the truth equals the AI prediction.
        assert cm.verdaderos_positivos == 1
        assert cm.verdaderos_negativos == 1
        assert cm.falsos_positivos == 0
        assert cm.falsos_negativos == 0

    def test_disagreement_with_override(self):
        """AI said no-violence, human said violence → FN (missed violence)."""
        analysis = {1: _analysis(1, tiene=False)}
        feedback = [_fb(1, agrees="false", corrected_cat="VDG_HOSTILIDAD_FEMINICIDIO")]
        cm = compute_confusion_matrix(feedback, analysis_lookup=analysis)
        assert cm.falsos_negativos == 1
        assert cm.verdaderos_positivos == 0

    def test_false_positive(self):
        """AI said violence, human said no violence → FP."""
        analysis = {1: _analysis(1, tiene=True, cat="VDG_VIOLENCIA_SIMBOLICA")}
        feedback = [_fb(1, agrees="false", corrected_cat="ninguna")]
        cm = compute_confusion_matrix(feedback, analysis_lookup=analysis)
        assert cm.falsos_positivos == 1

    def test_basura_excluded(self):
        """Rows with exclusion_label are treated as no-violence predictions."""
        analysis = {1: _analysis(1, tiene=True, exclusion="CODIGO_99")}
        feedback = [_fb(1, agrees="true")]  # ground truth matches prediction
        cm = compute_confusion_matrix(feedback, analysis_lookup=analysis)
        # predicted=no_violence (basura short-circuits); truth=no_violence
        assert cm.verdaderos_negativos == 1
        assert cm.falsos_negativos == 0

    def test_missing_analysis_skipped(self):
        """If the linked analysis row is unavailable, the row is skipped."""
        feedback = [_fb(99, agrees="true")]
        cm = compute_confusion_matrix(feedback, analysis_lookup={})
        assert cm.total == 0

    def test_to_dataframe_shape(self):
        analysis = {1: _analysis(1, tiene=True), 2: _analysis(2, tiene=False)}
        feedback = [_fb(1, agrees="true"), _fb(2, agrees="false", corrected_cat="VDG_X")]
        cm = compute_confusion_matrix(feedback, analysis_lookup=analysis)
        df = cm.to_dataframe()
        assert df.shape == (2, 3)
        assert "Real \\ Predicho" in df.columns


class TestComputeReliabilityMetrics:
    """Paso 6.2 — Precisión, Sensibilidad, F1."""

    def test_perfect_classifier(self):
        analysis = {
            1: _analysis(1, tiene=True, cat="VDG_HOSTILIDAD_FEMINICIDIO"),
            2: _analysis(2, tiene=True),
            3: _analysis(3, tiene=False),
            4: _analysis(4, tiene=False),
        }
        feedback = [
            _fb(1, agrees="true"),
            _fb(2, agrees="true"),
            _fb(3, agrees="true"),
            _fb(4, agrees="true"),
        ]
        m = compute_reliability_metrics(feedback, analysis_lookup=analysis)
        assert m.precision == 1.0
        assert m.sensibilidad == 1.0
        assert m.f1_score == 1.0
        assert m.soporte == 4

    def test_partial_match(self):
        analysis = {
            1: _analysis(1, tiene=True),
            2: _analysis(2, tiene=False),
            3: _analysis(3, tiene=False),
            4: _analysis(4, tiene=False),
        }
        feedback = [
            _fb(1, agrees="true"),
            _fb(2, agrees="true"),
            _fb(3, agrees="false", corrected_cat="VDG_X"),  # FP
            _fb(4, agrees="true"),
        ]
        m = compute_reliability_metrics(feedback, analysis_lookup=analysis)
        # Row 1: pred=viol, agrees=true → truth=viol → TP
        # Row 2: pred=no_viol, agrees=true → truth=no_viol → TN
        # Row 3: pred=no_viol, agrees=false → truth=viol → FN
        # Row 4: pred=no_viol, agrees=true → truth=no_viol → TN
        # → 1 TP, 2 TN, 0 FP, 1 FN
        # precision = TP / (TP + FP) = 1 / 1 = 1.0
        assert m.precision == 1.0
        # recall = TP / (TP + FN) = 1 / 2 = 0.5
        assert abs(m.sensibilidad - 0.5) < 0.01
        # F1 = 2*P*R/(P+R) = 2*1*0.5/1.5 ≈ 0.6667
        assert abs(m.f1_score - 0.6667) < 0.01

    def test_empty_returns_zeros(self):
        m = compute_reliability_metrics([])
        assert m.soporte == 0
        assert m.precision == 0.0
        assert m.f1_score == 0.0


class TestRenderMetricsReport:
    """Paso 6.3 — Reporte de Validación final."""

    def test_returns_complete_payload(self):
        analysis = {1: _analysis(1, tiene=True), 2: _analysis(2, tiene=False)}
        feedback = [_fb(1, agrees="true"), _fb(2, agrees="true")]
        report = render_metrics_report(feedback, analysis_lookup=analysis)
        assert "confusion_matrix" in report
        assert "metrics" in report
        assert report["soporte"] == 2
        assert report["metrics"]["Precisión"] == 1.0
        assert report["metrics"]["Sensibilidad (Recall)"] == 1.0
        assert report["metrics"]["F1-Score"] == 1.0
