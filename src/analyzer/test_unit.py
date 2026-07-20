"""Unit tests for analyzer module."""

from unittest.mock import MagicMock

from src.analyzer.category_mapping import Categoria, primary_label
from src.analyzer.embeddings import PostEmbeddings
from src.analyzer.rag_classifier import ClassificationResult, LabelAssignment, RAGClassifier
from src.analyzer.violence_types import Severity


class TestPrimaryLabel:
    """Pins the multi-label ``primary_label`` behaviour used to mirror
    the highest-severity label into the flat ``analysis_results``
    columns.

    Regression: ``bool('false') == True`` in Python — the old code
    returned ``'true'`` whenever the input string was non-empty,
    silently flipping every false-positive flag across the pipeline.
    """

    def test_empty_returns_neutral_defaults(self):
        out = primary_label([])
        assert out["categoria"] == "ninguna"
        assert out["dimension"] is None
        assert out["severidad"] == "ninguna"
        assert out["es_falso_positivo_probable"] == "false"

    def test_picks_highest_severity(self):
        out = primary_label(
            [
                {"categoria": "VDG_VIOLENCIA_SIMBOLICA", "dimension": "1.1", "severidad": "baja"},
                {
                    "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                    "dimension": "3.1",
                    "severidad": "alta",
                },
                {
                    "categoria": "VDG_COSIFICACION_SLUTSHAMING",
                    "dimension": "2.3",
                    "severidad": "media",
                },
            ]
        )
        assert out["categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert out["dimension"] == "3.1"
        assert out["severidad"] == "alta"

    def test_fpp_string_false_coerces_to_false(self):
        """The string 'false' must NOT be treated as truthy."""
        out = primary_label(
            [
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "media",
                    "es_falso_positivo_probable": "false",
                }
            ]
        )
        assert out["es_falso_positivo_probable"] == "false"

    def test_fpp_string_true_coerces_to_true(self):
        out = primary_label(
            [
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "media",
                    "es_falso_positivo_probable": "true",
                }
            ]
        )
        assert out["es_falso_positivo_probable"] == "true"

    def test_fpp_bool_true(self):
        out = primary_label(
            [
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "media",
                    "es_falso_positivo_probable": True,
                }
            ]
        )
        assert out["es_falso_positivo_probable"] == "true"

    def test_fpp_bool_false(self):
        out = primary_label(
            [
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "media",
                    "es_falso_positivo_probable": False,
                }
            ]
        )
        assert out["es_falso_positivo_probable"] == "false"

    def test_fpp_int_one(self):
        out = primary_label(
            [
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "media",
                    "es_falso_positivo_probable": 1,
                }
            ]
        )
        assert out["es_falso_positivo_probable"] == "true"


class TestSeverity:
    """Tests for Severity enum (the only hardcoded enum in the module)."""

    def test_all_levels(self):
        """Test all severity levels exist."""
        assert Severity.BAJA.value == "baja"
        assert Severity.MEDIA.value == "media"
        assert Severity.ALTA.value == "alta"
        assert Severity.NINGUNA.value == "ninguna"


