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
        """Test saving comments in batch (with in-batch dedup).

        10 comments with the same text + author + post collapse to
        one row — the survivor is chosen by ``pick_canonical``. The
        return value reports how many comments were actually saved,
        after dedup.
        """
        comments = []
        for i in range(10):
            comment = sample_comment.copy()
            comment["id"] = f"comment-{i}"
            comments.append(comment)

        saved = db.save_comments_batch(comments)
        assert saved == 1

    def test_save_comments_batch_dedup_keeps_distinct(self, db, sample_comment):
        """Distinct comments are all saved; only true duplicates collapse."""
        distinct_texts = [
            "Este es el primer comentario con un mensaje completamente diferente",
            "Acá hay otro texto que habla de otro tema distinto",
            "Lorem ipsum dolor sit amet consectetur adipiscing elit",
            "El usuario expresa una opinión política específica sobre el tema",
            "Una receta de cocina con ingredientes varios paso a paso",
        ]
        comments = []
        for i, text in enumerate(distinct_texts):
            comment = sample_comment.copy()
            comment["id"] = f"comment-distinct-{i}"
            comment["text"] = text
            comments.append(comment)

        # Plus 2 identical extras of the first one → 5 distinct + 2 dupes.
        for i in range(2):
            dup = comments[0].copy()
            dup["id"] = f"comment-dup-{i}"
            comments.append(dup)

        saved = db.save_comments_batch(comments)
        assert saved == 5

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


class TestFeedbackOperations:
    """Tests for human-feedback CRUD on analysis results."""

    def _seed_result(self, db, *, content_id: str = "p1") -> int:
        """Insert an analysis result and return its id."""
        return db.save_analysis_result(
            {
                "content_type": "post",
                "content_id": content_id,
                "tiene_violencia": "true",
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "baja",
                "justificacion": "AI orig",
                "evidencia": "ev orig",
            }
        )

    def test_save_feedback_insert(self, db):
        """First insert creates a new row."""
        rid = self._seed_result(db)
        fid = db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "the text",
                "agrees": "true",
            }
        )
        assert fid == 1
        row = db.get_feedback_for_analysis(rid)
        assert row is not None
        assert row["agrees"] == "true"
        assert row["corrected_categoria"] is None

    def test_save_feedback_upsert_by_analysis_id(self, db):
        """A second feedback for the same analysis replaces the first."""
        rid = self._seed_result(db)
        fid1 = db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
            }
        )
        fid2 = db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "true",
            }
        )
        assert fid2 == fid1
        rows = db.list_feedback()
        assert len(rows) == 1
        assert rows[0]["agrees"] == "true"

    def test_list_feedback_filters(self, db):
        """Filter by content_type / only_disagreements / only_pending_index."""
        r1 = self._seed_result(db, content_id="p1")
        r2 = self._seed_result(db, content_id="c1")

        # r1: comment-like feedback (upsert)
        db.save_feedback(
            {
                "analysis_result_id": r1,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
            }
        )
        db.save_feedback(
            {
                "analysis_result_id": r2,
                "content_type": "comment",
                "content_id": "c1",
                "text_snapshot": "t",
                "agrees": "true",
            }
        )

        assert len(db.list_feedback()) == 2
        assert len(db.list_feedback(content_type="post")) == 1
        assert len(db.list_feedback(only_disagreements=True)) == 1
        assert len(db.list_feedback(only_pending_index=True)) == 1

        # Mark r1 as indexed — pending list should now be empty
        db.mark_feedback_indexed(1, "chroma-1")
        assert len(db.list_feedback(only_pending_index=True)) == 0

    def test_mark_unmark_feedback_indexed(self, db):
        """Indexed flag toggles correctly."""
        rid = self._seed_result(db)
        fid = db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
            }
        )
        assert db.get_feedback_for_analysis(rid)["indexed_in_chromadb"] == "false"
        db.mark_feedback_indexed(fid, "doc_42")
        row = db.get_feedback_for_analysis(rid)
        assert row["indexed_in_chromadb"] == "true"
        assert row["chromadb_id"] == "doc_42"
        assert row["chromadb_indexed_at"] is not None
        db.unmark_feedback_indexed(fid)
        row = db.get_feedback_for_analysis(rid)
        assert row["indexed_in_chromadb"] == "false"
        assert row["chromadb_id"] is None

    def test_feedback_joined_with_analysis(self, db):
        """Join returns both original + corrected fields side by side."""
        rid = self._seed_result(db)
        db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "corrected_dimension": "3.1",
                "corrected_justificacion": "corr",
            }
        )
        joined = db.get_feedback_joined_with_analysis()
        assert len(joined) == 1
        assert joined[0]["original_categoria"] == "VDG_VIOLENCIA_SIMBOLICA"
        assert joined[0]["corrected_categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert joined[0]["corrected_dimension"] == "3.1"
        assert joined[0]["agrees"] == "false"

    def test_feedback_table_exists_for_legacy_db(self, tmp_path):
        """Database() must create analysis_feedback even on empty DB."""
        from sqlalchemy import inspect

        path = tmp_path / "legacy.db"
        db = Database(f"sqlite:///{path}")
        tables = inspect(db.engine).get_table_names()
        assert "analysis_feedback" in tables

    def test_feedback_updates_reindex_pending_flag(self, db):
        """Updating a feedback that's already indexed resets the flag."""
        rid = self._seed_result(db)
        fid = db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
            }
        )
        db.mark_feedback_indexed(fid, "chroma-1")
        # Upsert without specifying indexed_in_chromadb
        db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
            }
        )
        row = db.get_feedback_for_analysis(rid)
        assert row["indexed_in_chromadb"] == "false"
        assert row["chromadb_id"] is None

    def test_get_stats_includes_feedback(self, db):
        """get_stats() reports feedback counts."""
        rid = self._seed_result(db)
        db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
            }
        )
        stats = db.get_stats()
        assert stats["feedback_count"] == 1
        assert stats["feedback_disagreement_count"] == 1
        assert stats["feedback_agreement_count"] == 0
        assert stats["feedback_pending_index_count"] == 1


