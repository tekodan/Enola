"""Integration tests for storage module."""

import json
from pathlib import Path

import pytest

from src.storage.database import Database
from src.storage.export import ExportManager


@pytest.fixture
def db_with_data(tmp_path):
    """Create database with sample data."""
    db_path = tmp_path / "test.db"
    db = Database(f"sqlite:///{db_path}")

    # Add posts
    for i in range(5):
        db.save_post(
            {
                "id": f"post-{i}",
                "text": f"Contenido del post {i}",
                "author": f"Autor {i}",
                "likes": 100 + i * 10,
                "comments_count": 20 + i * 5,
                "shares": 5 + i,
                "page_id": "page-test",
            }
        )

    # Add comments
    for i in range(10):
        db.save_comment(
            {
                "id": f"comment-{i}",
                "text": f"Comentario {i}",
                "author": f"Usuario {i}",
                "likes": i * 2,
                "post_id": "post-0",
            }
        )

    # Add analysis results
    for i in range(3):
        db.save_analysis_result(
            {
                "content_type": "comment",
                "content_id": f"comment-{i}",
                "post_id": "post-0",
                "comment_id": f"comment-{i}",
                "tiene_violencia": "true" if i < 2 else "false",
                "categoria": ("VDG_HOSTILIDAD_FEMINICIDIO" if i < 2 else "ninguna"),
                "dimension": "3.1" if i < 2 else None,
                "codigo": None,
                "severidad": "alta" if i == 0 else "media",
                "confianza": "0.85" if i < 2 else None,
                "justificacion": f"Justificación {i}",
                "regla_disparada": "Cat 3 / Regla 1" if i < 2 else None,
                "marcadores_detectados": '["matar"]' if i < 2 else None,
                "es_falso_positivo_probable": "false",
                "score_ajuste": "0.9" if i < 2 else None,
            }
        )

    # Add seed pages
    for i in range(2):
        db.save_seed_page(
            {
                "url": f"https://facebook.com/page-{i}",
                "name": f"Pagina {i}",
                "is_seed": "true" if i == 0 else "false",
                "violence_score": "0.8" if i == 0 else "0.3",
                "posts_count": 50 + i * 10,
            }
        )

    return db


class TestFullWorkflow:
    """Integration tests for full workflows."""

    def test_save_and_retrieve_posts(self, db_with_data):
        """Test saving and retrieving posts."""
        posts = db_with_data.get_posts()

        assert len(posts) == 5
        assert all(p["text"].startswith("Contenido del post") for p in posts)

    def test_save_and_retrieve_comments(self, db_with_data):
        """Test saving and retrieving comments."""
        comments = db_with_data.get_comments(post_id="post-0")

        assert len(comments) == 10
        assert all(c["post_id"] == "post-0" for c in comments)

    def test_analysis_workflow(self, db_with_data):
        """Test full analysis workflow."""
        # Get posts
        posts = db_with_data.get_posts()
        assert len(posts) == 5

        # Get comments for first post
        comments = db_with_data.get_comments(post_id="post-0")
        assert len(comments) == 10

        # Get analysis results
        results = db_with_data.get_analysis_results(content_type="comment")
        assert len(results) == 3

        # Check violence distribution
        violence_results = [r for r in results if r["tiene_violencia"] == "true"]
        assert len(violence_results) == 2

    def test_seed_pages_workflow(self, db_with_data):
        """Test seed pages workflow."""
        # Get all seed pages
        all_pages = db_with_data.get_seed_pages()
        assert len(all_pages) == 2

        # Get only seed pages
        seed_pages = db_with_data.get_seed_pages(is_seed=True)
        assert len(seed_pages) == 1
        assert seed_pages[0]["is_seed"] == "true"


