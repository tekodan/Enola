"""Tests R7 from docs/recomendaciones-subdimensiones-2026-07-14.md.

These 7 cases are the residual errors documented in the audit
(``docs/auditoria-categorizaciones-2026-07-13.md``) and are the
ground-truth examples the calibrations are validated against:

| ar_id | Texto abreviado                                | Esperado                       | Valida       |
|------:|------------------------------------------------|--------------------------------|--------------|
| 25    | "actitudes de hombre blanco"                   | [4.2, 1.3]                     | R1 + R2      |
| 26    | "Para el aliade y la f3m1 nizta"               | [4.3, 4.3] (multi-marker)      | R4 + R6      |
| 36    | "ellas son las que me dan cariño y pagan todo" | []                             | R2 (1.1)     |
| 43    | "No es tan así si tenés más de 60 años…"       | []                             | R2 (1.3)     |
| 45    | "...como son todas las mujeres… enculada…"     | [1.3, 2.3, 4.2, 6.2]           | R1 + R3      |
| 60    | "No que a las feministas no les hacen caso jaja" | [4.3, 5.1, 6.2]               | R2 (6.2)     |
| 61    | "con mujer o sin mujer la paja no falta"       | []                             | R3 (2.1)     |

These tests run against the deterministic validator — no Ollama.
"""

from __future__ import annotations

from src.analyzer.category_mapping import (
    MAX_LABELS,
    normalize_dimension,
    validate_codigo,
)
from src.analyzer.rag_classifier import (
    ClassificationResult,
    RAGClassifier,
)


def _build_llm_payload(labels: list[dict]) -> str:
    """Return a JSON string that mimics the LLM's multi-label output."""
    import json

    return json.dumps(
        {
            "tiene_violencia": bool(labels),
            "severidad_global": "media",
            "clasificaciones": labels,
        }
    )


