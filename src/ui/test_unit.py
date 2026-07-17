"""Unit tests for the Enola UI helpers (utils.py + labels.py)."""

from __future__ import annotations

import io
import zipfile

from src.analyzer.category_mapping import CATEGORIAS_ORDENADAS
from src.ui.labels import CATEGORIA_LABELS, get_category_choices, get_category_label
from src.ui.utils import (
    CATEGORIA_COLORS,
    KNOWLEDGE_DIR,
    build_bar_chart,
    build_knowledge_zip,
    build_pie_chart,
    color_for,
    compute_bar_data,
    compute_kpis,
    compute_pie_data,
    filter_by_content_type,
    knowledge_summary,
    knowledge_zip_filename,
    label_for,
)


def test_categoria_labels_complete():
    assert set(CATEGORIA_LABELS.keys()) == set(CATEGORIAS_ORDENADAS)
    for code, label in CATEGORIA_LABELS.items():
        assert label and label != code, f"Missing human label for {code}"


def test_categoria_labels_new_names():
    """Verify the centralised labels use the updated names from taxonomy."""
    assert CATEGORIA_LABELS["VDG_COSIFICACION_SLUTSHAMING"] == "Mercantilización Corporal"
    assert CATEGORIA_LABELS["VDG_SALVAGUARDA_FALSO_POSITIVO"] == "Salvaguarda (Falso Positivo)"


def test_categoria_colors_complete():
    assert set(CATEGORIA_COLORS.keys()) == set(CATEGORIAS_ORDENADAS)
    for color in CATEGORIA_COLORS.values():
        assert color.startswith("#") and len(color) == 7


def test_label_for_known_code():
    assert label_for("VDG_VIOLENCIA_SIMBOLICA") == "Violencia Simbólica"


def test_label_for_unknown_code_passthrough():
    assert label_for("VDG_FUTURA") == "Vdg Futura"


def test_label_for_centralized():
    """label_for() and get_category_label() return the same value."""
    for code in CATEGORIAS_ORDENADAS:
        assert label_for(code) == get_category_label(code)


def test_get_category_choices_matches():
    choices = get_category_choices()
    assert set(choices.keys()) == set(CATEGORIAS_ORDENADAS)
    for code in CATEGORIAS_ORDENADAS:
        assert choices[code] == CATEGORIA_LABELS[code]


def test_color_for_known_code():
    assert color_for("VDG_VIOLENCIA_SIMBOLICA") == "#e67e22"


def test_color_for_unknown_returns_neutral():
    assert color_for("xxx") == "#95a5a6"


def test_filter_by_content_type_all():
    rows = [{"content_type": "post"}, {"content_type": "comment"}]
    assert len(filter_by_content_type(rows, "all")) == 2


def test_filter_by_content_type_post():
    rows = [{"content_type": "post"}, {"content_type": "comment"}]
    assert filter_by_content_type(rows, "post") == [{"content_type": "post"}]


def test_filter_by_content_type_comment():
    rows = [{"content_type": "post"}, {"content_type": "comment"}]
    assert filter_by_content_type(rows, "comment") == [{"content_type": "comment"}]


def test_compute_pie_data_basic():
    rows = [
        {"tiene_violencia": "true"},
        {"tiene_violencia": "true"},
        {"tiene_violencia": "false"},
    ]
    df = compute_pie_data(rows)
    counts = dict(zip(df["Estado"], df["Cantidad"], strict=True))
    assert counts["Con violencia"] == 2
    assert counts["Sin violencia"] == 1


def test_compute_pie_data_handles_unknown():
    rows = [
        {"tiene_violencia": "true"},
        {"tiene_violencia": "unknown"},
    ]
    df = compute_pie_data(rows)
    counts = dict(zip(df["Estado"], df["Cantidad"], strict=True))
    assert counts["Con violencia"] == 1
    assert counts["Sin clasificar"] == 1


def test_compute_bar_data_includes_all_categories():
    rows = [{"tiene_violencia": "true", "categoria": "VDG_VIOLENCIA_SIMBOLICA"}] * 5
    df = compute_bar_data(rows)
    assert len(df) == len(CATEGORIAS_ORDENADAS)
    assert list(df["Código"]) == CATEGORIAS_ORDENADAS
    top = df.sort_values("Cantidad", ascending=False).iloc[0]
    assert top["Código"] == "VDG_VIOLENCIA_SIMBOLICA"
    assert top["Porcentaje"] == 100.0


