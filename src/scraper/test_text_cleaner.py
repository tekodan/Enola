"""Tests for ``src.scraper.text_cleaner``."""

import pytest

from src.scraper.text_cleaner import (
    _strip_short_token_tail,
    strip_comment_noise,
    strip_post_noise,
    strip_standalone_numbers,
)


class TestStripStandaloneNumbers:
    """Tests for ``strip_standalone_numbers``."""

    def test_empty(self):
        assert strip_standalone_numbers("") == ""

    def test_none(self):
        assert strip_standalone_numbers(None) == ""

    def test_pure_digits(self):
        assert strip_standalone_numbers("123") == ""

    def test_mixed_text_with_digits(self):
        """Bare digits inside text are removed, words stay."""
        assert strip_standalone_numbers("Hola 123 mundo 456 hoy") == "Hola  mundo  hoy"

    def test_digits_glued_to_letters_preserved(self):
        """Digits inside alphanumeric tokens are preserved."""
        assert strip_standalone_numbers("URL1 facebook2 var3a") == "URL1 facebook2 var3a"

    def test_url_hashes(self):
        """Digits inside URLs/hashes are preserved (glued to letters)."""
        assert (
            strip_standalone_numbers("https://fb.com/post/abc123def")
            == "https://fb.com/post/abc123def"
        )

    def test_decimal_like(self):
        """Decimal point acts as boundary, both parts get stripped."""
        assert strip_standalone_numbers("3.14") == "."


class TestStripPostNoise:
    """Tests for ``strip_post_noise``."""

    def test_empty(self):
        assert strip_post_noise("") == ""
        assert strip_post_noise(None) == ""

    def test_clean_text_unchanged(self):
        clean = "Esto es un comentario perfectamente normal sin ruido."
        assert strip_post_noise(clean) == clean

    def test_leading_facebook_repetitions(self):
        raw = "Facebook Facebook Facebook Hola mundo"
        assert strip_post_noise(raw) == "Hola mundo"

    def test_leading_anti_scrape_with_middle_dot(self):
        raw = "t 0 6 8 5 4 9 2 1 · Confiar en la lealtad"
        assert strip_post_noise(raw) == "Confiar en la lealtad"

    def test_trailing_facebook_repetitions(self):
        raw = "Hola mundo Facebook Facebook Facebook Facebook Facebook"
        assert strip_post_noise(raw) == "Hola mundo"

    def test_trailing_anti_scrape_with_numbers(self):
        raw = "Hola mundo r n a 0 o i l m 662 35 97 Facebook Facebook Facebook"
        out = strip_post_noise(raw)
        assert "r n a 0 o i l m" not in out
        assert "Facebook" not in out
        assert "Hola mundo" in out

    def test_trailing_short_tokens_with_facebook(self):
        raw = "Hola mundo s 7 0 m 9 1 2 a 112 13 9 Facebook Facebook Facebook"
        out = strip_post_noise(raw)
        assert "s 7 0 m" not in out
        assert "Facebook" not in out
        assert out == "Hola mundo"

    def test_compartir_button(self):
        raw = "Texto interesante Compartir hoy"
        out = strip_post_noise(raw)
        assert "Compartir" not in out
        assert "Texto interesante hoy" == out

    def test_comentar_como_button(self):
        raw = "Post body… Comentar como Dani Alvez Facebook Facebook"
        out = strip_post_noise(raw)
        assert "Comentar como" not in out
        assert "Dani" not in out

    def test_url_spam_with_author(self):
        """Truncated URL + author spam link removed."""
        raw = "Post body… Ver más mGBr281.com Dani Author Text"
        out = strip_post_noise(raw)
        assert "mGBr281.com" not in out

    def test_compartido_con_publico(self):
        raw = "Post body Compartido con: Público más texto Facebook"
        out = strip_post_noise(raw)
        assert "Compartido con" not in out

    def test_idempotent_clean_text(self):
        clean = "Esto es un comentario perfectamente normal sin ruido."
        once = strip_post_noise(clean)
        twice = strip_post_noise(once)
        assert once == twice

    def test_idempotent_with_noise(self):
        raw = (
            "t 0 6 8 5 4 9 2 1 · Confiar en la lealtad … "
            "Ver más 27 5 Comentar como Dani Alvez Facebook Facebook"
        )
        once = strip_post_noise(raw)
        twice = strip_post_noise(once)
        assert once == twice

    def test_short_post_falls_through_safely(self):
        raw = "Hola."
        assert strip_post_noise(raw) == "Hola."

    def test_real_db_sample_short(self):
        """Sample from the actual data/tfm.db."""
        raw = (
            "s 7 0 m t 9 1 2 1 · DEJA DE PREOCUPARTE COMO UN GvS4N8 "
            "Es 1nútil y te hace ineficaz. Arruina tu estado de ánimo "
            "y te impide ser creativo y concentrarte.… "
            "Ver más 20 2 Comentar como Dani Alvez Facebook Facebook Facebook"
            " Facebook Facebook Facebook Facebook Facebook Facebook"
        )
        out = strip_post_noise(raw)
        assert out.startswith("DEJA DE PREOCUPARTE")
        assert "Ver más" not in out
        assert "Comentar como" not in out
        assert "Facebook" not in out
        assert "Dani Alvez" not in out

    def test_real_db_sample_with_url_spam(self):
        """URL-spam + author duplication from the actual data."""
        raw = (
            "r 3 2 0 8 i l m · Ella te vende la imagen de la chica "
            "buena.… Ver más mGBr281.com Dani Ella te vende la imagen "
            "de la chica buena. Su actuación es tan buena. r n a 0 o i l m "
            "662 35 97 Facebook Facebook Facebook Facebook Facebook Facebook"
            " Facebook Facebook Facebook Facebook Facebook"
        )
        out = strip_post_noise(raw)
        # The trailing short tokens + Facebook are stripped.
        assert "r n a 0 o i l m" not in out
        assert "Facebook" not in out
        # The intro is preserved.
        assert out.startswith("Ella te vende la imagen de la chica buena.")

    def test_author_prefix_stripped(self):
        raw = "Página de Prueba Esto es un post de prueba sobre violencia."
        out = strip_post_noise(raw, author="Página de Prueba")
        assert not out.startswith("Página de Prueba")
        assert out.startswith("Esto es un post")