class TestClassificationResult:
    """Tests for ClassificationResult model (ChromaDB-driven + canonical taxonomy)."""

    def test_create_default(self):
        """Test creating with defaults."""
        result = ClassificationResult()
        assert result.tiene_violencia is False
        assert result.categoria == "ninguna"
        assert result.dimension is None
        assert result.severidad == Severity.NINGUNA
        assert result.marcadores_detectados == []
        assert result.es_falso_positivo_probable is False
        assert result.score_ajuste is None
        assert result.regla_disparada is None

    def test_create_full(self):
        """Test creating with all fields."""
        result = ClassificationResult(
            tiene_violencia=True,
            confianza=0.9,
            clasificaciones=[
                LabelAssignment(
                    categoria="VDG_HOSTILIDAD_FEMINICIDIO",
                    dimension="3.1",
                    severidad=Severity.ALTA,
                    justificacion="Amenaza de muerte directa",
                    evidencia="te voy a matar",
                    regla_disparada="Cat 3 / Regla 1",
                    marcadores_detectados=["matar", "te voy a"],
                    es_falso_positivo_probable=False,
                    score_ajuste=0.95,
                )
            ],
        )
        assert result.tiene_violencia is True
        assert result.categoria == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert result.dimension == "3.1"
        assert result.severidad == Severity.ALTA
        assert result.confianza == 0.9
        assert result.marcadores_detectados == ["matar", "te voy a"]
        assert result.es_falso_positivo_probable is False
        assert result.score_ajuste == 0.95

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ClassificationResult(
            tiene_violencia=True,
            clasificaciones=[
                LabelAssignment(
                    categoria="VDG_COSIFICACION_SLUTSHAMING",
                    dimension="2.2",
                    severidad=Severity.MEDIA,
                    justificacion="Slut-shaming",
                    evidencia="zorra",
                )
            ],
        )
        data = result.to_dict()
        assert data["tiene_violencia"] is True
        assert data["categoria"] == "VDG_COSIFICACION_SLUTSHAMING"
        assert data["dimension"] == "2.2"
        assert data["severidad"] == "media"
        assert data["marcadores_detectados"] == []

    def test_from_llm_response_normalizes_categoria(self):
        """Test that free-form categoria is normalized to canonical VDG_*."""
        response = """{
            "tiene_violencia": true,
            "categoria": "violencia simbolica",
            "dimension": "1.2",
            "severidad": "baja",
            "confianza": 0.7,
            "justificacion": "Estereotipo",
            "evidencia": "calladita"
        }"""
        result = ClassificationResult.from_llm_response(response)
        assert result.categoria == "VDG_VIOLENCIA_SIMBOLICA"
        assert result.dimension == "1.2"
        assert result.severidad == Severity.BAJA

    def test_from_llm_response_normalizes_severity_compound(self):
        """Compound severities like 'alta-extrema' map to ALTA."""
        response = """{
            "tiene_violencia": true,
            "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
            "dimension": "3.1",
            "severidad": "alta-extrema",
            "confianza": 0.95
        }"""
        result = ClassificationResult.from_llm_response(response)
        assert result.severidad == Severity.ALTA

    def test_from_llm_response_rejects_invalid_categoria(self):
        """Out-of-set categoria gets normalized to 'ninguna' with a warning."""
        response = """{
            "tiene_violencia": true,
            "categoria": "inventada",
            "dimension": "1.1",
            "severidad": "alta"
        }"""
        result = ClassificationResult.from_llm_response(response)
        assert result.categoria == "ninguna"
        assert result.dimension is None

    def test_from_llm_response_rejects_invalid_dimension(self):
        """Dimension outside category's allowed list → None."""
        response = """{
            "tiene_violencia": true,
            "categoria": "VDG_VIOLENCIA_SIMBOLICA",
            "dimension": "5.1",
            "severidad": "alta"
        }"""
        result = ClassificationResult.from_llm_response(response)
        assert result.categoria == "VDG_VIOLENCIA_SIMBOLICA"
        assert result.dimension is None

    def test_from_llm_response_parses_new_fields(self):
        """The 4 new fields are extracted from the LLM response."""
        response = """{
            "tiene_violencia": true,
            "categoria": "VDG_MANOSFERA_ANTIFEMINISMO",
            "dimension": "4.2",
            "severidad": "media",
            "regla_disparada": "Cat 4 / Regla 2",
            "marcadores_detectados": ["feminazi", "mangina"],
            "es_falso_positivo_probable": false,
            "score_ajuste": 0.8
        }"""
        result = ClassificationResult.from_llm_response(response)
        assert result.regla_disparada == "Cat 4 / Regla 2"
        assert result.marcadores_detectados == ["feminazi", "mangina"]
        assert result.es_falso_positivo_probable is False
        assert result.score_ajuste == 0.8

    def test_from_llm_response_handles_string_fpp(self):
        """Falso-positivo flag accepts 'true'/'false' strings."""
        response = (
            '{"tiene_violencia": true, "categoria": "VDG_VIOLENCIA_SIMBOLICA", '
            '"dimension": "1.1", "severidad": "media", '
            '"es_falso_positivo_probable": "true"}'
        )
        result = ClassificationResult.from_llm_response(response)
        assert result.es_falso_positivo_probable is True

    def test_from_llm_response_handles_marcadores_as_string(self):
        """marcadores_detectados accepts comma-separated string."""
        response = (
            '{"tiene_violencia": true, "categoria": "VDG_VIOLENCIA_SIMBOLICA", '
            '"dimension": "1.1", "severidad": "media", '
            '"marcadores_detectados": "zorra, puta, feminazi"}'
        )
        result = ClassificationResult.from_llm_response(response)
        assert result.marcadores_detectados == ["zorra", "puta", "feminazi"]

    def test_from_llm_response_invalid(self):
        """Test parsing from invalid response.

        With the new ``error_parsing`` flag the result distinguishes
        "LLM returned no JSON" from "LLM genuinely said no violence".
        ``categoria`` falls back to ``"ninguna"`` (back-compat) but
        ``error_parsing`` is populated for the caller to flag the row.
        """
        result = ClassificationResult.from_llm_response("invalid json")
        assert result.tiene_violencia is False
        assert result.categoria == "ninguna"
        assert result.error_parsing is not None
        assert "JSONDecodeError" in result.error_parsing

    def test_from_llm_response_multi_label(self):
        """New schema: ``clasificaciones`` array of labels."""
        import json

        payload = {
            "tiene_violencia": True,
            "severidad_global": "alta",
            "clasificaciones": [
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "baja",
                    "justificacion": "estereotipo",
                    "evidencia": "a la cocina",
                    "marcadores_detectados": ["cocina", "mujeres"],
                },
                {
                    "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                    "dimension": "3.1",
                    "severidad": "alta",
                    "justificacion": "amenaza",
                    "evidencia": "te voy a matar",
                    "marcadores_detectados": ["matar"],
                },
            ],
        }
        r = ClassificationResult.from_llm_response(json.dumps(payload))
        assert r.tiene_violencia is True
        assert r.severidad_global == Severity.ALTA
        assert len(r.clasificaciones) == 2
        # The primary label is the highest-severity one (Phase 3.1:
        # ``validate_clasificaciones`` sorts by severity desc). For
        # this fixture the ALTA ``3.1`` wins over BAJA ``1.1``.
        assert r.categoria == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert r.dimension == "3.1"
        assert r.severidad == Severity.ALTA
        assert r.primary is not None
        assert r.primary.categoria == "VDG_HOSTILIDAD_FEMINICIDIO"

    def test_from_llm_response_legacy_single_label(self):
        """Legacy single-label schema is wrapped into a 1-element list."""
        legacy = (
            '{"tiene_violencia": true, "categoria": "VDG_COSIFICACION_SLUTSHAMING",'
            ' "dimension": "2.2", "severidad": "media",'
            ' "justificacion": "insulto sexual", "evidencia": "zorra"}'
        )
        r = ClassificationResult.from_llm_response(legacy)
        assert r.tiene_violencia is True
        assert r.categoria == "VDG_COSIFICACION_SLUTSHAMING"
        assert r.dimension == "2.2"
        assert r.severidad == Severity.MEDIA
        assert len(r.clasificaciones) == 1

    def test_from_llm_response_empty_clasificaciones(self):
        """Empty array + ``tiene_violencia: false`` ⇒ no labels."""
        import json

        r = ClassificationResult.from_llm_response(
            json.dumps({"tiene_violencia": False, "clasificaciones": []})
        )
        assert r.tiene_violencia is False
        assert r.clasificaciones == []
        assert r.categoria == "ninguna"

    def test_to_dict_exposes_labels(self):
        """``to_dict`` includes the full multi-label payload."""
        import json

        r = ClassificationResult.from_llm_response(
            json.dumps(
                {
                    "clasificaciones": [
                        {
                            "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                            "dimension": "1.1",
                            "severidad": "baja",
                            "justificacion": "j",
                        }
                    ]
                }
            )
        )
        d = r.to_dict()
        assert d["tiene_violencia"] is True
        assert d["categoria"] == "VDG_VIOLENCIA_SIMBOLICA"
        cls = d["clasificaciones"]
        assert isinstance(cls, list)
        assert len(cls) == 1


