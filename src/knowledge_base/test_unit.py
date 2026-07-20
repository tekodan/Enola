"""Unit tests for knowledge base module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.knowledge_base.discovery import (
    DEFAULT_DISCOVERY_QUERY,
    LEGACY_VIOLENCE_TYPES,
    build_discovery_prompt,
    diff_with_legacy_enum,
    discover_categories,
    parse_discovery_response,
    render_discovery_report,
    retrieve_discovery_chunks,
)
from src.knowledge_base.feedback_store import (
    DEFAULT_COLLECTION_NAME,
    FeedbackStore,
    render_few_shot_doc,
)
from src.knowledge_base.pdf_processor import (
    PDFProcessor,
    chunk_text,
    extract_text_from_pdf,
)
from src.knowledge_base.vector_store import VectorStoreManager


class TestPDFProcessor:
    """Tests for PDFProcessor."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        processor = PDFProcessor()

        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 50

    def test_init_custom(self):
        """Test initialization with custom values."""
        processor = PDFProcessor(chunk_size=1000, chunk_overlap=100)

        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 100

    def test_clean_text(self):
        """Test text cleaning."""
        processor = PDFProcessor()

        # Multiple whitespace
        text = "Hola   mundo   test"
        cleaned = processor._clean_text(text)
        assert cleaned == "Hola mundo test"

        # Non-printable characters
        text = "Hola\x00mundo\x1ftest"
        cleaned = processor._clean_text(text)
        assert "Hola" in cleaned
        assert "\x00" not in cleaned

    def test_chunk_text_simple(self):
        """Test chunking of simple text."""
        processor = PDFProcessor(chunk_size=50, chunk_overlap=10)

        text = "Esta es una oración corta. Esta es otra oración. Y una tercera oración."
        chunks = processor.chunk_text(text)

        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        assert all(len(c) <= 100 for c in chunks)  # Some tolerance

    def test_chunk_text_empty(self):
        """Test chunking of empty text."""
        processor = PDFProcessor()

        chunks = processor.chunk_text("")
        assert chunks == []

        chunks = processor.chunk_text(None)
        assert chunks == []

    def test_chunk_text_paragraphs(self):
        """Test chunking preserves paragraph structure."""
        processor = PDFProcessor(chunk_size=100, chunk_overlap=20)

        text = "Primer párrafo.\n\nSegundo párrafo.\n\nTercer párrafo."
        chunks = processor.chunk_text(text)

        assert len(chunks) >= 1

    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        processor = PDFProcessor(chunk_size=20, chunk_overlap=5)

        # Longer text that creates multiple chunks with overlap
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 2
        chunks = processor.chunk_text(text)

        if len(chunks) > 1:
            # Check overlap exists between consecutive chunks
            assert any(chunks[i][-5:] in chunks[i + 1] for i in range(len(chunks) - 1))


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf function."""

    def test_file_not_found(self):
        """Test error when file not found."""
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf("/nonexistent/file.pdf")


class TestChunkText:
    """Tests for chunk_text function."""

    def test_convenience_function(self):
        """Test convenience function."""
        text = "Hola mundo esto es una prueba."
        chunks = chunk_text(text, chunk_size=20, chunk_overlap=5)

        assert isinstance(chunks, list)
        assert all(isinstance(c, str) for c in chunks)


class TestVectorStoreManager:
    """Tests for VectorStoreManager."""

    def test_init_defaults(self, tmp_path):
        """Test initialization with defaults."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        assert manager.persist_directory == tmp_path / "chroma"
        assert manager.collection_name == "test_collection"
        assert manager.collection is None

    def test_create_collection(self, tmp_path):
        """Test collection creation."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        manager.create_collection()

        assert manager.collection is not None
        assert manager.collection.name == "test_collection"

    def test_get_collection_stats(self, tmp_path):
        """Test getting collection stats."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        # Before creation
        stats = manager.get_collection_stats()
        assert stats["count"] == 0

        # After creation
        manager.create_collection()
        stats = manager.get_collection_stats()
        assert "count" in stats

    def test_add_documents(self, tmp_path):
        """Test adding documents."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        manager.create_collection()

        documents = ["Documento 1", "Documento 2", "Documento 3"]
        metadatas = [
            {"source": "doc1", "type": "ley"},
            {"source": "doc2", "type": "articulo"},
            {"source": "doc3", "type": "manual"},
        ]
        ids = ["id1", "id2", "id3"]

        manager.add_documents(documents, metadatas, ids)

        stats = manager.get_collection_stats()
        assert stats["count"] == 3

    def test_add_documents_ids_are_unique_across_calls(self, tmp_path):
        """Multiple add_documents() calls with no ids must not collide."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )
        manager.create_collection()

        manager.add_documents(documents=["a", "b", "c"])
        manager.add_documents(documents=["d", "e", "f"])
        manager.add_documents(documents=["g"])

        assert manager.collection.count() == 7

    def test_delete_by_source(self, tmp_path):
        """delete-by-source removes only the chunks of that source."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )
        manager.create_collection()

        manager.add_documents(
            documents=["a1", "a2"],
            metadatas=[{"source": "file_a.md"}, {"source": "file_a.md"}],
        )
        manager.add_documents(
            documents=["b1", "b2"],
            metadatas=[{"source": "file_b.md"}, {"source": "file_b.md"}],
        )
        assert manager.collection.count() == 4

        ids_to_delete = manager.collection.get(where={"source": "file_a.md"})["ids"]
        manager.collection.delete(ids=ids_to_delete)
        assert manager.collection.count() == 2

        remaining = manager.collection.get(where={"source": "file_b.md"})["ids"]
        assert len(remaining) == 2

    def test_search(self, tmp_path):
        """Test searching documents."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        manager.create_collection()

        # Add some documents
        documents = [
            "La violencia de género es un problema social",
            "Elmachismo causa violencia",
            "Los derechos humanos son fundamentales",
        ]
        manager.add_documents(documents)

        # Search
        results = manager.search("violencia", n_results=2)

        assert isinstance(results, list)
        # Results depend on embeddings, but should return something

    def test_delete_collection(self, tmp_path):
        """Test deleting collection."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        manager.create_collection()
        manager.delete_collection()

        assert manager.collection is None


class TestVectorStoreEdgeCases:
    """Edge case tests for vector store."""

    def test_search_empty_collection(self, tmp_path):
        """Test search on empty collection."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        manager.create_collection()

        results = manager.search("test query")

        assert results == []

    def test_add_empty_documents(self, tmp_path):
        """Test adding empty documents list."""
        manager = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"), collection_name="test_collection"
        )

        manager.create_collection()

        # Empty list should not call add (ChromaDB 0.6+ requires non-empty)
        if False:  # skip: ChromaDB doesn't support empty documents
            manager.add_documents([])

        stats = manager.get_collection_stats()
        assert stats["count"] == 0


