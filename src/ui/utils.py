"""Shared helpers for the Enola Investigadora Digital Streamlit UI.

Centralizes:
- DB data loading with caching
- Human-readable category labels (delegated to ``src.ui.labels``)
- Altair chart builders (pie + bar)
- Knowledge base ZIP packaging for download
- KPI computation from analysis results
"""

from __future__ import annotations

import io
import zipfile
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd

from src.analyzer.category_mapping import CATEGORIAS_ORDENADAS
from src.storage import get_database
from src.storage.database import Database
from src.ui.labels import get_category_label

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_PATH = PROJECT_ROOT / "src" / "logo.png"
UGR_LOGO_PATH = PROJECT_ROOT / "src" / "ugr-white.png"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge" / "categorias-violencia-genero-digital"
README_PATH = PROJECT_ROOT / "README.md"
SPEC_PATH = PROJECT_ROOT / "SPEC.md"

GITHUB_REPO_URL = "https://github.com/investigador/tfm-violencia-genero"
GITHUB_FORK_URL = "https://github.com/investigador/tfm-violencia-genero/fork"
CONTACT_EMAIL = "investigador@example.com"

CATEGORIA_COLORS: dict[str, str] = {
    "VDG_VIOLENCIA_SIMBOLICA": "#e67e22",
    "VDG_COSIFICACION_SLUTSHAMING": "#8e44ad",
    "VDG_HOSTILIDAD_FEMINICIDIO": "#c0392b",
    "VDG_MANOSFERA_ANTIFEMINISMO": "#16a085",
    "VDG_SALVAGUARDA_FALSO_POSITIVO": "#7f8c8d",
    "VDG_DESACREDITACION_ACTIVISTAS": "#d35400",
}

VIOLENT_COLOR = "#c0392b"
NON_VIOLENT_COLOR = "#27ae60"


def label_for(code: str) -> str:
    """Return the human-readable label for a VDG_* code, or the code itself."""
    return get_category_label(code)


def color_for(code: str) -> str:
    """Return the chart color for a VDG_* code, or a neutral gray."""
    return CATEGORIA_COLORS.get(code, "#95a5a6")


