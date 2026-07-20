"""Promote auditor feedback to canonical analysis results.

For each ``analysis_feedback`` row whose ``agrees="false"`` carries a
non-empty override (i.e. the human reviewer disagreed with the LLM
classification), this script:

1. Overwrites the matching ``analysis_results`` row's flat columns
   (categoria, dimension, severidad, justificacion, evidencia,
   regla_disparada, marcadores_detectados, score_ajuste,
   es_falso_positivo_probable, exclusion_label) so the corrected
   verdict becomes the new "as-if-the-model-had-said" record.

2. Replaces the matching ``analysis_labels`` rows with the reviewer's
   per-label list (``analysis_feedback_labels``).

3. Pushes the correction to ChromaDB's ``feedback_corrections``
   collection so the next batch retrieves it as a
   ``[VALIDADO POR HUMANO]`` few-shot.

4. Deletes the ``analysis_feedback`` row (the side table is dropped
   by FK CASCADE).

Run with the project venv:

    .venv/bin/python scripts/promote_feedback_to_analysis.py

Idempotent: ``analysis_feedback`` rows that have already been promoted
(a marker column ``analysis_results.applied_feedback_id`` is
incremented) are skipped. If the column does not exist yet, the
script adds it on first run.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from src.knowledge_base.feedback_store import get_feedback_store
from src.storage.database import get_database

DB_PATH = Path("data/tfm.db")
DB_URL = f"sqlite:///{DB_PATH}"


def _normalize_marcadores(raw) -> str:
    """Coerce marcadores_detectados to a JSON array string."""
    if not raw:
        return "[]"
    if isinstance(raw, list):
        return json.dumps([str(m) for m in raw if m], ensure_ascii=False)
    return json.dumps(
        [m.strip() for m in str(raw).split(",") if m.strip()],
        ensure_ascii=False,
    )


def _ensure_marker_column(conn: sqlite3.Connection) -> None:
    """Add ``applied_feedback_id`` column to ``analysis_results`` if missing."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(analysis_results)").fetchall()}
    if "applied_feedback_id" not in cols:
        conn.execute("ALTER TABLE analysis_results ADD COLUMN applied_feedback_id INTEGER")
        conn.commit()


def _primary_label(labels: list[dict]) -> dict | None:
    """Pick the primary label (highest severidad, deterministically)."""
    if not labels:
        return None
    rank = {"alta": 3, "media": 2, "baja": 1, "ninguna": 0}
    return max(
        labels,
        key=lambda lbl: (
            rank.get(str(lbl.get("severidad") or "ninguna").lower(), 0),
            -lbl.get("orden", 0),
        ),
    )


def _is_vdg_category(cat: str | None) -> bool:
    if not cat:
        return False
    cat = cat.strip()
    return cat.startswith("VDG_") and cat != "VDG_SALVAGUARDA_FALSO_POSITIVO"


