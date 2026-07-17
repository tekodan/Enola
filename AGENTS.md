# AGENTS.md

## Project Overview

Python 3.12 academic research project: detects gender-based violence in Facebook content using RAG.
Stack: ScrapeGraphAI + Ollama (local LLM) + ChromaDB + LangChain + Streamlit.
No git repo, no CI, no Docker.

## Developer Commands

```bash
# Virtual environment
source .venv/bin/activate

# Install
pip install -e ".[dev]"

# Lint + auto-fix imports
ruff check --fix .
# Format (black-compatible)
ruff format .
# Type check
mypy src/

# Run all tests (includes coverage — addopts configured in pyproject.toml)
pytest

# Single module or file
pytest src/analyzer/
pytest src/analyzer/test_unit.py

# Clean text of already-persisted posts / comments (dry-run by default)
python scripts/clean_texts.py --dry-run      # preview only
python scripts/clean_texts.py --target all --apply  # write changes
python scripts/clean_texts.py --db-path data/otra.db --target comments --apply
```

## Test Layout

Tests live **inside each `src/<module>/`** directory:
- `src/config/test_unit.py` — unit tests
- `src/config/test_integration.py` — integration tests (require Ollama running)

Root `tests/` directory only contains shared fixtures:
- `conftest.py` — pytest fixtures
- `helpers.py` — test utilities
- `fixtures/*.json` — test data

pytest discovers from both `tests/` and `src/` (`testpaths = ["tests", "src"]`).
`asyncio_mode = auto` in pyproject.toml — async test functions work without decorator.

## Module Structure

Each module follows this pattern:
- `spec.py` — design contract (read before modifying)
- `test_unit.py` — unit tests (no external deps)
- `test_integration.py` — integration tests (Ollama at localhost:11434 required)

Public API re-exported from `src/__init__.py` — import from `src` directly.

## Import Convention

Always use `src.` prefix:

```python
from src.config import Settings, get_settings
from src.analyzer import RAGClassifier, ClassificationResult
```

## Config

- `config.yaml` at project root — main configuration source
- Loaded via `Settings.from_yaml()` (Pydantic models in `src/config/settings.py`)
- Copy `.env.example` to `.env` to override defaults
- Ollama: `http://localhost:11434`, LLM `qwen3.5:9b`, embedding `nomic-embed-text`

## Gotchas

- **Spanish domain**: All prompts, fixtures, taxonomy, and UI content are in Argentine Spanish.
- **Ollama dependency**: Integration tests require `ollama serve` running locally. Unit tests mock the LLM client — safe to run without Ollama.
- **Data directory**: `data/` contains runtime artifacts (ChromaDB, SQLite, exports). Not a git repo — no `.gitignore`.
- **Line length**: 100 chars (ruff, black, isort). Target Python: 3.12.
- **pytest addopts**: `-v --tb=short --cov=src --cov-report=term-missing` — coverage runs automatically.
- **ruff select**: `["E", "F", "I", "N", "W", "UP"]` — import sorting (`I`) included in lint step.
- **Pinned deps**: `passlib>=1.7.4,<2.0` + `bcrypt>=4.0.0,<4.1`. Newer `bcrypt 5.x` is incompatible with `passlib 1.7.4` (see `pyproject.toml`).

## Human-in-the-loop feedback

The validation UI lives in the **NiceGUI dashboard** at `/validacion`
(`src/ui/nicegui_app/pages/validacion.py`). The legacy Streamlit tab
in `app.py` is **deprecated** and now shows a redirect banner unless
`ENOLA_SHOW_DEPRECATED_TAB=true`.

### Login & roles

- **`users` table** in SQLite (`src/storage/models/user.py`) — bcrypt
  password hashes via `passlib`. Roles: `admin` (puede crear/bloquear
  usuarios vía CLI) y `reviewer` (sólo valida).
- **Sesión**: `app.storage.user["current"]`, sólo navegador (sin
  cookie persistente). Close la pestaña → logout automático.
- **Bootstrap admin**: lee `ENOLA_ADMIN_USERNAME` + `ENOLA_ADMIN_PASSWORD`
  del entorno en `__main__.py`. Idempotente.
- **CLI**: `python -m src.cli users add|list|set-active|set-role|set-password`
  para gestión. Si no pasás `--password`, lo pide por stdin (oculto) o
  genera uno aleatorio y lo imprime una sola vez.
- **CLI categorías**: `python -m src.cli categories list|edit|edit-subdim|refresh-cache`
  para editar títulos y descripciones de categorías/subdimensiones sin reiniciar server.
  Los títulos se resuelven desde SQLite (overrides) + `TAXONOMIA.md` (defaults).

### Reviews flow

The validation page lets a reviewer agree or disagree with each RAG
analysis. The corrections flow through two stores:

- **SQLite** (`analysis_feedback` table) — single source of truth for
  the reviewer's verdict, free-text reason and override fields. The
  row carries `reviewer_user_id` (FK to `users.id`) and
  `reviewer_username` (denormalized for quick listing). Upsert by
  `analysis_result_id`.
- **ChromaDB** (`feedback_corrections` collection) — only the
  *disagreements with corrections* are pushed here. Each doc carries
  metadata `user_id`, `added_by_username`, `added_at` for full
  traceability. `RAGClassifier` retrieves the top-3 relevant
  corrections per call and injects them into the prompt as
  `[VALIDADO POR HUMANO]` few-shots, so the LLM re-trains implicitly on
  each batch run.

### Validación UI (`/validacion`)

- **KPIs header**: pendientes, total revisiones, acuerdo, corregidas,
  indexadas en ChromaDB.
- **Panel ChromaDB** (expander): botón "🚀 Indexar pendientes".
- **Filtros**: tipo (post/comment/all), estado (todos/pendientes/
  acuerdo/corregidos), sólo violentos.
- **Formulario multi-etiqueta** (hasta `MAX_LABELS = 5`):
  categoria / dimensión / severidad / FPP / justificación / evidencia.
  Validación cruzada: cada `(categoria, dimension)` debe ser válido.
- **Dos CTAs**: `💾 Guardar` (SQLite sólo) y
  `💾+🔎 Guardar e indexar` (SQLite + ChromaDB con metadata user).
- **Auditoría**: cada feedback lleva `reviewer_user_id` +
  `reviewer_username`. La metadata de ChromaDB incluye
  `added_by_username`.

The **landing** page (`src/ui/landing.py` / NiceGUI `/inicio`) shows
the *adjusted* report: KPIs and charts are computed from
`build_adjusted_analysis(...)` which overlays the latest feedback on
top of the raw `analysis_results`. The legacy Streamlit "Reportes"
tab keeps the raw view for debugging and exports a CSV/JSON of all
reviewed rows.

## Multi-label classification (multi-categoría)

A single analyzed post/comment can carry **up to 5 labels** (each a
`LabelAssignment` with its own categoria, sub-dimension, severidad,
justificación, evidencia, marcadores, etc.). The architecture is:

- **LLM output** (`RAGClassifier`): the prompt asks the LLM to return a
  `clasificaciones: [...]` array (1..5 entries, deduped by
  `(categoria, dimension)`). The legacy single-label JSON
  (`categoria`/`dimension`/`justificacion`) is still accepted and
  auto-wrapped into a 1-element list.
- **Persistence** (`src/storage/database.py`): each analysis row
  continues to live in `analysis_results`, but the full label list is
  stored in the side table `analysis_labels` (one row per label,
  FK CASCADE). The flat `analysis_results` columns
  (`categoria`/`dimension`/`severidad`/`justificacion`/`evidencia`/...)
  are populated with the **primary** label (highest severity; ties
  broken by `orden`) so single-column queries and KPIs keep working.
- **Feedback**: same pattern — `analysis_feedback_labels` side table
  carries the reviewer's overrides; flat `corrected_*` columns mirror
  the primary override.
- **UI**: validation tab (`/validacion` in NiceGUI) renders a dynamic list of
  per-label rows (categoria, dimensión, severidad, justificación,
  evidencia, FPP), with `+ Agregar etiqueta` / `➖ Quitar` buttons
  capped at `MAX_LABELS = 5`. The Inspector (`landing.py`) and
  Reports tab display the full label list with per-label
  justifications.
- **KPIs / charts** (`src/ui/utils.py`): `compute_bar_data` and
  `compute_kpis` iterate `r["labels"]` instead of the single
  `categoria`, so a multi-label content contributes one vote per
  category. `compute_label_distribution` provides a drill-down
  view of the (categoria, dimension) pairs.
- **Backfill**: the migration creates the new side tables but does
  **not** backfill existing analyses. Run
  `python -m src.report analyze --reanalyze` to repopulate with the
  multi-label schema.
- **Cap**: ``MAX_LABELS = 5`` in `src/analyzer/category_mapping.py`.
  The LLM is told to return at most this many labels; the rule-based
  fallback sorts by severity and keeps the top-5.

## Exclusion label & methodological rules (basura digital / violencia común / estadística)

The system implements the methodology documented in the
``INSTRUCCIÓN DE SISTEMA: FILTRO DE EXCLUSIÓN PREVIA`` and the six
``REGLA N DEFINITIVA`` blocks (Reglas 1-6) plus the ``REGLA DE EXCLUSIÓN
DE VIOLENCIA COMÚN``.