class TestMultiLabel:
    """Tests for the multi-label side tables and helpers."""

    def _seed_post(self, db):
        db.save_post(
            {
                "id": "p1",
                "text": "te voy a matar zorra",
                "author": "x",
                "date": datetime(2024, 1, 1),
                "likes": 0,
                "comments_count": 0,
                "shares": 0,
                "url": "u",
                "page_id": "pg",
                "source": "facebook_page",
            }
        )

    def test_save_analysis_with_clasificaciones_creates_label_rows(self, db):
        """Passing ``clasificaciones`` writes one row per label."""
        self._seed_post(db)
        rid = db.save_or_update_analysis_result(
            {
                "content_type": "post",
                "content_id": "p1",
                "post_id": "p1",
                "tiene_violencia": "true",
                "clasificaciones": [
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.1",
                        "severidad": "baja",
                        "justificacion": "estereotipo",
                        "evidencia": "a la cocina",
                        "marcadores_detectados": ["cocina"],
                    },
                    {
                        "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                        "dimension": "3.1",
                        "severidad": "alta",
                        "justificacion": "amenaza",
                        "evidencia": "matar",
                        "marcadores_detectados": ["matar"],
                    },
                ],
            }
        )
        labels = db.get_labels_for_analysis(rid)
        assert len(labels) == 2
        assert labels[0]["orden"] == 0
        assert labels[1]["orden"] == 1
        # Primary label mirrored into the flat row.
        all_rows = db.get_analysis_results()
        row = next(r for r in all_rows if r["id"] == rid)
        # Highest severity is HOSTILIDAD/alta → that's the primary.
        assert row["categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert row["severidad"] == "alta"
        assert row["justificacion"] == "amenaza"
        assert len(row["labels"]) == 2

    def test_save_analysis_without_clasificaciones_keeps_flat_row(self, db):
        """Backwards-compat: missing ``clasificaciones`` is allowed."""
        self._seed_post(db)
        rid = db.save_or_update_analysis_result(
            {
                "content_type": "post",
                "content_id": "p1",
                "post_id": "p1",
                "tiene_violencia": "true",
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.2",
                "severidad": "media",
                "justificacion": "zorra",
            }
        )
        labels = db.get_labels_for_analysis(rid)
        assert labels == []
        rows = db.get_analysis_results()
        row = next(r for r in rows if r["id"] == rid)
        assert row["labels"] == []
        assert row["categoria"] == "VDG_COSIFICACION_SLUTSHAMING"

    def test_save_analysis_replaces_labels_on_update(self, db):
        """A second save with different labels replaces the side rows."""
        self._seed_post(db)
        rid = db.save_or_update_analysis_result(
            {
                "content_type": "post",
                "content_id": "p1",
                "tiene_violencia": "true",
                "clasificaciones": [
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.1",
                        "severidad": "baja",
                        "justificacion": "old",
                    },
                    {
                        "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                        "dimension": "3.1",
                        "severidad": "alta",
                        "justificacion": "old2",
                    },
                ],
            }
        )
        assert len(db.get_labels_for_analysis(rid)) == 2

        db.save_or_update_analysis_result(
            {
                "content_type": "post",
                "content_id": "p1",
                "tiene_violencia": "true",
                "clasificaciones": [
                    {
                        "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                        "dimension": "2.1",
                        "severidad": "alta",
                        "justificacion": "new",
                    },
                ],
            }
        )
        labels = db.get_labels_for_analysis(rid)
        assert len(labels) == 1
        assert labels[0]["categoria"] == "VDG_COSIFICACION_SLUTSHAMING"

    def test_save_feedback_with_corrected_labels(self, db):
        """Feedback multi-label: list_feedback returns the corrected labels."""
        self._seed_post(db)
        rid = db.save_or_update_analysis_result(
            {
                "content_type": "post",
                "content_id": "p1",
                "tiene_violencia": "true",
                "clasificaciones": [
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.1",
                        "severidad": "baja",
                    },
                ],
            }
        )
        fb_id = db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_labels": [
                    {
                        "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                        "dimension": "2.1",
                        "severidad": "media",
                        "justificacion": "reclasificado",
                    },
                    {
                        "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                        "dimension": "3.1",
                        "severidad": "alta",
                        "justificacion": "agregado",
                    },
                ],
            }
        )
        fb_rows = db.list_feedback()
        fb = next(r for r in fb_rows if r["id"] == fb_id)
        assert len(fb["labels"]) == 2
        # Flat columns mirror the primary (HOSTILIDAD alta).
        assert fb["corrected_categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert fb["corrected_dimension"] == "3.1"
        assert fb["corrected_justificacion"] == "agregado"

    def test_save_feedback_agreement_drops_labels(self, db):
        """``agrees='true'`` ⇒ corrected labels are NOT written."""
        self._seed_post(db)
        rid = db.save_or_update_analysis_result(
            {
                "content_type": "post",
                "content_id": "p1",
                "tiene_violencia": "true",
                "clasificaciones": [
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.1",
                        "severidad": "baja",
                        "justificacion": "x",
                    },
                ],
            }
        )
        db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "true",
                "corrected_labels": [
                    {
                        "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                        "dimension": "2.1",
                        "severidad": "media",
                    },
                ],
            }
        )
        fb_rows = db.list_feedback()
        assert len(fb_rows[0]["labels"]) == 0

    def test_cascade_delete_labels_declared_in_schema(self, db):
        """The schema declares ON DELETE CASCADE on the FK to analysis_results.

        SQLite needs ``PRAGMA foreign_keys = ON`` per connection for the
        cascade to actually fire (off by default). This test verifies
        the schema *declares* the cascade; the runtime enforcement is a
        deployment-time concern handled at the connection level.
        """
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        fks = inspector.get_foreign_keys("analysis_labels")
        assert any(
            "analysis_results" in (fk.get("referred_table") or "")
            and "CASCADE" in (fk.get("options", {}).get("ondelete") or "").upper()
            for fk in fks
        )


