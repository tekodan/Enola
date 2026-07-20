"""Unit tests for chat module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.chat.rag_chat import (
    ChatResponse,
    RAGChat,
    _build_chat_prompt,
    _build_taxonomy_text,
    _strip_thinking,
)


class TestChatResponse:
    """Tests for ChatResponse dataclass."""

    def test_defaults(self):
        resp = ChatResponse(text="hola", html="<p>hola</p>")
        assert resp.text == "hola"
        assert resp.html == "<p>hola</p>"
        assert resp.sources == []
        assert resp.error is None

    def test_with_sources(self):
        sources = [{"source": "test.md", "chunk_index": 0, "distance": 0.5, "text": "hi"}]
        resp = ChatResponse(text="ok", html="", sources=sources)
        assert len(resp.sources) == 1
        assert resp.sources[0]["source"] == "test.md"

    def test_error(self):
        resp = ChatResponse(text="", html="", error="no_llm")
        assert resp.error == "no_llm"


class TestStripThinking:
    """Tests for _strip_thinking."""

    def test_think_tags(self):
        raw = "<think>some reasoning</think> actual response"
        assert _strip_thinking(raw) == "actual response"

    def test_tool_calls(self):
        raw = "<tool_calls>json here</tool_calls> real answer"
        assert _strip_thinking(raw) == "real answer"

    def test_system_reminder(self):
        raw = "<system-reminder>ignore this</system-reminder> response"
        assert _strip_thinking(raw) == "response"

    def test_orphan_tags(self):
        raw = "<b>bold</b> text"
        assert _strip_thinking(raw) == "bold text"

    def test_clean_text(self):
        assert _strip_thinking("hello world") == "hello world"

    def test_empty(self):
        assert _strip_thinking("") == ""


class TestBuildTaxonomyText:
    """Tests for _build_taxonomy_text."""

    @patch("src.chat.rag_chat.get_taxonomy")
    @patch("src.chat.rag_chat.get_category_label")
    @patch("src.chat.rag_chat.get_subdimension_description")
    def test_basic_structure(self, mock_dim_desc, mock_cat_label, mock_get_tax):
        cat = MagicMock()
        cat.code = "VDG_VIOLENCIA_SIMBOLICA"
        cat.orden = 1
        cat.subdimensiones = [MagicMock(code="1.1"), MagicMock(code="1.2")]

        exc = MagicMock()
        exc.codigo_canonico = "EXC_BASURA_DIGITAL"
        exc.descripcion = "Basura digital"

        tax = MagicMock()
        tax.categorias = [cat]
        tax.categorias_exclusion = [exc]
        mock_get_tax.return_value = tax
        mock_cat_label.return_value = "Violencia Simbólica"
        mock_dim_desc.side_effect = lambda code: f"Desc {code}"

        result = _build_taxonomy_text()
        assert "TAXONOMÍA" in result
        assert "Violencia Simbólica" in result
        assert "1.1" in result
        assert "EXC_BASURA_DIGITAL" in result


class TestBuildChatPrompt:
    """Tests for _build_chat_prompt."""

    @patch("src.chat.rag_chat._build_taxonomy_text", return_value="TAXONOMIA")
    @patch("src.chat.rag_chat.render_tabla_canonica_prompt", return_value="TABLE")
    @patch("src.chat.rag_chat.render_severidad_prompt", return_value="SEV")
    def test_basic_prompt(self, _sev, _tbl, _tax):
        prompt = _build_chat_prompt("hola", [], [])
        assert "Soy ENOLA" in prompt
        assert "TAXONOMIA" in prompt
        assert "TABLE" in prompt
        assert "USUARIO: hola" in prompt
        assert "ASISTENTE:" in prompt

    @patch("src.chat.rag_chat._build_taxonomy_text", return_value="TAXONOMIA")
    @patch("src.chat.rag_chat.render_tabla_canonica_prompt", return_value="TABLE")
    @patch("src.chat.rag_chat.render_severidad_prompt", return_value="SEV")
    def test_context_chunks(self, _sev, _tbl, _tax):
        chunks = [
            {"text": "chunk1", "source": "file.md", "chunk_index": 0, "distance": 0.2},
            {"text": "chunk2", "source": "other.md", "chunk_index": 1, "distance": 0.4},
        ]
        prompt = _build_chat_prompt("test", chunks, [])
        assert "[1] fuente=file.md" in prompt
        assert "[2] fuente=other.md" in prompt
        assert "chunk1" in prompt
        assert "chunk2" in prompt

    @patch("src.chat.rag_chat._build_taxonomy_text", return_value="TAXONOMIA")
    @patch("src.chat.rag_chat.render_tabla_canonica_prompt", return_value="TABLE")
    @patch("src.chat.rag_chat.render_severidad_prompt", return_value="SEV")
    def test_feedback_chunks(self, _sev, _tbl, _tax):
        feedback = [
            {
                "text": "TEXTO: hi RESULTADO: {}",
                "metadata": {
                    "corrected_categoria": "VDG_VIOLENCIA_SIMBOLICA",
                    "corrected_dimension": "1.1",
                },
                "distance": 0.3,
                "id": "fb_1",
            }
        ]
        prompt = _build_chat_prompt("test", [], feedback)
        assert "[VALIDADO POR HUMANO · VDG_VIOLENCIA_SIMBOLICA/1.1]" in prompt

    @patch("src.chat.rag_chat._build_taxonomy_text", return_value="TAXONOMIA")
    @patch("src.chat.rag_chat.render_tabla_canonica_prompt", return_value="TABLE")
    @patch("src.chat.rag_chat.render_severidad_prompt", return_value="SEV")
    def test_no_chunks_message(self, _sev, _tbl, _tax):
        prompt = _build_chat_prompt("test", [], [])
        assert "No hay fragmentos disponibles" in prompt


class TestRAGChat:
    """Tests for RAGChat class."""

    def test_init_defaults(self):
        chat = RAGChat()
        assert chat.llm_client is None
        assert chat.vector_store is None
        assert chat.feedback_store is None
        assert chat.context_chunks == 5
        assert chat.feedback_n_results == 3

    def test_init_custom(self):
        chat = RAGChat(context_chunks=10, feedback_n_results=5)
        assert chat.context_chunks == 10
        assert chat.feedback_n_results == 5

    def test_retrieve_context_no_store(self):
        chat = RAGChat()
        assert chat._retrieve_context("test") == []

    def test_retrieve_feedback_no_store(self):
        chat = RAGChat()
        assert chat._retrieve_feedback("test") == []

    def test_retrieve_context_with_store(self):
        mock_store = MagicMock()
        mock_store.search.return_value = [
            {
                "text": "chunk1",
                "metadata": {"source": "a.md", "chunk_index": 0},
                "distance": 0.1,
                "id": "1",
            }
        ]
        chat = RAGChat(vector_store=mock_store, context_chunks=3)
        result = chat._retrieve_context("test query")
        assert len(result) == 1
        assert result[0]["text"] == "chunk1"
        assert result[0]["source"] == "a.md"
        mock_store.search.assert_called_once_with("test query", n_results=3)

    def test_retrieve_feedback_with_store(self):
        mock_store = MagicMock()
        mock_store.search_relevant_corrections.return_value = [
            {"text": "fb1", "metadata": {}, "distance": 0.2, "id": "fb_1"}
        ]
        chat = RAGChat(feedback_store=mock_store, feedback_n_results=2)
        result = chat._retrieve_feedback("test")
        assert len(result) == 1
        mock_store.search_relevant_corrections.assert_called_once_with("test", n_results=2)

    def test_retrieve_context_exception_handled(self):
        mock_store = MagicMock()
        mock_store.search.side_effect = RuntimeError("chromadb down")
        chat = RAGChat(vector_store=mock_store)
        result = chat._retrieve_context("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_chat_no_client(self):
        chat = RAGChat()
        result = await chat.chat("hola")
        assert result.error == "no_llm_client"

    @pytest.mark.asyncio
    async def test_chat_empty_query(self):
        chat = RAGChat()
        result = await chat.chat("")
        assert result.error == "empty_query"

    @pytest.mark.asyncio
    async def test_chat_with_mock_llm(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Respuesta de ENOLA"
        mock_vs = MagicMock()
        mock_vs.search.return_value = []
        mock_fs = MagicMock()
        mock_fs.search_relevant_corrections.return_value = []

        chat = RAGChat(llm_client=mock_llm, vector_store=mock_vs, feedback_store=mock_fs)
        result = await chat.chat("qué es VDG_VIOLENCIA_SIMBOLICA?")

        assert result.text == "Respuesta de ENOLA"
        assert result.error is None
        assert result.sources == []
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_strips_thinking(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "<think>reasoning</think> real answer"
        chat = RAGChat(llm_client=mock_llm)
        result = await chat.chat("test")
        assert result.text == "real answer"
        assert "<think>" not in result.text

    @pytest.mark.asyncio
    async def test_chat_includes_sources(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "ok"
        mock_vs = MagicMock()
        mock_vs.search.return_value = [
            {
                "text": "chunk text",
                "metadata": {"source": "test.md", "chunk_index": 2},
                "distance": 0.123,
                "id": "doc_1",
            }
        ]
        chat = RAGChat(llm_client=mock_llm, vector_store=mock_vs)
        result = await chat.chat("test")
        assert len(result.sources) == 1
        assert result.sources[0]["source"] == "test.md"
        assert result.sources[0]["chunk_index"] == 2
        assert result.sources[0]["text"] == "chunk text"
