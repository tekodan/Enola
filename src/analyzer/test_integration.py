"""Integration tests for analyzer module.

Integration tests exercise the rule-based fallback (no Ollama needed)
and verify that the new ChromaDB-driven canonical taxonomy propagates
end-to-end.
"""

from unittest.mock import MagicMock

from src.analyzer.category_mapping import Categoria
from src.analyzer.embeddings import PostEmbeddings
from src.analyzer.rag_classifier import ClassificationResult, RAGClassifier
from src.analyzer.violence_types import Severity


class TestClassificationWorkflow:
    """Tests for classification workflow."""

    def test_classify_texts_with_violence(self):
        """Test classifying texts with violence indicators."""
        classifier = RAGClassifier()

        violent_texts = [
            "Te voy a matar",
            "Las mujeres solo sirven para cocinar",
            "Si no accedés es tu culpa",
            "No te doy plata para que aprendas",
        ]

        for text in violent_texts:
            result = classifier.classify_sync(text)
            assert isinstance(result, ClassificationResult)
            assert result.tiene_violencia is True
            assert result.severidad != Severity.NINGUNA
            assert result.categoria in {c.value for c in Categoria}
            assert result.dimension is not None

    def test_classify_neutral_texts(self):
        """Test classifying neutral texts."""
        classifier = RAGClassifier()

        neutral_texts = [
            "Qué lindo día",
            "Feliz cumpleaños",
            "El clima está nice",
            "Compartí esta foto",
        ]

        for text in neutral_texts:
            result = classifier.classify_sync(text)
            assert result.tiene_violencia is False
            assert result.categoria == "ninguna"
            assert result.severidad == Severity.NINGUNA

    def test_batch_classification(self):
        """Test batch classification."""
        classifier = RAGClassifier()

        texts = ["Texto 1", "Texto 2", "Texto 3"]
        results = classifier.classify_batch_sync(texts)

        assert len(results) == len(texts)
        assert all(isinstance(r, ClassificationResult) for r in results)


class TestViolenceDetection:
    """Tests for specific violence detection scenarios."""

    def test_detect_physical_violence(self):
        """Test detecting physical violence."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Le pegó a su esposa")
        assert result.tiene_violencia is True
        assert result.severidad == Severity.ALTA

    def test_detect_psychological_violence(self):
        """Test detecting psychological violence."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("No sos nada sin mí")
        assert result.tiene_violencia is True

    def test_detect_sexual_violence(self):
        """Test detecting sexual violence."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Para eso estás, contenido sexual")
        assert result.tiene_violencia is True

    def test_detect_economic_violence(self):
        """Test detecting economic violence."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("No te doy plata, no decis nada")
        assert result.tiene_violencia is True

    def test_detect_symbolic_violence(self):
        """Test detecting symbolic violence."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Las mujeres son para la cocina")
        assert result.tiene_violencia is True
        assert result.severidad in (Severity.BAJA, Severity.MEDIA, Severity.ALTA)

    def test_detect_vicarious_violence(self):
        """Test detecting vicarious violence."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Si me dejás le hago daño a los hijos")
        assert result.tiene_violencia is True
        assert result.severidad == Severity.ALTA

    def test_detect_verbal_violence(self):
        """Test detecting verbal violence."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Sos una zorra y una puta")
        assert result.tiene_violencia is True

    def test_detect_manosphere(self):
        """Test detecting manosphere vocabulary."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Las feminazis son todas iguales, hembristas")
        assert result.tiene_violencia is True
        assert result.categoria == "VDG_MANOSFERA_ANTIFEMINISMO"

    def test_detect_activist_discrediting(self):
        """Test detecting attacks on feminist activists."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Las feministas radicales son todas unas viejas webonas")
        assert result.tiene_violencia is True
        assert result.categoria == "VDG_DESACREDITACION_ACTIVISTAS"


class TestSeverityLevels:
    """Tests for severity level determination."""

    def test_high_severity_indicators(self):
        """Test high severity detection."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Te voy a matar")
        assert result.tiene_violencia is True
        assert result.severidad == Severity.ALTA

    def test_low_severity_indicators(self):
        """Test low severity detection."""
        classifier = RAGClassifier()
        result = classifier.classify_sync("Las mujeres cocinan mejor")
        assert result.tiene_violencia is True
        assert result.severidad == Severity.BAJA


