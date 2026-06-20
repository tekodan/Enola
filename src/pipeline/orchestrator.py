"""Pipeline orchestrator module."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from src.analyzer.embeddings import PostEmbeddings
from src.analyzer.rag_classifier import RAGClassifier
from src.discovery.page_discovery import PageDiscovery
from src.storage.database import Database

SEED_PAGES_PATH = Path(__file__).parent.parent.parent / "data" / "seed_pages.txt"


def load_seed_pages(path: str | Path | None = None) -> list[str]:
    """Load seed page URLs from a file (one per line, # comments ignored).

    Defaults to ``data/seed_pages.txt`` if no path given.
    """
    p = Path(path) if path else SEED_PAGES_PATH
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


@dataclass
class PipelineStats:
    """Statistics for pipeline execution."""

    pages_scraped: int = 0
    posts_found: int = 0
    comments_found: int = 0
    posts_classified: int = 0
    comments_classified: int = 0
    violence_detected_posts: int = 0
    violence_detected_comments: int = 0
    new_pages_discovered: int = 0
    new_seed_pages_added: int = 0
    execution_time_seconds: float = 0.0


class PipelineResult(BaseModel):
    """Result of pipeline execution."""

    success: bool
    stats: PipelineStats
    errors: list[str] = field(default_factory=list)
    new_seeds: list[str] = field(default_factory=list)
    classified_posts: list[dict] = field(default_factory=list)
    classified_comments: list[dict] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class PipelineOrchestrator:
    """Orchestrator for the complete pipeline."""

    def __init__(
        self,
        database: Database | None = None,
        scraper=None,
        classifier: RAGClassifier | None = None,
        embeddings: PostEmbeddings | None = None,
        discovery: PageDiscovery | None = None,
        max_iterations: int = 3,
        min_violence_score: float = 0.7,
    ):
        """Initialize pipeline orchestrator.

        Args:
            database: Database instance
            scraper: Scraper instance
            classifier: RAG classifier
            embeddings: Post embeddings manager
            discovery: Page discovery engine
            max_iterations: Maximum pipeline iterations
            min_violence_score: Minimum score to add as seed
        """
        self.database = database
        self.scraper = scraper
        self.classifier = classifier or RAGClassifier()
        self.embeddings = embeddings
        self.discovery = discovery or PageDiscovery(
            similarity_engine=None,
            min_similarity=min_violence_score,
        )
        self.max_iterations = max_iterations
        self.min_violence_score = min_violence_score

    def run_seed_pipeline(self, seed_pages: list[str]) -> PipelineResult:
        """Run pipeline on seed pages.

        Args:
            seed_pages: List of seed page URLs

        Returns:
            PipelineResult with execution stats
        """
        start_time = datetime.now()
        stats = PipelineStats()
        errors = []

        try:
            for page_url in seed_pages:
                posts = []
                if self.scraper:
                    # Check if scraper has sync or async interface
                    if hasattr(self.scraper, "scrape_page_sync"):
                        posts = self.scraper.scrape_page_sync(page_url)
                    elif hasattr(self.scraper, "scrape_page"):
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        posts = loop.run_until_complete(self.scraper.scrape_page(page_url))

                # Save posts
                if self.database and posts:
                    self.database.save_posts_batch([p.to_dict() for p in posts])

                stats.pages_scraped += 1
                stats.posts_found += len(posts)

                # Classify posts
                for post in posts:
                    if self.classifier:
                        result = self.classifier.classify_sync(post.text)
                        stats.posts_classified += 1

                        if result.tiene_violencia:
                            stats.violence_detected_posts += 1

                            # Save analysis result
                            if self.database:
                                self.database.save_analysis_result(
                                    {
                                        "content_type": "post",
                                        "content_id": post.id,
                                        "post_id": post.id,
                                        "tiene_violencia": "true"
                                        if result.tiene_violencia
                                        else "false",
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
                                        "marcadores_detectados": (
                                            json.dumps(result.marcadores_detectados)
                                            if result.marcadores_detectados
                                            else None
                                        ),
                                        "es_falso_positivo_probable": "true"
                                        if result.es_falso_positivo_probable
                                        else "false",
                                        "score_ajuste": str(result.score_ajuste)
                                        if result.score_ajuste is not None
                                        else None,
                                    }
                                )

            execution_time = (datetime.now() - start_time).total_seconds()
            stats.execution_time_seconds = execution_time

            return PipelineResult(
                success=True,
                stats=stats,
                execution_time=execution_time,
            )

        except Exception as e:
            errors.append(str(e))
            return PipelineResult(
                success=False,
                stats=stats,
                errors=errors,
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

    def run_discovery_pipeline(self) -> PipelineResult:
        """Run discovery pipeline.

        Returns:
            PipelineResult with discovered pages
        """
        start_time = datetime.now()
        stats = PipelineStats()
        errors = []
        new_seeds = []

        try:
            # Get seed pages from database
            if self.database:
                seed_pages = self.database.get_seed_pages(is_seed=True)
            else:
                return PipelineResult(
                    success=False,
                    stats=stats,
                    errors=["No database configured"],
                )

            # Discover related pages
            all_related = []
            for page in seed_pages:
                related = self.discovery.discover_related_pages(page["url"])
                all_related.extend(related)

            # Filter by similarity
            high_similarity = self.discovery.get_pages_above_threshold(all_related)
            ranked = self.discovery.rank_pages_by_similarity(high_similarity)

            # Add as new seeds
            for page in ranked:
                if self.discovery.should_add_as_seed(page):
                    new_seeds.append(page.url)
                    stats.new_pages_discovered += 1

                    # Save to database
                    self.database.save_seed_page(
                        {
                            "url": page.url,
                            "name": page.name,
                            "is_seed": "true",
                            "discovered_from": page.discovered_from,
                            "violence_score": str(page.similarity_score),
                        }
                    )

            execution_time = (datetime.now() - start_time).total_seconds()
            stats.execution_time_seconds = execution_time

            return PipelineResult(
                success=True,
                stats=stats,
                new_seeds=new_seeds,
                execution_time=execution_time,
            )

        except Exception as e:
            errors.append(str(e))
            return PipelineResult(
                success=False,
                stats=stats,
                errors=errors,
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

    def run_full_pipeline(
        self, seed_pages: list[str], iterations: int | None = None
    ) -> PipelineResult:
        """Run full pipeline with iterations.

        Args:
            seed_pages: Initial seed page URLs
            iterations: Number of iterations (uses default if None)

        Returns:
            PipelineResult with combined stats
        """
        if iterations is None:
            iterations = self.max_iterations

        start_time = datetime.now()
        combined_stats = PipelineStats()
        all_errors = []
        all_new_seeds = []

        current_seeds = seed_pages.copy()

        for iteration in range(iterations):
            # Run seed pipeline
            result = self.run_seed_pipeline(current_seeds)
            combined_stats.pages_scraped += result.stats.pages_scraped
            combined_stats.posts_found += result.stats.posts_found
            combined_stats.posts_classified += result.stats.posts_classified
            combined_stats.violence_detected_posts += result.stats.violence_detected_posts
            all_errors.extend(result.errors)

            # Run discovery
            discovery_result = self.run_discovery_pipeline()
            combined_stats.new_pages_discovered += discovery_result.stats.new_pages_discovered
            combined_stats.new_seed_pages_added += len(discovery_result.new_seeds)
            all_new_seeds.extend(discovery_result.new_seeds)
            all_errors.extend(discovery_result.errors)

            # Add new seeds for next iteration
            if discovery_result.new_seeds:
                current_seeds.extend(discovery_result.new_seeds)

        execution_time = (datetime.now() - start_time).total_seconds()
        combined_stats.execution_time_seconds = execution_time

        return PipelineResult(
            success=len(all_errors) == 0,
            stats=combined_stats,
            errors=all_errors,
            new_seeds=all_new_seeds,
            execution_time=execution_time,
        )


def run_full_pipeline(
    seed_pages: list[str],
    database: Database | None = None,
    scraper=None,
    classifier: RAGClassifier | None = None,
    embeddings: PostEmbeddings | None = None,
    discovery: PageDiscovery | None = None,
    max_iterations: int = 3,
) -> PipelineResult:
    """Convenience function to run full pipeline.

    Args:
        seed_pages: Initial seed page URLs
        database: Database instance
        scraper: Scraper instance
        classifier: RAG classifier
        embeddings: Post embeddings
        discovery: Page discovery
        max_iterations: Maximum iterations

    Returns:
        PipelineResult
    """
    orchestrator = PipelineOrchestrator(
        database=database,
        scraper=scraper,
        classifier=classifier,
        embeddings=embeddings,
        discovery=discovery,
        max_iterations=max_iterations,
    )

    return orchestrator.run_full_pipeline(seed_pages)
