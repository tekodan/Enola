"""Unit tests for the bulk-agree helper.

Uses an isolated SQLite database so we can exercise the save path
without polluting the project DB.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest

from src.storage import database as db_module

# Load bulk_agree module via spec so we can inject it into sys.modules
# under a proper module name (dataclass requires __module__ set).
_BULK_PATH = Path(__file__).parent / "components" / "bulk_agree.py"
_spec = importlib.util.spec_from_file_location(
    "src.ui.nicegui_app.components.bulk_agree", _BULK_PATH
)
assert _spec and _spec.loader
_bulk = importlib.util.module_from_spec(_spec)
sys.modules["src.ui.nicegui_app.components.bulk_agree"] = _bulk
_spec.loader.exec_module(_bulk)
BulkAgreeResult = _bulk.BulkAgreeResult
bulk_agree = _bulk.bulk_agree


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Bind a temp SQLite database."""
    url = f"sqlite:///{tmp_path / 'bulk-agree-test.db'}"
    db = db_module.Database(url)
    monkeypatch.setattr(db_module, "get_database", lambda: db)
    return db


def _seed_post(db, pid: str = "p1", text: str = "Hello world") -> None:
    db.save_post(
        {
            "id": pid,
            "text": text,
            "author": "test",
            "date": datetime(2024, 1, 1),
            "likes": 0,
            "comments_count": 0,
            "shares": 0,
            "url": "u",
            "page_id": "pg",
            "source": "facebook_page",
        }
    )


def _seed_analysis(db, content_id: str = "p1") -> int:
    return db.save_or_update_analysis_result(
        {
            "content_type": "post",
            "content_id": content_id,
            "post_id": content_id,
            "tiene_violencia": "true",
            "categoria": "VDG_VIOLENCIA_SIMBOLICA",
            "severidad": "media",
        }
    )


class TestBulkAgreeResult:
    def test_initial_state_is_all_zero(self):
        r = BulkAgreeResult()
        assert r.saved == 0
        assert r.skipped == 0
        assert r.failed == 0
        assert r.errors == []
        assert r.total == 0

    def test_as_toast_for_empty(self):
        assert BulkAgreeResult().as_toast() == "Nada para marcar — ninguna fila seleccionada."

    def test_as_toast_for_mixed(self):
        r = BulkAgreeResult(saved=3, skipped=1, failed=1)
        text = r.as_toast()
        assert "3" in text
        assert "1 omitida" in text
        assert "1 con error" in text


class TestBulkAgree:
    def test_empty_input_returns_zero(self, isolated_db):
        result = bulk_agree(rows=[], user={"id": 1, "username": "kim"})
        assert result.saved == 0
        assert result.total == 0

    def test_skips_rows_with_existing_feedback(self, isolated_db):
        db = isolated_db
        db.create_user("kim", "pw", role="reviewer")
        _seed_post(db, "p1")
        rid = _seed_analysis(db)
        # Pre-seed a feedback row.
        db.save_feedback(
            {
                "analysis_result_id": rid,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "Hello world",
                "agrees": "true",
                "reviewer": "ana",
                "reviewer_user_id": 1,
                "reviewer_username": "ana",
            }
        )
        result = bulk_agree(
            rows=[
                {
                    "id": rid,
                    "content_type": "post",
                    "content_id": "p1",
                    "feedback_row": {"id": 1, "agrees": "true"},
                }
            ],
            user={"id": 1, "username": "kim"},
            db=db,
        )
        assert result.saved == 0
        assert result.skipped == 1

    def test_marks_unsaved_row_as_agreed(self, isolated_db):
        db = isolated_db
        db.create_user("kim", "pw", role="reviewer")
        _seed_post(db, "p1")
        rid = _seed_analysis(db)
        u = db.find_user_by_username("kim")
        assert u is not None, "user not created"
        result = bulk_agree(
            rows=[{"id": rid, "content_type": "post", "content_id": "p1", "text_snapshot": "x"}],
            user={"id": u["id"], "username": "kim"},
            db=db,
        )
        assert result.failed == 0, f"errors: {result.errors}"
        assert result.saved == 1
        assert result.skipped == 0
        all_fb = db.list_feedback()
        matching = [f for f in all_fb if f["analysis_result_id"] == rid]
        assert matching, "no feedback row retrievable after bulk_agree"
        assert matching[0]["agrees"] == "true"
        assert matching[0]["reviewer_username"] == "kim"

    def test_invalid_row_counted_as_failure(self, isolated_db):
        db = isolated_db
        result = bulk_agree(
            rows=[{"foo": "bar"}],  # no "id"
            user={"id": 1, "username": "kim"},
            db=db,
        )
        assert result.failed == 1
        assert result.saved == 0

    def test_mixed_batch(self, isolated_db):
        db = isolated_db
        db.create_user("kim", "pw", role="reviewer")
        _seed_post(db, "p1")
        rid1 = _seed_analysis(db)
        _seed_post(db, "p2")
        rid2 = _seed_analysis(db, "p2")
        # Pre-seed feedback for rid1.
        db.save_feedback(
            {
                "analysis_result_id": rid1,
                "content_type": "post",
                "content_id": "p1",
                "text_snapshot": "x",
                "agrees": "true",
                "reviewer": "ana",
                "reviewer_user_id": 1,
                "reviewer_username": "ana",
            }
        )
        result = bulk_agree(
            rows=[
                {"id": rid1, "content_type": "post", "content_id": "p1", "feedback_row": {"id": 1}},
                {"id": rid2, "content_type": "post", "content_id": "p2", "text_snapshot": "y"},
            ],
            user={"id": 1, "username": "kim"},
            db=db,
        )
        assert result.saved == 1
        assert result.skipped == 1
