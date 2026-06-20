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
