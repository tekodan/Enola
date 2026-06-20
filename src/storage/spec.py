"""SPEC: Storage Module.

Este módulo se encarga de la persistencia de datos usando SQLite
como base de datos y exportación a CSV/JSON.

## Responsabilidades
- Persistir posts y comentarios en SQLite
- Guardar resultados de análisis
- Gestionar páginas semilla
- Exportar datos a CSV/JSON
- Generar reportes de violencia

## Modelo de Datos (SQLAlchemy)

### PostModel
Tabla para posts de Facebook.
- id: Primary key, identificador único
- text: Contenido textual
- author: Autor del post
- date: Fecha de publicación
- likes: Cantidad de likes
- comments_count: Cantidad de comentarios
- shares: Cantidad de shares
- url: URL al post
- page_id: ID de la página
- source: Tipo de fuente
- created_at: Timestamp de creación

### CommentModel
Tabla para comentarios de Facebook.
- id: Primary key
- text: Contenido textual
- author: Autor del comentario
- date: Fecha de publicación
- likes: Cantidad de likes
- post_id: Foreign key a posts
- parent_id: ID del comentario padre (para replies)
- url: URL al comentario
- created_at: Timestamp de creación

### AnalysisResultModel
Tabla para resultados de análisis.
- id: Primary key, autoincrement
- content_type: 'post' o 'comment'
- content_id: ID del contenido analizado
- post_id: Foreign key a posts (nullable)
- comment_id: Foreign key a comments (nullable)
- tiene_violencia: 'true', 'false', o 'unknown'
- tipo: Tipo de violencia detectada
- severidad: 'baja', 'media', 'alta'
- justificacion: Explicación del análisis
- evidencia: Cita del texto
- confidence: Score de confianza
- created_at: Timestamp de creación

### SeedPageModel
Tabla para páginas semilla.
- id: Primary key, autoincrement
- url: URL única de la página
- name: Nombre de la página
- page_id: ID de la página en Facebook
- is_seed: 'true' o 'false'
- discovered_from: URL de donde se descubrió
- violence_score: Score de violencia
- posts_count: Cantidad de posts extraídos
- created_at: Timestamp de creación

## API Pública

### Database
Clase principal para operaciones de base de datos.

```python
from src.storage import Database, get_database

# Crear instancia
db = Database("sqlite:///data/tfm.db")

# Guardar post
db.save_post({"id": "123", "text": "Hola", "author": "Test"})

# Guardar posts en batch
db.save_posts_batch([{"id": "1", ...}, {"id": "2", ...}])

# Guardar comentarios
db.save_comment({"id": "c1", "text": "Comment", "post_id": "123"})

# Guardar resultado de análisis
db.save_analysis_result({
    "content_type": "comment",
    "content_id": "c1",
    "tiene_violencia": "true",
    "tipo": "verbal",
    "severidad": "media",
    "justificacion": "Contiene insultos"
})

# Obtener datos
posts = db.get_posts(page_id="page-123")
comments = db.get_comments(post_id="post-123")
results = db.get_analysis_results(content_type="comment")
seed_pages = db.get_seed_pages(is_seed=True)

# Estadísticas
stats = db.get_stats()
# {'posts_count': 100, 'comments_count': 500, ...}
```

### ExportManager
Clase para exportación de datos.

```python
from src.storage import ExportManager

exporter = ExportManager(db, export_dir="data/exports")

# Exportar a CSV
csv_path = exporter.export_to_csv()

# Exportar a JSON
json_path = exporter.export_to_json()

# Reporte de violencia
report_path = exporter.export_violence_report()

# Listar archivos exportados
files = exporter.get_export_files()
```

## Dependencias
- SQLAlchemy: ORM para SQLite
- Pydantic: Validación de datos

## Consideraciones
- Uso de contexto manager para sesiones
- Transacciones con rollback en errores
- Índices en campos frecuentemente consultados
- Relaciones entre tablas para integridad referencial

## Tests
Ver test_unit.py y test_integration.py para casos de prueba.
"""
