"""Unit tests for the Plotly chart builders.

Covers the new \"tricotómica\" pie: violento / no violento / basura digital.
The previous dicotómica logic silently bundled basura digital into \"Sin
violencia\" — these tests lock in the corrected behaviour.
"""

from __future__ import annotations

from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
)
from src.ui.nicegui_app.components.charts import build_pie_violent_vs_nonviolent


def _row(*, tiene_violencia: str | None = "false", exclusion_label: str | None = None) -> dict:
    return {"tiene_violencia": tiene_violencia, "exclusion_label": exclusion_label}


def _slice_for(fig, label: str) -> float:
    pie = fig.data[0]
    assert pie.type == "pie"
    labels = list(pie.labels)
    values = list(pie.values)
    return float(values[labels.index(label)])


class TestThemePalette:
    """Guardrail: the UI palette must cover **all** 19 canonical
    sub-dimensions (1.1 … 6.3, including 4.4 «Arquetipos femeninos
    deshumanizantes»). Previously 4.4 was missing — the bar chart
    silently fell back to a neutral gray, breaking the visual coherence
    of the cat-4 drill-down."""

    def test_all_nineteen_subdims_have_colors(self):
        from src.ui.nicegui_app import theme

        assert len(theme.SUBDIMENSIONES_ORDENADAS) == 19
        for code in theme.SUBDIMENSIONES_ORDENADAS:
            assert code in theme.SUBDIMENSION_COLORS, f"missing color for {code}"
            # Sanity: hex string
            assert theme.SUBDIMENSION_COLORS[code].startswith("#")

    def test_subdim_44_has_its_own_color(self):
        from src.ui.nicegui_app import theme

        assert "4.4" in theme.SUBDIMENSION_COLORS
        assert "4.4" in theme.SUBDIMENSION_LABELS


class TestBuildPieViolentVsNonviolent:
    def test_splits_basura_digital_into_own_slice(self):
        rows = [
            _row(tiene_violencia="true"),
            _row(tiene_violencia="true"),
            _row(tiene_violencia="false"),
            _row(tiene_violencia="false", exclusion_label=EXCLUSION_BASURA_DIGITAL),
            _row(tiene_violencia="false", exclusion_label=EXCLUSION_BASURA_DIGITAL),
        ]
        fig = build_pie_violent_vs_nonviolent(rows)
        assert _slice_for(fig, "Con violencia") == 2.0
        assert _slice_for(fig, "Sin violencia") == 1.0
        assert _slice_for(fig, "Basura digital (CÓDIGO 99)") == 2.0

    def test_violencia_comun_se_excluye_del_pie(self):
        rows = [
            _row(tiene_violencia="true"),
            _row(tiene_violencia="false", exclusion_label=EXCLUSION_VIOLENCIA_COMUN),
            _row(tiene_violencia="false"),
        ]
        fig = build_pie_violent_vs_nonviolent(rows)
        assert _slice_for(fig, "Con violencia") == 1.0
        assert _slice_for(fig, "Sin violencia") == 1.0  # VIOLENCIA_COMUN excluida
        labels = list(fig.data[0].labels)
        assert "Basura digital (CÓDIGO 99)" not in labels

    def test_unknown_rows_fall_into_sin_clasificar(self):
        rows = [
            _row(tiene_violencia="true"),
            _row(tiene_violencia=None),
            _row(tiene_violencia="unknown"),
        ]
        fig = build_pie_violent_vs_nonviolent(rows)
        assert _slice_for(fig, "Con violencia") == 1.0
        assert _slice_for(fig, "Sin clasificar") == 2.0

    def test_empty_input_returns_figure_with_zero_slices(self):
        fig = build_pie_violent_vs_nonviolent([])
        assert list(fig.data[0].labels) == ["Con violencia", "Sin violencia"]
        assert list(fig.data[0].values) == [0, 0]

    def test_title_mentions_basura_digital(self):
        fig = build_pie_violent_vs_nonviolent(
            [_row(tiene_violencia="true"), _row(exclusion_label=EXCLUSION_BASURA_DIGITAL)]
        )
        title_text = (fig.layout.title.text or "").lower()
        assert "basura" in title_text

    def test_basura_slice_color_is_brass(self):
        from src.ui.nicegui_app import theme

        fig = build_pie_violent_vs_nonviolent(
            [_row(tiene_violencia="false", exclusion_label=EXCLUSION_BASURA_DIGITAL)]
        )
        labels = list(fig.data[0].labels)
        colors = list(fig.data[0].marker.colors)
        idx = labels.index("Basura digital (CÓDIGO 99)")
        assert colors[idx] == theme.BRASS
