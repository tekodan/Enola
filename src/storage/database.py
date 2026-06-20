"""Database manager for SQLite operations.

The model definitions live in ``src.storage.models`` (one module per
class). This module only owns the ``Database`` class which encapsulates
sessions, CRUD helpers and the hierarchical ``save_page_with_posts``
write path used by the scraper.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.storage.base import Base
from src.storage.models import (
    AnalysisResultModel,
    CommentModel,
    PageModel,
    PostModel,
    SeedPageModel,
)


class Database:
    """Database manager for SQLite operations."""

    def __init__(self, database_url: str):
        """Initialize database with URL.

        Args:
            database_url: SQLAlchemy database URL (e.g. 'sqlite:///data/tfm.db')
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Ensure all model modules are imported so their tables are
        # registered with Base.metadata before create_all() runs.
        from src.storage import models  # noqa: F401

        # Create tables (no-op for tables that already exist)
        Base.metadata.create_all(self.engine)

        # Apply incremental migrations for any schema drift between
        # the current models and the on-disk database. This is a no-op
        # on a freshly-created database.
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Bring the on-disk schema in line with the current models.

        ``Base.metadata.create_all()`` only creates missing tables, it
        does not add missing columns to existing tables. This method
        inspects the live schema and runs ``ALTER TABLE ADD COLUMN``
        statements to add any columns that the models declare but the
        DB doesn't have. It also migrates legacy columns (``tipo`` →
        ``categoria``, ``confidence`` → ``confianza``) and drops them
        when the SQLite version supports it.

        Safe to run multiple times.
        """
        from sqlalchemy import inspect, text

        inspector = inspect(self.engine)
        if "analysis_results" not in inspector.get_table_names():
            return

        existing_cols = {c["name"] for c in inspector.get_columns("analysis_results")}

        additions: list[tuple[str, str]] = []
        if "categoria" not in existing_cols:
            additions.append(("categoria", "VARCHAR DEFAULT 'ninguna'"))
        if "dimension" not in existing_cols:
            additions.append(("dimension", "VARCHAR"))
        if "codigo" not in existing_cols:
            additions.append(("codigo", "VARCHAR"))
        if "confianza" not in existing_cols:
            additions.append(("confianza", "VARCHAR"))
        if "regla_disparada" not in existing_cols:
            additions.append(("regla_disparada", "VARCHAR"))
        if "marcadores_detectados" not in existing_cols:
            additions.append(("marcadores_detectados", "TEXT"))
        if "es_falso_positivo_probable" not in existing_cols:
            additions.append(("es_falso_positivo_probable", "VARCHAR DEFAULT 'false'"))
        if "score_ajuste" not in existing_cols:
            additions.append(("score_ajuste", "VARCHAR"))

        if not additions and "tipo" not in existing_cols and "confidence" not in existing_cols:
            return

        with self.engine.begin() as conn:
            for col_name, col_type in additions:
                conn.execute(text(f"ALTER TABLE analysis_results ADD COLUMN {col_name} {col_type}"))

            if "tipo" in existing_cols and "categoria" in (
                existing_cols | {a[0] for a in additions}
            ):
                conn.execute(
                    text("UPDATE analysis_results SET categoria = tipo WHERE tipo IS NOT NULL")
                )

            if "confidence" in existing_cols and "confianza" in (
                existing_cols | {a[0] for a in additions}
            ):
                conn.execute(
                    text(
                        "UPDATE analysis_results "
                        "SET confianza = confidence "
                        "WHERE confidence IS NOT NULL"
                    )
                )

            sqlite_version = conn.execute(text("SELECT sqlite_version()")).scalar() or ""
            major, minor, *_ = (int(x) for x in sqlite_version.split("."))
            if (major, minor) >= (3, 35):
                if "tipo" in existing_cols:
                    conn.execute(text("ALTER TABLE analysis_results DROP COLUMN tipo"))
                if "confidence" in existing_cols:
                    conn.execute(text("ALTER TABLE analysis_results DROP COLUMN confidence"))

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ----- Single-record save helpers -----

    def save_post(self, post_data: dict) -> bool:
        """Save a post to the database.

        Args:
            post_data: Dictionary with post data

        Returns:
            True if saved successfully
        """
        with self.get_session() as session:
            existing = session.query(PostModel).filter_by(id=post_data["id"]).first()
            if existing:
                for key, value in post_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                post = PostModel(**post_data)
                session.add(post)
            return True

    def save_comment(self, comment_data: dict) -> bool:
        """Save a comment to the database.

        Args:
            comment_data: Dictionary with comment data

        Returns:
            True if saved successfully
        """
        with self.get_session() as session:
            existing = session.query(CommentModel).filter_by(id=comment_data["id"]).first()
            if existing:
                for key, value in comment_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                comment = CommentModel(**comment_data)
                session.add(comment)
            return True

    def save_analysis_result(self, result_data: dict) -> int:
        """Save an analysis result.

        Args:
            result_data: Dictionary with analysis result data

        Returns:
            ID of the saved result
        """
        with self.get_session() as session:
            result = AnalysisResultModel(**result_data)
            session.add(result)
            session.flush()
            return result.id

    def save_seed_page(self, page_data: dict) -> int:
        """Save a seed page.

        Args:
            page_data: Dictionary with page data

        Returns:
            ID of the saved page
        """
        with self.get_session() as session:
            existing = session.query(SeedPageModel).filter_by(url=page_data["url"]).first()
            if existing:
                for key, value in page_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                return existing.id
            else:
                page = SeedPageModel(**page_data)
                session.add(page)
                session.flush()
                return page.id

    # ----- Batch save helpers -----

    def save_posts_batch(self, posts_data: list[dict]) -> int:
        """Save multiple posts in batch.

        Args:
            posts_data: List of post dictionaries

        Returns:
            Number of posts saved
        """
        saved = 0
        with self.get_session() as session:
            for post_data in posts_data:
                try:
                    existing = session.query(PostModel).filter_by(id=post_data["id"]).first()
                    if existing:
                        for key, value in post_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        post = PostModel(**post_data)
                        session.add(post)
                    saved += 1
                except Exception:
                    continue
        return saved

    def save_comments_batch(self, comments_data: list[dict]) -> int:
        """Save multiple comments in batch.

        Args:
            comments_data: List of comment dictionaries

        Returns:
            Number of comments saved
        """
        saved = 0
        with self.get_session() as session:
            for comment_data in comments_data:
                try:
                    existing = session.query(CommentModel).filter_by(id=comment_data["id"]).first()
                    if existing:
                        for key, value in comment_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        comment = CommentModel(**comment_data)
                        session.add(comment)
                    saved += 1
                except Exception:
                    continue
        return saved

    # ----- Hierarchical save -----

    def save_page_with_posts(
        self,
        page_id: str,
        url: str,
        title: str,
        posts_data: list[dict],
        html_size: int = 0,
        preprocessed_data: dict | None = None,
        raw_metadata: dict | None = None,
        scrape_status: str = "success",
        error_message: str | None = None,
    ) -> str:
        """Save a Facebook page with all its preprocessed posts and comments.

        This is the main method called after the preprocessor finishes.
        It stores the hierarchical structure: page -> posts -> comments.
        Uses upsert logic to handle duplicate posts gracefully.

        Args:
            page_id: Unique ID for the page
            url: Page URL
            title: Page title
            posts_data: List of post dicts from preprocessor (each may contain 'comments' key)
            html_size: Size of the raw HTML in chars
            preprocessed_data: Optional hierarchical JSON from preprocessor
            raw_metadata: Optional metadata dict
            scrape_status: 'success', 'error', or 'partial'
            error_message: Optional error message

        Returns:
            The page_id of the saved page
        """
        import json

        with self.get_session() as session:
            # Save or update the page
            existing_page = session.query(PageModel).filter_by(id=page_id).first()

            if existing_page:
                existing_page.title = title
                existing_page.html_size = html_size
                existing_page.posts_extracted = len(posts_data)
                existing_page.scrape_status = scrape_status
                existing_page.error_message = error_message
                if preprocessed_data:
                    existing_page.preprocessed_data = json.dumps(
                        preprocessed_data, ensure_ascii=False
                    )
                if raw_metadata:
                    existing_page.raw_metadata = json.dumps(raw_metadata, ensure_ascii=False)
                # Delete old posts (cascade will delete their comments)
                session.query(PostModel).filter_by(page_id=page_id).delete()
                session.flush()
            else:
                new_page = PageModel(
                    id=page_id,
                    url=url,
                    title=title,
                    source="facebook",
                    html_size=html_size,
                    posts_extracted=len(posts_data),
                    comments_extracted=0,  # Will be updated
                    preprocessed_data=json.dumps(preprocessed_data, ensure_ascii=False)
                    if preprocessed_data
                    else "",
                    raw_metadata=json.dumps(raw_metadata, ensure_ascii=False)
                    if raw_metadata
                    else "",
                    scrape_status=scrape_status,
                    error_message=error_message,
                )
                session.add(new_page)
                session.flush()

            # Save posts and their comments
            total_comments = 0
            seen_post_ids = set()  # Track IDs in this batch to avoid duplicates

            for post_idx, post_data in enumerate(posts_data):
                # Extract comments from post data if present
                comments = post_data.pop("comments", [])

                # Generate unique post_id: prefer preprocessor's id, else use idx-based
                post_id = post_data.get("id")
                if not post_id or post_id in seen_post_ids:
                    # Use page_id + idx for guaranteed uniqueness
                    post_id = f"{page_id}_p{post_idx}"

                seen_post_ids.add(post_id)

                # Parse date if string
                date_val = post_data.get("date")
                if isinstance(date_val, str):
                    try:
                        from datetime import datetime

                        date_val = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        date_val = None

                # Check if post already exists in this session
                existing_post = session.query(PostModel).filter_by(id=post_id).first()
                if existing_post:
                    # Update fields
                    existing_post.text = post_data.get("text", "")
                    existing_post.author = post_data.get("author", "")
                    existing_post.date = date_val
                    existing_post.likes = int(post_data.get("likes", 0) or 0)
                    existing_post.comments_count = len(comments)
                    existing_post.shares = int(post_data.get("shares", 0) or 0)
                    existing_post.url = post_data.get("url", "")
                    existing_post.page_id = page_id
                else:
                    post = PostModel(
                        id=post_id,
                        text=post_data.get("text", ""),
                        author=post_data.get("author", ""),
                        date=date_val,
                        likes=int(post_data.get("likes", 0) or 0),
                        comments_count=len(comments),
                        shares=int(post_data.get("shares", 0) or 0),
                        url=post_data.get("url", ""),
                        page_id=page_id,
                        source="facebook_page",
                    )
                    session.add(post)

                # Save comments for this post
                for comment_idx, comment_data in enumerate(comments):
                    comment_id = comment_data.get("id")
                    if not comment_id:
                        comment_id = f"{post_id}_c{comment_idx}"

                    comment_date = comment_data.get("date")
                    if isinstance(comment_date, str):
                        try:
                            from datetime import datetime

                            comment_date = datetime.fromisoformat(
                                comment_date.replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            comment_date = None

                    # Check if comment already exists
                    existing_comment = session.query(CommentModel).filter_by(id=comment_id).first()
                    if existing_comment:
                        existing_comment.text = comment_data.get("text", "")
                        existing_comment.author = comment_data.get("author", "")
                        existing_comment.date = comment_date
                        existing_comment.likes = int(comment_data.get("likes", 0) or 0)
                        existing_comment.post_id = post_id
                    else:
                        comment = CommentModel(
                            id=comment_id,
                            text=comment_data.get("text", ""),
                            author=comment_data.get("author", ""),
                            date=comment_date,
                            likes=int(comment_data.get("likes", 0) or 0),
                            post_id=post_id,
                            url=comment_data.get("url", ""),
                        )
                        session.add(comment)
                    total_comments += 1

            # Update comments count
            existing_page_check = session.query(PageModel).filter_by(id=page_id).first()
            if existing_page_check:
                existing_page_check.comments_extracted = total_comments

            return page_id

    # ----- Read helpers -----

    def get_posts(self, page_id: str | None = None, limit: int = 100) -> list[dict]:
        """Get posts from database.

        Args:
            page_id: Optional page ID to filter by
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries
        """
        with self.get_session() as session:
            query = session.query(PostModel)
            if page_id:
                query = query.filter_by(page_id=page_id)
            return [p.to_dict() for p in query.limit(limit).all()]

    def get_pages(self, limit: int = 100) -> list[dict]:
        """Get scraped pages from database.

        Args:
            limit: Maximum number of pages to return

        Returns:
            List of page dictionaries
        """
        with self.get_session() as session:
            return [p.to_dict() for p in session.query(PageModel).limit(limit).all()]

    def get_page_with_posts(self, page_id: str) -> dict | None:
        """Get a page with all its posts and comments (hierarchical).

        Args:
            page_id: Page ID

        Returns:
            Dictionary with page info, posts, and comments
        """
        import json

        with self.get_session() as session:
            page = session.query(PageModel).filter_by(id=page_id).first()
            if not page:
                return None

            result = page.to_dict()

            # Parse preprocessed_data if present
            if page.preprocessed_data:
                try:
                    result["preprocessed_data"] = json.loads(page.preprocessed_data)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Get posts for this page
            posts = session.query(PostModel).filter_by(page_id=page_id).all()
            result["posts"] = []
            for post in posts:
                post_dict = post.to_dict()
                comments = session.query(CommentModel).filter_by(post_id=post.id).all()
                post_dict["comments"] = [c.to_dict() for c in comments]
                result["posts"].append(post_dict)

            return result

    def get_comments(self, post_id: str, limit: int = 100) -> list[dict]:
        """Get comments from database.

        Args:
            post_id: Post ID to filter by
            limit: Maximum number of comments to return

        Returns:
            List of comment dictionaries
        """
        with self.get_session() as session:
            comments = session.query(CommentModel).filter_by(post_id=post_id).limit(limit).all()
            return [c.to_dict() for c in comments]

    def get_analysis_results(self, content_type: str | None = None) -> list[dict]:
        """Get analysis results from database.

        Args:
            content_type: Optional filter ('post' or 'comment')

        Returns:
            List of analysis result dictionaries
        """
        with self.get_session() as session:
            query = session.query(AnalysisResultModel)
            if content_type:
                query = query.filter_by(content_type=content_type)
            return [r.to_dict() for r in query.all()]

    def get_seed_pages(self, is_seed: bool | None = None) -> list[dict]:
        """Get seed pages from database.

        Args:
            is_seed: Optional filter for seed status

        Returns:
            List of seed page dictionaries
        """
        with self.get_session() as session:
            query = session.query(SeedPageModel)
            if is_seed is not None:
                query = query.filter_by(is_seed="true" if is_seed else "false")
            return [p.to_dict() for p in query.all()]

    def get_stats(self) -> dict:
        """Get database statistics with hierarchical counts.

        Returns:
            Dictionary with counts of pages, posts, comments, etc.
        """
        with self.get_session() as session:
            return {
                "pages_count": session.query(PageModel).count(),
                "posts_count": session.query(PostModel).count(),
                "comments_count": session.query(CommentModel).count(),
                "analysis_results_count": session.query(AnalysisResultModel).count(),
                "seed_pages_count": session.query(SeedPageModel).count(),
            }

    # ----- Batch analysis methods -----

    def save_or_update_analysis_result(self, result_data: dict) -> int:
        """Upsert an analysis result.

        If a result with the same ``(content_type, content_id)`` already
        exists, its fields are updated.  Otherwise a new row is created.

        Args:
            result_data: Dictionary with AnalysisResultModel fields

        Returns:
            ID of the saved/updated result
        """
        content_type = result_data.get("content_type", "")
        content_id = result_data.get("content_id", "")

        with self.get_session() as session:
            existing = (
                session.query(AnalysisResultModel)
                .filter_by(
                    content_type=content_type,
                    content_id=content_id,
                )
                .first()
            )

            if existing:
                for key, value in result_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                return existing.id

            result = AnalysisResultModel(**result_data)
            session.add(result)
            session.flush()
            return result.id

    def get_unanalyzed_posts(self) -> list[dict]:
        """Get posts that have no analysis result yet.

        Returns:
            List of post dicts without an entry in ``analysis_results``
        """
        with self.get_session() as session:
            analyzed_ids = {
                r.content_id
                for r in session.query(AnalysisResultModel).filter_by(content_type="post").all()
            }
            posts = session.query(PostModel).all()
            return [p.to_dict() for p in posts if p.id not in analyzed_ids]

    def get_unanalyzed_comments(self) -> list[dict]:
        """Get comments that have no analysis result yet.

        Returns:
            List of comment dicts without an entry in ``analysis_results``
        """
        with self.get_session() as session:
            analyzed_ids = {
                r.content_id
                for r in session.query(AnalysisResultModel).filter_by(content_type="comment").all()
            }
            comments = session.query(CommentModel).all()
            return [c.to_dict() for c in comments if c.id not in analyzed_ids]

    def get_analysis_result_by_content(self, content_type: str, content_id: str) -> dict | None:
        """Get a single analysis result by content type and ID.

        Args:
            content_type: ``"post"`` or ``"comment"``
            content_id: ID of the post or comment

        Returns:
            Analysis result dict, or None
        """
        with self.get_session() as session:
            result = (
                session.query(AnalysisResultModel)
                .filter_by(
                    content_type=content_type,
                    content_id=content_id,
                )
                .first()
            )
            return result.to_dict() if result else None

    def get_analysis_grouped(self) -> list[dict]:
        """Get analysis results grouped by page, with post/comment details.

        Returns:
            List of page-level dicts containing their analysis results
        """

        with self.get_session() as session:
            pages = session.query(PageModel).all()
            result = []
            for page in pages:
                page_dict = page.to_dict()
                posts = session.query(PostModel).filter_by(page_id=page.id).all()
                page_dict["posts"] = []
                for post in posts:
                    post_dict = post.to_dict()
                    post_analysis = (
                        session.query(AnalysisResultModel)
                        .filter_by(content_type="post", content_id=post.id)
                        .first()
                    )
                    post_dict["analysis"] = post_analysis.to_dict() if post_analysis else None

                    comments = session.query(CommentModel).filter_by(post_id=post.id).all()
                    post_dict["comments"] = []
                    for comment in comments:
                        c_dict = comment.to_dict()
                        comment_analysis = (
                            session.query(AnalysisResultModel)
                            .filter_by(content_type="comment", content_id=comment.id)
                            .first()
                        )
                        c_dict["analysis"] = (
                            comment_analysis.to_dict() if comment_analysis else None
                        )
                        post_dict["comments"].append(c_dict)

                    page_dict["posts"].append(post_dict)
                result.append(page_dict)
            return result

    @staticmethod
    def _generate_id(*parts: str) -> str:
        """Generate a unique ID from string parts using MD5 hash."""
        import hashlib

        content = "_".join(str(p) for p in parts)
        return hashlib.md5(content.encode()).hexdigest()[:16]


# Global database instance
_database: Database | None = None


def get_database(database_url: str = "sqlite:///data/tfm.db") -> Database:
    """Get or create database instance."""
    global _database
    if _database is None:
        _database = Database(database_url)
    return _database
