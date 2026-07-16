---
tipo: Glosario de patrones de basura digital
proposito: Lista cerrada de expresiones regulares que el pre-filtro de
  exclusión usa para detectar entradas con contenido no clasificable:
  risas puras (jajaja/jeje/haha/rsrs), muletillas o reacciones de uno
  o dos caracteres (ok/si/no/ya/je), y otros payloads sin lexical útil.
  Consumido por ``src/analyzer/exclusion_filter.py::_load_basura_digital_patterns``.
fecha_origen: 2026-07-14 (incorporación como glosario del pre-filtro,
  en paralelo al resto de glosarios canónicos bajo
  ``knowledge/categorias-violencia-genero-digital/glosario/``).
actualizaciones:
  - 2026-07-15: documenta COND_6_TAG_PERSONA (helper Python, no
    regex del glosario) — el detector de menciones vive en
    ``_is_only_mention_payload`` porque no es un patrón fullmatch
    sino una validación compuesta (presencia de ``@user`` Y ausencia
    de lexical word). El spec metodológico lo numera como COND_4; el
    código lo emite como COND_6 para preservar la numeración de las
    filas ya persistidas en ``analysis_results.exclusion_codigo``.
    Ver ``docs/informe-ambiguedades-subdimensiones-2026-07-14.md``.
---

# Glosario de patrones de basura digital

Lista cerrada de **expresiones regulares** que el pre-filtro
(`src/analyzer/exclusion_filter.py`) evalúa antes de invocar al LLM.
Si el texto matchea con CUALQUIERA de estos patrones (con
`re.fullmatch` sobre el texto normalizado a minúsculas sin espacios
laterales), se etiqueta como `CODIGO_99` — excluido del análisis de
categorización.

## Bloque canónico (parseado por el código)

El módulo ``_load_basura_digital_patterns()`` lee este bloque
``plain`` y compila cada línea como un patrón regex. Las líneas
vacías o que comienzan con ``#`` se ignoran. Cada patrón matchea
con `re.fullmatch` después de normalizar:

- minúsculas
- sin espacios al inicio/final
- sin acentos (NFKD + drop combining)

```plain
# ---- Risas puras (COND_4_SOLO_RISA) ----
^(ja){2,}[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(je){2,}[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(ji){2,}[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(ha){2,}[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(he){2,}[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(rs){2,}[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(lol)+[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(lmao)+[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(xd)+[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(ajaj+)(ja)*[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
^(jaj)+(aj)*[!¡¿?.,\s]*$ # COND_4_SOLO_RISA
# ---- Reacciones / muletillas cortas (COND_5_REACCION_CORTA) ----
^ok[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^dale[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^va[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^ya[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^si[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^no[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^je[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^ah[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^oh[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^eh[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^uf[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^uy[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^sep[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^obvio[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^claro[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^exacto[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
# ---- Monosílabos y partículas sueltas (COND_5_REACCION_CORTA) ----
# Conectores / partículas que carecen de contenido clasificable
# cuando aparecen como único payload del mensaje. ``re.fullmatch``
# exige que el mensaje entero sea uno de estos tokens (con cola
# opcional de ``! ? . ,``); "el café se fue" NO matchea.
^pues[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^se[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^que[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^qu(e|é)[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^qu(i|í)(s|z)(a|á)(s|z)?[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^a ver[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^aver[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^tal[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^cual[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^c(u|ú)al[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^quien[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^q(u|ú)ien[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^como[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^c(o|ó)mo[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^donde[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^d(o|ó)nde[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^cuando[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^cu(a|á)ndo[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^tambien[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^t(a|á)mbien[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^tampoco[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^tamp(o|ó)co[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^vale[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^venga[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^ahi[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^ah(i|í)[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^aqui[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^aqu(i|í)[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^alla[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^all(a|á)[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^aca[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^ac(a|á)[!¡¿?.,\s]*$ # COND_5_REACCION_CORTA
^q[!.?]?$ # COND_5_REACCION_CORTA
^k[!.?]?$ # COND_5_REACCION_CORTA
```

## Reglas de matching

1. **Case-insensitive.** Todo se normaliza a minúsculas antes de
   aplicar `re.fullmatch`.
2. **Acento-insensitive.** `jajajá` matchea con `jajaja` (se eliminan
   marcas diacríticas antes de la comparación).
3. **Trim de espacios.** `   jajaja   ` matchea con `jajaja`.
4. **Puntuación final permitida.** Se acepta una cola de signos
   (`!`, `?`, `.`, `,`) y/o un único espacio al final, pero el
   cuerpo del match debe ser EXACTAMENTE la risa o muletilla.
