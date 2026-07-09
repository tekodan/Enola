"""Unit tests for the descriptive-statistics module (Reglas 2, 3, 4)."""

from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
)
from src.report.stats import (
    compute_crosstabs,
    compute_frequency_distribution,
    compute_mode,
)


def _row(cat: str | None = "ninguna", *, dim: str | None = None, **kw):
    base = {
        "tiene_violencia": "true" if cat and cat != "ninguna" else "false",
        "categoria": cat or "ninguna",
        "dimension": dim,
        "exclusion_label": None,
    }
    base.update(kw)
    return base


class TestComputeFrequencyDistribution:
    """Regla 2 — 4 columnas con % válido (excluye missing) y % acumulado."""

    def test_empty_input_returns_zero(self):
        ft = compute_frequency_distribution([])
        assert ft.total_validos == 0
        assert ft.n_excluidos == 0
        assert all(r.frecuencia_absoluta == 0 for r in ft.rows)

    def test_basic_counts(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
        ]
        ft = compute_frequency_distribution(rows)
        assert ft.total_validos == 3
        by_cat = {r.categoria: r for r in ft.rows}
        assert by_cat["VDG_VIOLENCIA_SIMBOLICA"].frecuencia_absoluta == 2
        assert by_cat["VDG_HOSTILIDAD_FEMINICIDIO"].frecuencia_absoluta == 1

    def test_excludes_basura_and_comun_from_denominator(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
            _row(exclusion_label=EXCLUSION_BASURA_DIGITAL),
            _row(exclusion_label=EXCLUSION_VIOLENCIA_COMUN),
        ]
        ft = compute_frequency_distribution(rows)
        assert ft.total_validos == 2  # basura + comun excluded
        assert ft.n_excluidos == 2

    def test_four_columns_exact(self):
        rows = [_row("VDG_VIOLENCIA_SIMBOLICA"), _row("VDG_VIOLENCIA_SIMBOLICA")]
        ft = compute_frequency_distribution(rows)
        df = ft.to_dataframe()
        assert list(df.columns) == [
            "Categoría",
            "Código",
            "Frecuencia Absoluta",
            "Porcentaje Válido",
            "Porcentaje Acumulado",
        ]

    def test_porcentaje_acumulado_sums_to_100(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
            _row("VDG_COSIFICACION_SLUTSHAMING"),
        ]
        ft = compute_frequency_distribution(rows)
        last = ft.rows[-1]
        # Floating-point rounding may give 99.99 or 100.01
        assert abs(last.porcentaje_acumulado - 100.0) < 0.05

    def test_descending_order(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
            _row("VDG_COSIFICACION_SLUTSHAMING"),
        ]
        ft = compute_frequency_distribution(rows)
        counts = [r.frecuencia_absoluta for r in ft.rows]
        assert counts == sorted(counts, reverse=True)

    def test_multi_label_per_row(self):
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                labels=[
                    {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"},
                    {"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.1"},
                ],
            )
        ]
        ft = compute_frequency_distribution(rows)
        # Two votes from one row
        assert ft.total_validos == 2


class TestComputeMode:
    """Regla 3 — Moda, bimodalidad, texto automatizado."""

    def test_unimodal(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
        ]
        mr = compute_mode(rows)
        assert mr.modas == ["VDG_VIOLENCIA_SIMBOLICA"]
        assert not mr.es_multimodal
        assert "MODA" in mr.texto_descriptivo
        assert "Violencia Simbólica" in mr.texto_descriptivo

    def test_bimodal(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
        ]
        mr = compute_mode(rows)
        assert len(mr.modas) == 2
        assert mr.es_multimodal
        assert "bimodal" in mr.texto_descriptivo
        assert "y" in mr.texto_descriptivo  # both categories named

    def test_multimodal_three(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO"),
            _row("VDG_COSIFICACION_SLUTSHAMING"),
        ]
        mr = compute_mode(rows)
        assert len(mr.modas) == 3
        assert mr.es_multimodal
        assert "multimodal" in mr.texto_descriptivo

    def test_empty_returns_message(self):
        mr = compute_mode([])
        assert mr.modas == []
        assert "no se puede calcular" in mr.texto_descriptivo.lower()

    def test_excludes_codigo_99(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA"),
            _row(exclusion_label=EXCLUSION_BASURA_DIGITAL),
            _row(exclusion_label=EXCLUSION_BASURA_DIGITAL),
            _row(exclusion_label=EXCLUSION_BASURA_DIGITAL),
        ]
        mr = compute_mode(rows)
        assert mr.modas == ["VDG_VIOLENCIA_SIMBOLICA"]


class TestComputeCrosstabs:
    """Regla 4 — Tabulación cruzada (categoría × subdimensión | página | fecha)."""

    def test_subdimension_crosstab(self):
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.2",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.2"}],
            ),
            _row(
                "VDG_HOSTILIDAD_FEMINICIDIO",
                dim="3.1",
                labels=[{"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.1"}],
            ),
        ]
        ct = compute_crosstabs(rows, dimension="subdimension")
        assert ct.filas == ["VDG_VIOLENCIA_SIMBOLICA", "VDG_HOSTILIDAD_FEMINICIDIO"]
        assert set(ct.columnas) == {"1.1", "1.2", "3.1"}
        # row totals
        assert sum(ct.frecuencias[0]) == 2
        assert sum(ct.frecuencias[1]) == 1
        assert ct.alerta_patron is not None

    def test_pagina_crosstab(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", post_id="p1"),
            _row("VDG_VIOLENCIA_SIMBOLICA", post_id="p1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", post_id="p2"),
        ]
        posts = [
            {"id": "p1", "page_id": "pg1"},
            {"id": "p2", "page_id": "pg2"},
        ]
        page_lookup = {"pg1": "Página A", "pg2": "Página B"}
        ct = compute_crosstabs(
            rows,
            dimension="pagina",
            posts=posts,
            page_lookup=page_lookup,
        )
        assert set(ct.columnas) == {"Página A", "Página B"}
        # cell Página A × VDG_VIOLENCIA_SIMBOLICA should be 2
        idx = ct.filas.index("VDG_VIOLENCIA_SIMBOLICA")
        col_idx = ct.columnas.index("Página A")
        assert ct.frecuencias[idx][col_idx] == 2

    def test_fecha_crosstab(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", post_id="p1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", post_id="p2"),
        ]
        posts = [
            {"id": "p1", "date": "2024-03-15T10:00:00"},
            {"id": "p2", "date": "2024-04-20T10:00:00"},
        ]
        ct = compute_crosstabs(rows, dimension="fecha", posts=posts)
        assert set(ct.columnas) == {"2024-03", "2024-04"}

    def test_excludes_codigo_99_from_cells(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row(exclusion_label=EXCLUSION_BASURA_DIGITAL),
        ]
        ct = compute_crosstabs(rows, dimension="subdimension")
        total = sum(sum(fila) for fila in ct.frecuencias)
        assert total == 1  # basura row did not contribute

    def test_invalid_dimension_raises(self):
        import pytest

        with pytest.raises(ValueError):
            compute_crosstabs([], dimension="bogus")

    def test_marginales_suma_100_por_columna(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", dim="3.1"),
        ]
        ct = compute_crosstabs(rows, dimension="subdimension")
        for j, col in enumerate(ct.columnas):
            col_sum = sum(ct.porcentajes_marginales_columna[i][j] for i in range(len(ct.filas)))
            if ct.frecuencias[0][j] + ct.frecuencias[1][j] > 0:
                assert abs(col_sum - 100.0) < 0.05