class TestUsers:
    """Tests for the ``users`` table, bcrypt auth, and feedback linkage."""

    def test_users_table_created(self, db):
        from sqlalchemy import inspect

        tables = inspect(db.engine).get_table_names()
        assert "users" in tables

    def test_create_user_stores_hash_not_plain(self, db):
        uid = db.create_user("alice", "secret-pw", role="admin", full_name="Alice")
        u = db.find_user_by_username("alice")
        assert u is not None
        assert u["id"] == uid
        assert u["role"] == "admin"
        assert u["full_name"] == "Alice"
        assert u["is_active"] == "true"
        assert "password_hash" not in u

    def test_create_user_is_idempotent(self, db):
        a = db.create_user("bob", "pw-a")
        b = db.create_user("bob", "pw-b")
        assert a == b

    def test_verify_credentials_ok(self, db):
        db.create_user("carol", "pw-good")
        u = db.verify_credentials("carol", "pw-good")
        assert u is not None
        assert u["username"] == "carol"
        assert u["last_login"] is not None

    def test_verify_credentials_wrong_password(self, db):
        db.create_user("dan", "pw-good")
        assert db.verify_credentials("dan", "pw-bad") is None

    def test_verify_credentials_unknown_user(self, db):
        assert db.verify_credentials("nobody", "x") is None

    def test_inactive_user_blocks_login(self, db):
        uid = db.create_user("eve", "pw-good")
        db.set_user_active(uid, False)
        assert db.verify_credentials("eve", "pw-good") is None

    def test_set_user_role_validates(self, db):
        uid = db.create_user("frank", "pw")
        db.set_user_role(uid, "reviewer")
        assert db.find_user_by_id(uid)["role"] == "reviewer"
        with pytest.raises(ValueError):
            db.set_user_role(uid, "godmode")

    def test_set_user_password_rotates(self, db):
        uid = db.create_user("gina", "old-pw")
        assert db.verify_credentials("gina", "old-pw") is not None
        db.set_user_password(uid, "new-pw")
        assert db.verify_credentials("gina", "old-pw") is None
        assert db.verify_credentials("gina", "new-pw") is not None

    def test_list_users_ordered_by_username(self, db):
        db.create_user("zoe", "p")
        db.create_user("ana", "p")
        db.create_user("marco", "p")
        names = [u["username"] for u in db.list_users()]
        assert names == ["ana", "marco", "zoe"]

    def _seed_result(self, db):
        db.save_post(
            {
                "id": "p1",
                "text": "text",
                "author": "x",
                "date": datetime(2024, 1, 1),
                "likes": 0,
                "comments_count": 0,
                "shares": 0,
                "url": "u",
                "page_id": "pg",
                "source": "facebook_page",
            }
        )
        return db.save_or_update_analysis_result(
            {
                "content_type": "post",
                "content_id": "p1",
                "post_id": "p1",
                "tiene_violencia": "true",
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "severidad": "media",
            }
        )

    def test_feedback_reviewer_user_id_is_persisted(self, db):
        """``reviewer_user_id`` and ``reviewer_username`` are stored."""
        rid = self._seed_result(db)
        uid = db.create_user("hank", "pw", role="reviewer")
        db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "reviewer_user_id": uid,
                "reviewer_username": "hank",
            }
        )
        row = db.get_feedback_for_analysis(rid)
        assert row["reviewer_user_id"] == uid
        assert row["reviewer_username"] == "hank"

    def test_feedback_columns_migrated_on_legacy_db(self, tmp_path):
        """Existing ``analysis_feedback`` rows get the two new columns on upgrade."""
        import sqlite3

        from sqlalchemy import inspect

        db_path = tmp_path / "legacy.db"
        url = f"sqlite:///{db_path}"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE analysis_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_result_id INTEGER NOT NULL,
                content_type VARCHAR NOT NULL,
                content_id VARCHAR NOT NULL,
                text_snapshot TEXT NOT NULL,
                agrees VARCHAR NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

        db = Database(url)
        cols = {c["name"] for c in inspect(db.engine).get_columns("analysis_feedback")}
        assert "reviewer_user_id" in cols
        assert "reviewer_username" in cols

    def test_get_feedback_includes_all_labels(self, db):
        """Editing existing feedback must surface every stored label.

        Before this fix, ``get_feedback_for_analysis`` only returned
        the flat ``corrected_*`` columns, so a re-render of the
        multi-label form silently lost every label except the primary
        — the user's other corrections vanished on save.
        """
        rid = self._seed_result(db)
        db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "t",
                "agrees": "false",
                "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "corrected_dimension": "1.1",
                "corrected_justificacion": "primary",
                "corrected_labels": [
                    {
                        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                        "dimension": "1.1",
                        "severidad": "alta",
                        "justificacion": "stereotype",
                    },
                    {
                        "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                        "dimension": "2.2",
                        "severidad": "media",
                        "justificacion": "slut-shaming",
                    },
                    {
                        "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                        "dimension": "3.3",
                        "severidad": "alta",
                        "justificacion": "apología",
                    },
                ],
            }
        )
        row = db.get_feedback_for_analysis(rid)
        assert "labels" in row
        assert len(row["labels"]) == 3
        cats = [lbl["categoria"] for lbl in row["labels"]]
        assert cats == [
            "VDG_VIOLENCIA_SIMBOLICA",
            "VDG_COSIFICACION_SLUTSHAMING",
            "VDG_HOSTILIDAD_FEMINICIDIO",
        ]