class TestExportWorkflow:
    """Integration tests for export workflows."""

    def test_full_csv_export(self, db_with_data, tmp_path):
        """Test full CSV export with all data types."""
        exporter = ExportManager(db_with_data, export_dir=str(tmp_path))

        path = exporter.export_to_csv(
            include_posts=True,
            include_comments=True,
            include_analysis=True,
        )

        assert Path(path).exists()

        # Read and verify content
        content = Path(path).read_text(encoding="utf-8")

        assert "=== POSTS ===" in content
        assert "=== COMMENTS ===" in content
        assert "=== ANALYSIS RESULTS ===" in content

    def test_full_json_export(self, db_with_data, tmp_path):
        """Test full JSON export with all data types."""
        exporter = ExportManager(db_with_data, export_dir=str(tmp_path))

        path = exporter.export_to_json(
            include_posts=True,
            include_comments=True,
            include_analysis=True,
            include_stats=True,
        )

        assert Path(path).exists()

        # Read and verify JSON structure
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert "exported_at" in data
        assert "stats" in data
        assert "posts" in data
        assert "comments" in data
        assert "analysis_results" in data
        assert "seed_pages" in data

        assert len(data["posts"]) == 5
        assert len(data["analysis_results"]) == 3

    def test_violence_report(self, db_with_data, tmp_path):
        """Test violence report generation."""
        exporter = ExportManager(db_with_data, export_dir=str(tmp_path))

        path = exporter.export_violence_report()

        assert Path(path).exists()

        # Read and verify report
        with open(path, encoding="utf-8") as f:
            report = json.load(f)

        assert "generated_at" in report
        assert "summary" in report
        assert "total_violence_detected" in report["summary"]
        assert "by_type" in report["summary"]
        assert "by_severity" in report["summary"]

        assert report["summary"]["total_violence_detected"] == 2

    def test_export_files_list(self, db_with_data, tmp_path):
        """Test listing export files."""
        exporter = ExportManager(db_with_data, export_dir=str(tmp_path))

        # Create some export files
        exporter.export_to_csv()
        exporter.export_to_json()
        exporter.export_violence_report()

        files = exporter.get_export_files()

        assert len(files) == 3
        assert all(f["size"] > 0 for f in files)


class TestDataIntegrity:
    """Tests for data integrity."""

    def test_no_duplicate_posts(self, db_with_data):
        """Test that duplicate posts are not created."""
        # Try to save the same post again
        db_with_data.save_post(
            {
                "id": "post-0",
                "text": "Updated text",
                "author": "Updated Author",
            }
        )

        posts = db_with_data.get_posts()
        assert len(posts) == 5  # Still 5 posts

    def test_no_duplicate_comments(self, db_with_data):
        """Test that duplicate comments are not created."""
        db_with_data.save_comment(
            {
                "id": "comment-0",
                "text": "Updated comment",
                "author": "Updated User",
                "post_id": "post-0",
            }
        )

        comments = db_with_data.get_comments(post_id="post-0")
        assert len(comments) == 10  # Still 10 comments

    def test_referential_integrity(self, db_with_data):
        """Test referential integrity between tables."""
        # Comments should reference existing posts
        comments = db_with_data.get_comments(post_id="post-0")
        for comment in comments:
            assert comment["post_id"] == "post-0"

        # Analysis results should reference existing content
        results = db_with_data.get_analysis_results()
        for result in results:
            if result["content_type"] == "comment":
                assert result["comment_id"] is not None


class TestStatsAccuracy:
    """Tests for statistics accuracy."""

    def test_stats_accuracy(self, db_with_data):
        """Test that statistics are accurate."""
        stats = db_with_data.get_stats()

        assert stats["posts_count"] == 5
        assert stats["comments_count"] == 10
        assert stats["analysis_results_count"] == 3
        assert stats["seed_pages_count"] == 2

    def test_stats_update_on_save(self, db_with_data):
        """Test that stats update when new data is saved."""
        initial_stats = db_with_data.get_stats()

        db_with_data.save_post(
            {
                "id": "new-post",
                "text": "New post",
                "author": "New Author",
            }
        )

        updated_stats = db_with_data.get_stats()

        assert updated_stats["posts_count"] == initial_stats["posts_count"] + 1


class TestConcurrentOperations:
    """Tests for concurrent operations."""

    def test_multiple_saves_same_session(self, db_with_data):
        """Test multiple saves in sequence."""
        # Save multiple posts
        for i in range(10):
            db_with_data.save_post(
                {
                    "id": f"concurrent-post-{i}",
                    "text": f"Concurrent post {i}",
                    "author": "Concurrent Author",
                }
            )

        posts = db_with_data.get_posts()
        assert len(posts) == 15  # 5 original + 10 new

    def test_batch_save_integrity(self, db_with_data):
        """Test batch save maintains integrity."""
        posts = []
        for i in range(20):
            posts.append(
                {
                    "id": f"batch-post-{i}",
                    "text": f"Batch post {i}",
                    "author": "Batch Author",
                }
            )

        saved = db_with_data.save_posts_batch(posts)
        assert saved == 20

        all_posts = db_with_data.get_posts()
        assert len(all_posts) == 25  # 5 original + 20 batch
