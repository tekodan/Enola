# TFM — Detección de Violencia de Género en Facebook

Sistema académico que scrapea contenido de Facebook (páginas públicas), lo clasifica con un LLM local (Ollama) asistido por RAG sobre un marco teórico en ChromaDB, y persiste los resultados en SQLite.

> **Stack:** Python 3.12 · ScrapeGraphAI · Ollama (LLM local) · ChromaDB · LangChain · SQLAlchemy · Streamlit
>
> **Idioma del proyecto:** prompts, fixtures, taxonomía y UI en castellano argentino (voseo).

---

## Tabla de contenidos

1. [Arquitectura general](#arquitectura-general)
2. [Setup inicial](#setup-inicial)
3. [Quickstart con la CLI `tfm`](#quickstart-con-la-cli-tfm)
4. [Configuración](#configuración)
5. [Pipeline end-to-end](#pipeline-end-to-end)
6. [Scraping](#scraping)
7. [Análisis / clasificación RAG](#análisis--clasificación-rag)
8. [Base de conocimiento (ChromaDB)](#base-de-conocimiento-chromadb)
9. [Reportes y exports](#reportes-y-exports)
10. [UI de Streamlit](#ui-de-streamlit)
11. [CLI de administración (knowledge_base)](#cli-de-administración-knowledge_base)
12. [Programación: API Python](#programación-api-python)
13. [Tests, lint y type-check](#tests-lint-y-type-check)
14. [Glosario de paths y archivos](#glosario-de-paths-y-archivos)
15. [Troubleshooting](#troubleshooting)

---

## Arquitectura general

```
                        ┌──────────────────────────────────────────┐
                        │           data/seed_pages.txt            │
                        └────────────────────┬─────────────────────┘
                                             │ URLs semilla
                                             ▼
   ┌────────────────┐    ┌────────────────────────────────────┐    ┌──────────────┐
   │ ScrapeGraphAI  │───▶│      SQLite  (data/tfm.db)         │◀───│ BatchAnalyzer│
   │  + Playwright  │    │  pages · posts · comments · analysis│    │  + RAG       │
   │  (Facebook)    │    └─────────────────┬──────────────────┘    │  + Ollama    │
   └────────────────┘                      │                       └──────┬───────┘
                                            │                              │
                                            │   retrieve top-k            │ prompt
                                            ▼                              ▼
                                  ┌──────────────────────┐        ┌──────────────────┐
                                  │  ChromaDB            │        │  Ollama          │
                                  │  violencia_genero    │◀───────│  (LLM local)     │
                                  │  120+ chunks         │ context│  gemma4:…        │
                                  │  CATEGORIAS TFM …md  │        │  qwen3.5:9b      │
                                  └──────────────────────┘        └──────────────────┘
```

Cinco componentes:

| Componente | Responsabilidad | Módulo |
|---|---|---|
| **Scraper** | Login Facebook + extracción de posts y comentarios | `src/scraper/` |
| **Storage** | Persistencia jerárquica en SQLite | `src/storage/` |
| **Knowledge base** | Marco teórico en ChromaDB (RAG) | `src/knowledge_base/` |
| **Analyzer** | Clasificador RAG (Ollama + fallback rule-based) | `src/analyzer/` |
| **Pipeline** | Orquestación scraping→clasificación | `src/pipeline/` |
| **UI** | Inspección y carga visual | `src/ui/` |
| **Report** | Reportes de texto/CSV/JSON | `src/report/` |

---

## Setup inicial

### 1. Requisitos

- **Python 3.12**
- **Ollama** corriendo localmente (`http://localhost:11434`) con al menos un modelo LLM descargado
- **Chromium** (lo maneja Playwright; se instala la primera vez)

### 2. Instalación

```bash
# Clonar e instalar
cd /home/ronin/code/tfm
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Instalar Chromium para Playwright (lo usa el scraper)
playwright install chromium

# Descargar el modelo LLM (ejemplo con qwen 3.5 9B)
ollama pull qwen3.5:9b
# o el que esté en config.yaml:
ollama pull gemma4:e2b-it-qat-asst-think-64k
```

### 3. Variables de entorno

```bash
cp .env.example .env
# Editar .env si querés overridear los defaults
```

Valores por defecto (ver `.env.example`):

| Variable | Default | Para qué |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint Ollama |
| `OLLAMA_LLM_MODEL` | `qwen3.5:9b` | Modelo LLM (overridable vía `config.yaml`) |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Modelo de embeddings |
| `DATABASE_PATH` | `data/tfm.db` | Path al SQLite |
| `CHROMA_PERSIST_DIRECTORY` | `data/chroma_db` | Path a ChromaDB |
| `LOG_LEVEL` | `INFO` | Nivel de log |

### 4. Sesión de Facebook (solo para scraping real)

El scraper usa Playwright con sesión persistente para evitar bloqueos. Una vez por máquina:

```bash
source .venv/bin/activate
python scripts/save_facebook_session.py
```

Esto abre un Chromium no-headless, te logueás manualmente, cerrás la ventana, y la sesión queda guardada en `data/facebook_auth.json`. **No commitear este archivo** (contiene cookies).

---

## Quickstart con la CLI `tfm`

Una vez instalado (`pip install -e .`), el proyecto expone una CLI unificada llamada `tfm` que agrupa las 3 operaciones principales: scrapear, analizar y servir la UI. Funciona desde cualquier directorio.

### Panorama

```bash
tfm scrape          # Scrapea + preprocesa páginas seed → SQLite
tfm analyze         # Clasifica con RAG lo no analizado
tfm serve           # Lanza el dashboard de Streamlit (blocking)
tfm status          # Resumen de SQLite + ChromaDB
tfm report          # Reporte textual de los análisis
tfm all             # scrape + analyze en una sola corrida

tfm --help          # Ayuda general
tfm <subcomando> --help   # Ayuda de un subcomando específico
```

### Flujo típico en 3 pasos

```bash
# 1. Ver el estado actual del sistema
tfm status

# 2. Scrapea las páginas seed (URLs en data/seed_pages.txt)
tfm scrape

# 3. Clasifica todo el contenido scrapeado con RAG
tfm analyze

# (Opcional) Re-analiza desde cero con la taxonomía canónica vigente
tfm analyze --reanalyze

# (Opcional) Combiná scrape + analyze en una sola corrida
tfm all
```

### `tfm scrape` — Scraping + preprocesamiento

Scrapea las páginas listadas en `data/seed_pages.txt` (una URL por línea, `#` para comentarios) y guarda la jerarquía `página → posts → comments` en `data/tfm.db`. **No clasifica**, solo extrae.

```bash
tfm scrape                                          # usa data/seed_pages.txt
tfm scrape --seeds otra_lista.txt                   # archivo custom
tfm scrape --max-posts 30 --max-comments 50         # límites custom (0 = config.yaml)
tfm scrape --headful                                # browser visible (debugging)
```

**Output esperado:**

```
Scrapeando 2 página(s) seed:
  • https://facebook.com/pagina1
  • https://facebook.com/pagina2

Config: max_posts=50, max_comments=100, headless=True

==================================================
SCRAPE COMPLETO
==================================================
  Páginas scrapeadas:  2
  Posts encontrados:   45
  Tiempo:              47.3s
==================================================
```

### `tfm analyze` — Clasificación con RAG

Toma todos los posts/comments no analizados de SQLite, los clasifica con el LLM local (Ollama) usando RAG contra ChromaDB, y persiste los resultados en `analysis_results`. Los resultados son **homogéneos** (taxonomía cerrada de 6 categorías `VDG_*` y 19 subdimensiones `N.M`).

```bash
tfm analyze                       # solo lo no analizado
tfm analyze --reanalyze           # re-analiza todo (incluso lo previo)
tfm analyze --posts-only          # ignora comments
tfm analyze --log-level DEBUG     # logs detallados
```

**Output esperado:**

```
Iniciando análisis batch con RAG...
  Re-analizar existentes: False
  Incluir comments:       True

==================================================
ANÁLISIS COMPLETO
==================================================
  Posts analizados:       7
  Comments analizados:    71
  Violencia detectada:    24 (30.8%)
  Errores:                0
  Tiempo:                 12.4s
==================================================
```

### `tfm serve` — Dashboard de Streamlit

Lanza la UI de **Enola Investigadora Digital** (KPIs, gráficos de violencia, inspector de contenido, descarga de la base de conocimiento, página de documentación).

```bash
tfm serve                          # puerto 8501, en foreground (Ctrl+C para detener)
tfm serve --port 9000              # puerto custom
tfm serve --no-browser             # no abre el browser
tfm serve --detach                 # lanza en background, devuelve el PID
tfm serve --detach --port 9000     # combinación común
```

Cuando se usa `--detach`, el proceso queda corriendo y podés hacer otras cosas en la misma terminal:

```bash
$ tfm serve --detach
Lanzando: streamlit run /home/.../src/ui/landing.py --server.port 8501
  -> http://localhost:8501
  PID: 12345 (detach=True, no se espera)
  Para detenerlo: kill 12345
$ tfm status    # mientras la UI corre en otra pestaña
```

### `tfm status` — Health check rápido

Resumen de las dos bases de datos: SQLite (páginas, posts, comments, análisis) y ChromaDB (documentos vectorizados).

```bash
tfm status                  # human-readable
tfm status --json           # para scripts / CI
```

**Output:**

```
==================================================
ESTADO DEL SISTEMA
==================================================
SQLite (data/tfm.db):
  Páginas:        2
  Posts:          7
  Comments:       71
  Análisis:       78

ChromaDB (violencia_genero):
  Documentos:     191
==================================================
```

### `tfm report` — Reporte textual

Similar a `tfm status` pero con foco en la distribución de violencia por categoría. Útil para ver rápidamente qué categorías canónicas están apareciendo en el corpus.

```bash
tfm report                   # human-readable
tfm report --json            # para integrar con otros tools
```

### `tfm all` — Pipeline completo

Encadena `scrape` + `analyze` en una sola corrida. Equivale a correr los dos comandos secuencialmente.

```bash
tfm all                                  # scrape + analyze básico
tfm all --reanalyze                      # + re-analizar lo previo
tfm all --posts-only --headful           # combinaciones válidas
```

### Notas de uso

- **Funciona desde cualquier CWD**: la CLI resuelve rutas absolutas a `data/tfm.db` y `data/chroma_db` usando el path del propio módulo, no el directorio actual.
- **`scrape` no clasifica**: para tener análisis en la DB hace falta correr `analyze` (o `all`) después.
- **`serve --detach` requiere cleanup manual**: usá `kill <PID>` (el comando lo imprime) o `pkill -f "streamlit.*landing.py"`.
- **Ollama debe estar corriendo** (`ollama serve`) para `analyze` y para que la UI pueda clasificar on-demand.

### Aliases / equivalente en `python -m`

Si preferís no instalar el binario `tfm`, todos los comandos tienen un equivalente `python -m`:

```bash
# Equivalencias:
tfm scrape              ==  python -m src.cli scrape
tfm analyze             ==  python -m src.cli analyze
tfm serve               ==  python -m src.cli serve
tfm all                 ==  python -m src.cli all
```

El módulo `src/cli/__main__.py` es donde vive la implementación. Hay 18 tests en `src/cli/test_unit.py` que cubren el parser, los defaults de cada subcomando y los helpers de paths.

---

## Configuración

`config.yaml` en la raíz es la fuente principal de configuración (overridable vía `.env`):

```yaml
ollama:
  base_url: "http://localhost:11434"
  llm_model: "gemma4:e2b-it-qat-asst-think-64k"
  embedding_model: "snowflake-arctic-embed:m"

scraper:
  max_posts_per_page: 50
  max_comments_per_post: 100
  delay_between_requests: 2.0
  headless: true

analyzer:
  context_chunks: 5       # cuántos chunks de ChromaDB pasar al LLM
  temperature: 0          # 0 = determinístico
  few_shot_examples: 5    # (no usado actualmente; ver nota)

knowledge_base:
  chunk_size: 500
  chunk_overlap: 50
  collection_name: "violencia_genero"
  persist_directory: "data/chroma_db"

storage:
  database_path: "data/tfm.db"
  export_dir: "data/exports"
```

> **Nota:** el campo `few_shot_examples` en config está conservado por compatibilidad, pero la lista de ejemplos ahora se pasa al construir el `RAGClassifier` (ver [API Python](#programación-api-python)).

---

## Pipeline end-to-end

El flujo canónico es:

```bash
# 1. Cargar el marco teórico en ChromaDB (una vez por versión del marco)
python -m src.knowledge_base reingest

# 2. Scraping + análisis (lee data/seed_pages.txt)
python -m src.pipeline

# 3. Reporte
python -m src.report report
```

Cada paso puede correrse de forma independiente (ver secciones siguientes).

---

## Scraping

### Sesión de Facebook (precondición)

```bash
source .venv/bin/activate
python scripts/save_facebook_session.py
```

Manual: abrís un browser headful, te logueás, cerrás. Se guarda `data/facebook_auth.json`.

### Páginas semilla

Las URLs a scrapear viven en `data/seed_pages.txt`, una por línea, líneas que empiezan con `#` son comentarios. Ejemplo:

```
# Mentalidad100 (default seed)
https://www.facebook.com/Mentalidad100
```

### Comando

```bash
# Usar el seed file por defecto (data/seed_pages.txt)
python -m src.pipeline

# Usar un seed file custom
python -m src.pipeline /path/to/mis_seeds.txt
```

Output esperado:

```
Ejecutando pipeline con 1 páginas seed:
  • https://www.facebook.com/Mentalidad100
Pipeline completado: éxito=True
Páginas procesadas: 1
Posts encontrados: 12
Violencia detectada: 3
Nuevas páginas descubiertas: 2
```

### Modo mock (sin Facebook)

```bash
# (El módulo src.pipeline_mock existe pero su entry point está roto.
# Para tests sin red, usar pytest src/scraper/ con mocks.)
```

### Detalles técnicos

- **Scraper:** `src/scraper/facebook.py` usa ScrapeGraphAI como extractor LLM con un preprocesador DOM (`src/scraper/facebook_preprocessor.py`) que intenta extracción determinística primero; el LLM es fallback.
- **Persistencia:** el método `Database.save_page_with_posts()` guarda la jerarquía `page → posts → comments` en SQLite, con `ON DELETE CASCADE`.
- **Anti-bloqueo:** delay configurable entre requests (`scraper.delay_between_requests`), user-agent rotativo, sesión persistente.

---

## Análisis / clasificación RAG

### Cómo funciona

1. **Retrieve:** de la DB se levantan posts/comments sin análisis (o todos si se pasa `--reanalyze`).
2. **RAG context:** por cada texto se hace `vector_store.search(texto, n_results=5)` contra ChromaDB. Los top-5 chunks del marco teórico se inyectan al prompt.
3. **LLM call:** se manda el prompt al Ollama local (modelo configurable en `config.yaml`).
4. **Parse:** la respuesta JSON del LLM se valida contra el schema `ClassificationResult`.
5. **Persist:** el resultado se guarda/actualiza en `analysis_results` con UPSERT.

### Prompt (resumido)

El prompt instruye al LLM a usar **exclusivamente** las categorías y sub-dimensiones presentes en los chunks de ChromaDB recuperados. Las únicas constantes hardcodeadas son los niveles de `severity` (`baja` / `media` / `alta` / `ninguna`).

Schema JSON de salida:

```json
{
  "tiene_violencia": true,
  "categoria": "1.4 Amenazas de Agresión Física o Letal",
  "dimension": "1.4.1 Amenazas de Muerte",
  "codigo": "VDG_ODIO_MISOGINO",
  "severidad": "alta",
  "confianza": 0.92,
  "justificacion": "Contiene amenaza de muerte directa",
  "evidencia": "te voy a matar"
}
```

Los campos `categoria`, `dimension` y `codigo` son strings libres que reflejan la taxonomía de ChromaDB. **No** hay un enum hardcodeado para esos campos — el LLM los extrae del contexto.

### Comandos

```bash
# Analizar contenido pendiente en la DB
python -m src.report analyze

# Re-analizar todo (ignora resultados previos)
python -m src.report analyze --reanalyze

# Analizar solo posts (skip comments)
python -m src.report analyze --posts-only
```

Output esperado:

```
RESULTADOS DEL ANÁLISIS
==================================================
  Posts analizados:       12
  Comments analizados:    340
  Violencia en posts:     3
  Violencia en comments:  18
  Errores:                0
  Tiempo:                 42.1s
```

### Fallback rule-based

Si Ollama no responde o se pasa `llm_client=None` al `RAGClassifier`, se usa un clasificador por keywords en `rag_classifier._rule_based_classify()` con buckets: `amenaza_muerte`, `agresion_fisica`, `insulto_sexual`, `amenaza_general`, `sexual_explicito`, `psicologica`, `estereotipo`, `control_economico`, `vicaria`.

---

## Base de conocimiento (ChromaDB)

ChromaDB guarda el marco teórico (categorías y sub-dimensiones de violencia de género digital) en `data/chroma_db/`. La colección por defecto es `violencia_genero`.

**Taxonomía actual:** el marco está compuesto por:
- 1 archivo `CATEGORIAS TFM CONSOLIDADO.md` (120 chunks, ~5 Niveles con sub-dimensiones 1.x, 1.2.x, etc., categorías programáticas VDG_*, perfiles T-140/2021, estrategias de evasión)
- 10 archivos en `knowledge/categorias-violencia-genero-digital/` (190 chunks total: protocolo algorítmico + 6 categorías + glosarios)

### Comandos CLI del módulo `knowledge_base`

```bash
python -m src.knowledge_base --help
```

| Subcomando | Descripción |
|---|---|
| `stats` | Muestra el contador de documentos de la colección |
| `discover-categories` | Descubre la taxonomía usando el LLM (ver [Discovery](#discovery-de-taxonomía)) |
| `reingest` | Re-carga el archivo principal del marco (replace mode por defecto) |
| `add` | Agrega un documento puntual a la colección |
| `add-dir` | Agrega recursivamente todos los `.md`/`.txt` de un directorio |
| `delete-collection` | Borra toda la colección (con confirmación) |

### Cargar documentos (4 formas)

#### 1. Re-cargar el archivo principal del marco (`reingest`)

```bash
# Re-carga CATEGORIAS TFM CONSOLIDADO.md (default, replace mode)
python -m src.knowledge_base reingest

# Re-cargar desde otro path
python -m src.knowledge_base reingest --source /path/to/marco.md

# Clean slate: borra TODA la colección y re-carga solo este archivo
python -m src.knowledge_base reingest --full
```

#### 2. Agregar un documento puntual (`add`)

```bash
# Agregar un nuevo .md o .txt (append; falla si el source ya existe)
python -m src.knowledge_base add --source /path/to/nuevo.md

# Con tags para filtrar después
python -m src.knowledge_base add --source /path/to/nuevo.md --tags "jurisprudencia,2024"

# Sobrescribir si el source ya existe
python -m src.knowledge_base add --source /path/to/nuevo.md --replace
```

> El `source` se toma del nombre de archivo (`basename`), no del path completo. Esto es lo que se usa como filtro `where={"source": "X"}` en queries.

#### 3. Agregar un directorio completo (`add-dir`)

```bash
# Recursivo: procesa todos los .md y .txt bajo el directorio
python -m src.knowledge_base add-dir --source-dir /home/ronin/code/tfm/knowledge

# Con tags
python -m src.knowledge_base add-dir --source-dir /path/ --tags "categoria-X,2024"

# Sobrescribir sources que ya existan
python -m src.knowledge_base add-dir --source-dir /path/ --replace
```

Resumen final del `add-dir`:

```
ADD-DIR COMPLETADO
============================================================
  Archivos procesados:  10
  Chunks agregados:     190
  Chunks reemplazados:  0
  Archivos omitidos:    0
  Antes:                120 documentos
  Después:              310 documentos
```

#### 4. UI de Streamlit (visual, recomendado para inspeccionar)

```bash
streamlit run src/ui/app.py
```

Tabs:
- **Cargar documentos**: file uploader, soporta `.md`/`.txt`/`.pdf`, con `replace mode` (reemplaza chunks del mismo source) y tags libres.
- **Explorar base**: search box, lista de fuentes, muestra aleatoria de chunks.
- **Reportes**: distribución de violencia por categoría, filtros, botón de análisis batch.

### Borrar documentos

```bash
# Borra TODA la colección (con confirmación interactiva)
python -m src.knowledge_base delete-collection

# Sin prompt
python -m src.knowledge_base delete-collection --yes
```

Para borrar chunks de un source específico sin tocar el resto, usar `add --replace` con un archivo vacío, o `add-dir --replace` apuntando a un dir con archivos vacíos. **No hay comando `delete-source`** dedicado todavía.

### Ver el estado

```bash
python -m src.knowledge_base stats
```

```
==================================================
CHROMADB COLLECTION
==================================================
  Nombre:     violencia_genero
  Documentos: 311
==================================================
```

### Discovery de taxonomía

Preguntarle al LLM qué categorías y sub-dimensiones encuentra en la colección:

```bash
# Con LLM (default, requiere Ollama corriendo)
python -m src.knowledge_base discover-categories --n-results 30

# Sin LLM: solo retrieval (muestra los chunks top-k)
python -m src.knowledge_base discover-categories --no-llm --n-results 10

# Diff contra el enum legacy (ya no se usa pero se conserva para auditoría)
python -m src.knowledge_base discover-categories --diff-with-enum

# Query custom
python -m src.knowledge_base discover-categories --query "VCMP violencia política" --n-results 20

# Guardar resultado a JSON
python -m src.knowledge_base discover-categories --out data/taxonomy_discovery.json
```

Output típico:

```
======================================================================
TAXONOMÍA DE VIOLENCIA DE GÉNERO DIGITAL — ChromaDB
======================================================================
Modo: llm
Chunks muestreados: 30 (n_results pedido: 30)
Fuentes en la muestra: CATEGORIAS TFM CONSOLIDADO.md, 04-categoria-4-…

[1.3] Misoginia Virtual Organizada (Manosfera)
    • 1.3.1 — Incels / MGTOW / PUA / ADH
[1.4] Amenazas de Agresión Física o Letal
    • 1.4.1 — Amenazas de Muerte
Categorías programáticas:
  • VDGPOLITICAVCMP — Violencia Política contra la Mujer
  • VDGODIOMISOGINO — Discurso de Odio y Misoginia Explícita
  • VDG_ESTEREOTIPO — Estereotipos, Dominación y Doble Estándar
```

---

## Reportes y exports

### Reporte de texto

```bash
python -m src.report report          # human-readable
python -m src.report report --json   # JSON completo
```

### Análisis batch (re-correr clasificación)

```bash
python -m src.report analyze                  # solo pendientes
python -m src.report analyze --reanalyze      # forzar re-análisis de todo
python -m src.report analyze --posts-only     # skip comments
```

### Exports a CSV / JSON

Programáticamente (no hay CLI, hay que usar Python):

```python
from src.storage import Database, ExportManager, get_database

db = get_database()
exporter = ExportManager(db, export_dir="data/exports")

# CSV con posts, comments y analysis results
path = exporter.export_to_csv()                    # → data/exports/export_YYYYMMDD_HHMMSS.csv

# JSON equivalente
path = exporter.export_to_json()                   # → data/exports/export_YYYYMMDD_HHMMSS.json

# Reporte de violencia agrupado por categoría
path = exporter.export_violence_report()
```

O desde la UI de Streamlit (tab **Reportes**).

---

## UI de Streamlit

```bash
source .venv/bin/activate
streamlit run src/ui/app.py
```

Tabs:

1. **Cargar documentos** — uploader de archivos (`.md`/`.txt`/`.pdf`) con opción de "replace mode" y tags libres.
2. **Explorar base** — búsqueda semántica, lista de fuentes en la colección, muestra aleatoria.
3. **Reportes** — métricas, tabla filtrable de análisis, gráfico de distribución por categoría, botón de análisis batch.

---

## CLI de administración (knowledge_base)

Resumen completo de subcomandos:

```bash
python -m src.knowledge_base stats
python -m src.knowledge_base discover-categories [--no-llm] [--n-results N] [--query "..."] [--out PATH] [--diff-with-enum]
python -m src.knowledge_base reingest [--source PATH] [--full]
python -m src.knowledge_base add --source PATH [--tags "t1,t2"] [--replace]
python -m src.knowledge_base add-dir --source-dir PATH [--tags "t1,t2"] [--replace]
python -m src.knowledge_base delete-collection [--yes]
```

Cualquier subcomando acepta `--log-level DEBUG|INFO|WARNING|ERROR`.

---

## Programación: API Python

### Imports principales

```python
from src import (
    RAGClassifier, ClassificationResult, Severity,
    Settings, get_settings,
    Database, get_database, ExportManager,
    PipelineOrchestrator, run_full_pipeline,
    FacebookScraper, Post, Comment,
)
```

### Clasificar un texto individual

```python
import asyncio
from src.analyzer import RAGClassifier
from src.analyzer.llm_client import OllamaClient
from src.knowledge_base import get_vector_store
from src.config import get_settings

settings = get_settings()
vs = get_vector_store(
    persist_directory=settings.knowledge_base.persist_directory,
    collection_name=settings.knowledge_base.collection_name,
)
llm = OllamaClient(
    base_url=settings.ollama.base_url,
    model=settings.ollama.llm_model,
    temperature=settings.analyzer.temperature,
)
classifier = RAGClassifier(
    llm_client=llm,
    vector_store=vs,
    context_chunks=settings.analyzer.context_chunks,
)

result: ClassificationResult = classifier.classify_sync("te voy a matar")
print(result.categoria, result.severidad, result.confianza)
```

### Cargar un documento a ChromaDB (sin CLI)

```python
from pathlib import Path
from src.knowledge_base import get_vector_store, process_text
from src.config import get_settings

settings = get_settings()
vs = get_vector_store(
    persist_directory=settings.knowledge_base.persist_directory,
    collection_name=settings.knowledge_base.collection_name,
)
vs.create_collection()

content = Path("/path/to/mi_doc.md").read_text(encoding="utf-8")
chunks = process_text(
    content=content,
    source="mi_doc.md",          # este es el 'source' que aparece en metadata
    file_format="md",
    chunk_size=settings.knowledge_base.chunk_size,
    chunk_overlap=settings.knowledge_base.chunk_overlap,
)
vs.add_documents(
    documents=[c["text"] for c in chunks],
    metadatas=[c["metadata"] for c in chunks],
)
```

### Borrar la colección

```python
from src.knowledge_base import get_vector_store
vs = get_vector_store()
vs.delete_collection()
```

### Discovery programático

```python
import asyncio
from src.knowledge_base import get_vector_store
from src.knowledge_base.discovery import discover_categories, diff_with_legacy_enum
from src.analyzer.llm_client import OllamaClient
from src.config import get_settings

settings = get_settings()
vs = get_vector_store()
vs.create_collection()
llm = OllamaClient(base_url=settings.ollama.base_url, model=settings.ollama.llm_model)

result = asyncio.run(
    discover_categories(vector_store=vs, llm_client=llm, n_results=30)
)
print(result["taxonomy"])  # dict con la taxonomía detectada
```

### Ejecutar el pipeline desde Python

```python
from src.pipeline import run_full_pipeline, PipelineOrchestrator
from src.scraper import FacebookScraper

# Modo fácil:
stats = run_full_pipeline(seeds=["https://www.facebook.com/Mentalidad100"])

# Modo custom:
scraper = FacebookScraper(max_posts=20, max_comments=50)
orch = PipelineOrchestrator(scraper=scraper)
result = orch.run_full_pipeline(seeds=["..."])
```

---

## Tests, lint y type-check

```bash
# Activar venv
source .venv/bin/activate

# Suite completa (incluye coverage)
pytest

# Solo un módulo
pytest src/analyzer/
pytest src/knowledge_base/test_unit.py

# Lint (autofix imports + E/F/I/N/W/UP)
ruff check --fix .

# Format
ruff format .

# Type check
mypy src/
```

### Tipos de tests

- **`test_unit.py`**: mocks, sin red ni Ollama. Seguro correr offline.
- **`test_integration.py`**: requiere Ollama corriendo en `localhost:11434`. Marcado con fixtures que asumen el modelo configurado.

Convención: los tests viven **dentro** de cada módulo en `src/<module>/test_*.py`. El root `tests/` solo tiene fixtures compartidos.

---

## Glosario de paths y archivos

| Path | Qué es |
|---|---|
| `config.yaml` | Config principal (overridable vía `.env`) |
| `.env` | Secrets y overrides por environment (no commitear) |
| `data/seed_pages.txt` | URLs semilla para el scraper, una por línea |
| `data/tfm.db` | SQLite con `pages`, `posts`, `comments`, `analysis_results` |
| `data/chroma_db/` | Persistencia de ChromaDB (HNSW index + sqlite) |
| `data/exports/` | Exports CSV/JSON de `ExportManager` |
| `data/facebook_auth.json` | Cookies de Playwright (no commitear) |
| `data/taxonomy.json` | Output opcional de `discover-categories --out` |
| `knowledge/` | Directorio de docs teóricos (markdowns del marco) |
| `scripts/save_facebook_session.py` | Helper para guardar sesión de Facebook |
| `src/pipeline/__main__.py` | CLI: `python -m src.pipeline [seeds_file]` |
| `src/report/__main__.py` | CLI: `python -m src.report {analyze,report}` |
| `src/knowledge_base/__main__.py` | CLI: `python -m src.knowledge_base {stats,discover-categories,reingest,add,add-dir,delete-collection}` |
| `src/ui/app.py` | UI Streamlit: `streamlit run src/ui/app.py` |

---

## Troubleshooting

### `Ollama connection refused`

```bash
# Verificar que Ollama esté corriendo
curl http://localhost:11434/api/tags

# Si no responde, iniciarlo
ollama serve
```

### `Collection violencia_genero is empty`

```bash
# Cargá el marco teórico
python -m src.knowledge_base reingest
```

### `El LLM invierte la estructura del JSON`

El modelo local a veces agrega fences markdown al JSON. El parser `ClassificationResult.from_llm_response()` ya los strippea, pero si tu modelo produce algo muy raro, bajale la `temperature` a 0 (ya está en 0 por default) o probá con otro modelo más grande.

### `ModuleNotFoundError: No module named 'pdfplumber'`

```bash
pip install -e ".[dev]"
# o específicamente:
pip install pdfplumber PyPDF2
```

### `TypeError: 'tipo' is an invalid keyword argument for AnalysisResultModel`

El schema de la DB cambió (se eliminó el campo legacy `tipo` y se agregaron `categoria`/`dimension`/`codigo`/`confianza`). Si tenés una DB vieja en `data/tfm.db`, **borrarla** y empezar de cero:

```bash
rm data/tfm.db
# Re-scrapear y re-analizar
```

### `sqlite3.OperationalError: no such column: analysis_results.categoria`

Tu DB existe pero quedó con un schema anterior (solo `tipo`/`confidence`). El proyecto ahora incluye una **migración automática** en `Database.__init__()` que:

1. Detecta las columnas faltantes (`categoria`/`dimension`/`codigo`/`confianza`)
2. Las agrega con `ALTER TABLE ADD COLUMN`
3. Copia los datos de `tipo` → `categoria` y `confidence` → `confianza`
4. Droppea las columnas viejas (en SQLite ≥ 3.35)

La migración se aplica sola la próxima vez que instancies `Database` (típicamente al correr `python -m src.report analyze`). **No hace falta borrar `data/tfm.db`**.

Si la migración automática no aplica (por permisos, schema corrupto, etc.), el workaround manual sigue siendo:

```bash
rm data/tfm.db
# Re-scrapear y re-analizar
```

### Tests fallan por imports de `ViolenceType` o `VIOLENCE_TYPES`

Esos nombres fueron removidos en la migración a taxonomía ChromaDB-driven. Si tenés código externo que los importa, actualizar a:

```python
# antes:
from src.analyzer import ViolenceType, VIOLENCE_TYPES
# ahora:
from src.analyzer import Severity  # único enum que queda
```

### Quiero borrar un source específico de ChromaDB sin tocar el resto

No hay subcomando dedicado. Workaround:

```bash
# 1. Re-cargar el archivo vacío / stub de ese source
echo "" > /tmp/empty.md
python -m src.knowledge_base add --source /tmp/empty.md --replace
# Esto deja el source con 1 chunk vacío, pero ya no contamina retrieval.
# Si querés borrarlo del todo, hay que ir a sqlite:
python3 -c "
import sqlite3
conn = sqlite3.connect('data/chroma_db/chroma.sqlite3')
cur = conn.cursor()
cur.execute(\"\"\"
    DELETE FROM embeddings WHERE id IN (
        SELECT em.id FROM embedding_metadata em
        WHERE em.key='source' AND em.string_value='mi_archivo.md'
    )
\"\"\")
cur.execute(\"DELETE FROM embedding_metadata WHERE key='source' AND string_value='mi_archivo.md'\")
conn.commit()
print('OK')
"
```

(Si esto se vuelve un caso común, se puede agregar un subcomando `delete-source` en el futuro.)

---

## Licencia

MIT — ver header en `pyproject.toml`.

## Autor

Investigador — `investigador@example.com`
