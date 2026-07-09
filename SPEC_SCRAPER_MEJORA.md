# SPEC: Mejora del Módulo Scraper

> Fecha: 2026-07-02
> Estado: En progreso — Fase 1
> Autor: OpenCode

---

## Contexto

El módulo `src/scraper/` extrae posts y comentarios de Facebook usando una estrategia híbrida:
1. **DOM-based extraction** (`FacebookPreprocessor`) con BeautifulSoup
2. **LLM fallback** (`SmartScraperGraph` + Ollama) si el DOM falla
3. **Interactive extraction** (`CommentInteractor` con Playwright) para comentarios en modales

El scraper funciona conceptualmente, pero tiene bugs críticos que causan pérdida de datos, tests con mocks incorrectos, y una arquitectura frágil ante cambios de selectores de Facebook.

---

## Problemas diagnosticados

### Críticos (pérdida de datos)
1. **Método duplicado** `find_comment_button` en `CommentInteractor` — sobrescrita silenciosa.
2. **Todos los comentarios asignados al primer post** — posts 2..N pierden sus comentarios.
3. **IDs de posts colisionan** — `_generate_post_id` usa `url+author+date`, pero el preprocessor genera URLs placeholder (`#post_{idx}`) y muchas fechas quedan vacías.
4. **Regex anti-scraping destruye texto español legítimo** — `(?:\s+[a-zA-Z0-9]\s*){5,}` borra secuencias como "a e i o u".

### De calidad
5. **Tests en raíz del proyecto** (`test_preprocessor.py`, `test_scraper_preprocessing.py`) violan la convención `AGENTS.md` (tests deben vivir en `src/<module>/`).
6. **Mocks incorrectos** en `test_scraper_preprocessing.py` — mockea `ChromiumLoader` que el scraper real nunca usa (usa Playwright directo).
7. **Múltiples parses de BeautifulSoup** — cada método de `FacebookPreprocessor` crea un `BeautifulSoup` nuevo.

### De robustez
8. **Sin detección de login wall / captcha** — si Facebook devuelve "Iniciar sesión", el scraper devuelve lista vacía sin avisar.
9. **Sin retry ni backoff** en interacciones de modales.
10. **User-agent fijo** — fácil de fingerprintear.
11. **Sin cache de HTML** — rescrapea la misma página cada vez.

---

## Plan de mejora

### Fase 1: Hotfixes críticos (1-2 días)

| # | Tarea | Archivo(s) | Criterio de aceptación |
|---|-------|------------|------------------------|
| 1.1 | Eliminar duplicado `find_comment_button` | `comment_interactor.py` | Solo 1 definición del método |
| 1.2 | Asignar comentarios por proximidad DOM | `facebook_preprocessor.py`, `facebook.py` | Cada comentario va al post más cercano arriba en el árbol DOM; no todos al primero |
| 1.3 | IDs únicos con hash de texto | `facebook.py` | `hashlib.md5(f"{url}_{idx}_{text[:50]}")` — sin colisiones entre posts de misma página |
| 1.4 | Mover tests a `src/scraper/` | `test_preprocessor.py` → `src/scraper/test_preprocessor.py` | Tests en ubicación correcta según convención del proyecto |
| 1.5 | Corregir regex anti-scraping | `facebook_preprocessor.py` | No borra texto español legítimo en tests de muestra |

**Milestone 1**: `pytest src/scraper/` pasa. No hay métodos duplicados. Comentarios asignados correctamente.

---

### Fase 2: Fortalecer extracción DOM (2-3 días)

