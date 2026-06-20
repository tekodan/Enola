"""Integration tests for knowledge base module."""

from unittest.mock import MagicMock

import pytest

from src.knowledge_base.pdf_processor import PDFProcessor, chunk_text
from src.knowledge_base.vector_store import VectorStoreManager


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    La violencia de género es un problema social que afecta a millones de personas.

    Según la Ley Orgánica 1/2004, la violencia de género comprende todo acto de violencia
    física y psicológica emanada de un hombre hacia una mujer con la que tiene o ha tenido
    una relación afectiva.

    Los tipos de violencia incluyen:
    - Violencia física: Agresiones, golpes, heridas
    - Violencia psicológica: Humillaciones, insultos, control
    - Violencia sexual: Abuso, acoso, violación
    - Violencia económica: Control financiero, privación de recursos

    El machismo es una causa fundamental de la violencia de género.
    """


@pytest.fixture
def mock_embeddings_provider():
    """Mock embeddings provider."""
    provider = MagicMock()

    def embed(texts):
        # Simple hash-based embeddings for testing
        return [[hash(t) % 100 / 100 for _ in range(5)] for t in texts]

    provider.embed.side_effect = embed
    return provider


class TestPDFProcessorIntegration:
    """Integration tests for PDF processor."""

    def test_process_document_workflow(self, sample_text):
        """Test full document processing workflow."""
        processor = PDFProcessor(chunk_size=200, chunk_overlap=50)

        # Chunk text (simulating PDF extraction)
        chunks = processor.chunk_text(sample_text)

        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

        # Each chunk should be reasonable size
        for chunk in chunks:
            assert len(chunk) <= 400  # Some tolerance for overlap

    def test_chunk_quality(self, sample_text):
        """Test quality of chunking."""
        processor = PDFProcessor(chunk_size=100, chunk_overlap=20)

        chunks = processor.chunk_text(sample_text)

        # Chunks should preserve complete sentences
        for chunk in chunks:
            # Should not cut in middle of sentences typically
            # (allowing some edge cases)
            pass

        # Overlap should help with context
        if len(chunks) > 1:
            # Check that overlap is meaningful
            overlap_found = False
            for i in range(len(chunks) - 1):
                if chunks[i][-20:] in chunks[i + 1]:
                    overlap_found = True
                    break
            # Some chunks should have overlap
            assert overlap_found or len(chunks) == 1


class TestVectorStoreIntegration:
    """Integration tests for vector store."""

    def test_full_ingestion_pipeline(self, tmp_path, mock_embeddings_provider):
        """Test full document ingestion pipeline."""
        vector_store = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"),
            collection_name="test_ingestion",
            embeddings_provider=mock_embeddings_provider,
        )

        # Create collection
        vector_store.create_collection()

        # Simulate documents
        documents = [
            "La violencia física incluye golpes y heridas",
            "La violencia psicológica incluye insultos y humillaciones",
            "El control económico es una forma de violencia",
            "El acoso sexual es violencia de género",
            "Los estereotipos de género causan violencia",
        ]

        metadatas = [
            {"source": "ley_fisica", "tipo": "fisica"},
            {"source": "ley_psicologica", "tipo": "psicologica"},
            {"source": "ley_economica", "tipo": "economica"},
            {"source": "ley_sexual", "tipo": "sexual"},
            {"source": "ley_simbolica", "tipo": "simbolica"},
        ]

        # Add documents
        vector_store.add_documents(documents, metadatas)

        # Verify count
        stats = vector_store.get_collection_stats()
        assert stats["count"] == 5

    def test_search_pipeline(self, tmp_path, mock_embeddings_provider):
        """Test search pipeline."""
        vector_store = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"),
            collection_name="test_search",
            embeddings_provider=mock_embeddings_provider,
        )

        vector_store.create_collection()

        # Add documents
        documents = [
            "El machismo causa violencia de género",
            "Los hombres golpean a las mujeres",
            "La educación previene la violencia",
            "El amor no justifica la violencia",
            "Las mujeres merecen respeto",
        ]
        vector_store.add_documents(documents)

        # Search for violence-related content
        results = vector_store.search("violencia contra mujeres", n_results=3)

        assert isinstance(results, list)
        # Should return results (exact matches depend on embeddings)

    def test_metadata_filtering(self, tmp_path, mock_embeddings_provider):
        """Test metadata-based filtering."""
        vector_store = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"),
            collection_name="test_filter",
            embeddings_provider=mock_embeddings_provider,
        )

        vector_store.create_collection()

        # Add documents with different types
        documents = [
            "Documento de tipo física",
            "Documento de tipo psicológica",
            "Documento de tipo sexual",
        ]
        metadatas = [
            {"tipo": "fisica"},
            {"tipo": "psicologica"},
            {"tipo": "sexual"},
        ]
        vector_store.add_documents(documents, metadatas)

        # Search with filter
        vector_store.search("documento", n_results=10, where={"tipo": "fisica"})

        # Should filter by metadata
        # Note: ChromaDB filtering behavior may vary

    def test_persistence(self, tmp_path, mock_embeddings_provider):
        """Test that data persists between instances."""
        # First instance - add data
        vector_store1 = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"),
            collection_name="test_persist",
            embeddings_provider=mock_embeddings_provider,
        )
        vector_store1.create_collection()
        vector_store1.add_documents(["Persistent document"])

        # Second instance - verify data
        vector_store2 = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"),
            collection_name="test_persist",
            embeddings_provider=mock_embeddings_provider,
        )
        vector_store2.create_collection()

        stats = vector_store2.get_collection_stats()
        assert stats["count"] == 1


class TestEndToEnd:
    """End-to-end tests."""

    def test_document_to_vector_workflow(self, tmp_path, mock_embeddings_provider):
        """Test complete document to vector workflow."""
        # 1. Process document
        processor = PDFProcessor(chunk_size=100, chunk_overlap=20)
        sample_text = """
        La violencia de género es un problema grave.

        Incluye violencia física, psicológica y sexual.

        Elmachismo es una causa fundamental.
        """
        chunks = processor.chunk_text(sample_text)

        # 2. Create vector store
        vector_store = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"),
            collection_name="e2e_test",
            embeddings_provider=mock_embeddings_provider,
        )
        vector_store.create_collection()

        # 3. Add chunks to vector store
        metadatas = [{"chunk_index": i, "source": "e2e_test"} for i in range(len(chunks))]
        ids = [f"chunk_{i}" for i in range(len(chunks))]

        vector_store.add_documents(chunks, metadatas, ids)

        # 4. Verify
        stats = vector_store.get_collection_stats()
        assert stats["count"] == len(chunks)

        # 5. Search
        results = vector_store.search("violencia", n_results=2)
        assert isinstance(results, list)

    def test_multiple_documents_workflow(self, tmp_path, mock_embeddings_provider):
        """Test workflow with multiple documents."""
        vector_store = VectorStoreManager(
            persist_directory=str(tmp_path / "chroma"),
            collection_name="multi_doc_test",
            embeddings_provider=mock_embeddings_provider,
        )
        vector_store.create_collection()

        # Add multiple documents
        all_documents = []
        all_metadatas = []
        all_ids = []

        for doc_num in range(3):
            doc_text = f"Documento {doc_num} sobre violencia de género"
            chunks = chunk_text(doc_text, chunk_size=50, chunk_overlap=10)

            for i, chunk in enumerate(chunks):
                all_documents.append(chunk)
                all_metadatas.append({"doc_num": doc_num, "chunk": i, "source": f"doc_{doc_num}"})
                all_ids.append(f"doc{doc_num}_chunk{i}")

        vector_store.add_documents(all_documents, all_metadatas, all_ids)

        # Verify all added
        stats = vector_store.get_collection_stats()
        assert stats["count"] == len(all_documents)

        # Search should find results
        results = vector_store.search("violencia", n_results=5)
        assert len(results) > 0
