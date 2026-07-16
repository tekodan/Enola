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

    def test_subdimension_level_returns_up_to_nineteen_rows(self):
        from src.analyzer.category_mapping import SUBDIMENSIONES_ORDENADAS

        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_HOSTILIDAD_FEMINICIDIO",
                dim="3.1",
                labels=[{"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.1"}],
            ),
        ]
        ft = compute_frequency_distribution(rows, level="subdimension")
        assert len(ft.rows) == len(SUBDIMENSIONES_ORDENADAS)
        by_dim = {r.categoria: r for r in ft.rows}
        assert by_dim["1.1"].frecuencia_absoluta == 2
        assert by_dim["3.1"].frecuencia_absoluta == 1
        # Subdimensiones no usadas conservan 0 (incluida 4.4)
        assert by_dim["1.2"].frecuencia_absoluta == 0
        assert by_dim["4.4"].frecuencia_absoluta == 0

    def test_subdimension_level_excluye_basura_del_denominador(self):
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(exclusion_label=EXCLUSION_BASURA_DIGITAL),
            _row(exclusion_label=EXCLUSION_VIOLENCIA_COMUN),
        ]
        ft = compute_frequency_distribution(rows, level="subdimension")
        assert ft.total_validos == 1
        assert ft.n_excluidos == 2

    def test_subdimension_level_acumulado_suma_100(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", dim="3.1"),
            _row("VDG_COSIFICACION_SLUTSHAMING", dim="2.2"),
        ]
        ft = compute_frequency_distribution(rows, level="subdimension")
        last = ft.rows[-1]
        assert abs(last.porcentaje_acumulado - 100.0) < 0.05

    def test_subdimension_level_descendente(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", dim="3.1"),
            _row("VDG_COSIFICACION_SLUTSHAMING", dim="2.2"),
        ]
        ft = compute_frequency_distribution(rows, level="subdimension")
        counts = [r.frecuencia_absoluta for r in ft.rows]
        assert counts == sorted(counts, reverse=True)


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

    def test_subdimension_level_unimodal(self):
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_HOSTILIDAD_FEMINICIDIO",
                dim="3.1",
                labels=[{"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.1"}],
            ),
        ]
        mr = compute_mode(rows, level="subdimension")
        assert mr.modas == ["1.1"]
        assert not mr.es_multimodal
        assert "subdimensión" in mr.texto_descriptivo
        assert "1.1" in mr.texto_descriptivo

    def test_subdimension_level_bimodal(self):
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_VIOLENCIA_SIMBOLICA", dim="1.1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", dim="3.1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", dim="3.1"),
        ]
        mr = compute_mode(rows, level="subdimension")
        assert sorted(mr.modas) == ["1.1", "3.1"]
        assert mr.es_multimodal
        assert "bimodal" in mr.texto_descriptivo
        assert "subdimensiones" in mr.texto_descriptivo


