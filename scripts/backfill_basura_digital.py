"""Backfill de CODIGO_99 (basura digital) en ``analysis_results``.

Recorre ``comments`` y ``posts``, aplica el filtro algorítmico
:func:`src.analyzer.exclusion_filter.detectar_basura_digital` y
actualiza las columnas ``exclusion_label``, ``exclusion_codigo`` y
``exclusion_justificacion`` de ``analysis_results``. No requiere
Ollama — sólo el filtro (Regla N6 del pre-filtro de exclusión).

Por defecto corre en modo ``--dry-run``. Usar ``--apply`` para
escribir cambios a la base.

Uso:

    source .venv/bin/activate
    python scripts/backfill_basura_digital.py --dry-run
    python scripts/backfill_basura_digital.py --apply
    python scripts/backfill_basura_digital.py --db-path data/otra.db --target comments --apply
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyzer.exclusion_filter import (  # noqa: E402
    EXCLUSION_BASURA_DIGITAL,
    ExclusionResult,
    detectar_basura_digital,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/tfm.db"

_TARGETS: dict[str, tuple[str, str]] = {
    "comment": ("comments", "comment"),
    "post": ("posts", "post"),
}


@dataclass(frozen=True)
class Candidate:
    """Fila candidata a ser marcada como CODIGO_99."""

    analysis_id: int
    content_type: str
    content_id: str
    text: str
    result: ExclusionResult


def find_candidates(db_path: str, target: str) -> list[Candidate]:
    """Devuelve las filas que el filtro marca como ``CODIGO_99``.

    Considera toda fila sin ``exclusion_label`` previo (incluyendo
    las que ya tienen una ``categoria`` asignada por el LLM) — el
    filtro algorítmico es la autoridad sobre basura digital: si
    el texto está vacío, es ``GIPHY`` o matchea alguno de los
    patrones de ``COND_5``, gana el filtro por sobre la
    clasificación previa.

    La única restricción dura es no pisar filas con
    ``exclusion_label`` ya establecido (otro proceso pudo haber
    etiquetado la fila como ``VIOLENCIA_COMUN`` u otro).
    """
    targets = _TARGETS.items() if target == "all" else [(target, _TARGETS[target])]
    con = sqlite3.connect(db_path)
    candidates: list[Candidate] = []
    for content_type, (table, _) in targets:
        sql = f"""
            SELECT a.id, c.id, c.text
            FROM {table} c
            JOIN analysis_results a
              ON a.content_id = c.id AND a.content_type = ?
            WHERE a.exclusion_label IS NULL
        """
        for analysis_id, content_id, text in con.execute(sql, (content_type,)):
            result = detectar_basura_digital(text or "")
            if result.etiqueta == EXCLUSION_BASURA_DIGITAL:
                candidates.append(
                    Candidate(
                        analysis_id=int(analysis_id),
                        content_type=content_type,
                        content_id=str(content_id),
                        text=text or "",
                        result=result,
                    )
                )
    con.close()
    return candidates


def apply_updates(db_path: str, candidates: list[Candidate]) -> int:
    """Escribe ``CODIGO_99`` en ``analysis_results`` para cada candidata.

    Devuelve la cantidad de filas efectivamente actualizadas (la
    cláusula ``AND exclusion_label IS NULL`` del UPDATE previene
    pisar filas modificadas por otro proceso entre find y apply).
    """
    if not candidates:
        return 0
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        total = 0
        for c in candidates:
            cur.execute(
                """
                UPDATE analysis_results
                SET exclusion_label = ?,
                    exclusion_codigo = ?,
                    exclusion_justificacion = ?
                WHERE id = ?
                  AND exclusion_label IS NULL
                """,
                (
                    EXCLUSION_BASURA_DIGITAL,
                    c.result.codigo,
                    c.result.justificacion,
                    c.analysis_id,
                ),
            )
            total += cur.rowcount
        con.commit()
        return total
    finally:
        con.close()


def print_table(candidates: list[Candidate]) -> None:
    """Imprime una tabla resumen del dry-run."""
    if not candidates:
        print("Sin candidatas.")
        return
    header = f"{'analysis_id':>11}  {'type':<8}  {'content_id':<18}  {'codigo':<24}  texto"
    print(header)
    print("-" * len(header))
    for c in candidates:
        preview = (c.text[:50] + "…") if len(c.text) > 50 else c.text
        preview = preview.replace("\n", " ").replace("\r", " ")
        print(
            f"{c.analysis_id:>11}  {c.content_type:<8}  {c.content_id:<18}  "
            f"{c.result.codigo or '-':<24}  {preview!r}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill de CODIGO_99 (basura digital) en analysis_results."
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Ruta al archivo SQLite")
    parser.add_argument(
        "--target",
        choices=["all", "post", "comment"],
        default="all",
        help="Tabla a procesar (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=True,
        help="(default) Solo muestra candidatas, no escribe.",
    )
    parser.add_argument(
        "--apply",
        dest="dry_run",
        action="store_false",
        help="Escribe los cambios en analysis_results.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Logging a nivel DEBUG.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    candidates = find_candidates(args.db_path, args.target)
    print(f"DB: {args.db_path}")
    print(f"Target: {args.target}")
    print(f"Candidatas CODIGO_99: {len(candidates)}\n")
    print_table(candidates)

    if args.dry_run:
        print("\n(dry-run — usar --apply para escribir)")
        return 0

    updated = apply_updates(args.db_path, candidates)
    skipped = len(candidates) - updated
    print(f"\nActualizadas: {updated}")
    if skipped:
        print(f"Omitidas (carrera u otra modificación concurrente): {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
