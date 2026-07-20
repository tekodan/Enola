#!/usr/bin/env python3
"""Extract all statistical data from the database for the report.

Outputs a JSON file with every statistic the report needs.
Usage: python scripts/extract_stats.py [--db data/tfm.db] [--out data/exports/stats_snapshot.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.storage import get_database
from src.ui.adjusted_report import (
    build_adjusted_analysis,
    compute_adjustment_breakdown,
    compute_validation_breakdown,
)
from src.ui.utils import (
    compute_bar_data,
    compute_kpis,
    compute_label_distribution,
    compute_pie_data,
    knowledge_summary,
)


def _df_to_records(df):
    """Convert a pandas DataFrame to a list of dicts (JSON-safe)."""
    return json.loads(df.to_json(orient="records"))


def extract_all(db_path: str) -> dict:
    """Run every statistical function and return a nested dict."""
    import os

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    db = get_database()

    stats_raw = db.get_stats()
    analysis = db.get_analysis_results()
    feedback = db.get_feedback_with_labels()
    knowledge = knowledge_summary()

    # --- Regla 1: reliability ---
    from src.report.reliability import calcular_valores_perdidos

    reliability = calcular_valores_perdidos(analysis)

    # --- Regla 2: frequency distribution (categoria) ---
    from src.report.stats import compute_frequency_distribution

    freq_cat = compute_frequency_distribution(analysis, level="categoria")
    freq_sub = compute_frequency_distribution(analysis, level="subdimension")

    # --- Regla 3: mode ---
    from src.report.stats import compute_mode

    mode_cat = compute_mode(analysis, level="categoria")
    mode_sub = compute_mode(analysis, level="subdimension")

    # --- Regla 4: crosstabs ---
    from src.report.stats import compute_crosstabs

    crosstab_subdim = compute_crosstabs(analysis, dimension="subdimension")
    # fecha crosstab needs posts for month lookup
    posts = db.get_posts(limit=1000)
    page_lookup: dict[str, str] = {}
    for p in posts:
        pid = p.get("page_id") or ""
        if pid:
            page_lookup[pid] = p.get("page_title") or pid
    crosstab_pagina = compute_crosstabs(
        analysis, dimension="pagina", posts=posts, page_lookup=page_lookup
    )
    crosstab_fecha = compute_crosstabs(
        analysis, dimension="fecha", posts=posts, page_lookup=page_lookup
    )

    # --- Regla 6: metrics ---
    from src.report.metrics import compute_confusion_matrix, compute_reliability_metrics

    cm = compute_confusion_matrix(feedback, analysis_lookup={a["id"]: a for a in analysis})
    rm = compute_reliability_metrics(feedback, analysis_lookup={a["id"]: a for a in analysis})

    # --- UI KPIs ---
    kpis = compute_kpis(stats_raw, analysis, knowledge)

    # --- HITL validation breakdown ---
    adjusted = build_adjusted_analysis(analysis, feedback)
    adj_breakdown = compute_adjustment_breakdown(adjusted)
    val_breakdown = compute_validation_breakdown(adjusted)

    # --- Pie / bar data ---
    pie_df = compute_pie_data(analysis)
    bar_df = compute_bar_data(analysis)
    label_dist_df, total_label_votes = compute_label_distribution(analysis)

    return {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "db_path": db_path,
            "total_analysis": len(analysis),
            "total_feedback": len(feedback),
            "total_posts": stats_raw.get("posts_count", 0),
            "total_comments": stats_raw.get("comments_count", 0),
            "total_pages": stats_raw.get("pages_count", 0),
        },
        "kpis": kpis,
        "reliability": reliability.to_dict(),
        "frequency_categoria": _df_to_records(freq_cat.to_dataframe()),
        "frequency_subdimension": _df_to_records(freq_sub.to_dataframe()),
        "mode_categoria": mode_cat.to_dict(),
        "mode_subdimension": mode_sub.to_dict(),
        "crosstab_subdim": {
            "dimension": crosstab_subdim.dimension,
            "filas": crosstab_subdim.filas,
            "columnas": crosstab_subdim.columnas,
            "frecuencias": crosstab_subdim.frecuencias,
            "porcentajes_marginales": crosstab_subdim.porcentajes_marginales_columna,
            "alerta": crosstab_subdim.alerta_patron,
        },
        "crosstab_pagina": {
            "dimension": crosstab_pagina.dimension,
            "filas": crosstab_pagina.filas,
            "columnas": crosstab_pagina.columnas,
            "frecuencias": crosstab_pagina.frecuencias,
            "porcentajes_marginales": crosstab_pagina.porcentajes_marginales_columna,
            "alerta": crosstab_pagina.alerta_patron,
        },
        "crosstab_fecha": {
            "dimension": crosstab_fecha.dimension,
            "filas": crosstab_fecha.filas,
            "columnas": crosstab_fecha.columnas,
            "frecuencias": crosstab_fecha.frecuencias,
            "porcentajes_marginales": crosstab_fecha.porcentajes_marginales_columna,
            "alerta": crosstab_fecha.alerta_patron,
        },
        "confusion_matrix": cm.to_dict(),
        "reliability_metrics": rm.to_dict(),
        "pie_data": _df_to_records(pie_df),
        "bar_data": _df_to_records(bar_df),
        "label_distribution": {
            "rows": _df_to_records(label_dist_df),
            "total_label_votes": total_label_votes,
        },
        "validation_breakdown": val_breakdown,
        "adjustment_breakdown": adj_breakdown,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract stats snapshot")
    parser.add_argument("--db", default=str(ROOT / "data" / "tfm.db"))
    parser.add_argument("--out", default=str(ROOT / "data" / "exports" / "stats_snapshot.json"))
    args = parser.parse_args()

    data = extract_all(args.db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    print(f"Snapshot written to {out_path}")
    print(f"  Total analysis: {data['meta']['total_analysis']}")
    print(f"  Total feedback: {data['meta']['total_feedback']}")
    print(f"  Total posts: {data['meta']['total_posts']}")
    print(f"  Total comments: {data['meta']['total_comments']}")
    print(f"  Total pages: {data['meta']['total_pages']}")


if __name__ == "__main__":
    main()
