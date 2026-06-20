# SPEC.md - Sistema de Detección de Violencia de Género en Facebook

## 📋 Resumen Ejecutivo

Sistema de investigación académica para detectar, clasificar y descubrir contenido con violencia de género en Facebook, utilizando ScrapeGraphAI para extracción, RAG para clasificación, y un pipeline iterativo de descubrimiento automático.

**Stack:** Python 3.12 + ScrapeGraphAI + Ollama + ChromaDB + LangChain + Streamlit

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PIPELINE PRINCIPAL                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   SCRAPER   │───▶│   STORAGE   │───▶│  ANALYZER   │───▶│   OUTPUT    │  │
│  │             │    │             │    │             │    │             │  │
│  │ • Facebook   │    │ • SQLite    │    │ • RAG       │    │ • CSV       │  │
│  │ • Comments   │    │ • JSON      │    │ • Few-shot  │    │ • Reports   │  │
│  │ • Posts      │    │ • Export    │    │ • Embeddings│    │ • UI        │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                                           │                       │
│         ▼                                           ▼                       │
│  ┌─────────────┐                            ┌─────────────┐                 │
│  │  DISCOVERY  │◀──────────────────────────│ KNOWLEDGE   │                 │
│  │             │                            │    BASE     │                 │
│  │ • Related   │                            │             │                 │
│  │ • Groups    │                            │ • PDFs      │                 │
│  │ • Similarity│                            │ • ChromaDB  │                 │
│  └─────────────┘                            └─────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
/home/ronin/code/tfm/
├── SPEC.md                           # Este archivo
├── config.yaml                       # Configuración general
├── requirements.txt                  # Dependencias Python
├── pyproject.toml                    # Configuración del proyecto
├── .env.example                      # Variables de entorno ejemplo
│
├── src/                              # Código fuente
│   ├── __init__.py
│   ├── config/                       # Configuración
│   │   ├── __init__.py
│   │   ├── settings.py                # Settings (pydantic)
│   │   ├── spec.py                    # SPEC: Config
│   │   └── test_unit.py              # Tests: Config
│   │
│   ├── scraper/                      # Módulo de extracción
│   │   ├── __init__.py
│   │   ├── models.py                  # Modelos de datos (Pydantic)
│   │   ├── facebook.py                # Scraper de Facebook
│   │   ├── spec.py                    # SPEC: Scraper
│   │   ├── test_unit.py              # Tests unitarios
│   │   └── test_integration.py        # Tests de integración
│   │
│   ├── discovery/                    # Descubrimiento automático
│   │   ├── __init__.py
│   │   ├── page_discovery.py          # Discovery de páginas
│   │   ├── similarity.py              # Búsqueda por similitud
│   │   ├── spec.py                    # SPEC: Discovery
│   │   ├── test_unit.py              # Tests unitarios
│   │   └── test_integration.py        # Tests de integración
│   │
│   ├── knowledge_base/               # Base de conocimiento RAG
│   │   ├── __init__.py
│   │   ├── pdf_processor.py           # Procesamiento de PDFs
│   │   ├── vector_store.py            # ChromaDB
│   │   ├── spec.py                    # SPEC: Knowledge Base
│   │   ├── test_unit.py              # Tests unitarios
│   │   └── test_integration.py        # Tests de integración
│   │
│   ├── analyzer/                     # Clasificación
│   │   ├── __init__.py
│   │   ├── rag_classifier.py          # Clasificador RAG
│   │   ├── embeddings.py              # Embeddings de posts
│   │   ├── violence_types.py          # Taxonomía de violencia
│   │   ├── spec.py                    # SPEC: Analyzer
│   │   ├── test_unit.py              # Tests unitarios
│   │   └── test_integration.py        # Tests de integración
│   │
│   ├── storage/                      # Almacenamiento
│   │   ├── __init__.py
│   │   ├── database.py                # SQLite
│   │   ├── export.py                  # Exportación
│   │   ├── spec.py                    # SPEC: Storage
│   │   ├── test_unit.py              # Tests unitarios
│   │   └── test_integration.py        # Tests de integración
│   │
│   └── pipeline/                     # Pipeline principal
│       ├── __init__.py
│       ├── orchestrator.py            # Orquestación
│       ├── spec.py                    # SPEC: Pipeline
│       ├── test_unit.py              # Tests unitarios
│       └── test_integration.py        # Tests de integración
│
├── tests/                            # Tests generales
│   ├── __init__.py
│   ├── conftest.py                   # Configuración de pytest
│   ├── fixtures/                     # Datos de test
│   │   ├── facebook_pages.json
│   │   ├── posts_sample.json
│   │   └── violence_examples.json
│   └── helpers.py                    # Helpers para tests
│
├── data/                             # Datos (gitignored)
│   ├── facebook/
│   ├── chroma_db/
│   └── analysis/
│
└── docs/                             # Documentación
    └── architecture.md
