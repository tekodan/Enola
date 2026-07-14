"""Unit tests for the validation helpers in ``src.ui.validacion``."""

from __future__ import annotations

from src.analyzer.category_mapping import Categoria
from src.ui.validacion import (
    MAX_LABELS,
    build_feedback_payload,
    categoria_choices,
    dimension_options_for,
    feedback_status_label,
    filter_analysis_for_validation,
    is_valid_categoria_for_dimension,
    normalize_label_row,
)


def _analysis(id: int, *, content_type: str = "post") -> dict[str, object]:
    return {
        "id": id,
        "content_type": content_type,
        "content_id": f"{content_type}-{id}",
        "tiene_violencia": "true",
        "categoria": "VDG_VIOLENCIA_SIMBOLICA",
        "dimension": "1.1",
    }


def _feedback(ar_id: int, *, agrees: str = "false") -> dict[str, object]:
    return {
        "analysis_result_id": ar_id,
        "agrees": agrees,
        "corrected_categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
    }


class TestCategoriaChoices:
    def test_choices_include_all_canonical_categories(self):
        """``categoria_choices`` returns a ``{value: label}`` dict.

        The dict format is required because NiceGUI 3.x ``ui.select``
        only accepts ``dict`` (or a flat ``list[str]``) as ``options``;
        the older ``[(label, value), ...]`` tuple form raises
        ``ValueError: Invalid value`` and silently breaks the widget tree.
        """
        pairs = categoria_choices()
        assert isinstance(pairs, dict)
        codes = [v for v in pairs if v]
        assert Categoria.VDG_VIOLENCIA_SIMBOLICA.value in codes
        assert Categoria.VDG_COSIFICACION_SLUTSHAMING.value in codes
        assert Categoria.VDG_HOSTILIDAD_FEMINICIDIO.value in codes
        assert Categoria.VDG_MANOSFERA_ANTIFEMINISMO.value in codes
        assert Categoria.VDG_DESACREDITACION_ACTIVISTAS.value in codes

    def test_choices_include_sin_categoria_sentinel(self):
        pairs = categoria_choices()
        assert "" in pairs
        assert "Sin categor" in pairs[""]


class TestDimensionOptions:
    def test_dimension_for_violencia_simbolica(self):
        options = dimension_options_for(Categoria.VDG_VIOLENCIA_SIMBOLICA.value)
        assert isinstance(options, dict)
        codes = [v for v in options if v]
        assert codes == ["1.1", "1.2", "1.3"]

    def test_dimension_for_ninguna_returns_empty_pair_only(self):
        options = dimension_options_for(Categoria.NINGUNA.value)
        assert options == {"": "(Sin dimensión)"}

    def test_dimension_for_empty_returns_empty_pair_only(self):
        options = dimension_options_for("")
        assert options == {"": "(Sin dimensión)"}

    def test_dimension_labels_include_descriptions(self):
        options = dimension_options_for(Categoria.VDG_COSIFICACION_SLUTSHAMING.value)
        # Each non-empty code label has the form "<code> — <desc>"
        first_label = next(iter(options.values()))
        assert " — " in first_label


class TestValidation:
    def test_dimension_must_belong_to_categoria(self):
        assert is_valid_categoria_for_dimension(Categoria.VDG_VIOLENCIA_SIMBOLICA.value, "1.2")
        assert not is_valid_categoria_for_dimension(Categoria.VDG_VIOLENCIA_SIMBOLICA.value, "2.1")

    def test_empty_dimension_valid(self):
        assert is_valid_categoria_for_dimension(Categoria.VDG_VIOLENCIA_SIMBOLICA.value, "")
        assert is_valid_categoria_for_dimension("", "")

    def test_empty_categoria_with_dimension_invalid(self):
        assert not is_valid_categoria_for_dimension("", "1.1")


