---
tipo: Recomendaciones de calibración
fecha: 2026-07-14
audiencia: Mantenimiento del sistema RAG (categorización de VDG)
origen: Análisis cruzado de TAXONOMIA.md, los 6 docs narrativos (01-06),
  el Protocolo algorítmico (00), las dos tablas canónicas (07 +
  glosario/marcadores-por-subdimension.md), los glosarios, los datos de
  data/tfm.db (79) y data/tfm78valida.db (78), y las auditorías
  2026-07-12 / 2026-07-13.
estado: PROPUESTA — pendiente de aprobación
---

# Recomendaciones para corregir la asignación de sub-dimensiones en el clasificador RAG

> **TL;DR.** El LLM acierta la **categoría** (Cat. 1, 2, 3, 4, 5, 6) pero se
> equivoca en la **sub-dimensión** (`1.1`/`1.2`/`1.3`, `2.1`/`2.2`/`2.3`, etc.).
> Las causas son **cuatro**: (1) los dos archivos que deberían contener el mismo
> contrato léxico están desalineados; (2) las reglas de desempate entre
> sub-dimensiones viven en prosa narrativa y nunca llegan al prompt;
> (3) la deduplicación colapsa múltiples marcadores en una sola etiqueta;
> (4) los `SAFEGUARD` huérfanos no tienen default. Las recomendaciones
> siguientes atacan cada causa con cambios quirúrgicos, sin tocar la
> taxonomía cerrada ni el enum `Categoria`.

---

## 0. Glosario operativo

| Término | Definición |
|---------|------------|
| **Overlap** | Un mismo marcador (palabra/frase) está listado como válido para **más de una** sub-dimensión en distintos archivos del sistema. El LLM no sabe cuál elegir sin una regla de desempate. |
| **Desempate** | Regla explícita que decide qué sub-dimensión gana según el contexto sintáctico o semántico del marcador. |
| **Disparador obligatorio** | Token o patrón que, si aparece, **fuerza** la asignación de una sub-dimensión (no es opcional, es requisito). |
| **Guardarraíl** | Restricción dura que se aplica desde el validador determinístico (no desde el LLM) para bloquear asignaciones inválidas. |
| **Bloque para prompt** | Sección `## Bloque para prompt` dentro de un `.md` que `load_prompt_block()` inyecta verbatim al clasificador. |

---

## 1. Diagnóstico resumido (contexto)

El sistema está bien diseñado en su **arquitectura**: la taxonomía cerrada en
`TAXONOMIA.md`, validada por invariantes en `taxonomy_loader.py:130-151` y
expuesta como enum `Categoria` en `category_mapping.py:81-97`, es robusta. El
clasificador RAG (`rag_classifier.py`) carga 5 bloques markdown al prompt:
marcadores canónicos, leetspeak, mitigadores, coocurrencia y Cat. 5. La
auditoría 2026-07-13 reconoció 91% de acuerdo global.

Pero el **contrato léxico** que el prompt inyecta está **roto en cuatro
puntos concretos**, todos detectables empíricamente con los 79 análisis de
`data/tfm.db`:

| # | Punto de fricción | Evidencia |
|---|-------------------|-----------|
| F1 | Las dos tablas canónicas no coinciden | `07-tabla-canonica-prompt.md:125` lista `mujeres modernas, degeneración` para 4.2; `marcadores-por-subdimension.md:35` los omite. |
| F2 | Marcadores en la dimensión equivocada | `marcadores-por-subdimension.md:25` lista `mujer al volante / calladita` en 1.1; el doc 01 Regla 2 dice 1.2. |
| F3 | Reglas de desempate ausentes del prompt | El Protocolo §4 / §4.bis / §4.ter explica 1.1↔1.3, 3.1↔3.3, 4.1↔4.2↔4.3 en prosa narrativa; el prompt no las inyecta. |
| F4 | Multi-etiqueta colapsada en Cat. 4 | `validate_clasificaciones` deduplica por `(cat, dim)`, perdiendo `aliade` + `f3m1 nizta` como dos filas distintas. |

A esto se suman tres **errores residuales** que la propia auditoría
documenta: `SAFEGUARD` huérfanos, 2.1 disparado por mera presencia de
"mujer", y sobre-uso de 3.1 como cajón de "lo grave".

---

## 2. Las 8 recomendaciones

