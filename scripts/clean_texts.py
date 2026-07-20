"""Limpia el texto de posts y comments ya persistidos en SQLite.

Aplica ``strip_post_noise`` / ``strip_comment_noise`` (definidos en
``src/scraper/text_cleaner.py``) a cada fila de ``posts.text`` o
``comments.text`` y guarda los cambios.  Soporta dry-run y modo apply.

Uso:

    source .venv/bin/activate && python scripts/clean_texts.py --dry-run
    source .venv/bin/activate && python scripts/clean_texts.py --apply
    source .venv/bin/activate && python scripts/clean_texts.py --target comments --apply
    source .venv/bin/activate && python scripts/clean_texts.py --target posts --apply
    source .venv/bin/activate && python scripts/clean_texts.py --db-path data/otra.db --apply
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from src.config.settings import get_settings
from src.scraper.text_cleaner import strip_comment_noise, strip_post_noise
from src.storage.database import Database
from src.storage.models import CommentModel, PostModel

logger = logging.getLogger(__name__)

DEFAULT_DB_URL = "sqlite:///data/tfm.db"


@dataclass
class CleanStats:
    """Aggregate stats from one cleaning pass over a table."""

    target: str
    scanned: int = 0
    modified: int = 0
    unchanged: int = 0
    chars_before: int = 0
    chars_after: int = 0
    examples: list[tuple[str, str]] = field(default_factory=list)

    @property
    def chars_removed(self) -> int:
        return self.chars_before - self.chars_after

    def record(self, original: str, cleaned: str, max_examples: int = 5) -> None:
        self.scanned += 1
        self.chars_before += len(original)
        self.chars_after += len(cleaned)
        if original != cleaned:
            self.modified += 1
            if len(self.examples) < max_examples:
                self.examples.append((original, cleaned))
        else:
            self.unchanged += 1

    def merge(self, other: CleanStats) -> None:
        self.scanned += other.scanned
        self.modified += other.modified
        self.unchanged += other.unchanged
        self.chars_before += other.chars_before
        self.chars_after += other.chars_after
        self.examples.extend(other.examples[: 5 - len(self.examples)])

    def report(self) -> str:
        pct = (self.modified / self.scanned * 100.0) if self.scanned else 0.0
        lines = [
            f"[{self.target}] {self.scanned} filas escaneadas, "
            f"{self.modified} modificadas ({pct:.1f}%), {self.unchanged} sin cambio",
            f"  - chars: {self.chars_before} → {self.chars_after} (removidos {self.chars_removed})",
        ]
        if self.examples:
            lines.append("  - ejemplos (original → limpio):")
            for orig, clean in self.examples:
                lines.append(f"      {orig[:80]!r}")
                lines.append(f"        → {clean[:80]!r}")
        return "\n".join(lines)


def clean_posts(
    db: Database,
    *,
    dry_run: bool,
    batch_size: int = 500,
) -> CleanStats:
    """Clean ``posts.text`` rows in-place.

    Args:
        db: Database handle.
        dry_run: When True, no UPDATE statements are issued.
        batch_size: Commit every N rows (ignored in dry-run).

    Returns:
        ``CleanStats`` describing the pass.
    """
    stats = CleanStats(target="posts")

    with db.get_session() as session:
        posts = session.execute(select(PostModel)).scalars().all()
        pending = 0
        for post in posts:
            original = str(post.text or "")
            author = str(post.author or "")
            cleaned = strip_post_noise(original, author=author)
            stats.record(original, cleaned)
            if not dry_run and original != cleaned:
                post.text = cleaned  # type: ignore[assignment]
                pending += 1
                if pending >= batch_size:
                    session.commit()
                    pending = 0
        if not dry_run and pending:
            session.commit()

    logger.info(
        "posts: scanned=%d modified=%d (dry_run=%s)",
        stats.scanned,
        stats.modified,
        dry_run,
    )
    return stats


def clean_comments(
    db: Database,
    *,
    dry_run: bool,
    batch_size: int = 500,
) -> CleanStats:
    """Clean ``comments.text`` rows in-place.

    For each row, ``strip_comment_noise`` returns ``(body, time_ago,
    responses)``. The cleaned body goes to ``comments.text``; if the
    existing ``time_ago`` / ``responses`` columns are NULL/0, we fill
    them from the extraction so future runs don't re-strip the same
    metadata.

    Args:
        db: Database handle.
        dry_run: When True, no UPDATE statements are issued.
        batch_size: Commit every N rows (ignored in dry-run).

    Returns:
        ``CleanStats`` describing the pass.
    """
    stats = CleanStats(target="comments")

    with db.get_session() as session:
        comments = session.execute(select(CommentModel)).scalars().all()
        pending = 0
        for comment in comments:
            original = str(comment.text or "")
            author_val = comment.author or None  # type: ignore[assignment]
            author = str(author_val) if author_val is not None else None
            cleaned_body, time_ago, responses = strip_comment_noise(original, known_author=author)
            stats.record(original, cleaned_body)
            if not dry_run and (original != cleaned_body):
                comment.text = cleaned_body  # type: ignore[assignment]
                if time_ago and not comment.time_ago:  # type: ignore[has-member]
                    comment.time_ago = time_ago  # type: ignore[assignment]
                if responses and not comment.responses:  # type: ignore[has-member]
                    comment.responses = responses  # type: ignore[assignment]
                pending += 1
                if pending >= batch_size:
                    session.commit()
                    pending = 0
        if not dry_run and pending:
            session.commit()

    logger.info(
        "comments: scanned=%d modified=%d (dry_run=%s)",
        stats.scanned,
        stats.modified,
        dry_run,
    )
    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Limpia el texto de posts y comments persistidos en SQLite."
    )
    parser.add_argument(
        "--target",
        choices=("posts", "comments", "all"),
        default="all",
        help="Qué tablas limpiar (default: all)",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help=(
            "Ruta al archivo SQLite (ej: data/tfm.db). Si no se pasa, usa "
            "la URL de la configuración del proyecto o "
            "DEFAULT_DB_URL como fallback."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica los cambios. Sin este flag, solo muestra el reporte.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Commitea cada N filas modificadas (default: 500)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    db_url = DEFAULT_DB_URL
    if args.db_path:
        path = Path(args.db_path).expanduser().resolve()
        db_url = f"sqlite:///{path}"
    else:
        try:
            settings = get_settings()
            configured = getattr(settings.storage, "database_url", None)
            if configured:
                db_url = configured
        except Exception:
            logger.debug("Could not load settings; using default DB URL", exc_info=True)

    logger.info("Conectando a: %s", db_url)
    db = Database(db_url)

    dry_run = not args.apply
    if dry_run:
        print("[DRY-RUN] No se aplicarán cambios. Usá --apply para escribir en la DB.")

    stats: list[CleanStats] = []
    if args.target in ("posts", "all"):
        stats.append(clean_posts(db, dry_run=dry_run, batch_size=args.batch_size))
    if args.target in ("comments", "all"):
        stats.append(clean_comments(db, dry_run=dry_run, batch_size=args.batch_size))

    print()
    print("=" * 60)
    print("LIMPIEZA DE TEXTOS" + (" [DRY-RUN]" if dry_run else " [APPLIED]"))
    print("=" * 60)
    for s in stats:
        print(s.report())
    print("=" * 60)

    total_modified = sum(s.modified for s in stats)
    if dry_run and total_modified:
        print(
            f"\n{total_modified} fila(s) serían modificadas. "
            "Re-ejecutá con --apply para escribir los cambios."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