| # | Tarea | Archivo(s) | Criterio de aceptación |
|---|-------|------------|------------------------|
| 2.1 | Centralizar selectores en `FACEBOOK_SELECTORS` | `facebook_preprocessor.py`, `config.yaml` | Un solo diccionario/config con todos los selectores |
| 2.2 | Parsear BeautifulSoup una sola vez | `facebook_preprocessor.py` | Métodos internos reciben `soup: BeautifulSoup` en vez de `html: str` |
| 2.3 | Más estrategias de detección de posts | `facebook_preprocessor.py` | Detecta posts por `role="article"`, `[data-pagelet]`, `[role="feed"]` además de aria-labels |
| 2.4 | Scroll adaptativo por `scrollHeight` | `facebook.py` | Detecta fin de feed cuando `scrollHeight` no cambia tras 2 scrolls consecutivos |
| 2.5 | Tests con HTML reales de muestra | `src/scraper/test_preprocessor.py` | Extrae posts de `facebook_html_sample.txt` y `mentalidad100.html` |

**Milestone 2**: El preprocessor extrae posts de al menos 2 de los 3 HTMLs de muestra existentes en el repo.

---

### Fase 3: Interactor robusto + manejo de errores (2-3 días)

| # | Tarea | Archivo(s) | Criterio de aceptación |
|---|-------|------------|------------------------|
| 3.1 | Retry con backoff en clicks | `comment_interactor.py` | Máx 3 intentos con sleep exponencial (1s, 2s, 4s) |
| 3.2 | Detectar login wall | `facebook.py` | Si HTML contiene "Iniciar sesión" o "log in", `ScrapeResult` devuelve `requires_auth=True` |
| 3.3 | Detectar captcha | `facebook.py` | Si HTML contiene `[name="captcha"]` o "Seguridad", aborta graceful |
| 3.4 | Tests del interactor con mocks | `src/scraper/test_interactor.py` | Mockea Playwright page y testea `expand_and_extract` |
| 3.5 | Flag `use_interactive` en config | `config.yaml`, `facebook.py` | Permite desactivar interactor y usar solo extracción DOM |

**Milestone 3**: `pytest src/scraper/` pasa incluyendo tests del interactor. Login wall detectado y reportado.

---

### Fase 4: Arquitectura extensible (3-5 días)

| # | Tarea | Archivo(s) | Criterio de aceptación |
|---|-------|------------|------------------------|
| 4.1 | Clase abstracta `ExtractionStrategy` | `src/scraper/strategies/` | `DOMExtractionStrategy`, `LLMExtractionStrategy` implementan la misma interfaz |
| 4.2 | Refactorizar `FacebookScraper` con strategies | `facebook.py` | Constructor recibe `strategy: ExtractionStrategy` |
| 4.3 | Cache de HTML con TTL | `facebook.py`, `config.yaml` | Guarda HTML en `data/cache/` con TTL configurable (default 24h) |
| 4.4 | Rotación de user-agents | `config.yaml`, `facebook.py` | Lista de 5-10 agents, rota por request |
| 4.5 | Actualizar `spec.py` | `src/scraper/spec.py` | Documenta nueva arquitectura y config |

**Milestone 4**: Se puede instanciar `FacebookScraper(strategy="dom")` o `FacebookScraper(strategy="llm")`. Cache funcional.

---

## Decisiones registradas

| Fecha | Decisión | Justificación |
|-------|----------|---------------|
| 2026-07-02 | Empezar por Fase 1 (hotfixes) | Bugs críticos causan pérdida de datos; arreglarlos primero permite validar mejoras posteriores sobre una base sólida |
| 2026-07-02 | Mantener español argentino en prompts y logs | Convención del proyecto (`AGENTS.md`: *Spanish domain*) |
| 2026-07-02 | No cambiar `ScrapeGraphAI` ni `Playwright` por ahora | Stack ya definido en `AGENTS.md`; mejoras son sobre uso de estas herramientas, no reemplazo |

---

## Métricas de éxito

- **Coverage del scraper**: actualmente ~30% (solo modelos). Target post-mejora: >70%.
- **Tasa de extracción de posts en HTML de muestra**: target >80% de posts visibles extraídos.
- **Tasa de asignación correcta de comentarios**: target >90%.
- **Tiempo de scrape por página**: no debe aumentar >20% con las mejoras.

---

## Notas

- Todos los cambios deben pasar `ruff check --fix . && ruff format . && pytest`.
- Target Python: 3.12. Line length: 100 chars.
- Import convention: `from src.scraper import ...`