```

---

## 🔧 Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|-----------|-----------|---------|-----------|
| **Lenguaje** | Python | 3.12+ | Core |
| **Extracción** | ScrapeGraphAI | 1.x | Scraping con LLM |
| **LLM** | Ollama | latest | Modelos locales |
| **Embeddings** | Ollama (nomic-embed-text) | latest | Vectorización |
| **Vector Store** | ChromaDB | 0.5.x | Almacenamiento de embeddings |
| **RAG Framework** | LangChain | 0.3.x | Pipeline RAG |
| **Base de datos** | SQLite | 3.x | Almacenamiento estructurado |
| **UI** | Streamlit | 1.30+ | Interfaz de revisión |
| **Testing** | pytest | 8.x | Tests unitarios e integración |
| **Configuración** | Pydantic + YAML | 2.x | Settings |

---

## 📦 Módulos del Sistema

### 1. `scraper` - Módulo de Extracción

**Responsabilidad:** Extraer posts y comentarios de páginas de Facebook.

**Componentes:**
- `models.py`: Modelos Pydantic para Post, Comment
- `facebook.py`: Scraper usando ScrapeGraphAI

**Specs:**
- [x] Modelo `Post` con campos: id, text, author, date, likes, comments_count, url, page_id
- [x] Modelo `Comment` con campos: id, text, author, date, likes, post_id, parent_id
- [x] Función `scrape_facebook_page(url, max_posts=50)` → List[Post]
- [x] Función `scrape_post_comments(post_url, max_comments=100)` → List[Comment]
- [x] Manejo de errores con logging
- [x] Rate limiting configurado

**Tests:**
- [x] Unitarios: Validación de modelos, parsing de datos
- [x] Integración: Extracción real de página de Facebook

---

### 2. `storage` - Módulo de Almacenamiento

**Responsabilidad:** Persistir datos extraídos y resultados de análisis.

**Componentes:**
- `database.py`: SQLite con SQLAlchemy
- `export.py`: Exportación a CSV/JSON

**Specs:**
- [x] Tabla `posts`: id, text, author, date, likes, comments_count, url, page_id, created_at
- [x] Tabla `comments`: id, text, author, date, likes, post_id, parent_id, created_at
- [x] Tabla `analysis_results`: id, content_type, content_id, tiene_violencia, tipo, severidad, justificacion, created_at
- [x] Tabla `seed_pages`: id, url, name, is_seed, discovered_from, created_at
- [x] Función `save_posts(posts)` → int (cantidad guardada)
- [x] Función `save_comments(comments)` → int
- [x] Función `save_analysis_result(result)` → int
- [x] Función `get_posts(page_id=None)` → List[Post]
- [x] Función `get_comments(post_id)` → List[Comment]
- [x] Función `export_to_csv(output_path)` → bool
- [x] Función `export_to_json(output_path)` → bool

**Tests:**
- [x] Unitarios: CRUD operations, validación de datos
- [x] Integración: Persistencia real en SQLite

---

### 3. `knowledge_base` - Módulo de Base de Conocimiento

**Responsabilidad:** Procesar PDFs de violencia de género y crear vector store.

**Componentes:**
- `pdf_processor.py`: Extracción de texto de PDFs
- `vector_store.py`: ChromaDB setup

**Specs:**
- [x] Función `extract_text_from_pdf(pdf_path)` → str
- [x] Función `chunk_text(text, chunk_size=500, overlap=50)` → List[str]
- [x] Función `ingest_documents(documents_dir)` → int (cantidad de chunks)
- [x] Función `search_relevant_chunks(query, k=5)` → List[dict]
- [x] Función `get_vector_store()` → ChromaDB client
- [x] Metadata por chunk: source, page, type_violencia

**Tests:**
- [x] Unitarios: Extracción de texto, chunking
- [x] Integración: Ingesta real a ChromaDB

---

### 4. `analyzer` - Módulo de Clasificación

**Responsabilidad:** Clasificar posts/comentarios usando RAG y few-shot learning.

**Componentes:**
- `rag_classifier.py`: Clasificador RAG
- `embeddings.py`: Creación de embeddings de posts
- `violence_types.py`: Taxonomía de violencia

**Specs:**
- [x] Enum `ViolenceType`: FISICA, PSICOLOGICA, SEXUAL, ECONOMICA, SIMBOLICA, VICARIA, VERBAL, NINGUNA
- [x] Enum `Severity`: BAJA, MEDIA, ALTA
- [x] Modelo `ClassificationResult`: tiene_violencia, tipo, severidad, justificacion, evidencia
- [x] Función `classify_text(text, context_chunks=None)` → ClassificationResult
- [x] Función `classify_batch(texts, context_chunks=None)` → List[ClassificationResult]
- [x] Función `create_seed_embeddings(posts_with_violence)` → List[Embedding]
- [x] Función `calculate_similarity(text, seed_embeddings)` → float

**Prompt template:**
```
Analizá el siguiente texto y determiná si contiene violencia de género.