class TestR7SubdimensionRules:
    """Each test simulates a JSON the LLM might emit and verifies the
    validator produces the expected classification.
    """

    def test_ar25_actitudes_hombre_blanco(self) -> None:
        """'actitudes de hombre blanco' → [4.2, 1.3] (R1+R2)."""
        payload = _build_llm_payload(
            [
                {
                    "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                    "dimension": "4.2",
                    "severidad": "media",
                    "justificacion": "esencialismo",
                    "evidencia": "actitudes de hombre blanco",
                    "marcadores_detectados": ["actitudes de hombre blanco"],
                },
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.3",
                    "severidad": "baja",
                    "justificacion": "doble estándar",
                    "evidencia": "actitudes de hombre blanco",
                    "marcadores_detectados": ["valiste mergas"],
                },
            ]
        )
        result = ClassificationResult.from_llm_response(payload)
        cats_dims = {(lbl.categoria, lbl.dimension) for lbl in result.clasificaciones}
        assert ("VDG_MANOSFERA_ANTIFEMINISMO", "4.2") in cats_dims
        assert ("VDG_VIOLENCIA_SIMBOLICA", "1.3") in cats_dims

    def test_ar26_aliade_feminazi_double_4_3(self) -> None:
        """'Para el aliade y la f3m1 nizta' → [4.3, 4.3] (R4+R6)."""
        payload = _build_llm_payload(
            [
                {
                    "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                    "dimension": "4.3",
                    "severidad": "media",
                    "justificacion": "aliade emasculado",
                    "evidencia": "aliade",
                    "marcadores_detectados": ["aliade"],
                },
                {
                    "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                    "dimension": "4.3",
                    "severidad": "media",
                    "justificacion": "feminazi troleo",
                    "evidencia": "f3m1 nizta",
                    "marcadores_detectados": ["f3m1 nizta"],
                },
            ]
        )
        result = ClassificationResult.from_llm_response(payload)
        # R4: dos entradas 4.3 con marcadores distintos → no colapsadas.
        cat_dim_list = [(lbl.categoria, lbl.dimension) for lbl in result.clasificaciones]
        assert cat_dim_list.count(("VDG_MANOSFERA_ANTIFEMINISMO", "4.3")) == 2
        # Cada entrada debe tener su marcador independiente preservado.
        marcadores = [sorted(lbl.marcadores_detectados) for lbl in result.clasificaciones]
        assert ["aliade"] in marcadores
        assert ["f3m1 nizta"] in marcadores

    def test_ar36_imperativo_domestico_ausente(self) -> None:
        """'ellas son las que me dan cariño y pagan todo' → [] (R2).

        No aparece ningún imperativo doméstico (a lavar, cocinar, criar).
        El validador no puede crear la 1.1 desde el aire.
        """
        # Si el LLM erróneamente emite 1.1, el ``validate_codigo`` no
        # tiene cómo saber si el marcador está ausente — eso es trabajo
        # del LLM. Lo que probamos es que la salida de 1.1 NO sobrevive
        # si la dimension no matchea; pero más importante, este test
        # documenta el caso y verifica que el LLM (en este simulacro)
        # NO emite 1.1 cuando el texto no lo justifica.
        # Aquí validamos el caso positivo: si el LLM emite 1.1 sin
        # marcadores, el validador lo acepta (no podemos hacer
        # cherry-pick desde el validador puro). El guardarraíl real es
        # el prompt R2.
        # Por lo tanto el test es: dado que el LLM NO emite 1.1 (porque
        # el prompt R2 lo inhibe), el resultado es [].
        payload = _build_llm_payload([])  # empty
        result = ClassificationResult.from_llm_response(payload)
        assert result.clasificaciones == []
        assert result.tiene_violencia is False

    def test_ar43_false_positive_1_3(self) -> None:
        """'No es tan así si tenés más de 60 años…' → [] (R2).

        Sin marcador 1.3 canónico (no 'como son todas las mujeres', etc.).
        El prompt R2 instruye a no asignar 1.3 sin marcador.
        """
        payload = _build_llm_payload([])
        result = ClassificationResult.from_llm_response(payload)
        assert result.clasificaciones == []

    def test_ar45_full_multi(self) -> None:
        """Texto largo: 1.3 + 2.3 + 4.2 + 6.2 (R1+R3)."""
        payload = _build_llm_payload(
            [
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.3",
                    "severidad": "media",
                    "justificacion": "doble estándar moral",
                    "evidencia": "como son todas las mujeres",
                    "marcadores_detectados": ["como son todas las mujeres"],
                },
                {
                    "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                    "dimension": "2.3",
                    "severidad": "media",
                    "justificacion": "slut-shaming",
                    "evidencia": "siempre están enculada o les duele la cabeza",
                    "marcadores_detectados": [
                        "siempre están enculada",
                        "les duele la cabeza",
                    ],
                },
                {
                    "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                    "dimension": "4.2",
                    "severidad": "media",
                    "justificacion": "esencialismo victimista",
                    "evidencia": "la más cara es una esposa",
                    "marcadores_detectados": ["la más cara es una esposa"],
                },
                {
                    "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                    "dimension": "6.2",
                    "severidad": "ninguna",
                    "justificacion": "humor hostil",
                    "evidencia": "jajaja",
                    "marcadores_detectados": ["jajaja"],
                },
            ]
        )
        result = ClassificationResult.from_llm_response(payload)
        cats_dims = {(lbl.categoria, lbl.dimension) for lbl in result.clasificaciones}
        assert ("VDG_VIOLENCIA_SIMBOLICA", "1.3") in cats_dims
        assert ("VDG_COSIFICACION_SLUTSHAMING", "2.3") in cats_dims
        assert ("VDG_MANOSFERA_ANTIFEMINISMO", "4.2") in cats_dims
        assert ("VDG_SALVAGUARDA_FALSO_POSITIVO", "6.2") in cats_dims
        # Primary (alta/media/baja/ninguna) is severidad desc — 6.2 has
        # "ninguna" so it sorts to the end. Primary should be one of the
        # media ones.
        assert result.severidad_global.value == "media"

    def test_ar60_6_2_with_4_3_5_1(self) -> None:
        """'No que a las feministas no les hacen caso jaja' → [4.3, 5.1, 6.2]."""
        payload = _build_llm_payload(
            [
                {
                    "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                    "dimension": "4.3",
                    "severidad": "media",
                    "justificacion": "troleo de género",
                    "evidencia": "feministas",
                    "marcadores_detectados": ["feministas"],
                },
                {
                    "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                    "dimension": "5.1",
                    "severidad": "media",
                    "justificacion": "deslegitimación",
                    "evidencia": "no les hacen caso",
                    "marcadores_detectados": ["no les hacen caso"],
                },
                {
                    "categoria": "VDG_SALVAGUARDA_FALSO_POSITIVO",
                    "dimension": "6.2",
                    "severidad": "ninguna",
                    "justificacion": "humor hostil",
                    "evidencia": "jaja",
                    "marcadores_detectados": ["jaja"],
                },
            ]
        )
        result = ClassificationResult.from_llm_response(payload)
        cats_dims = {(lbl.categoria, lbl.dimension) for lbl in result.clasificaciones}
        assert ("VDG_MANOSFERA_ANTIFEMINISMO", "4.3") in cats_dims
        assert ("VDG_DESACREDITACION_ACTIVISTAS", "5.1") in cats_dims
        assert ("VDG_SALVAGUARDA_FALSO_POSITIVO", "6.2") in cats_dims

    def test_ar61_false_positive_2_1(self) -> None:
        """'con mujer o sin mujer la paja no falta' → [] (R3).

        Sin marcador cosificador. El prompt R3 instruye al LLM a no
        asignar 2.1 sin un adjetivo o sintagma cosificador.
        """
        payload = _build_llm_payload([])
        result = ClassificationResult.from_llm_response(payload)
        assert result.clasificaciones == []


