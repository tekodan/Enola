---
tipo: Glosario de marcadores de género
proposito: Lista cerrada de tokens que el discriminador de
  violencia común usa para decidir si una entrada agresiva
  tiene sesgo de género o es violencia común genérica.
  Usado por ``src/analyzer/exclusion_filter.py::_load_gender_markers()``.
fecha_origen: 2026-07-12 (último tramo del refactor
  reglas-codigo → reglas-markdown)
---

# Glosario de marcadores de género

Lista cerrada de **palabras y frases** que el discriminador de
violencia común usa como señal de sesgo de género. Si el input
contiene UNO O MÁS de estos tokens cumpliendo función desvalorizante
hacia una mujer, el sistema lo trata como VDG potencial y NO lo
descarta como `VIOLENCIA_COMUN`.

## Bloque canónico (parseado por el código)

Las palabras de abajo son las que `src/analyzer/exclusion_filter.py`
lee al inicializar el módulo. Una por línea, sin acentos ni
mayúsculas (el matching es case-insensitive y sin acentos):

```plain
feminazi
foid
femoid
mangina
incel
mgtow
redpill
red pill
pastilla roja
hembrista
zorra
puta
perra
guarra
cosificar
matar
violar
violacion
violación
femicidio
mujeres de cocina
solo sirven
para eso estas
para eso estás
```

## Reglas de matching

1. **Case-insensitive.** Todo se normaliza a minúsculas antes de
   comparar.
2. **Acento-insensitive.** `violación` matchea `violacion` (sin
   acento).
3. **Substring match.** Si el término aparece dentro de una palabra
   más larga se considera presente.
4. **Función requerida.** El token debe usarse con función
   desvalorizante hacia una mujer — el discriminador NO decide
   función; cuando un token aparece pero el contexto es neutro
   (p. ej. un comentario académico que cita `incels` para
   analizarlos), el LLM recibe el input sin descuento de
   `VIOLENCIA_COMUN`.

## Origen de los tokens

| Categoría de origen | Tokens |
|---------------------|--------|
| Manosfera directa | `feminazi`, `foid`, `femoid`, `mangina`, `incel`, `mgtow`, `redpill`, `red pill`, `pastilla roja`, `hembrista` |
| Insulto sexual / cosificación | `zorra`, `puta`, `perra`, `guarra`, `cosificar` |
| Léxico letal | `matar`, `violar`, `violacion` / `violación`, `femicidio` |
| Roles y estereotipos | `mujeres de cocina`, `solo sirven`, `para eso estas/estás` |

## Trazabilidad

- Decisión de diseño: este glosario se carga en
  `exclusion_filter._load_gender_markers()` con `functools.lru_cache`
  (análogo a `_load_aggression_keywords()`).
- Última modificación: 2026-07-12 — la lista vivía hardcoded en
  `src/analyzer/exclusion_filter.py::_GENDER_MARKERS` (~30 líneas).
  Hoy se carga desde este markdown.

## Cambios recientes

- **2026-07-12.** Inicial. Cierra el último pase del refactor
  "reglas en código vs. reglas en documento" iniciado el 2026-07-12
  con los marcadores por subdimensión.
