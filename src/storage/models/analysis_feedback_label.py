"""AnalysisFeedbackLabelModel - one row per human-corrected label.

Mirrors :class:`AnalysisLabelModel` but linked to a feedback row instead
of an analysis row. Carries the reviewer's overrides for category,
dimension, justification, evidence, severity and the false-positive
flag.

Cascade-delete on ``analysis_feedback_id`` keeps the table clean when a
feedback entry is removed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.storage.base import Base


class AnalysisFeedbackLabelModel(Base):
    """SQLAlchemy model for the ``analysis_feedback_labels`` table.

    Each row is one corrected label for a feedback entry. ``orden``
    preserves the order the reviewer arranged the rows in the UI.
    """

    __tablename__ = "analysis_feedback_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_feedback_id = Column(
        Integer,
        ForeignKey("analysis_feedback.id", ondelete="CASCADE"),
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
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    feedback = relationship("AnalysisFeedbackModel")

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
        updated_at_raw = self.updated_at  # type: ignore[assignment]

        return {
            "id": self.id,
            "analysis_feedback_id": self.analysis_feedback_id,
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
            "updated_at": updated_at_raw.isoformat() if updated_at_raw is not None else None,
        }


__all__ = ["AnalysisFeedbackLabelModel"]