- **Pre-filter (``src/analyzer/exclusion_filter.py``)** — runs FIRST in
  `RAGClassifier.classify()`, before the LLM and ChromaDB lookups. Detects
  basura digital (CÓDIGO 99) under **five** conditions: **(1)** empty/NaN
  payload (incl. stickers/GIFs/imágenes sin texto), **(2)** orphan
  hyperlink, **(3)** typographic noise (punctuation/emojis/repeated
  chars with no lexical structure), **(4)** pure laughter
  (``jajaja``/``jeje``/``haha``/``rsrs``/``lol``/``xd`` —
  ``COND_4_SOLO_RISA``), **(5)** short reactions, muletillas o
  monosílabos sueltos (``ok``/``si``/``no``/``ya``/``dale``/``je``/
  ``ah``/``se``/``pues``/``que``/``qué``/``quiza``/``tal``/``como``/
  ``donde``/``cuando``/``también``/``tampoco``/``vale``/``venga``/
  ``ahí``/``aquí``/``allá``/``acá``/``a ver``/``q``/``k`` —
  ``COND_5_REACCION_CORTA``). Patterns for COND_4/COND_5 are loaded
  from
  ``knowledge/categorias-violencia-genero-digital/glosario/patrones-basura-digital.md``
  via ``_load_basura_digital_patterns()`` (same design as the gender
  /aggression glosarios). The violencia-común heuristic is exposed
  for the rule-based fallback path but the primary discrimination
  lives in the LLM prompt (instructions block at the start of
  `classify()`).
- **Exclusión documentada en la taxonomía** — Las pseudo-categorías
  pre-clasificatorias (``EXC_BASURA_DIGITAL``, ``EXC_VIOLENCIA_COMUN``)
  viven ahora en una sección aparte ``categorias_exclusion`` del
  frontmatter de ``knowledge/taxonomia/TAXONOMIA.md`` (no cuentan
  para el invariante de 6 categorías operativas). ``Taxonomy.exclusion_codes()``
  devuelve el mapeo ``EXC_*`` → ``CODIGO_*`` y
  ``canonical_exclusion_labels()`` el ``frozenset`` de códigos. El
  modelo Pydantic es ``src.analyzer.taxonomy_loader.ExclusionCategoriaMD``.
- **Schema** — `analysis_results` gained three columns via
  `database.py:_migrate_schema()`: `exclusion_label` (`CODIGO_99` |
  `VIOLENCIA_COMUN` | NULL), `exclusion_codigo` (e.g. `COND_2_ENLACE_HUERFANO`),
  `exclusion_justificacion`. Rows with these labels are NOT deleted —
  they participate in the missing-values report (Regla 1) and are
  excluded from the violence-incidence denominators (Reglas 2-4).
- **Regla 1 — Valores perdidos** (``src/report/reliability.py``):
  `calcular_valores_perdidos()` returns a `ReliabilityReport` with
  `n_basura_digital`, `pct_basura`, `nivel` (`ok` < 5% / `preventiva`
  5-10% / `critica` > 10%) and the exact wording mandated by the spec.
  Surfaced as a banner with color-coded alert in
  `landing.py:render_reliability_banner()`.
- **Regla 2 — Distribución de frecuencias** (``src/report/stats.py``):
  `compute_frequency_distribution()` returns a `FrequencyTable` with
  EXACTLY 4 columns — Categoría / Frecuencia Absoluta / Porcentaje
  Válido / Porcentaje Acumulado. Porcentaje válido excludes CÓDIGO 99
  and VIOLENCIA_COMUN. Porcentaje acumulado is a cumsum in descending
  order that reaches 100% at the last row.
- **Regla 3 — Moda** (``src/report/stats.py:compute_mode``): returns
  the unique mode OR detects bimodal/multimodal distributions when two
  or more categories share the maximum frequency. Emits the descriptive
  text required by the spec (Paso 3.4).
- **Regla 4 — Análisis bivariado** (``src/report/stats.py:compute_crosstabs``):
  contingency tables crossing `categoria` against `subdimension` /
  `pagina` / `fecha`. Computes observed frequencies and column-marginal
  percentages (Paso 4.3) and emits the descriptive alert (Paso 4.4).
- **Regla 5 — Dashboard** (``src/ui/landing.py``): pie chart
  (Regla 5.2) + bar chart sorted descending (Regla 5.3) +
  frequency-table rendered BELOW the charts per Regla 5.4.
- **Regla 6 — Métricas de IA** (``src/report/metrics.py``):
  `compute_confusion_matrix()` produces VP/VN/FP/FN;
  `compute_reliability_metrics()` uses sklearn to compute Precisión,
  Sensibilidad (Recall) and F1-Score; `render_metrics_report()` emits
  the full report. Ground truth comes from `analysis_feedback` rows —
  `agrees="true"` rows are TP/TN; `agrees="false"` rows use the
  reviewer's `corrected_categoria` override.
