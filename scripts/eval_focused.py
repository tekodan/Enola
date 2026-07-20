"""Focused live eval sobre los 7 errores residuales R7 + muestra aleatoria.

Más rápido que ``eval_live.py`` (corre ~30s por item en lugar de ~50s
gracias al caché de Ollama) y permite ver la mejora en los casos más
diagnósticos.

Uso:
    .venv/bin/python scripts/eval_focused.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GT = REPO_ROOT / "data" / "ground_truth_audit.json"
DEFAULT_DB = REPO_ROOT / "data" / "tfm.db"

sys.path.insert(0, str(REPO_ROOT))


# Hard-coded sample of diagnostic cases (R7 + high-value multi-label).
DIAGNOSTIC_CIDS = [
    "0f3e884a8a124fd1_p0",  # multi: 1.3 + 2.3 + 4.2 (decoded leetspeak)
    "0f3e884a8a124fd1_p2",  # multi: 4.1 + 4.2 + 4.3
    "dc8ae80a3ae35f92",  # multi: 1.3 + 2.3 + 4.1
    "b0bcbbb5eb375a41",  # multi: 1.3 + 2.3 + 4.1 + 4.2 (4 labels!)
    "ed489d3558a69eef",  # 4.3 x 2 (multi-marcador)
    "2020cf0150b86856",  # multi: 4.2 + 1.3
    "6983ada882e8a729",  # multi: 1.3 + 4.2
    "5fbccd33967c9c0b",  # multi: 1.3 + 4.2
    "d160eac77321b71d",  # multi: 1.2 + 6.1
    "b177ef1b0bf960bf",  # multi: 3.3 + 6.3 + 5.2
    "7e6c8887fea366de",  # multi: 4.3 + 6.1 + 5.2 (con jaja)
    "6ac63c8dd7b3dbcd",  # multi: 1.3 + 2.3 + 4.2 + 5.2 (4 labels)
    "e355f12847ca56e7",  # multi: 1.1 + 4.2
    "247eade36a76b5ad",  # multi: 4.1 + 4.2
    "2effd62b3d4cbac5",  # single: 1.3
    "74da4732a892ce97",  # single: 6.1
    # Casos negativos (no VDG, deben seguir clasificándose como ninguna)
    "1635ffd5d8837cf6",  # [USUARIO_FB]
    "f787d814b5a47750",  # "Ahora resulta que los hombres no engañan"
    "3741fe9979b310c6",  # "Muchos así..."
    "8b70afaf7ae522f0",  # "Un clasico"
    "d00e75474ff087a6",  # "Es chistoso por qué es cierto..."
    # Falsos positivos que el clasificador NO debe repetir:
    "d09fd0fa741fd562",  # "ellas son las que me dan cariño y pagan todo" → []
    "b7aff28bc7d3c1de",  # "con mujer o sin mujer la paja no falta" → []
    "9e768e369f38ae29",  # "si tenés más de 60 años..." → []
]


def _cat_code(orden: int) -> str:
    return {
        1: "VDG_VIOLENCIA_SIMBOLICA",
        2: "VDG_COSIFICACION_SLUTSHAMING",
        3: "VDG_HOSTILIDAD_FEMINICIDIO",
        4: "VDG_MANOSFERA_ANTIFEMINISMO",
        5: "VDG_DESACREDITACION_ACTIVISTAS",
        6: "VDG_SALVAGUARDA_FALSO_POSITIVO",
    }[orden]


def _load_corpus(db_path: Path, cids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    placeholders = ",".join("?" * len(cids))
    cur.execute(f"SELECT id, text FROM posts WHERE id IN ({placeholders})", cids)
    for r in cur.fetchall():
        out[str(r["id"])] = {"text": r["text"] or "", "type": "post"}
    cur.execute(f"SELECT id, text FROM comments WHERE id IN ({placeholders})", cids)
    for r in cur.fetchall():
        if str(r["id"]) not in out:
            out[str(r["id"])] = {"text": r["text"] or "", "type": "comment"}
    con.close()
    return out


def _load_ground_truth_subset(path: Path, cids: list[str]) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["content_id"]: item for item in data["items"] if item["content_id"] in cids}


async def main_async(args: argparse.Namespace) -> int:
    gt_full = json.loads(args.ground_truth.read_text(encoding="utf-8"))
    cids = DIAGNOSTIC_CIDS if args.diagnostic_only else [i["content_id"] for i in gt_full["items"]]
    ground_truth = _load_ground_truth_subset(args.ground_truth, cids)
    corpus = _load_corpus(args.db, cids)
    print(f"Total ground truth: {len(ground_truth)} items")
    print(f"Encontrados en DB  : {len(corpus)} items (con texto)")
    missing = [cid for cid in cids if cid not in corpus]
    if missing:
        print(f"Sin texto en DB    : {len(missing)} -> {missing[:5]}...")

    from src.analyzer.few_shot_loader import load_few_shot_examples
    from src.analyzer.llm_client import OllamaClient
    from src.analyzer.rag_classifier import RAGClassifier
    from src.config.settings import get_settings

    settings = get_settings()
    llm = OllamaClient(
        base_url=settings.ollama.base_url,
        model=settings.ollama.llm_model,
        temperature=0,
        max_tokens=settings.analyzer.max_tokens,
    )
    classifier = RAGClassifier(
        llm_client=llm,
        few_shot_examples=list(load_few_shot_examples()),
        context_chunks=0,
        feedback_store=None,
    )

    print(f"\nModelo  : {settings.ollama.llm_model}")
    print(f"Max tok : {settings.analyzer.max_tokens}")
    print(f"Fewshots: {len(classifier.few_shot_examples)}")
    print()

    distrib_pred: Counter = Counter()
    distrib_gt: Counter = Counter()
    exact = partial = none = fp = fn = 0
    jaccards: list[float] = []
    per_subdim: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    per_item: list[dict] = []
    parse_errors = 0

    t0 = time.monotonic()
    for cid in cids:
        item_corpus = corpus.get(cid)
        if not item_corpus or not item_corpus.get("text"):
            print(f"  SKIP {cid} (sin texto)")
            continue
        text = item_corpus["text"]
        gt_entry = ground_truth[cid]
        gt_labels = {(_cat_code(o), d) for o, d in gt_entry["ground_truth"]}

        t1 = time.monotonic()
        try:
            res = await classifier.classify(text)
        except Exception as e:
            print(f"  ERROR {cid}: {e}")
            continue
        elapsed = time.monotonic() - t1

        pred_labels = {(lbl.categoria, lbl.dimension) for lbl in res.clasificaciones}
        if res.error_parsing:
            parse_errors += 1

        distrib_gt[len(gt_labels)] += 1
        distrib_pred[len(pred_labels)] += 1

        if gt_labels == pred_labels:
            match = "EXACT"
            exact += 1
        elif gt_labels & pred_labels:
            match = "partial"
            partial += 1
        elif gt_labels and not pred_labels:
            match = "FN"
            fn += 1
        elif pred_labels and not gt_labels:
            match = "FP"
            fp += 1
        else:
            match = "neg-neg"

        if not gt_labels and pred_labels:
            fp += 1
        if gt_labels and not pred_labels:
            fn += 1

        for cat, dim in gt_labels:
            key = f"{cat}::{dim}"
            if (cat, dim) in pred_labels:
                per_subdim[key]["tp"] += 1
            else:
                per_subdim[key]["fn"] += 1
        for cat, dim in pred_labels:
            if (cat, dim) not in gt_labels:
                per_subdim[key]["fp"] += 1

        union = gt_labels | pred_labels
        jac = (len(gt_labels & pred_labels) / len(union)) if union else 1.0
        jaccards.append(jac)

        gt_short = ",".join(f"{d}" for _, d in sorted(gt_labels)) or "[]"
        pred_short = ",".join(f"{d}" for _, d in sorted(pred_labels)) or "[]"
        print(
            f"  [{match:6}] {cid[:40]:<40} gt={gt_short:<25} pred={pred_short:<25} ({elapsed:.0f}s)"
        )
        per_item.append(
            {
                "cid": cid,
                "match": match,
                "gt": sorted(gt_labels),
                "pred": sorted(pred_labels),
                "jaccard": round(jac, 3),
                "elapsed_s": round(elapsed, 1),
            }
        )

    total_t = time.monotonic() - t0
    total_tp = sum(s["tp"] for s in per_subdim.values())
    total_fp = sum(s["fp"] for s in per_subdim.values())
    total_fn = sum(s["fn"] for s in per_subdim.values())
    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0

    print()
    print("=" * 80)
    print(f"RESULTADOS ({len(jaccards)} items evaluados, {total_t:.1f}s total)")
    print("=" * 80)
    print()
    print(
        f"Exact match       : {exact}/{len(jaccards)} = {100 * exact / max(len(jaccards), 1):.1f}%"
    )
    print(f"Partial match     : {partial}")
    print(f"Falsos positivos  : {fp}")
    print(f"Falsos negativos  : {fn}")
    print(f"Avg Jaccard       : {sum(jaccards) / max(len(jaccards), 1):.3f}")
    print(f"Parse errors      : {parse_errors}")
    print()
    print(f"Precision = {precision:.3f} | Recall = {recall:.3f} | F1 = {f1:.3f}")
    print()
    print("Distribución de n_labels:")
    print(f"  Predichas : {dict(sorted(distrib_pred.items()))}")
    print(f"  Ground truth: {dict(sorted(distrib_gt.items()))}")
    if distrib_gt.get(3, 0) or distrib_gt.get(4, 0):
        n_multi_gt = sum(v for k, v in distrib_gt.items() if k >= 2)
        n_multi_pred = sum(v for k, v in distrib_pred.items() if k >= 2)
        print(f"  Items multi-etiqueta (≥2): GT={n_multi_gt}, Pred={n_multi_pred}")

    # Save results
    out_path = Path(args.output)
    out_path.write_text(
        json.dumps(
            {
                "n_items": len(jaccards),
                "exact": exact,
                "partial": partial,
                "fp": fp,
                "fn": fn,
                "avg_jaccard": round(sum(jaccards) / max(len(jaccards), 1), 3),
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
                "parse_errors": parse_errors,
                "distrib_pred": dict(sorted(distrib_pred.items())),
                "distrib_gt": dict(sorted(distrib_gt.items())),
                "per_item": per_item,
                "per_subdim": {k: dict(v) for k, v in sorted(per_subdim.items())},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print()
    print(f"Reporte guardado en {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--diagnostic-only", action="store_true", help="Solo los 25 casos diagnósticos hardcoded"
    )
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "baseline_focused.json")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
