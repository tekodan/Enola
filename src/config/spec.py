"""SPEC: Configuration Module.

Este módulo define la configuración del sistema usando Pydantic para validación
y YAML para persistencia. Toda la configuración debe pasar por aquí.

## Responsabilidades
- Cargar configuración desde config.yaml
- Validar tipos y rangos de valores
- Proveer valores por defecto sensatos
- Soportar múltiples entornos (dev, prod)

## Modelo de Datos

### AppConfig
Configuración general de la aplicación.
- name: Nombre de la aplicación
- version: Versión semver
- debug: Modo debug
- log_level: Nivel de logging

### OllamaConfig
Configuración de Ollama para LLM y embeddings.
- base_url: URL base del servidor Ollama
- llm_model: Modelo para clasificación
- embedding_model: Modelo para embeddings
- timeout: Timeout en segundos

### ScraperConfig
Configuración del scraper de Facebook.
- max_posts_per_page: Máximo de posts a extraer por página
- max_comments_per_post: Máximo de comentarios por post
- delay_between_requests: Delay en segundos entre requests
- timeout: Timeout general en segundos

### AnalyzerConfig
Configuración del clasificador RAG.
- similarity_threshold: Threshold para similitud de embeddings
- context_chunks: Número de chunks de contexto para RAG
- temperature: Temperatura del LLM (0 = determinístico)
- max_tokens: Máximo de tokens en respuesta
- few_shot_examples: Número de ejemplos para few-shot

### KnowledgeBaseConfig
Configuración de la base de conocimiento.
- chunk_size: Tamaño de chunks en tokens
- chunk_overlap: Overlap entre chunks en tokens
- collection_name: Nombre de la colección en ChromaDB
- persist_directory: Directorio para persistencia de ChromaDB

### StorageConfig
Configuración de almacenamiento.
- database_path: Ruta a la base de datos SQLite
- export_dir: Directorio para exportaciones
- backup_enabled: Habilitar backups automáticos
- backup_interval_hours: Intervalo de backup en horas

### DiscoveryConfig
Configuración del descubrimiento automático.
- max_iterations: Máximo de iteraciones del pipeline
- min_violence_score: Score mínimo para agregar como semilla
- batch_size: Tamaño de batch para procesamiento
- related_pages_limit: Límite de páginas relacionadas
- groups_keywords: Keywords para buscar grupos

### PipelineConfig
Configuración de orquestación del pipeline.
- enable_discovery: Habilitar descubrimiento automático
- enable_backup: Habilitar backups
- checkpoint_interval: Intervalo de checkpoints
- max_parallel_pages: Máximo de páginas en paralelo

## Uso

```python
from src.config import Settings, get_settings

# Cargar desde archivo
settings = Settings.from_yaml("config.yaml")

# Obtener instancia única (cached)
settings = get_settings()

# Acceder a configuración
ollama_url = settings.ollama.base_url
db_url = settings.get_database_url()
```

## Tests
- test_settings_from_yaml: Carga correcta de YAML
- test_settings_defaults: Valores por defecto correctos
- test_settings_validation: Validación de rangos
- test_get_database_url: Generación correcta de URL
- test_get_chroma_dir: Ruta correcta de ChromaDB
"""
