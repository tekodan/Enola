"""PostModel - posts extracted from Facebook pages."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.storage.base import Base


class PostModel(Base):
    """SQLAlchemy model for posts table.

    Each post belongs to a PageModel and can have many comments.
    """

    __tablename__ = "posts"

    id = Column(String, primary_key=True)
    text = Column(Text, default="")
    author = Column(String, default="")
    date = Column(DateTime, nullable=True)
    likes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    url = Column(String, nullable=True)
    page_id = Column(String, ForeignKey("pages.id"), nullable=True)
    source = Column(String, default="facebook_page")
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    page = relationship("PageModel", back_populates="posts")
    comments = relationship("CommentModel", back_populates="post", cascade="all, delete-orphan")
    analysis_results = relationship(
        "AnalysisResultModel", back_populates="post", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Convert PostModel to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "likes": self.likes,
            "comments_count": self.comments_count,
            "shares": self.shares,
            "url": self.url,
            "page_id": self.page_id,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
