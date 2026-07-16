"""Live re-classification evaluation: corre el clasificador sobre el corpus
auditado y compara contra ground truth sin tocar la DB.

Usa el LLM real (Ollama) si está disponible; si no, cae al fallback
rule-based. Reporta las mismas métricas que ``eval_baseline.py`` para
facilitar la comparación pre/post-fix.

Uso:
    .venv/bin/python scripts/eval_live.py
    .venv/bin/python scripts/eval_live.py --limit 10
    .venv/bin/python scripts/eval_live.py --output data/baseline_post_fix.json
    .venv/bin/python scripts/eval_live.py --rule-based  # sin Ollama
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GT = REPO_ROOT / "data" / "ground_truth_audit.json"
DEFAULT_DB = REPO_ROOT / "data" / "tfm.db"
DEFAULT_OUT = REPO_ROOT / "data" / "baseline_post_fix.json"

# Ensure the repo root is on sys.path so ``import src`` works even when
# the package isn't installed editable in the current venv.
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _cat_code(orden: int) -> str:
    return {
        1: "VDG_VIOLENCIA_SIMBOLICA",
        2: "VDG_COSIFICACION_SLUTSHAMING",
        3: "VDG_HOSTILIDAD_FEMINICIDIO",
        4: "VDG_MANOSFERA_ANTIFEMINISMO",
        5: "VDG_DESACREDITACION_ACTIVISTAS",
        6: "VDG_SALVAGUARDA_FALSO_POSITIVO",
    }[orden]


def _load_ground_truth(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["content_id"]: item for item in data["items"]}


def _load_corpus_texts(db_path: Path, cids: Iterable[str]) -> dict[str, dict]:
    """Returns ``{content_id: {"text": str, "type": "post"|"comment"}}``.

    Falls back to scanning both tables because the audit ground truth
    mixes posts and comments under the same ``content_id`` key.
    """
    out: dict[str, dict] = {}
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cid_list = list(cids)
    if not cid_list:
        return out
    placeholders = ",".join("?" * len(cid_list))
    cur.execute(
        f"SELECT id, text FROM posts WHERE id IN ({placeholders})",
        cid_list,
    )
    for r in cur.fetchall():
        out[str(r["id"])] = {"text": r["text"] or "", "type": "post"}
    cur.execute(
        f"SELECT id, text FROM comments WHERE id IN ({placeholders})",
        cid_list,
    )
    for r in cur.fetchall():
        if str(r["id"]) not in out:
            out[str(r["id"])] = {"text": r["text"] or "", "type": "comment"}
    con.close()
    return out


def _normalize_gt(gt_entry: dict) -> tuple[set, set]:
    labels = set()
    for orden, subdim in gt_entry["ground_truth"]:
        labels.add((_cat_code(orden), subdim))
    exclusions = set()
    if gt_entry.get("exclusion_label"):
        exclusions.add(gt_entry["exclusion_label"])
    return labels, exclusions


def _normalize_predicted(result) -> tuple[set, set]:
    labels = {(lbl.categoria, lbl.dimension) for lbl in result.clasificaciones}
    exclusions = set()
    if result.exclusion_label:
        exclusions.add(result.exclusion_label)
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


async def _classify_all(classifier, cids: list[str], corpus: dict[str, dict]) -> dict[str, object]:
    """Run ``classifier.classify`` on every cid concurrently (sequential)."""
    preds: dict[str, object] = {}
    errors: dict[str, str] = {}
    parse_errors: dict[str, str] = {}
    t0 = time.monotonic()
    for cid in cids:
        text = corpus.get(cid, {}).get("text", "")
        if not text:
            preds[cid] = None
            continue
        try:
            res = await classifier.classify(text)
            preds[cid] = res
            if getattr(res, "error_parsing", None):
                parse_errors[cid] = res.error_parsing
        except Exception as e:
            errors[cid] = f"{type(e).__name__}: {e}"
            preds[cid] = None
    elapsed = time.monotonic() - t0
    return {
        "preds": preds,
        "errors": errors,
        "parse_errors": parse_errors,
        "elapsed_s": elapsed,
    }


def evaluate(
    ground_truth: dict[str, dict],
    preds: dict[str, object],
    corpus: dict[str, dict],
) -> dict:
    distrib_pred = Counter()
    distrib_gt = Counter()
    distrib_match = Counter()
    per_subdim: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    jaccards: list[float] = []
    exact = partial = none = 0
    fp_items = fn_items = 0
    n = 0
    for cid, gt_entry in ground_truth.items():
        if cid not in corpus:
            continue
        n += 1
        gt_labels, gt_excl = _normalize_gt(gt_entry)
        result = preds.get(cid)
        if result is None:
            pred_labels: set = set()
            pred_excl: set = set()
        else:
            pred_labels, pred_excl = _normalize_predicted(result)

        distrib_gt[len(gt_labels)] += 1
        distrib_pred[len(pred_labels)] += 1

        if gt_labels == pred_labels and gt_excl == pred_excl:
            exact += 1
            distrib_match["exact"] += 1
        elif gt_labels & pred_labels:
            partial += 1
            distrib_match["partial"] += 1
        else:
            none += 1
            distrib_match["none"] += 1

        if not gt_labels and pred_labels:
            fp_items += 1
        if gt_labels and not pred_labels:
            fn_items += 1

        for cat, dim in gt_labels:
            key = f"{cat}::{dim}"
            if (cat, dim) in pred_labels:
                per_subdim[key]["tp"] += 1
            else:
                per_subdim[key]["fn"] += 1
        for cat, dim in pred_labels:
            if (cat, dim) not in gt_labels:
                per_subdim[key]["fp"] += 1

        jaccards.append(_jaccard(gt_labels, pred_labels))

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

    total_tp = sum(s["tp"] for s in per_subdim.values())
    total_fp = sum(s["fp"] for s in per_subdim.values())
    total_fn = sum(s["fn"] for s in per_subdim.values())
    agg_precision = _safe_div(total_tp, total_tp + total_fp)
    agg_recall = _safe_div(total_tp, total_tp + total_fn)
    agg_f1 = _safe_div(2 * agg_precision * agg_recall, agg_precision + agg_recall)

    avg_n_labels_pred = sum(k * v for k, v in distrib_pred.items()) / max(
        sum(distrib_pred.values()), 1
    )
    avg_n_labels_gt = sum(k * v for k, v in distrib_gt.items()) / max(sum(distrib_gt.values()), 1)

    return {
        "n_items_evaluated": n,
        "distrib_n_labels_predicted": dict(sorted(distrib_pred.items())),
        "distrib_n_labels_ground_truth": dict(sorted(distrib_gt.items())),
        "match_distribution": distrib_match,
        "exact_match": exact,
        "partial_match": partial,
        "no_match": none,
        "false_positive_items": fp_items,
        "false_negative_items": fn_items,
        "avg_jaccard": round(sum(jaccards) / max(len(jaccards), 1), 3),
        "avg_n_labels_predicted": round(avg_n_labels_pred, 2),
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


async def main_async(args: argparse.Namespace) -> int:
    if not args.ground_truth.exists():
        print(f"ERROR: ground truth no encontrado en {args.ground_truth}", file=sys.stderr)
        return 1
    ground_truth = _load_ground_truth(args.ground_truth)
    cids = sorted(ground_truth.keys())
    if args.limit:
        cids = cids[: args.limit]
    corpus = _load_corpus_texts(args.db, cids)

    print(f"Corpus: {len(corpus)}/{len(cids)} items encontrados en DB")
    if not corpus:
        print("Nada que evaluar — abortando.", file=sys.stderr)
        return 1

    # Build classifier.
    from src.analyzer.few_shot_loader import load_few_shot_examples
    from src.analyzer.llm_client import OllamaClient
    from src.analyzer.rag_classifier import RAGClassifier
    from src.config.settings import get_settings

    few_shots = list(load_few_shot_examples()) if not args.no_few_shots else []
    if args.rule_based:
        classifier = RAGClassifier(
            few_shot_examples=few_shots,
            context_chunks=0,
        )
    else:
        settings = get_settings()
        llm = OllamaClient(
            base_url=settings.ollama.base_url,
            model=settings.ollama.llm_model,
            temperature=settings.analyzer.temperature,
            max_tokens=settings.analyzer.max_tokens,
        )
        classifier = RAGClassifier(
            llm_client=llm,
            few_shot_examples=few_shots,
            context_chunks=0,
            feedback_store=None,
        )

    result = await _classify_all(classifier, cids, corpus)
    preds = result["preds"]
    errors = result["errors"]
    parse_errors = result["parse_errors"]
    print(f"Tiempo total: {result['elapsed_s']:.1f}s")
    if errors:
        print(f"Errores Ollama: {len(errors)}")
    if parse_errors:
        print(f"Errores de parsing JSON: {len(parse_errors)}")

    metrics = evaluate(ground_truth, preds, corpus)

    print()
    print("=" * 70)
    print(
        f"LIVE EVAL ({'rule-based' if args.rule_based else 'LLM'} + few_shots={not args.no_few_shots})"
    )
    print("=" * 70)
    print(f"Items evaluados   : {metrics['n_items_evaluated']}")
    print()
    print("--- Distribucion de n_labels (items con violencia) ---")
    print(f"  Predichas        : {metrics['distrib_n_labels_predicted']}")
    print(f"  Ground truth     : {metrics['distrib_n_labels_ground_truth']}")
    print(f"  Promedio pred    : {metrics['avg_n_labels_predicted']}")
    print(f"  Promedio GT      : {metrics['avg_n_labels_ground_truth']}")
    print()
    print("--- Match por item ---")
    print(f"  Exact match     : {metrics['exact_match']}")
    print(f"  Partial match   : {metrics['partial_match']}")
    print(f"  No match        : {metrics['no_match']}")
    print(f"  Avg Jaccard     : {metrics['avg_jaccard']}")
    print()
    print("--- Errores por item ---")
    print(f"  Falsos positivos : {metrics['false_positive_items']}")
    print(f"  Falsos negativos : {metrics['false_negative_items']}")
    print()
    print("--- Metricas agregadas ---")
    print(
        f"  TP={metrics['aggregate']['tp']} FP={metrics['aggregate']['fp']} FN={metrics['aggregate']['fn']}"
    )
    print(f"  Precision = {metrics['aggregate']['precision']:.3f}")
    print(f"  Recall    = {metrics['aggregate']['recall']:.3f}")
    print(f"  F1        = {metrics['aggregate']['f1']:.3f}")
    print()
    print("--- Per-subdim (top errores) ---")
    sorted_by_fn = sorted(
        metrics["per_subdim"].items(),
        key=lambda x: (x[1]["fn"], x[1]["fp"]),
        reverse=True,
    )
    for key, m in sorted_by_fn[:15]:
        print(
            f"  {key:<40} TP={m['tp']:>2} FP={m['fp']:>2} FN={m['fn']:>2} P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}"
        )

    metrics["meta"] = {
        "rule_based": args.rule_based,
        "no_few_shots": args.no_few_shots,
        "elapsed_s": round(result["elapsed_s"], 1),
        "errors": errors,
        "parse_errors": parse_errors,
    }

    args.output.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, sort_keys=False),
        encoding="utf-8",
    )
    print()
    print(f"Metricas guardadas en {args.output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=0, help="Probar solo los primeros N items")
    parser.add_argument("--rule-based", action="store_true", help="No usar Ollama")
    parser.add_argument("--no-few-shots", action="store_true", help="No inyectar few-shots")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
