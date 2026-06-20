"""Unit tests for storage module."""

from datetime import datetime
from pathlib import Path

import pytest

from src.storage.database import Database
from src.storage.export import ExportManager


@pytest.fixture
def db_url(tmp_path):
    """Create temporary database URL."""
    db_path = tmp_path / "test.db"
    return f"sqlite:///{db_path}"


@pytest.fixture
def db(db_url):
    """Create database instance."""
    return Database(db_url)


@pytest.fixture
def sample_post():
    """Sample post data."""
    return {
        "id": "post-123",
        "text": "Este es un post de prueba",
        "author": "Pagina de Prueba",
        "date": datetime(2024, 1, 15, 10, 30),
        "likes": 100,
        "comments_count": 25,
        "shares": 10,
        "url": "https://facebook.com/post/123",
        "page_id": "page-456",
        "source": "facebook_page",
    }


@pytest.fixture
def sample_comment():
    """Sample comment data."""
    return {
        "id": "comment-789",
        "text": "Este es un comentario de prueba",
        "author": "Usuario de Prueba",
        "date": datetime(2024, 1, 15, 11, 0),
        "likes": 10,
        "post_id": "post-123",
        "parent_id": None,
        "url": "https://facebook.com/comment/789",
    }


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result data."""
    return {
        "content_type": "comment",
        "content_id": "comment-789",
        "post_id": "post-123",
        "comment_id": "comment-789",
        "tiene_violencia": "true",
        "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
        "dimension": "3.1",
        "codigo": None,
        "severidad": "media",
        "confianza": "0.8",
        "justificacion": "Contiene insultos y lenguaje denigrante",
        "evidencia": "Eres una zorra",
        "regla_disparada": "Cat 3 / Regla 1",
        "marcadores_detectados": '["zorra", "puta"]',
        "es_falso_positivo_probable": "false",
        "score_ajuste": "0.85",
    }


@pytest.fixture
def sample_seed_page():
    """Sample seed page data."""
    return {
        "url": "https://facebook.com/page-test",
        "name": "Pagina de Prueba",
        "page_id": "page-456",
        "is_seed": "true",
        "discovered_from": None,
        "violence_score": "0.8",
        "posts_count": 50,
    }


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_create_database(self, db_url):
        """Test database creation."""
        db = Database(db_url)
        assert db.engine is not None
        assert db.SessionLocal is not None

    def test_tables_created(self, db):
        """Test that all tables are created."""
        # Check tables exist via inspection
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        assert "posts" in tables
        assert "comments" in tables
        assert "analysis_results" in tables
        assert "seed_pages" in tables

    def test_migrate_legacy_schema(self, tmp_path):
        """Legacy DBs with old `tipo`/`confidence` columns must be migrated."""
        import sqlite3

        from sqlalchemy import inspect, text

        db_path = tmp_path / "legacy.db"
        url = f"sqlite:///{db_path}"

        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type VARCHAR NOT NULL,
                content_id VARCHAR NOT NULL,
                post_id VARCHAR,
                comment_id VARCHAR,
                tiene_violencia VARCHAR DEFAULT 'unknown',
                tipo VARCHAR DEFAULT 'ninguna',
                severidad VARCHAR DEFAULT 'ninguna',
                justificacion TEXT DEFAULT '',
                evidencia TEXT DEFAULT '',
                confidence VARCHAR,
                created_at DATETIME
            )
            """
        )
        conn.execute(
            "INSERT INTO analysis_results "
            "(content_type, content_id, tipo, severidad, confidence) "
            "VALUES ('post', 'p1', 'verbal', 'alta', '0.9')"
        )
        conn.commit()
        conn.close()

        db = Database(url)
        cols = {c["name"] for c in inspect(db.engine).get_columns("analysis_results")}

        # First migration: tipo/confianza split
        assert "categoria" in cols
        assert "dimension" in cols
        assert "codigo" in cols
        assert "confianza" in cols
        # Second migration: extended JSON output
        assert "regla_disparada" in cols
        assert "marcadores_detectados" in cols
        assert "es_falso_positivo_probable" in cols
        assert "score_ajuste" in cols

        with db.engine.connect() as s:
            row = s.execute(
                text("SELECT categoria, confianza FROM analysis_results WHERE content_id='p1'")
            ).first()
        assert row is not None
        assert row[0] == "verbal"
        assert row[1] == "0.9"

        # New fields default correctly
        with db.engine.connect() as s:
            row = s.execute(
                text(
                    "SELECT es_falso_positivo_probable, marcadores_detectados "
                    "FROM analysis_results WHERE content_id='p1'"
                )
            ).first()
        assert row[0] == "false"
        assert row[1] is None