class TestBuildFeedbackPayload:
    def test_agreement_payload_has_no_overrides(self):
        payload = build_feedback_payload(
            analysis_result_id=1,
            content_type="post",
            content_id="p1",
            text_snapshot="x",
            agrees=True,
            reason="",
            corrected_categoria="ignored",
            corrected_dimension="ignored",
            corrected_justificacion="ignored",
        )
        assert payload["agrees"] == "true"
        assert payload["corrected_categoria"] is None
        assert payload["corrected_dimension"] is None
        assert payload["corrected_justificacion"] is None

    def test_disagreement_payload_keeps_overrides(self):
        payload = build_feedback_payload(
            analysis_result_id=2,
            content_type="comment",
            content_id="c1",
            text_snapshot="y",
            agrees=False,
            reason="mal categorizado",
            corrected_categoria="VDG_VIOLENCIA_SIMBOLICA",
            corrected_dimension="1.1",
            corrected_justificacion="corr",
            reviewer="kim",
        )
        assert payload["agrees"] == "false"
        assert payload["corrected_categoria"] == "VDG_VIOLENCIA_SIMBOLICA"
        assert payload["corrected_dimension"] == "1.1"
        assert payload["corrected_justificacion"] == "corr"
        assert payload["reviewer"] == "kim"

    def test_empty_optional_strings_become_none(self):
        payload = build_feedback_payload(
            analysis_result_id=3,
            content_type="post",
            content_id="p",
            text_snapshot="",
            agrees=False,
            reason="   ",
            corrected_categoria="",
            corrected_dimension="",
            corrected_justificacion="",
        )
        assert payload["reason"] is None
        assert payload["corrected_categoria"] is None
        assert payload["corrected_dimension"] is None
        assert payload["corrected_justificacion"] is None


class TestFilterAnalysis:
    def test_pending_when_no_feedback(self):
        rows = [_analysis(1), _analysis(2)]
        out = filter_analysis_for_validation(rows, [])
        assert all(r["feedback_status"] == "pending" for r in out)
        assert all(r["feedback_row"] is None for r in out)

    def test_filters_by_review_state(self):
        rows = [_analysis(i) for i in range(1, 4)]
        fb_rows = [_feedback(1, agrees="true"), _feedback(2, agrees="false")]

        out = filter_analysis_for_validation(rows, fb_rows, review_state="agreed")
        assert [r["id"] for r in out] == [1]

        out = filter_analysis_for_validation(rows, fb_rows, review_state="disagreed")
        assert [r["id"] for r in out] == [2]

        out = filter_analysis_for_validation(rows, fb_rows, review_state="pending")
        assert [r["id"] for r in out] == [3]

        out = filter_analysis_for_validation(rows, fb_rows, review_state="all")
        assert len(out) == 3

    def test_filter_by_content_type(self):
        rows = [_analysis(1, content_type="post"), _analysis(2, content_type="comment")]
        out = filter_analysis_for_validation(rows, [], content_type="comment")
        assert len(out) == 1
        assert out[0]["id"] == 2

    def test_filter_by_only_violent(self):
        rows = [
            {**_analysis(1), "tiene_violencia": "true"},
            {**_analysis(2), "tiene_violencia": "false"},
        ]
        out = filter_analysis_for_validation(rows, [], only_violent=True)
        assert [r["id"] for r in out] == [1]


class TestFeedbackStatusLabel:
    def test_agreement_label(self):
        assert "De acuerdo" in feedback_status_label({"agrees": "true"})

    def test_disagreement_label(self):
        assert "Corregido" in feedback_status_label({"agrees": "false"})

    def test_pending_label(self):
        assert "Pendiente" in feedback_status_label({})