### R1. Sincronizar las dos tablas canónicas de marcadores

**Cambio concreto** en
`knowledge/categorias-violencia-genero-digital/glosario/marcadores-por-subdimension.md`:

- **1.1** — quitar `mujer al volante, mujer florero, calladita, niñata`.
- **1.2** — agregar los anteriores + restaurar `no sabe, le falta un hervor`.
- **2.2** — quitar `zorra, puta, perra, guarra` (movidos a 2.3).
- **2.3** — agregar `zorra, puta, perra, guarra`.
- **4.1** — agregar `foid, femoid, femoids, human female, bio-lump`.
- **4.2** — agregar `mujeres modernas, degeneración, mentalidad moderna`.

**Por qué funciona.** El prompt del clasificador carga
`_PROMPT_BLOCK_MARCADORES` desde este archivo (línea 50 de
`rag_classifier.py`) y lo inyecta verbatim como sección "MARCADORES
CANONICOS". Si los términos no están ahí, **el LLM no puede anclar el
match léxico** y se ve forzado a elegir por inferencia semántica — donde
falla sistemáticamente, porque la inferencia sin anclaje léxico se va al
"vecino más cercano" del set canónico, que suele ser el código de
gravedad media (1.3, 3.1, 4.3). El post 1 (`ar_id=1`, "*Las mvjeres
modernas crecen en un entorno que incentiva la degenerac18n*") terminó
etiquetado 1.3 en `tfm.db` precisamente por esto: el LLM no encontró
`degeneración` mapeado a 4.2 en su prompt y cayó al 1.3 por defecto.

Cuando las dos tablas (`07-tabla-canonica-prompt.md` y
`marcadores-por-subdimension.md`) digan lo mismo, el LLM tiene **un único
dueño por término** y reduce su espacio de ambigüedad sin tocar la
lógica del clasificador. Es el cambio más estructural porque quita la
contradicción en la fuente.

**Casos testigo que valida la corrección:**

| `ar_id` | Texto | Antes | Después esperado |
|---:|---|---|---|
| 1 | "mujeres modernas + degenerac18n" | `1.3` | `1.3, 2.3, 4.2` (con `degeneración` ya mapeado) |
| 4 | "cog13nd8 + c8g1d8 + beta" | `1.3, 2.3, 4.1` | igual + 4.2 reforzado |
| 6 | "beta + soltera + follar" | `1.3, 2.3, 4.1, 4.2` | igual |

---

### R2. Crear `glosario/reglas-desempate.md` e inyectarlo al prompt

**Cambio concreto.** Nuevo archivo
`knowledge/categorias-violencia-genero-digital/glosario/reglas-desempate.md`
con sección `## Bloque para prompt` que contenga reglas con disparadores
explícitos para las cuatro fronteras ambiguas:

| Frontera | Disparador primario (gana) | Si NO aparece → evaluar |
|---|---|---|
| **1.1 vs 1.3** | `a lavar / a limpiar / cocinar / criar al bebé / cuidar de sus hijos / pónganse a barrer / tener recogido` → **1.1** | 1.2 / 1.3 / 4.2 |
| **3.1 vs 3.3** | `te voy a / la voy a / voy a golpear / a puñetazo limpio / golpeen su cara` → **3.1** | Si aparece `se lo buscaron / es mejor no meterse aunque la estén matando / justicia de miércoles / por eso ocurren los feminicidios` → **3.3** (no 3.1) |
| **4.1 vs 4.2 vs 4.3** | Arquetipo (`beta / del 1% / red pill / incel / mgtow / foid`) → **4.1** | Esencialismo victimista (`mujeres modernas / degeneración / hipergamia / gold digger / mentalidad 1%`) → **4.2**; troleo (`feminazi / hembrista / aliade / mangina / pagafantas / f3m1 nizta`) → **4.3** |
| **1.3 vs 6.2** | Si hay nombre propio de feminista / `@usuario` / hashtag `#8M` / contexto de protesta → **6.2** | Si no → **1.3** |

Modificar `src/analyzer/rag_classifier.py`:

- Línea 50-54 — añadir `_PROMPT_BLOCK_DESEMPATE = load_prompt_block("glosario/reglas-desempate.md")`.
- Línea ~618 — añadir `desempate_bloque = _PROMPT_BLOCK_DESEMPATE` e inyectarlo en el `f"""..."""`.

**Por qué funciona.** El LLM no es bueno discriminando por descripción
narrativa ("se aplican reglas generales de inclusión algorítmica…"). Es
bueno discriminando por **reglas con disparadores enumerados**. Las 4
fronteras ambiguas ya están descritas cualitativamente en el Protocolo
`00-protocolo-algoritmico.md` (secciones 4, 4.bis, 4.ter), pero **nunca
se inyectan al prompt**. Es exactamente el patrón que la auditoría
2026-07-12 detectó y que el refactor del 13 no cerró: las reglas están en
el documento teórico pero el clasificador opera como si no existieran.

**Por qué las reglas con disparadores explícitos funcionan mejor que las
descripciones narrativas:**

1. **Reduce el espacio de búsqueda.** En lugar de evaluar las 18
   sub-dimensiones abiertas, el LLM puede ejecutar un *match* directo
   contra un set cerrado de tokens antes de inferir.
2. **Elimina la transferencia por similitud semántica.** Sin
   disparadores, el LLM elige por vecindad conceptual: 1.1 y 1.3 son
   "ambos violencia simbólica hacia mujeres", así que cuando duda va al
   más genérico (1.3). Con disparadores, la elección es mecánica.
3. **Permite verificar.** Un test puede afirmar *"si el texto contiene
   `a lavar`, debe asignar 1.1; si no, nunca 1.1"*. Sin disparadores,
   el test es opinable.

**Casos testigo que valida la corrección:**

| `ar_id` | Texto abreviado | Antes | Después esperado |
|---:|---|---|---|
| 36 | "ellas son las que me dan cariño y pagan todo" | `1.1` ❌ | `[]` (sin imperativo doméstico) |
| 43 | "si tenés más de 60 años… si no colaboras no se te acerca ninguna" | `1.3` ❌ | `[]` (sin marcador 1.3 canónico) |
| 71 | "asi la estén matando es mejor no meterse" | `3.1` ❌ | `3.3, 6.3, 5.2` ✅ |

---

### R3. Regla dura para Cat. 2.1 en el prompt

**Cambio concreto.** Añadir al bloque de desempate (R2) la frase:

> *"Cat. 2.1 exige un adjetivo o sintagma cosificador
> (`putita obediente | packs | enseñando las nalgas | naquitas | mostrá
> las tetas | para eso estás | objetivar`). La sola mención de 'mujer'
> como presencia/ausencia NO es 2.1."*

**Por qué funciona.** El caso `b7aff28bc7d3c1de` (`ar_id=61`,
"*A mí me da igual con mujer o sin mujer la paja no falta*") disparó
2.1 porque el LLM vio `mujer` y asumió cosificación. El problema es que
**"mujer"** es un **referente válido para coocurrencia** (necesario para
muchas categorías), no un marcador suficiente. El sistema actual en
`marcadores-por-subdimension.md:28` lista los marcadores correctos pero
**no prohíbe usar 2.1 sin ellos**. La regla dura lo convierte en un
**requisito explícito** en el prompt, no en una sugerencia implícita.

**Por qué funciona a nivel cognitivo del LLM:** el modelo distingue
entre *tokens de contexto* (palabras que dan tema, como "mujer") y
*tokens de marcador* (palabras que disparan una categoría, como
"nalgas"). Sin la regla, los **fusiona** porque ambos aparecen en
contextos similares. Con la regla, el LLM ejecuta un pipeline de dos
pasos: (a) ¿hay tema femenino? → continuar; (b) ¿hay marcador
cosificador? → si no, descartar 2.1.

---

### R4. Cambiar la deduplicación en `validate_clasificaciones` para Cat. 4

**Cambio concreto.** En
`src/analyzer/category_mapping.py:372-388`, la clave de dedupe pasa
de `key = (cat, dim)` a
`key = (cat, dim, tuple(sorted(marcadores_detectados)))`. La
deduplicación colapsa solo si las tres componentes son idénticas.

**Por qué funciona.** Hoy el comentario `ed489d3558a69eef` (`ar_id=26`,
"*Para el aliade y la f3m1 nizta*") tiene **dos marcadores 4.3
independientes**: uno por cada término decodificado del leetspeak
(`aliade` → aliado emasculado, `f3m1 nizta` → feminazi). Atacan a
colectivos distintos (varón aliado vs. feminista) y la auditoría 2026-07-13
recomienda `4.3 × 2`. `validate_clasificaciones:386` los colapsa en una
sola entrada porque coinciden en `(cat, dim)`.

Cambiar la clave por la **triplupla** preserva la trazabilidad
multi-marcador **sin cambiar el formato JSON de salida** ni el contrato
con los tests existentes. Es el cambio más quirúrgico: no toca el
prompt, no toca el LLM, no rompe nada. Solo permite que dos
etiquetas con la misma `(cat, dim)` pero distintos `marcadores_detectados`
coexistan.

**Por qué funciona a nivel de datos:** el modelo `LabelAssignment`
(`rag_classifier.py:68-89`) ya tiene `marcadores_detectados: list[str]`
como campo opcional. La clave compuesta es solo un cambio en la función
de deduplicación, no en el schema. La tabla lateral `analysis_labels`
(`database.py:119`) ya tiene columnas por-label y `analysis_feedback_labels`
(id. 1180) espeja correctamente, así que **no hay migración de DB**.

**Caso testigo:**

| `ar_id` | Texto | Antes | Después esperado |
|---:|---|---|---|
| 26 | "Para el aliade y la f3m1 nizta" | `4.3` (×1) | `4.3, 4.3` (×2 con marcadores distintos) |

---

### R5. Forzar 5.3 cuando llega `SAFEGUARD` sin sub-dim

**Cambio concreto.** En
`src/analyzer/category_mapping.py:normalize_dimension` (líneas 203-233),
agregar al inicio del cuerpo:

```python
if categoria == Categoria.VDG_SALVAGUARDA_FALSO_POSITIVO.value:
    return "5.3"  # por defecto: reapropiación / fuera de VDG
```

Emitir un `logger.warning` con `categoria` y la dimensión original para
trazabilidad.

**Por qué funciona.** Los dos casos `a1478d1dd8727dd4` (`ar_id=19`) y
`1f09dfc016268ce8` (`ar_id=56`) quedaron como `VDG_SALVAGUARDA_FALSO_POSITIVO`
con `dimension=NULL`. La auditoría 2026-07-13 recomienda asignar **5.3**
por defecto. El razonamiento empírico: en la práctica, cualquier SAVEGUARD
sin sub-dim es un caso donde el LLM **"sospecha" pero no confirma
ataque**, lo que se asimila más a **5.3 (reapropiación / falsa alarma /
fuera de VDG)** que a 5.1 (sarcasmo) o 5.2 (humor hostil), que serían
explícitos si los hubiera.

**Por qué funciona como guardarraíl determinístico:**

1. **No contradice al LLM.** Si el LLM emitió 5.1, 5.2 o 5.3
   explícitamente, la entrada pasa tal cual. Solo cambia los casos
   huérfanos.
2. **Es reversible.** El warning estructurado permite que un humano
   revise luego y, si lo desea, lo reclasifique.
3. **Cierra una consulta SQL frecuente.** El reporte de
   `analysis_results` actualmente tiene que filtrar
   `categoria='SAFEGUARD' AND dimension IS NULL` por separado; con
   esta regla siempre será `dimension='5.3'`, simplificando joins.

**Caso testigo:**

| `ar_id` | Texto | Antes | Después esperado |
|---:|---|---|---|
| 19 | "Nadie vendrá a salvarte…" | `SAFEGUARD / null` | `SAFEGUARD / 5.3` |
| 56 | "Nadie vendrá a salvarte…" | `SAFEGUARD / null` | `SAFEGUARD / 5.3` |

---

### R6. Inyectar al prompt la regla "una entrada por marcador independiente en Cat. 4"

**Cambio concreto.** Crear
`knowledge/categorias-violencia-genero-digital/glosario/multi-etiqueta-instrucciones.md`
con bloque `## Bloque para prompt`:

> *"En Cat. 4 (manosfera), si el texto contiene VARIOS marcadores
> independientes (p. ej. `aliade` + `f3m1 nizta`), devolvé una entrada
> `clasificaciones` POR CADA marcador, con sus propios
> `marcadores_detectados` y `evidencia`. Las demás categorías (1, 2, 3,
> 5, 6) sí se deduplican por `(categoria, dimension)` salvo que los
> marcadores sean semánticamente distintos."*

E inyectarlo en `rag_classifier.py:_build_prompt()` (línea ~618), después
del bloque de desempate.

**Por qué funciona.** El cambio R4 (deduplicación por tripleta) **sin**
esta instrucción explícita en el prompt dejaría al LLM emitiendo un solo
JSON con `marcadores_detectados=['aliade', 'f3m1 nizta']` — el
validador no podría partirlo en dos filas retroactivamente. Combinado
con R4, queda **blindado en dos capas**: instrucción explícita al LLM +
validación determinística.

**Por qué dos capas funcionan mejor que una:**

1. **El LLM produce la estructura correcta desde el origen.** No hay
   que reconstruir a posteriori.
2. **Si el LLM no cumple la instrucción, el validador igualmente
   preserva los marcadores** porque no colapsa por `(cat, dim)` puro.
3. **Los tests pueden verificar ambos extremos:** el JSON crudo del LLM
   debe tener 2 entradas, y la tabla `analysis_labels` debe tener 2 filas.

---

### R7. Tests que blinden los 7 errores residuales de la auditoría 2026-07-13

**Cambio concreto.** Agregar a
`src/analyzer/test_category_mapping.py` (o crear
`src/analyzer/test_subdimension_rules.py`) los 7 casos de la tabla §3 de
`docs/auditoria-categorizaciones-2026-07-13.md`:

| `ar_id` | Texto abreviado | Esperado | Valida |
|---:|---|---|---|
| 25 | "actitudes de hombre blanco" | `[4.2, 1.3]` | R1 + R2 |
| 26 | "Para el aliade y la f3m1 nizta" | `[4.3, 4.3]` (multi-marker) | R4 + R6 |
| 36 | "ellas son las que me dan cariño y pagan todo" | `[]` | R2 (1.1 sin imperativo) |
| 43 | "No es tan así si tenés más de 60 años…" | `[]` | R2 (1.3 sin marcador canónico) |
| 45 | "...como son todas las mujeres… enculada o les duele la cabeza" | `[1.3, 2.3, 4.2, 5.2]` | R1 (4.2 vs 4.3) + R3 |
| 60 | "No que a las feministas no les hacen caso jaja" | `[4.3, 6.1, 5.2]` | R2 (5.2 multi) |
| 61 | "con mujer o sin mujer la paja no falta" | `[]` | R3 (2.1 sin cosificador) |

Los tests corren contra el **validador determinístico**
(`validate_clasificaciones`, `normalize_dimension`, `validate_codigo`),
no contra el LLM directo. Se simulan JSON crudos como los que devolvería
el LLM y se verifica que el validador produce el resultado esperado.

**Por qué funciona.**

1. **Los 7 casos están validados por el auditor humano.** La auditoría
   2026-07-13 explícitamente dice "DE ACUERDO con observación" /
   "RECATEGORIZAR" sobre estos. Son ground truth.
2. **Son tests unitarios rápidos** (~ms cada uno) — no requieren Ollama
   ni ChromaDB, solo CPU. Se ejecutan en `pytest` sin tag de
   integración.
3. **Cubren las 4 causas raíz** identificadas: F1 (caso 25), F2
   (casos 36, 43, 45), F3 (caso 60), F4 (caso 26), 2.1 falso positivo
   (caso 61).
4. **Actúan como contratos vivos.** Cualquier modificación futura al
   prompt o al validador que rompa uno de estos 7 casos **falla el
   test** y alerta al desarrollador antes del merge.

---

### R8. Regla de oro: no tocar la taxonomía cerrada ni el enum `Categoria`

**Cambio concreto.** Ninguno. Es una **restricción explícita** sobre
qué no hacer.

**Por qué funciona (como restricción).** La taxonomía cerrada
(6 categorías × 3 sub-dimensiones = 18 códigos) está validada por
invariantes duros en
`src/analyzer/taxonomy_loader.py:130-151`:

```python
if len(self.categorias) != 6: raise ValueError(...)
codes = [c.code for c in self.categorias]
if len(set(codes)) != 6: raise ValueError(...)
if ordens != [1, 2, 3, 4, 5, 6]: raise ValueError(...)
dim_codes = [..., ...]
if len(set(dim_codes)) != 18: raise ValueError(...)
```

Y el enum `Categoria` en
`src/analyzer/category_mapping.py:81-97` es la fuente de verdad para
los tipos en todo el sistema. Cambiar la taxonomía rompería:

- El schema SQLite (`analysis_results.categoria`, `analysis_labels`,
  `analysis_feedback_labels`).
- El árbol del dashboard NiceGUI (`src/ui/nicegui_app/`).
- Los reportes de Regla 2 (`src/report/stats.py`),
  Regla 3 (`compute_mode`),
  Regla 4 (`compute_crosstabs`),
  Regla 6 (`src/report/metrics.py`).
- Las migraciones (`database.py:_migrate_schema`).
- El fixture ChromaDB (`data/chroma_db/`).
- Los tests de `test_taxonomy_loader.py`.

**Las 7 recomendaciones anteriores preservan exactamente los 18 códigos
(`1.1`…`6.3`) intactos** — solo cambian marcadores léxicos y reglas de
desempate **dentro** de cada código. Esto es lo que hace que el cambio
sea de bajo riesgo y alta ganancia.

---

## 3. Por qué la combinación funciona mejor que cada cambio aislado

Los 7 cambios no son independientes — son **complementarios**:

```
         ┌─────────────────────────────────────┐
         │   PROMPT (lo que el LLM ve)         │
         │                                     │
         │   R1: marcadores correctos           │
         │   R2: reglas de desempate            │
         │   R3: regla dura para 2.1            │
         │   R6: instrucción multi-etiqueta    │
         └─────────────────┬───────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   LLM (qwen3.5:9b)     │
              │   emite JSON crudo     │
              └────────────┬───────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │   VALIDADOR (lo que el sistema      │
         │   acepta o rechaza)                 │
         │                                     │
         │   R4: dedup por tripleta en Cat. 4  │
         │   R5: default 5.3 si SAFEGUARD nulo │
         └─────────────────┬───────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   TESTS (R7)           │
              │   blindan la regresión │
              └────────────────────────┘
```

- **R1 + R2 + R3 + R6** atacan el lado **generativo** (el LLM produce
  mejor).
- **R4 + R5** atacan el lado **validativo** (el sistema no rompe lo que
  el LLM emite).
- **R7** ataca el lado **contractual** (futuros cambios no rompen lo
  validado).

Si solo hiciéramos R1 sin R2, el LLM seguiría sin saber discriminar
1.1/1.3. Si solo hiciéramos R4 sin R6, el LLM seguiría emitiendo JSON
con un solo `4.3` aunque el validador acepte multi. Si solo hiciéramos
R5 sin R2, los SAVEGUARD huérfanos quedarían resueltos pero las
discriminaciones finas seguirían rotas.

---

## 4. Plan de implementación

### Orden sugerido (con dependencias)

| Paso | Cambio | Depende de | Esfuerzo | Riesgo |
|------|--------|------------|----------|--------|
| 1 | R1 (sincronizar tablas) | — | Bajo (edición de 1 archivo) | Bajo |
| 2 | R2 (crear `reglas-desempate.md` + inyectar) | — | Bajo (1 archivo nuevo + 2 líneas de código) | Bajo |
| 3 | R3 (añadir regla 2.1 al bloque de R2) | R2 | Trivial (1 línea en R2) | Nulo |
| 4 | R5 (default 5.3) | — | Trivial (5 líneas de código) | Muy bajo |
| 5 | R4 (dedup por tripleta) | — | Bajo (1 línea) | Bajo |
| 6 | R6 (instrucción multi) | R4 | Bajo (1 archivo nuevo + 2 líneas) | Bajo |
| 7 | R7 (tests) | R1-R6 implementados | Medio (7 tests nuevos) | Nulo |
| 8 | Re-correr batch sobre los 79 textos | R1-R6 | Bajo (1 comando `python -m src.report analyze`) | Nulo |

### Tiempo estimado

~3-4 horas de implementación + ~30 min de revisión + ~30 min de
re-batch + ~30 min de análisis comparativo.

---

## 5. Métricas de éxito

Comparar los resultados de re-correr el batch sobre los mismos 79
textos contra los datos actuales en `data/tfm.db`:

| Métrica | Hoy (auditoría 2026-07-13) | Meta post-cambios |
|---------|---:|---:|
| Acuerdo global | 91% (78 casos) | **≥97%** |
| Falsos positivos residuales | 2 (`ar_id=43`, `ar_id=61`) | 0 |
| Falsos positivos `SAFEGUARD` huérfanos | 2 (`ar_id=19`, `ar_id=56`) | 0 |
| Multi-etiqueta colapsada en Cat. 4 | 1 (`ar_id=26`) | 0 |
| Errores 1.1 sin imperativo | 1 (`ar_id=36`) | 0 |
| Errores 3.1↔3.3 | 0 (post-fix 2026-07-13) | mantener |
| Cobertura de marcadores leetspeak | 100% | mantener |

**Medición adicional cualitativa:** correr la nueva clasificación sobre
los ~40 comentarios del archivo de fixture `tests/fixtures/*.json` (si
existe) y verificar que los marcadores de `degeneración`, `mujeres
modernas`, `aliade`, `f3m1 nizta`, `foid` siempre caen en la
sub-dimensión correcta.

---

## 6. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Cambiar dedupe (R4) rompe tests existentes que asumen 1 entrada por `(cat, dim)` | Baja | Bajo | Revisar `test_category_mapping.py`; ajustar asserts que comparen `len(result)==1` cuando hay multi-marker. |
| Inyectar bloque de desempate (R2) hace el prompt demasiado largo (>2k tokens) | Baja | Bajo | El bloque es ~600 tokens. Total del prompt quedaría en ~3.5k tokens. Ollama con `qwen3.5:9b` soporta 8k context sin problemas. |
| Default 5.3 (R5) oculta un caso real de 5.1 o 5.2 que el LLM no supo etiquetar | Media | Bajo | El warning estructurado permite revisión posterior; los reviewers humanos pueden sobrescribir. |
| Reglas de desempate demasiado rígidas bloquean casos grises legítimos | Baja | Medio | Las reglas usan "Si aparece X → Y; si NO → evaluar". Son **pistas direccionales**, no prohibiciones absolutas. El LLM puede seguir emitiendo lo que quiera, solo que ahora tiene un ancla más fuerte. |
| R1 introduce marcadores que ya estaban en otra sub-dim y genera nuevos overlaps | Baja | Bajo | R2 cubre la política de overlaps. Si surge un nuevo conflicto, se resuelve con R2 + revisión de la tabla consolidada. |

---

## 7. Lo que NO se hace (y por qué)

- **No se cambian los 18 códigos (`1.1`…`6.3`).** Ver R8.
- **No se modifica el enum `Categoria` en `category_mapping.py:81-97`.**
  Ver R8.
- **No se cambia el schema de `analysis_labels` / `analysis_feedback_labels`.** El modelo Pydantic `LabelAssignment` y los side tables
  ya soportan multi-marcador. Solo cambia la deduplicación en el
  validador (R4).
- **No se reescribe `_build_prompt()`.** Solo se añade un bloque más
  (R2, R6) en la posición correcta. El resto del prompt queda intacto.
- **No se elimina el bloque Cat. 5 que ya está.** El bloque
  `_PROMPT_BLOCK_CAT5` (línea 54 de `rag_classifier.py`) es correcto y
  resuelve 5.1/5.2/5.3 bien. R5 solo agrega el default determinístico
  cuando la sub-dim es nula.

---

## 8. Validación final: ¿cuándo decimos que está listo?

Cuando se cumplan las tres condiciones:

1. **Tests R7 pasan en CI/local** sin Ollama ni ChromaDB.
2. **Re-batch sobre los 79 textos de `data/tfm.db` produce ≥97% de
   acuerdo con la auditoría 2026-07-13** (medido como intersección de
   `(ar_id, categoria, dimension)` contra la tabla §3 de la auditoría).
3. **Los 5 errores residuales** (`ar_id=25`, 26, 36, 43, 60, 61) están
   todos corregidos.

---

*Documento preparado el 2026-07-14 a partir del cruce entre TAXONOMIA.md,
los docs 01-06 + 07, los glosarios en
`knowledge/categorias-violencia-genero-digital/glosario/`, los datos en
`data/tfm.db` y `data/tfm78valida.db`, y las auditorías
`docs/auditoria-categorizaciones-2026-07-12.md` y
`docs/auditoria-categorizaciones-2026-07-13.md`. Cualquier discrepancia
con esos documentos debe prevalecer sobre las recomendaciones aquí
expresadas.*
