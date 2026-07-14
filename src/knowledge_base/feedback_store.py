"""FeedbackStore — ChromaDB-backed store for human-validated corrections.

Stores corrections confirmed by humans as documents in a dedicated
ChromaDB collection (``feedback_corrections``). The
:class:`~src.analyzer.rag_classifier.RAGClassifier` retrieves them at
classification time and uses them as few-shot examples so the LLM
learns from confirmed disagreements.

Mirrors the public API of :class:`VectorStoreManager` so callers can
swap them.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC
from typing import Protocol

from chromadb import PersistentClient

logger = logging.getLogger(__name__)


class EmbeddingsProvider(Protocol):
    """Protocol for embeddings provider (matches VectorStoreManager)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...


def render_few_shot_doc(
    text: str,
    *,
    categoria: str | None = None,
    dimension: str | None = None,
    justificacion: str = "",
    severidad: str = "ninguna",
    confianza: float = 1.0,
    clasificaciones: list[dict] | None = None,
) -> str:
    """Render a single few-shot example in the format ``RAGClassifier`` uses.

    The format must match ``RAGClassifier._build_prompt`` so the LLM
    treats the injected examples identically whether they come from the
    static list or from the feedback collection.

    Two call patterns are supported:

    - **Multi-label (preferred)**: pass ``clasificaciones`` — a list of
      label dicts. The result is rendered in the new
      ``clasificaciones: [...]`` schema.
    - **Single-label (legacy)**: pass ``categoria``/``dimension``/
      ``justificacion``. The result is wrapped into a 1-element list
      for backwards-compat with the older prompt schema.
    """
    if clasificaciones is None:
        if categoria and categoria != "ninguna":
            clasificaciones = [
                {
                    "categoria": categoria,
                    "dimension": dimension,
                    "severidad": severidad,
                    "confianza": confianza,
                    "regla_disparada": None,
                    "marcadores_detectados": [],
                    "es_falso_positivo_probable": False,
                    "score_ajuste": 1.0,
                    "justificacion": justificacion,
                    "evidencia": "",
                }
            ]
        else:
            clasificaciones = []

    payload = {
        "tiene_violencia": bool(clasificaciones),
        "severidad_global": max(
            (str(lbl.get("severidad") or "ninguna") for lbl in clasificaciones),
            key=lambda s: {"alta": 3, "media": 2, "baja": 1, "ninguna": 0}.get(s, 0),
            default="ninguna",
        ),
        "clasificaciones": clasificaciones,
    }
    return f'TEXTO: "{text}"\nRESULTADO: {json.dumps(payload, ensure_ascii=False)}'


