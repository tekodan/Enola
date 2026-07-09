"""Reporte de fiabilidad y valores perdidos (Regla 1 del documento).

Implements the three algorithmic steps described in ``REGLA 1
DEFINITIVA PARA ENOLA: DEPURACIÓN DE LA MATRIZ Y VALORES PERDIDOS``:

* **Paso 1.1 — Escaneo y Detección de Errores**: scan 100% of rows and
  isolate those with empty/NaN/null payloads or pure noise. These are
  marked with the sentinel ``exclusion_label = "CODIGO_99"`` (basura
  digital) or ``"VIOLENCIA_COMUN"`` (aggression without gender bias).
* **Paso 1.2 — Asignación de Código**: the rows are NOT deleted — they
  carry the exclusion sentinel and remain in the database so the
  frequency distribution can be computed properly.
* **Paso 1.3 — Reporte de Fiabilidad y Alerta**: if the share of
  CODIGO_99 rows exceeds 5% a *preventiva* warning is emitted, and
  if it exceeds 10% a *CRÍTICA* alert is emitted (instrument stability
  problem).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
)


@dataclass(frozen=True)
class ReliabilityReport:
    """Reporte de fiabilidad (Paso 1.3)."""

    total: int
    n_basura_digital: int
    n_violencia_comun: int
    pct_basura: float
    pct_violencia_comun: float
    nivel: str  # "ok" | "preventiva" | "critica"
    mensaje: str
    detalle_basura_codigos: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "n_basura_digital": self.n_basura_digital,
            "n_violencia_comun": self.n_violencia_comun,
            "pct_basura": self.pct_basura,
            "pct_violencia_comun": self.pct_violencia_comun,
            "nivel": self.nivel,
            "mensaje": self.mensaje,
            "detalle_basura_codigos": dict(self.detalle_basura_codigos),
        }


def _is_basura_digital(row: dict) -> bool:
    return row.get("exclusion_label") == EXCLUSION_BASURA_DIGITAL


def _is_violencia_comun(row: dict) -> bool:
    return row.get("exclusion_label") == EXCLUSION_VIOLENCIA_COMUN


def calcular_valores_perdidos(analysis: Sequence[dict] | Iterable[dict]) -> ReliabilityReport:
    """Calcular el reporte de fiabilidad sobre los análisis.

    ``analysis`` is an iterable of ``analysis_results`` dicts (typically
    coming from ``Database.get_analysis_results()``).

    Returns a :class:`ReliabilityReport` with the percentage of missing
    values (CODIGO_99), the share of violencia-común exclusions, the
    derived alert level, and the exact wording mandated by the spec.
    """
    rows = list(analysis)
    total = len(rows)

    if total == 0:
        return ReliabilityReport(
            total=0,
            n_basura_digital=0,
            n_violencia_comun=0,
            pct_basura=0.0,
            pct_violencia_comun=0.0,
            nivel="ok",
            mensaje="Sin análisis cargados — no se puede calcular el reporte de fiabilidad.",
            detalle_basura_codigos={},
        )

    basura_rows = [r for r in rows if _is_basura_digital(r)]
    comun_rows = [r for r in rows if _is_violencia_comun(r)]
    n_basura = len(basura_rows)
    n_comun = len(comun_rows)

    pct_basura = round(n_basura / total * 100, 2)
    pct_comun = round(n_comun / total * 100, 2)

    detalle_codigos: dict[str, int] = {}
    for r in basura_rows:
        codigo = str(r.get("exclusion_codigo") or "SIN_CODIGO")
        detalle_codigos[codigo] = detalle_codigos.get(codigo, 0) + 1

    if pct_basura > 10:
        nivel = "critica"
        mensaje = (
            f"ALERTA CRÍTICA: el {pct_basura}% de los registros son valores "
            f"perdidos (CÓDIGO 99), superando el umbral del 10%. El instrumento "
            f"de extracción (scraper) tiene problemas de estabilidad y la "
            f"extracción debe revisarse."
        )
    elif pct_basura > 5:
        nivel = "preventiva"
        mensaje = (
            f"Notificación preventiva: el {pct_basura}% de los registros son "
            f"valores perdidos (CÓDIGO 99), por encima del 5% recomendado. "
            f"Revisar la estabilidad del scraper antes de proseguir."
        )
    else:
        nivel = "ok"
        mensaje = (
            f"Reporte de fiabilidad OK: el {pct_basura}% de los registros son "
            f"valores perdidos (CÓDIGO 99), por debajo del 5% recomendado."
        )

    return ReliabilityReport(
        total=total,
        n_basura_digital=n_basura,
        n_violencia_comun=n_comun,
        pct_basura=pct_basura,
        pct_violencia_comun=pct_comun,
        nivel=nivel,
        mensaje=mensaje,
        detalle_basura_codigos=detalle_codigos,
    )


__all__ = [
    "ReliabilityReport",
    "calcular_valores_perdidos",
]
