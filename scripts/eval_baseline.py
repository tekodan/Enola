"""Baseline evaluation: compara el estado actual de la DB contra el ground truth.

Lee:
- data/ground_truth_audit.json (ground truth curado de docs/auditoria-categorizaciones-2026-07-13.md
  + docs/informe-revalidacion-2026-07-14.md)
- data/tfm.db (estado actual de analysis_results + analysis_labels)

Calcula:
- Distribucion de n_labels en items con tiene_violencia=true (1 / 2 / 3 / 4+)
- Distribucion de n_labels esperados vs actuales
- Recall / precision / F1 por sub-dimension
- Exact match (sets iguales) por item
- Jaccard promedio
- Conteo de falsos positivos / falsos negativos
- Cobertura del ground truth sobre la DB

Uso:
    .venv/bin/python scripts/eval_baseline.py
    .venv/bin/python scripts/eval_baseline.py --output data/baseline_pre_fix.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GT = REPO_ROOT / "data" / "ground_truth_audit.json"
DEFAULT_DB = REPO_ROOT / "data" / "tfm.db"
DEFAULT_OUT = REPO_ROOT / "data" / "baseline_pre_fix.json"

CAT_PREFIX = "VDG_"


def _cat_code(orden: int) -> str:
    """Traduce el orden de la categoria (1..6) a su codigo VDG_*."""
    mapping = {
        1: "VDG_VIOLENCIA_SIMBOLICA",
        2: "VDG_COSIFICACION_SLUTSHAMING",
        3: "VDG_HOSTILIDAD_FEMINICIDIO",
        4: "VDG_MANOSFERA_ANTIFEMINISMO",
        5: "VDG_DESACREDITACION_ACTIVISTAS",
        6: "VDG_SALVAGUARDA_FALSO_POSITIVO",
    }
    return mapping[orden]


def _load_ground_truth(path: Path) -> dict[str, dict]:
    """Carga el JSON de ground truth. Devuelve dict {content_id: entry}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["content_id"]: item for item in data["items"]}


def _load_db_state(path: Path) -> dict[str, dict]:
    """Lee analysis_results + analysis_labels. Devuelve dict {content_id: state}.

    Cada state tiene:
      - tiene_violencia (bool)
      - severidad (str)
      - exclusion_label (str | None)
      - labels (list[(cat_code, dim)]) -> tuples ordenadas por orden ascendente
      - id (int)
    """
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        """
        SELECT id, content_id, tiene_violencia, severidad, exclusion_label,
               categoria, dimension
        FROM analysis_results
        """
    )
    by_cid: dict[str, dict] = {}
    for r in cur.fetchall():
        by_cid[r["content_id"]] = {
            "id": r["id"],
            "tiene_violencia": r["tiene_violencia"],
            "severidad": r["severidad"],
            "exclusion_label": r["exclusion_label"],
            "labels": [],
        }
    cur.execute(
        """
        SELECT analysis_result_id, categoria, dimension, severidad, orden
        FROM analysis_labels
        ORDER BY analysis_result_id, orden
        """
    )
    rid_to_cid = {state["id"]: cid for cid, state in by_cid.items()}
    for r in cur.fetchall():
        cid = rid_to_cid.get(r["analysis_result_id"])
        if cid is None:
            continue
        by_cid[cid]["labels"].append((r["categoria"], r["dimension"]))
    con.close()
    return by_cid


def _normalize_gt(gt_entry: dict) -> tuple[set[tuple[str, str | None]], set[str]]:
    """Convierte el ground truth a (set de tuplas canónicas, set de exclusion_labels)."""
    labels = set()
    for orden, subdim in gt_entry["ground_truth"]:
        labels.add((_cat_code(orden), subdim))
    exclusions = set()
    if gt_entry.get("exclusion_label"):
        exclusions.add(gt_entry["exclusion_label"])
    return labels, exclusions


