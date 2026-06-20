# src/analyzer/__init__.py
"""Analyzer module for violence classification.

The taxonomy of digital gender violence is recovered from ChromaDB
(collection ``violencia_genero``) at classification time. The only
hardcoded enum is :class:`Severity`.
"""

from src.analyzer.embeddings import PostEmbeddings
from src.analyzer.llm_client import OllamaClient
from src.analyzer.rag_classifier import ClassificationResult, RAGClassifier
from src.analyzer.violence_types import Severity

__all__ = [
    "Severity",
    "RAGClassifier",
    "ClassificationResult",
    "OllamaClient",
    "PostEmbeddings",
]