def load_data() -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Load DB stats, analysis results, posts, and pages in one shot."""
    db: Database = get_database()
    return (
        db.get_stats(),
        db.get_analysis_results(),
        db.get_posts(limit=1000),
        db.get_pages(limit=100),
    )


def filter_by_content_type(analysis: Sequence[dict], content_type: str) -> list[dict]:
    """Filter analysis results by 'post', 'comment', or 'all'."""
    if content_type == "all":
        return list(analysis)
    return [a for a in analysis if a.get("content_type") == content_type]


def compute_pie_data(results: Sequence[dict]) -> pd.DataFrame:
    """Build a DataFrame for the violent vs non-violent pie chart."""
    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
    valid = [a for a in results if a.get("exclusion_label") not in _exclusion]
    counts = Counter(a.get("tiene_violencia") for a in valid)
    violent = counts.get("true", 0)
    non_violent = counts.get("false", 0)
    rows: list[dict[str, object]] = [
        {"Estado": "Con violencia", "Cantidad": violent},
        {"Estado": "Sin violencia", "Cantidad": non_violent},
    ]
    return pd.DataFrame(rows)


def compute_bar_data(results: Sequence[dict]) -> pd.DataFrame:
    """Build a DataFrame for the per-category bar chart.

    **Multi-label aware**: each analysis row contributes as many votes
    as labels it carries (via the ``labels`` side key, falling back to
    the flat ``categoria`` when no labels are present). A single
    analyzed content that triggers two categories is therefore counted
    twice — once per label.

    **Excludes** rows carrying any exclusion sentinel (CÓDIGO 99 or
    VIOLENCIA_COMUN) from both the numerator and the denominator, so
    the percentages reflect "what fraction of valid violence is each
    category" (Regla 2 — Porcentaje Válido).

    Always includes the 6 canonical categories; missing ones get 0 so
    the chart stays stable across data changes.
    """
    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
    valid = [
        a
        for a in results
        if a.get("tiene_violencia") == "true" and a.get("exclusion_label") not in _exclusion
    ]
    counts: Counter[str] = Counter()
    for a in valid:
        labels = a.get("labels") or []
        if labels:
            for lbl in labels:
                cat = lbl.get("categoria") or "ninguna"
                if cat == "ninguna":
                    continue
                counts[cat] += 1
        else:
            cat = a.get("categoria", "ninguna")
            if cat == "ninguna":
                continue
            counts[cat] += 1
    total = sum(counts.get(c, 0) for c in CATEGORIAS_ORDENADAS)
    rows: list[dict[str, object]] = []
    for code in CATEGORIAS_ORDENADAS:
        n = counts.get(code, 0)
        pct = (n / total * 100.0) if total > 0 else 0.0
        rows.append(
            {
                "Categoría": label_for(code),
                "Código": code,
                "Cantidad": n,
                "Porcentaje": round(pct, 1),
            }
        )
    return pd.DataFrame(rows)


def compute_label_distribution(
    results: Sequence[dict],
) -> tuple[pd.DataFrame, int]:
    """Multi-label aware: count distinct categories, total label votes,
    and the most common (categoria, dimension) pair.

    Returns:
        Tuple ``(per_label_df, total_label_votes)`` where
        ``per_label_df`` has columns ``Categoría``/``Código``/
        ``Subdimensión``/``Cantidad``/``Porcentaje``. Useful for
        drill-down views that want to see which sub-dimensions are
        firing, not just the umbrella categories.
    """
    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
    violent = [
        a
        for a in results
        if a.get("tiene_violencia") == "true" and a.get("exclusion_label") not in _exclusion
    ]
    counts: Counter[tuple[str, str | None]] = Counter()
    for a in violent:
        labels = a.get("labels") or []
        if labels:
            for lbl in labels:
                counts[(lbl.get("categoria") or "ninguna", lbl.get("dimension"))] += 1
        else:
            counts[(a.get("categoria", "ninguna"), a.get("dimension"))] += 1
    total = sum(counts.values())
    rows: list[dict[str, object]] = []
    for (cat, dim), n in counts.most_common():
        cat_str: str = str(cat) if cat is not None else "ninguna"
        pct = (n / total * 100.0) if total > 0 else 0.0
        rows.append(
            {
                "Categoría": label_for(cat_str),
                "Código": cat_str,
                "Subdimensión": str(dim) if dim else "—",
                "Cantidad": n,
                "Porcentaje": round(pct, 1),
            }
        )
    return pd.DataFrame(rows), total


def build_pie_chart(df: pd.DataFrame) -> alt.Chart:
    """Build an interactive donut chart for violent vs non-violent."""
    return (
        alt.Chart(df)
        .mark_arc(innerRadius=80, outerRadius=140, stroke="#fff", strokeWidth=2)
        .encode(
            theta=alt.Theta("Cantidad:Q", title=None),
            color=alt.Color(
                "Estado:N",
                scale=alt.Scale(
                    domain=["Con violencia", "Sin violencia", "Sin clasificar"],
                    range=[VIOLENT_COLOR, NON_VIOLENT_COLOR, "#bdc3c7"],
                ),
                legend=alt.Legend(title="Estado", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Estado:N", title="Estado"),
                alt.Tooltip("Cantidad:Q", title="Cantidad"),
            ],
        )
        .properties(height=320)
    )


def build_bar_chart(df: pd.DataFrame) -> alt.Chart:
    """Build a horizontal bar chart with the 6 canonical categories."""
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Porcentaje:Q", title="% sobre contenido violento"),
            y=alt.Y(
                "Categoría:N",
                sort=alt.SortField(field="Porcentaje", order="descending"),
                title=None,
            ),
            color=alt.Color(
                "Código:N",
                scale=alt.Scale(
                    domain=CATEGORIAS_ORDENADAS,
                    range=[CATEGORIA_COLORS[c] for c in CATEGORIAS_ORDENADAS],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Categoría:N", title="Categoría"),
                alt.Tooltip("Cantidad:Q", title="Cantidad"),
                alt.Tooltip("Porcentaje:Q", title="%", format=".1f"),
            ],
        )
        .properties(height=320)
    )


def build_knowledge_zip() -> bytes:
    """Zip the canonical knowledge base directory in memory.

    Returns the raw bytes of a ZIP containing all .md files in
    ``knowledge/categorias-violencia-genero-digital/`` with their
    relative paths preserved (e.g. ``glosario/jerga-manosfera.md``).
    """
    if not KNOWLEDGE_DIR.is_dir():
        return b""

    buf = io.BytesIO()
    base = KNOWLEDGE_DIR.parent
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
            arcname = path.relative_to(base)
            zf.write(path, arcname=str(arcname))
    return buf.getvalue()


def knowledge_zip_filename() -> str:
    """Return a dated filename for the knowledge base zip download."""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"enola-taxonomia-violencia-{today}.zip"


def knowledge_summary() -> dict[str, int]:
    """Return summary stats about the knowledge directory contents."""
    if not KNOWLEDGE_DIR.is_dir():
        return {"files": 0, "size_bytes": 0}
    files = list(KNOWLEDGE_DIR.rglob("*.md"))
    size = sum(f.stat().st_size for f in files)
    return {"files": len(files), "size_bytes": size}


def compute_kpis(
    stats: dict, analysis: Sequence[dict], knowledge: dict[str, int]
) -> dict[str, object]:
    """Compute the four headline KPIs for the hero section.

    Multi-label aware: the "violent" count is the number of contents
    with at least one violent label; the "top label" is the most
    frequent individual ``categoria`` across all labels (so a single
    multi-label content can boost several tops).
    """
    _exclusion = {"CODIGO_99", "VIOLENCIA_COMUN"}
    valid = [a for a in analysis if a.get("exclusion_label") not in _exclusion]
    net_total = len(valid)
    violent = sum(1 for a in valid if a.get("tiene_violencia") == "true")
    violent_pct = (violent / net_total * 100.0) if net_total else 0.0
    top_cat: str | None = None
    if violent:
        counter: Counter[str] = Counter()
        for a in valid:
            if a.get("tiene_violencia") != "true":
                continue
            labels = a.get("labels") or []
            if labels:
                for lbl in labels:
                    code = lbl.get("categoria")
                    if code:
                        counter[str(code)] += 1
            elif a.get("categoria"):
                counter[str(a["categoria"])] += 1
        if counter:
            top_cat = label_for(str(counter.most_common(1)[0][0]))
    return {
        "total": net_total,
        "violent": violent,
        "violent_pct": round(violent_pct, 1),
        "categories": len(CATEGORIAS_ORDENADAS),
        "pages": stats.get("pages_count", 0) or 0,
        "top_category": top_cat or "—",
        "knowledge_files": knowledge.get("files", 0),
    }