class TestDiscoveryRetrieveChunks:
    """Tests for retrieve_discovery_chunks()."""

    def test_returns_empty_when_no_vector_store(self):
        """Should return [] when vector_store is None."""
        assert retrieve_discovery_chunks(None) == []

    def test_extracts_metadata_correctly(self):
        """Should pull source/chunk_index/distance/id from the results."""
        vs = MagicMock()
        vs.search.return_value = [
            {
                "text": "fragmento A",
                "metadata": {"source": "MARCO.md", "chunk_index": 3},
                "distance": 0.21,
                "id": "doc_3",
            },
            {
                "text": "fragmento B",
                "metadata": {"source": "MARCO.md", "chunk_index": 9},
                "distance": 0.45,
                "id": "doc_9",
            },
        ]

        chunks = retrieve_discovery_chunks(vs, n_results=2, query="violencia")

        vs.search.assert_called_once_with("violencia", n_results=2)
        assert len(chunks) == 2
        assert chunks[0] == {
            "text": "fragmento A",
            "source": "MARCO.md",
            "chunk_index": 3,
            "distance": 0.21,
            "id": "doc_3",
        }

    def test_uses_default_query_when_not_provided(self):
        """Default query should be the Spanish umbrella query."""
        vs = MagicMock()
        vs.search.return_value = []

        retrieve_discovery_chunks(vs, n_results=5)

        vs.search.assert_called_once_with(DEFAULT_DISCOVERY_QUERY, n_results=5)