class FeedbackStore:
    """ChromaDB store for human-validated corrections.

    Only disagreements with non-empty overrides are pushed here. The
    collection is **separate** from the canonical taxonomy collection
    so a malformed correction never pollutes the retrieval corpus
    used for general classification.

    Args:
        persist_directory: ChromaDB directory (same one used by
            ``VectorStoreManager``).
        collection_name: Default ``"feedback_corrections"``.
        embeddings_provider: Optional embeddings provider. If ``None``,
            ChromaDB's default embedding function is used.
    """

    DEFAULT_COLLECTION_NAME = "feedback_corrections"

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embeddings_provider: EmbeddingsProvider | None = None,
    ):
        from pathlib import Path

        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embeddings_provider = embeddings_provider

        self.client = PersistentClient(path=str(self.persist_directory))
        self.collection = None

    def create_collection(self) -> None:
        """Create or get the feedback collection."""
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "Human-validated correction few-shots for RAG",
                "source": "human_feedback",
            },
        )

    def add_correction(
        self,
        *,
        feedback_id: int,
        text: str,
        corrected_categoria: str,
        corrected_dimension: str | None,
        corrected_justificacion: str | None,
        original_categoria: str | None = None,
        content_type: str,
        content_id: str,
        reason: str | None = None,
        id: str | None = None,
        corrected_labels: list[dict] | None = None,
        user_id: int | None = None,
        added_by_username: str | None = None,
        added_at: str | None = None,
    ) -> str:
        """Push a single correction as a few-shot example document.

        Multi-label aware. If ``corrected_labels`` is given, it
        supersedes the ``corrected_categoria``/``corrected_dimension``
        trio and the few-shot doc is rendered with the full label
        list. Otherwise the call falls back to a single-label
        representation for backwards compatibility.

        Provenance metadata: pass ``user_id`` + ``added_by_username`` so
        the few-shot carries a traceable "added by @user" line.
        ``added_at`` defaults to the current UTC ISO timestamp.

        Returns the ChromaDB id of the new document.
        """
        from datetime import datetime

        if self.collection is None:
            self.create_collection()

        if not text.strip():
            raise ValueError("Cannot add empty text to feedback store")

        if corrected_labels:
            doc_text = render_few_shot_doc(
                text,
                clasificaciones=corrected_labels,
            )
        else:
            doc_text = render_few_shot_doc(
                text,
                categoria=corrected_categoria,
                dimension=corrected_dimension,
                justificacion=corrected_justificacion or "",
            )

        # Metadata mirrors the primary corrected label for quick
        # filtering (legacy: one categoria+dimension per doc).
        primary_cat = corrected_categoria
        primary_dim = corrected_dimension or ""
        if corrected_labels:
            primary = corrected_labels[0]
            primary_cat = str(primary.get("categoria") or corrected_categoria)
            primary_dim = str(primary.get("dimension") or "") or primary_dim

        added_at_iso = added_at or datetime.now(UTC).isoformat(timespec="seconds")

        metadata: dict[str, object] = {
            "source": "human_feedback",
            "feedback_id": str(feedback_id),
            "content_type": content_type,
            "content_id": content_id,
            "corrected_categoria": primary_cat,
            "corrected_dimension": primary_dim,
            "original_categoria": original_categoria or "",
            "label_count": str(len(corrected_labels) if corrected_labels else 1),
            "user_id": str(user_id) if user_id else "",
            "added_by_username": added_by_username or "",
            "added_at": added_at_iso,
        }

        start = self.collection.count() if self.collection else 0
        doc_id = id or f"feedback_{start}"

        if self.embeddings_provider:
            embeddings = self.embeddings_provider.embed([doc_text])
        else:
            embeddings = None

        self.collection.add(
            documents=[doc_text],
            metadatas=[metadata],
            ids=[doc_id],
            embeddings=embeddings,
        )
        logger.info(
            "Indexed feedback %s as ChromaDB id %s (%s/%s, %d labels)",
            feedback_id,
            doc_id,
            primary_cat,
            primary_dim,
            len(corrected_labels) if corrected_labels else 1,
        )
        return doc_id

    def search_relevant_corrections(
        self,
        query_text: str,
        n_results: int = 3,
    ) -> list[dict[str, object]]:
        """Return corrections that match the query text.

        Each result is a dict with ``text``, ``metadata``, ``distance``
        and ``id`` keys — the same shape as
        :meth:`VectorStoreManager.search`.
        """
        if self.collection is None:
            self.create_collection()

        try:
            count = self.collection.count()
        except Exception:
            count = 0
        if count == 0 or not query_text.strip():
            return []

        n = min(n_results, count)

        if self.embeddings_provider:
            query_embedding = self.embeddings_provider.embed([query_text])[0]
        else:
            query_embedding = None

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n,
                query_embeddings=[query_embedding] if query_embedding else None,
            )
        except Exception as e:
            logger.warning("Feedback search failed: %s", e)
            return []

        docs = results.get("documents", [[]])[0]
        if not docs:
            return []
        formatted: list[dict[str, object]] = []
        for i, doc in enumerate(docs):
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            formatted.append(
                {
                    "text": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": distances[i] if i < len(distances) else None,
                    "id": ids[i] if i < len(ids) else None,
                }
            )
        return formatted

    def remove_correction(self, chromadb_id: str) -> bool:
        """Remove a single correction document by ChromaDB id."""
        if self.collection is None or not chromadb_id:
            return False
        try:
            self.collection.delete(ids=[chromadb_id])
            return True
        except Exception as e:
            logger.warning("Failed to delete feedback %s: %s", chromadb_id, e)
            return False

    def get_count(self) -> int:
        """Return the number of corrections currently indexed."""
        if self.collection is None:
            try:
                self.create_collection()
            except Exception:
                return 0
        try:
            return int(self.collection.count())
        except Exception:
            return 0

    def delete_collection(self) -> None:
        """Drop the entire corrections collection (destructive)."""
        if self.collection is not None:
            self.client.delete_collection(name=self.collection_name)
            self.collection = None


# Global instance
_feedback_store: FeedbackStore | None = None

# Module-level alias for ergonomics
DEFAULT_COLLECTION_NAME: str = FeedbackStore.DEFAULT_COLLECTION_NAME


def get_feedback_store(
    persist_directory: str = "data/chroma_db",
    collection_name: str = FeedbackStore.DEFAULT_COLLECTION_NAME,
    embeddings_provider: EmbeddingsProvider | None = None,
) -> FeedbackStore:
    """Get or create the global :class:`FeedbackStore`."""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embeddings_provider=embeddings_provider,
        )
    return _feedback_store


__all__ = [
    "FeedbackStore",
    "DEFAULT_COLLECTION_NAME",
    "render_few_shot_doc",
    "get_feedback_store",
]