5. **Full-match.** El regex es anclado con `^` y `$` (o implícito
   vía `re.fullmatch`); ningún carácter adicional fuera del patrón
   matchea. Esto evita falsos positivos con textos cortos como
   "asistió" (que contiene "si" pero no matchea `^si$`).
6. **Unicode por patrón.** Los caracteres no-ASCII (emojis
   sueltos, etc.) ya quedan capturados por `COND_3_RUIDO_TIPOGRAFICO`
   en el pre-filtro principal; este glosario es complementario.

## Origen de los patrones

| Categoría | Patrones | Justificación |
|-----------|----------|---------------|
| Risas puras | `jajaja`, `jeje`, `jiji`, `haha`, `hehe`, `rsrs`, `lol`, `lmao`, `xd`, `ajaj`, `jajaj` | Expresiones onomatopéyicas de risa sin contenido semántico clasificable. |
| Muletillas | `ok`, `dale`, `va`, `ya`, `si`, `no`, `je`, `ah`, `oh`, `eh`, `uf`, `uy`, `sep` | Reacciones de uno o dos caracteres que no codifican un acto violento. |
| Confirmaciones | `obvio`, `claro`, `exacto`, `vale`, `venga` | Asentimientos lexicalmente pobres que el LLM tiende a sobre-interpretar. |
| Monosílabos / partículas (2026-07-14) | `pues`, `se`, `que/qué`, `tal`, `cual/cuál`, `quien/quién`, `como/cómo`, `donde/dónde`, `cuando/cuándo`, `también`, `tampoco`, `ahí`, `aqui/aquí`, `allá`, `acá`, `a ver`, `q`, `k` | Conectores y partículas sueltas que, usados como único payload, no aportan contenido clasificable. El ``fullmatch`` exige que TODO el mensaje sea el token, por lo que ``"el café se fue"`` NO matchea. |
| Menciones a persona (2026-07-15) — COND_6 | `@usuario`, `@user.name`, `@user_123`, `@user1 @user2` | Implementado en ``_is_only_mention_payload`` (helper Python, no regex de este glosario). El mensaje debe consistir exclusivamente en uno o más tokens ``@user`` sin ninguna otra palabra legible. ``"hola @user cómo estás"`` NO matchea (hay lexical word fuera de las menciones). Spec lo numera COND_4; el código lo emite como COND_6 para preservar la numeración existente. |

## Trazabilidad

- Decisión de diseño: este glosario se carga en
  ``_load_basura_digital_patterns()`` con ``functools.lru_cache``
  (análogo a ``_load_gender_markers()`` y
  ``_load_aggression_keywords()``).
- Si el archivo no existe, el módulo cae a una lista vacía y el
  pre-filtro sigue funcionando — la lista se conserva como fuente
  de verdad editable, no como contrato duro.
- Última modificación: 2026-07-14 — inicial. Cierra la solicitud
  de reforzar la detección de basura digital para entradas muy
  cortas (comentarios tipo risa, muletillas, monosílabos sueltos,
  GIF con caption vacío).

## Cómo editar los patrones

1. Agregar o quitar líneas en el bloque ``plain`` de arriba.
2. Si un patrón implica cambios semánticos (p. ej. capturar
   negaciones tipo "no loca" — actualmente NO matchea porque la
   palabra "no" exige `^no$` y rechaza "no loca"), documentar la
   decisión en la tabla "Origen de los patrones".
3. Reindexar no es necesario: el módulo recompila los patrones al
   siguiente import (o al invalidar el cache con
   ``reset_cache()``).

## Cambios recientes

- **2026-07-14.** Inicial. Cierra la solicitud de reforzar la
  detección de basura digital para entradas muy cortas (comentarios
  tipo risa, muletillas, monosílabos como `no`/`si`/`se`/`pues`/
  `que`, GIF con caption vacío, etc.).
- **2026-07-15.** Documenta COND_6_TAG_PERSONA. La nueva condición
  (mención a persona sola, sin comentario adicional) NO vive como
  regex en este glosario porque no es un patrón ``fullmatch`` sino
  una validación compuesta: presencia de al menos un token ``@user``
  Y ausencia de lexical word fuera de las menciones. El helper
  ``_is_only_mention_payload`` en ``src/analyzer/exclusion_filter.py``
  encapsula esa lógica. Numerado como COND_6 para no colisionar con
  COND_4_SOLO_RISA / COND_5_REACCION_CORTA ya persistidos en
  ``analysis_results.exclusion_codigo``.
