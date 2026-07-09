# src/analyzer/__init__.py
"""Analyzer module for violence classification.

The taxonomy of digital gender violence is recovered from ChromaDB
(collection ``violencia_genero``) at classification time. The only
hardcoded enum is :class:`Severity`.

Multi-label: a single classification can carry up to ``MAX_LABELS`` (5)
:class:`LabelAssignment` entries, each with its own categoria,
sub-dimension, justification, evidence and severity.

The pre-classification filter (:mod:`src.analyzer.exclusion_filter`)
excludes "basura digital" (CÓDIGO 99) and "violencia común sin sesgo
de género" before any LLM call.
"""

from src.analyzer.category_mapping import MAX_LABELS
from src.analyzer.embeddings import PostEmbeddings
from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_LABELS,
    EXCLUSION_VIOLENCIA_COMUN,
    ExclusionResult,
    detectar_basura_digital,
    detectar_violencia_comun_heuristica,
    evaluar_exclusiones,
)
from src.analyzer.llm_client import OllamaClient
from src.analyzer.rag_classifier import ClassificationResult, LabelAssignment, RAGClassifier
from src.analyzer.violence_types import Severity

__all__ = [
    "MAX_LABELS",
    "Severity",
    "RAGClassifier",
    "ClassificationResult",
    "LabelAssignment",
    "OllamaClient",
    "PostEmbeddings",
    "ExclusionResult",
    "EXCLUSION_BASURA_DIGITAL",
    "EXCLUSION_VIOLENCIA_COMUN",
    "EXCLUSION_LABELS",
    "detectar_basura_digital",
    "detectar_violencia_comun_heuristica",
    "evaluar_exclusiones",
]
