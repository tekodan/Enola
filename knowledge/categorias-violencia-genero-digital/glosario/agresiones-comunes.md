---
tipo: Glosario
proposito: Vocabulario agresivo genérico (sin sesgo de género) usado por
  el discriminador de violencia común en ``src/analyzer/exclusion_filter.py``
fecha: 2026-07-12
---

# Glosario de agresiones comunes (sin sesgo de género)

Lista cerrada de **palabras y groserías genéricas** (sin referente
femenino) que el discriminador heurístico de violencia común busca
para decidir si una entrada agresiva pertenece al cajón de
`exclusion_label = "VIOLENCIA_COMUN"` o si debe pasar al LLM para
clasificación VDG sustantiva.

> **Regla de uso (Regla de exclusión — discriminación por motivación).**
> Si el input contiene UNO O MÁS de estos términos agresivos y NO
> contiene ningún marcador de género del glosario
> [`argot-misogino-general.md`](./argot-misogino-general.md), el
> sistema lo trata como **violencia común** (sin sesgo de género) y
> lo excluye del cálculo de incidencia VDG. La carga del archivo se
> hace una sola vez en `exclusion_filter._load_aggression_words()`
> con `functools.lru_cache`.

## Bloque canónico (parseado por el código)

Las palabras de abajo son las que `src/analyzer/exclusion_filter.py`
lee al inicializar el módulo. Una por línea, sin acentos ni
mayúsculas (el matching es case-insensitive y sin acentos):

```plain
idiota
imbecil
imbecil
estupido
estupido
mierda
carajo
joder
maldito
maldita
basura
inutil
inutil
huevon
huevon
boludo
pelotudo
forro
giles
gil
de mierda
ctm
ptm
hdp
hijueputa
hp
pendejo
pendeja
```

> **Por qué este set:** la auditoría 2026-07-12 detectó que
> `pendejo` era el insulto dominante en entradas agresivas sin
> sesgo de género (caso ar_id=72). Se incluyó además `pendeja`
> para mantener simetría de género — si el LLM recibe una frase
> agresiva dirigida específicamente a una mujer, ese caso disparará
> otras reglas (Cat. 2 / Cat. 3) y no llegará a este filtro.

## Reglas de matching

1. **Case-insensitive.** Todo se normaliza a minúsculas antes de
   comparar.
2. **Acento-insensitive.** `imbécil` matchea la entrada `imbecil`
   (sin acento).
3. **Substring match.** Si el término aparece dentro de una palabra
   más larga se considera presente. Por eso `ctm` queda como una
   sola unidad (4 caracteres) — matchear en sub-palabras produciría
   demasiados falsos positivos.
4. **No se aplica a Cat. 4 / 5.** Si el texto contiene un marcador
   manosférico (`feminazi`, `incel`, `beta`, etc.) o de sarcasmo
   marcado (`jajaja` + verbo agresivo), este discriminador **se
   saltea** y la entrada pasa al LLM.

## Trazabilidad

- Decisión de diseño: `docs/decisiones/2026-07-12_deteccion_reglas.md`
  (pendiente de crear) — "Mover listas léxicas del código al glosario".
- Última modificación: 2026-07-12 — agregado `pendejo` / `pendeja`
  tras la auditoría 2026-07-12 sobre `data/tfm.db`.
- Auditado en la auditoría `docs/auditoria-categorizaciones-2026-07-12.md`
  (entries `94a5252cf77e41e6`).

## Cambios recientes

- **2026-07-12.** Inicial. Lista consolidada con las groserías que
  el discriminador cargaba hardcoded en `exclusion_filter.py`. Se
  agrega `pendejo` / `pendeja` que faltaba.
