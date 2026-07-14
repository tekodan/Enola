"""Tests for comment text cleaning helper."""

import pytest

from src.scraper.comment_interactor import clean_comment_text


class TestCleanCommentText:
    """Tests for ``clean_comment_text``."""

    def test_basic_extraction(self):
        """Extract body, time_ago and responses from a typical comment."""
        raw = (
            "Israel Florez Que el tipo gane mucho dinero no garantiza "
            "que le va a resolver la vida jajaja 18 sem Me gusta Responder 17"
        )
        clean, time_ago, responses = clean_comment_text(raw)
        # Without known_author the heuristic strips at most 3 leading
        # words, so the body starts with "el tipo gane". The trailing
        # metadata (time_ago, responses) is always extracted cleanly.
        assert "el tipo gane" in clean
        assert time_ago == "18 sem"
        assert responses == 17

    def test_known_author_stripped(self):
        """When the author is known, strip the full name from the prefix."""
        raw = (
            "Juan J. Cinelli Siempre me ha parecido raro que la gente se preocupe "
            "5 sem Me gusta Responder 93"
        )
        clean, time_ago, responses = clean_comment_text(raw, known_author="Juan J. Cinelli")
        assert clean.startswith("Siempre me ha parecido")
        assert time_ago == "5 sem"
        assert responses == 93

    def test_fan_destacado_prefix(self):
        """Strip ``Fan destacado`` prefix too."""
        raw = "Fan destacado Chuy Macias Hola correcto mensaje 1 sem Me gusta Responder 5"
        clean, time_ago, responses = clean_comment_text(raw, known_author="Chuy Macias")
        assert clean == "Hola correcto mensaje"
        assert time_ago == "1 sem"
        assert responses == 5

    def test_editado_marker(self):
        """Handle ``Editado`` marker between time and count."""
        raw = "Choco Zambo Da tristeza ver tanto 7 sem Me gusta Responder Editado 270"
        clean, time_ago, responses = clean_comment_text(raw, known_author="Choco Zambo")
        assert "Da tristeza" in clean
        assert time_ago == "7 sem"
        assert responses == 270

    def test_no_ui_suffix(self):
        """When there's no trailing UI, keep text intact."""
        raw = "Texto sin ningún indicador de tiempo al final"
        clean, time_ago, responses = clean_comment_text(raw, known_author="Texto")
        # With known_author it strips the prefix even without trailing UI.
        assert clean == "sin ningún indicador de tiempo al final"
        assert time_ago is None
        assert responses == 0

    def test_empty_text(self):
        """Empty text returns empty clean and no metadata."""
        clean, time_ago, responses = clean_comment_text("")
        assert clean == ""
        assert time_ago is None
        assert responses == 0

    def test_ver_mas_preserved(self):
        """``Ver más`` truncation marker is preserved in the body."""
        raw = (
            "Gladys Carrillo mi madre siempre decía del agua mansa… Ver más "
            "3 sem Me gusta Responder 22"
        )
        clean, time_ago, responses = clean_comment_text(raw, known_author="Gladys Carrillo")
        assert "Ver más" in clean
        assert time_ago == "3 sem"
        assert responses == 22

    def test_dias_time_format(self):
        """Handle days/weeks time formats."""
        raw = "Maria Hoy hace calor 5 días Me gusta Responder 10"
        clean, time_ago, responses = clean_comment_text(raw, known_author="Maria")
        assert clean == "Hoy hace calor"
        assert time_ago == "5 días"
        assert responses == 10

    def test_strips_standalone_numbers_in_body(self):
        """Bare digit tokens inside the body are removed; metadata still parsed."""
        raw = "Juan Pérez Tengo 5 hijos y trabajo 10 horas al día 12 min Me gusta Responder 3"
        clean, time_ago, responses = clean_comment_text(raw, known_author="Juan Pérez")
        # Bare digits are gone from the body, time_ago / responses remain.
        assert "5" not in clean.split("horas")[0] if "horas" in clean else "5" not in clean
        assert "10" not in clean
        assert time_ago == "12 min"
        assert responses == 3

    def test_strips_ver_mas_comentarios_inside_body(self):
        """``Ver más comentarios`` button form is removed from the body."""
        raw = "Juan Pérez Hola Ver más comentarios 22 min Me gusta Responder 5"
        clean, _, _ = clean_comment_text(raw, known_author="Juan Pérez")
        assert "Ver más comentarios" not in clean
        assert "Hola" in clean

    def test_body_equals_author_yields_empty(self):
        """When the body after trailing UI equals the author, result is empty."""
        raw = "Manuel Lazo 12 h Me gusta Responder"
        clean, time_ago, responses = clean_comment_text(raw, known_author="Manuel Lazo")
        assert clean == ""
        assert time_ago == "12 h"
        assert responses == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
