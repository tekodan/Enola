"""CLI unificada — TFM Violencia de Género / Enola Investigadora Digital.

Subcomandos:
    scrape    Scrapea + preprocesa páginas seed y guarda en SQLite
    analyze   Clasifica con RAG (LLM + ChromaDB) los posts/comments pendientes
    serve     Lanza el dashboard de Streamlit
    status    Resumen de SQLite + ChromaDB
    report    Reporte textual de los análisis almacenados
    all       scrape + analyze en una sola corrida

Ejemplos::

    tfm scrape
    tfm analyze --reanalyze --posts-only
    tfm serve --port 8501
    tfm status --json
    tfm all --reanalyze
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _db_url() -> str:
    """Absolute sqlite URL for the project's data/tfm.db (CWD-independent)."""
    return f"sqlite:///{_project_root / 'data' / 'tfm.db'}"


def _db():
    """Get the database using the absolute project-root path."""
    from src.storage import get_database

    return get_database(_db_url())


def _vector_store():
    """Get the vector store using the absolute project-root path."""
    from src.config.settings import get_settings
    from src.knowledge_base.vector_store import get_vector_store

    settings = get_settings()
    persist_dir = str(_project_root / settings.knowledge_base.persist_directory)
    return get_vector_store(
        persist_directory=persist_dir,
        collection_name=settings.knowledge_base.collection_name,
    )


def _build_logger(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s:%(name)s:%(message)s",
    )