class TestBuildFeedbackPayloadMultiLabel:
    def test_multi_label_routes_through_corrected_labels(self):
        """Passing corrected_labels propagates the list and mirrors primary."""
        payload = build_feedback_payload(
            analysis_result_id=1,
            content_type="post",
            content_id="p1",
            text_snapshot="x",
            agrees=False,
            corrected_labels=[
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "baja",
                    "justificacion": "estereotipo",
                },
                {
                    "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                    "dimension": "3.1",
                    "severidad": "alta",
                    "justificacion": "amenaza",
                },
            ],
        )
        assert payload["agrees"] == "false"
        assert len(payload["corrected_labels"]) == 2
        # Primary (highest severity) mirrored to the flat columns.
        assert payload["corrected_categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert payload["corrected_dimension"] == "3.1"
        assert payload["corrected_justificacion"] == "amenaza"

    def test_legacy_single_label_built_into_one_element(self):
        """Passing corrected_categoria/.. is wrapped into corrected_labels."""
        payload = build_feedback_payload(
            analysis_result_id=2,
            content_type="post",
            content_id="p1",
            text_snapshot="x",
            agrees=False,
            corrected_categoria="VDG_COSIFICACION_SLUTSHAMING",
            corrected_dimension="2.2",
            corrected_justificacion="zorra",
        )
        assert len(payload["corrected_labels"]) == 1
        assert payload["corrected_labels"][0]["categoria"] == ("VDG_COSIFICACION_SLUTSHAMING")

    def test_agreement_payload_has_no_corrected_labels(self):
        payload = build_feedback_payload(
            analysis_result_id=3,
            content_type="post",
            content_id="p1",
            text_snapshot="x",
            agrees=True,
            corrected_labels=[{"categoria": "X", "dimension": "1.1"}],
        )
        assert payload["agrees"] == "true"
        assert payload["corrected_labels"] == []
        assert payload["corrected_categoria"] is None

    def test_caps_at_max_labels(self):
        # Use distinct valid (categoria, dimension) pairs spread across
        # the 6 categories so the cap really is exercised.
        labels: list[dict] = []
        for i in range(MAX_LABELS + 3):
            cat_idx = i % 6
            cat_code = [
                "VDG_VIOLENCIA_SIMBOLICA",
                "VDG_COSIFICACION_SLUTSHAMING",
                "VDG_HOSTILIDAD_FEMINICIDIO",
                "VDG_MANOSFERA_ANTIFEMINISMO",
                "VDG_SALVAGUARDA_FALSO_POSITIVO",
                "VDG_DESACREDITACION_ACTIVISTAS",
            ][cat_idx]
            dim = f"{cat_idx + 1}.1"
            labels.append({"categoria": cat_code, "dimension": dim})
        payload = build_feedback_payload(
            analysis_result_id=4,
            content_type="post",
            content_id="p1",
            text_snapshot="x",
            agrees=False,
            corrected_labels=labels,
        )
        assert len(payload["corrected_labels"]) == MAX_LABELS

    def test_dedupes_duplicate_pairs(self):
        labels = [
            {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"},
            {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"},
        ]
        payload = build_feedback_payload(
            analysis_result_id=5,
            content_type="post",
            content_id="p1",
            text_snapshot="x",
            agrees=False,
            corrected_labels=labels,
        )
        assert len(payload["corrected_labels"]) == 1

    def test_invalid_categoria_is_dropped(self):
        labels = [
            {"categoria": "inventada", "dimension": "9.9"},
            {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1"},
        ]
        payload = build_feedback_payload(
            analysis_result_id=6,
            content_type="post",
            content_id="p1",
            text_snapshot="x",
            agrees=False,
            corrected_labels=labels,
        )
        assert len(payload["corrected_labels"]) == 1
        assert payload["corrected_labels"][0]["categoria"] == ("VDG_VIOLENCIA_SIMBOLICA")


class TestNormalizeLabelRow:
    def test_normalizes_basic_fields(self):
        clean = normalize_label_row(
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.1",
                "severidad": "alta",
                "justificacion": "j",
                "evidencia": "e",
                "marcadores_detectados": ["a", "b"],
                "es_falso_positivo_probable": True,
            }
        )
        assert clean is not None
        assert clean["categoria"] == "VDG_VIOLENCIA_SIMBOLICA"
        assert clean["severidad"] == "alta"
        assert clean["marcadores_detectados"] == ["a", "b"]
        assert clean["es_falso_positivo_probable"] is True

    def test_marcadores_from_csv_string(self):
        clean = normalize_label_row(
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "marcadores_detectados": "zorra, puta",
            }
        )
        assert clean["marcadores_detectados"] == ["zorra", "puta"]

    def test_returns_none_for_missing_categoria(self):
        assert normalize_label_row({}) is None
        assert normalize_label_row({"categoria": ""}) is None

    def test_severidad_string_normalized(self):
        clean = normalize_label_row(
            {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "severidad": "alta-extrema"}
        )
        assert clean["severidad"] == "alta"
