"""SPEC: Knowledge Base Module.

Este módulo se encarga del procesamiento de documentos PDF y la creación
del vector store para el RAG.

## Responsabilidades
- Extraer texto de PDFs
- Chunking inteligente de texto
- Almacenamiento en ChromaDB
- Búsqueda de chunks relevantes

## Modelo de Datos

### PDFProcessor
Procesador de PDFs.
- extract_text_from_pdf: Extrae texto de un PDF
- chunk_text: Divide texto en chunks
- process_document: Procesa un documento completo

### VectorStoreManager
Gestor del vector store en ChromaDB.
- create_collection: Crea o obtiene la colección
- add_documents: Agrega documentos al vector store
- search: Busca documentos similares
- get_collection_stats: Estadísticas de la colección

## API Pública

### PDFProcessor
```python
from src.knowledge_base import PDFProcessor

processor = PDFProcessor(chunk_size=500, chunk_overlap=50)

# Extraer texto de PDF
text = processor.extract_text_from_pdf("documento.pdf")

# Chunkear texto
chunks = processor.chunk_text(text)

# Procesar documento completo
documents = processor.process_document("documento.pdf", source_name="Ley VG")
```

### VectorStoreManager
```python
from src.knowledge_base import VectorStoreManager

vector_store = VectorStoreManager(
    persist_directory="data/chroma_db",
    collection_name="violencia_genero",
    embeddings_provider=provider
)

# Agregar documentos
vector_store.add_documents(
    documents=["texto1", "texto2"],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}],
    ids=["id1", "id2"]
)

# Buscar documentos similares
results = vector_store.search("texto a buscar", n_results=5)
```

## Dependencias
- pdfplumber o PyPDF2: Extracción de PDF
- chromadb: Vector store

## Tests
Ver test_unit.py y test_integration.py para casos de prueba.
"""
