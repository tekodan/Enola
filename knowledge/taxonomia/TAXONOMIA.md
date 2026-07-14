---
version: "1.1.0"
schema: "taxonomia-v1"
descripcion: "Taxonomía canónica de violencia de género digital en seis categorías operativas. Cada categoría incluye tres subdimensiones analíticas. Esta es la fuente de verdad estructural que consume el clasificador RAG; los documentos narrativos 01-06 de knowledge/categorias-violencia-genero-digital/ mantienen la fundamentación teórica y los marcadores léxicos asociados. Adicionalmente incluye la sección ``categorias_exclusion`` que documenta las pseudo-categorías pre-clasificatorias (``CODIGO_99`` = basura digital, ``VIOLENCIA_COMUN`` = agresión sin sesgo de género) consumidas por ``src.analyzer.exclusion_filter``. Las exclusiones no cuentan para el invariante de 6 categorías operativas."

categorias:
  - code: VDG_VIOLENCIA_SIMBOLICA
    orden: 1
    gravedad: "baja-media"
    subdimensiones:
      - code: "1.1"
        descripcion: "Roles tradicionales y de sumisión (imperativos doméstico-privados)"
      - code: "1.2"
        descripcion: "Incompetencia e inferioridad intelectual o física atribuida"
      - code: "1.3"
        descripcion: "Doble estándar moral / desvalorización genérica del colectivo femenino"

  - code: VDG_COSIFICACION_SLUTSHAMING
    orden: 2
    gravedad: "media"
    subdimensiones:
      - code: "2.1"
        descripcion: "Cosificación corporal o hipersexualización no consentida"
      - code: "2.2"
        descripcion: "Slut-shaming / juzgamiento anatómico"
      - code: "2.3"
        descripcion: "Doble estándar sexual / juzgar la conducta sexual femenina"

  - code: VDG_HOSTILIDAD_FEMINICIDIO
    orden: 3
    gravedad: "alta-extrema"
    subdimensiones:
      - code: "3.1"
        descripcion: "Amenaza explícita de agresión física o letal contra mujeres"
      - code: "3.2"
        descripcion: "Léxico letal mutado (leetspeak) o deseo de muerte explícito"
      - code: "3.3"
        descripcion: "Apología al feminicidio / normalización o minimización de la violencia"

  - code: VDG_MANOSFERA_ANTIFEMINISMO
    orden: 4
    gravedad: "media-alta"
    subdimensiones:
      - code: "4.1"
        descripcion: "Subculturas masculinistas y taxonomías de dominación"
      - code: "4.2"
        descripcion: "Desinformación de género / victimismo masculino"
      - code: "4.3"
        descripcion: "Troleo de género, jerga feminazi/aliade o animalización"

  - code: VDG_SALVAGUARDA_FALSO_POSITIVO
    orden: 5
    gravedad: "ortogonal"
    subdimensiones:
      - code: "5.1"
        descripcion: "Sarcasmo que vehiculariza un ataque (es VDG)"
      - code: "5.2"
        descripcion: "Humor hostil que enmascara una agresión (es VDG)"
      - code: "5.3"
        descripcion: "Reapropiación / cita / denuncia con marcadores mitigadores (NO VDG)"

  - code: VDG_DESACREDITACION_ACTIVISTAS
    orden: 6
    gravedad: "media-alta"
    subdimensiones:
      - code: "6.1"
        descripcion: "Deslegitimación ideológica del feminismo en abstracto"
      - code: "6.2"
        descripcion: "Ataque a activista específica (nombre propio)"
      - code: "6.3"
        descripcion: "Tergiversación: feminismo como perseguidor o victimizador"

