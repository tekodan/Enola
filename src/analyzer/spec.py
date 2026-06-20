"""SPEC: Analyzer Module.

Este módulo se encarga de la clasificación de contenido usando RAG
y few-shot learning para detectar violencia de género digital.

## Responsabilidades
- Clasificar posts y comentarios
- Recuperar contexto desde ChromaDB (taxonomía del marco teórico)
- Few-shot learning con ejemplos
- Calcular similitud con posts semilla

## Modelo de Datos

### Categorías y sub-dimensiones (ChromaDB-driven)

La taxonomía de violencia de género digital **NO está hardcodeada**.
Vive en la base vectorial ChromaDB (colección ``violencia_genero``,
fuente ``CATEGORIAS TFM CONSOLIDADO.md``) y se recupera en tiempo
de clasificación.

Estructura de cada categoría:

- Categoría de Nivel 1 (ej: "1.2 Violencia Sexual Digital y Cosificación")
- Sub-dimensión (ej: "1.2.1 IBSA", opcional)
- Código programático (ej: "VDG_ODIO_MISOGINO", opcional)

### Severity (única escala fija)
Enum con niveles de severidad del clasificador:
- BAJA
- MEDIA
- ALTA
- NINGUNA

### ClassificationResult
Resultado de clasificación (lo que devuelve el LLM en JSON):
- tiene_violencia: bool
- categoria: str (de ChromaDB)
- dimension: str | None (de ChromaDB)
- codigo: str | None (de ChromaDB)
- severidad: Severity
- confianza: float (opcional)
- justificacion: str
- evidencia: str

### RAGClassifier
Clasificador RAG:
- classify: Clasifica un texto
- classify_batch: Clasifica múltiples textos
- _build_prompt: Construye prompt con contexto de ChromaDB
- _rule_based_classify: Fallback sin LLM

### PostEmbeddings
Gestor de embeddings para similitud:
- create_embedding: Crea embedding
- compute_similarity: Calcula similitud
- compute_batch_similarity: Similitud en batch

## API Pública

### Clasificación
```python
from src.analyzer import RAGClassifier, ClassificationResult

classifier = RAGClassifier(
    llm_client=llm,
    vector_store=vector_store,
    context_chunks=5,
    few_shot_examples=examples,
)

result = classifier.classify_sync("Texto a clasificar")
# result.tiene_violencia, result.categoria, result.dimension,
# result.codigo, result.severidad, result.confianza
```

### Similitud
```python
from src.analyzer import PostEmbeddings

embeddings = PostEmbeddings(provider=provider)

score = embeddings.compute_similarity("texto1", "texto2")
scores = embeddings.compute_batch_similarity(texts, references)
avg = embeddings.compute_average_similarity(texts, references)
```

## Tests
Ver test_unit.py y test_integration.py para casos de prueba.
"""
