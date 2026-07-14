"""Unit tests for the unified CLI parser and helpers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from src.cli.__main__ import _build_parser, _db_url, _project_root, main


def test_build_parser_returns_parser():
    parser = _build_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "tfm"


def test_parser_has_all_six_subcommands():
    parser = _build_parser()
    help_text = parser.format_help()
    for sub in ("scrape", "analyze", "serve", "status", "report", "all"):
        assert sub in help_text, f"Missing subcommand in help: {sub}"


def test_scrape_subcommand_defaults():
    parser = _build_parser()
    args = parser.parse_args(["scrape"])
    assert args.command == "scrape"
    assert args.seeds is None
    assert args.max_posts == 0
    assert args.max_comments == 0
    assert args.headful is False


def test_scrape_subcommand_with_args():
    parser = _build_parser()
    args = parser.parse_args(
        [
            "scrape",
            "--seeds",
            "custom.txt",
            "--max-posts",
            "100",
            "--max-comments",
            "50",
            "--headful",
        ]
    )
    assert args.seeds == "custom.txt"
    assert args.max_posts == 100
    assert args.max_comments == 50
    assert args.headful is True


def test_analyze_subcommand_defaults():
    parser = _build_parser()
    args = parser.parse_args(["analyze"])
    assert args.command == "analyze"
    assert args.reanalyze is False
    assert args.posts_only is False


def test_analyze_subcommand_with_flags():
    parser = _build_parser()
    args = parser.parse_args(["analyze", "--reanalyze", "--posts-only"])
    assert args.reanalyze is True
    assert args.posts_only is True


def test_serve_subcommand_defaults():
    parser = _build_parser()
    args = parser.parse_args(["serve"])
    assert args.command == "serve"
    assert args.port == 8501
    assert args.no_browser is False
    assert args.detach is False


def test_serve_subcommand_with_flags():
    parser = _build_parser()
    args = parser.parse_args(["serve", "--port", "9000", "--detach"])
    assert args.port == 9000
    assert args.detach is True


def test_status_subcommand_defaults():
    parser = _build_parser()
    args = parser.parse_args(["status"])
    assert args.command == "status"
    assert args.json is False


def test_status_subcommand_json():
    parser = _build_parser()
    args = parser.parse_args(["status", "--json"])
    assert args.json is True


def test_report_subcommand():
    parser = _build_parser()
    args = parser.parse_args(["report", "--json"])
    assert args.command == "report"
    assert args.json is True


def test_all_subcommand_forwards_flags():
    parser = _build_parser()
    args = parser.parse_args(
        [
            "all",
            "--reanalyze",
            "--posts-only",
            "--seeds",
            "x.txt",
            "--headful",
        ]
    )
    assert args.command == "all"
    assert args.reanalyze is True
    assert args.posts_only is True
    assert args.seeds == "x.txt"
    assert args.headful is True


def test_log_level_global_flag():
    parser = _build_parser()
    args = parser.parse_args(["--log-level", "DEBUG", "status"])
    assert args.log_level == "DEBUG"


def test_no_subcommand_exits(monkeypatch):
    parser = _build_parser()
    namespace = parser.parse_args([])
    assert namespace.command is None
    assert hasattr(namespace, "func") is False or namespace.func is None


def test_db_url_is_absolute_and_uses_project_root():
    url = _db_url()
    assert url.startswith("sqlite:////")
    assert url.endswith("data/tfm.db")
    project_db = _project_root / "data" / "tfm.db"
    assert Path(url.replace("sqlite:///", "")) == project_db


def test_project_root_resolves_to_repo_root():
    expected = Path(__file__).resolve().parents[2]
    assert _project_root == expected


def test_main_prints_help_when_no_subcommand(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tfm"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "SUBCOMMAND" in captured.out


def test_subcommand_func_attribute_set():
    parser = _build_parser()
    for sub in ("scrape", "analyze", "serve", "status", "report", "all", "dedup"):
        args = parser.parse_args([sub])
        assert hasattr(args, "func"), f"{sub} missing 'func' attribute"
        assert callable(args.func), f"{sub} 'func' is not callable"


def test_dedup_subcommand_defaults():
    parser = _build_parser()
    args = parser.parse_args(["dedup"])
    assert args.command == "dedup"
    assert args.apply is False
    assert args.threshold == 0.95
    assert args.json is False


def test_dedup_subcommand_full_flags():
    parser = _build_parser()
    args = parser.parse_args(["dedup", "--apply", "--threshold", "0.85", "--json"])
    assert args.apply is True
    assert args.threshold == 0.85
    assert args.json is True


class TestDedupSubcommand:
    """End-to-end tests for ``tfm dedup`` against an isolated DB."""

    def _seed_db(self, tmp_path: Path):
        """Create a fresh DB with two duplicate comments + analysis rows.

        The DB lives at ``tmp_path/tfm.db`` so the backup step finds it.
        """
        from src.storage import database as db_module
        from src.storage import get_database
        from src.storage.models import (
            AnalysisResultModel,
            CommentModel,
            PageModel,
            PostModel,
        )

        url = f"sqlite:///{tmp_path / 'tfm.db'}"
        # Reset module-level singleton so each test gets a fresh DB.
        db_module._database = None
        db = get_database(url)

        with db.get_session() as session:
            session.add(PageModel(id="p1", url="https://facebook.com/page1", title="Test"))
            session.add(
                PostModel(
                    id="post1",
                    text="body",
                    author="Page",
                    page_id="p1",
                    comments_count=3,
                )
            )
            session.add(
                CommentModel(
                    id="c1",
                    text="Meza Jose Honestidad y respeto e gusta Responder",
                    author="Meza Jose",
                    post_id="post1",
                )
            )
            session.add(
                CommentModel(
                    id="c2",
                    text="Meza Jose Honestidad y respeto e gusta Responder",
                    author="Meza Jose",
                    post_id="post1",
                )
            )
            session.add(
                CommentModel(
                    id="c3",
                    text="Otro comentario completamente distinto",
                    author="Otro Autor",
                    post_id="post1",
                )
            )
            session.add(
                AnalysisResultModel(
                    content_type="comment",
                    content_id="c1",
                    comment_id="c1",
                    categoria="ninguna",
                )
            )
            session.add(
                AnalysisResultModel(
                    content_type="comment",
                    content_id="c2",
                    comment_id="c2",
                    categoria="ninguna",
                )
            )

        return db

    def test_dry_run_prints_plan_without_modifying(self, tmp_path: Path, monkeypatch, capsys):
        import src.cli.__main__ as cli_main

        db = self._seed_db(tmp_path)
        monkeypatch.setattr(cli_main, "_db", lambda: db)
        monkeypatch.setattr(cli_main, "_db_url", lambda: f"sqlite:///{tmp_path / 'tfm.db'}")

        cli_main.cmd_dedup(argparse.Namespace(threshold=0.95, apply=False, json=False))

        captured = capsys.readouterr().out
        assert "DEDUP" in captured
        assert "Grupos:" in captured
        assert "c2" in captured  # The dup id is named in the plan
        assert "dry-run" in captured

        # No rows deleted.
        with db.get_session() as session:
            from src.storage.models import CommentModel

            assert session.query(CommentModel).count() == 3

    def test_apply_deletes_duplicates_and_repoints_fks(self, tmp_path: Path, monkeypatch, capsys):
        import src.cli.__main__ as cli_main

        db = self._seed_db(tmp_path)
        monkeypatch.setattr(cli_main, "_db", lambda: db)
        monkeypatch.setattr(cli_main, "_db_url", lambda: f"sqlite:///{tmp_path / 'tfm.db'}")

        cli_main.cmd_dedup(argparse.Namespace(threshold=0.95, apply=True, json=False))

        captured = capsys.readouterr().out
        assert "Aplicado" in captured
        assert "Backup creado" in captured

        from src.storage.models import AnalysisResultModel, CommentModel

        with db.get_session() as session:
            assert session.query(CommentModel).count() == 2
            # Both analysis rows now point at the surviving comment.
            fks = {row.comment_id for row in session.query(AnalysisResultModel).all()}
            assert len(fks) == 1
            assert "c1" in fks  # c1 was the canonical (same length, lower id)

        # Backup file was created next to the original.
        backups = list(tmp_path.glob("tfm.db.bak-*.db"))
        assert len(backups) == 1
        assert backups[0].stat().st_size > 0

    def test_json_output_is_valid_json(self, tmp_path: Path, monkeypatch, capsys):
        import json

        import src.cli.__main__ as cli_main

        db = self._seed_db(tmp_path)
        monkeypatch.setattr(cli_main, "_db", lambda: db)
        monkeypatch.setattr(cli_main, "_db_url", lambda: f"sqlite:///{tmp_path / 'tfm.db'}")

        cli_main.cmd_dedup(argparse.Namespace(threshold=0.95, apply=False, json=True))

        captured = capsys.readouterr().out
        payload = json.loads(captured)
        assert payload["groups"] == 1
        assert payload["duplicates_to_delete"] == 1
        # Only the analysis row pointing to c2 (the duplicate) needs
        # to be re-pointed; the row pointing to c1 (the canonical)
        # stays as-is.
        assert payload["fks_to_repoint"] == 1
        assert payload["apply"] is False
        assert payload["groups_detail"][0]["duplicate_ids"] == ["c2"]