class TestRAGClassifier:
    """Tests for RAGClassifier."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        classifier = RAGClassifier()
        assert classifier.llm_client is None
        assert classifier.vector_store is None
        assert classifier.context_chunks == 5
        assert classifier.temperature == 0
        assert classifier.few_shot_examples == []

    def test_init_custom(self):
        """Test initialization with custom params."""
        mock_llm = MagicMock()
        mock_vector = MagicMock()
        classifier = RAGClassifier(
            llm_client=mock_llm,
            vector_store=mock_vector,
            context_chunks=10,
            temperature=0.5,
        )
        assert classifier.llm_client == mock_llm
        assert classifier.vector_store == mock_vector
        assert classifier.context_chunks == 10

    def test_init_with_feedback_store(self):
        """Classifier accepts and stores a feedback_store."""
        mock_fb = MagicMock()
        classifier = RAGClassifier(
            llm_client=MagicMock(),
            vector_store=MagicMock(),
            feedback_store=mock_fb,
            feedback_n_results=5,
        )
        assert classifier.feedback_store is mock_fb
        assert classifier.feedback_n_results == 5

    def test_classify_calls_feedback_store(self):
        """When a feedback_store is provided, retrieval is invoked at classify time."""
        import asyncio

        mock_fb = MagicMock()
        mock_fb.search_relevant_corrections.return_value = []
        classifier = RAGClassifier(
            llm_client=None,  # triggers rule-based fallback (no Ollama needed)
            vector_store=None,
            feedback_store=mock_fb,
        )
        asyncio.run(classifier.classify("sample text"))
        mock_fb.search_relevant_corrections.assert_called_once()

    def test_classify_without_feedback_store_skips_lookup(self):
        """Without a feedback_store, no search call is made."""
        import asyncio

        classifier = RAGClassifier(
            llm_client=None,
            vector_store=None,
            feedback_store=None,
        )
        # Should not raise; path is silently skipped.
        result = asyncio.run(classifier.classify("sample"))
        # Either rule-based or no-op result is acceptable — we just
        # care that the no-feedback path doesn't blow up.
        assert result is not None

    def test_build_prompt_with_feedback_chunks(self):
        """Human-validated blocks appear in the prompt body."""
        classifier = RAGClassifier(context_chunks=2)
        chunks = [{"text": "ctx", "source": "s", "chunk_index": 0, "distance": 0.1}]
        feedback_chunks = [
            {
                "text": 'TEXTO: "x" RESULTADO: {"y":1}',
                "metadata": {
                    "corrected_categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                    "corrected_dimension": "3.1",
                },
                "distance": 0.05,
            }
        ]
        prompt = classifier._build_prompt("some text", chunks, feedback_chunks)
        assert "[VALIDADO POR HUMANO · VDG_HOSTILIDAD_FEMINICIDIO/3.1]" in prompt
        assert 'TEXTO: "x" RESULTADO: {"y":1}' in prompt

    def test_build_prompt_without_feedback_falls_back(self):
        """When no feedback chunks are given, prompt still renders."""
        classifier = RAGClassifier(context_chunks=2)
        chunks: list[dict[str, object]] = []
        prompt = classifier._build_prompt("text", chunks, None)
        assert "(Sin ejemplos few-shot)" in prompt

    def test_build_prompt_includes_canonical_table(self):
        """The prompt must include the 19-row canonical table."""
        classifier = RAGClassifier(context_chunks=5)
        chunks = [
            {
                "text": "Fragmento de prueba",
                "source": "test.md",
                "chunk_index": 0,
                "distance": 0.1,
            }
        ]
        prompt = classifier._build_prompt("Test text", chunks)

        # Canonical codes
        assert "VDG_VIOLENCIA_SIMBOLICA" in prompt
        assert "VDG_COSIFICACION_SLUTSHAMING" in prompt
        assert "VDG_HOSTILIDAD_FEMINICIDIO" in prompt
        assert "VDG_MANOSFERA_ANTIFEMINISMO" in prompt
        assert "VDG_SALVAGUARDA_FALSO_POSITIVO" in prompt
        assert "VDG_DESACREDITACION_ACTIVISTAS" in prompt

        # All 19 dimensions
        for cat, dims in [
            ("1", ["1.1", "1.2", "1.3"]),
            ("2", ["2.1", "2.2", "2.3"]),
            ("3", ["3.1", "3.2", "3.3"]),
            ("4", ["4.1", "4.2", "4.3", "4.4"]),
            ("5", ["5.1", "5.2", "5.3"]),
            ("6", ["6.1", "6.2", "6.3"]),
        ]:
            for d in dims:
                assert d in prompt, f"Missing sub-dim {d} in prompt"

        # New fields requested
        assert "regla_disparada" in prompt
        assert "marcadores_detectados" in prompt
        assert "es_falso_positivo_probable" in prompt
        assert "score_ajuste" in prompt

    def test_build_prompt_uses_chroma_chunks(self):
        """Test that the prompt lists ChromaDB chunks."""
        classifier = RAGClassifier(context_chunks=5)
        chunks = [
            {
                "text": "Fragmento del marco 1",
                "source": "CATEGORIAS.md",
                "chunk_index": 0,
                "distance": 0.12,
            },
            {
                "text": "Fragmento del marco 2",
                "source": "CATEGORIAS.md",
                "chunk_index": 5,
                "distance": 0.30,
            },
        ]
        prompt = classifier._build_prompt("Test text", chunks)
        assert "Test text" in prompt
        assert "Fragmento del marco 1" in prompt
        assert "Fragmento del marco 2" in prompt
        assert "FRAGMENTOS RECUPERADOS DE ChromaDB" in prompt
        assert "k=5" in prompt

    def test_build_prompt_without_context(self):
        """Test prompt with no context uses the placeholder."""
        classifier = RAGClassifier()
        prompt = classifier._build_prompt("Texto", [])
        assert "No hay fragmentos disponibles en ChromaDB" in prompt

    def test_retrieve_context_uses_vector_store(self):
        """Test that retrieval pulls metadata correctly."""
        mock_vs = MagicMock()
        mock_vs.search.return_value = [
            {
                "text": "contenido 1",
                "metadata": {"source": "CATEGORIAS.md", "chunk_index": 7},
                "distance": 0.1,
                "id": "doc_7",
            }
        ]
        classifier = RAGClassifier(vector_store=mock_vs, context_chunks=3)
        chunks = classifier._retrieve_context("hola")
        mock_vs.search.assert_called_once_with("hola", n_results=3)
        assert chunks[0]["text"] == "contenido 1"
        assert chunks[0]["source"] == "CATEGORIAS.md"
        assert chunks[0]["chunk_index"] == 7
        assert chunks[0]["distance"] == 0.1

    def test_retrieve_context_no_vector_store(self):
        """Test that empty list is returned when no vector_store."""
        classifier = RAGClassifier()
        assert classifier._retrieve_context("hola") == []

    def test_rule_based_classify_returns_canonical_codes(self):
        """Rule-based classification must return VDG_* / X.Y codes."""
        classifier = RAGClassifier()
        result = classifier._rule_based_classify("Te voy a matar si seguís así", [])
        assert result.tiene_violencia is True
        assert result.categoria in {c.value for c in Categoria}
        assert result.dimension is not None
        assert result.regla_disparada is not None
        assert result.marcadores_detectados != []

    def test_rule_based_classify_no_violence(self):
        """Test rule-based classification without violence."""
        classifier = RAGClassifier()
        result = classifier._rule_based_classify("Qué lindo día hace hoy", [])
        assert result.tiene_violencia is False
        assert result.categoria == "ninguna"
        assert result.severidad == Severity.NINGUNA
        assert result.marcadores_detectados == []

    def test_classify_sync_fallback(self):
        """Test synchronous classify uses fallback when no LLM."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Test")
        assert isinstance(result, ClassificationResult)


class TestPostEmbeddings:
    """Tests for PostEmbeddings."""

    def test_init(self):
        """Test initialization."""
        embeddings = PostEmbeddings()
        assert embeddings.embeddings_provider is None
        assert embeddings.embeddings_cache == {}

    def test_init_with_provider(self):
        """Test initialization with provider."""
        provider = MagicMock()
        embeddings = PostEmbeddings(provider)
        assert embeddings.embeddings_provider == provider

    def test_clear_cache(self):
        """Test cache clearing."""
        embeddings = PostEmbeddings()
        embeddings.embeddings_cache["test"] = [1, 2, 3]
        embeddings.clear_cache()
        assert embeddings.embeddings_cache == {}

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        score = PostEmbeddings._cosine_similarity([1, 0], [1, 0])
        assert score == 1.0
        score = PostEmbeddings._cosine_similarity([1, 0], [0, 1])
        assert score == 0.0

    def test_cosine_similarity_empty(self):
        """Test cosine similarity with empty vectors."""
        score = PostEmbeddings._cosine_similarity([], [1, 2])
        assert score == 0.0
        score = PostEmbeddings._cosine_similarity([1, 2], [])
        assert score == 0.0
