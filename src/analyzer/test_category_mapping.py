"""Unit tests for category_mapping — the canonical taxonomy."""

import logging

from src.analyzer.category_mapping import (
    CATEGORIAS_ORDENADAS,
    DESCRIPCION_SUBDIMENSION,
    KNOWLEDGE_ROOT,
    SUBDIMENSIONES_POR_CATEGORIA,
    Categoria,
    load_prompt_block,
    map_gravedad,
    normalize_categoria,
    normalize_dimension,
    render_severidad_prompt,
    render_tabla_canonica_prompt,
    validate_codigo,
)
from src.analyzer.violence_types import Severity


class TestCategoriaEnum:
    """Tests for the Categoria enum (6 valid alphabetic codes)."""

    def test_six_canonical_codes(self):
        """The enum has exactly 7 values (6 categories + NINGUNA)."""
        assert len(list(Categoria)) == 7

    def test_canonical_values(self):
        """The 6 expected alphabetic codes exist."""
        assert Categoria.VDG_VIOLENCIA_SIMBOLICA.value == "VDG_VIOLENCIA_SIMBOLICA"
        assert Categoria.VDG_COSIFICACION_SLUTSHAMING.value == "VDG_COSIFICACION_SLUTSHAMING"
        assert Categoria.VDG_HOSTILIDAD_FEMINICIDIO.value == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert Categoria.VDG_MANOSFERA_ANTIFEMINISMO.value == "VDG_MANOSFERA_ANTIFEMINISMO"
        assert Categoria.VDG_SALVAGUARDA_FALSO_POSITIVO.value == "VDG_SALVAGUARDA_FALSO_POSITIVO"
        assert Categoria.VDG_DESACREDITACION_ACTIVISTAS.value == "VDG_DESACREDITACION_ACTIVISTAS"
        assert Categoria.NINGUNA.value == "ninguna"

    def test_ordered_list_matches_enum(self):
        """CATEGORIAS_ORDENADAS excludes NINGUNA and matches the 6 cats."""
        assert len(CATEGORIAS_ORDENADAS) == 6
        assert Categoria.NINGUNA.value not in CATEGORIAS_ORDENADAS


class TestSubdimensionCoverage:
    """Tests for the 18 valid sub-dimension codes."""

    def test_three_dims_per_category(self):
        """Every category (except NINGUNA) has exactly 3 sub-dimensions."""
        for cat in CATEGORIAS_ORDENADAS:
            assert len(SUBDIMENSIONES_POR_CATEGORIA[cat]) == 3

    def test_eighteen_total_combinations(self):
        """6 cats × 3 dims = 18 valid combinations."""
        total = sum(len(dims) for dims in SUBDIMENSIONES_POR_CATEGORIA.values())
        assert total == 18

    def test_dims_match_category_number(self):
        """Sub-dimension N.M must match category N (1.1, 1.2, 1.3 for cat 1).

        The category code is alphabetic (``VDG_VIOLENCIA_SIMBOLICA``)
        while the sub-dimension is numeric (``1.1``). The numeric
        prefix of the sub-dimension is what the LLM uses; we just
        verify the N is in the range 1-6 and that the M is 1, 2 or 3.
        """
        for cat in CATEGORIAS_ORDENADAS:
            for dim in SUBDIMENSIONES_POR_CATEGORIA[cat]:
                n_str, m_str = dim.split(".")
                assert 1 <= int(n_str) <= 6
                assert 1 <= int(m_str) <= 3
            # The category index in CATEGORIAS_ORDENADAS should match N
            idx = CATEGORIAS_ORDENADAS.index(cat) + 1
            for dim in SUBDIMENSIONES_POR_CATEGORIA[cat]:
                assert dim.startswith(f"{idx}.")

    def test_dims_covered_in_descriptions(self):
        """Every sub-dimension code has a description."""
        for cat, dims in SUBDIMENSIONES_POR_CATEGORIA.items():
            for dim in dims:
                assert dim in DESCRIPCION_SUBDIMENSION, f"Missing description for {cat} / {dim}"


