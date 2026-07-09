"""Unit tests for the exclusion filter (CÓDIGO 99 + Violencia Común).

Mirrors the spec's three algorithmic conditions for basura digital
plus the pragmatic-discrimination rule for violencia común.
"""

import math

from src.analyzer.exclusion_filter import (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
    ExclusionResult,
    detectar_basura_digital,
    detectar_violencia_comun_heuristica,
    evaluar_exclusiones,
)


class TestDetectarBasuraDigital:
    """Tests for ``detectar_basura_digital`` (Condiciones 1-3)."""

    def test_none_is_basura(self):
        """Cond 1 — None payload."""
        r = detectar_basura_digital(None)
        assert r.excluded
        assert r.etiqueta == EXCLUSION_BASURA_DIGITAL
        assert r.codigo == "COND_1_NA"

    def test_nan_is_basura(self):
        """Cond 1 — NaN floats (pandas reads of empty cells)."""
        r = detectar_basura_digital(float("nan"))
        assert r.excluded
        assert r.etiqueta == EXCLUSION_BASURA_DIGITAL
        assert r.codigo == "COND_1_NAN"

    def test_empty_string_is_basura(self):
        """Cond 1 — empty / whitespace-only string."""
        assert detectar_basura_digital("").excluded
        assert detectar_basura_digital("   ").excluded
        assert detectar_basura_digital("\n\t").excluded

    def test_orphan_https_is_basura(self):
        """Cond 2 — only an https URL."""
        r = detectar_basura_digital("https://facebook.com/post/123")
        assert r.excluded
        assert r.codigo == "COND_2_ENLACE_HUERFANO"

    def test_orphan_www_is_basura(self):
        """Cond 2 — only a www URL."""
        r = detectar_basura_digital("www.example.com")
        assert r.excluded
        assert r.codigo == "COND_2_ENLACE_HUERFANO"

    def test_orphan_tco_is_basura(self):
        """Cond 2 — only a t.co shortlink."""
        r = detectar_basura_digital("t.co/abc123")
        assert r.excluded
        assert r.codigo == "COND_2_ENLACE_HUERFANO"

    def test_url_with_text_is_not_basura(self):
        """URL plus a legible word is NOT orphan."""
        r = detectar_basura_digital("mirá esto https://facebook.com/post/123")
        assert not r.excluded

    def test_only_emojis_is_basura(self):
        """Cond 3 — only emojis (no lexical structure)."""
        r = detectar_basura_digital("😀😡🔥")
        assert r.excluded
        assert r.codigo == "COND_3_RUIDO_TIPOGRAFICO"

    def test_only_punctuation_is_basura(self):
        """Cond 3 — only punctuation."""
        r = detectar_basura_digital("!!! ??? ### ???")
        assert r.excluded
        assert r.codigo == "COND_3_RUIDO_TIPOGRAFICO"

    def test_only_special_chars_is_basura(self):
        """Cond 3 — special chars without letters."""
        r = detectar_basura_digital("@#$%^&*()_+")
        assert r.excluded
        assert r.codigo == "COND_3_RUIDO_TIPOGRAFICO"

    def test_repeated_chars_is_basura(self):
        """Cond 3 — repeated character with no lexical content."""
        r = detectar_basura_digital("aaaaaaaaaaaaa")
        assert r.excluded
        assert r.codigo == "COND_3_RUIDO_TIPOGRAFICO"

    def test_normal_text_passes(self):
        """A normal sentence with a few words is not basura."""
        r = detectar_basura_digital("Esta es una opinión válida sobre política.")
        assert not r.excluded

    def test_short_real_word_passes(self):
        """Even a short real word passes."""
        r = detectar_basura_digital("ok")
        assert not r.excluded

    def test_text_with_accent_passes(self):
        """Accented characters count as lexical."""
        r = detectar_basura_digital("áéíóú ñü")
        assert not r.excluded

    def test_emoji_plus_word_passes(self):
        """Emoji + word → word wins."""
        r = detectar_basura_digital("🔥 mujeres dicen cosas")
        assert not r.excluded


class TestDetectarViolenciaComun:
    """Tests for ``detectar_violencia_comun_heuristica``."""

    def test_aggression_without_gender_marker_excluded(self):
        """Political/sports insult without gender marker → VIOLENCIA_COMUN."""
        r = detectar_violencia_comun_heuristica("Sos un imbécil y un corrupto")
        assert r.excluded
        assert r.etiqueta == EXCLUSION_VIOLENCIA_COMUN

    def test_aggression_with_gender_marker_passes(self):
        """Aggression with gender marker stays for normal classification."""
        r = detectar_violencia_comun_heuristica("Sos una puta")
        assert not r.excluded

    def test_neutral_text_passes(self):
        """No aggression marker → no exclusion."""
        r = detectar_violencia_comun_heuristica("Que buen día para caminar")
        assert not r.excluded

    def test_empty_passes(self):
        """Empty string is the basura filter's job, not this one."""
        r = detectar_violencia_comun_heuristica("")
        assert not r.excluded

    def test_accent_insensitive(self):
        """Aggression marker survives accent stripping."""
        r = detectar_violencia_comun_heuristica("malditos boludos")
        assert r.excluded