class TestComputeCrosstabs:
    """Regla 4 — Tabulación cruzada (categoría × subdimensión | página | fecha)."""

    def test_subdimension_crosstab(self):
        """``dimension='subdimension'`` always emits canonical 6×18 layout."""
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
        from src.analyzer.category_mapping import (
            CATEGORIAS_ORDENADAS,
            SUBDIMENSIONES_ORDENADAS,
        )

        ct = compute_crosstabs(rows, dimension="subdimension")
        # Layout: las 6 categorías canónicas en orden, las 18
        # subdimensiones canónicas en orden, aunque haya celdas en cero.
        assert ct.filas == CATEGORIAS_ORDENADAS
        assert ct.columnas == SUBDIMENSIONES_ORDENADAS
        # Frecuencias: VDG_VIOLENCIA_SIMBOLICA recibe (1.1)=1, (1.2)=1, resto=0
        sim_idx = ct.filas.index("VDG_VIOLENCIA_SIMBOLICA")
        hos_idx = ct.filas.index("VDG_HOSTILIDAD_FEMINICIDIO")
        assert ct.frecuencias[sim_idx][ct.columnas.index("1.1")] == 1
        assert ct.frecuencias[sim_idx][ct.columnas.index("1.2")] == 1
        assert ct.frecuencias[hos_idx][ct.columnas.index("3.1")] == 1
        # Cells sin observaciones deben valer 0 (no '—' / sin bucket agregado).
        for i, cat in enumerate(ct.filas):
            for j, _dim in enumerate(ct.columnas):
                assert isinstance(ct.frecuencias[i][j], int)
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
        for j, _col in enumerate(ct.columnas):
            col_sum = sum(ct.porcentajes_marginales_columna[i][j] for i in range(len(ct.filas)))
            col_total = sum(ct.frecuencias[i][j] for i in range(len(ct.filas)))
            if col_total > 0:
                assert abs(col_sum - 100.0) < 0.05
            else:
                assert col_sum == 0.0

    def test_alerta_patron_concordancia_genero_subdimension(self):
        """Regla 4 — alerta usa «la subdimensión» (femenino, sin acento)."""
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
        ]
        ct = compute_crosstabs(rows, dimension="subdimension")
        assert ct.alerta_patron is not None
        assert "la subdimensión 1.1" in ct.alerta_patron
        assert "el subdimensión" not in ct.alerta_patron  # bug previo
        assert "el subdimension" not in ct.alerta_patron

    def test_alerta_patron_concordancia_genero_pagina(self):
        """Regla 4 — alerta usa «la página» (femenino)."""
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", post_id="p1"),
            _row("VDG_VIOLENCIA_SIMBOLICA", post_id="p1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", post_id="p2"),
        ]
        posts = [{"id": "p1", "page_id": "pg1"}, {"id": "p2", "page_id": "pg2"}]
        ct = compute_crosstabs(
            rows,
            dimension="pagina",
            posts=posts,
            page_lookup={"pg1": "Página A", "pg2": "Página B"},
        )
        assert ct.alerta_patron is not None
        assert "la página" in ct.alerta_patron
        assert "el página" not in ct.alerta_patron  # bug previo

    def test_alerta_patron_concordancia_genero_fecha(self):
        """Regla 4 — alerta usa «el mes» (masculino, evita 'el fecha')."""
        rows = [
            _row("VDG_VIOLENCIA_SIMBOLICA", post_id="p1"),
            _row("VDG_HOSTILIDAD_FEMINICIDIO", post_id="p2"),
        ]
        posts = [
            {"id": "p1", "date": "2024-03-15T10:00:00"},
            {"id": "p2", "date": "2024-04-20T10:00:00"},
        ]
        ct = compute_crosstabs(rows, dimension="fecha", posts=posts)
        assert ct.alerta_patron is not None
        assert "el mes" in ct.alerta_patron
        assert "el fecha" not in ct.alerta_patron  # bug previo

    def test_alerta_patron_acepta_dimension_con_y_sin_tilde(self):
        """_emitir_alerta_patron normaliza tildes (compat con call sites)."""
        from src.report.stats import _emitir_alerta_patron

        filas = ["VDG_VIOLENCIA_SIMBOLICA"]
        columnas = ["Página X"]
        freqs = [[2]]
        pcts = [[100.0]]
        # Variante con tilde (call site real de ``dimension="pagina"``)
        texto = _emitir_alerta_patron(filas, columnas, freqs, pcts, {}, "página")
        assert texto is not None
        assert "la página Página X" in texto
        assert "el página" not in texto

    # --- Layout canónico 6×18 (Regla 4 · cat × subdim) -----------------

    def test_subdimension_canonical_layout_with_empty_input(self):
        """Sin filas violentas, devuelve 6×19 canónico con ceros."""
        from src.analyzer.category_mapping import (
            CATEGORIAS_ORDENADAS,
            SUBDIMENSIONES_ORDENADAS,
        )

        ct = compute_crosstabs([], dimension="subdimension")
        assert ct.filas == CATEGORIAS_ORDENADAS
        assert ct.columnas == SUBDIMENSIONES_ORDENADAS
        assert len(ct.frecuencias) == 6
        assert all(len(fila) == 19 for fila in ct.frecuencias)
        assert all(v == 0 for fila in ct.frecuencias for v in fila)
        assert all(v == 0.0 for fila in ct.porcentajes_marginales_columna for v in fila)
        assert ct.alerta_patron is None

    def test_subdimension_drops_labels_without_dimension(self):
        """Etiquetas con ``dimension`` vacía/None NO crean bucket '—'."""
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim=None,
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": None}],
            ),
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": ""}],
            ),
        ]
        ct = compute_crosstabs(rows, dimension="subdimension")
        # Columnas nunca incluyen "—"
        assert "—" not in ct.columnas
        assert "" not in ct.columnas
        # Sólo el voto con dim=1.1 cuenta
        sim_idx = ct.filas.index("VDG_VIOLENCIA_SIMBOLICA")
        assert ct.frecuencias[sim_idx][ct.columnas.index("1.1")] == 1
        # Total de frecuencias == 1
        assert sum(sum(fila) for fila in ct.frecuencias) == 1

    def test_subdimension_density_on_realistic_data(self):
        """Con datos multi-label, cada celda que existe suma correctamente."""
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[
                    {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"},
                    {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.2"},
                ],
            ),
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[
                    {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"},
                    {"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.1"},
                ],
            ),
        ]
        ct = compute_crosstabs(rows, dimension="subdimension")
        sim = ct.filas.index("VDG_VIOLENCIA_SIMBOLICA")
        hos = ct.filas.index("VDG_HOSTILIDAD_FEMINICIDIO")
        # Votos: (sim, 1.1)=2, (sim, 1.2)=1, (hos, 3.1)=1
        assert ct.frecuencias[sim][ct.columnas.index("1.1")] == 2
        assert ct.frecuencias[sim][ct.columnas.index("1.2")] == 1
        assert ct.frecuencias[hos][ct.columnas.index("3.1")] == 1
        # El resto 0
        assert ct.frecuencias[sim][ct.columnas.index("3.1")] == 0
        assert ct.frecuencias[hos][ct.columnas.index("1.1")] == 0
        # % marginal columna: para 1.1=100% sim, para 1.2=100% sim, para 3.1=100% hos
        assert abs(ct.porcentajes_marginales_columna[sim][ct.columnas.index("1.1")] - 100.0) < 0.05
        assert abs(ct.porcentajes_marginales_columna[hos][ct.columnas.index("3.1")] - 100.0) < 0.05

    def test_subdimension_zero_density_cell_skipped_in_alerta(self):
        """La alerta del Paso 4.4 ignora celdas con 0 votos (no inflar %)."""
        rows = [
            _row(
                "VDG_VIOLENCIA_SIMBOLICA",
                dim="1.1",
                labels=[{"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"}],
            ),
            _row(
                "VDG_HOSTILIDAD_FEMINICIDIO",
                dim="3.1",
                labels=[{"categoria": "VDG_HOSTILIDAD_FEMINICIDIO", "dimension": "3.1"}],
            ),
        ]
        ct = compute_crosstabs(rows, dimension="subdimension")
        # Hay 2 celdas con 100% — la alerta debe ser una de ellas, no
        # cualquier celda 0%.
        assert ct.alerta_patron is not None
        assert "100.0%" in ct.alerta_patron