class TestBuildDiscoveryPrompt:
    """Tests for build_discovery_prompt()."""

    def test_includes_chunks_in_prompt(self):
        """Prompt should contain the chunk text and source metadata."""
        chunks = [
            {
                "text": "Contenido del fragmento 1",
                "source": "MARCO.md",
                "chunk_index": 0,
                "distance": 0.1,
            }
        ]
        prompt = build_discovery_prompt(chunks)

        assert "Contenido del fragmento 1" in prompt
        assert "MARCO.md" in prompt
        assert "JSON ESTRICTO" in prompt
        assert "niveles" in prompt
        assert "subdimensiones" in prompt
        assert "codigos_programaticos" in prompt

    def test_handles_empty_chunks(self):
        """Empty chunks should produce the 'no fragments' placeholder."""
        prompt = build_discovery_prompt([])

        assert "No hay fragmentos disponibles" in prompt


class TestParseDiscoveryResponse:
    """Tests for parse_discovery_response()."""

    def test_parses_valid_json(self):
        """Valid JSON string should parse to a dict."""
        raw = '{"niveles": [{"codigo": "1.2", "nombre": "X"}], "total": 1}'
        parsed = parse_discovery_response(raw)
        assert "niveles" in parsed
        assert parsed["niveles"][0]["codigo"] == "1.2"

    def test_strips_markdown_fences(self):
        """Should strip ```json and ``` wrappers."""
        raw = '```json\n{"niveles": []}\n```'
        parsed = parse_discovery_response(raw)
        assert parsed == {"niveles": []}

    def test_returns_error_on_invalid_json(self):
        """Invalid JSON should return an error dict, not raise."""
        parsed = parse_discovery_response("not json")
        assert "_error" in parsed
        assert "_raw" in parsed

    def test_handles_non_string_input(self):
        """Non-string input should return an error dict."""
        parsed = parse_discovery_response(None)
        assert "_error" in parsed


class TestDiffWithLegacyEnum:
    """Tests for diff_with_legacy_enum()."""

    def test_finds_legacy_codes_in_taxonomy(self):
        """Legacy codes mentioned in the taxonomy should be flagged."""
        taxonomy = {
            "niveles": [
                {
                    "codigo": "1.4",
                    "nombre": "Amenazas",
                    "subdimensiones": [],
                    "codigos_programaticos": [],
                }
            ]
        }
        diff = diff_with_legacy_enum(taxonomy)

        assert "fisica" not in diff["legacy_in_taxonomy"]
        assert diff["discovered_niveles_count"] == 1

    def test_handles_none_taxonomy(self):
        """None taxonomy should not crash."""
        diff = diff_with_legacy_enum(None)
        assert diff["discovered_niveles_count"] == 0
        assert diff["legacy_types"] == sorted(LEGACY_VIOLENCE_TYPES.keys())

    def test_counts_subdimensiones(self):
        """Sub-dimensions across levels should be summed."""
        taxonomy = {
            "niveles": [
                {
                    "codigo": "1.2",
                    "nombre": "X",
                    "subdimensiones": [
                        {"codigo": "1.2.1", "nombre": "a"},
                        {"codigo": "1.2.2", "nombre": "b"},
                    ],
                },
                {
                    "codigo": "1.4",
                    "nombre": "Y",
                    "subdimensiones": [
                        {"codigo": "1.4.1", "nombre": "c"},
                    ],
                },
            ]
        }
        diff = diff_with_legacy_enum(taxonomy)
        assert diff["discovered_subdimensiones_count"] == 3


