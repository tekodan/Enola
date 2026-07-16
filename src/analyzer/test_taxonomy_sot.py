"""SSoT invariant tests for ``TAXONOMIA.md``.

These tests guard the Single-Source-of-Truth guarantee: every
canonical marker, overlap and exclusion pattern lives in one place
(the YAML frontmatter of ``knowledge/taxonomia/TAXONOMIA.md``)
and the loader's invariants keep it consistent.
"""

from __future__ import annotations

import unicodedata

import pytest

from src.analyzer.taxonomy_loader import (
    Taxonomy,
    load_taxonomy,
    reset_cache,
)


def _norm(m: str) -> str:
    nfkd = unicodedata.normalize("NFKD", m.lower())
    no = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(no.split())


def _tx() -> Taxonomy:
    reset_cache()
    return load_taxonomy()


# ─────────────────────────────────────────────────────────────────────────────
# Coverage
# ─────────────────────────────────────────────────────────────────────────────


def test_all_subdims_have_markers() -> None:
    """When ``marcadores_canonicos`` is present (v5.0 SSoT), every
    sub-dimension must have ≥3 markers.

    Pre-v5.0 (v1.1.1) doesn't have ``marcadores_canonicos`` — in that
    case this test is a no-op (the field is empty).
    """
    tx = _tx()
    markers_by_subdim = tx.markers_by_subdimension()
    if not any(markers_by_subdim.values()):
        pytest.skip("v1.1.x: marcadores_canonicos not yet in TAXONOMIA.md")
    n_subdims = len(markers_by_subdim)
    assert n_subdims in (18, 19), f"Expected 18 or 19, got {n_subdims}"
    empty = [code for code, ms in markers_by_subdim.items() if len(ms) < 3]
    assert not empty, f"Subdims with < 3 markers: {empty}"


def test_all_canonical_categories_have_4_or_3_subdims() -> None:
    """Cat. 4 has 3 or 4 subdims (depending on schema version); all
    others have exactly 3. Invariant.
    """
    tx = _tx()
    counts = {cat.code: len(cat.subdimensiones) for cat in tx.categorias}
    for cat in tx.categorias:
        if cat.orden == 4:
            # v1.1.x has 3; v2.0+ has 4 (added 4.4 Arquetipos Femeninos Deshumanizantes).
            assert counts[cat.code] in (3, 4), (
                f"{cat.code} should have 3 or 4 subdims, got {counts[cat.code]}"
            )
        else:
            assert counts[cat.code] == 3, f"{cat.code} should have 3 subdims"


def test_basura_digital_has_all_6_conditions() -> None:
    """The six algorithmic conditions of basura digital are all reachable.

    COND_1 (empty/NaN), COND_2 (orphan URL) and COND_3 (typographic
    noise) are hardcoded in :func:`detectar_basura_digital`. COND_4
    (pure laughter) and COND_5 (short reactions) are regex patterns in
    ``patrones-basura-digital.md``. COND_6_TAG_PERSONA (added
    2026-07-15) is a composite check in
    :func:`_is_only_mention_payload` — see
    ``test_exclusion_filter.TestBasuraDigitalCond6TagPersona``.

    The single-source-of-truth check is: each condition is *reachable*
    via :func:`detectar_basura_digital` with the right input.
    """
    from src.analyzer.exclusion_filter import detectar_basura_digital

    cases: list[tuple[str, str]] = [
        ("", "COND_1_VACIO"),
        ("https://example.com", "COND_2_ENLACE_HUERFANO"),
        ("🎉🎉🎉", "COND_3_RUIDO_TIPOGRAFICO"),
        ("jajaja", "COND_4_SOLO_RISA"),
        ("ok", "COND_5_REACCION_CORTA"),
        ("@user", "COND_6_TAG_PERSONA"),
    ]
    for text, expected_codigo in cases:
        r = detectar_basura_digital(text)
        assert r.excluded, f"{text!r} should be excluded"
        assert r.codigo == expected_codigo, f"{text!r}: expected {expected_codigo}, got {r.codigo}"


def test_desempate_rules_have_disparador() -> None:
    """Each tie-breaker rule has at least one trigger (primary or mandatory)."""
    tx = _tx()
    rules = tx.desempate_rules()
    if not rules:
        pytest.skip("v1.1.x: reglas_desempate not yet in TAXONOMIA.md")
    for r in rules:
        assert r.id and r.frontera and r.subdim_ganadora
        triggers = r.disparador_primario + r.disparador_obligatorio
        assert triggers, f"Rule {r.id} has no disparador"


# ─────────────────────────────────────────────────────────────────────────────
# Uniqueness
# ─────────────────────────────────────────────────────────────────────────────


