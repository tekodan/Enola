# src/discovery/__init__.py
"""Discovery module for automatic page discovery."""

from src.discovery.page_discovery import ControversialGroup, PageDiscovery, RelatedPage
from src.discovery.similarity import SimilarityEngine, compute_similarity

__all__ = [
    "PageDiscovery",
    "RelatedPage",
    "ControversialGroup",
    "SimilarityEngine",
    "compute_similarity",
]