class TestStripCommentNoise:
    """Tests for ``strip_comment_noise``."""

    def test_empty(self):
        body, ta, resp = strip_comment_noise("")
        assert body == ""
        assert ta is None
        assert resp == 0

    def test_none(self):
        body, ta, resp = strip_comment_noise(None)
        assert body == ""
        assert ta is None
        assert resp == 0

    def test_basic_extraction(self):
        raw = "Diamante Rosa Ahora resulta que los hombres no engañan e gusta Responder"
        body, ta, resp = strip_comment_noise(raw, known_author="Diamante Rosa")
        assert "Ahora resulta que los hombres no engañan" == body
        assert ta is None
        assert resp == 0

    def test_known_author_strips_full_name(self):
        raw = (
            "Juan J. Cinelli Siempre me ha parecido raro que la gente se preocupe "
            "5 sem Me gusta Responder 93"
        )
        body, ta, resp = strip_comment_noise(raw, known_author="Juan J. Cinelli")
        assert body.startswith("Siempre me ha parecido")
        assert ta == "5 sem"
        assert resp == 93

    def test_fan_destacado_prefix(self):
        raw = "Fan destacado Chuy Macias Hola correcto mensaje 1 sem Me gusta Responder 5"
        body, ta, resp = strip_comment_noise(raw, known_author="Chuy Macias")
        assert body == "Hola correcto mensaje"
        assert ta == "1 sem"
        assert resp == 5

    def test_editado_marker(self):
        raw = "Choco Zambo Da tristeza ver tanto 7 sem Me gusta Responder Editado 270"
        body, ta, resp = strip_comment_noise(raw, known_author="Choco Zambo")
        assert "Da tristeza ver tanto" in body
        assert ta == "7 sem"
        assert resp == 270

    def test_no_ui_suffix_keep_text_intact(self):
        raw = "Texto sin ningún indicador de tiempo al final"
        body, ta, resp = strip_comment_noise(raw, known_author="Texto")
        assert body == "sin ningún indicador de tiempo al final"
        assert ta is None
        assert resp == 0

    def test_body_equals_author_only(self):
        """When body equals the known author, the result is empty."""
        raw = "Manuel Lazo 12 h Me gusta Responder"
        body, ta, resp = strip_comment_noise(raw, known_author="Manuel Lazo")
        assert body == ""
        assert ta == "12 h"
        assert resp == 0

    def test_corrupted_trailing(self):
        raw = "Meza Jose Honestidad valores e gusta Responder"
        body, ta, resp = strip_comment_noise(raw, known_author="Meza Jose")
        assert "Honestidad valores" == body

    def test_strips_standalone_numbers_in_body(self):
        raw = "Juan Pérez Tengo 5 hijos y trabajo 10 horas 12 min Me gusta Responder 3"
        body, ta, resp = strip_comment_noise(raw, known_author="Juan Pérez")
        assert "5" not in body
        assert "10" not in body
        # time/responses extraction still works
        assert ta == "12 min"
        assert resp == 3

    def test_strips_ver_mas_comentarios(self):
        raw = "Juan Pérez Hola gente Ver más comentarios 22 min Me gusta Responder 5"
        body, ta, resp = strip_comment_noise(raw, known_author="Juan Pérez")
        assert "Ver más comentarios" not in body
        assert ta == "22 min"
        assert resp == 5

    def test_strips_ver_mas_respuestas(self):
        raw = "Juan Pérez Hola gente Ver más respuestas 22 min Me gusta Responder 5"
        body, ta, resp = strip_comment_noise(raw, known_author="Juan Pérez")
        assert "Ver más respuestas" not in body

    def test_preserves_user_truncation_marker(self):
        """The user-written ``… Ver más`` truncation marker at the end
        of a long body, before the trailing UI, is preserved."""
        raw = (
            "Gladys Carrillo mi madre siempre decía del agua mansa… Ver más "
            "3 sem Me gusta Responder 22"
        )
        body, ta, resp = strip_comment_noise(raw, known_author="Gladys Carrillo")
        assert "Ver más" in body
        assert ta == "3 sem"
        assert resp == 22

    def test_idempotent(self):
        raw = "Juan Pérez Esta es una opinión personal sobre las cosas 5 min Me gusta Responder"
        body1, ta1, resp1 = strip_comment_noise(raw, known_author="Juan Pérez")
        body2, ta2, resp2 = strip_comment_noise(body1, known_author="Juan Pérez")
        assert body1 == body2
        # time_ago/responses are already extracted so re-running
        # returns them as None/0.
        assert ta2 is None
        assert resp2 == 0

    def test_real_db_comments(self):
        """Run through all real DB samples."""
        cases = [
            (
                "Diamante Rosa Ahora resulta que los hombres no engañan e gusta Responder",
                "Diamante Rosa",
                "Ahora resulta que los hombres no engañan",
                None,
                0,
            ),
            (
                "Leonel Morales GIPHY 11 min Me gusta Responder",
                "Leonel Morales",
                "GIPHY",
                "11 min",
                0,
            ),
            (
                "Meza Jose Honestidad, responsabilidad y respeto son "
                "valores que te llevarán lejos en la vida. e gusta Responder",
                "Meza Jose",
                "Honestidad, responsabilidad y respeto son valores "
                "que te llevarán lejos en la vida.",
                None,
                0,
            ),
        ]
        for raw, author, exp_body, exp_ta, exp_resp in cases:
            body, ta, resp = strip_comment_noise(raw, known_author=author)
            assert body == exp_body
            assert ta == exp_ta
            assert resp == exp_resp


