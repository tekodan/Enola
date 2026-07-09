# src/report/__init__.py
"""Report generation, statistical and reliability computations.

Modules
-------

* :mod:`src.report.reliability` — Regla 1: reporte de valores perdidos
  (CÓDIGO 99) con alertas 5% / 10% según la metodología.
* :mod:`src.report.stats` — Reglas 2, 3 y 4: distribución de
  frecuencias, moda y análisis bivariado (crosstabs).
* :mod:`src.report.metrics` — Regla 6: métricas de fiabilidad y
  validez de la IA (matriz de confusión, precisión, sensibilidad,
  F1-Score) usando sklearn.
"""

from src.report.metrics import (
    ConfusionMatrix,
    ReliabilityMetrics,
    compute_confusion_matrix,
    compute_reliability_metrics,
    render_metrics_report,
)
from src.report.reliability import ReliabilityReport, calcular_valores_perdidos
from src.report.stats import (
    CrosstabResult,
    FrequencyRow,
    FrequencyTable,
    ModeResult,
    compute_crosstabs,
    compute_frequency_distribution,
    compute_mode,
)

__all__ = [
    "ReliabilityReport",
    "calcular_valores_perdidos",
    "FrequencyRow",
    "FrequencyTable",
    "ModeResult",
    "compute_frequency_distribution",
    "compute_mode",
    "CrosstabResult",
    "compute_crosstabs",
    "ConfusionMatrix",
    "ReliabilityMetrics",
    "compute_confusion_matrix",
    "compute_reliability_metrics",
    "render_metrics_report",
]
