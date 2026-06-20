# src/report/__main__.py
"""CLI entry point for batch analysis and report generation.

Usage::

    python -m src.report analyze              # analyze unanalyzed content
    python -m src.report report               # print summary report
    python -m src.report analyze --reanalyze  # re-analyze everything
    python -m src.report analyze --posts-only # skip comments
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.analyzer.batch_analyzer import BatchAnalyzer  # noqa: E402
from src.storage import get_database  # noqa: E402


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run batch analysis on database content."""
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    db = get_database()

    analyzer = BatchAnalyzer(
        database=db,
        analyze_posts=True,
        analyze_comments=not args.posts_only,
        reanalyze_existing=args.reanalyze,
    )

    print("Iniciando análisis batch...")
    print(f"  Re-analizar existentes: {args.reanalyze}")
    print(f"  Incluir comments: {not args.posts_only}")
    print()

    stats = analyzer.analyze_all()

    print()
    print("=" * 50)
    print("RESULTADOS DEL ANÁLISIS")
    print("=" * 50)
    print(f"  Posts analizados:       {stats.posts_analyzed}")
    print(f"  Comments analizados:    {stats.comments_analyzed}")
    print(f"  Violencia en posts:     {stats.violence_detected_posts}")
    print(f"  Violencia en comments:  {stats.violence_detected_comments}")
    print(f"  Errores:                {stats.errors}")
    print(f"  Tiempo:                 {stats.execution_time_seconds:.1f}s")
    print("=" * 50)


def cmd_report(args: argparse.Namespace) -> None:
    """Print a summary report from the database."""
    db = get_database()

    stats = db.get_stats()
    analysis = db.get_analysis_results()
    pages = db.get_pages()

    print("=" * 50)
    print("INFORME DE LA BASE DE DATOS")
    print("=" * 50)
    print(f"  Páginas:              {stats['pages_count']}")
    print(f"  Posts:                {stats['posts_count']}")
    print(f"  Comments:             {stats['comments_count']}")
    print(f"  Análisis realizados:  {stats['analysis_results_count']}")
    print()

    if analysis:
        violence = [a for a in analysis if a.get("tiene_violencia") == "true"]
        posts_analysis = [a for a in analysis if a.get("content_type") == "post"]
        comments_analysis = [a for a in analysis if a.get("content_type") == "comment"]

        print(f"  Resultados con violencia: {len(violence)}")
        print(f"  Posts analizados:         {len(posts_analysis)}")
        print(f"  Comments analizados:      {len(comments_analysis)}")
        print()

        # Group by category
        from collections import Counter

        categorias = Counter(a.get("categoria") or "ninguna" for a in violence)
        print("  Violencia por categoría (taxonomía ChromaDB):")
        for categoria, count in categorias.most_common():
            print(f"    - {categoria}: {count}")
        print()

    if args.json:
        report = {
            "stats": stats,
            "pages": [p["id"] for p in pages],
            "analysis_results": analysis,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch analysis and reporting for TFM Violencia de Género"
    )
    parser.add_argument("--log-level", default="INFO", help="Log level (DEBUG, INFO, etc.)")
    subparsers = parser.add_subparsers(dest="command", help="Subcomando")

    # analyze
    ap = subparsers.add_parser("analyze", help="Analyze content in database")
    ap.add_argument("--reanalyze", action="store_true", help="Re-analyze already analyzed content")
    ap.add_argument("--posts-only", action="store_true", help="Only analyze posts, skip comments")
    ap.set_defaults(func=cmd_analyze)

    # report
    rp = subparsers.add_parser("report", help="Print summary report")
    rp.add_argument("--json", action="store_true", help="Output as JSON")
    rp.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
