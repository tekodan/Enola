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


def _build_dedup_plan(db, threshold: float) -> tuple[list[dict], int, int]:
    """Detect duplicate comment groups in the database and build a merge plan.

    Returns ``(plan, fk_total, dup_total)`` where ``plan`` is the list
    of merge records (see ``comment_dedup.plan_merge``), ``fk_total`` is
    the number of ``analysis_results.comment_id`` rows that would be
    re-pointed to the canonical, and ``dup_total`` is the number of
    duplicate comment rows that would be deleted.

    The function is read-only — it does not mutate the database.
    """
    from src.scraper.comment_dedup import find_duplicate_groups, plan_merge

    with db.get_session() as session:
        rows = session.execute(_select_all_comments()).fetchall()

    dict_rows = [dict(r._mapping) for r in rows]
    groups = find_duplicate_groups(dict_rows, threshold=threshold)
    plan = plan_merge(groups)

    fk_total = 0
    dup_ids: list[str] = []
    for entry in plan:
        dup_ids.extend(entry["duplicate_ids"])

    if dup_ids:
        with db.get_session() as session:
            from src.storage.models import AnalysisResultModel

            fk_total = (
                session.query(AnalysisResultModel)
                .filter(AnalysisResultModel.comment_id.in_(dup_ids))
                .count()
            )

    return plan, fk_total, len(dup_ids)


def _select_all_comments():
    """SQLAlchemy select for the comment rows needed by the dedup CLI."""
    from sqlalchemy import select

    from src.storage.models import CommentModel

    return select(
        CommentModel.id,
        CommentModel.post_id,
        CommentModel.author,
        CommentModel.text,
        CommentModel.likes,
        CommentModel.created_at,
    )


def _print_dedup_plan(plan: list[dict], fk_total: int, dup_total: int) -> None:
    """Human-friendly rendering of a merge plan."""
    print("=" * 60)
    print("DEDUP — Grupos de comentarios duplicados detectados")
    print("=" * 60)
    print(f"  Grupos:                {len(plan)}")
    print(f"  Comentarios a borrar:  {dup_total}")
    print(f"  FKs a re-puntero:      {fk_total} (analysis_results.comment_id)")
    print()
    if not plan:
        print("  (sin duplicados)")
        return

    for i, entry in enumerate(plan, start=1):
        print(f"  Grupo #{i}:")
        print(f"    KEEP    {entry['canonical_id']}")
        snippet = (entry["canonical_text"] or "").replace("\n", " ")[:100]
        print(
            f'            "{snippet}…"'
            if len(entry["canonical_text"] or "") > 100
            else f'            "{snippet}"'
        )
        for dup_id in entry["duplicate_ids"]:
            print(f"    DROP    {dup_id}")


def _apply_dedup_plan(db, plan: list[dict]) -> tuple[int, int]:
    """Execute a merge plan: re-point FKs, then delete duplicates.

    Returns ``(fk_updated, rows_deleted)``.
    """
    from src.storage.models import AnalysisResultModel, CommentModel

    dup_ids: list[str] = []
    canonical_map: dict[str, str] = {}
    for entry in plan:
        for dup_id in entry["duplicate_ids"]:
            dup_ids.append(dup_id)
            canonical_map[dup_id] = entry["canonical_id"]

    if not dup_ids:
        return 0, 0

    fk_updated = 0
    with db.get_session() as session:
        for dup_id, canonical_id in canonical_map.items():
            updated = (
                session.query(AnalysisResultModel)
                .filter(AnalysisResultModel.comment_id == dup_id)
                .update(
                    {AnalysisResultModel.comment_id: canonical_id},
                    synchronize_session=False,
                )
            )
            fk_updated += updated

        deleted = (
            session.query(CommentModel)
            .filter(CommentModel.id.in_(dup_ids))
            .delete(synchronize_session=False)
        )

    return fk_updated, int(deleted)


def _backup_db(db_path: Path) -> Path | None:
    """Copy the on-disk SQLite DB next to itself with a timestamp suffix.

    Returns the backup path, or ``None`` if the source DB doesn't exist
    (e.g. in-memory test DBs).
    """
    if not db_path.exists():
        return None
    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.bak-{ts}.db")
    import shutil

    shutil.copy2(db_path, backup)
    return backup


