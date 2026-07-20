"""Tests for ``scripts/backfill_basura_digital.py``."""

from __future__ import annotations

import importlib.util
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "backfill_basura_digital.py"


def _load_script_module():
    """Load ``scripts/backfill_basura_digital.py`` without making it a package."""
    spec = importlib.util.spec_from_file_location("backfill_basura_digital", SCRIPT_PATH)
    assert spec and spec.loader, "Could not load backfill_basura_digital.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCHEMA_SQL = """
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    text TEXT
);

CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    text TEXT,
    post_id TEXT
);

CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT,
    content_id TEXT,
    tiene_violencia TEXT,
    categoria TEXT,
    exclusion_label TEXT,
    exclusion_codigo TEXT,
    exclusion_justificacion TEXT
);
"""


@pytest.fixture
def temp_db(tmp_path):
    """Fresh SQLite with the minimal schema needed by the backfill script."""
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_SQL)
    con.commit()
    con.close()
    yield db_path


def _insert(con, *, content_type, content_id, text, tiene_violencia="false", categoria=None):
    """Insert one row into posts/comments + analysis_results."""
    table = "posts" if content_type == "post" else "comments"
    con.execute(f"INSERT INTO {table} (id, text) VALUES (?, ?)", (content_id, text))
    con.execute(
        """
        INSERT INTO analysis_results
            (content_type, content_id, tiene_violencia, categoria, exclusion_label)
        VALUES (?, ?, ?, ?, NULL)
        """,
        (content_type, content_id, tiene_violencia, categoria),
    )
    con.commit()


def _run_cli(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(PROJECT_ROOT), "PATH": sys.prefix + "/bin"}
    import os

    env.update(os.environ)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--db-path", str(db_path), *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        check=False,
    )


class TestFindCandidates:
    def test_returns_only_vacio_comments(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="comment", content_id="c1", text="")
        _insert(
            con, content_type="comment", content_id="c2", text="Una opinión perfectamente limpia."
        )
        con.close()

        mod = _load_script_module()
        find_candidates = mod.find_candidates

        cands = find_candidates(str(temp_db), "all")
        assert len(cands) == 1
        assert cands[0].content_id == "c1"
        assert cands[0].result.codigo == "COND_1_VACIO"
        assert cands[0].analysis_id == 1

    def test_skips_rows_with_tiene_violencia_true(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="comment", content_id="c1", text="", tiene_violencia="true")
        con.close()

        mod = _load_script_module()
        find_candidates = mod.find_candidates

        assert find_candidates(str(temp_db), "all") == []

    def test_skips_rows_with_categoria_set(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(
            con,
            content_type="comment",
            content_id="c1",
            text="",
            categoria="VDG_VIOLENCIA_SIMBOLICA",
        )
        con.close()

        mod = _load_script_module()
        find_candidates = mod.find_candidates

        assert find_candidates(str(temp_db), "all") == []

    def test_handles_post_and_comment(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="post", content_id="p1", text="")
        _insert(con, content_type="comment", content_id="c1", text="")
        con.close()

        mod = _load_script_module()
        find_candidates = mod.find_candidates

        cands = find_candidates(str(temp_db), "all")
        assert {c.content_type for c in cands} == {"post", "comment"}

    def test_target_filters_table(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="post", content_id="p1", text="")
        _insert(con, content_type="comment", content_id="c1", text="")
        con.close()

        mod = _load_script_module()
        find_candidates = mod.find_candidates

        posts = find_candidates(str(temp_db), "post")
        comments = find_candidates(str(temp_db), "comment")
        assert {c.content_type for c in posts} == {"post"}
        assert {c.content_type for c in comments} == {"comment"}


class TestApplyUpdates:
    def test_apply_marks_candidates(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="comment", content_id="c1", text="")
        _insert(con, content_type="comment", content_id="c2", text="Texto real OK")
        con.close()

        mod = _load_script_module()
        find_candidates = mod.find_candidates
        apply_updates = mod.apply_updates

        cands = find_candidates(str(temp_db), "all")
        assert apply_updates(str(temp_db), cands) == 1

        con = sqlite3.connect(str(temp_db))
        row = con.execute(
            "SELECT exclusion_label, exclusion_codigo, exclusion_justificacion "
            "FROM analysis_results WHERE content_id='c1'"
        ).fetchone()
        assert row[0] == "CODIGO_99"
        assert row[1] == "COND_1_VACIO"
        assert "vacío" in row[2].lower() or "vacio" in row[2].lower()

        row2 = con.execute(
            "SELECT exclusion_label FROM analysis_results WHERE content_id='c2'"
        ).fetchone()
        assert row2[0] is None
        con.close()

    def test_apply_is_idempotent(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="comment", content_id="c1", text="")
        con.close()

        mod = _load_script_module()
        find_candidates = mod.find_candidates
        apply_updates = mod.apply_updates

        cands = find_candidates(str(temp_db), "all")
        assert apply_updates(str(temp_db), cands) == 1
        # Second pass: find_candidates skips already-labeled rows.
        cands2 = find_candidates(str(temp_db), "all")
        assert cands2 == []
        assert apply_updates(str(temp_db), cands2) == 0


class TestCli:
    def test_dry_run_does_not_modify_db(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="comment", content_id="c1", text="")
        con.close()

        result = _run_cli(temp_db)
        assert result.returncode == 0
        assert "(dry-run" in result.stdout
        assert "COND_1_VACIO" in result.stdout

        con = sqlite3.connect(str(temp_db))
        row = con.execute(
            "SELECT exclusion_label FROM analysis_results WHERE content_id='c1'"
        ).fetchone()
        assert row[0] is None
        con.close()

    def test_apply_updates_db(self, temp_db):
        con = sqlite3.connect(str(temp_db))
        _insert(con, content_type="comment", content_id="c1", text="")
        con.close()

        result = _run_cli(temp_db, "--apply")
        assert result.returncode == 0
        assert "Actualizadas: 1" in result.stdout

        con = sqlite3.connect(str(temp_db))
        row = con.execute(
            "SELECT exclusion_label, exclusion_codigo FROM analysis_results WHERE content_id='c1'"
        ).fetchone()
        assert row[0] == "CODIGO_99"
        assert row[1] == "COND_1_VACIO"
        con.close()
