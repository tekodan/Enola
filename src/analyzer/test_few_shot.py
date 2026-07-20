"""Tests for few_shot_loader + wiring into RAGClassifier.

These tests cover:
- The loader normalizes both multi-label and legacy single-label entries.
- RAGClassifier injects the few-shots into the prompt verbatim.
- BatchAnalyzer forwards the few-shots to its internal classifier.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.analyzer import few_shot_loader
from src.analyzer.batch_analyzer import BatchAnalyzer
from src.analyzer.few_shot_loader import (
    DEFAULT_PATH,
    load_few_shot_examples,
    reset_cache,
)
from src.analyzer.rag_classifier import RAGClassifier


@pytest.fixture(autouse=True)
def _clear_loader_cache() -> None:
    """Each test starts with a fresh cache."""
    reset_cache()


class TestFewShotLoader:
    def test_load_returns_normalized_dicts(self) -> None:
        examples = load_few_shot_examples()
        assert len(examples) >= 5
        for ex in examples:
            assert "text" in ex
            assert "result" in ex
            cls = ex["result"].get("clasificaciones", [])
            assert isinstance(cls, list)
            for entry in cls:
                assert entry["categoria"].startswith("VDG_")
                assert entry["severidad"] in {"baja", "media", "alta", "ninguna"}

    def test_multilabel_entry_preserves_per_label_evidence(self) -> None:
        examples = load_few_shot_examples()
        multi = next(ex for ex in examples if len(ex["result"]["clasificaciones"]) >= 2)
        labels = multi["result"]["clasificaciones"]
        assert len({lbl["categoria"] for lbl in labels}) >= 2
        for lbl in labels:
            assert lbl["evidencia"]
            assert lbl["justificacion"]

    def test_legacy_entry_is_wrapped_into_clasificaciones(self) -> None:
        legacy = {
            "text": "test legacy",
            "result": {
                "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                "dimension": "1.3",
                "severidad": "baja",
                "justificacion": "test",
                "evidencia": "test",
                "marcadores_detectados": ["x"],
            },
        }
        normalized = few_shot_loader._normalize_example(legacy)
        assert len(normalized["result"]["clasificaciones"]) == 1
        assert normalized["result"]["clasificaciones"][0]["categoria"] == (
            "VDG_VIOLENCIA_SIMBOLICA"
        )
        assert normalized["result"]["clasificaciones"][0]["dimension"] == "1.3"

    def test_empty_array_raises(self, tmp_path) -> None:
        p = tmp_path / "empty.json"
        p.write_text('{"examples": []}', encoding="utf-8")
        with pytest.raises(ValueError, match="no examples"):
            load_few_shot_examples(p)

    def test_missing_file_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            load_few_shot_examples(tmp_path / "does-not-exist.json")

    def test_default_path_exists(self) -> None:
        assert DEFAULT_PATH.exists()


class TestFewShotInjectionIntoPrompt:
    def test_static_examples_appear_in_prompt(self) -> None:
        examples = list(load_few_shot_examples())
        classifier = RAGClassifier(few_shot_examples=examples)
        prompt = classifier._build_prompt("texto de prueba", context_chunks=[])
        assert "EJEMPLO 1:" in prompt
        assert examples[0]["text"] in prompt
        assert "clasificaciones" in prompt

    def test_empty_few_shots_shows_placeholder(self) -> None:
        classifier = RAGClassifier(few_shot_examples=[])
        prompt = classifier._build_prompt("texto", context_chunks=[])
        assert "(Sin ejemplos few-shot)" in prompt


class TestBatchAnalyzerWiring:
    def test_batch_analyzer_loads_default_few_shots(self) -> None:
        """When no classifier is passed, BatchAnalyzer builds one with the
        default few-shots loaded from disk.
        """
        vs = MagicMock()
        fb = MagicMock()
        llm = MagicMock()
        analyzer = BatchAnalyzer(
            database=MagicMock(),
            vector_store=vs,
            feedback_store=fb,
            llm_client=llm,
            analyze_posts=False,
            analyze_comments=False,
        )
        assert len(analyzer.classifier.few_shot_examples) >= 5

    def test_batch_analyzer_honors_explicit_few_shots(self) -> None:
        vs = MagicMock()
        fb = MagicMock()
        llm = MagicMock()
        custom = [
            {
                "text": "x",
                "result": {
                    "clasificaciones": [
                        {
                            "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                            "dimension": "1.1",
                            "severidad": "alta",
                            "justificacion": "x",
                            "evidencia": "x",
                            "marcadores_detectados": ["x"],
                        }
                    ]
                },
            }
        ]
        analyzer = BatchAnalyzer(
            database=MagicMock(),
            vector_store=vs,
            feedback_store=fb,
            llm_client=llm,
            analyze_posts=False,
            analyze_comments=False,
            few_shot_examples=custom,
        )
        assert analyzer.classifier.few_shot_examples == custom