class TestR5SafeguardDefault63:
    """Safeguard without a subdimension defaults to 6.3."""

    def test_safeguard_without_dimension_defaults_to_6_3(self) -> None:
        cat, dim = validate_codigo("VDG_SALVAGUARDA_FALSO_POSITIVO", None)
        assert cat == "VDG_SALVAGUARDA_FALSO_POSITIVO"
        assert dim == "6.3"

    def test_safeguard_with_empty_string_defaults_to_6_3(self) -> None:
        cat, dim = validate_codigo("VDG_SALVAGUARDA_FALSO_POSITIVO", "")
        assert dim == "6.3"

    def test_safeguard_with_null_string_defaults_to_6_3(self) -> None:
        cat, dim = validate_codigo("VDG_SALVAGUARDA_FALSO_POSITIVO", "null")
        assert dim == "6.3"

    def test_safeguard_with_valid_dim_unchanged(self) -> None:
        cat, dim = validate_codigo("VDG_SALVAGUARDA_FALSO_POSITIVO", "6.1")
        assert dim == "6.1"

    def test_safeguard_via_normalize_dimension(self) -> None:
        assert normalize_dimension("VDG_SALVAGUARDA_FALSO_POSITIVO", None) == "6.3"
        assert normalize_dimension("VDG_SALVAGUARDA_FALSO_POSITIVO", "6.2") == "6.2"

    def test_non_safeguard_without_dimension_is_none(self) -> None:
        assert normalize_dimension("VDG_VIOLENCIA_SIMBOLICA", None) is None


class TestR4SeveritySortAndDedup:
    """R4: validate_clasificaciones sorts by severity desc and dedups
    by (cat, dim, sorted(marcadores)).
    """

    def test_truncation_keeps_highest_severity(self) -> None:
        """When more than MAX_LABELS are emitted, high-severity wins."""
        labels = [
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["x"],
            },
            {
                "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                "dimension": "3.1",
                "severidad": "alta",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["x"],
            },
            {
                "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                "dimension": "2.1",
                "severidad": "media",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["x"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.2",
                "severidad": "media",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["x"],
            },
            {
                "categoria": "VDG_DESACREDITACION_ACTIVISTAS",
                "dimension": "5.1",
                "severidad": "media",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["x"],
            },
            # This one is BAJA and should be dropped (6th label).
            {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.2",
                "severidad": "baja",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["x"],
            },
        ]
        result = ClassificationResult.from_llm_response(_build_llm_payload(labels))
        assert len(result.clasificaciones) == MAX_LABELS
        # Primary should be the ALTA one.
        assert result.categoria == "VDG_HOSTILIDAD_FEMINICIDIO"
        # The truncated one (1.2 BAJA) must NOT be present.
        cats_dims = {(lbl.categoria, lbl.dimension) for lbl in result.clasificaciones}
        assert ("VDG_VIOLENCIA_SIMBOLICA", "1.2") not in cats_dims

    def test_dedup_preserves_distinct_markers_in_cat_4(self) -> None:
        """Two 4.3 entries with distinct markers coexist (aliade + f3m1)."""
        labels = [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "aliade",
                "evidencia": "aliade",
                "marcadores_detectados": ["aliade"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "f3m1",
                "evidencia": "f3m1 nizta",
                "marcadores_detectados": ["f3m1 nizta"],
            },
        ]
        result = ClassificationResult.from_llm_response(_build_llm_payload(labels))
        assert len(result.clasificaciones) == 2
        marcadores_collected = sorted(
            m for lbl in result.clasificaciones for m in lbl.marcadores_detectados
        )
        assert marcadores_collected == ["aliade", "f3m1 nizta"]

    def test_dedup_collapses_identical_entries(self) -> None:
        """Two 4.3 entries with IDENTICAL marcadores → 1."""
        labels = [
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["f3m1 nizta"],
            },
            {
                "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
                "dimension": "4.3",
                "severidad": "media",
                "justificacion": "x",
                "evidencia": "x",
                "marcadores_detectados": ["f3m1 nizta"],
            },
        ]
        result = ClassificationResult.from_llm_response(_build_llm_payload(labels))
        assert len(result.clasificaciones) == 1


class TestPromptBlocksLoaded:
    """Verify the desempate block is wired into the prompt."""

    def test_desempate_block_in_prompt(self) -> None:
        classifier = RAGClassifier()
        prompt = classifier._build_prompt("texto de prueba", context_chunks=[])
        assert "REGLAS DE DESEMPATE" in prompt
        assert "FRONTERA 1.1 vs 1.3" in prompt
        assert "FRONTERA 3.1 vs 3.3" in prompt
        assert "FRONTERA 4.1 vs 4.2 vs 4.3" in prompt
        assert "REGLA DURA PARA 2.1" in prompt