def cmd_dedup(args: argparse.Namespace) -> None:
    """Detecta y opcionalmente elimina comentarios duplicados.

    Sin ``--apply`` corre en modo dry-run: detecta los grupos,
    imprime el plan y sale sin tocar la base. Con ``--apply``:
    1. copia ``data/tfm.db`` a ``data/tfm.db.bak-YYYYMMDD_HHMMSS``
    2. re-punta ``analysis_results.comment_id`` al comentario canónico
    3. borra los duplicados
    """
    threshold = args.threshold

    db = _db()
    plan, fk_total, dup_total = _build_dedup_plan(db, threshold)

    if args.json:
        payload = {
            "threshold": threshold,
            "groups": len(plan),
            "duplicates_to_delete": dup_total,
            "fks_to_repoint": fk_total,
            "apply": bool(args.apply),
            "groups_detail": plan,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if not args.apply:
            return

    if not args.apply:
        if not args.json:
            _print_dedup_plan(plan, fk_total, dup_total)
            print()
            print("  Modo dry-run: no se modificó la base.")
            print("  Re-ejecutá con --apply para borrar los duplicados.")
            print("=" * 60)
        return

    # --apply path --------------------------------------------------------
    if not plan:
        print("Sin duplicados — nada que hacer.")
        return

    db_path = Path(_db_url().replace("sqlite:///", ""))
    backup = _backup_db(db_path)
    if backup:
        print(f"Backup creado: {backup.name}")

    if not args.json:
        _print_dedup_plan(plan, fk_total, dup_total)
        print()

    fk_updated, rows_deleted = _apply_dedup_plan(db, plan)
    print("=" * 60)
    print("DEDUP — Aplicado")
    print("=" * 60)
    print(f"  Comentarios borrados: {rows_deleted}")
    print(f"  FKs re-punteadas:     {fk_updated}")
    print("=" * 60)


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


# --- users subcommand ------------------------------------------------------


def _prompt_password(prompt: str = "Password: ") -> str:
    """Read a password from stdin (hides input when possible)."""
    import getpass

    try:
        return getpass.getpass(prompt)
    except Exception:
        return input(prompt)


def _random_password(length: int = 16) -> str:
    """Return a URL-safe random password."""
    import secrets

    return secrets.token_urlsafe(length)


def cmd_users_add(args: argparse.Namespace) -> None:
    """Create a new admin/reviewer. Idempotent on existing username."""
    db = _db()
    password = args.password or _prompt_password()
    if not password:
        print("Password vacío — abortando.", file=sys.stderr)
        sys.exit(1)
    try:
        uid = db.create_user(
            username=args.username,
            password=password,
            role=args.role,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    user = db.find_user_by_id(uid)
    if user and not db.verify_credentials(args.username, password):
        # Already existed with a different password — note it.
        print(
            f"  ℹ Usuario {user['username']!r} ya existía (rol: {user['role']}, "
            f"activo: {user['is_active']}). Password NO modificado."
        )
        return
    print(f"  ✅ Usuario creado: {user['username']!r} (id={user['id']}, rol={user['role']})")
    if args.password is None:
        print("  ℹ Password generado automáticamente:", password)


def cmd_users_list(args: argparse.Namespace) -> None:
    """List all users."""
    db = _db()
    users = db.list_users()
    if not users:
        print("(No hay usuarios cargados.)")
        return
    print(f"{'ID':>4}  {'Username':<22}  {'Rol':<10}  {'Activo':<6}  Nombre")
    print("-" * 70)
    for u in users:
        full = u.get("full_name") or "—"
        print(f"{u['id']:>4}  {u['username']:<22}  {u['role']:<10}  {u['is_active']:<6}  {full}")
    print(f"\nTotal: {len(users)} usuario(s).")


def cmd_users_set_active(args: argparse.Namespace) -> None:
    """Activate / deactivate a user by username."""
    db = _db()
    u = db.find_user_by_username(args.username)
    if not u:
        print(f"Usuario {args.username!r} no existe.", file=sys.stderr)
        sys.exit(1)
    ok = db.set_user_active(u["id"], args.active == "true")
    if not ok:
        print("No se pudo actualizar el usuario.", file=sys.stderr)
        sys.exit(1)
    print(
        f"  ✅ {args.username!r} → is_active={args.active} "
        f"('true' = habilitado, 'false' = bloqueado)"
    )


def cmd_users_set_role(args: argparse.Namespace) -> None:
    """Change a user's role."""
    db = _db()
    u = db.find_user_by_username(args.username)
    if not u:
        print(f"Usuario {args.username!r} no existe.", file=sys.stderr)
        sys.exit(1)
    try:
        ok = db.set_user_role(u["id"], args.role)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    if not ok:
        print("No se pudo actualizar el rol.", file=sys.stderr)
        sys.exit(1)
    print(f"  ✅ {args.username!r} → rol={args.role}")


def cmd_users_set_password(args: argparse.Namespace) -> None:
    """Rotate a user's password. Reads from stdin if not passed."""
    db = _db()
    u = db.find_user_by_username(args.username)
    if not u:
        print(f"Usuario {args.username!r} no existe.", file=sys.stderr)
        sys.exit(1)
    password = args.password or _prompt_password()
    if not password:
        print("Password vacío — abortando.", file=sys.stderr)
        sys.exit(1)
    db.set_user_password(u["id"], password)
    print(f"  ✅ Password de {args.username!r} actualizado.")


# --- categories subcommand handlers ---------------------------------------


def cmd_categories_list(args: argparse.Namespace) -> None:
    """List category display rows (defaults + overrides)."""
    db = _db()
    from src.storage.category_display import list_category_display, list_subdimension_display

    cat_rows = list_category_display(db)
    sub_rows = list_subdimension_display(db)

    overrides_only = getattr(args, "overrides", False)

    print("=" * 60)
    print("CATEGORÍAS")
    print("=" * 60)
    print(f"{'Código':<38} {'Título':<30} {'Fuente':<12}")
    print("-" * 80)
    for r in cat_rows:
        if overrides_only and r["source"] == "taxonomy":
            continue
        print(f"{r['code']:<38} {r['title']:<30} {r['source']:<12}")
    print(f"\nTotal: {len(cat_rows)} categoría(s).")

    print()
    print("=" * 60)
    print("SUBDIMENSIONES")
    print("=" * 60)
    print(f"{'Código':<10} {'Cat. Padre':<38} {'Descripción':<50} {'Fuente':<12}")
    print("-" * 110)
    for r in sub_rows:
        if overrides_only and r["source"] == "taxonomy":
            continue
        print(f"{r['code']:<10} {r['category_code']:<38} {r['description']:<50} {r['source']:<12}")
    print(f"\nTotal: {len(sub_rows)} subdimensión(es).")


def cmd_categories_edit(args: argparse.Namespace) -> None:
    """Edit a category display title."""
    from src.analyzer.category_mapping import Categoria

    if args.code not in {c.value for c in Categoria}:
        print(f"Error: {args.code!r} no es un código VDG_* válido.", file=sys.stderr)
        print(f"Válidos: {', '.join(c.value for c in Categoria if c is not Categoria.NINGUNA)}")
        sys.exit(1)

    db = _db()
    from src.storage.category_display import set_category_title

    ok = set_category_title(db, args.code, args.title)
    if not ok:
        print(f"Error al actualizar {args.code!r}.", file=sys.stderr)
        sys.exit(1)

    from src.ui.labels import refresh_cache

    refresh_cache()
    print(f"  ✅ {args.code!r} → título actualizado a {args.title!r}")
    print("  ℹ Caché recargada.")


def cmd_categories_edit_subdim(args: argparse.Namespace) -> None:
    """Edit a sub-dimension description."""
    from src.analyzer.category_mapping import SUBDIMENSIONES_ORDENADAS

    if args.code not in SUBDIMENSIONES_ORDENADAS:
        print(
            f"Error: {args.code!r} no es un código de subdimensión válido.",
            file=sys.stderr,
        )
        print(f"Válidos: {', '.join(SUBDIMENSIONES_ORDENADAS)}")
        sys.exit(1)

    db = _db()
    from src.storage.category_display import set_subdimension_description

    ok = set_subdimension_description(db, args.code, args.description)
    if not ok:
        print(f"Error al actualizar subdimensión {args.code!r}.", file=sys.stderr)
        sys.exit(1)

    from src.ui.labels import refresh_cache

    refresh_cache()
    print(f"  ✅ Subdimensión {args.code!r} → descripción actualizada.")
    print("  ℹ Caché recargada.")


def cmd_categories_refresh(args: argparse.Namespace) -> None:
    """Recargar la caché de display."""
    from src.ui.labels import refresh_cache

    refresh_cache()
    print("  ✅ Caché de display recargada desde SQLite + taxonomía.")


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

    s = sub.add_parser(
        "dedup",
        help="Detecta y opcionalmente elimina comentarios duplicados en SQLite",
    )
    s.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta la limpieza (default: dry-run)",
    )
    s.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Umbral de similitud difflib (0.0–1.0, default 0.95)",
    )
    s.add_argument(
        "--json",
        action="store_true",
        help="Imprime el plan en JSON en vez del formato humano",
    )
    s.set_defaults(func=cmd_dedup)

    s = sub.add_parser("all", help="scrape + analyze en una sola corrida")
    s.add_argument("--seeds", help="Path al seed_pages.txt")
    s.add_argument("--max-posts", type=int, default=0)
    s.add_argument("--max-comments", type=int, default=0)
    s.add_argument("--headful", action="store_true")
    s.add_argument("--reanalyze", action="store_true")
    s.add_argument("--posts-only", action="store_true")
    s.set_defaults(func=cmd_all)

    # --- users subcommand (admin/reviewer account management) -----
    users = sub.add_parser(
        "users", help="Gestión de usuarios (admin / reviewer) para el login NiceGUI"
    )
    users_sub = users.add_subparsers(dest="users_command", metavar="ACTION")

    u_add = users_sub.add_parser("add", help="Crea un usuario")
    u_add.add_argument("username", help="Username único (case-sensitive)")
    u_add.add_argument(
        "--password",
        help="Password en texto plano (si no, lo pide por stdin; si stdin "
        "tampoco está disponible, genera uno aleatorio)",
    )
    u_add.add_argument(
        "--role",
        choices=["admin", "reviewer"],
        default="reviewer",
        help="Rol del usuario (default: reviewer)",
    )
    u_add.set_defaults(func=cmd_users_add)

    u_list = users_sub.add_parser("list", help="Lista todos los usuarios")
    u_list.set_defaults(func=cmd_users_list)

    u_active = users_sub.add_parser("set-active", help="Activa/desactiva un usuario")
    u_active.add_argument("username")
    u_active.add_argument(
        "--active",
        choices=["true", "false"],
        required=True,
        help="true = habilitado, false = bloqueado",
    )
    u_active.set_defaults(func=cmd_users_set_active)

    u_role = users_sub.add_parser("set-role", help="Cambia el rol de un usuario")
    u_role.add_argument("username")
    u_role.add_argument("--role", choices=["admin", "reviewer"], required=True)
    u_role.set_defaults(func=cmd_users_set_role)

    u_pw = users_sub.add_parser("set-password", help="Rota el password de un usuario")
    u_pw.add_argument("username")
    u_pw.add_argument("--password", help="Si se omite, lo pide por stdin")
    u_pw.set_defaults(func=cmd_users_set_password)

    # --- categories subcommand (display overrides) --------------------
    categories = sub.add_parser(
        "categories", help="Gestión de títulos/descripciones de categorías y subdimensiones"
    )
    categories_sub = categories.add_subparsers(dest="categories_command", metavar="ACTION")

    cat_list = categories_sub.add_parser("list", help="Lista categorías con títulos y fuentes")
    cat_list.add_argument(
        "--overrides", action="store_true", help="Solo filas con override (source != taxonomy)"
    )
    cat_list.set_defaults(func=cmd_categories_list)

    cat_edit = categories_sub.add_parser("edit", help="Edita el título de una categoría")
    cat_edit.add_argument("code", help="Código VDG_* (ej: VDG_COSIFICACION_SLUTSHAMING)")
    cat_edit.add_argument("--title", required=True, help="Nuevo título visible")
    cat_edit.set_defaults(func=cmd_categories_edit)

    cat_edit_sub = categories_sub.add_parser(
        "edit-subdim", help="Edita la descripción de una subdimensión"
    )
    cat_edit_sub.add_argument("code", help="Código de subdimensión (ej: 2.1)")
    cat_edit_sub.add_argument("--description", required=True, help="Nueva descripción")
    cat_edit_sub.set_defaults(func=cmd_categories_edit_subdim)

    cat_refresh = categories_sub.add_parser(
        "refresh-cache", help="Recarga la caché de display sin reiniciar servidor"
    )
    cat_refresh.set_defaults(func=cmd_categories_refresh)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    if args.command == "users" and getattr(args, "users_command", None) is None:
        parser.parse_args(["users", "--help"])
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