TIPO DE ANÁLISIS: Clasificación de violencia de género

TIPOS DE VIOLENCIA:
- FISICA: Agresiones físicas, golpes, heridas
- PSICOLOGICA: Humillaciones, insultos, control, manipulación
- SEXUAL: Abuso sexual, acoso, violación
- ECONOMICA: Control financiero, privación de recursos
- SIMBOLICA: Estereotipos, representaciones degradantes
- VICARIA: Violencia hacia seres queridos
- VERBAL: Amenazas, gritos, lenguaje denigrante

CONTEXTO RELEVANTE (del marco teórico):
{context}

TEXTOS DE EJEMPLO (few-shot):
{ejemplos}

TEXTO A ANALIZAR:
{text}

RESPONDER EN JSON:
{
  "tiene_violencia": true/false,
  "tipo": "tipo de violencia o 'ninguna'",
  "severidad": "baja/media/alta",
  "justificacion": "explicación breve",
  "evidencia": "cita del texto que sustenta la clasificación"
}
```

**Tests:**
- [x] Unitarios: Parsing de respuesta, validación de resultados
- [x] Integración: Clasificación real con Ollama

---

### 5. `discovery` - Módulo de Descubrimiento

**Responsabilidad:** Descubrir automáticamente páginas con violencia de género.

**Componentes:**
- `page_discovery.py`: Búsqueda de páginas relacionadas
- `similarity.py`: Búsqueda por similitud

**Specs:**
- [x] Función `discover_related_pages(page_url)` → List[PageInfo]
- [x] Función `discover_controversial_groups()` → List[GroupInfo]
- [x] Función `get_similarity_score(page_posts, seed_embeddings)` → float
- [x] Función `should_add_as_seed(page_score, threshold=0.7)` → bool
- [x] Función `update_seed_embeddings(new_violence_posts)` → None

**Tests:**
- [x] Unitarios: Cálculo de similitud, umbrales
- [x] Integración: Descubrimiento real

---

### 6. `pipeline` - Módulo de Orquestación

**Responsabilidad:** Orquestar el flujo completo del pipeline.

**Componentes:**
- `orchestrator.py`: Orquestación de módulos

**Specs:**
- [x] Función `run_seed_pipeline(seed_pages)` → PipelineResult
- [x] Función `run_discovery_pipeline()` → PipelineResult
- [x] Función `run_full_pipeline(seed_pages, iterations=3)` → PipelineResult
- [x] Clase `PipelineResult`: pages_processed, posts_found, comments_found, violence_detected, new_pages_discovered

**Tests:**
- [x] Unitarios: Orquestación de componentes
- [x] Integración: Pipeline completo end-to-end

---

## 🔄 Flujo del Pipeline

### Pipeline Principal (Iterativo)

```python
def run_full_pipeline(seed_pages, iterations=3):
    """
    Pipeline iterativo de descubrimiento.
    
    1. Extraer posts y comentarios de páginas semilla
    2. Clasificar con RAG + few-shot
    3. Crear embeddings de posts con violencia
    4. Descubrir páginas relacionadas
    5. Clasificar nuevas páginas
    6. Repetir hasta alcanzar iteraciones o threshold
    """
    
    seed_embeddings = []
    all_discovered_pages = []
    
    for iteration in range(iterations):
        # FASE 1: Extracción
        posts = []
        comments = []
        for page in seed_pages:
            page_posts = scrape_facebook_page(page)
            posts.extend(page_posts)
            
            for post in page_posts:
                page_comments = scrape_post_comments(post.url)
                comments.extend(page_comments)
        
        # FASE 2: Clasificación
        classified = []
        for comment in comments:
            result = classify_with_rag(comment.text, few_shot_examples=seed_examples)
            classified.append((comment, result))
            
            if result.tiene_violencia:
                # Agregar a embeddings semilla
                seed_embeddings.append(embed(comment.text))
        
        # FASE 3: Descubrimiento
        related_pages = []
        for page in seed_pages:
            pages = discover_related_pages(page)
            related_pages.extend(pages)
        
        # FASE 4: Filtrado por similitud
        new_seeds = []
        for page in related_pages:
            posts = scrape_facebook_page(page)
            score = calculate_similarity(posts, seed_embeddings)
            
            if should_add_as_seed(score, threshold=0.7):
                new_seeds.append(page)
        
        # FASE 5: Expansion
        seed_pages.extend(new_seeds)
        all_discovered_pages.extend(new_seeds)
        
        print(f"Iteración {iteration}: {len(new_seeds)} nuevas páginas")
    
    return PipelineResult(
        pages_processed=len(seed_pages),
        posts_found=len(posts),
        comments_found=len(comments),
        violence_detected=count_violence(classified),
        new_pages_discovered=len(all_discovered_pages)
    )