class TestPostOperations:
    """Tests for post CRUD operations."""

    def test_save_post(self, db, sample_post):
        """Test saving a single post."""
        result = db.save_post(sample_post)
        assert result is True

    def test_save_post_update(self, db, sample_post):
        """Test updating an existing post."""
        db.save_post(sample_post)

        # Update with modified data
        sample_post["likes"] = 200
        result = db.save_post(sample_post)
        assert result is True

    def test_save_posts_batch(self, db, sample_post):
        """Test saving posts in batch."""
        posts = []
        for i in range(10):
            post = sample_post.copy()
            post["id"] = f"post-{i}"
            posts.append(post)

        saved = db.save_posts_batch(posts)
        assert saved == 10

    def test_get_posts(self, db, sample_post):
        """Test getting posts."""
        db.save_post(sample_post)

        posts = db.get_posts()
        assert len(posts) == 1
        assert posts[0]["id"] == "post-123"

    def test_get_posts_filtered(self, db, sample_post):
        """Test getting posts filtered by page_id."""
        db.save_post(sample_post)

        # Add another post with different page_id
        post2 = sample_post.copy()
        post2["id"] = "post-456"
        post2["page_id"] = "page-789"
        db.save_post(post2)

        posts = db.get_posts(page_id="page-456")
        assert len(posts) == 1
        assert posts[0]["page_id"] == "page-456"


class TestCommentOperations:
    """Tests for comment CRUD operations."""

    def test_save_comment(self, db, sample_comment):
        """Test saving a single comment."""
        result = db.save_comment(sample_comment)
        assert result is True

    def test_save_comment_update(self, db, sample_comment):
        """Test updating an existing comment."""
        db.save_comment(sample_comment)

        sample_comment["likes"] = 50
        result = db.save_comment(sample_comment)
        assert result is True

    def test_save_comments_batch(self, db, sample_comment):
        """Test saving comments in batch."""
        comments = []
        for i in range(10):
            comment = sample_comment.copy()
            comment["id"] = f"comment-{i}"
            comments.append(comment)

        saved = db.save_comments_batch(comments)
        assert saved == 10

    def test_get_comments(self, db, sample_comment, sample_post):
        """Test getting comments for a post."""
        db.save_post(sample_post)
        db.save_comment(sample_comment)

        comments = db.get_comments(post_id="post-123")
        assert len(comments) == 1
        assert comments[0]["id"] == "comment-789"


