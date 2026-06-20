"""Vector store module for ChromaDB."""

from pathlib import Path
from typing import Protocol

from chromadb import PersistentClient


class EmbeddingsProvider(Protocol):
    """Protocol for embeddings provider."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...


class VectorStoreManager:
    """Manager for ChromaDB vector store."""

    def __init__(
        self,
        persist_directory: str = "data/chroma_db",
        collection_name: str = "violencia_genero",
        embeddings_provider: EmbeddingsProvider | None = None,
    ):
        """Initialize vector store manager.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection
            embeddings_provider: Provider for generating embeddings
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embeddings_provider = embeddings_provider

        # Ensure directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = PersistentClient(path=str(self.persist_directory))
        self.collection = None

    def create_collection(self) -> None:
        """Create or get the collection."""
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Violencia de género knowledge base"},
        )

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of document texts
            metadatas: Optional list of metadata dicts
            ids: Optional list of document IDs. If ``None``, IDs are
                auto-generated as ``doc_{start_idx}`` where ``start_idx``
                continues from the current collection size, so multiple
                calls do not collide.
        """
        if self.collection is None:
            self.create_collection()

        if ids is None:
            start = self.collection.count()
            ids = [f"doc_{start + i}" for i in range(len(documents))]

        if metadatas is None:
            metadatas = [{"source": f"doc_{i}"} for i in range(len(documents))]
        else:
            metadatas = [
                meta if meta else {"source": f"doc_{i}"} for i, meta in enumerate(metadatas)
            ]

        # Generate embeddings if provider is available
        if self.embeddings_provider:
            embeddings = self.embeddings_provider.embed(documents)
        else:
            # ChromaDB will use default embeddings
            embeddings = None

        self.collection.add(
            documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings
        )

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """Search for similar documents.

        Args:
            query: Query text
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            List of result documents with scores
        """
        if self.collection is None:
            self.create_collection()

        # Generate query embedding
        if self.embeddings_provider:
            query_embedding = self.embeddings_provider.embed([query])[0]
        else:
            query_embedding = None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            query_embeddings=[query_embedding] if query_embedding else None,
        )

        # Format results
        formatted = []
        for i, doc in enumerate(results["documents"][0]):
            formatted.append(
                {
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "id": results["ids"][0][i],
                }
            )

        return formatted

    def get_collection_stats(self) -> dict:
        """Get collection statistics."""
        if self.collection is None:
            return {"count": 0}

        return {
            "count": self.collection.count(),
            "name": self.collection_name,
        }

    def delete_collection(self) -> None:
        """Delete the collection."""
        if self.collection is not None:
            self.client.delete_collection(name=self.collection_name)
            self.collection = None


# Global vector store instance
_vector_store: VectorStoreManager | None = None


def get_vector_store(
    persist_directory: str = "data/chroma_db",
    collection_name: str = "violencia_genero",
    embeddings_provider: EmbeddingsProvider | None = None,
) -> VectorStoreManager:
    """Get or create vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreManager(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embeddings_provider=embeddings_provider,
        )
    return _vector_store
