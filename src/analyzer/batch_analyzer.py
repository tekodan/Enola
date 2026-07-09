"""Batch analyzer — classifies all unanalyzed posts and comments from SQLite.

Reads posts/comments from the database, sends each to the RAG classifier
(which uses ChromaDB for context), and writes the result back to the
``analysis_results`` table.

By default, a :class:`~src.knowledge_base.feedback_store.FeedbackStore`
is wired up so the classifier injects human-validated corrections as
dynamic few-shot examples.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime

from src.analyzer.llm_client import OllamaClient
from src.analyzer.rag_classifier import RAGClassifier
from src.config.settings import get_settings
from src.knowledge_base.feedback_store import get_feedback_store
from src.knowledge_base.vector_store import get_vector_store
from src.storage.database import Database

logger = logging.getLogger(__name__)


@dataclass
class BatchAnalysisStats:
    """Statistics for a batch analysis run."""

    posts_analyzed: int = 0
    comments_analyzed: int = 0
    violence_detected_posts: int = 0
    violence_detected_comments: int = 0
    errors: int = 0
    execution_time_seconds: float = 0.0


class BatchAnalyzer:
    """Analyze posts/comments from DB using RAG classifier.

    Usage::

        analyzer = BatchAnalyzer(database, classifier)
        stats = analyzer.analyze_all()
        print(stats)
    """

    def __init__(
        self,
        database: Database,
        classifier: RAGClassifier | None = None,
        llm_client: OllamaClient | None = None,
        vector_store=None,
        feedback_store=None,
        analyze_posts: bool = True,
        analyze_comments: bool = True,
        reanalyze_existing: bool = False,
    ):
        self.database = database
        self.analyze_posts = analyze_posts
        self.analyze_comments = analyze_comments
        self.reanalyze_existing = reanalyze_existing

        if classifier is not None:
            self.classifier = classifier
        else:
            settings = get_settings()
            vs = vector_store or get_vector_store(
                persist_directory=settings.knowledge_base.persist_directory,
                collection_name=settings.knowledge_base.collection_name,
            )
            fb_store = feedback_store or get_feedback_store(
                persist_directory=settings.knowledge_base.persist_directory,
                collection_name=settings.knowledge_base.feedback_collection_name,
            )
            llm = llm_client or OllamaClient(
                base_url=settings.ollama.base_url,
                model=settings.ollama.llm_model,
                temperature=settings.analyzer.temperature,
            )
            self.classifier = RAGClassifier(
                llm_client=llm,
                vector_store=vs,
                feedback_store=fb_store,
                context_chunks=settings.analyzer.context_chunks,
            )
            logger.info(
                "RAGClassifier initialized: vector_store=%s, feedback_store=%s, llm=%s",
                type(vs).__name__,
                type(fb_store).__name__,
                type(llm).__name__,
            )

    def analyze_all(self) -> BatchAnalysisStats:
        """Analyze all unanalyzed content in the database.

        Returns:
            BatchAnalysisStats with counts
        """
        start = datetime.now()
        stats = BatchAnalysisStats()

        if self.analyze_posts:
            self._analyze_posts(stats)

        if self.analyze_comments:
            self._analyze_comments(stats)

        stats.execution_time_seconds = (datetime.now() - start).total_seconds()
        logger.info(
            "Batch analysis complete: %d posts, %d comments, "
            "%d violence posts, %d violence comments, %d errors (%.1fs)",
            stats.posts_analyzed,
            stats.comments_analyzed,
            stats.violence_detected_posts,
            stats.violence_detected_comments,
            stats.errors,
            stats.execution_time_seconds,
        )
        return stats

    def _get_items(self) -> tuple[list[dict], list[dict]]:
        """Get posts and comments to analyze."""
        posts = []
        comments = []

        if self.reanalyze_existing:
            if self.analyze_posts:
                posts = self.database.get_posts(limit=10_000)
            if self.analyze_comments:
                comments = []
                for p in posts:
                    comments.extend(self.database.get_comments(p["id"], limit=100))
        else:
            if self.analyze_posts:
                posts = self.database.get_unanalyzed_posts()
            if self.analyze_comments:
                comments = self.database.get_unanalyzed_comments()

        return posts, comments

    def _analyze_posts(self, stats: BatchAnalysisStats) -> None:
        """Classify all (unanalyzed) posts."""
        posts, _ = self._get_items()
        # Actually get posts properly - the above also gets comments
        if self.reanalyze_existing:
            items = self.database.get_posts(limit=10_000)
        else:
            items = self.database.get_unanalyzed_posts()

        for item in items:
            try:
                text = item.get("text", "")

                result = self.classifier.classify_sync(text)

                self.database.save_or_update_analysis_result(
                    {
                        "content_type": "post",
                        "content_id": item["id"],
                        "post_id": item.get("id", ""),
                        "tiene_violencia": "true" if result.tiene_violencia else "false",
                        "categoria": result.categoria,
                        "dimension": result.dimension,
                        "codigo": None,
                        "severidad": result.severidad.value,
                        "confianza": str(result.confianza)
                        if result.confianza is not None
                        else None,
                        "justificacion": result.justificacion,
                        "evidencia": result.evidencia,
                        "regla_disparada": result.regla_disparada,
                        "marcadores_detectados": json.dumps(result.marcadores_detectados)
                        if result.marcadores_detectados
                        else None,
                        "es_falso_positivo_probable": "true"
                        if result.es_falso_positivo_probable
                        else "false",
                        "score_ajuste": str(result.score_ajuste)
                        if result.score_ajuste is not None
                        else None,
                        "clasificaciones": [c.to_dict() for c in result.clasificaciones],
                        "exclusion_label": result.exclusion_label,
                        "exclusion_codigo": result.exclusion_codigo,
                        "exclusion_justificacion": result.exclusion_justificacion,
                    }
                )

                stats.posts_analyzed += 1
                if result.tiene_violencia:
                    stats.violence_detected_posts += 1

            except Exception as e:
                logger.warning("Error analyzing post %s: %s", item.get("id", ""), e)
                stats.errors += 1

    def _analyze_comments(self, stats: BatchAnalysisStats) -> None:
        """Classify all (unanalyzed) comments."""
        if self.reanalyze_existing:
            items = []
            posts = self.database.get_posts(limit=10_000)
            for p in posts:
                items.extend(self.database.get_comments(p["id"], limit=100))
        else:
            items = self.database.get_unanalyzed_comments()

        for item in items:
            try:
                text = item.get("text", "")

                result = self.classifier.classify_sync(text)

                self.database.save_or_update_analysis_result(
                    {
                        "content_type": "comment",
                        "content_id": item["id"],
                        "post_id": item.get("post_id", ""),
                        "comment_id": item.get("id", ""),
                        "tiene_violencia": "true" if result.tiene_violencia else "false",
                        "categoria": result.categoria,
                        "dimension": result.dimension,
                        "codigo": None,
                        "severidad": result.severidad.value,
                        "confianza": str(result.confianza)
                        if result.confianza is not None
                        else None,
                        "justificacion": result.justificacion,
                        "evidencia": result.evidencia,
                        "regla_disparada": result.regla_disparada,
                        "marcadores_detectados": json.dumps(result.marcadores_detectados)
                        if result.marcadores_detectados
                        else None,
                        "es_falso_positivo_probable": "true"
                        if result.es_falso_positivo_probable
                        else "false",
                        "score_ajuste": str(result.score_ajuste)
                        if result.score_ajuste is not None
                        else None,
                        "clasificaciones": [c.to_dict() for c in result.clasificaciones],
                        "exclusion_label": result.exclusion_label,
                        "exclusion_codigo": result.exclusion_codigo,
                        "exclusion_justificacion": result.exclusion_justificacion,
                    }
                )

                stats.comments_analyzed += 1
                if result.tiene_violencia:
                    stats.violence_detected_comments += 1

            except Exception as e:
                logger.warning("Error analyzing comment %s: %s", item.get("id", ""), e)
                stats.errors += 1


def run_batch_analysis(
    database: Database | None = None,
    classifier: RAGClassifier | None = None,
    reanalyze: bool = False,
    posts_only: bool = False,
) -> BatchAnalysisStats:
    """Convenience function to run batch analysis.

    Args:
        database: Database instance (created from default URL if None)
        classifier: RAGClassifier instance (created with defaults if None)
        reanalyze: If True, re-analyze already analyzed content
        posts_only: If True, skip comment analysis

    Returns:
        BatchAnalysisStats
    """
    if database is None:
        from src.storage import get_database

        database = get_database()

    analyzer = BatchAnalyzer(
        database=database,
        classifier=classifier,
        analyze_comments=not posts_only,
        reanalyze_existing=reanalyze,
    )
    return analyzer.analyze_all()
