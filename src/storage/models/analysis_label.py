"""AnalysisLabelModel - one row per label assigned to an analysis result.

A single analyzed post/comment can carry multiple labels (different
``VDG_*`` categories, sub-dimensions, each with its own justification,
evidence, markers, severity, etc.). The flat ``analysis_results`` table
still stores the **primary** label (highest severity, ties broken by
LLM order) in its single ``categoria``/``dimension``/``severidad``/
``justificacion``/``evidencia`` columns for fast queries and
backwards-compat; this side table preserves the full ordered list.

Cascade-delete on ``analysis_result_id`` keeps the table clean when an
analysis is removed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.storage.base import Base


class AnalysisLabelModel(Base):
    """SQLAlchemy model for the ``analysis_labels`` table.

    Each row is one label applied to an analysis. ``orden`` preserves
    the order in which the LLM emitted the labels (0-based).
    """

    __tablename__ = "analysis_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_result_id = Column(
        Integer,
        ForeignKey("analysis_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orden = Column(Integer, nullable=False, default=0)

    categoria = Column(String, nullable=False)
    dimension = Column(String, nullable=True)
    severidad = Column(String, default="ninguna", nullable=False)

    justificacion = Column(Text, default="", nullable=False)
    evidencia = Column(Text, default="", nullable=False)
    regla_disparada = Column(String, nullable=True)
    marcadores_detectados = Column(Text, nullable=True)  # JSON array
    confianza = Column(String, nullable=True)
    score_ajuste = Column(String, nullable=True)
    es_falso_positivo_probable = Column(String, default="false", nullable=False)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    analysis_result = relationship("AnalysisResultModel")

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-friendly dict (decodes ``marcadores`` back to list)."""
        import json

        marcadores_raw = self.marcadores_detectados  # type: ignore[assignment]
        marcadores: list[str] = []
        if marcadores_raw is not None:
            try:
                decoded = json.loads(str(marcadores_raw))
                if isinstance(decoded, list):
                    marcadores = [str(m) for m in decoded if m]
            except (ValueError, TypeError):
                marcadores = []

        created_at_raw = self.created_at  # type: ignore[assignment]

        return {
            "id": self.id,
            "analysis_result_id": self.analysis_result_id,
            "orden": self.orden,
            "categoria": self.categoria,
            "dimension": self.dimension,
            "severidad": self.severidad,
            "justificacion": self.justificacion or "",
            "evidencia": self.evidencia or "",
            "regla_disparada": self.regla_disparada,
            "marcadores_detectados": marcadores,
            "confianza": self.confianza,
            "score_ajuste": self.score_ajuste,
            "es_falso_positivo_probable": self.es_falso_positivo_probable,
            "created_at": created_at_raw.isoformat() if created_at_raw is not None else None,
        }


__all__ = ["AnalysisLabelModel"]