```

---

## 📊 Tipos de Violencia de Género

```python
VIOLENCE_TYPES = {
    "fisica": {
        "description": "Agresiones físicas, golpes, heridas",
        "examples": [
            "golpeó a su esposa",
            "la agarró del cuello",
            "la tiró al piso"
        ]
    },
    "psicologica": {
        "description": "Humillaciones, insultos, control, manipulación",
        "examples": [
            "no sos nadie sin mí",
            "estás loca",
            "me volvés loco"
        ]
    },
    "sexual": {
        "description": "Abuso sexual, acoso, violación",
        "examples": [
            "si no accedés es tu culpa",
            "para eso estás"
        ]
    },
    "economica": {
        "description": "Control financiero, privación de recursos",
        "examples": [
            "no te doy plata",
            "no trabajás, no decis nada"
        ]
    },
    "simbolica": {
        "description": "Estereotipos, representaciones degradantes",
        "examples": [
            "las mujeres solo sirven para",
            "esa es mujer de cocina"
        ]
    },
    "vicaria": {
        "description": "Violencia hacia seres queridos (hijos, mascotas)",
        "examples": [
            "si me dejás les hago daño a los hijos",
            "le pego al perro porque vos no me hacés caso"
        ]
    },
    "verbal": {
        "description": "Amenazas, gritos, lenguaje denigrante",
        "examples": [
            "te voy a matar",
            "sos una zorra",
            "te voy a hacer	callar"
        ]
    }
}
```

---

## 🧪 Estrategia de Testing

### Tests Unitarios
- Validación de modelos Pydantic
- Parsing de respuestas
- Cálculos de similitud
- Chunking de texto
- CRUD de base de datos

### Tests de Integración
- Extracción real de página de Facebook (con mock)
- Ingesta real a ChromaDB
- Clasificación real con Ollama
- Pipeline completo end-to-end

### Fixtures
- Posts de ejemplo en JSON
- Comentarios de ejemplo en JSON
- Páginas de Facebook mock
- Respuestas de LLM mockeadas

---

## ⚙️ Configuración

### config.yaml
```yaml
app:
  name: "TFM - Detección de Violencia de Género"
  version: "1.0.0"
  debug: false

