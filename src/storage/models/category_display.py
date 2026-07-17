"""CategoryDisplay model — display overrides for category titles and sub-dimension descriptions.

This model reads from ``category_display`` and ``subdimension_display`` tables
in SQLite. If no overrides exist, defaults are resolved from the taxonomy YAML.
"""


from sqlalchemy import Column, DateTime, Integer, String

from src.storage.base import Base


class CategoryDisplayModel(Base):
    """Display override for a single VDG_* category (title)."""

    __tablename__ = "category_display"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False, default="taxonomy")
    updated_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "source": self.source,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SubdimensionDisplayModel(Base):
    """Display override for a single sub-dimension (description)."""

    __tablename__ = "subdimension_display"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False, index=True)
    category_code = Column(String, nullable=False)
    description = Column(String, nullable=False)
    source = Column(String, nullable=False, default="taxonomy")
    updated_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "category_code": self.category_code,
            "description": self.description,
            "source": self.source,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
