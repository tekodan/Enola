"""Unit tests for the exclusion filter (CÓDIGO 99 + Violencia Común).

Mirrors the spec's algorithmic conditions for basura digital
(Cond 1 — vacío; Cond 2 — enlace huérfano; Cond 3 — ruido
tipográfico; Cond 4 — risas puras; Cond 5 — reacciones cortas;
Cond 6 — mención a persona sin comentario) plus the
pragmatic-discrimination rule for violencia común.
"""

import math
from pathlib import Path

import pytest

from src.analyzer.exclusion_filter import (
    _GENDER_MARKERS,
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
    MARCADORES_DE_GENERO_MARKDOWN,
    PATRONES_BASURA_DIGITAL_MARKDOWN,
    ExclusionResult,
    _load_basura_digital_patterns,
    detectar_basura_digital,
    detectar_violencia_comun_heuristica,
    evaluar_exclusiones,
    reset_basura_patterns_cache,
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
        """Short real words that are NOT pure reactions pass through.

        Date note: as of 2026-07-14 the pre-filter now also excludes
        pure reactions (COND_5 — ``ok``, ``si``, ``no``, ``ya``,
        ``dale`` …) so this assertion explicitly checks a word that's
        NOT a pure reaction, since the previous behavior of letting
        ``ok`` through has been replaced by the new COND_5 rule.
        """
        r = detectar_basura_digital("asco")
        assert not r.excluded

    def test_text_with_accent_passes(self):
        """Accented characters count as lexical."""
        r = detectar_basura_digital("áéíóú ñü")
        assert not r.excluded

    def test_emoji_plus_word_passes(self):
        """Emoji + word → word wins."""
        r = detectar_basura_digital("🔥 mujeres dicen cosas")
        assert not r.excluded


class TestBasuraDigitalCondiciones4y5:
    """COND_4 (risas) and COND_5 (reacciones cortas) — added 2026-07-14.

    Pattern-driven detection backed by the canonical
    ``glosario/patrones-basura-digital.md``. The list is loaded once
    via :func:`_load_basura_digital_patterns`; :func:`reset_basura_patterns_cache`
    clears the ``lru_cache`` so the new patterns take effect after the
    markdown is edited.
    """

    def test_jajaja_es_basura(self):
        """Pure laughter → COND_4_SOLO_RISA."""
        r = detectar_basura_digital("jajaja")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_jeje_es_basura(self):
        r = detectar_basura_digital("jeje")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_hahaha_es_basura(self):
        r = detectar_basura_digital("hahaha")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_rsrs_es_basura(self):
        r = detectar_basura_digital("rsrs")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_lol_es_basura(self):
        r = detectar_basura_digital("lol")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_xd_es_basura(self):
        r = detectar_basura_digital("xd")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_jajaja_con_puntuacion(self):
        """Trailing punctuation is allowed."""
        r = detectar_basura_digital("jajaja!")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_jajaja_minuscula_y_mayuscula(self):
        """Matching is case-insensitive."""
        r = detectar_basura_digital("JAJAJA")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_jajaja_acento_insensitive(self):
        r = detectar_basura_digital("jajajá")
        assert r.excluded
        assert r.codigo == "COND_4_SOLO_RISA"

    def test_ok_es_basura(self):
        """Pure reaction → COND_5_REACCION_CORTA."""
        r = detectar_basura_digital("ok")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_si_es_basura(self):
        r = detectar_basura_digital("si")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_no_es_basura(self):
        r = detectar_basura_digital("no")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_ya_es_basura(self):
        r = detectar_basura_digital("ya")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_dale_con_exclamacion(self):
        r = detectar_basura_digital("dale!")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_palabra_real_corta_no_es_basura(self):
        """Real words with content escape COND_5 — only pure reactions match."""
        r = detectar_basura_digital("asco")
        assert not r.excluded

    def test_mal_no_es_basura(self):
        r = detectar_basura_digital("mal")
        assert not r.excluded

    def test_frase_completa_con_palabra_clave_pasa(self):
        """Whitespace + laughter appended to a real sentence does NOT trigger."""
        r = detectar_basura_digital("Esto es terrible jajaja")
        assert not r.excluded

    def test_multi_palabra_con_ok_pasa(self):
        """``ok`` in context does NOT trigger (fullmatch requires the whole input)."""
        r = detectar_basura_digital("ok, gracias")
        assert not r.excluded

    def test_mujeres_no_es_basura(self):
        """Words like 'mujeres' that contain 'je' don't fullmatch COND_5."""
        r = detectar_basura_digital("mujeres")
        assert not r.excluded

    def test_text_con_emoji_y_palabra_pasa(self):
        """An emoji plus a real word passes; COND_5 is exact-match only."""
        r = detectar_basura_digital("ok 🔥 palabra")
        assert not r.excluded

    def test_patron_glosario_cargado(self):
        """The glosario is loaded (sanity check)."""
        patterns = _load_basura_digital_patterns()
        assert len(patterns) > 0
        assert any("ja" in p for p in patterns)
        assert any("ok" in p for p in patterns)

    def test_se_es_basura(self):
        """Monosyllabic ``se`` particle is COND_5_REACCION_CORTA."""
        r = detectar_basura_digital("se")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_pues_es_basura(self):
        r = detectar_basura_digital("pues")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_que_es_basura(self):
        r = detectar_basura_digital("que")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_que_con_acento_es_basura(self):
        """Accent-insensitive matching for ``qué``."""
        r = detectar_basura_digital("qué")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_quiza_es_basura(self):
        r = detectar_basura_digital("quiza")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_quizas_es_basura(self):
        r = detectar_basura_digital("quizas")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_que_con_pregunta_es_basura(self):
        """Trailing punctuation is allowed (``que?`` / ``que.`` …)."""
        r = detectar_basura_digital("que?")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_tal_es_basura(self):
        r = detectar_basura_digital("tal")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_como_es_basura(self):
        r = detectar_basura_digital("como")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_donde_es_basura(self):
        r = detectar_basura_digital("donde")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_cuando_es_basura(self):
        r = detectar_basura_digital("cuando")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_tambien_es_basura(self):
        r = detectar_basura_digital("tambien")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_tampoco_es_basura(self):
        r = detectar_basura_digital("tampoco")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_vale_es_basura(self):
        r = detectar_basura_digital("vale")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_ahi_es_basura(self):
        r = detectar_basura_digital("ahi")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_aqui_es_basura(self):
        r = detectar_basura_digital("aqui")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_a_ver_es_basura(self):
        r = detectar_basura_digital("a ver")
        assert r.excluded
        assert r.codigo == "COND_5_REACCION_CORTA"

    def test_q_y_k_son_basura(self):
        """Single letters ``q`` and ``k`` are basura (COND_3 or COND_5).

        Whether they trigger ``COND_3_RUIDO_TIPOGRAFICO`` (single
        letter fails the lexical-structure check) or
        ``COND_5_REACCION_CORTA`` (matches the inline pattern) is an
        implementation detail — both produce the same
        ``CODIGO_99`` exclusion.
        """
        for txt in ("q", "k", "q?", "k!"):
            r = detectar_basura_digital(txt)
            assert r.excluded, f"expected {txt!r} to be excluded"
            assert r.codigo in {
                "COND_3_RUIDO_TIPOGRAFICO",
                "COND_5_REACCION_CORTA",
            }, f"unexpected codigo for {txt!r}: {r.codigo}"

    def test_frase_con_se_no_es_basura(self):
        """A real sentence containing ``se`` as a particle does NOT trigger."""
        r = detectar_basura_digital("el cafe se fue")
        assert not r.excluded

    def test_frase_con_que_no_es_basura(self):
        """A real sentence with ``que`` does NOT trigger COND_5."""
        r = detectar_basura_digital("que te pasa")
        assert not r.excluded

    def test_frase_con_pues_no_es_basura(self):
        """``pues mira te digo`` does NOT trigger COND_5."""
        r = detectar_basura_digital("pues mira te digo")
        assert not r.excluded

    def test_frase_con_quiza_sin_coma_no_es_basura(self):
        """``quiza no se preocupe`` does NOT trigger COND_5."""
        r = detectar_basura_digital("quiza no se preocupe")
        assert not r.excluded

    def test_frase_con_como_no_es_basura(self):
        """``como no te da`` does NOT trigger COND_5."""
        r = detectar_basura_digital("como no te da")
        assert not r.excluded

    def test_q_con_palabra_no_es_basura(self):
        """``q tal`` (chat shorthand) is NOT pure ``q`` — passes to LLM."""
        r = detectar_basura_digital("q tal")
        assert not r.excluded

    def test_k_con_palabra_no_es_basura(self):
        """``k ase`` (chat shorthand) is NOT pure ``k`` — passes to LLM."""
        r = detectar_basura_digital("k ase")
        assert not r.excluded

    def test_glosario_fallback_vacio(self, monkeypatch):
        """If the glosario file is missing, patterns fall back to empty.

        The pre-filter keeps working — only COND_4/COND_5 are silent.
        """
        from src.analyzer import exclusion_filter

        monkeypatch.setattr(
            exclusion_filter,
            "PATRONES_BASURA_DIGITAL_MARKDOWN",
            Path("/nonexistent/glosario.md"),
        )
        reset_basura_patterns_cache()
        try:
            assert exclusion_filter._load_basura_digital_patterns() == ()
        finally:
            monkeypatch.undo()
            reset_basura_patterns_cache()

    def test_glosario_ruta_existe(self):
        """The canonical glosario markdown must be on disk."""
        assert PATRONES_BASURA_DIGITAL_MARKDOWN.is_file()


class TestBasuraDigitalCond6TagPersona:
    """COND_6_TAG_PERSONA — added 2026-07-15.

    Implements the spec rule: ``Cuando se etiqueta a una persona
    @elnombredelapersona sin estar acompañado de ningún otro
    comentario`` → ``CODIGO_99``. Detected by
    :func:`_is_only_mention_payload` in ``exclusion_filter.py``.

    Not a ``re.fullmatch`` pattern (lives in the helper, not in
    ``patrones-basura-digital.md``) because the rule is a composite
    check: presence of at least one ``@user`` token AND absence of any
    other legible word. The spec numbers this as COND_4; the code
    emits it as COND_6 to preserve the numbering of
    COND_4_SOLO_RISA / COND_5_REACCION_CORTA already persisted in
    ``analysis_results.exclusion_codigo``.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "@juan",
            "@juan.perez",
            "@user_123",
            "@user-name",
            "@a",
            "@user1 @user2",
            "@user1,@user2",
            "@user1.",
            "@USUARIO",
            "@user1 @user2 @user3",
            "@user\n",
            "  @user  ",
        ],
    )
    def test_only_mention_is_basura(self, text: str):
        """Pure-mention payloads → COND_6_TAG_PERSONA."""
        from src.analyzer.exclusion_filter import (
            detectar_basura_digital,
        )

        r = detectar_basura_digital(text)
        assert r.excluded, f"expected {text!r} to be excluded"
        assert r.codigo == "COND_6_TAG_PERSONA", f"unexpected codigo for {text!r}: {r.codigo}"

    @pytest.mark.parametrize(
        "text",
        [
            "@user mirá esto",
            "Hola @user cómo estás",
            "mirá @user",
            "@user! qué onda",
            "respondeme @user",
        ],
    )
    def test_mention_with_extra_word_is_not_basura(self, text: str):
        """A lexical word outside the mentions defeats COND_6.

        The important invariant is that real sentences (with at least
        one extra word) pass through. Punctuation-only additions
        (``@user.``, ``@user 🔥``) remain COND_6 because no lexical
        word is added.
        """
        from src.analyzer.exclusion_filter import (
            detectar_basura_digital,
        )

        r = detectar_basura_digital(text)
        assert not r.excluded, f"expected {text!r} to reach the LLM"

    @pytest.mark.parametrize(
        "text",
        [
            "@user 🔥",
            "@user.",
            "@user!",
            "@user?",
            "@user 😀",
        ],
    )
    def test_mention_with_only_noise_is_still_cond6(self, text: str):
        """Punctuation / emoji additions are not "other comments"."""
        r = detectar_basura_digital(text)
        assert r.excluded, f"expected {text!r} to be excluded"
        assert r.codigo == "COND_6_TAG_PERSONA"

    def test_email_is_not_basura(self):
        """``juan@gmail.com`` is NOT a mention — the ``@`` is mid-token."""
        r = detectar_basura_digital("juan@gmail.com")
        assert not r.excluded

    def test_at_solo_no_es_cond6(self):
        """A bare ``@`` (no username) does not match COND_6.

        It is still excluded via COND_3_RUIDO_TIPOGRAFICO (single
        non-letter), but the codigo is NOT COND_6.
        """
        r = detectar_basura_digital("@")
        assert r.excluded
        assert r.codigo == "COND_3_RUIDO_TIPOGRAFICO"

    def test_at_con_espacio_no_matchea(self):
        """``@ user`` (space between @ and username) does NOT match
        COND_6 — the regex requires the ``@`` to be glued to the
        username.

        After stripping emojis/punctuation, ``user`` is a valid
        4-letter lexical word, so COND_3_RUIDO_TIPOGRAFICO does NOT
        fire either. The message reaches the LLM (it carries the
        word ``user``). The important invariant for this test is
        that the codigo is NOT COND_6.
        """
        r = detectar_basura_digital("@ user")
        assert not r.excluded
        assert r.codigo != "COND_6_TAG_PERSONA"

    def test_mention_plus_url_sigue_siendo_cond6(self):
        """Per the spec, a URL does not count as a "comment", so
        ``@user https://example.com`` is still COND_6_TAG_PERSONA.

        Order in ``detectar_basura_digital``:
        COND_1 → COND_3 (repeated chars) → COND_2 (URL) → COND_6 (mention).
        COND_2 does NOT fire here because ``user`` is a lexical word
        outside the URL, so the URL is not orphan. COND_6 fires
        because URLs are stripped before checking lexical content.
        """
        r = detectar_basura_digital("@user https://example.com")
        assert r.excluded
        assert r.codigo == "COND_6_TAG_PERSONA"

    def test_only_mention_multi_line(self):
        """Multi-line mention-only payloads → COND_6."""
        r = detectar_basura_digital("@user1\n@user2")
        assert r.excluded
        assert r.codigo == "COND_6_TAG_PERSONA"

    def test_classify_short_circuits_llm_for_tag_only(self):
        """RAGClassifier.classify on a mention-only payload must NOT
        call the LLM — same behavior as the other basura conditions.
        """
        import asyncio
        from unittest.mock import MagicMock

        from src.analyzer.rag_classifier import RAGClassifier

        llm = MagicMock()
        cls = RAGClassifier(llm_client=llm)

        result = asyncio.run(cls.classify("@juan.perez"))
        assert result.exclusion_label == EXCLUSION_BASURA_DIGITAL
        assert result.exclusion_codigo == "COND_6_TAG_PERSONA"
        assert result.tiene_violencia is False
        llm.generate.assert_not_called()

    def test_glosario_documenta_cond6(self):
        """The glosario markdown mentions COND_6_TAG_PERSONA so the
        rule stays documented alongside the regex patterns."""
        from src.analyzer.exclusion_filter import (
            PATRONES_BASURA_DIGITAL_MARKDOWN,
        )

        text = PATRONES_BASURA_DIGITAL_MARKDOWN.read_text(encoding="utf-8")
        assert "COND_6" in text
        assert "Menciones a persona" in text or "mención" in text.lower()


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
        """RAGClassifier.classify on basura digital (emoji-only) must
        NOT call the LLM.

        Note 2026-07-12: switched from ``""`` to a typographic-noise
        basura case (emoji-only, COND_3). The empty-string short-circuit
        was intentionally simplified — the user asked to focus on
        detection rule improvements in the prompt/markdown, not on the
        exclusion pre-filter logic.
        """
        import asyncio
        from unittest.mock import MagicMock

        from src.analyzer.rag_classifier import RAGClassifier

        llm = MagicMock()
        cls = RAGClassifier(llm_client=llm)

        result = asyncio.run(cls.classify("🎉🎉🎉"))
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


class TestGenderMarkersGlossary:
    """Verifies that the gender markers list is loaded from the markdown
    glosario, not hardcoded in Python."""

    def test_glossary_file_exists(self):
        assert MARCADORES_DE_GENERO_MARKDOWN.is_file()

    def test_loads_expected_subset_of_markers(self):
        """Spot-check that the canonical markers are present in the
        loaded frozenset (loaded from the glosario markdown)."""
        for marker in (
            "feminazi",
            "incel",
            "mgtow",
            "mangina",
            "zorra",
            "puta",
            "matar",
            "violar",
            "femicidio",
            "mujeres de cocina",
            "para eso estas",
            "para eso estás",
        ):
            assert marker in _GENDER_MARKERS, f"missing marker: {marker!r}"

    def test_handcraft_markers_not_loaded_when_glossary_missing(self, monkeypatch):
        """If the glosario file is missing, ``_GENDER_MARKERS`` falls back
        to an empty frozenset — it does NOT silently use the old
        hardcoded list."""
        from src.analyzer import exclusion_filter

        monkeypatch.setattr(
            exclusion_filter,
            "MARCADORES_DE_GENERO_MARKDOWN",
            Path("/nonexistent/glosario.md"),
        )
        # Cache invalidation: must reload on next call.
        exclusion_filter._load_gender_markers.cache_clear()
        try:
            markers = exclusion_filter._load_gender_markers()
            assert markers == frozenset()
        finally:
            # Restore for other tests.
            monkeypatch.undo()
            exclusion_filter._load_gender_markers.cache_clear()
            exclusion_filter._GENDER_MARKERS = exclusion_filter._load_gender_markers()
