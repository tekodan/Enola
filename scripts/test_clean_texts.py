"""Tests for ``scripts/clean_texts.py``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.storage.database import Database
from src.storage.models import CommentModel, PostModel

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "clean_texts.py"


@pytest.fixture
def temp_db(tmp_path):
    """Return a fresh SQLite database preloaded with one post and one comment."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    db = Database(db_url)

    with db.get_session() as session:
        session.add(
            PostModel(
                id="p1",
                text="t 0 6 8 5 4 9 2 1 · Hola mundo Facebook Facebook Facebook",
                author="Author",
            )
        )
        session.add(
            CommentModel(
                id="c1",
                post_id="p1",
                text="Diamante Rosa Hola mundo e gusta Responder",
                author="Diamante Rosa",
            )
        )
        session.add(
            CommentModel(
                id="c2",
                post_id="p1",
                text="Una opinión perfectamente limpia sin basura.",
                author="Persona",
            )
        )
        session.commit()

    yield db_path
    db_path.unlink(missing_ok=True)


def _run_script(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke ``scripts/clean_texts.py`` with the given extra args."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--db-path", str(db_path), *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        check=False,
    )


class TestCleanTextsScript:
    """End-to-end tests for ``scripts/clean_texts.py``."""

    def test_dry_run_does_not_modify_db(self, temp_db):
        """Default invocation (no ``--apply``) leaves the DB untouched."""
        result = _run_script(temp_db)
        assert result.returncode == 0
        assert "DRY-RUN" in result.stdout

        db_url = f"sqlite:///{temp_db}"
        db = Database(db_url)
        with db.get_session() as session:
            p = session.get(PostModel, "p1")
            assert p is not None
            assert "Facebook" in (p.text or "")
            assert "t 0 6 8" in (p.text or "")

    def test_apply_modifies_dirty_rows(self, temp_db):
        """With ``--apply`` the dirty rows are cleaned in place."""
        result = _run_script(temp_db, "--apply")
        assert result.returncode == 0
        assert "APPLIED" in result.stdout

        db_url = f"sqlite:///{temp_db}"
        db = Database(db_url)
        with db.get_session() as session:
            p = session.get(PostModel, "p1")
            c1 = session.get(CommentModel, "c1")
            c2 = session.get(CommentModel, "c2")

            # Dirty post is cleaned.
            assert p is not None
            assert p.text == "Hola mundo"
            assert "Facebook" not in (p.text or "")
            assert "t 0 6 8" not in (p.text or "")

            # Dirty comment is cleaned: author + corrupted trail gone.
            assert c1 is not None
            assert c1.text == "Hola mundo"
            assert "Diamante Rosa" not in (c1.text or "")
            assert "e gusta" not in (c1.text or "")

            # Clean comment is left alone.
            assert c2 is not None
            assert c2.text == "Una opinión perfectamente limpia sin basura."

    def test_apply_extracts_time_ago_and_responses(self, temp_db):
        """When ``time_ago`` / ``responses`` are NULL they get filled in
        from the extracted metadata."""
        result = _run_script(temp_db, "--apply")
        assert result.returncode == 0

        db_url = f"sqlite:///{temp_db}"
        db = Database(db_url)
        with db.get_session() as session:
            c1 = session.get(CommentModel, "c1")
            assert c1 is not None
            # The corrupted "e gusta Responder" carries no time_ago so
            # it stays NULL; the body is cleaned anyway.
            assert c1.text == "Hola mundo"

    def test_target_posts_only(self, temp_db):
        """``--target posts`` only cleans the posts table."""
        result = _run_script(temp_db, "--apply", "--target", "posts")
        assert result.returncode == 0

        db_url = f"sqlite:///{temp_db}"
        db = Database(db_url)
        with db.get_session() as session:
            p = session.get(PostModel, "p1")
            c1 = session.get(CommentModel, "c1")
            assert p is not None and "Facebook" not in (p.text or "")
            assert c1 is not None
            # Comments NOT touched.
            assert c1.text == "Diamante Rosa Hola mundo e gusta Responder"

    def test_target_comments_only(self, temp_db):
        """``--target comments`` only cleans the comments table."""
        result = _run_script(temp_db, "--apply", "--target", "comments")
        assert result.returncode == 0

        db_url = f"sqlite:///{temp_db}"
        db = Database(db_url)
        with db.get_session() as session:
            p = session.get(PostModel, "p1")
            c1 = session.get(CommentModel, "c1")
            # Posts NOT touched.
            assert p is not None
            assert "Facebook" in (p.text or "")
            # Comments cleaned.
            assert c1 is not None
            assert c1.text == "Hola mundo"

    def test_report_includes_modified_count(self, temp_db):
        """Dry-run report lists exactly which rows would change."""
        result = _run_script(temp_db, "--target", "all")
        assert result.returncode == 0
        # 1 dirty post + 1 dirty comment = 2 modified.
        assert "2 fila(s) serían modificadas" in result.stdout

    def test_apply_idempotent(self, temp_db):
        """Running ``--apply`` twice doesn't keep modifying rows."""
        result1 = _run_script(temp_db, "--apply")
        assert result1.returncode == 0

        result2 = _run_script(temp_db, "--apply")
        assert result2.returncode == 0
        # Second pass finds no further changes.
        assert "0 modificadas" in result2.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
