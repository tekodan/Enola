"""Reliability and validity metrics for the RAG classifier (Regla 6).

Implements the three algorithmic steps described in ``REGLA 6
DEFINITIVA: EVALUACIÓN DE CONFIABILIDAD Y VALIDEZ DEL INSTRUMENTO``:

* **Paso 6.1 — Matriz de Confusión**: cruzar las predicciones de la
  máquina con las anotaciones humanas (``analysis_feedback``) y emitir
  VP / VN / FP / FN.
* **Paso 6.2 — Métricas de Confiabilidad Algorítmica**: Precisión,
  Sensibilidad (Recall) y F1-Score via ``sklearn.metrics``.
* **Paso 6.3 — Reporte de Validación**: emitir el reporte final.

The classification is performed at the **binary "any violence vs no
violence"** level (matching the document's VP/VN framing). The
6-category taxonomy is preserved as a richer per-class breakdown when
enough feedback is available.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
)

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class ConfusionMatrix:
    """Matriz de confusión binaria (Paso 6.1)."""

    verdaderos_positivos: int
    verdaderos_negativos: int
    falsos_positivos: int
    falsos_negativos: int

    @property
    def total(self) -> int:
        return (
            self.verdaderos_positivos
            + self.verdaderos_negativos
            + self.falsos_positivos
            + self.falsos_negativos
        )

    def to_dict(self) -> dict:
        return {
            "VP": self.verdaderos_positivos,
            "VN": self.verdaderos_negativos,
            "FP": self.falsos_positivos,
            "FN": self.falsos_negativos,
            "Total": self.total,
        }

    def to_dataframe(self) -> pd.DataFrame:
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "Real \\ Predicho": "Con violencia",
                    "Pred: Sí": self.verdaderos_positivos,
                    "Pred: No": self.falsos_negativos,
                },
                {
                    "Real \\ Predicho": "Sin violencia",
                    "Pred: Sí": self.falsos_positivos,
                    "Pred: No": self.verdaderos_negativos,
                },
            ]
        )


@dataclass(frozen=True)
class ReliabilityMetrics:
    """Métricas de fiabilidad (Paso 6.2)."""

    precision: float
    sensibilidad: float  # recall
    f1_score: float
    soporte: int  # total de casos evaluados

    def to_dict(self) -> dict:
        return {
            "Precisión": round(self.precision, 4),
            "Sensibilidad (Recall)": round(self.sensibilidad, 4),
            "F1-Score": round(self.f1_score, 4),
            "Soporte": self.soporte,
        }


def _to_binary_pred(row: dict) -> str:
    """Return ``"violencia"`` or ``"no_violencia"`` for a predicted row."""
    if row.get("exclusion_label") in {EXCLUSION_BASURA_DIGITAL, EXCLUSION_VIOLENCIA_COMUN}:
        return "no_violencia"
    return "violencia" if row.get("tiene_violencia") == "true" else "no_violencia"


def _to_binary_truth(row: dict, prediction: str) -> str:
    """Return the ground truth label from a human feedback row.

    * ``agrees="true"`` → the reviewer confirmed the AI prediction, so the
      row is counted as a true positive or true negative.
    * ``agrees="false"`` → the reviewer supplied the ground-truth category;
      use ``corrected_categoria`` if present (else "no_violencia").
    """
    if row.get("agrees") == "true":
        return prediction
    cat = row.get("corrected_categoria")
    if cat and cat != "ninguna":
        return "violencia"
    return "no_violencia"


def compute_confusion_matrix(
    feedback: Sequence[dict],
    *,
    analysis_lookup: Mapping[Any, dict] | None = None,
) -> ConfusionMatrix:
    """Compute the binary confusion matrix (Paso 6.1).

    ``feedback`` is a list of ``analysis_feedback`` dicts (each row
    corresponds to one human review). ``analysis_lookup`` is an optional
    mapping ``analysis_result_id -> analysis_results row`` used to
    recover the AI's prediction when ``agrees="true"``.
    """
    lookup = analysis_lookup or {}

    vp = vn = fp = fn = 0

    for fb in feedback:
        ar_id = fb.get("analysis_result_id")
        analysis_row = lookup.get(ar_id) if ar_id is not None else None
        pred = _to_binary_pred(analysis_row) if analysis_row else None
        if pred is None:
            # Without the linked analysis row we cannot compute the
            # prediction side of the matrix.
            continue

        truth = _to_binary_truth(fb, pred)

        if pred == "violencia" and truth == "violencia":
            vp += 1
        elif pred == "no_violencia" and truth == "no_violencia":
            vn += 1
        elif pred == "violencia" and truth == "no_violencia":
            fp += 1
        else:
            fn += 1

    return ConfusionMatrix(
        verdaderos_positivos=vp,
        verdaderos_negativos=vn,
        falsos_positivos=fp,
        falsos_negativos=fn,
    )


def compute_reliability_metrics(
    feedback: Sequence[dict],
    *,
    analysis_lookup: Mapping[Any, dict] | None = None,
) -> ReliabilityMetrics:
    """Compute Precisión, Sensibilidad and F1-Score (Paso 6.2).

    Uses ``sklearn.metrics`` for arithmetic correctness.
    """
    from sklearn.metrics import f1_score, precision_score, recall_score

    lookup = analysis_lookup or {}

    y_true: list[int] = []
    y_pred: list[int] = []

    for fb in feedback:
        ar_id = fb.get("analysis_result_id")
        analysis_row = lookup.get(ar_id) if ar_id is not None else None
        if analysis_row is None:
            continue
        pred = _to_binary_pred(analysis_row)
        truth = _to_binary_truth(fb, pred)
        y_pred.append(1 if pred == "violencia" else 0)
        y_true.append(1 if truth == "violencia" else 0)

    soporte = len(y_true)
    if soporte == 0:
        return ReliabilityMetrics(
            precision=0.0,
            sensibilidad=0.0,
            f1_score=0.0,
            soporte=0,
        )

    # zero_division=0 keeps the metrics well-defined when a class is
    # entirely absent from the predictions / truths.
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    return ReliabilityMetrics(
        precision=float(prec),
        sensibilidad=float(rec),
        f1_score=float(f1),
        soporte=soporte,
    )


def render_metrics_report(
    feedback: Sequence[dict],
    *,
    analysis_lookup: Mapping[Any, dict] | None = None,
) -> dict:
    """Emit the full report (Paso 6.3) as a dict for the UI layer."""
    cm = compute_confusion_matrix(feedback, analysis_lookup=analysis_lookup)
    metrics = compute_reliability_metrics(feedback, analysis_lookup=analysis_lookup)
    return {
        "confusion_matrix": cm.to_dict(),
        "confusion_matrix_df": cm.to_dataframe(),
        "metrics": metrics.to_dict(),
        "soporte": metrics.soporte,
    }


__all__ = [
    "ConfusionMatrix",
    "ReliabilityMetrics",
    "compute_confusion_matrix",
    "compute_reliability_metrics",
    "render_metrics_report",
]