class TestLegacyFeedbackSchema:
    """Tests that the schema migration works against existing DBs."""

    def test_feedback_columns_migrated_on_legacy_db(self, tmp_path):
        """Existing ``analysis_feedback`` rows get the two new columns on upgrade."""
        import sqlite3

        from sqlalchemy import inspect

        db_path = tmp_path / "legacy.db"
        url = f"sqlite:///{db_path}"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE analysis_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_result_id INTEGER NOT NULL,
                content_type VARCHAR NOT NULL,
                content_id VARCHAR NOT NULL,
                text_snapshot TEXT NOT NULL,
                agrees VARCHAR NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

        db = Database(url)
        cols = {c["name"] for c in inspect(db.engine).get_columns("analysis_feedback")}
        assert "reviewer_user_id" in cols
        assert "reviewer_username" in cols


class TestSessions:
    """Tests for the persistent login sessions table."""

    def test_create_session_returns_unique_id(self, db):
        uid = db.create_user("sam", "pw", role="reviewer")
        s1 = db.create_session(uid, "sam")
        s2 = db.create_session(uid, "sam")
        assert s1["id"] != s2["id"]
        assert s1["user_id"] == uid
        assert s1["username"] == "sam"
        assert s1["expires_at"] > s1["created_at"]

    def test_find_session_returns_existing(self, db):
        uid = db.create_user("nina", "pw", role="reviewer")
        s = db.create_session(uid, "nina")
        found = db.find_session(s["id"])
        assert found is not None
        assert found["user_id"] == uid

    def test_find_session_missing_returns_none(self, db):
        assert db.find_session("doesnotexist") is None
        assert db.find_session("") is None

    def test_find_session_expired_returns_none(self, db):
        from datetime import datetime, timedelta

        uid = db.create_user("eve", "pw", role="reviewer")
        s = db.create_session(uid, "eve", ttl_hours=0)
        # Manually push expires_at into the past so we don't have to wait.
        from src.storage.models import SessionModel

        with db.get_session() as session:
            row = session.query(SessionModel).filter_by(id=s["id"]).first()
            assert row is not None
            row.expires_at = datetime.now() - timedelta(seconds=1)
        assert db.find_session(s["id"]) is None

    def test_delete_session_removes_row(self, db):
        uid = db.create_user("oscar", "pw", role="reviewer")
        s = db.create_session(uid, "oscar")
        assert db.find_session(s["id"]) is not None
        assert db.delete_session(s["id"]) is True
        assert db.find_session(s["id"]) is None
        # Second delete is a no-op.
        assert db.delete_session(s["id"]) is False

    def test_touch_session_updates_last_seen(self, db):
        uid = db.create_user("pam", "pw", role="reviewer")
        s = db.create_session(uid, "pam")
        first_seen = s["created_at"]
        # Touch and confirm last_seen_at advances.
        import time as _time

        _time.sleep(0.05)
        assert db.touch_session(s["id"]) is True
        refreshed = db.find_session(s["id"])
        assert refreshed["last_seen_at"] >= first_seen

    def test_purge_expired_sessions(self, db):
        from datetime import datetime, timedelta

        uid = db.create_user("quinn", "pw", role="reviewer")
        fresh = db.create_session(uid, "quinn", ttl_hours=24)
        expired = db.create_session(uid, "quinn", ttl_hours=1)
        from src.storage.models import SessionModel

        with db.get_session() as session:
            row = session.query(SessionModel).filter_by(id=expired["id"]).first()
            row.expires_at = datetime.now() - timedelta(seconds=1)

        purged = db.purge_expired_sessions()
        assert purged == 1
        assert db.find_session(fresh["id"]) is not None
        assert db.find_session(expired["id"]) is None