class TestStripShortTokenTail:
    """Tests for ``_strip_short_token_tail``."""

    def test_empty(self):
        assert _strip_short_token_tail("") == ""

    def test_clean_text_unchanged(self):
        clean = "Esta es una oración normal"
        assert _strip_short_token_tail(clean) == clean

    def test_short_tail_with_facebook(self):
        raw = "Hola mundo s 7 0 m 9 1 2 a 112 13 9 Facebook Facebook Facebook"
        out = _strip_short_token_tail(raw)
        assert out == "Hola mundo"

    def test_short_tail_without_facebook(self):
        raw = "Hola mundo s 7 0 m 9 1 2 a 112 13 9"
        out = _strip_short_token_tail(raw)
        assert out == "Hola mundo"

    def test_no_false_positive_on_normal_words(self):
        """Normal Spanish words shouldn't be matched as 'short tokens'."""
        clean = "El beta cae en la trampa de creer que esa palabra significa lo mismo para los dos"
        assert _strip_short_token_tail(clean) == clean

    def test_returns_unchanged_when_all_short(self):
        """If every token is short, don't strip (legitimate short input)."""
        raw = "a b c d e f g h i j"
        assert _strip_short_token_tail(raw) == raw

    def test_min_tokens_below_threshold(self):
        """5 short tokens is below the default 7-token threshold."""
        raw = "Hola 1 2 3 4 5"
        assert _strip_short_token_tail(raw) == raw


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
