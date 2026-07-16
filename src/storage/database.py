"""Database manager for SQLite operations.

The model definitions live in ``src.storage.models`` (one module per
class). This module only owns the ``Database`` class which encapsulates
sessions, CRUD helpers and the hierarchical ``save_page_with_posts``
write path used by the scraper.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.storage.base import Base
from src.storage.models import (
    AnalysisFeedbackLabelModel,
    AnalysisFeedbackModel,
    AnalysisLabelModel,
    AnalysisResultModel,
    CommentModel,
    PageModel,
    PostModel,
    SeedPageModel,
    SessionModel,
    UserModel,
)
from src.storage.models.session import SESSION_TTL_HOURS


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

        Multi-label side tables (``analysis_labels`` and
        ``analysis_feedback_labels``) are created when missing. They
        are intentionally **not** backfilled — the user is expected
        to run ``python -m src.report analyze --reanalyze`` to repopulate
        with the new multi-label schema.

        Safe to run multiple times.
        """
        from sqlalchemy import inspect, text

        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())

        # Ensure multi-label side tables exist. They are created with
        # plain DDL (not via Base.metadata.create_all on the parent)
        # so the migration is a single pass.
        if "analysis_labels" not in existing_tables:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE analysis_labels (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            analysis_result_id INTEGER NOT NULL
                                REFERENCES analysis_results(id) ON DELETE CASCADE,
                            orden INTEGER NOT NULL DEFAULT 0,
                            categoria VARCHAR NOT NULL,
                            dimension VARCHAR,
                            severidad VARCHAR NOT NULL DEFAULT 'ninguna',
                            justificacion TEXT NOT NULL DEFAULT '',
                            evidencia TEXT NOT NULL DEFAULT '',
                            regla_disparada VARCHAR,
                            marcadores_detectados TEXT,
                            confianza VARCHAR,
                            score_ajuste VARCHAR,
                            es_falso_positivo_probable VARCHAR NOT NULL DEFAULT 'false',
                            created_at DATETIME NOT NULL
                        )
                        """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX ix_analysis_labels_result "
                        "ON analysis_labels(analysis_result_id)"
                    )
                )

        if "analysis_feedback_labels" not in existing_tables:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE analysis_feedback_labels (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            analysis_feedback_id INTEGER NOT NULL
                                REFERENCES analysis_feedback(id) ON DELETE CASCADE,
                            orden INTEGER NOT NULL DEFAULT 0,
                            categoria VARCHAR NOT NULL,
                            dimension VARCHAR,
                            severidad VARCHAR NOT NULL DEFAULT 'ninguna',
                            justificacion TEXT NOT NULL DEFAULT '',
                            evidencia TEXT NOT NULL DEFAULT '',
                            regla_disparada VARCHAR,
                            marcadores_detectados TEXT,
                            confianza VARCHAR,
                            score_ajuste VARCHAR,
                            es_falso_positivo_probable VARCHAR NOT NULL DEFAULT 'false',
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL
                        )
                        """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX ix_analysis_feedback_labels_fb "
                        "ON analysis_feedback_labels(analysis_feedback_id)"
                    )
                )

        # Refresh inspector after potential table creation.
        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())

        if "analysis_results" not in existing_tables:
            return

        # Users table — created if missing. The review/admin accounts for
        # the NiceGUI login.
        if "users" not in existing_tables:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username VARCHAR NOT NULL UNIQUE,
                            password_hash VARCHAR NOT NULL,
                            role VARCHAR NOT NULL DEFAULT 'reviewer',
                            full_name VARCHAR,
                            is_active VARCHAR NOT NULL DEFAULT 'true',
                            created_at DATETIME NOT NULL,
                            last_login DATETIME
                        )
                        """
                    )
                )
                conn.execute(text("CREATE UNIQUE INDEX ix_users_username ON users(username)"))

        # Sessions table — persistent login sessions so the NiceGUI
        # dashboard survives server restarts. Without this, ``app.storage.user``
        # is in-memory only and every reboot logs everyone out.
        if "sessions" not in existing_tables:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE sessions (
                            id VARCHAR PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            username VARCHAR NOT NULL,
                            created_at DATETIME NOT NULL,
                            expires_at DATETIME NOT NULL,
                            last_seen_at DATETIME NOT NULL,
                            user_agent VARCHAR
                        )
                        """
                    )
                )
                conn.execute(text("CREATE INDEX ix_sessions_user_id ON sessions(user_id)"))
                conn.execute(text("CREATE INDEX ix_sessions_expires_at ON sessions(expires_at)"))

        # analysis_feedback columns for reviewer identity. Populated by
        # the NiceGUI validation UI; left NULL for legacy rows.
        feedback_additions: list[tuple[str, str]] = []
        if "analysis_feedback" in existing_tables:
            feedback_cols = {c["name"] for c in inspector.get_columns("analysis_feedback")}
            if "reviewer_user_id" not in feedback_cols:
                feedback_additions.append(("reviewer_user_id", "INTEGER"))
            if "reviewer_username" not in feedback_cols:
                feedback_additions.append(("reviewer_username", "VARCHAR"))
            if "regla_disparada_sistema" not in feedback_cols:
                feedback_additions.append(("regla_disparada_sistema", "VARCHAR"))

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
        if "exclusion_label" not in existing_cols:
            additions.append(("exclusion_label", "VARCHAR"))
        if "exclusion_codigo" not in existing_cols:
            additions.append(("exclusion_codigo", "VARCHAR"))
        if "exclusion_justificacion" not in existing_cols:
            additions.append(("exclusion_justificacion", "TEXT"))

        # Migrate seed_pages: add ``source`` column if missing.
        seed_additions: list[tuple[str, str]] = []
        if "seed_pages" in existing_tables:
            seed_cols = {c["name"] for c in inspector.get_columns("seed_pages")}
            if "source" not in seed_cols:
                seed_additions.append(("source", "VARCHAR DEFAULT 'facebook_page'"))

        # Build list of comments additions independently so we can
        # decide whether to skip the analysis_results block entirely.
        comment_additions: list[tuple[str, str]] = []
        if "comments" in existing_tables:
            comment_cols = {c["name"] for c in inspector.get_columns("comments")}
            if "time_ago" not in comment_cols:
                comment_additions.append(("time_ago", "VARCHAR"))
            if "responses" not in comment_cols:
                comment_additions.append(("responses", "INTEGER DEFAULT 0"))

        if (
            not additions
            and "tipo" not in existing_cols
            and "confidence" not in existing_cols
            and not seed_additions
            and not comment_additions
            and not feedback_additions
        ):
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

            for col_name, col_type in seed_additions:
                conn.execute(text(f"ALTER TABLE seed_pages ADD COLUMN {col_name} {col_type}"))

            for col_name, col_type in comment_additions:
                conn.execute(text(f"ALTER TABLE comments ADD COLUMN {col_name} {col_type}"))

            for col_name, col_type in feedback_additions:
                conn.execute(
                    text(f"ALTER TABLE analysis_feedback ADD COLUMN {col_name} {col_type}")
                )

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

    @staticmethod
    def _coerce_datetime_fields(data: dict, fields: tuple[str, ...]) -> dict:
        """Convert ISO-format strings in ``fields`` to ``datetime``.

        SQLAlchemy ``DateTime`` columns reject naive string inputs; this
        helper keeps the call sites clean by normalizing the dict before
        it reaches the ORM.
        """
        from datetime import datetime

        for f in fields:
            value = data.get(f)
            if isinstance(value, str) and value:
                try:
                    data[f] = datetime.fromisoformat(value)
                except ValueError:
                    data[f] = None
        return data

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
        from sqlalchemy import inspect

        valid_keys = {c.key for c in inspect(PostModel).mapper.columns}
        saved = 0
        with self.get_session() as session:
            for post_data in posts_data:
                try:
                    post_data = self._coerce_datetime_fields(
                        post_data,
                        ("date", "created_at"),
                    )
                    post_data = {k: v for k, v in post_data.items() if k in valid_keys}
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

        Before insertion, the batch is de-duplicated by
        :func:`src.scraper.comment_dedup.find_duplicate_groups` so two
        copies of the same comment (same ``post_id`` + ``author``,
        normalized text identical or fuzzy ≥ ``0.95``) collapse to a
        single row. The survivor is chosen by
        :func:`src.scraper.comment_dedup.pick_canonical` (longest text,
        then most likes, then earliest created_at).

        Args:
            comments_data: List of comment dictionaries

        Returns:
            Number of comments saved
        """
        from sqlalchemy import inspect

        from src.scraper.comment_dedup import find_duplicate_groups, pick_canonical

        # De-dupe within the batch. ``find_duplicate_groups`` returns
        # only the duplicate groups (size ≥ 2); singletons pass through.
        # Within each group we drop the non-canonical copies and keep
        # the survivor chosen by ``pick_canonical``.
        groups = find_duplicate_groups(comments_data, threshold=0.95)
        if groups:
            drop_ids: set[int] = set()
            for group in groups:
                canonical = pick_canonical(group)
                for c in group:
                    if c is not canonical:
                        drop_ids.add(id(c))
            comments_data = [c for c in comments_data if id(c) not in drop_ids]

        valid_keys = {c.key for c in inspect(CommentModel).mapper.columns}
        saved = 0
        with self.get_session() as session:
            for comment_data in comments_data:
                try:
                    comment_data = self._coerce_datetime_fields(
                        comment_data,
                        ("date", "created_at"),
                    )
                    comment_data = {k: v for k, v in comment_data.items() if k in valid_keys}
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

                # De-dupe comments within this post: the scraper can
                # emit the same comment twice when the DOM path and the
                # LLM fallback both fire, or when polling retries see
                # the same elements. See comment_dedup for the rules.
                if comments:
                    from src.scraper.comment_dedup import (
                        find_duplicate_groups,
                        pick_canonical,
                    )

                    inline_groups = find_duplicate_groups(comments, threshold=0.95)
                    if inline_groups:
                        drop_ids: set[int] = set()
                        for group in inline_groups:
                            canonical = pick_canonical(group)
                            for c in group:
                                if c is not canonical:
                                    drop_ids.add(id(c))
                        comments = [c for c in comments if id(c) not in drop_ids]

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

    def get_orphan_comments(self) -> list[dict]:
        """Get comments whose post_id doesn't exist in the posts table.

        Returns:
            List of orphan comment dictionaries
        """
        with self.get_session() as session:
            post_ids = {p.id for p in session.query(PostModel).all()}
            orphan_comments = (
                session.query(CommentModel).filter(~CommentModel.post_id.in_(post_ids)).all()
            )
            return [c.to_dict() for c in orphan_comments]

    def get_analysis_results(self, content_type: str | None = None) -> list[dict]:
        """Get analysis results from database.

        Each returned dict is enriched with a ``labels`` key holding the
        ordered list of :class:`AnalysisLabelModel` rows (or an empty
        list when the analysis was created before the multi-label
        schema and never re-analyzed).

        Args:
            content_type: Optional filter ('post' or 'comment')

        Returns:
            List of analysis result dictionaries
        """
        with self.get_session() as session:
            query = session.query(AnalysisResultModel)
            if content_type:
                query = query.filter_by(content_type=content_type)
            rows = [r.to_dict() for r in query.all()]

            ids = [r["id"] for r in rows if r.get("id") is not None]
            labels_by_id: dict[int, list[dict]] = {ar_id: [] for ar_id in ids}
            if ids:
                label_rows = (
                    session.query(AnalysisLabelModel)
                    .filter(AnalysisLabelModel.analysis_result_id.in_(ids))
                    .order_by(
                        AnalysisLabelModel.analysis_result_id.asc(),
                        AnalysisLabelModel.orden.asc(),
                    )
                    .all()
                )
                for lr in label_rows:
                    labels_by_id.setdefault(lr.analysis_result_id, []).append(lr.to_dict())

        for r in rows:
            labels = labels_by_id.get(r.get("id"), [])
            r["labels"] = labels
        return rows

    def get_feedback_with_labels(self, content_type: str | None = None) -> list[dict]:
        """Return feedback rows enriched with their corrected ``labels`` list.

        The flat ``corrected_*`` columns stay (backwards-compat) and
        mirror the primary corrected label; the new ``labels`` key
        carries the full list.
        """
        with self.get_session() as session:
            query = session.query(AnalysisFeedbackModel)
            if content_type:
                query = query.filter_by(content_type=content_type)
            fb_rows = [r.to_dict() for r in query.all()]

            ids = [r["id"] for r in fb_rows if r.get("id") is not None]
            labels_by_id: dict[int, list[dict]] = {fb_id: [] for fb_id in ids}
            if ids:
                label_rows = (
                    session.query(AnalysisFeedbackLabelModel)
                    .filter(AnalysisFeedbackLabelModel.analysis_feedback_id.in_(ids))
                    .order_by(
                        AnalysisFeedbackLabelModel.analysis_feedback_id.asc(),
                        AnalysisFeedbackLabelModel.orden.asc(),
                    )
                    .all()
                )
                for lr in label_rows:
                    labels_by_id.setdefault(lr.analysis_feedback_id, []).append(lr.to_dict())

        for r in fb_rows:
            r["labels"] = labels_by_id.get(r.get("id"), [])
        return fb_rows

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
            feedback_total = session.query(AnalysisFeedbackModel).count()
            feedback_disagreements = (
                session.query(AnalysisFeedbackModel).filter_by(agrees="false").count()
            )
            feedback_agreements = (
                session.query(AnalysisFeedbackModel).filter_by(agrees="true").count()
            )
            feedback_pending_index = (
                session.query(AnalysisFeedbackModel)
                .filter_by(indexed_in_chromadb="false")
                .filter(AnalysisFeedbackModel.agrees == "false")
                .count()
            )
            return {
                "pages_count": session.query(PageModel).count(),
                "posts_count": session.query(PostModel).count(),
                "comments_count": session.query(CommentModel).count(),
                "analysis_results_count": session.query(AnalysisResultModel).count(),
                "seed_pages_count": session.query(SeedPageModel).count(),
                "feedback_count": feedback_total,
                "feedback_disagreement_count": feedback_disagreements,
                "feedback_agreement_count": feedback_agreements,
                "feedback_pending_index_count": feedback_pending_index,
            }

    # ----- Batch analysis methods -----

    def save_or_update_analysis_result(self, result_data: dict) -> int:
        """Upsert an analysis result.

        If a result with the same ``(content_type, content_id)`` already
        exists, its fields are updated.  Otherwise a new row is created.

        When ``result_data`` carries a ``clasificaciones`` list (list of
        dicts with the same shape as
        :class:`~src.analyzer.rag_classifier.LabelAssignment`), the
        side table ``analysis_labels`` is replaced with the new list
        and the flat ``analysis_results`` columns (``categoria`` /
        ``dimension`` / ``severidad`` / ``justificacion`` / ``evidencia``
        / ``regla_disparada`` / ``marcadores_detectados`` / etc.) are
        populated with the **primary** label (highest severity, ties
        broken by list order) so legacy single-column queries keep
        working.

        Args:
            result_data: Dictionary with AnalysisResultModel fields.
                May also include ``clasificaciones`` (list of label
                dicts).

        Returns:
            ID of the saved/updated result
        """
        content_type = result_data.get("content_type", "")
        content_id = result_data.get("content_id", "")

        clasificaciones_raw = result_data.pop("clasificaciones", None)

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
                result_id = existing.id
            else:
                result = AnalysisResultModel(**result_data)
                session.add(result)
                session.flush()
                result_id = result.id

            if isinstance(clasificaciones_raw, list):
                self._replace_labels_for_result(session, result_id, clasificaciones_raw)

            return result_id

    @staticmethod
    def _primary_label_dict(labels: list[dict]) -> dict:
        """Pick the primary label for filling the flat columns.

        Delegates to :func:`src.analyzer.category_mapping.primary_label`
        — single source of truth for the severity ranking so the UI
        layer (``adjusted_report``) and the persistence layer stay in
        sync. Always returns a dict with the full set of flat-column
        keys (filled with neutral defaults when the chosen label does
        not carry them).
        """
        from src.analyzer.category_mapping import primary_label

        return primary_label(labels)

    @staticmethod
    def _replace_labels_for_result(
        session: Session, analysis_result_id: int, labels: list[dict]
    ) -> None:
        """Replace the ``analysis_labels`` rows for one result.

        Also mirrors the primary label back into the flat
        ``analysis_results`` columns for backwards compatibility.
        """
        # Wipe existing labels for this result.
        session.query(AnalysisLabelModel).filter_by(analysis_result_id=analysis_result_id).delete(
            synchronize_session=False
        )

        import json as _json

        for orden, lbl in enumerate(labels):
            marcadores = lbl.get("marcadores_detectados") or []
            if isinstance(marcadores, list):
                marcadores_json = _json.dumps(marcadores, ensure_ascii=False)
            else:
                marcadores_json = _json.dumps(
                    [m.strip() for m in str(marcadores).split(",") if m.strip()],
                    ensure_ascii=False,
                )
            row = AnalysisLabelModel(
                analysis_result_id=analysis_result_id,
                orden=orden,
                categoria=str(lbl.get("categoria") or "ninguna"),
                dimension=lbl.get("dimension"),
                severidad=str(lbl.get("severidad") or "ninguna"),
                justificacion=str(lbl.get("justificacion") or ""),
                evidencia=str(lbl.get("evidencia") or ""),
                regla_disparada=lbl.get("regla_disparada"),
                marcadores_detectados=marcadores_json,
                confianza=_to_str_or_none(lbl.get("confianza")),
                score_ajuste=_to_str_or_none(lbl.get("score_ajuste")),
                es_falso_positivo_probable=_to_bool_str(lbl.get("es_falso_positivo_probable")),
            )
            session.add(row)

        # Mirror the primary label into the flat columns.
        import json as _json

        primary = Database._primary_label_dict(labels)
        marcadores_flat = primary["marcadores_detectados"]
        if isinstance(marcadores_flat, list):
            marcadores_str = _json.dumps(marcadores_flat, ensure_ascii=False)
        elif marcadores_flat is None:
            marcadores_str = None
        else:
            marcadores_str = str(marcadores_flat)

        result = session.query(AnalysisResultModel).filter_by(id=analysis_result_id).one()
        result.categoria = primary["categoria"]
        result.dimension = primary["dimension"]
        result.severidad = primary["severidad"]
        result.justificacion = primary["justificacion"]
        result.evidencia = primary["evidencia"]
        result.regla_disparada = primary["regla_disparada"]
        result.marcadores_detectados = marcadores_str
        result.confianza = primary["confianza"]
        result.score_ajuste = primary["score_ajuste"]
        result.es_falso_positivo_probable = primary["es_falso_positivo_probable"]

    def get_labels_for_analysis(self, analysis_result_id: int) -> list[dict[str, object]]:
        """Return the ordered list of labels for one analysis result."""
        with self.get_session() as session:
            rows = (
                session.query(AnalysisLabelModel)
                .filter_by(analysis_result_id=analysis_result_id)
                .order_by(AnalysisLabelModel.orden.asc())
                .all()
            )
            return [r.to_dict() for r in rows]

    def get_all_analysis_labels(self) -> dict[int, list[dict[str, object]]]:
        """Return ``{analysis_result_id: [labels...]}`` for every analysis."""
        with self.get_session() as session:
            rows = (
                session.query(AnalysisLabelModel)
                .order_by(
                    AnalysisLabelModel.analysis_result_id.asc(),
                    AnalysisLabelModel.orden.asc(),
                )
                .all()
            )
            out: dict[int, list[dict[str, object]]] = {}
            for r in rows:
                out.setdefault(r.analysis_result_id, []).append(r.to_dict())
            return out

    def get_feedback_labels(self, feedback_id: int) -> list[dict[str, object]]:
        """Return the ordered list of corrected labels for one feedback row."""
        with self.get_session() as session:
            rows = (
                session.query(AnalysisFeedbackLabelModel)
                .filter_by(analysis_feedback_id=feedback_id)
                .order_by(AnalysisFeedbackLabelModel.orden.asc())
                .all()
            )
            return [r.to_dict() for r in rows]

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

    # ----- Feedback (human validation) -----

    def save_feedback(self, feedback_data: dict) -> int:
        """Upsert a feedback row.

        The logical key is ``analysis_result_id`` — at most one feedback per
        analysis. If a row already exists for that ``analysis_result_id``,
        its fields are updated and ``indexed_in_chromadb`` is reset to
        ``"false"`` so the corrected version can be re-pushed.

        When ``feedback_data`` carries a ``corrected_labels`` list
        (list of label dicts with the same shape as
        :class:`~src.analyzer.rag_classifier.LabelAssignment`), the
        side table ``analysis_feedback_labels`` is replaced with the
        new list and the flat ``corrected_*`` columns mirror the
        **primary** corrected label.

        Args:
            feedback_data: Dictionary with ``AnalysisFeedbackModel``
                fields. May also include ``corrected_labels``.

        Returns:
            ID of the saved (or updated) feedback row.
        """
        analysis_result_id = feedback_data.get("analysis_result_id")

        corrected_labels_raw = feedback_data.pop("corrected_labels", None)

        with self.get_session() as session:
            existing = (
                session.query(AnalysisFeedbackModel)
                .filter_by(analysis_result_id=analysis_result_id)
                .first()
            )

            # Auto-populate regla_disparada_sistema from analysis_results
            # if the caller did not pass it explicitly. Lets the validation
            # UI show "what rule did the AI fire?" without an extra JOIN.
            # ``agrees`` (yes/no) is the human's verdict on the rule.
            if "regla_disparada_sistema" not in feedback_data and analysis_result_id is not None:
                ar_rule = session.execute(
                    text("SELECT regla_disparada FROM analysis_results WHERE id = :arid"),
                    {"arid": analysis_result_id},
                ).scalar()
                feedback_data["regla_disparada_sistema"] = ar_rule

            if existing:
                for key, value in feedback_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                # If the human changed their mind, the old ChromaDB entry
                # is stale — force a re-index on next sync.
                if feedback_data.get("indexed_in_chromadb") is None:
                    existing.indexed_in_chromadb = "false"
                    existing.chromadb_id = None
                    existing.chromadb_indexed_at = None
                feedback_id = existing.id
            else:
                row = AnalysisFeedbackModel(**feedback_data)
                session.add(row)
                session.flush()
                feedback_id = row.id

            if (
                isinstance(corrected_labels_raw, list)
                and str(feedback_data.get("agrees", "false")).lower() == "false"
            ):
                self._replace_feedback_labels(session, feedback_id, corrected_labels_raw)

            return feedback_id

    @staticmethod
    def _replace_feedback_labels(session: Session, feedback_id: int, labels: list[dict]) -> None:
        """Replace the ``analysis_feedback_labels`` rows for one feedback row.

        Also mirrors the primary label back into the flat
        ``analysis_feedback`` columns for backwards compatibility.
        """
        session.query(AnalysisFeedbackLabelModel).filter_by(
            analysis_feedback_id=feedback_id
        ).delete(synchronize_session=False)

        import json as _json

        for orden, lbl in enumerate(labels):
            marcadores = lbl.get("marcadores_detectados") or []
            if isinstance(marcadores, list):
                marcadores_json = _json.dumps(marcadores, ensure_ascii=False)
            else:
                marcadores_json = _json.dumps(
                    [m.strip() for m in str(marcadores).split(",") if m.strip()],
                    ensure_ascii=False,
                )
            row = AnalysisFeedbackLabelModel(
                analysis_feedback_id=feedback_id,
                orden=orden,
                categoria=str(lbl.get("categoria") or "ninguna"),
                dimension=lbl.get("dimension"),
                severidad=str(lbl.get("severidad") or "ninguna"),
                justificacion=str(lbl.get("justificacion") or ""),
                evidencia=str(lbl.get("evidencia") or ""),
                regla_disparada=lbl.get("regla_disparada"),
                marcadores_detectados=marcadores_json,
                confianza=_to_str_or_none(lbl.get("confianza")),
                score_ajuste=_to_str_or_none(lbl.get("score_ajuste")),
                es_falso_positivo_probable=_to_bool_str(lbl.get("es_falso_positivo_probable")),
            )
            session.add(row)

        # Mirror the primary label into the flat columns.
        primary = Database._primary_label_dict(labels)
        fb = session.query(AnalysisFeedbackModel).filter_by(id=feedback_id).one()
        fb.corrected_categoria = primary["categoria"]
        fb.corrected_dimension = primary["dimension"]
        fb.corrected_justificacion = primary["justificacion"]

    def get_feedback_for_analysis(self, analysis_result_id: int) -> dict | None:
        """Return the feedback for a single analysis result, or ``None``.

        The returned dict is enriched with a ``labels`` key carrying the
        ordered list of corrected labels from
        ``analysis_feedback_labels`` (so the validation UI can re-render
        the multi-label form with all existing overrides — not just
        the primary flat-column one).
        """
        with self.get_session() as session:
            row = (
                session.query(AnalysisFeedbackModel)
                .filter_by(analysis_result_id=analysis_result_id)
                .first()
            )
            if not row:
                return None
            out = row.to_dict()
            label_rows = (
                session.query(AnalysisFeedbackLabelModel)
                .filter_by(analysis_feedback_id=row.id)
                .order_by(AnalysisFeedbackLabelModel.orden.asc())
                .all()
            )
            out["labels"] = [
                {
                    "categoria": lr.categoria,
                    "dimension": lr.dimension,
                    "severidad": lr.severidad,
                    "justificacion": lr.justificacion,
                    "evidencia": lr.evidencia,
                    "es_falso_positivo_probable": lr.es_falso_positivo_probable,
                    "regla_disparada": lr.regla_disparada,
                    "marcadores_detectados": lr.marcadores_detectados,
                }
                for lr in label_rows
            ]
            return out

    def list_feedback(
        self,
        content_type: str | None = None,
        only_disagreements: bool = False,
        only_pending_index: bool = False,
    ) -> list[dict]:
        """List feedback rows with optional filters.

        Each returned dict is enriched with a ``labels`` key holding the
        ordered list of corrected labels (empty if no overrides were
        stored via the multi-label API).

        Args:
            content_type: Filter by ``"post"`` or ``"comment"``.
            only_disagreements: If True, return only ``agrees="false"``.
            only_pending_index: If True, return only rows whose
                ``indexed_in_chromadb`` is ``"false"`` AND that are
                disagreements (corrections worth pushing).

        Returns:
            List of feedback dicts.
        """
        with self.get_session() as session:
            query = session.query(AnalysisFeedbackModel)
            if content_type:
                query = query.filter_by(content_type=content_type)
            if only_disagreements:
                query = query.filter_by(agrees="false")
            if only_pending_index:
                query = query.filter_by(indexed_in_chromadb="false", agrees="false")
            rows = [r.to_dict() for r in query.all()]

            ids = [r["id"] for r in rows if r.get("id") is not None]
            labels_by_id: dict[int, list[dict]] = {i: [] for i in ids}
            if ids:
                label_rows = (
                    session.query(AnalysisFeedbackLabelModel)
                    .filter(AnalysisFeedbackLabelModel.analysis_feedback_id.in_(ids))
                    .order_by(
                        AnalysisFeedbackLabelModel.analysis_feedback_id.asc(),
                        AnalysisFeedbackLabelModel.orden.asc(),
                    )
                    .all()
                )
                for lr in label_rows:
                    labels_by_id.setdefault(lr.analysis_feedback_id, []).append(lr.to_dict())

        for r in rows:
            r["labels"] = labels_by_id.get(r.get("id"), [])
        return rows

    def get_feedback_joined_with_analysis(
        self,
        content_type: str | None = None,
        only_disagreements: bool = False,
    ) -> list[dict]:
        """Return feedback joined with the original analysis row.

        Each output dict contains the analysis_result fields plus the
        feedback fields, prefixed with ``original_`` for clarity. Used
        by the "Análisis corregidos" report.

        Args:
            content_type: Filter by ``"post"`` or ``"comment"``.
            only_disagreements: If True, keep only rows where the
                reviewer disagreed.

        Returns:
            List of joined dicts, ordered by ``updated_at`` desc.
        """
        with self.get_session() as session:
            query = session.query(AnalysisFeedbackModel, AnalysisResultModel).join(
                AnalysisResultModel,
                AnalysisResultModel.id == AnalysisFeedbackModel.analysis_result_id,
            )
            if content_type:
                query = query.filter(AnalysisFeedbackModel.content_type == content_type)
            if only_disagreements:
                query = query.filter(AnalysisFeedbackModel.agrees == "false")

            query = query.order_by(AnalysisFeedbackModel.updated_at.desc())

            results: list[dict] = []
            for fb, ar in query.all():
                joined = ar.to_dict()
                fb_dict = fb.to_dict()
                joined["feedback"] = fb_dict
                joined["original_categoria"] = ar.categoria
                joined["original_dimension"] = ar.dimension
                joined["original_justificacion"] = ar.justificacion
                joined["original_severidad"] = ar.severidad
                joined["corrected_categoria"] = fb.corrected_categoria
                joined["corrected_dimension"] = fb.corrected_dimension
                joined["corrected_justificacion"] = fb.corrected_justificacion
                joined["reason"] = fb.reason
                joined["agrees"] = fb.agrees
                results.append(joined)
            return results

    def get_original_text(self, content_type: str, content_id: str) -> str:
        """Return the original text for a post/comment (used by feedback form)."""
        with self.get_session() as session:
            if content_type == "post":
                row = session.query(PostModel).filter_by(id=content_id).first()
            elif content_type == "comment":
                row = session.query(CommentModel).filter_by(id=content_id).first()
            else:
                return ""
            return (row.text or "") if row else ""

    def mark_feedback_indexed(self, feedback_id: int, chromadb_id: str) -> bool:
        """Mark a feedback row as indexed in ChromaDB.

        Args:
            feedback_id: PK of the feedback row.
            chromadb_id: ID returned by ChromaDB ``add``.

        Returns:
            True on success, False if the row doesn't exist.
        """
        from datetime import datetime

        with self.get_session() as session:
            row = session.query(AnalysisFeedbackModel).filter_by(id=feedback_id).first()
            if not row:
                return False
            row.indexed_in_chromadb = "true"
            row.chromadb_id = chromadb_id
            row.chromadb_indexed_at = datetime.now()
            return True

    def unmark_feedback_indexed(self, feedback_id: int) -> bool:
        """Mark a feedback row as no-longer-indexed (ChromaDB entry removed).

        Args:
            feedback_id: PK of the feedback row.

        Returns:
            True on success.
        """
        with self.get_session() as session:
            row = session.query(AnalysisFeedbackModel).filter_by(id=feedback_id).first()
            if not row:
                return False
            row.indexed_in_chromadb = "false"
            row.chromadb_id = None
            row.chromadb_indexed_at = None
            return True

    # ----- Users (admin / reviewer accounts) -----

    @staticmethod
    def _hash_password(password: str) -> str:
        """Return the bcrypt hash of ``password`` using passlib."""
        from passlib.context import CryptContext

        return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)

    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        """Return True if ``password`` matches the bcrypt ``hashed`` value."""
        from passlib.context import CryptContext

        try:
            return CryptContext(schemes=["bcrypt"], deprecated="auto").verify(password, hashed)
        except (ValueError, TypeError):
            return False

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "reviewer",
        full_name: str | None = None,
    ) -> int:
        """Create a new user. Idempotent: returns the existing id on conflict.

        Args:
            username: Unique login (case-sensitive).
            password: Plaintext password — hashed with bcrypt before storage.
            role: ``"admin"`` or ``"reviewer"``. Defaults to ``"reviewer"``.
            full_name: Optional display name.

        Returns:
            PK of the (new or existing) user row.
        """
        from datetime import datetime

        normalized = str(username or "").strip()
        if not normalized:
            raise ValueError("username cannot be empty")
        if role not in {"admin", "reviewer"}:
            raise ValueError(f"role must be 'admin' or 'reviewer' — got {role!r}")

        with self.get_session() as session:
            existing = session.query(UserModel).filter_by(username=normalized).first()
            if existing:
                return existing.id
            row = UserModel(
                username=normalized,
                password_hash=self._hash_password(password),
                role=role,
                full_name=full_name,
                is_active="true",
                created_at=datetime.now(),
            )
            session.add(row)
            session.flush()
            return row.id

    def verify_credentials(self, username: str, password: str) -> dict | None:
        """Return the user dict if ``(username, password)`` is valid.

        Inactive users always fail even with the right password. Unknown
        usernames return ``None`` (never raise) so the UI can render a
        generic "invalid credentials" message.
        """
        from datetime import datetime

        normalized = str(username or "").strip()
        if not normalized or not password:
            return None
        with self.get_session() as session:
            row = session.query(UserModel).filter_by(username=normalized).first()
            if not row:
                return None
            if str(row.is_active).lower() != "true":
                return None
            if not self._verify_password(password, row.password_hash):
                return None
            row.last_login = datetime.now()
            return row.to_dict()

    def find_user_by_username(self, username: str) -> dict | None:
        """Return the user dict for ``username`` (without password hash)."""
        with self.get_session() as session:
            row = session.query(UserModel).filter_by(username=str(username or "").strip()).first()
            return row.to_dict() if row else None

    def find_user_by_id(self, user_id: int) -> dict | None:
        """Return the user dict by id (without password hash)."""
        with self.get_session() as session:
            row = session.query(UserModel).filter_by(id=user_id).first()
            return row.to_dict() if row else None

    def list_users(self) -> list[dict]:
        """Return all users, ordered by username ascending."""
        with self.get_session() as session:
            rows = session.query(UserModel).order_by(UserModel.username.asc()).all()
            return [r.to_dict() for r in rows]

    def set_user_active(self, user_id: int, active: bool) -> bool:
        """Activate / deactivate a user. Returns False if the id is unknown."""
        flag = "true" if active else "false"
        with self.get_session() as session:
            row = session.query(UserModel).filter_by(id=user_id).first()
            if not row:
                return False
            row.is_active = flag
            return True

    def set_user_role(self, user_id: int, role: str) -> bool:
        """Change a user's role. Returns False if the id is unknown."""
        if role not in {"admin", "reviewer"}:
            raise ValueError(f"role must be 'admin' or 'reviewer' — got {role!r}")
        with self.get_session() as session:
            row = session.query(UserModel).filter_by(id=user_id).first()
            if not row:
                return False
            row.role = role
            return True

    def set_user_password(self, user_id: int, password: str) -> bool:
        """Replace a user's password (hashed with bcrypt)."""
        with self.get_session() as session:
            row = session.query(UserModel).filter_by(id=user_id).first()
            if not row:
                return False
            row.password_hash = self._hash_password(password)
            return True

    # ----- Sessions (persistent login state) -----

    @staticmethod
    def _generate_session_id() -> str:
        """Return a fresh opaque session id."""
        import uuid

        return uuid.uuid4().hex

    def create_session(
        self,
        user_id: int,
        username: str,
        *,
        ttl_hours: int | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Create a persistent login session for ``user_id``.

        Args:
            user_id: FK to ``users.id``.
            username: Denormalized for fast lookup without a JOIN.
            ttl_hours: Time-to-live in hours. Defaults to
                :data:`SESSION_TTL_HOURS` (24).
            user_agent: Optional browser UA string for diagnostics.

        Returns:
            Session dict (with ``id``) — store the ``id`` in the
            browser-side cookie so the next request can look it up.
        """
        from datetime import datetime, timedelta

        ttl = ttl_hours if ttl_hours is not None else SESSION_TTL_HOURS
        now = datetime.now()
        expires = now + timedelta(hours=ttl)
        sid = self._generate_session_id()
        with self.get_session() as session:
            row = SessionModel(
                id=sid,
                user_id=int(user_id),
                username=username,
                created_at=now,
                expires_at=expires,
                last_seen_at=now,
                user_agent=user_agent,
            )
            session.add(row)
            session.flush()
        return {
            "id": sid,
            "user_id": int(user_id),
            "username": username,
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }

    def find_session(self, session_id: str) -> dict | None:
        """Return the session row, or ``None`` if missing / expired.

        Expired rows are NOT deleted here — use :meth:`purge_expired_sessions`
        for cleanup. They just stop being honored for auth.
        """
        if not session_id:
            return None
        with self.get_session() as session:
            row = session.query(SessionModel).filter_by(id=session_id).first()
            if not row:
                return None
            from datetime import datetime

            if row.expires_at and datetime.now() >= row.expires_at:
                return None
            return row.to_dict()

    def touch_session(self, session_id: str) -> bool:
        """Bump ``last_seen_at`` so idle sessions don't appear stale."""
        from datetime import datetime

        if not session_id:
            return False
        with self.get_session() as session:
            row = session.query(SessionModel).filter_by(id=session_id).first()
            if not row:
                return False
            row.last_seen_at = datetime.now()
            return True

    def delete_session(self, session_id: str) -> bool:
        """Remove a session (logout / explicit revocation)."""
        if not session_id:
            return False
        with self.get_session() as session:
            row = session.query(SessionModel).filter_by(id=session_id).first()
            if not row:
                return False
            session.delete(row)
            return True

    def purge_expired_sessions(self) -> int:
        """Delete every expired session row. Returns the number purged."""
        from datetime import datetime

        with self.get_session() as session:
            expired = (
                session.query(SessionModel).filter(SessionModel.expires_at <= datetime.now()).all()
            )
            count = len(expired)
            for row in expired:
                session.delete(row)
            return count


def _to_str_or_none(value: object) -> str | None:
    """Coerce a numeric/string to a string for storage, or None.

    Used to write the ``confianza`` / ``score_ajuste`` columns of
    ``analysis_labels`` / ``analysis_feedback_labels`` from arbitrary
    Python inputs (float, int, stringified number, ``None``).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        s = value.strip()
        return s if s else None


def _to_bool_str(value: object) -> str:
    """Coerce ``value`` to the ``"true"`` / ``"false"`` storage string.

    Important: do NOT use ``bool(value)`` directly because Python's truthiness
    treats the *string* ``"false"`` as truthy — this is the bug that flipped
    every false-positive flag to ``true`` across the data pipeline. Accept
    bools, ints/floats (0 → False), and string literals (``"true"`` /
    ``"false"`` / ``"yes"`` / ``"si"`` / ``"sí"`` / ``"1"``).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return "true" if value != 0 else "false"
    if isinstance(value, str):
        return "true" if value.strip().lower() in {"true", "1", "yes", "si", "sí"} else "false"
    return "false"
    return None


# Global database instance
_database: Database | None = None


def get_database(database_url: str = "sqlite:///data/tfm.db") -> Database:
    """Get or create database instance."""
    global _database
    if _database is None:
        _database = Database(database_url)
    return _database
