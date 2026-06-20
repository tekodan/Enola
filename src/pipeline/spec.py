"""SPEC: Pipeline Module.

Este módulo orquesta el flujo completo del pipeline de detección
de violencia de género.

## Responsabilidades
- Orquestar todos los módulos
- Ejecutar pipeline iterativo
- Generar resultados combinados
- Manejar errores y logging

## Modelo de Datos

### PipelineStats
Estadísticas de ejecución del pipeline:
- pages_scraped: Páginas raspadas
- posts_found: Posts encontrados
- comments_found: Comentarios encontrados
- posts_classified: Posts clasificados
- comments_classified: Comentarios clasificados
- violence_detected_posts: Posts con violencia
- violence_detected_comments: Comentarios con violencia
- new_pages_discovered: Nuevas páginas descubiertas
- new_seed_pages_added: Nuevas semillas agregadas
- execution_time_seconds: Tiempo de ejecución

### PipelineResult
Resultado del pipeline:
- success: Si fue exitoso
- stats: PipelineStats
- errors: Lista de errores
- new_seeds: Nuevas semillas
- classified_posts: Posts clasificados
- classified_comments: Comentarios clasificados
- execution_time: Tiempo total
- timestamp: Timestamp de ejecución

### PipelineOrchestrator
Orquestador del pipeline:
- run_seed_pipeline: Ejecuta en páginas semilla
- run_discovery_pipeline: Ejecuta descubrimiento
- run_full_pipeline: Ejecuta pipeline completo con iteraciones

## API Pública

### PipelineOrchestrator
```python
from src.pipeline import PipelineOrchestrator, run_full_pipeline

orchestrator = PipelineOrchestrator(
    database=db,
    scraper=scraper,
    classifier=classifier,
    discovery=discovery,
    max_iterations=3
)

# Ejecutar en páginas semilla
result = orchestrator.run_seed_pipeline(["https://facebook.com/page1"])

# Ejecutar descubrimiento
result = orchestrator.run_discovery_pipeline()

# Ejecutar pipeline completo
result = orchestrator.run_full_pipeline(
    seed_pages=["https://facebook.com/page1"],
    iterations=3
)
```

### run_full_pipeline (función conveniencia)
```python
from src.pipeline import run_full_pipeline

result = run_full_pipeline(
    seed_pages=["https://facebook.com/page1"],
    database=db,
    classifier=classifier,
    max_iterations=3
)

print(f"Éxito: {result.success}")
print(f"Posts encontrados: {result.stats.posts_found}")
print(f"Violencia detectada: {result.stats.violence_detected_posts}")
```

## Tests
Ver test_unit.py y test_integration.py para casos de prueba.
"""
