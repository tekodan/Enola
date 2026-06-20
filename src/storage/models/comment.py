"""CommentModel - comments extracted from Facebook posts."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.storage.base import Base


class CommentModel(Base):
    """SQLAlchemy model for comments table.

    Each comment belongs to a PostModel and can have analysis results.
    Supports threaded comments via parent_id.
    """

    __tablename__ = "comments"

    id = Column(String, primary_key=True)
    text = Column(Text, default="")
    author = Column(String, default="")
    date = Column(DateTime, nullable=True)
    likes = Column(Integer, default=0)
    post_id = Column(String, ForeignKey("posts.id"), nullable=True)
    parent_id = Column(String, nullable=True)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    post = relationship("PostModel", back_populates="comments")
    analysis_results = relationship(
        "AnalysisResultModel", back_populates="comment", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Convert CommentModel to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "likes": self.likes,
            "post_id": self.post_id,
            "parent_id": self.parent_id,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