def cmd_scrape(args: argparse.Namespace) -> None:
    """Scrape + preprocesa páginas seed y guarda en SQLite (sin análisis)."""
    from src.config.settings import get_settings
    from src.pipeline.orchestrator import PipelineOrchestrator, load_seed_pages
    from src.scraper.facebook import FacebookScraper

    settings = get_settings()
    seeds = load_seed_pages(args.seeds)
    if not seeds:
        print("No se encontraron páginas seed.", file=sys.stderr)
        sys.exit(1)

    max_posts = args.max_posts or settings.scraper.max_posts_per_page
    max_comments = args.max_comments or settings.scraper.max_comments_per_post

    print(f"Scrapeando {len(seeds)} página(s) seed:")
    for s in seeds:
        print(f"  • {s}")
    print()
    print(
        f"Config: max_posts={max_posts}, max_comments={max_comments}, headless={not args.headful}"
    )
    print()

    scraper = FacebookScraper(
        max_posts=max_posts,
        max_comments=max_comments,
        headless=not args.headful,
    )
    orchestrator = PipelineOrchestrator(scraper=scraper)
    result = orchestrator.run_seed_pipeline(seeds)

    print()
    print("=" * 50)
    print("SCRAPE COMPLETO")
    print("=" * 50)
    print(f"  Páginas scrapeadas:  {result.stats.pages_scraped}")
    print(f"  Posts encontrados:   {result.stats.posts_found}")
    print(f"  Tiempo:              {result.stats.execution_time_seconds:.1f}s")
    if result.errors:
        print(f"  Errores:             {len(result.errors)}")
        for e in result.errors[:5]:
            print(f"    - {e}")
    print("=" * 50)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Clasifica con RAG todos los posts/comments no analidados."""
    from src.analyzer.batch_analyzer import BatchAnalyzer

    _build_logger(args.log_level)
    db = _db()
    analyzer = BatchAnalyzer(
        database=db,
        analyze_posts=True,
        analyze_comments=not args.posts_only,
        reanalyze_existing=args.reanalyze,
    )

    print("Iniciando análisis batch con RAG...")
    print(f"  Re-analizar existentes: {args.reanalyze}")
    print(f"  Incluir comments:       {not args.posts_only}")
    print()

    stats = analyzer.analyze_all()

    total_violence = stats.violence_detected_posts + stats.violence_detected_comments
    total = stats.posts_analyzed + stats.comments_analyzed
    pct = (total_violence / total * 100.0) if total else 0.0

    print()
    print("=" * 50)
    print("ANÁLISIS COMPLETO")
    print("=" * 50)
    print(f"  Posts analizados:       {stats.posts_analyzed}")
    print(f"  Comments analizados:    {stats.comments_analyzed}")
    print(f"  Violencia detectada:    {total_violence} ({pct:.1f}%)")
    print(f"  Errores:                {stats.errors}")
    print(f"  Tiempo:                 {stats.execution_time_seconds:.1f}s")
    print("=" * 50)


def cmd_serve(args: argparse.Namespace) -> None:
    """Lanza el dashboard de Streamlit en background o en foreground."""
    app_path = _project_root / "src" / "ui" / "landing.py"
    cmd = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(args.port),
    ]
    if args.no_browser:
        cmd.extend(["--server.headless", "true"])

    print(f"Lanzando: {' '.join(cmd)}")
    print(f"  -> http://localhost:{args.port}")
    print("  (Ctrl+C para detener)")
    print()

    if args.detach:
        proc = subprocess.Popen(cmd, cwd=str(_project_root), start_new_session=True)
        print(f"  PID: {proc.pid} (detach=True, no se espera)")
        print(f"  Para detenerlo: kill {proc.pid}")
        return

    try:
        subprocess.run(cmd, cwd=str(_project_root), check=False)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")


def cmd_status(args: argparse.Namespace) -> None:
    """Resumen rápido de SQLite + ChromaDB."""
    db = _db()
    vs = _vector_store()
    vs.create_collection()
    vs_stats = vs.get_collection_stats()
    db_stats = db.get_stats()

    if args.json:
        print(
            json.dumps(
                {"sqlite": db_stats, "chromadb": vs_stats},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print("=" * 50)
    print("ESTADO DEL SISTEMA")
    print("=" * 50)
    print("SQLite (data/tfm.db):")
    print(f"  Páginas:        {db_stats['pages_count']}")
    print(f"  Posts:          {db_stats['posts_count']}")
    print(f"  Comments:       {db_stats['comments_count']}")
    print(f"  Análisis:       {db_stats['analysis_results_count']}")
    print()
    print(f"ChromaDB ({vs_stats['name']}):")
    print(f"  Documentos:     {vs_stats['count']}")
    print("=" * 50)


def cmd_report(args: argparse.Namespace) -> None:
    """Reporte textual de los análisis almacenados."""
    from src.report.__main__ import cmd_report as _impl

    _db()
    _impl(args)


def cmd_all(args: argparse.Namespace) -> None:
    """Scrape + analyze en secuencia."""
    scrape_args = argparse.Namespace(
        seeds=args.seeds,
        max_posts=args.max_posts,
        max_comments=args.max_comments,
        headful=args.headful,
    )
    analyze_args = argparse.Namespace(
        reanalyze=args.reanalyze,
        posts_only=args.posts_only,
        log_level=args.log_level,
    )
    cmd_scrape(scrape_args)
    print()
    cmd_analyze(analyze_args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tfm",
        description=(
            "CLI unificada del TFM Violencia de Género. "
            "Detecta violencia de género en Facebook con RAG + Ollama + ChromaDB."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Nivel de log (DEBUG, INFO, WARNING, ERROR)",
    )
    sub = parser.add_subparsers(dest="command", metavar="SUBCOMMAND")

    s = sub.add_parser("scrape", help="Scrapea + preprocesa + guarda en SQLite")
    s.add_argument("--seeds", help="Path al seed_pages.txt (default: data/seed_pages.txt)")
    s.add_argument("--max-posts", type=int, default=0, help="0 = usar config.yaml")
    s.add_argument("--max-comments", type=int, default=0, help="0 = usar config.yaml")
    s.add_argument("--headful", action="store_true", help="Browser visible (default: headless)")
    s.set_defaults(func=cmd_scrape)

    s = sub.add_parser("analyze", help="Clasifica con RAG lo no analizado")
    s.add_argument("--reanalyze", action="store_true", help="Re-analiza contenido ya analizado")
    s.add_argument("--posts-only", action="store_true", help="Solo posts, no comments")
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("serve", help="Lanza el dashboard de Streamlit")
    s.add_argument("--port", type=int, default=8501, help="Puerto del servidor (default: 8501)")
    s.add_argument(
        "--no-browser",
        action="store_true",
        help="No abre el browser automáticamente",
    )
    s.add_argument(
        "--detach",
        action="store_true",
        help="Lanza en background (no espera Ctrl+C)",
    )
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("status", help="Resumen de SQLite + ChromaDB")
    s.add_argument("--json", action="store_true", help="Output en JSON")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("report", help="Reporte textual de los análisis")
    s.add_argument("--json", action="store_true", help="Output en JSON")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("all", help="scrape + analyze en una sola corrida")
    s.add_argument("--seeds", help="Path al seed_pages.txt")
    s.add_argument("--max-posts", type=int, default=0)
    s.add_argument("--max-comments", type=int, default=0)
    s.add_argument("--headful", action="store_true")
    s.add_argument("--reanalyze", action="store_true")
    s.add_argument("--posts-only", action="store_true")
    s.set_defaults(func=cmd_all)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
