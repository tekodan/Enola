"""SPEC: Discovery Module.

Este módulo se encarga del descubrimiento automático de páginas
con contenido similar a las páginas semilla.

## Responsabilidades
- Descubrir páginas relacionadas a partir de semillas
- Buscar grupos públicos polémicos
- Calcular similitud entre contenido
- Determinar qué páginas agregar como nuevas semillas

## Modelo de Datos

### RelatedPage
Modelo para páginas descubiertas.
- id: Identificador único
- name: Nombre de la página
- url: URL a la página
- likes: Cantidad de likes
- similarity_score: Score de similitud (0-1)
- discovered_from: URL de donde se descubrió
- category: Categoría de la página

### ControversialGroup
Modelo para grupos controvertidos.
- id: Identificador único
- name: Nombre del grupo
- url: URL al grupo
- members: Cantidad de miembros
- keywords_matched: Keywords que coincidieron
- privacy: Configuración de privacidad

### SimilarityEngine
Motor para calcular similitud entre contenidos.
- Usa embeddings para representación semántica
- Fallback con word overlap si no hay embeddings
- Support para batch processing

## API Pública

### PageDiscovery
```python
from src.discovery import PageDiscovery, RelatedPage

discovery = PageDiscovery(
    scraper=scraper,
    similarity_engine=similarity_engine,
    min_similarity=0.7
)

# Descubrir páginas relacionadas
related = discovery.discover_related_pages("https://facebook.com/page-seed")

# Filtrar por threshold
high_similarity = discovery.get_pages_above_threshold(related)

# Determinar si agregar como seed
for page in high_similarity:
    if discovery.should_add_as_seed(page):
        add_to_seeds(page)
```

### SimilarityEngine
```python
from src.discovery import SimilarityEngine

engine = SimilarityEngine(embeddings_provider=provider)

# Similitud entre dos textos
score = engine.compute_similarity("texto1", "texto2")

# Similitud en batch
scores = engine.compute_batch_similarity(texts, reference_texts)

# Similitud promedio
avg = engine.compute_average_similarity(texts, reference_texts)
```

## Consideraciones
- El scraper puede ser None para testing
- El similarity engine puede usar embeddings locales (Ollama)
- Threshold configurable para ajustar sensibilidad

## Tests
Ver test_unit.py y test_integration.py para casos de prueba.
"""