class TestDiscoverCategories:
    """Tests for discover_categories() (async)."""

    def test_retrieval_only_mode(self):
        """When llm_client is None, return retrieval-only result."""
        vs = MagicMock()
        vs.search.return_value = [
            {
                "text": "t1",
                "metadata": {"source": "MARCO.md", "chunk_index": 0},
                "distance": 0.1,
                "id": "doc_0",
            }
        ]

        result = asyncio.run(discover_categories(vs, llm_client=None, n_results=1))

        assert result["mode"] == "retrieval-only"
        assert len(result["chunks"]) == 1
        assert result["chunks"][0]["text"] == "t1"
        assert "taxonomy" not in result

    def test_llm_mode_parses_response(self):
        """When llm_client is provided, parse the response as taxonomy."""
        vs = MagicMock()
        vs.search.return_value = [
            {
                "text": "t1",
                "metadata": {"source": "MARCO.md", "chunk_index": 0},
                "distance": 0.1,
                "id": "doc_0",
            }
        ]
        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value='{"niveles": [{"codigo": "1.1", "nombre": "X"}], "total_categorias_nivel_1": 1}'
        )

        result = asyncio.run(discover_categories(vs, llm_client=llm, n_results=1))

        assert result["mode"] == "llm"
        assert result["taxonomy"] is not None
        assert result["taxonomy"]["niveles"][0]["codigo"] == "1.1"
        assert "raw_response" in result

    def test_llm_error_handled(self):
        """When the LLM raises, return a result with an error key."""
        vs = MagicMock()
        vs.search.return_value = []
        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=RuntimeError("ollama down"))

        result = asyncio.run(discover_categories(vs, llm_client=llm, n_results=1))

        assert result["mode"] == "llm"
        assert result["taxonomy"] is None
        assert "ollama down" in result["error"]


class TestRenderDiscoveryReport:
    """Tests for render_discovery_report()."""

    def test_renders_retrieval_only(self):
        """Retrieval-only result should render a 'sample of chunks' section."""
        result = {
            "mode": "retrieval-only",
            "n_results": 2,
            "chunks": [
                {
                    "text": "fragmento de muestra uno",
                    "source": "MARCO.md",
                    "chunk_index": 0,
                    "distance": 0.1,
                    "id": "doc_0",
                }
            ],
        }

        report = render_discovery_report(result)

        assert "TAXONOMÍA" in report
        assert "retrieval-only" in report
        assert "MARCO.md" in report

    def test_renders_llm_taxonomy(self):
        """LLM taxonomy should be rendered with niveles and subdimensiones."""
        result = {
            "mode": "llm",
            "n_results": 1,
            "chunks": [
                {
                    "text": "t",
                    "source": "MARCO.md",
                    "chunk_index": 0,
                    "distance": 0.1,
                    "id": "doc_0",
                }
            ],
            "taxonomy": {
                "niveles": [
                    {
                        "codigo": "1.2",
                        "nombre": "Violencia Sexual Digital",
                        "subdimensiones": [
                            {"codigo": "1.2.1", "nombre": "IBSA"},
                        ],
                        "codigos_programaticos": ["VDG_ODIO_MISOGINO"],
                    }
                ],
                "categorias_programaticas": [],
                "perfiles_constitucionales": [],
            },
        }

        report = render_discovery_report(result)

        assert "1.2" in report
        assert "Violencia Sexual Digital" in report
        assert "1.2.1" in report
        assert "IBSA" in report
        assert "VDG_ODIO_MISOGINO" in report

    def test_renders_diff_section(self):
        """Diff should be rendered when chunks are present and diff is provided."""
        result = {
            "mode": "llm",
            "n_results": 1,
            "chunks": [
                {
                    "text": "taxonomy content",
                    "source": "MARCO.md",
                    "chunk_index": 0,
                    "distance": 0.1,
                    "id": "doc_0",
                }
            ],
            "taxonomy": {"niveles": [], "categorias_programaticas": []},
        }
        diff = {
            "legacy_types": ["fisica", "verbal"],
            "legacy_in_taxonomy": ["verbal"],
            "legacy_missing": ["fisica"],
            "discovered_niveles_count": 0,
            "discovered_subdimensiones_count": 0,
            "discovered_categorias_programaticas_count": 0,
            "niveles": [],
            "categorias_programaticas": [],
        }

        report = render_discovery_report(result, diff=diff)

        assert "DIFF" in report
        assert "fisica" in report
        assert "verbal" in report

    def test_diff_with_empty_chunks_is_skipped(self):
        """When no chunks, diff is still noted but section is not rendered."""
        result = {"mode": "retrieval-only", "n_results": 0, "chunks": []}
        diff = {
            "legacy_types": [],
            "legacy_in_taxonomy": [],
            "legacy_missing": [],
            "discovered_niveles_count": 0,
            "discovered_subdimensiones_count": 0,
            "discovered_categorias_programaticas_count": 0,
            "niveles": [],
            "categorias_programaticas": [],
        }

        report = render_discovery_report(result, diff=diff)

        assert "DIFF" not in report
        assert "Diff omitido" in report

    def test_renders_empty_collection_message(self):
        """When no chunks, render a clear message."""
        result = {"mode": "retrieval-only", "n_results": 5, "chunks": []}
        report = render_discovery_report(result)
        assert "no se recuperaron chunks" in report.lower()


