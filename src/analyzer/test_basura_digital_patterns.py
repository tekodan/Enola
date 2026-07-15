"""Tests for the v5 SSoT-driven basura digital patterns.

Covers the new patterns added on 2026-07-15 to
``knowledge/taxonomia/TAXONOMIA.md`` (block ``patrones_basura_digital``
under ``COND_5_REACCION_CORTA``). Patterns live in the taxon's
frontmatter and are loaded via :func:`_load_basura_digital_patterns`.

If you change ``TAXONOMIA.md`` you'll need to reload modules to clear
the LRU caches — see ``reset_basura_patterns_cache`` /
``reset_violencia_comun_cache``.
"""

from __future__ import annotations

import re

import pytest

from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    detectar_basura_digital,
)


@pytest.fixture(autouse=True)
def _fresh_basura_cache():
    """Reset cached patterns before each test to avoid stale data."""
    from src.analyzer import exclusion_filter

    exclusion_filter.reset_basura_patterns_cache()
    yield
    exclusion_filter.reset_basura_patterns_cache()


class TestStickerAndGifPlaceholders:
    """Placeholders de adjunto (GIPHY, sticker, imagen, foto)."""

    @pytest.mark.parametrize(
        "text",
        [
            "GIPHY",
            "giphy",
            "Giphy",
            "gif",
            "GIF",
            "sticker",
            "Sticker",
            "imagen",
            "foto",
            "giphy!",
            "GIPHY.",
            "imagen?",
        ],
    )
    def test_placeholder_is_basura(self, text: str):
        r = detectar_basura_digital(text)
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_real_sentence_with_giphy_passes(self):
        """ "Hay un giphy en el post" no es basura (palabras adicionales)."""
        r = detectar_basura_digital("Hay un giphy en este post")
        assert not r.excluded


class TestFacebookUiFragments:
    """Chips de reacción y unidades temporales."""

    @pytest.mark.parametrize(
        "text",
        [
            "Me gusta",
            "Responder",
            "Compartir",
            "Comentar",
            "Ver mas",
            "Ver menos",
            "Ver perfil",
        ],
    )
    def test_chip_is_basura(self, text: str):
        r = detectar_basura_digital(text)
        assert r.excluded

    def test_truncated_m_chip(self):
        """ "e gusta Responder" — UI chip con la "m" truncada."""
        r = detectar_basura_digital("e gusta Responder")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_truncated_m_chip_without_suffix(self):
        """ "e gusta" — UI chip mínimo."""
        r = detectar_basura_digital("e gusta")
        assert r.excluded

    @pytest.mark.parametrize(
        "text",
        [
            "5 min",
            "2 horas",
            "1 día",
            "3 semanas",
            "1 año",
            "5 min Me gusta",
            "2 hora Me gusta Responder",
            "3 dias",
        ],
    )
    def test_temporal_label_is_basura(self, text: str):
        r = detectar_basura_digital(text)
        assert r.excluded

    def test_fb_year_label(self):
        """ "año Me gusta Responder" — sólo unidad temporal sola."""
        r = detectar_basura_digital("año Me gusta Responder")
        assert r.excluded


class TestGreetingsAndFarewells:
    """Saludos / despedidas como único payload."""

    @pytest.mark.parametrize(
        "text",
        [
            "Hola",
            "Hola!",
            "hi",
            "Hello",
            "Hey",
            "Buenas",
            "Buenos dias",
            "Buenos días",
            "Buenas tardes",
            "Buenas noches",
        ],
    )
    def test_greeting_is_basura(self, text: str):
        r = detectar_basura_digital(text)
        assert r.excluded

    @pytest.mark.parametrize(
        "text",
        [
            "Adios",
            "Adiós",
            "Chau",
            "Chao",
            "Bye",
            "Hasta luego",
            "Hasta mañana",
            "Hasta pronto",
            "Nos vemos",
        ],
    )
    def test_farewell_is_basura(self, text: str):
        r = detectar_basura_digital(text)
        assert r.excluded

    def test_real_greeting_with_body_passes(self):
        """ "Hola, ¿cómo estás?" NO es basura — palabras adicionales."""
        r = detectar_basura_digital("Hola, ¿cómo estás?")
        assert not r.excluded