def test_compute_bar_data_zero_for_missing_categories():
    rows = [{"tiene_violencia": "true", "categoria": "VDG_COSIFICACION_SLUTSHAMING"}]
    df = compute_bar_data(rows)
    assert df.loc[df["Código"] == "VDG_COSIFICACION_SLUTSHAMING", "Porcentaje"].iloc[0] == 100.0
    assert df.loc[df["Código"] == "VDG_HOSTILIDAD_FEMINICIDIO", "Porcentaje"].iloc[0] == 0.0


def test_compute_bar_data_empty_returns_all_zeros():
    df = compute_bar_data([])
    assert df["Porcentaje"].sum() == 0.0
    assert len(df) == 6


def test_compute_bar_data_multi_label_counts_each_label():
    """A row with two labels contributes two votes."""
    rows = [
        {
            "tiene_violencia": "true",
            "categoria": "VDG_VIOLENCIA_SIMBOLICA",
            "labels": [
                {"categoria": "VDG_VIOLENCIA_SIMBOLICA"},
                {"categoria": "VDG_HOSTILIDAD_FEMINICIDIO"},
            ],
        }
    ]
    df = compute_bar_data(rows)
    simb = df.loc[df["Código"] == "VDG_VIOLENCIA_SIMBOLICA", "Cantidad"].iloc[0]
    host = df.loc[df["Código"] == "VDG_HOSTILIDAD_FEMINICIDIO", "Cantidad"].iloc[0]
    assert simb == 1
    assert host == 1


def test_compute_kpis_basic():
    stats = {
        "analysis_results_count": 10,
        "pages_count": 3,
    }
    analysis = [
        {"tiene_violencia": "true", "categoria": "VDG_VIOLENCIA_SIMBOLICA"},
        {"tiene_violencia": "true", "categoria": "VDG_VIOLENCIA_SIMBOLICA"},
        {"tiene_violencia": "false"},
    ]
    kpis = compute_kpis(stats, analysis, {"files": 10, "size_bytes": 100})
    assert kpis["total"] == 10
    assert kpis["violent"] == 2
    assert kpis["violent_pct"] == 20.0
    assert kpis["categories"] == 6
    assert kpis["pages"] == 3
    assert kpis["top_category"] == "Violencia Simbólica"


def test_compute_kpis_no_violence():
    kpis = compute_kpis({"analysis_results_count": 5, "pages_count": 0}, [], {})
    assert kpis["violent"] == 0
    assert kpis["violent_pct"] == 0.0
    assert kpis["top_category"] == "—"


def test_build_pie_chart_returns_altair_chart():
    df = compute_pie_data([{"tiene_violencia": "true"}, {"tiene_violencia": "false"}])
    chart = build_pie_chart(df)
    assert chart is not None
    assert hasattr(chart, "to_dict")


def test_build_bar_chart_returns_altair_chart():
    df = compute_bar_data([{"tiene_violencia": "true", "categoria": "VDG_VIOLENCIA_SIMBOLICA"}])
    chart = build_bar_chart(df)
    assert chart is not None
    assert hasattr(chart, "to_dict")


def test_build_knowledge_zip_returns_bytes():
    data = build_knowledge_zip()
    assert isinstance(data, bytes)
    assert len(data) > 1000


def test_knowledge_zip_contains_all_md_files():
    data = build_knowledge_zip()
    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    md_files = [n for n in names if n.endswith(".md")]
    assert len(md_files) >= 8
    assert any("00-protocolo-algoritmico" in n for n in md_files)
    assert any("01-categoria-1" in n for n in md_files)
    assert any("06-categoria-6" in n for n in md_files)


def test_knowledge_zip_preserves_subdirs():
    data = build_knowledge_zip()
    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    assert any("glosario/" in n for n in names)


def test_knowledge_zip_filename_format():
    name = knowledge_zip_filename()
    assert name.startswith("enola-taxonomia-violencia-")
    assert name.endswith(".zip")
    assert len(name.split("-")) >= 4


def test_knowledge_summary_matches_disk():
    summary = knowledge_summary()
    assert summary["files"] >= 8
    assert summary["size_bytes"] > 0
    assert KNOWLEDGE_DIR.is_dir()


def test_filter_by_content_type_empty():
    assert filter_by_content_type([], "all") == []
    assert filter_by_content_type([], "post") == []
