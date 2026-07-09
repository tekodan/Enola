"""AnalysisResultModel - RAG analysis results for posts and comments."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.storage.base import Base


class AnalysisResultModel(Base):
    """SQLAlchemy model for analysis results table.

    Stores the output of the RAG classifier (violence detection)
    for each post or comment analyzed.
    """

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(String, nullable=False)  # 'post' or 'comment'
    content_id = Column(String, nullable=False)
    post_id = Column(String, ForeignKey("posts.id"), nullable=True)
    comment_id = Column(String, ForeignKey("comments.id"), nullable=True)
    tiene_violencia = Column(String, default="unknown")
    categoria = Column(String, default="ninguna")
    dimension = Column(String, nullable=True)
    codigo = Column(String, nullable=True)
    severidad = Column(String, default="ninguna")
    confianza = Column(String, nullable=True)
    justificacion = Column(Text, default="")
    evidencia = Column(Text, default="")
    regla_disparada = Column(String, nullable=True)
    marcadores_detectados = Column(Text, nullable=True)
    es_falso_positivo_probable = Column(String, default="false")
    score_ajuste = Column(String, nullable=True)
    exclusion_label = Column(String, nullable=True)
    exclusion_codigo = Column(String, nullable=True)
    exclusion_justificacion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    post = relationship("PostModel", back_populates="analysis_results")
    comment = relationship("CommentModel", back_populates="analysis_results")

    def to_dict(self) -> dict:
        """Convert AnalysisResultModel to dictionary."""
        return {
            "id": self.id,
            "content_type": self.content_type,
            "content_id": self.content_id,
            "post_id": self.post_id,
            "comment_id": self.comment_id,
            "tiene_violencia": self.tiene_violencia,
            "categoria": self.categoria,
            "dimension": self.dimension,
            "codigo": self.codigo,
            "severidad": self.severidad,
            "confianza": self.confianza,
            "justificacion": self.justificacion,
            "evidencia": self.evidencia,
            "regla_disparada": self.regla_disparada,
            "marcadores_detectados": self.marcadores_detectados,
            "es_falso_positivo_probable": self.es_falso_positivo_probable,
            "score_ajuste": self.score_ajuste,
            "exclusion_label": self.exclusion_label,
            "exclusion_codigo": self.exclusion_codigo,
            "exclusion_justificacion": self.exclusion_justificacion,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
