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
    for sub in ("scrape", "analyze", "serve", "status", "report", "all"):
        args = parser.parse_args([sub])
        assert hasattr(args, "func"), f"{sub} missing 'func' attribute"
        assert callable(args.func), f"{sub} 'func' is not callable"