ollama:
  base_url: "http://localhost:11434"
  llm_model: "qwen3.5:9b"
  embedding_model: "nomic-embed-text"

scraper:
  max_posts_per_page: 50
  max_comments_per_post: 100
  delay_between_requests: 2.0
  timeout: 60

analyzer:
  similarity_threshold: 0.7
  context_chunks: 5
  temperature: 0

knowledge_base:
  chunk_size: 500
  chunk_overlap: 50
  collection_name: "violencia_genero"

storage:
  database_path: "data/tfm.db"
  export_dir: "data/exports"

discovery:
  max_iterations: 3
  min_violence_score: 0.7
  batch_size: 10
```

---

## 📈 Métricas de Éxito

| Métrica | Target | Descripción |
|---------|--------|-------------|
| Precisión de clasificación | > 85% | % de posts correctamente clasificados |
| Recall de descubrimiento | > 70% | % de páginas con violencia descubiertas |
| Tiempo de extracción | < 5s/post | Tiempo promedio por post |
| Tiempo de clasificación | < 2s/text | Tiempo promedio por clasificación |

---

## 🔒 Consideraciones Éticas

1. **Solo contenido público**: Extraer solo de páginas/grupos públicos
2. **Anonimización**: Para publicar resultados, anonimizar nombres
3. **Uso académico**: Este sistema es para investigación, no uso comercial
4. **Consentimiento implícito**: Las páginas públicas tienen expectativa de acceso público
5. **Comité de ética**: Consultar con la universidad si es necesario

---

## 📅 Timeline de Implementación

| Fase | Módulo | Días | Entregable |
|------|--------|------|------------|
| 1 | Config + Storage | 2 | Base de datos funcionando |
| 2 | Scraper | 3 | Extracción de posts/comentarios |
| 3 | Knowledge Base | 2 | Vector store con PDFs |
| 4 | Analyzer | 3 | Clasificador RAG |
| 5 | Discovery | 2 | Descubrimiento automático |
| 6 | Pipeline + UI | 3 | Pipeline completo + Streamlit |
| 7 | Testing + Docs | 3 | Tests + documentación |

**Total estimado: 18 días**

---

## ✅ Checklist de Specs

### Módulo Config
- [x] Settings con Pydantic
- [x] Carga desde YAML
- [x] Validación de tipos

### Módulo Scraper
- [x] Modelo Post
- [x] Modelo Comment
- [x] Función scrape_facebook_page
- [x] Función scrape_post_comments
- [x] Manejo de errores
- [x] Rate limiting

### Módulo Storage
- [x] Tablas: posts, comments, analysis_results, seed_pages
- [x] CRUD operations
- [x] Export CSV/JSON

### Módulo Knowledge Base
- [x] Extracción de PDFs
- [x] Chunking de texto
- [x] Ingesta a ChromaDB
- [x] Búsqueda de chunks

### Módulo Analyzer
- [x] Enum ViolenceType
- [x] Enum Severity
- [x] Modelo ClassificationResult
- [x] Función classify_text
- [x] Función classify_batch
- [x] Few-shot prompting
- [x] Embeddings de posts

### Módulo Discovery
- [x] Función discover_related_pages
- [x] Función discover_controversial_groups
- [x] Función calculate_similarity
- [x] Función should_add_as_seed

### Módulo Pipeline
- [x] Función run_seed_pipeline
- [x] Función run_discovery_pipeline
- [x] Función run_full_pipeline
- [x] Modelo PipelineResult

---

*Versión: 1.0.0*
*Última actualización: 2026-06-11*