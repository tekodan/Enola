"""Unit tests for ``taxonomy_loader``.

Covers:
- Frontmatter parsing (valid + error cases).
- Pydantic invariants (counts, codes, gravedad).
- Derived structures (ordered_codes, subdims_by_category, etc.).
- Loader caching (singleton + reload).
- The real ``knowledge/taxonomia/TAXONOMIA.md`` parses cleanly.
"""

from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from src.analyzer.taxonomy_loader import (
    DEFAULT_TAXONOMY_PATH,
    GRAVEDAD_TOKENS,
    CategoriaMD,
    ExclusionCategoriaMD,
    SubdimensionMD,
    Taxonomy,
    TaxonomyFormatError,
    get_taxonomy,
    load_taxonomy,
    load_taxonomy_from_string,
    reload_taxonomy,
    reset_cache,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_md() -> str:
    return textwrap.dedent(
        """\
        ---
        version: "1.0.0"
        schema: "taxonomia-v1"
        descripcion: "Test taxonomy"
        categorias:
          - code: VDG_VIOLENCIA_SIMBOLICA
            orden: 1
            gravedad: "baja-media"
            subdimensiones:
              - code: "1.1"
                descripcion: "Roles tradicionales y de sumisión"
              - code: "1.2"
                descripcion: "Incompetencia atribuida"
              - code: "1.3"
                descripcion: "Doble estándar moral"
          - code: VDG_COSIFICACION_SLUTSHAMING
            orden: 2
            gravedad: "media"
            subdimensiones:
              - code: "2.1"
                descripcion: "Cosificación corporal"
              - code: "2.2"
                descripcion: "Slut-shaming"
              - code: "2.3"
                descripcion: "Doble estándar sexual"
          - code: VDG_HOSTILIDAD_FEMINICIDIO
            orden: 3
            gravedad: "alta-extrema"
            subdimensiones:
              - code: "3.1"
                descripcion: "Amenaza explícita"
              - code: "3.2"
                descripcion: "Léxico letal mutado"
              - code: "3.3"
                descripcion: "Apología al feminicidio"
          - code: VDG_MANOSFERA_ANTIFEMINISMO
            orden: 4
            gravedad: "media-alta"
            subdimensiones:
              - code: "4.1"
                descripcion: "Subculturas masculinistas"
              - code: "4.2"
                descripcion: "Desinformación de género"
              - code: "4.3"
                descripcion: "Troleo de género"
          - code: VDG_SALVAGUARDA_FALSO_POSITIVO
            orden: 5
            gravedad: "ortogonal"
            subdimensiones:
              - code: "5.1"
                descripcion: "Sarcasmo agresivo"
              - code: "5.2"
                descripcion: "Humor hostil"
              - code: "5.3"
                descripcion: "Reapropiación"
          - code: VDG_DESACREDITACION_ACTIVISTAS
            orden: 6
            gravedad: "media-alta"
            subdimensiones:
              - code: "6.1"
                descripcion: "Deslegitimación ideológica"
              - code: "6.2"
                descripcion: "Ataque a activista"
              - code: "6.3"
                descripcion: "Tergiversación"
        ---
        """
    )


@pytest.fixture
def valid_md_text() -> str:
    return _valid_md()


def _md_with_exclusions(exclusions_block: str = "") -> str:
    """Build a valid 6-category taxonomy with a ``categorias_exclusion`` block.

    ``exclusions_block`` defaults to the two canonical entries
    (``EXC_BASURA_DIGITAL``, ``EXC_VIOLENCIA_COMUN``).
    """
    if not exclusions_block:
        exclusions_block = textwrap.dedent(
            """\
            categorias_exclusion:
              - code: EXC_BASURA_DIGITAL
                codigo_canonico: CODIGO_99
                descripcion: "Basura digital preclasificatoria"
              - code: EXC_VIOLENCIA_COMUN
                codigo_canonico: VIOLENCIA_COMUN
                descripcion: "Agresion sin sesgo de genero"
            """
        ).rstrip()
    base = textwrap.dedent(
        """\
        ---
        version: "1.0.0"
        schema: "taxonomia-v1"
        descripcion: "Test taxonomy"
        categorias:
          - code: VDG_VIOLENCIA_SIMBOLICA
            orden: 1
            gravedad: "baja-media"
            subdimensiones:
              - code: "1.1"
                descripcion: "Roles tradicionales"
              - code: "1.2"
                descripcion: "Incompetencia"
              - code: "1.3"
                descripcion: "Doble estandar moral"
          - code: VDG_COSIFICACION_SLUTSHAMING
            orden: 2
            gravedad: "media"
            subdimensiones:
              - code: "2.1"
                descripcion: "Cosificacion"
              - code: "2.2"
                descripcion: "Slut-shaming"
              - code: "2.3"
                descripcion: "Doble estandar sexual"
          - code: VDG_HOSTILIDAD_FEMINICIDIO
            orden: 3
            gravedad: "alta-extrema"
            subdimensiones:
              - code: "3.1"
                descripcion: "Amenaza"
              - code: "3.2"
                descripcion: "Lexico letal"
              - code: "3.3"
                descripcion: "Apologia"
          - code: VDG_MANOSFERA_ANTIFEMINISMO
            orden: 4
            gravedad: "media-alta"
            subdimensiones:
              - code: "4.1"
                descripcion: "Subculturas"
              - code: "4.2"
                descripcion: "Desinformacion"
              - code: "4.3"
                descripcion: "Troleo"
          - code: VDG_SALVAGUARDA_FALSO_POSITIVO
            orden: 5
            gravedad: "ortogonal"
            subdimensiones:
              - code: "5.1"
                descripcion: "Sarcasmo"
              - code: "5.2"
                descripcion: "Humor hostil"
              - code: "5.3"
                descripcion: "Reapropiacion"
          - code: VDG_DESACREDITACION_ACTIVISTAS
            orden: 6
            gravedad: "media-alta"
            subdimensiones:
              - code: "6.1"
                descripcion: "Deslegitimacion"
              - code: "6.2"
                descripcion: "Ataque a activista"
              - code: "6.3"
                descripcion: "Tergiversacion"
        """
    )
    return base + exclusions_block + "\n---\n"


@pytest.fixture
def md_with_exclusions() -> str:
    return _md_with_exclusions()


@pytest.fixture(autouse=True)
def _drop_cache():
    reset_cache()
    yield
    reset_cache()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestLoadValidTaxonomy:
    def test_parses_six_categories(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        assert len(tx.categorias) == 6

    def test_version_and_schema(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        assert tx.version == "1.0.0"
        assert tx.schema_version == "taxonomia-v1"

    def test_each_category_has_three_subdimensions(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        for cat in tx.categorias:
            assert len(cat.subdimensiones) == 3, cat.code

    def test_ordered_codes_match_input_order(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        assert tx.ordered_codes() == [
            "VDG_VIOLENCIA_SIMBOLICA",
            "VDG_COSIFICACION_SLUTSHAMING",
            "VDG_HOSTILIDAD_FEMINICIDIO",
            "VDG_MANOSFERA_ANTIFEMINISMO",
            "VDG_SALVAGUARDA_FALSO_POSITIVO",
            "VDG_DESACREDITACION_ACTIVISTAS",
        ]

    def test_subdims_by_category_keys(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        subdims = tx.subdims_by_category()
        assert set(subdims.keys()) == set(tx.ordered_codes())
        for cat, dims in subdims.items():
            assert len(dims) == 3

    def test_gravedad_por_categoria(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        gp = tx.gravedad_por_categoria()
        assert gp["VDG_VIOLENCIA_SIMBOLICA"] == "baja-media"
        assert gp["VDG_SALVAGUARDA_FALSO_POSITIVO"] == "ortogonal"

    def test_ordered_subdimensions_has_18_items(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        out = tx.ordered_subdimensions()
        assert len(out) == 18
        assert out[0] == "1.1"
        assert out[-1] == "6.3"

    def test_categoria_por_subdimension_inverse(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        inv = tx.categoria_por_subdimension()
        assert inv["1.1"] == "VDG_VIOLENCIA_SIMBOLICA"
        assert inv["6.3"] == "VDG_DESACREDITACION_ACTIVISTAS"
        assert len(inv) == 18

    def test_descripcion_subdim(self, valid_md_text: str) -> None:
        tx = load_taxonomy_from_string(valid_md_text)
        descs = tx.descripcion_subdim()
        assert "Roles tradicionales" in descs["1.1"]
        assert "feminicidio" in descs["3.3"].lower()


# ---------------------------------------------------------------------------
# Loader behavior
# ---------------------------------------------------------------------------


class TestLoaderFromDisk:
    def test_real_md_parses(self) -> None:
        """The committed TAXONOMIA.md must parse cleanly and have 6 cats."""
        if not DEFAULT_TAXONOMY_PATH.exists():
            pytest.skip(f"Real TAXONOMIA.md not found at {DEFAULT_TAXONOMY_PATH}")
        tx = load_taxonomy()
        assert len(tx.categorias) == 6
        assert len(tx.ordered_subdimensions()) == 18

    def test_default_path_resolves(self) -> None:
        """DEFAULT_TAXONOMY_PATH must point inside the project tree."""
        assert DEFAULT_TAXONOMY_PATH.name == "TAXONOMIA.md"
        assert DEFAULT_TAXONOMY_PATH.parent.name == "taxonomia"

    def test_load_taxonomy_caches_via_get_taxonomy(self, valid_md_text: str, tmp_path) -> None:
        target = tmp_path / "TAX.md"
        target.write_text(valid_md_text, encoding="utf-8")
        # Populate the cache via reload (explicit path).
        cached = reload_taxonomy(target)
        # Subsequent get_taxonomy() returns the cached instance.
        assert get_taxonomy() is cached


class TestCache:
    def test_get_taxonomy_returns_same_object_after_reload(
        self, valid_md_text: str, tmp_path
    ) -> None:
        target = tmp_path / "TAX.md"
        target.write_text(valid_md_text, encoding="utf-8")
        reload_taxonomy(target)
        first = get_taxonomy()
        second = get_taxonomy()
        assert first is second

    def test_reload_replaces_cache_with_new_instance(self, valid_md_text: str, tmp_path) -> None:
        target = tmp_path / "TAX.md"
        target.write_text(valid_md_text, encoding="utf-8")
        first = reload_taxonomy(target)
        second = reload_taxonomy(target)
        # Two reloads produce different model instances but the cache holds
        # the latest one.
        assert first is not second
        assert get_taxonomy() is second

    def test_reset_cache_forces_reload(self, valid_md_text: str, tmp_path) -> None:
        target = tmp_path / "TAX.md"
        target.write_text(valid_md_text, encoding="utf-8")
        first = load_taxonomy(target)
        reset_cache()
        second = load_taxonomy(target)
        assert first.model_dump() == second.model_dump()


# ---------------------------------------------------------------------------
# Error cases — frontmatter format
# ---------------------------------------------------------------------------


class TestFrontmatterFormatErrors:
    def test_no_frontmatter_block_raises(self) -> None:
        with pytest.raises(TaxonomyFormatError, match="YAML frontmatter"):
            load_taxonomy_from_string("no frontmatter here\n")

    def test_empty_body_with_only_frontmatter_ok(self) -> None:
        text = "---\nversion: x\nschema: y\n---\n"
        with pytest.raises(ValidationError):
            load_taxonomy_from_string(text)

    def test_top_level_indented_key_raises(self) -> None:
        md = "---\n  indented_key: x\n---\n"
        with pytest.raises(TaxonomyFormatError):
            load_taxonomy_from_string(md)

    def test_missing_colon_raises(self) -> None:
        md = "---\nversion x\nschema: y\n---\n"
        with pytest.raises(TaxonomyFormatError):
            load_taxonomy_from_string(md)

    def test_key_without_value_block_raises(self) -> None:
        md = "---\nkey_with_no_value:\n---\n"
        with pytest.raises(TaxonomyFormatError, match="no value"):
            load_taxonomy_from_string(md)


# ---------------------------------------------------------------------------
# Error cases — Pydantic invariants
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_wrong_category_count_rejected(self) -> None:
        md = textwrap.dedent(
            """\
            ---
            version: "1.0.0"
            schema: "taxonomia-v1"
            categorias:
              - code: VDG_VIOLENCIA_SIMBOLICA
                orden: 1
                gravedad: "baja-media"
                subdimensiones:
                  - code: "1.1"
                    descripcion: "x"
                  - code: "1.2"
                    descripcion: "y"
                  - code: "1.3"
                    descripcion: "z"
            ---
            """
        )
        with pytest.raises(ValidationError, match="exactly 6 categories"):
            load_taxonomy_from_string(md)

    def test_wrong_orden_rejected(self) -> None:
        md = textwrap.dedent(
            """\
            ---
            version: "1.0.0"
            schema: "taxonomia-v1"
            categorias:
              - code: VDG_VIOLENCIA_SIMBOLICA
                orden: 2
                gravedad: "baja-media"
                subdimensiones:
                  - code: "1.1"
                    descripcion: "x"
                  - code: "2.2"
                    descripcion: "y"
                  - code: "2.3"
                    descripcion: "z"
              - code: VDG_COSIFICACION_SLUTSHAMING
                orden: 1
                gravedad: "media"
                subdimensiones:
                  - code: "2.1"
                    descripcion: "x"
                  - code: "2.2"
                    descripcion: "y"
                  - code: "2.3"
                    descripcion: "z"
            ---
            """
        )
        with pytest.raises(ValidationError):
            load_taxonomy_from_string(md)

    def test_duplicate_category_code_rejected(self) -> None:
        md = textwrap.dedent(
            """\
            ---
            version: "1.0.0"
            schema: "taxonomia-v1"
            categorias:
              - code: VDG_VIOLENCIA_SIMBOLICA
                orden: 1
                gravedad: "baja-media"
                subdimensiones:
                  - code: "1.1"
                    descripcion: "x"
                  - code: "1.2"
                    descripcion: "y"
                  - code: "1.3"
                    descripcion: "z"
              - code: VDG_VIOLENCIA_SIMBOLICA
                orden: 2
                gravedad: "media"
                subdimensiones:
                  - code: "2.1"
                    descripcion: "x"
                  - code: "2.2"
                    descripcion: "y"
                  - code: "2.3"
                    descripcion: "z"
            ---
            """
        )
        with pytest.raises(ValidationError):
            load_taxonomy_from_string(md)

    def test_subdim_must_have_three_entries(self) -> None:
        # 2 entries → rejected by length validator
        with pytest.raises(ValidationError, match="exactly 3"):
            CategoriaMD.model_validate(
                {
                    "code": "VDG_X",
                    "orden": 1,
                    "gravedad": "media",
                    "subdimensiones": [
                        {"code": "1.1", "descripcion": "a"},
                        {"code": "1.2", "descripcion": "b"},
                    ],
                }
            )
        # 3 entries → accepted
        cat = CategoriaMD.model_validate(
            {
                "code": "VDG_X",
                "orden": 1,
                "gravedad": "media",
                "subdimensiones": [
                    {"code": "1.1", "descripcion": "a"},
                    {"code": "1.2", "descripcion": "b"},
                    {"code": "1.3", "descripcion": "c"},
                ],
            }
        )
        assert len(cat.subdimensiones) == 3

    def test_gravedad_must_be_in_closed_set(self) -> None:
        with pytest.raises(ValidationError):
            CategoriaMD.model_validate(
                {
                    "code": "VDG_X",
                    "orden": 1,
                    "gravedad": "super-mega",
                    "subdimensiones": [
                        {"code": "1.1", "descripcion": "a"},
                        {"code": "1.2", "descripcion": "b"},
                        {"code": "1.3", "descripcion": "c"},
                    ],
                }
            )

    def test_gravedad_set_includes_known_tokens(self) -> None:
        assert "baja" in GRAVEDAD_TOKENS
        assert "baja-media" in GRAVEDAD_TOKENS
        assert "media-alta" in GRAVEDAD_TOKENS
        assert "alta-extrema" in GRAVEDAD_TOKENS
        assert "ortogonal" in GRAVEDAD_TOKENS

    def test_category_code_must_start_with_vdg(self) -> None:
        with pytest.raises(ValidationError):
            CategoriaMD.model_validate(
                {
                    "code": "OTRA_COSA",
                    "orden": 1,
                    "gravedad": "media",
                    "subdimensiones": [
                        {"code": "1.1", "descripcion": "a"},
                        {"code": "1.2", "descripcion": "b"},
                        {"code": "1.3", "descripcion": "c"},
                    ],
                }
            )

    def test_subdim_code_pattern_enforced(self) -> None:
        with pytest.raises(ValidationError):
            SubdimensionMD.model_validate({"code": "7.1", "descripcion": "x"})
        with pytest.raises(ValidationError):
            SubdimensionMD.model_validate({"code": "1.4", "descripcion": "x"})
        with pytest.raises(ValidationError):
            SubdimensionMD.model_validate({"code": "x.y", "descripcion": "x"})

    def test_subdim_descripcion_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            SubdimensionMD.model_validate({"code": "1.1", "descripcion": "   "})

    def test_categoria_orden_must_be_in_range(self) -> None:
        with pytest.raises(ValidationError):
            CategoriaMD.model_validate(
                {
                    "code": "VDG_X",
                    "orden": 0,
                    "gravedad": "media",
                    "subdimensiones": [
                        {"code": "1.1", "descripcion": "a"},
                        {"code": "1.2", "descripcion": "b"},
                        {"code": "1.3", "descripcion": "c"},
                    ],
                }
            )
        with pytest.raises(ValidationError):
            CategoriaMD.model_validate(
                {
                    "code": "VDG_X",
                    "orden": 7,
                    "gravedad": "media",
                    "subdimensiones": [
                        {"code": "1.1", "descripcion": "a"},
                        {"code": "1.2", "descripcion": "b"},
                        {"code": "1.3", "descripcion": "c"},
                    ],
                }
            )


# ---------------------------------------------------------------------------
# Direct model access
# ---------------------------------------------------------------------------


class TestTaxonomyModel:
    def test_taxonomy_construction_from_dict(self) -> None:
        tx = Taxonomy.model_validate(
            {
                "version": "2.0",
                "schema": "taxonomia-v2",
                "categorias": [
                    {
                        "code": f"VDG_X_{i}",
                        "orden": i + 1,
                        "gravedad": "media",
                        "subdimensiones": [
                            {"code": f"{i + 1}.1", "descripcion": "x"},
                            {"code": f"{i + 1}.2", "descripcion": "x"},
                            {"code": f"{i + 1}.3", "descripcion": "x"},
                        ],
                    }
                    for i in range(6)
                ],
            }
        )
        assert tx.version == "2.0"
        assert tx.schema_version == "taxonomia-v2"


# ---------------------------------------------------------------------------
# Categorías de exclusión (categorias_exclusion)
# ---------------------------------------------------------------------------


class TestCategoriasExclusion:
    """The ``categorias_exclusion`` block documents the pre-classification
    pseudo-categories (``CODIGO_99`` / ``VIOLENCIA_COMUN``). They live
    outside the closed 6-category invariant but still go through a
    Pydantic validator.
    """

    def test_default_md_parses_with_two_exclusions(self, md_with_exclusions: str) -> None:
        """A taxonomy MD with the canonical exclusions block parses."""
        tx = load_taxonomy_from_string(md_with_exclusions)
        assert len(tx.categorias) == 6
        assert len(tx.categorias_exclusion) == 2

    def test_exclusion_codes(self, md_with_exclusions: str) -> None:
        """``exclusion_codes`` returns the EXC_* → CODIGO_* mapping."""
        tx = load_taxonomy_from_string(md_with_exclusions)
        mapping = tx.exclusion_codes()
        assert mapping == {
            "EXC_BASURA_DIGITAL": "CODIGO_99",
            "EXC_VIOLENCIA_COMUN": "VIOLENCIA_COMUN",
        }

    def test_canonical_exclusion_labels(self, md_with_exclusions: str) -> None:
        tx = load_taxonomy_from_string(md_with_exclusions)
        labels = tx.canonical_exclusion_labels()
        assert labels == frozenset({"CODIGO_99", "VIOLENCIA_COMUN"})

    def test_no_exclusions_is_valid(self, valid_md_text: str) -> None:
        """A taxonomy without categorias_exclusion still parses (back-compat)."""
        tx = load_taxonomy_from_string(valid_md_text)
        assert tx.categorias_exclusion == []
        assert tx.exclusion_codes() == {}
        assert tx.canonical_exclusion_labels() == frozenset()

    def test_exclusion_code_must_start_with_exc(self) -> None:
        with pytest.raises(ValidationError):
            ExclusionCategoriaMD.model_validate(
                {
                    "code": "BASURA_DIGITAL",  # missing EXC_ prefix
                    "codigo_canonico": "CODIGO_99",
                }
            )

    def test_exclusion_codigo_canonico_must_be_alphanumeric(self) -> None:
        with pytest.raises(ValidationError):
            ExclusionCategoriaMD.model_validate(
                {
                    "code": "EXC_X",
                    "codigo_canonico": "with spaces",
                }
            )

    def test_exclusion_codes_must_be_unique(self, md_with_exclusions: str) -> None:
        """Two exclusions sharing the same ``EXC_*`` code are rejected."""
        bad = _md_with_exclusions(
            textwrap.dedent(
                """\
                categorias_exclusion:
                  - code: EXC_BASURA_DIGITAL
                    codigo_canonico: CODIGO_99
                    descripcion: "x"
                  - code: EXC_BASURA_DIGITAL
                    codigo_canonico: CODIGO_OTHER
                    descripcion: "y"
                """
            ).rstrip()
        )
        with pytest.raises(ValidationError, match="Exclusion codes must be unique"):
            load_taxonomy_from_string(bad)

    def test_exclusion_canonicos_must_be_unique(self, md_with_exclusions: str) -> None:
        """Two exclusions sharing the same ``CODIGO_*`` value are rejected."""
        bad = _md_with_exclusions(
            textwrap.dedent(
                """\
                categorias_exclusion:
                  - code: EXC_ONE
                    codigo_canonico: CODIGO_99
                    descripcion: "x"
                  - code: EXC_TWO
                    codigo_canonico: CODIGO_99
                    descripcion: "y"
                """
            ).rstrip()
        )
        with pytest.raises(ValidationError, match="codigo_canonico values must be unique"):
            load_taxonomy_from_string(bad)

    def test_operational_invariant_unaffected_by_exclusions(self, md_with_exclusions: str) -> None:
        """Adding categorias_exclusion doesn't break the 6-categories rule."""
        tx = load_taxonomy_from_string(md_with_exclusions)
        assert len(tx.categorias) == 6
        assert all(c.code.startswith("VDG_") for c in tx.categorias)
        assert all(c.code.startswith("EXC_") for c in tx.categorias_exclusion)

    def test_real_md_has_canonical_exclusions(self) -> None:
        """The committed TAXONOMIA.md declares both canonical exclusions."""
        if not DEFAULT_TAXONOMY_PATH.exists():
            pytest.skip(f"Real TAXONOMIA.md not found at {DEFAULT_TAXONOMY_PATH}")
        tx = load_taxonomy()
        mapping = tx.exclusion_codes()
        assert "EXC_BASURA_DIGITAL" in mapping
        assert "EXC_VIOLENCIA_COMUN" in mapping
        assert mapping["EXC_BASURA_DIGITAL"] == "CODIGO_99"
        assert mapping["EXC_VIOLENCIA_COMUN"] == "VIOLENCIA_COMUN"
