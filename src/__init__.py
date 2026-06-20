# src/__init__.py
"""TFM - Detección de Violencia de Género en Facebook."""

__version__ = "1.0.0"
__author__ = "Investigador"

from src.analyzer import ClassificationResult, RAGClassifier, Severity
from src.config import Settings, get_settings
from src.pipeline import PipelineOrchestrator, PipelineResult, run_full_pipeline
from src.scraper import Comment, FacebookScraper, Post
from src.storage import Database, ExportManager, get_database

__all__ = [
    "__version__",
    "Settings",
    "get_settings",
    "FacebookScraper",
    "Post",
    "Comment",
    "Database",
    "get_database",
    "ExportManager",
    "RAGClassifier",
    "ClassificationResult",
    "Severity",
    "PipelineOrchestrator",
    "PipelineResult",
    "run_full_pipeline",
]
