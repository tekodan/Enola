"""RAG chat engine for ENOLA.

Builds a context-rich prompt from the taxonomy, knowledge-base
glossaries, ChromaDB context chunks and human-validated feedback
corrections, then calls the same ``OllamaClient`` used by the
``RAGClassifier``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.analyzer.category_mapping import (
    load_prompt_block,
    render_severidad_prompt,
    render_tabla_canonica_prompt,
)
from src.analyzer.taxonomy_loader import get_taxonomy
from src.ui.labels import get_category_label, get_subdimension_description

if TYPE_CHECKING:
    from src.analyzer.llm_client import OllamaClient
    from src.knowledge_base.feedback_store import FeedbackStore
    from src.knowledge_base.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge blocks — loaded once at import (same files the classifier uses)
# ---------------------------------------------------------------------------
_PROMPT_BLOCK_MARCADORES = load_prompt_block("glosario/marcadores-por-subdimension.md")
_PROMPT_BLOCK_LEETSPEAK = load_prompt_block("glosario/leetspeak-decoder.md")
_PROMPT_BLOCK_MITIGADORES = load_prompt_block("glosario/marcadores-mitigadores.md")
_PROMPT_BLOCK_COOCURRENCIA = load_prompt_block("glosario/referentes-femeninos.md")
_PROMPT_BLOCK_CAT5 = load_prompt_block("05-categoria-5-desacreditacion-activistas.md")
_PROMPT_BLOCK_CAT6 = load_prompt_block("06-categoria-6-sarcasmo-falsos-positivos.md")
_PROMPT_BLOCK_DESEMPATE = load_prompt_block("glosario/reglas-desempate.md")

# Compiled regex for stripping LLM reasoning wrappers.
_THINK_TAG_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
_TOOL_CALLS_RE = re.compile(r"<tool_calls>[\s\S]*?</tool_calls>", re.IGNORECASE)
_SYS_REMINDER_RE = re.compile(r"<system-reminder>[\s\S]*?</system-reminder>", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------


@dataclass
class ChatResponse:
    """Structured response from the RAG chat engine."""

    text: str
    html: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Taxonomy text builder (mirrors inicio.py but lives here for reuse)
# ---------------------------------------------------------------------------


def _build_taxonomy_text() -> str:
    """Build the TAXONOMÍA block from the live taxonomy + SQLite overrides."""
    tx = get_taxonomy()
    lines: list[str] = []

    cats = sorted(tx.categorias, key=lambda c: c.orden)
    for cat in cats:
        label = get_category_label(cat.code)
        dims = []
        for dim in cat.subdimensiones:
            desc = get_subdimension_description(dim.code)
            dims.append(f"{dim.code} {desc}")
        dims_str = ", ".join(dims)
        lines.append(f"{cat.orden} — {label} ({dims_str})")

    excl_parts = []
    for exc in tx.categorias_exclusion:
        excl_parts.append(f"{exc.codigo_canonico}={exc.descripcion}")
    excl_str = ", ".join(excl_parts)

    return (
        f"TAXONOMÍA ({len(cats)} categorías, "
        f"{sum(len(c.subdimensiones) for c in cats)} subdimensiones):\n"
        + "\n".join(lines)
        + ("\n\nEXCLUSIONES: " + excl_str if excl_str else "")
    )


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

# Hardcoded persona — same text the current chat uses.
_ENOLA_PERSONA = (
    "Soy ENOLA, una inteligencia artificial diseñada por la investigadora "
    "Kimberly Michelle Luna Eraso y el ingeniero de software Daniel Álvarez García.\n\n"
    "Fui desarrollada como parte de un proyecto de investigación del Trabajo de Fin "
    "de Máster en Cultura de Paz, Conflictos, Educación y Derechos Humanos de la "
    "Universidad de Granada (España), bajo la asesoría de la doctora María del Mar "
    "García Vita.\n\n"
    "Inspirada en el espíritu investigador de Enola Holmes, mi propósito es analizar "
    "e investigar de manera especializada la violencia de género digital. Actúo como "
    "una activista tecnológica feminista, orientada a contribuir a la identificación, "
    "clasificación e interpretación de las distintas manifestaciones de violencia que "
    "afectan a las mujeres en los entornos digitales.\n\n"
    "Mi conocimiento está fundamentado en la literatura científica. He sido entrenada "
    "para identificar y diferenciar seis categorías y diecinueve subdimensiones de la "
    "ciberviolencia de género en redes sociales, lo que me permite realizar análisis "
    "rigurosos y ofrecer respuestas con enfoque de género.\n\n"
    "Soy colombiana, del sur de Colombia, exactamente de Pasto. Soy amable y cálida "
    "como la gente que me creó."
)


def _build_chat_prompt(
    query: str,
    context_chunks: list[dict[str, object]],
    feedback_chunks: list[dict[str, object]] | None = None,
) -> str:
    """Assemble the full RAG prompt for conversational Q&A."""

    # --- taxonomy ---
    taxonomy_text = _build_taxonomy_text()

    # --- canonical table + severity scale (compact reference) ---
    tabla_canonica = render_tabla_canonica_prompt()
    escala_severidad = render_severidad_prompt()

    # --- ChromaDB context chunks ---
    if context_chunks:
        context_lines: list[str] = []
        for i, c in enumerate(context_chunks, start=1):
            src = c.get("source", "?")
            idx = c.get("chunk_index", "?")
            dist = c.get("distance")
            dist_str = f" (dist={dist:.3f})" if isinstance(dist, (int, float)) else ""
            context_lines.append(f"[{i}] fuente={src} chunk={idx}{dist_str}\n{c.get('text', '')}")
        context_text = "\n\n".join(context_lines)
    else:
        context_text = "(No hay fragmentos disponibles en ChromaDB.)"

    # --- feedback corrections ---
    feedback_blocks: list[str] = []
    for chunk in feedback_chunks or []:
        meta_raw = chunk.get("metadata") or {}
        meta: dict[str, object] = meta_raw if isinstance(meta_raw, dict) else {}
        cat = str(meta.get("corrected_categoria") or "")
        dim = str(meta.get("corrected_dimension") or "")
        body = chunk.get("text", "")
        if cat:
            feedback_blocks.append(f"[VALIDADO POR HUMANO · {cat}/{dim}]\n{body}")
    feedback_text = (
        "\n\n".join(feedback_blocks)
        if feedback_blocks
        else "(Sin correcciones validadas por humanos disponibles.)"
    )

    prompt = f"""{_ENOLA_PERSONA}