def test_marker_uniqueness_across_subdims() -> None:
    """No marker is canonical in more than one sub-dim unless declared as overlap.

    The Pydantic invariant already enforces this, but the test pins
    it down explicitly with a clearer error message.
    """
    tx = _tx()
    declared = set()
    for cat in tx.categorias:
        for dim in cat.subdimensiones:
            for ov in dim.marcadores_overlap:
                declared.add((_norm(ov.marker), ov.subdim_secundaria))

    seen: dict[str, str] = {}
    conflicts: list[str] = []
    for cat in tx.categorias:
        for dim in cat.subdimensiones:
            for marker in dim.marcadores_canonicos:
                key = _norm(marker)
                if key in seen and seen[key] != dim.code:
                    if (key, dim.code) not in declared:
                        conflicts.append(f"{marker!r} → {seen[key]} AND {dim.code}")
                seen[key] = dim.code
    assert not conflicts, "Marker overlap conflicts: " + ", ".join(conflicts)


def test_basura_pattern_ids_unique() -> None:
    """Two patterns cannot share the same id."""
    tx = _tx()
    bd = tx.patrones_basura_digital_dict()
    assert len(bd) == len(set(bd.keys()))


def test_exclusion_codes_unique() -> None:
    tx = _tx()
    canon = list(tx.exclusion_codes().values())
    assert len(canon) == len(set(canon))


# ─────────────────────────────────────────────────────────────────────────────
# Overlap coverage
# ─────────────────────────────────────────────────────────────────────────────


def test_overlap_rules_have_regla() -> None:
    """Each declared overlap carries a non-empty ``regla`` explaining the disambiguation."""
    tx = _tx()
    n_overlaps = 0
    for cat in tx.categorias:
        for dim in cat.subdimensiones:
            for ov in dim.marcadores_overlap:
                n_overlaps += 1
                assert ov.marker, "Overlap missing marker"
                assert ov.subdim_secundaria, "Overlap missing secondary subdim"
                assert ov.regla and len(ov.regla) > 5, (
                    f"Overlap {ov.marker!r}→{ov.subdim_secundaria} has too short regla"
                )
    if n_overlaps == 0:
        pytest.skip("v1.1.x: marcadores_overlap not yet in TAXONOMIA.md")


# ─────────────────────────────────────────────────────────────────────────────
# SSoT accessors
# ─────────────────────────────────────────────────────────────────────────────


def test_markers_by_subdimension_is_complete() -> None:
    """Each marker appears in at most one sub-dim per the uniqueness invariant.

    The flat ``all_canonical_markers()`` set is the deduplicated union
    of every sub-dimension's ``marcadores_canonicos`` list. Because
    overlaps are declared separately (``marcadores_overlap``), the
    flat set should be ≤ the sum of per-sub-dim lists.
    """
    tx = _tx()
    by_subdim = tx.markers_by_subdimension()
    flat = tx.all_canonical_markers()
    sum_per_subdim = sum(len(v) for v in by_subdim.values())
    assert len(flat) <= sum_per_subdim
    # And every sub-dim's markers are part of the flat set.
    for markers in by_subdim.values():
        for m in markers:
            assert m in flat


def test_leetspeak_map_is_normalized() -> None:
    tx = _tx()
    mapping = tx.leetspeak_map()
    if not mapping:
        pytest.skip("v1.1.x: leetspeak_global not yet in TAXONOMIA.md")
    for src, dst in mapping.items():
        assert len(src) == 1, f"Leetspeak key {src!r} should be a single char"


def test_referentes_femeninos_set_nonempty() -> None:
    tx = _tx()
    if not tx.referentes_femeninos:
        pytest.skip("v1.1.x: referentes_femeninos not yet in TAXONOMIA.md")
    assert len(tx.referentes_femeninos_set()) >= 10


def test_marcadores_de_genero_nonempty() -> None:
    tx = _tx()
    if not tx.marcadores_de_genero:
        pytest.skip("v1.1.x: marcadores_de_genero not yet in TAXONOMIA.md")
    assert len(tx.marcadores_de_genero_set()) >= 10


def test_patrones_violencia_comun_nonempty() -> None:
    tx = _tx()
    if not tx.patrones_violencia_comun:
        pytest.skip("v1.1.x: patrones_violencia_comun not yet in TAXONOMIA.md")
    assert len(tx.patrones_violencia_comun_set()) >= 10


def test_multi_etiqueta_instruccion_nonempty() -> None:
    tx = _tx()
    if not tx.multi_etiqueta_instruccion:
        pytest.skip("v1.1.x: multi_etiqueta_instruccion not yet in TAXONOMIA.md")
    inst = tx.multi_etiqueta_instruccion
    assert inst and "clasificaciones" in inst and "Cat. 4" in inst