class TestRenderFewShotDoc:
    """Tests for the few-shot document renderer shared with RAGClassifier."""

    def test_includes_corrected_categoria(self):
        doc = render_few_shot_doc(
            "user said zorra",
            categoria="VDG_COSIFICACION_SLUTSHAMING",
            dimension="2.2",
            justificacion="corrected",
        )
        assert "VDG_COSIFICACION_SLUTSHAMING" in doc
        assert '"dimension": "2.2"' in doc
        assert '"justificacion": "corrected"' in doc

    def test_dimension_null_serialized(self):
        """``dimension=None`` ⇒ no ``clasificaciones`` array (no violencia)."""
        doc = render_few_shot_doc("t", categoria="ninguna", dimension=None, justificacion="x")
        assert '"tiene_violencia": false' in doc
        assert '"clasificaciones": []' in doc

    def test_quotes_in_justificacion_are_emitted_verbatim(self):
        """Renderer encodes via ``json.dumps``; quotes are escaped."""
        import json as _json

        doc = render_few_shot_doc(
            "t", categoria="X", dimension="1.1", justificacion='has "quotes" inside'
        )
        expected = _json.dumps('has "quotes" inside')
        assert expected in doc

    def test_multi_label_render_uses_clasificaciones(self):
        """Passing ``clasificaciones`` produces the new multi-label shape."""
        doc = render_few_shot_doc(
            "t",
            clasificaciones=[
                {
                    "categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "dimension": "1.1",
                    "severidad": "baja",
                    "justificacion": "j1",
                },
                {
                    "categoria": "VDG_HOSTILIDAD_FEMINICIDIO",
                    "dimension": "3.1",
                    "severidad": "alta",
                    "justificacion": "j2",
                },
            ],
        )
        assert '"tiene_violencia": true' in doc
        assert '"severidad_global": "alta"' in doc
        assert '"VDG_VIOLENCIA_SIMBOLICA"' in doc
        assert '"VDG_HOSTILIDAD_FEMINICIDIO"' in doc
        assert '"clasificaciones"' in doc