class TestAnalysisResultOperations:
    """Tests for analysis result operations."""

    def test_save_analysis_result(self, db, sample_analysis_result, sample_post, sample_comment):
        """Test saving analysis result."""
        # First save post and comment
        db.save_post(sample_post)
        db.save_comment(sample_comment)

        # Then save analysis result
        result_id = db.save_analysis_result(sample_analysis_result)
        assert result_id is not None
        assert result_id > 0

    def test_get_analysis_results(self, db, sample_analysis_result, sample_post, sample_comment):
        """Test getting analysis results."""
        db.save_post(sample_post)
        db.save_comment(sample_comment)
        db.save_analysis_result(sample_analysis_result)

        results = db.get_analysis_results()
        assert len(results) == 1
        assert results[0]["categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert results[0]["dimension"] == "3.1"
        assert results[0]["regla_disparada"] == "Cat 3 / Regla 1"
        assert results[0]["es_falso_positivo_probable"] == "false"


class TestSeedPageOperations:
    """Tests for seed page operations."""

    def test_save_seed_page(self, db, sample_seed_page):
        """Test saving seed page."""
        page_id = db.save_seed_page(sample_seed_page)
        assert page_id is not None
        assert page_id > 0

    def test_save_seed_page_update(self, db, sample_seed_page):
        """Test updating existing seed page."""
        db.save_seed_page(sample_seed_page)

        sample_seed_page["violence_score"] = "0.9"
        page_id = db.save_seed_page(sample_seed_page)
        assert page_id == 1  # Same page, same ID

    def test_get_seed_pages(self, db, sample_seed_page):
        """Test getting seed pages."""
        db.save_seed_page(sample_seed_page)

        pages = db.get_seed_pages()
        assert len(pages) == 1
        assert pages[0]["url"] == "https://facebook.com/page-test"

    def test_get_seed_pages_filtered(self, db, sample_seed_page):
        """Test getting seed pages filtered by is_seed."""
        db.save_seed_page(sample_seed_page)

        # Add non-seed page
        non_seed = sample_seed_page.copy()
        non_seed["url"] = "https://facebook.com/page-other"
        non_seed["is_seed"] = "false"
        db.save_seed_page(non_seed)

        seed_pages = db.get_seed_pages(is_seed=True)
        assert len(seed_pages) == 1
        assert seed_pages[0]["is_seed"] == "true"


class TestStats:
    """Tests for database statistics."""

    def test_get_stats_empty(self, db):
        """Test stats with empty database."""
        stats = db.get_stats()

        assert stats["posts_count"] == 0
        assert stats["comments_count"] == 0
        assert stats["analysis_results_count"] == 0
        assert stats["seed_pages_count"] == 0

    def test_get_stats_with_data(self, db, sample_post, sample_comment, sample_seed_page):
        """Test stats with data."""
        db.save_post(sample_post)
        db.save_comment(sample_comment)
        db.save_seed_page(sample_seed_page)

        stats = db.get_stats()

        assert stats["posts_count"] == 1
        assert stats["comments_count"] == 1
        assert stats["seed_pages_count"] == 1


class TestExportManager:
    """Tests for export manager."""

    def test_export_to_csv(self, db, sample_post, tmp_path):
        """Test CSV export."""
        db.save_post(sample_post)

        exporter = ExportManager(db, export_dir=str(tmp_path))
        path = exporter.export_to_csv()

        assert Path(path).exists()
        assert path.endswith(".csv")

    def test_export_to_json(self, db, sample_post, sample_comment, tmp_path):
        """Test JSON export."""
        db.save_post(sample_post)
        db.save_comment(sample_comment)

        exporter = ExportManager(db, export_dir=str(tmp_path))
        path = exporter.export_to_json()

        assert Path(path).exists()
        assert path.endswith(".json")

    def test_export_violence_report(
        self, db, sample_post, sample_comment, sample_analysis_result, tmp_path
    ):
        """Test violence report export."""
        db.save_post(sample_post)
        db.save_comment(sample_comment)
        db.save_analysis_result(sample_analysis_result)

        exporter = ExportManager(db, export_dir=str(tmp_path))
        path = exporter.export_violence_report()

        assert Path(path).exists()

    def test_get_export_files(self, db, tmp_path):
        """Test getting export files list."""
        exporter = ExportManager(db, export_dir=str(tmp_path))

        # Create some export files
        (tmp_path / "export1.json").touch()
        (tmp_path / "export2.csv").touch()

        files = exporter.get_export_files()
        assert len(files) == 2
