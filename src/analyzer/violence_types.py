"""Severity levels for violence classification.

The taxonomy of digital gender violence categories and sub-dimensions
is **not** defined here. It lives in the ChromaDB vector store
(collection ``violencia_genero``, source ``CATEGORIAS TFM CONSOLIDADO.md``)
and is retrieved at classification time via the RAG context.

This module only owns the fixed severity scale used by the classifier.
"""

from enum import StrEnum


class Severity(StrEnum):
    """Severity levels for violence classification.

    This is the **only** categorical field with a hardcoded taxonomy
    in the codebase. All violence categories/sub-dimensions are
    supplied by ChromaDB.
    """

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    NINGUNA = "ninguna"