class TestEvaluarExclusiones:
    """Tests for the composed ``evaluar_exclusiones`` entry point.

    ``evaluar_exclusiones`` only runs the basura digital detector — the
    violencia-común discrimination belongs to the LLM (prompt) and to
    :func:`detectar_violencia_comun_heuristica` (rule-based fallback).
    """

    def test_basura_takes_priority(self):
        """Empty payload → basura."""
        r = evaluar_exclusiones("")
        assert r.etiqueta == EXCLUSION_BASURA_DIGITAL

    def test_only_text_with_no_aggression_passes(self):
        """Plain opinion passes — let the LLM decide."""
        r = evaluar_exclusiones("Me gusta el café por la mañana")
        assert not r.excluded

    def test_url_with_word_passes(self):
        """A URL plus words is a valid input."""
        r = evaluar_exclusiones("mirá esto https://ejemplo.com")
        assert not r.excluded

    def test_aggression_passes_to_llm(self):
        """Aggressive but ungendered text is NOT pre-blocked — the LLM
        is asked to mark it VIOLENCIA_COMUN.
        """
        r = evaluar_exclusiones("Sos un imbécil y un corrupto")
        assert not r.excluded


class TestExclusionResultDataclass:
    """Dataclass invariants."""

    def test_excluded_property_when_set(self):
        a = ExclusionResult(etiqueta="CODIGO_99", codigo="X", justificacion="y")
        assert a.excluded

    def test_excluded_property_when_none(self):
        b = ExclusionResult(etiqueta=None, codigo=None, justificacion="")
        assert not b.excluded

    def test_is_immutable(self):
        """The dataclass is frozen — fields cannot be reassigned."""
        a = ExclusionResult(etiqueta="CODIGO_99", codigo="X", justificacion="y")
        try:
            a.etiqueta = "OTHER"  # type: ignore[misc]
            assigned = True
        except (AttributeError, Exception):
            assigned = False
        assert not assigned


class TestRAGClassifierIntegration:
    """The pre-filter must short-circuit ``classify()`` before the LLM."""

    def test_classify_basura_returns_exclusion_label(self):
        """RAGClassifier.classify on basura must NOT call the LLM."""
        import asyncio
        from unittest.mock import MagicMock

        from src.analyzer.rag_classifier import RAGClassifier

        llm = MagicMock()
        cls = RAGClassifier(llm_client=llm)

        result = asyncio.run(cls.classify(""))
        assert result.exclusion_label == EXCLUSION_BASURA_DIGITAL
        assert result.tiene_violencia is False
        llm.generate.assert_not_called()

    def test_classify_orphan_url_returns_exclusion_label(self):
        """RAGClassifier.classify on orphan URL must NOT call the LLM."""
        import asyncio
        from unittest.mock import MagicMock

        from src.analyzer.rag_classifier import RAGClassifier

        llm = MagicMock()
        cls = RAGClassifier(llm_client=llm)

        result = asyncio.run(cls.classify("https://facebook.com/post/123"))
        assert result.exclusion_label == EXCLUSION_BASURA_DIGITAL
        llm.generate.assert_not_called()

    def test_classify_emoji_only_returns_exclusion_label(self):
        """RAGClassifier.classify on emoji-only must NOT call the LLM."""
        import asyncio
        from unittest.mock import MagicMock

        from src.analyzer.rag_classifier import RAGClassifier

        llm = MagicMock()
        cls = RAGClassifier(llm_client=llm)

        result = asyncio.run(cls.classify("🔥🔥🔥"))
        assert result.exclusion_label == EXCLUSION_BASURA_DIGITAL
        llm.generate.assert_not_called()

    def test_classify_normal_text_reaches_llm(self):
        """A normal sentence MUST reach the LLM (no false exclusion)."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.analyzer.rag_classifier import RAGClassifier

        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value='{"tiene_violencia": false, "severidad_global": "ninguna", '
            '"clasificaciones": []}'
        )
        cls = RAGClassifier(llm_client=llm)

        result = asyncio.run(cls.classify("Me gusta el café"))
        assert result.exclusion_label is None
        llm.generate.assert_called_once()

    def test_classify_aggression_without_gender_still_reaches_llm(self):
        """The regla de exclusión for violencia común is primarily an LLM
        judgement. The pre-filter does NOT bypass the LLM for aggressive
        but ungendered text — the prompt tells the LLM to mark it
        VIOLENCIA_COMUN.
        """
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.analyzer.rag_classifier import RAGClassifier

        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value='{"tiene_violencia": false, "severidad_global": "ninguna", '
            '"clasificaciones": [], "exclusion_label": "VIOLENCIA_COMUN"}'
        )
        cls = RAGClassifier(llm_client=llm)

        result = asyncio.run(cls.classify("Sos un imbécil"))
        llm.generate.assert_called_once()  # LLM is asked to decide
        # The LLM's exclusion verdict is propagated to the result.
        assert result.exclusion_label == EXCLUSION_VIOLENCIA_COMUN
        assert result.tiene_violencia is False


def test_nan_constant_value():
    """Sanity check: math.nan behaves as expected by the detector."""
    assert math.isnan(float("nan"))