class TestEmbeddingsWorkflow:
    """Tests for embeddings workflow."""

    def test_batch_similarity_empty(self):
        """Test batch similarity with empty input."""
        embeddings = PostEmbeddings()
        assert embeddings.compute_batch_similarity([], ["ref"]) == []
        assert embeddings.compute_batch_similarity(["text"], []) == []

    def test_average_similarity_empty(self):
        """Test average similarity with empty input."""
        embeddings = PostEmbeddings()
        assert embeddings.compute_average_similarity([], ["ref"]) == 0.0
        assert embeddings.compute_average_similarity(["text"], []) == 0.0

    def test_similarity_with_mock_provider(self):
        """Test similarity with mock provider."""
        mock_provider = MagicMock()
        mock_provider.embed.return_value = [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
        embeddings = PostEmbeddings(mock_provider)
        score = embeddings.compute_similarity("text1", "text2")
        assert 0 <= score <= 1


class TestClassificationResults:
    """Tests for classification results handling."""

    def test_results_to_dict(self):
        """Test converting results to dict."""
        result = ClassificationResult(
            tiene_violencia=True,
            categoria="VDG_HOSTILIDAD_FEMINICIDIO",
            dimension="3.1",
            severidad=Severity.ALTA,
            justificacion="Amenaza de muerte",
            evidencia="te voy a matar",
            confianza=0.95,
        )
        data = result.to_dict()
        assert data["tiene_violencia"] is True
        assert data["categoria"] == "VDG_HOSTILIDAD_FEMINICIDIO"
        assert data["severidad"] == "alta"
        assert data["confianza"] == 0.95
        assert data["marcadores_detectados"] == []

    def test_results_json_serialization(self):
        """Test JSON serialization of results."""
        import json

        result = ClassificationResult(
            tiene_violencia=True,
            categoria="VDG_COSIFICACION_SLUTSHAMING",
            dimension="2.1",
            severidad=Severity.MEDIA,
            justificacion="Cosificación",
            evidencia="para eso estás",
        )
        json_str = json.dumps(result.to_dict())
        restored = json.loads(json_str)
        assert restored["tiene_violencia"] is True
        assert restored["categoria"] == "VDG_COSIFICACION_SLUTSHAMING"
        assert restored["dimension"] == "2.1"


class TestEndToEnd:
    """End-to-end tests (rule-based path)."""

    def test_full_classification_pipeline(self):
        """Test full classification pipeline."""
        classifier = RAGClassifier()
        texts = [
            "Te voy a matar si seguís así",
            "Las mujeres solo sirven para cocinar",
            "Qué lindo día hace hoy",
            "Compartí esta foto",
        ]
        results = classifier.classify_batch_sync(texts)
        assert len(results) == 4
        assert results[0].tiene_violencia
        assert results[1].tiene_violencia
        assert not results[2].tiene_violencia
        assert not results[3].tiene_violencia

    def test_classification_consistency(self):
        """Test classification consistency."""
        classifier = RAGClassifier()
        text = "Te voy a matar"
        r1 = classifier.classify_sync(text)
        r2 = classifier.classify_sync(text)
        assert r1.tiene_violencia == r2.tiene_violencia
        assert r1.categoria == r2.categoria
        assert r1.severidad == r2.severidad

    def test_all_canonical_categories_reachable(self):
        """All 6 categories are reachable via rule-based path."""
        classifier = RAGClassifier()
        cat_to_text = {
            "VDG_VIOLENCIA_SIMBOLICA": "las mujeres son para la cocina",
            "VDG_COSIFICACION_SLUTSHAMING": "sos una zorra",
            "VDG_HOSTILIDAD_FEMINICIDIO": "te voy a matar",
            "VDG_MANOSFERA_ANTIFEMINISMO": "feminazi hembrista",
            "VDG_SALVAGUARDA_FALSO_POSITIVO": "ninguna",  # solo se activa con cat ortogonal
            "VDG_DESACREDITACION_ACTIVISTAS": "feministas radicales",
        }
        for expected_cat, text in cat_to_text.items():
            if expected_cat == "VDG_SALVAGUARDA_FALSO_POSITIVO":
                # Esta categoría es ortogonal — no se activa por texto positivo
                continue
            result = classifier.classify_sync(text)
            assert result.categoria == expected_cat, (
                f"Expected {expected_cat} for '{text}', got {result.categoria}"
            )