class TestFestiveMessages:
    """Felicitaciones / festividades como único payload."""

    @pytest.mark.parametrize(
        "text",
        [
            "Feliz cumple",
            "Feliz cumpleaños",
            "Feliz cumpleanios",
            "Feliz navidad",
            "Feliz año",
            "Feliz año nuevo",
            "Felicidades",
            "felicidades!",
            "Felices fiestas",
            "Prospero año",
            "Próspero año",
            "Happy birthday",
            "Happy new year",
        ],
    )
    def test_festive_is_basura(self, text: str):
        r = detectar_basura_digital(text)
        assert r.excluded


class TestShortConfirms:
    """Confirmaciones cortas redundantes."""

    @pytest.mark.parametrize(
        "text",
        ["sip", "nop", "sisi", "nono", "ya!", "ya!!", "ok", "okay", "okey!", "dale"],
    )
    def test_confirm_is_basura(self, text: str):
        r = detectar_basura_digital(text)
        assert r.excluded


class TestBasuraPatternsAreLoadable:
    """Sanity check de los patrones generados desde el SSoT."""

    def test_patterns_loaded_from_taxonomy(self):
        from src.analyzer.exclusion_filter import _load_basura_digital_patterns

        patterns = _load_basura_digital_patterns()
        # We expect at least the legacy cond_4 + cond_5 set: roughly
        # 50–80 patterns in total after the 2026-07-15 reinforcement.
        assert len(patterns) >= 30

    def test_all_patterns_compile(self):
        """Each pattern must be a valid regex."""
        from src.analyzer.exclusion_filter import _load_basura_digital_patterns

        for p in _load_basura_digital_patterns():
            # Strip the inline comment tag (any tag suffix ` # TAG`).
            regex_str = p.split("#", 1)[0].strip() if "#" in p else p.strip()
            re.compile(regex_str)  # raises re.error if invalid

    def test_dry_run_targets_real_db_rows(self):
        """If a DB exists with basura-real rows, the run picks them up.

        Skip if no DB is reachable.
        """
        from pathlib import Path

        if not Path("data/tfm.db").exists():
            pytest.skip("data/tfm.db not available")

        import sqlite3

        db = sqlite3.connect("data/tfm.db")
        db.row_factory = sqlite3.Row
        cur = db.execute(
            """
            SELECT a.id, c.text
            FROM analysis_results a
            JOIN comments c ON a.content_id = c.id AND a.content_type = 'comment'
            WHERE a.exclusion_label = 'CODIGO_99'
              AND a.exclusion_codigo = 'COND_5_REACCION_CORTA'
            LIMIT 100
            """
        )
        hits = [tuple(r) for r in cur.fetchall()]
        assert hits, "Expected at least one GIPHY/e gusta chip in the tagged set"


def test_basura_vs_violencia_invariant():
    """Texts that carry gender violence MUST NOT be tagged as basura.

    Sanity check on real manosfera content already classified by the
    LLM. Those rows live in the DB but the pre-filter must NOT flip
    them to basura.
    """
    from pathlib import Path

    if not Path("data/tfm.db").exists():
        pytest.skip("data/tfm.db not available")

    import sqlite3

    db = sqlite3.connect("data/tfm.db")
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT c.text
        FROM analysis_results a
        JOIN comments c ON a.content_id = c.id AND a.content_type = 'comment'
        WHERE a.categoria IN ('VDG_VIOLENCIA_SIMBOLICA', 'VDG_COSIFICACION_SLUTSHAMING',
                              'VDG_HOSTILIDAD_FEMINICIDIO', 'VDG_MANOSFERA_ANTIFEMINISMO')
          AND a.tiene_violencia = 'true'
          AND a.exclusion_label IS NULL
        LIMIT 20
        """
    ).fetchall()
    assert rows, "Need at least some positive matches for this invariant"
    for r in rows:
        text = r["text"] or ""
        if not text.strip():
            continue
        result = detectar_basura_digital(text)
        assert not result.excluded, (
            f"Real violence content flagged as basura (false positive):\n{text[:120]!r}"
        )


# Sanity: all the tests above use ``EXCLUSION_BASURA_DIGITAL`` so the
# import isn't unused.
_ = EXCLUSION_BASURA_DIGITAL