def main() -> int:
    db = get_database(DB_URL)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_marker_column(conn)
        fb_rows = conn.execute(
            "SELECT id, analysis_result_id, content_type, content_id, "
            "text_snapshot, agrees, reason, corrected_categoria, "
            "corrected_dimension, corrected_justificacion, reviewer_username "
            "FROM analysis_feedback ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    print(f"[ok] {len(fb_rows)} feedback rows to consider")

    fs = get_feedback_store()
    fs.create_collection()
    initial_chroma = fs.get_count()
    print(f"[ok] ChromaDB feedback_corrections count = {initial_chroma}")

    promoted = 0
    skipped = 0
    failed = 0

    for fb in fb_rows:
        fb_id = int(fb["id"])
        ar_id = int(fb["analysis_result_id"])
        content_id = fb["content_id"]
        ctype = fb["content_type"]
        text = fb["text_snapshot"] or ""
        agrees = (fb["agrees"] or "").strip().lower()
        reviewer = fb["reviewer_username"] or "unknown"

        if agrees == "true":
            skipped += 1
            continue

        conn = sqlite3.connect(DB_PATH)
        try:
            already = conn.execute(
                "SELECT applied_feedback_id FROM analysis_results WHERE id = ?",
                (ar_id,),
            ).fetchone()
            if already and already[0]:
                skipped += 1
                continue

            labels = []
            for row in conn.execute(
                "SELECT orden, categoria, dimension, severidad, justificacion, "
                "evidencia, regla_disparada, marcadores_detectados, confianza, "
                "score_ajuste, es_falso_positivo_probable "
                "FROM analysis_feedback_labels WHERE analysis_feedback_id = ? "
                "ORDER BY orden",
                (fb_id,),
            ).fetchall():
                labels.append(
                    {
                        "orden": row[0],
                        "categoria": row[1],
                        "dimension": row[2],
                        "severidad": row[3] or "ninguna",
                        "justificacion": row[4] or "",
                        "evidencia": row[5] or "",
                        "regla_disparada": row[6],
                        "marcadores_detectados": row[7] or "[]",
                        "confianza": row[8],
                        "score_ajuste": row[9],
                        "es_falso_positivo_probable": row[10],
                    }
                )
            primary = _primary_label(labels)
        finally:
            conn.close()

        for lbl in labels:
            if isinstance(lbl["marcadores_detectados"], str):
                try:
                    lbl["marcadores_detectados"] = json.loads(lbl["marcadores_detectados"])
                except Exception:
                    lbl["marcadores_detectados"] = [
                        m.strip() for m in lbl["marcadores_detectados"].split(",") if m.strip()
                    ]

        corrected_labels_for_chroma = [
            {
                "categoria": lbl["categoria"],
                "dimension": lbl["dimension"],
                "severidad": lbl.get("severidad") or "ninguna",
                "justificacion": lbl.get("justificacion", ""),
                "evidencia": lbl.get("evidencia", ""),
                "regla_disparada": lbl.get("regla_disparada"),
                "marcadores_detectados": lbl.get("marcadores_detectados", []),
                "es_falso_positivo_probable": bool(
                    str(lbl.get("es_falso_positivo_probable") or "").lower() in {"true", "1", "yes"}
                ),
                "score_ajuste": lbl.get("score_ajuste"),
            }
            for lbl in labels
        ]

        try:
            chroma_id = fs.add_correction(
                feedback_id=fb_id,
                text=text,
                corrected_categoria=(fb["corrected_categoria"] or "ninguna"),
                corrected_dimension=fb["corrected_dimension"],
                corrected_justificacion=fb["corrected_justificacion"],
                original_categoria=None,
                content_type=ctype,
                content_id=content_id,
                reason=fb["reason"],
                corrected_labels=corrected_labels_for_chroma or None,
                user_id=None,
                added_by_username=reviewer,
                added_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        except Exception as exc:
            print(f"[chroma-fail] {content_id}: {exc}")
            chroma_id = None

        primary_cat = (primary or {}).get("categoria")
        primary_dim = (primary or {}).get("dimension")
        primary_sev = (primary or {}).get("severidad") or "ninguna"
        primary_justif = (primary or {}).get("justificacion", "")
        primary_evid = (primary or {}).get("evidencia", "")
        primary_regla = (primary or {}).get("regla_disparada")
        primary_marcadores = _normalize_marcadores((primary or {}).get("marcadores_detectados", []))
        primary_score = (primary or {}).get("score_ajuste")
        primary_fpp = bool(
            str((primary or {}).get("es_falso_positivo_probable") or "").lower()
            in {"true", "1", "yes"}
        )

        tiene_violencia_value = "true" if primary and _is_vdg_category(primary_cat) else "false"

        if primary_cat == "VIOLENCIA_COMUN":
            exclusion_label = "VIOLENCIA_COMUN"
            exclusion_codigo = "FEEDBACK_PROMOTION"
            exclusion_justif = primary_justif or (fb["corrected_justificacion"] or "")
        elif primary_cat == "ninguna" or primary_cat is None:
            exclusion_label = None
            exclusion_codigo = None
            exclusion_justif = None
        else:
            exclusion_label = None
            exclusion_codigo = None
            exclusion_justif = None

        flat_categoria = primary_cat if primary else (fb["corrected_categoria"] or "ninguna")
        flat_dimension = primary_dim if primary else fb["corrected_dimension"]
        flat_severidad = primary_sev if primary else "ninguna"
        flat_justificacion = primary_justif if primary else (fb["corrected_justificacion"] or "")
        flat_evidencia = primary_evid if primary else ""
        flat_regla = primary_regla if primary else None
        flat_marcadores = primary_marcadores if primary else "[]"
        flat_score = float(primary_score) if primary and primary_score is not None else None
        flat_fpp = "true" if primary_fpp else "false"

        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                UPDATE analysis_results SET
                    categoria = ?,
                    dimension = ?,
                    severidad = ?,
                    justificacion = ?,
                    evidencia = ?,
                    regla_disparada = ?,
                    marcadores_detectados = ?,
                    score_ajuste = ?,
                    es_falso_positivo_probable = ?,
                    tiene_violencia = ?,
                    exclusion_label = ?,
                    exclusion_codigo = ?,
                    exclusion_justificacion = ?,
                    applied_feedback_id = ?
                WHERE id = ?
                """,
                (
                    flat_categoria,
                    flat_dimension,
                    flat_severidad,
                    flat_justificacion,
                    flat_evidencia,
                    flat_regla,
                    flat_marcadores,
                    str(flat_score) if flat_score is not None else None,
                    flat_fpp,
                    tiene_violencia_value,
                    exclusion_label,
                    exclusion_codigo,
                    exclusion_justif,
                    fb_id,
                    ar_id,
                ),
            )

            conn.execute(
                "DELETE FROM analysis_labels WHERE analysis_result_id = ?",
                (ar_id,),
            )

            for orden, lbl in enumerate(labels):
                cat_l = lbl.get("categoria") or "ninguna"
                dim_l = lbl.get("dimension")
                sev_l = lbl.get("severidad") or "ninguna"
                just_l = lbl.get("justificacion") or ""
                evid_l = lbl.get("evidencia") or ""
                regla_l = lbl.get("regla_disparada")
                marc_l = _normalize_marcadores(lbl.get("marcadores_detectados", []))
                fpp_l = bool(
                    str(lbl.get("es_falso_positivo_probable") or "").lower() in {"true", "1", "yes"}
                )
                sc_l = lbl.get("score_ajuste")
                conf_l = lbl.get("confianza")
                conn.execute(
                    """
                    INSERT INTO analysis_labels (
                        analysis_result_id, orden, categoria, dimension,
                        severidad, justificacion, evidencia, regla_disparada,
                        marcadores_detectados, score_ajuste, es_falso_positivo_probable,
                        confianza, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ar_id,
                        orden,
                        cat_l,
                        dim_l,
                        sev_l,
                        just_l,
                        evid_l,
                        regla_l,
                        marc_l,
                        str(sc_l) if sc_l is not None else None,
                        "true" if fpp_l else "false",
                        str(conf_l) if conf_l is not None else None,
                        datetime.now().isoformat(timespec="seconds"),
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )

            conn.execute("DELETE FROM analysis_feedback WHERE id = ?", (fb_id,))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f"[db-fail] {content_id}: {exc}")
            failed += 1
            continue
        finally:
            conn.close()

        promoted += 1
        print(
            f"[ok] {content_id:36s}  ar={ar_id:>3}  fb={fb_id:>3}  "
            f"-> {flat_categoria}/{flat_dimension}/{flat_severidad}  "
            f"chroma_id={chroma_id}"
        )

    print(
        f"\nDone. promoted={promoted} skipped={skipped} failed={failed}  "
        f"chroma_count={fs.get_count()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
