"""SPEC: Scraper Module.

Este módulo se encarga de la extracción de posts y comentarios de Facebook
usando una estrategia híbrida: DOM-based extraction + LLM fallback.

## Responsabilidades
- Extraer posts de páginas de Facebook
- Extraer comentarios de posts
- Descubrir páginas relacionadas
- Manejar errores, rate limiting, login walls y captchas
- Persistir datos extraídos
- Cachear HTML para evitar rescrapeos repetidos

## Modelo de Datos

### Post
Modelo que representa un post de Facebook.
- id: Identificador único (hash del URL + contenido)
- text: Contenido textual del post
- author: Nombre del autor/página
- date: Fecha de publicación
- likes: Cantidad de likes
- comments_count: Cantidad de comentarios
- shares: Cantidad de shares
- url: URL completo al post
- page_id: ID de la página que publicó
- source: Tipo de fuente (page, group, post)
- reactions: Diccionario de reacciones por tipo
- media_urls: URLs de medios en el post

### Comment
Modelo que representa un comentario de Facebook.
- id: Identificador único
- text: Contenido textual del comentario
- author: Nombre del comentarista
- date: Fecha de publicación
- likes: Cantidad de likes
- post_id: ID del post padre
- parent_id: ID del comentario padre (para replies)
- url: URL completo al comentario

### PageInfo
Modelo que representa información de una página.
- id: Identificador único
- name: Nombre de la página
- url: URL a la página
- likes: Cantidad de likes
- description: Descripción de la página
- category: Categoría de la página

### GroupInfo
Modelo que representa información de un grupo.
- id: Identificador único
- name: Nombre del grupo
- url: URL al grupo
- members: Cantidad de miembros
- description: Descripción del grupo
- privacy: Configuración de privacidad

### ScrapeResult
Resultado de una operación de scraping.
- success: Si el scraping fue exitoso
- posts: Lista de posts extraídos
- comments: Lista de comentarios extraídos
- pages: Lista de páginas descubiertas
- errors: Lista de mensajes de error
- pages_scraped: Cantidad de páginas raspadas
- posts_found: Cantidad de posts encontrados
- comments_found: Cantidad de comentarios encontrados
- requires_auth: True si Facebook pidió login
- has_captcha: True si apareció captcha/security check

## Arquitectura de Estrategias

El scraper usa el patrón Strategy para extracción:

```python
from src.scraper import FacebookScraper
from src.scraper.strategies import DOMExtractionStrategy

scraper = FacebookScraper(strategy=DOMExtractionStrategy())
```

Estrategias disponibles:
- `DOMExtractionStrategy`: Extracción DOM-based con BeautifulSoup (rápida, sin LLM)
- `LLMExtractionStrategy`: Extracción vía LLM (placeholder, delega a DOM por ahora)

## API Pública

### FacebookScraper
Clase principal para el scraping de Facebook.

```python
from src.scraper import FacebookScraper, Post, Comment

scraper = FacebookScraper()

# Extraer posts de una página
posts = await scraper.scrape_page("https://facebook.com/page-name")

# Extraer comentarios de un post
comments = await scraper.scrape_comments(post.url, max_comments=100)

# Extraer todo (posts + comentarios)
result = await scraper.scrape_full("https://facebook.com/page-name")

# Modo interactivo (abre modales de comentarios en vivo)
posts = await scraper.scrape_page_interactive("https://facebook.com/page-name")
```

## Configuración

El scraper usa la configuración de config.yaml:
- scraper.max_posts_per_page: Máximo de posts por página
- scraper.max_comments_per_post: Máximo de comentarios por post
- scraper.delay_between_requests: Delay entre requests
- scraper.timeout: Timeout general
- scraper.headless: Modo headless del browser
- scraper.use_interactive: Usar extracción interactiva de comentarios

## Dependencias
- ScrapeGraphAI: Motor de scraping con LLM (fallback)
- Playwright: Navegación y extracción interactiva
- BeautifulSoup4: Preprocesamiento DOM
- Pydantic: Validación de modelos

## Consideraciones
- Solo contenido público (páginas/grupos públicos)
- Rate limiting con user-agent rotation
- Cache de HTML con TTL (default 24h)
- Detección de login wall y captcha
- Retry con backoff en interacciones de modales
- Logging de errores
- Manejo de páginas con contenido dinámico

## Tests
- test_unit.py — Tests de modelos Pydantic
- test_integration.py — Tests de serialización y fixtures
- test_preprocessor.py — Tests del FacebookPreprocessor
- test_scraper_preprocessing.py — Tests del flujo scraper + preprocessor
- test_interactor.py — Tests del CommentInteractor

## Estructura de archivos
- `facebook.py` — Scraper principal
- `facebook_preprocessor.py` — Preprocesador DOM
- `comment_interactor.py` — Interacción con modales de comentarios
- `models.py` — Modelos Pydantic
- `strategies.py` — Estrategias de extracción (Strategy pattern)
- `mock_facebook.py` — Mock para testing sin Facebook
"""