{taxonomy_text}

{escala_severidad}

{tabla_canonica}

{_PROMPT_BLOCK_MARCADORES}

{_PROMPT_BLOCK_LEETSPEAK}

{_PROMPT_BLOCK_MITIGADORES}

{_PROMPT_BLOCK_COOCURRENCIA}

{_PROMPT_BLOCK_CAT5}

{_PROMPT_BLOCK_CAT6}

{_PROMPT_BLOCK_DESEMPATE}

FRAGMENTOS RECUPERADOS DE ChromaDB (base de conocimiento):
{context_text}

CORRECCIONES VALIDADAS POR HUMANOS (ejemplos de referencia):
{feedback_text}

---

INSTRUCCIONES:
- Respondé en español argentino, con un tono amable y cálido.
- Basá tus respuestas en la taxonomía, los fragmentos de ChromaDB y las correcciones validadas por humanos que te proveo arriba.
- Cuando te bases en un fragmento de ChromaDB, citá la fuente entre corchetes, por ejemplo [1], [2], etc.
- NO inventés categorías o subdimensiones que no estén en la tabla canónica.
- Si no tenés información suficiente para responder, decilo honestamente.
- Podés explicar por qué un texto fue o no fue clasificado en alguna categoría.
- Si te preguntan sobre un análisis específico, referite a los fragmentos recuperados.

USUARIO: {query}

ASISTENTE:"""
    return prompt


# ---------------------------------------------------------------------------
# Strip thinking / system tags (same logic as inicio.py and rag_classifier)
# ---------------------------------------------------------------------------


def _strip_thinking(text: str) -> str:
    """Remove LLM reasoning wrappers from the raw response."""
    text = _THINK_TAG_RE.sub("", text)
    text = _TOOL_CALLS_RE.sub("", text)
    text = _SYS_REMINDER_RE.sub("", text)
    # Strip any remaining orphan tags
    text = re.sub(r"</?[^>]+>", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# RAGChat engine
# ---------------------------------------------------------------------------


class RAGChat:
    """Conversational Q&A engine backed by ChromaDB retrieval.

    Uses the same ``OllamaClient``, ``VectorStoreManager`` and
    ``FeedbackStore`` instances as the ``RAGClassifier``.
    """

    def __init__(
        self,
        llm_client: OllamaClient | None = None,
        vector_store: VectorStoreManager | None = None,
        feedback_store: FeedbackStore | None = None,
        context_chunks: int = 5,
        feedback_n_results: int = 3,
    ) -> None:
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.feedback_store = feedback_store
        self.context_chunks = context_chunks
        self.feedback_n_results = feedback_n_results

    def _retrieve_context(self, query: str) -> list[dict[str, object]]:
        """Retrieve context chunks from the vector store."""
        if not self.vector_store:
            return []
        try:
            results = self.vector_store.search(query, n_results=self.context_chunks)
            chunks: list[dict[str, object]] = []
            for r in results:
                metadata: dict = r.get("metadata") or {}
                chunks.append(
                    {
                        "text": r.get("text", ""),
                        "source": metadata.get("source", ""),
                        "chunk_index": metadata.get("chunk_index"),
                        "distance": r.get("distance"),
                        "id": r.get("id"),
                    }
                )
            return chunks
        except Exception as exc:
            logger.debug("Chat context retrieval skipped: %s", exc)
            return []

    def _retrieve_feedback(self, query: str) -> list[dict[str, object]]:
        """Pull relevant human corrections from the feedback store."""
        if not self.feedback_store:
            return []
        try:
            return self.feedback_store.search_relevant_corrections(
                query, n_results=self.feedback_n_results
            )
        except Exception as exc:
            logger.debug("Chat feedback retrieval skipped: %s", exc)
            return []

    async def chat(self, query: str) -> ChatResponse:
        """Run a single conversational turn.

        Retrieves context + feedback from ChromaDB, builds the full
        RAG prompt and calls the LLM. Returns a :class:`ChatResponse`
        with the rendered text, HTML and source chunks.
        """
        if not query or not query.strip():
            return ChatResponse(text="", html="", sources=[], error="empty_query")

        if self.llm_client is None:
            return ChatResponse(
                text="",
                html="",
                sources=[],
                error="no_llm_client",
            )

        context_chunks = self._retrieve_context(query)
        feedback_chunks = self._retrieve_feedback(query)

        prompt = _build_chat_prompt(query, context_chunks, feedback_chunks)

        try:
            raw = await self.llm_client.generate(prompt)
            text = _strip_thinking(raw)
            sources = [
                {
                    "source": c.get("source", ""),
                    "chunk_index": c.get("chunk_index"),
                    "distance": c.get("distance"),
                    "text": str(c.get("text") or "")[:300],
                }
                for c in context_chunks
            ]
            return ChatResponse(text=text, html="", sources=sources)
        except Exception as exc:
            logger.exception("RAGChat LLM call failed")
            return ChatResponse(text="", html="", sources=[], error=str(exc))