def _normalize_predicted(state: dict) -> tuple[set[tuple[str, str | None]], set[str]]:
    """Convierte el estado de la DB a (set de tuplas canónicas, set de exclusion_labels)."""
    labels = set()
    for cat, dim in state["labels"]:
        labels.add((cat, dim))
    exclusions = set()
    if state["exclusion_label"]:
        exclusions.add(state["exclusion_label"])
    return labels, exclusions


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def evaluate(ground_truth: dict[str, dict], db_state: dict[str, dict]) -> dict:
    """Ejecuta la evaluacion completa y devuelve el dict con metricas."""
    cids = sorted(set(ground_truth.keys()) | set(db_state.keys()))

    # Distribucion de n_labels
    distrib_db = Counter()
    distrib_gt = Counter()
    distrib_match = Counter()  # match por item (exact o no)

    per_subdim: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    jaccards: list[float] = []
    exact_matches = 0
    partial_matches = 0  # cualquier label en comun pero no exact
    false_positives_items = 0  # predice violencia, gt dice ninguna
    false_negatives_items = 0  # gt dice violencia, predice ninguna
    n_items_evaluated = 0

    for cid in cids:
        gt_entry = ground_truth.get(cid)
        state = db_state.get(cid)
        if gt_entry is None:
            continue  # item solo en DB, sin ground truth
        n_items_evaluated += 1

        gt_labels, gt_excl = _normalize_gt(gt_entry)
        if state is None:
            pred_labels, pred_excl = set(), set()
        else:
            pred_labels, pred_excl = _normalize_predicted(state)

        distrib_gt[len(gt_labels)] += 1
        distrib_db[len(pred_labels)] += 1

        if gt_labels == pred_labels and gt_excl == pred_excl:
            exact_matches += 1
            distrib_match["exact"] += 1
        elif gt_labels & pred_labels:
            partial_matches += 1
            distrib_match["partial"] += 1
        else:
            distrib_match["none"] += 1

        if not gt_labels and pred_labels:
            false_positives_items += 1
        if gt_labels and not pred_labels:
            false_negatives_items += 1

        # Per-subdim TP/FP/FN
        for cat, dim in gt_labels:
            key = f"{cat}::{dim}"
            if (cat, dim) in pred_labels:
                per_subdim[key]["tp"] += 1
            else:
                per_subdim[key]["fn"] += 1
        for cat, dim in pred_labels:
            if (cat, dim) not in gt_labels:
                key = f"{cat}::{dim}"
                per_subdim[key]["fp"] += 1

        jaccards.append(_jaccard(gt_labels, pred_labels))

    # Compute precision/recall/F1 por sub-dim
    subdim_metrics = {}
    for key, counts in per_subdim.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        subdim_metrics[key] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }

    # Aggregate
    total_tp = sum(s["tp"] for s in per_subdim.values())
    total_fp = sum(s["fp"] for s in per_subdim.values())
    total_fn = sum(s["fn"] for s in per_subdim.values())
    agg_precision = _safe_div(total_tp, total_tp + total_fp)
    agg_recall = _safe_div(total_tp, total_tp + total_fn)
    agg_f1 = _safe_div(2 * agg_precision * agg_recall, agg_precision + agg_recall)

    avg_n_labels_db = sum(k * v for k, v in distrib_db.items()) / max(sum(distrib_db.values()), 1)
    avg_n_labels_gt = sum(k * v for k, v in distrib_gt.items()) / max(sum(distrib_gt.values()), 1)
    avg_jaccard = sum(jaccards) / max(len(jaccards), 1) if jaccards else 0.0

    return {
        "n_items_in_ground_truth": len(ground_truth),
        "n_items_in_db": len(db_state),
        "n_items_evaluated": n_items_evaluated,
        "distrib_n_labels_db": dict(sorted(distrib_db.items())),
        "distrib_n_labels_ground_truth": dict(sorted(distrib_gt.items())),
        "match_distribution": distrib_match,
        "exact_match": exact_matches,
        "partial_match": partial_matches,
        "no_match": distrib_match.get("none", 0),
        "false_positive_items": false_positives_items,
        "false_negative_items": false_negatives_items,
        "avg_jaccard": round(avg_jaccard, 3),
        "avg_n_labels_db": round(avg_n_labels_db, 2),
        "avg_n_labels_ground_truth": round(avg_n_labels_gt, 2),
        "aggregate": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(agg_precision, 3),
            "recall": round(agg_recall, 3),
            "f1": round(agg_f1, 3),
        },
        "per_subdim": dict(sorted(subdim_metrics.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=DEFAULT_GT,
        help="Path al JSON con ground truth",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="Path a la base SQLite",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Path al JSON de salida con las metricas",
    )
    args = parser.parse_args()

    if not args.ground_truth.exists():
        print(f"ERROR: ground truth no encontrado en {args.ground_truth}", file=sys.stderr)
        return 1
    if not args.db.exists():
        print(f"ERROR: DB no encontrada en {args.db}", file=sys.stderr)
        return 1

    ground_truth = _load_ground_truth(args.ground_truth)
    db_state = _load_db_state(args.db)
    metrics = evaluate(ground_truth, db_state)

    print("=" * 70)
    print(f"BASELINE EVALUATION ({args.db.name} vs {args.ground_truth.name})")
    print("=" * 70)
    print(f"Items en ground truth : {metrics['n_items_in_ground_truth']}")
    print(f"Items en DB            : {metrics['n_items_in_db']}")
    print(f"Items evaluados        : {metrics['n_items_evaluated']}")
    print()
    print("--- Distribucion de n_labels (items con violencia) ---")
    print(f"  DB actual        : {metrics['distrib_n_labels_db']}")
    print(f"  Ground truth     : {metrics['distrib_n_labels_ground_truth']}")
    print(f"  Promedio DB      : {metrics['avg_n_labels_db']}")
    print(f"  Promedio GT      : {metrics['avg_n_labels_ground_truth']}")
    print()
    print("--- Match por item ---")
    print(f"  Exact match     : {metrics['exact_match']}")
    print(f"  Partial match   : {metrics['partial_match']}")
    print(f"  No match        : {metrics['no_match']}")
    print(f"  Avg Jaccard     : {metrics['avg_jaccard']}")
    print()
    print("--- Errores por item ---")
    print(f"  Falsos positivos (predice VDG, GT=nada): {metrics['false_positive_items']}")
    print(f"  Falsos negativos (GT=VDG, predice nada): {metrics['false_negative_items']}")
    print()
    print("--- Metricas agregadas (multi-label) ---")
    print(
        f"  TP={metrics['aggregate']['tp']} FP={metrics['aggregate']['fp']} FN={metrics['aggregate']['fn']}"
    )
    print(f"  Precision = {metrics['aggregate']['precision']:.3f}")
    print(f"  Recall    = {metrics['aggregate']['recall']:.3f}")
    print(f"  F1        = {metrics['aggregate']['f1']:.3f}")
    print()
    print("--- Metricas por sub-dimension (top errores) ---")
    sorted_by_fn = sorted(
        metrics["per_subdim"].items(),
        key=lambda x: (x[1]["fn"], x[1]["fp"]),
        reverse=True,
    )
    for key, m in sorted_by_fn[:15]:
        print(
            f"  {key:<40} TP={m['tp']:>2} FP={m['fp']:>2} FN={m['fn']:>2} P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}"
        )

    args.output.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, sort_keys=False),
        encoding="utf-8",
    )
    print()
    print(f"Metricas guardadas en {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
