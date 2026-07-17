"""Centralised category / sub-dimension display resolution.

Reads display data from these sources (in priority order):

1. Override in SQLite (``category_display`` / ``subdimension_display`` tables).
2. Taxonomy YAML frontmatter (``label`` field on each category, ``descripcion``
   on each sub-dimension).
3. Fallback: formatted code (``VDG_FOO_BAR`` → ``"Vdg Foo Bar"``).

An in-memory cache speeds up repeated lookups. Call ``refresh_cache()`` after
editing the SQLite overrides (on the same process) to pick up changes without
restarting the server.
"""

from __future__ import annotations

import logging
from threading import Lock

from src.analyzer.category_mapping import (
    CATEGORIAS_ORDENADAS,
    DESCRIPCION_SUBDIMENSION,
)
from src.analyzer.taxonomy_loader import get_taxonomy

logger = logging.getLogger(__name__)

_lock = Lock()
_CATEGORY_TITLE_CACHE: dict[str, str] | None = None
_SUBDIM_DESCRIPTION_CACHE: dict[str, str] | None = None


def _load_overrides() -> tuple[dict[str, str], dict[str, str]]:
    try:
        from src.storage import get_database
        from src.storage.category_display import (
            get_category_display_overrides,
            get_subdimension_display_overrides,
        )

        db = get_database()
        cat_overrides = get_category_display_overrides(db)
        sub_overrides = get_subdimension_display_overrides(db)
        return cat_overrides, sub_overrides
    except Exception:
        return {}, {}


def _build_category_title_cache() -> dict[str, str]:
    cat_overrides, _ = _load_overrides()
    tx = get_taxonomy()
    default_labels = tx.category_labels()
    cache: dict[str, str] = {}
    for code in CATEGORIAS_ORDENADAS:
        cache[code] = (
            cat_overrides.get(code) or default_labels.get(code) or code.replace("_", " ").title()
        )
    return cache


def _build_subdim_description_cache() -> dict[str, str]:
    _, sub_overrides = _load_overrides()
    cache: dict[str, str] = {}
    for code, desc in DESCRIPCION_SUBDIMENSION.items():
        cache[code] = sub_overrides.get(code) or desc
    return cache


def get_category_label(code: str) -> str:
    """Return the display label for a VDG_* category code."""
    global _CATEGORY_TITLE_CACHE
    if _CATEGORY_TITLE_CACHE is None:
        with _lock:
            if _CATEGORY_TITLE_CACHE is None:
                _CATEGORY_TITLE_CACHE = _build_category_title_cache()
    return _CATEGORY_TITLE_CACHE.get(code, code.replace("_", " ").title())


def get_category_choices() -> dict[str, str]:
    """Return ``{VDG_*: title}`` dict for all canonical categories."""
    return {code: get_category_label(code) for code in CATEGORIAS_ORDENADAS}


def get_subdimension_description(code: str) -> str:
    """Return the display description for a sub-dimension code (e.g. ``1.1``)."""
    global _SUBDIM_DESCRIPTION_CACHE
    if _SUBDIM_DESCRIPTION_CACHE is None:
        with _lock:
            if _SUBDIM_DESCRIPTION_CACHE is None:
                _SUBDIM_DESCRIPTION_CACHE = _build_subdim_description_cache()
    return _SUBDIM_DESCRIPTION_CACHE.get(code, code)


def refresh_cache() -> None:
    """Invalidate the in-memory caches so next calls reload from SQLite + taxonomy."""
    global _CATEGORY_TITLE_CACHE, _SUBDIM_DESCRIPTION_CACHE
    with _lock:
        _CATEGORY_TITLE_CACHE = None
        _SUBDIM_DESCRIPTION_CACHE = None
    logger.info("Category display cache refreshed")


CATEGORIA_LABELS: dict[str, str] = get_category_choices()
"""Module-level dict for backwards compatibility with existing imports.

This is populated once at import time. If you edit overrides at runtime
and need the latest values, call :func:`get_category_label` directly or
run :func:`refresh_cache` + re-import.
"""