class TestNormalizeCategoria:
    """Tests for normalize_categoria — accepts free-form input."""

    def test_canonical_passes_through(self):
        assert normalize_categoria("VDG_VIOLENCIA_SIMBOLICA") == "VDG_VIOLENCIA_SIMBOLICA"
        assert normalize_categoria("ninguna") == "ninguna"

    def test_lowercase_variants_normalize(self):
        assert normalize_categoria("violencia simbolica") == "VDG_VIOLENCIA_SIMBOLICA"
        assert normalize_categoria("Violencia Simbólica") == "VDG_VIOLENCIA_SIMBOLICA"
        assert normalize_categoria("violencia-simbólica") == "VDG_VIOLENCIA_SIMBOLICA"

    def test_unknown_returns_ninguna(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = normalize_categoria("categoria inventada")
        assert result == "ninguna"
        assert "fuera del set canónico" in caplog.text

    def test_empty_returns_ninguna(self):
        assert normalize_categoria("") == "ninguna"
        assert normalize_categoria(None) == "ninguna"


class TestNormalizeDimension:
    """Tests for normalize_dimension — validates against category."""

    def test_valid_dim_passes(self):
        assert normalize_dimension("VDG_VIOLENCIA_SIMBOLICA", "1.1") == "1.1"
        assert normalize_dimension("VDG_HOSTILIDAD_FEMINICIDIO", "3.3") == "3.3"

    def test_invalid_dim_for_category_returns_none(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = normalize_dimension("VDG_VIOLENCIA_SIMBOLICA", "5.1")
        assert result is None
        assert "dimensión inválida" in caplog.text

    def test_empty_dim_returns_none(self):
        assert normalize_dimension("VDG_VIOLENCIA_SIMBOLICA", None) is None
        assert normalize_dimension("VDG_VIOLENCIA_SIMBOLICA", "") is None

    def test_ninguna_categoria_returns_none(self):
        assert normalize_dimension("ninguna", "1.1") is None


class TestValidateCodigo:
    """Tests for the canonical validate_codigo() function."""

    def test_valid_combination(self):
        cat, dim = validate_codigo("VDG_COSIFICACION_SLUTSHAMING", "2.2")
        assert cat == "VDG_COSIFICACION_SLUTSHAMING"
        assert dim == "2.2"

    def test_invalid_categoria_normalized(self):
        cat, dim = validate_codigo("feminicidio", "3.1")
        assert cat == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert dim == "3.1"

    def test_invalid_dimension_normalized(self):
        cat, dim = validate_codigo("VDG_VIOLENCIA_SIMBOLICA", "9.9")
        assert cat == "VDG_VIOLENCIA_SIMBOLICA"
        assert dim is None

    def test_ninguna_passes_through(self):
        cat, dim = validate_codigo("ninguna", "1.1")
        assert cat == "ninguna"
        assert dim is None


class TestMapGravedad:
    """Tests for severity mapping (compound → closed enum)."""

    def test_compound_to_closed(self):
        assert map_gravedad("baja-media") == Severity.BAJA
        assert map_gravedad("media-alta") == Severity.MEDIA
        assert map_gravedad("alta-extrema") == Severity.ALTA

    def test_simple_values(self):
        assert map_gravedad("baja") == Severity.BAJA
        assert map_gravedad("media") == Severity.MEDIA
        assert map_gravedad("alta") == Severity.ALTA
        assert map_gravedad("extrema") == Severity.ALTA
        assert map_gravedad("ninguna") == Severity.NINGUNA

    def test_empty_or_invalid(self):
        assert map_gravedad("") == Severity.NINGUNA
        assert map_gravedad(None) == Severity.NINGUNA
        # "nada" doesn't contain alta/media/baja → NINGUNA + warning
        assert map_gravedad("nada") == Severity.NINGUNA


class TestRenderTabla:
    """Tests for the prompt-table renderer."""

    def test_renders_18_rows(self):
        table = render_tabla_canonica_prompt()
        # Count the data rows (lines starting with "| " that have a category or dimension)
        rows = [
            line
            for line in table.split("\n")
            if line.startswith("|") and "categoria" not in line and "---" not in line
        ]
        assert len(rows) == 18

    def test_includes_all_canonical_codes(self):
        table = render_tabla_canonica_prompt()
        for cat in CATEGORIAS_ORDENADAS:
            assert cat in table

    def test_includes_all_subdimensions(self):
        table = render_tabla_canonica_prompt()
        for dims in SUBDIMENSIONES_POR_CATEGORIA.values():
            for d in dims:
                assert d in table

    def test_mentions_ninguna(self):
        table = render_tabla_canonica_prompt()
        assert "ninguna" in table


class TestRenderSeveridad:
    def test_renders_severity_legend(self):
        text = render_severidad_prompt()
        assert '"baja"' in text
        assert '"media"' in text
        assert '"alta"' in text
        assert '"ninguna"' in text


class TestLoadPromptBlock:
    """Loads rule blocks from markdown glosarios."""

    def test_loads_marcadores_block(self):
        block = load_prompt_block("glosario/marcadores-por-subdimension.md")
        assert "MARCADORES_CANONICOS" in block
        assert "a lavar" in block
        assert "1.1 (VDG_VIOLENCIA_SIMBOLICA)" in block
        assert "aliade" in block

    def test_loads_leetspeak_block(self):
        block = load_prompt_block("glosario/leetspeak-decoder.md")
        assert "DESCODIFICACIÓN" in block
        assert "f3m1 nizta → feminazi" in block
        assert "aliade → aliado" in block

    def test_loads_mitigadores_block(self):
        block = load_prompt_block("glosario/marcadores-mitigadores.md")
        assert "MARCADORES_MITIGADORES" in block
        assert "patriarcal" in block
        assert "#NiUnaMenos" in block

    def test_loads_referentes_block(self):
        block = load_prompt_block("glosario/referentes-femeninos.md")
        assert "REGLA DE COOCURRENCIA" in block
        assert "mujer" in block
        assert "stacy" in block

    def test_loads_cat5_block_from_categoria_5_md(self):
        block = load_prompt_block("05-categoria-5-sarcasmo-falsos-positivos.md")
        assert "USO DE Cat. 5" in block
        assert "5.3 reapropiación" in block

    def test_returns_empty_for_missing_file(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = load_prompt_block("glosario/no-existe.md")
        assert result == ""

    def test_returns_empty_for_missing_anchor(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = load_prompt_block(
                "glosario/leetspeak-decoder.md",
                anchor="No Existe",
            )
        assert result == ""

    def test_knowledge_root_points_to_markdowns(self):
        assert (KNOWLEDGE_ROOT / "glosario" / "leetspeak-decoder.md").is_file()
        assert (KNOWLEDGE_ROOT / "00-protocolo-algoritmico.md").is_file()
