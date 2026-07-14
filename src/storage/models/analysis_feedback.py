"""AnalysisFeedbackModel - human validation feedback for RAG analysis results.

Stores the reviewer's verdict (agree / disagree) for a single
``AnalysisResultModel`` row. When ``agrees='false'``, the override fields
(``corrected_categoria`` / ``corrected_dimension`` / ``corrected_justificacion``)
hold the human ground truth, which is also pushed (separately) to the
``feedback_corrections`` ChromaDB collection so the RAG classifier can
retrieve them as few-shot examples.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.storage.base import Base


class AnalysisFeedbackModel(Base):
    """SQLAlchemy model for the ``analysis_feedback`` table.

    One row per human review of an analysis result. If the reviewer
    revises the same row multiple times, the row is upserted (the
    primary key is auto-increment but the logical key is
    ``analysis_result_id`` — at most one feedback per analysis).
    """

    __tablename__ = "analysis_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_result_id = Column(
        Integer,
        ForeignKey("analysis_results.id"),
        nullable=False,
        index=True,
    )

    # Denormalized for simpler queries (avoids an extra JOIN when listing)
    content_type = Column(String, nullable=False, index=True)
    content_id = Column(String, nullable=False, index=True)
    text_snapshot = Column(Text, nullable=False)

    agrees = Column(String, nullable=False)  # "true" / "false"

    # Override fields — populated only when agrees="false"
    reason = Column(Text, nullable=True)
    corrected_categoria = Column(String, nullable=True)
    corrected_dimension = Column(String, nullable=True)
    corrected_justificacion = Column(Text, nullable=True)

    # ChromaDB sync tracking
    indexed_in_chromadb = Column(String, default="false")
    chromadb_id = Column(String, nullable=True)
    chromadb_indexed_at = Column(DateTime, nullable=True)

    reviewer = Column(String, nullable=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reviewer_username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    analysis_result = relationship("AnalysisResultModel")

    def to_dict(self) -> dict:
        """Convert ``AnalysisFeedbackModel`` to a JSON-friendly dict."""
        return {
            "id": self.id,
            "analysis_result_id": self.analysis_result_id,
            "content_type": self.content_type,
            "content_id": self.content_id,
            "text_snapshot": self.text_snapshot,
            "agrees": self.agrees,
            "reason": self.reason,
            "corrected_categoria": self.corrected_categoria,
            "corrected_dimension": self.corrected_dimension,
            "corrected_justificacion": self.corrected_justificacion,
            "indexed_in_chromadb": self.indexed_in_chromadb,
            "chromadb_id": self.chromadb_id,
            "chromadb_indexed_at": self.chromadb_indexed_at.isoformat()
            if self.chromadb_indexed_at
            else None,
            "reviewer": self.reviewer,
            "reviewer_user_id": self.reviewer_user_id,
            "reviewer_username": self.reviewer_username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
