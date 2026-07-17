"""Category display CRUD — seed, list, edit overrides in SQLite.

Called from the CLI and from the storage layer.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from src.storage.models.category_display import CategoryDisplayModel, SubdimensionDisplayModel

if TYPE_CHECKING:
    from src.storage.database import Database

logger = logging.getLogger(__name__)


def seed_category_display(db: Database) -> None:
    """Seed ``category_display`` and ``subdimension_display`` from taxonomy defaults.

    Only inserts rows when the tables are empty (first run).
    """
    from src.analyzer.taxonomy_loader import get_taxonomy

    tx = get_taxonomy()

    with db.get_session() as session:
        existing = session.query(CategoryDisplayModel).count()
        if existing == 0:
            logger.info("Seeding category_display table from taxonomy...")
            for cat in tx.categorias:
                session.add(
                    CategoryDisplayModel(
                        code=cat.code,
                        title=cat.label or cat.code,
                        source="taxonomy",
                        updated_at=datetime.now(),
                    )
                )
        existing_sub = session.query(SubdimensionDisplayModel).count()
        if existing_sub == 0:
            logger.info("Seeding subdimension_display table from taxonomy...")
            for cat in tx.categorias:
                for dim in cat.subdimensiones:
                    session.add(
                        SubdimensionDisplayModel(
                            code=dim.code,
                            category_code=cat.code,
                            description=dim.descripcion,
                            source="taxonomy",
                            updated_at=datetime.now(),
                        )
                    )


def get_category_display_overrides(db: Database) -> dict[str, str]:
    """Return ``{code: title}`` for rows whose ``source != 'taxonomy'``."""
    with db.get_session() as session:
        rows = (
            session.query(CategoryDisplayModel)
            .filter(CategoryDisplayModel.source != "taxonomy")
            .all()
        )
        return {r.code: r.title for r in rows}


def get_subdimension_display_overrides(db: Database) -> dict[str, str]:
    """Return ``{code: description}`` for rows whose ``source != 'taxonomy'``."""
    with db.get_session() as session:
        rows = (
            session.query(SubdimensionDisplayModel)
            .filter(SubdimensionDisplayModel.source != "taxonomy")
            .all()
        )
        return {r.code: r.description for r in rows}


def set_category_title(db: Database, code: str, title: str) -> bool:
    """Upsert a category display override."""
    now = datetime.now()
    with db.get_session() as session:
        existing = session.query(CategoryDisplayModel).filter_by(code=code).first()
        if existing:
            existing.title = title
            existing.source = "override"
            existing.updated_at = now
        else:
            session.add(
                CategoryDisplayModel(
                    code=code,
                    title=title,
                    source="override",
                    updated_at=now,
                )
            )
    return True


def set_subdimension_description(db: Database, code: str, description: str) -> bool:
    """Upsert a sub-dimension display override."""
    from src.analyzer.taxonomy_loader import get_taxonomy

    tx = get_taxonomy()
    parent = tx.categoria_por_subdimension().get(code)
    if not parent:
        return False
    now = datetime.now()
    with db.get_session() as session:
        existing = session.query(SubdimensionDisplayModel).filter_by(code=code).first()
        if existing:
            existing.description = description
            existing.source = "override"
            existing.updated_at = now
        else:
            session.add(
                SubdimensionDisplayModel(
                    code=code,
                    category_code=parent,
                    description=description,
                    source="override",
                    updated_at=now,
                )
            )
    return True


def list_category_display(db: Database) -> list[dict]:
    """Return all category display rows (defaults + overrides)."""
    with db.get_session() as session:
        rows = session.query(CategoryDisplayModel).order_by(CategoryDisplayModel.code).all()
        return [r.to_dict() for r in rows]


def list_subdimension_display(db: Database) -> list[dict]:
    """Return all sub-dimension display rows (defaults + overrides)."""
    with db.get_session() as session:
        rows = session.query(SubdimensionDisplayModel).order_by(SubdimensionDisplayModel.code).all()
        return [r.to_dict() for r in rows]
