"""SeedPageModel - original seed pages for the pipeline."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from src.storage.base import Base


class SeedPageModel(Base):
    """SQLAlchemy model for seed pages table.

    Stores the initial seed URLs that the pipeline starts from,
    plus any auto-discovered pages.
    """

    __tablename__ = "seed_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    name = Column(String, default="")
    page_id = Column(String, nullable=True)
    source = Column(String, default="facebook_page")  # page/post/group/unknown
    is_seed = Column(String, default="true")  # 'true' or 'false'
    discovered_from = Column(String, nullable=True)
    violence_score = Column(String, nullable=True)
    posts_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        """Convert SeedPageModel to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "name": self.name,
            "page_id": self.page_id,
            "source": self.source,
            "is_seed": self.is_seed,
            "discovered_from": self.discovered_from,
            "violence_score": self.violence_score,
            "posts_count": self.posts_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
