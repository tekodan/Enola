"""PageModel - scraped Facebook pages with preprocessed data."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from src.storage.base import Base


class PageModel(Base):
    """SQLAlchemy model for scraped Facebook pages.

    Stores page-level metadata and the full preprocessed hierarchical
    structure (page -> posts -> comments) as JSON.
    """

    __tablename__ = "pages"

    id = Column(String, primary_key=True)
    url = Column(String, nullable=False, index=True)
    title = Column(String, default="")
    source = Column(String, default="facebook")
    html_size = Column(Integer, default=0)
    posts_extracted = Column(Integer, default=0)
    comments_extracted = Column(Integer, default=0)
    preprocessed_data = Column(Text, default="")  # JSON serializado
    raw_metadata = Column(Text, default="")  # JSON con metadata
    scrape_status = Column(String, default="success")  # success, error, partial
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    posts = relationship("PostModel", back_populates="page", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Convert PageModel to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "html_size": self.html_size,
            "posts_extracted": self.posts_extracted,
            "comments_extracted": self.comments_extracted,
            "scrape_status": self.scrape_status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