categorias_exclusion:
  - code: EXC_BASURA_DIGITAL
    codigo_canonico: CODIGO_99
    descripcion: "Pseudo-categoría pre-clasificatoria. Se asigna automáticamente por src.analyzer.exclusion_filter.detectar_basura_digital cuando el payload no aporta contenido clasificable: Condición 1 — Vacío / NaN / Nulo. Condición 2 — Enlace huérfano (URL sin texto adicional). Condición 3 — Ruido tipográfico o emojis sin lexical útil. Condición 4 — Risas puras (jajaja, jeje, haha, rsrs, lol, xd). Condición 5 — Reacciones o muletillas de uno o dos caracteres sin lexical útil (ok, si, no, ya, dale, je, ah, obv). Los patrones léxicos viven en knowledge/categorias-violencia-genero-digital/glosario/patrones-basura-digital.md. Las filas etiquetadas con este código NO son borradas: persisten en analysis_results.exclusion_label y participan en el reporte de fiabilidad (Regla 1 — Valores perdidos) pero se excluyen del cómputo de violencia (Reglas 2-6)."
  - code: EXC_VIOLENCIA_COMUN
    codigo_canonico: VIOLENCIA_COMUN
    descripcion: "Pseudo-categoría pre-clasificatoria. El LLM (con apoyo del heurístico detectar_violencia_comun_heuristica en el fallback rule-based) devuelve este código cuando la agresividad detectada NO ataca a la víctima por su condición de mujer y carece de marcadores de las seis dimensiones de ciberviolencia. Discriminada por la REGLA DE EXCLUSIÓN: FILTRO DE DISCRIMINACIÓN DE VIOLENCIA COMÚN (SIN SESGO DE GÉNERO). Las filas etiquetadas se excluyen de la distribución de categorías operativas pero persisten para auditoría."
---

# Taxonomía canónica de violencia de género digital

Esta taxonomía es la **fuente de verdad estructural** que el clasificador
RAG (``src.analyzer.RAGClassifier``), el validador
(``src.analyzer.validate_codigo``) y los generadores de prompt
(``src.analyzer.render_tabla_canonica_prompt``) consumen.

## Cómo se usa desde el código

- **Loader:** ``src.analyzer.taxonomy_loader`` lee este archivo al
  arranque y lo cachea (``get_taxonomy()``).
- **Validación:** la clase ``Taxonomy`` de Pydantic garantiza
  invariantes: 6 categorías operativas, 3 subdimensiones por categoría,
  códigos únicos, gravedad ∈ set cerrado, orden correlativo.
- **Fachada:** ``src.analyzer.category_mapping`` reconstruye el enum
  ``Categoria``, los dicts ``SUBDIMENSIONES_POR_CATEGORIA`` /
  ``DESCRIPCION_SUBDIMENSION`` / ``GRAVEDAD_POR_CATEGORIA`` y la lista
  ``CATEGORIAS_ORDENADAS`` desde el modelo cargado, conservando la
  compatibilidad con todo el código existente.
- **Pseudo-categorías de exclusión:** ``categorias_exclusion`` documenta
  los códigos ``CODIGO_99`` (basura digital) y ``VIOLENCIA_COMUN``
  consumidos por ``src.analyzer.exclusion_filter``. NO entran en la
  distribución de las seis operativas ni en los gráficos/charts del
  reportes. ``taxonomy_loader.exclusion_codes()`` devuelve el mapeo
  ``EXC_*`` → ``CODIGO_*`` para el resto del sistema.

## Documentación teórica complementaria

Los siguientes documentos — indexados por ChromaDB y consumidos por
el prompt — amplían cada categoría con marcadores léxicos, errores
típicos y citas académicas:

- ``01-categoria-1-violencia-simbolica.md``
- ``02-categoria-2-cosificacion-slutshaming.md``
- ``03-categoria-3-hostilidad-feminicidio.md``
- ``04-categoria-4-manosfera-antifeminismo.md``
- ``05-categoria-5-sarcasmo-falsos-positivos.md``
- ``06-categoria-6-desacreditacion-activistas.md``
- ``07-tabla-canonica-prompt.md``

## Cómo editar la taxonomía

1. Modificar este archivo (frontmatter + cuerpo si aplica).
2. Si cambia el nombre de un código operativo, actualizar
   ``Categoria`` enum en ``src/analyzer/category_mapping.py``.
3. Si cambia una descripción de subdimensión, actualizar también los
   documentos narrativos ``01-06`` y la tabla canónica
   ``07-tabla-canonica-prompt.md``.
4. Si cambian los patrones léxicos de una pseudo-categoría de
   exclusión (p. ej. ``EXC_BASURA_DIGITAL``), editar el glosario
   correspondiente bajo
   ``knowledge/categorias-violencia-genero-digital/glosario/``
   (actualmente ``patrones-basura-digital.md``).
5. Reindexar ChromaDB: ``python -m src.knowledge_base add --source
   knowledge/taxonomia/TAXONOMIA.md``.