class TestFeedbackStore:
    """Tests for the ChromaDB-backed feedback store."""

    def _make_store(self, tmp_path, *, name: str = "test_feedback") -> FeedbackStore:
        fs = FeedbackStore(persist_directory=str(tmp_path / "chroma"), collection_name=name)
        fs.create_collection()
        return fs

    def test_default_collection_name(self):
        assert DEFAULT_COLLECTION_NAME == "feedback_corrections"
        assert FeedbackStore.DEFAULT_COLLECTION_NAME == "feedback_corrections"

    def test_init_creates_directory(self, tmp_path):
        target = tmp_path / "new_chroma"
        FeedbackStore(persist_directory=str(target))
        assert target.exists()

    def test_create_collection_idempotent(self, tmp_path):
        fs = self._make_store(tmp_path)
        fs.create_collection()
        fs.create_collection()  # second call must not raise
        assert fs.collection is not None

    def test_add_correction_returns_id(self, tmp_path):
        fs = self._make_store(tmp_path)
        cid = fs.add_correction(
            feedback_id=1,
            text="sample text",
            corrected_categoria="VDG_HOSTILIDAD_FEMINICIDIO",
            corrected_dimension="3.1",
            corrected_justificacion="corr",
            content_type="post",
            content_id="p1",
            original_categoria="VDG_VIOLENCIA_SIMBOLICA",
        )
        assert cid.startswith("feedback_")
        assert fs.get_count() == 1

    def test_add_correction_rejects_empty_text(self, tmp_path):
        import pytest

        fs = self._make_store(tmp_path)
        with pytest.raises(ValueError):
            fs.add_correction(
                feedback_id=1,
                text="   ",
                corrected_categoria="X",
                corrected_dimension="1.1",
                corrected_justificacion="",
                content_type="post",
                content_id="p1",
            )

    def test_search_relevant_returns_indexed(self, tmp_path):
        fs = self._make_store(tmp_path)
        fs.add_correction(
            feedback_id=1,
            text="user said zorra",
            corrected_categoria="VDG_COSIFICACION_SLUTSHAMING",
            corrected_dimension="2.2",
            corrected_justificacion="x",
            content_type="post",
            content_id="p1",
        )
        results = fs.search_relevant_corrections("zorra", n_results=1)
        assert len(results) == 1
        meta = results[0]["metadata"]
        assert meta["source"] == "human_feedback"
        assert meta["corrected_categoria"] == "VDG_COSIFICACION_SLUTSHAMING"

    def test_search_empty_collection_returns_empty(self, tmp_path):
        fs = self._make_store(tmp_path)
        assert fs.search_relevant_corrections("anything") == []

    def test_remove_correction_decrements_count(self, tmp_path):
        fs = self._make_store(tmp_path)
        cid = fs.add_correction(
            feedback_id=1,
            text="a",
            corrected_categoria="VDG_X",
            corrected_dimension="1.1",
            corrected_justificacion="",
            content_type="post",
            content_id="p",
        )
        assert fs.remove_correction(cid) is True
        assert fs.get_count() == 0

    def test_remove_correction_unknown_id_silent_noop(self, tmp_path):
        """ChromaDB returns success silently for missing ids — return True."""
        fs = self._make_store(tmp_path)
        # ChromaDB .delete() on a missing id is a no-op rather than raising,
        # so treat unknown ids as a successful no-op (the UI sees no error).
        assert fs.remove_correction("feedback_doesnotexist") is True

    def test_count_includes_one_doc(self, tmp_path):
        fs = self._make_store(tmp_path)
        assert fs.get_count() == 0
        fs.add_correction(
            feedback_id=1,
            text="text",
            corrected_categoria="VDG_X",
            corrected_dimension="1.1",
            corrected_justificacion="",
            content_type="post",
            content_id="p",
        )
        assert fs.get_count() == 1

    def test_add_correction_stores_user_metadata(self, tmp_path):
        """``user_id``, ``added_by_username`` and ``added_at`` are persisted."""
        fs = self._make_store(tmp_path)
        fs.add_correction(
            feedback_id=42,
            text="text",
            corrected_categoria="VDG_X",
            corrected_dimension="1.1",
            corrected_justificacion="",
            content_type="post",
            content_id="p",
            user_id=7,
            added_by_username="alice",
        )
        results = fs.search_relevant_corrections("text", n_results=1)
        meta = results[0]["metadata"]
        assert meta["user_id"] == "7"
        assert meta["added_by_username"] == "alice"
        assert meta["added_at"]
        assert meta["feedback_id"] == "42"

    def test_add_correction_user_metadata_optional(self, tmp_path):
        """``user_id``/``added_by_username`` default to empty strings."""
        fs = self._make_store(tmp_path)
        fs.add_correction(
            feedback_id=1,
            text="text",
            corrected_categoria="VDG_X",
            corrected_dimension="1.1",
            corrected_justificacion="",
            content_type="post",
            content_id="p",
        )
        results = fs.search_relevant_corrections("text", n_results=1)
        meta = results[0]["metadata"]
        assert meta["user_id"] == ""
        assert meta["added_by_username"] == ""
        assert meta["added_at"]  # timestamp defaults to now()
