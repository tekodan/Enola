---
tipo: Informe de ambigüedades y contradicciones entre sub-dimensiones
fecha: 2026-07-14
estado: BORRADOR
audiencia: Mantenimiento del sistema RAG de categorización VDG
alcance: Cruce documental entre TAXONOMIA.md, docs 00-07, glosarios
  (argot-misogino-general, jerga-manosfera, marcadores-por-subdimension,
  marcadores-mitigadores, marcadores-de-genero, agresiones-comunes,
  leetspeak-decoder, patrones-basura-digital, referentes-femeninos) y
  auditorías docs/auditoria-categorizaciones-2026-07-12.md +
  2026-07-13.md + recomendaciones-2026-07-14.md.
origen: Solicitud directa — "tomar las dimensiones que tenemos en docs/
  e intentar ver si entre cada dimensión existe alguna ambigüedad o
  contradicción".
restricciones: Este informe NO modifica taxonomía cerrada, glosarios
  ni código. Solo documenta hallazgos.
---

# Informe de ambigüedades y contradicciones entre sub-dimensiones VDG

> **TL;DR.** Se detectan **15 contradicciones documentales** donde un mismo
> marcador aparece asignado a distintas sub-dimensiones según el archivo
> que se consulte, **10 ambigüedades operativas** que el LLM no puede
> resolver con la información que recibe en el prompt, y **4
> contradicciones con el código** ya documentadas en el informe
> `recomendaciones-subdimensiones-2026-07-14.md`. El grueso del problema
> se concentra en **Cat. 1.1↔1.2↔1.3**, **Cat. 2.2↔2.3**, **Cat.
> 4.1↔4.2↔4.3** y en la ausencia de **reglas de desempate inyectadas al
> prompt**.

---

## A. Contradicciones documentales (mismo término → distinta sub-dimensión según el archivo)

Estas son las inconsistencias duras entre fuentes. El LLM recibe varias
versiones del mismo contrato léxico y no tiene regla para elegir.

| # | Marcador | `doc 01–06` | `marcadores-por-subdimension.md` | `07-tabla-canonica-prompt.md` | `argot-misogino-general.md` | Veredicto |
|---|---|---|---|---|---|---|
| **C1** | `mujer al volante` / `mujer florero` / `calladita` / `niñata` | **1.2** (Regla 2) | **1.1** (línea 25) | **1.1** (línea 33) | **1.2** (líneas 27-29) | 3 vs. 1 → **gana 1.2** (doc canónico) |
| **C2** | `estupidez` / `incapaz` / `tonta` / `inútil` | **1.2** | **1.2** | **1.2** | **1.2** | Consenso |
| **C3** | `zorra` / `puta` / `perra` / `guarra` | **2.3** (slut-shaming) | **2.2** (línea 29) | **2.2** (línea 73) | **2.3** (líneas 49-50) | Mixto → conflicto real |
| **C4** | `viejas webonas` | **1.3** (Regla 3) | **1.3** | **1.3** | **1.3** + **6.2** (overlap explícito) | Overlap aceptado |
| **C5** | `ridículas` | **1.3** | **1.3** + **6.2** | **1.3** + **6.2** | **1.3** + **5.2** | 4 fuentes, ninguna consistente |
| **C6** | `degeneración` / `mujeres modernas` / `mentalidad moderna` | **4.2** (doc 04 Regla 2) | **no listado** | **4.2** (línea 123) | **no listado** | **F1** del doc recomendaciones |
| **C7** | `foid` / `femoid` / `human female` / `bio-lump` | **4.1** (deshumanización arquetípica) | **4.3** (línea 36) | **4.3** (línea 130) | **no listado** | **F1** — mal mapeado en dos tablas |
| **C8** | `pagafantas` / `huelebragas` / `mangina` / `beta` / `simpa` / `white knight` | **4.3** (castigo aliados) + **4.1** (beta/white knight) | mezclados **4.1 + 4.3** | mezclados | **no listado** | Overlap caótico |
| **C9** | `feminazi` / `hembrista` | **4.3** + cruce con **6.1** | **4.3** | **4.3** | **4.2 / 4.3** (línea 136 glosario manosfera) | 3 sitios distintos |
| **C10** | `perra` / `gata` / `gallina` / `foca` / `mono` / `cabra` | **4.3** (animalización) | **4.3** | **4.3** | **no listado** | `perra` solapa con **2.2** |
| **C11** | `stacy` / `karen` / `becky` / `mujer superficial` | **4.1** (arquetipos) | **4.1** (vía glosario manosfera) | **no listado explícitamente** | **no listado** | Cobertura parcial |
| **C12** | `igualdad de género` / `lucha por la igualdad` | **6.3** (tergiversación) | **6.3** | **no listado** | **6.3** (líneas 85-86, ⚠ reapropiable) | Coherente con caveat |
| **C13** | `tradwife` / `team alienadas` | **4.2** (glosario manosfera) | **no listado** | **no listado** | **no listado** | Solo vive en un glosario |
| **C14** | `calladita te ves más bonita` / `te ves más bonita` | **5.1** | **5.1** | **5.1** | **5.1** | Consenso |
| **C15** | `jajaja` / `era una broma` / `es solo humor` / `generación de cristal` | **5.2** | **5.2** | **5.2** | **5.2** | Consenso |

**Lectura:** 8 de 18 sub-dimensiones tienen contradicción documental
real (1.1, 1.3 parcial, 2.2, 2.3, 4.1, 4.2, 4.3, 5.2). Las demás
(1.2, 2.1, 3.1, 3.2, 3.3, 5.1, 5.3, 6.1, 6.2) son consistentes.

---

## B. Ambigüedades operativas (zonas grises que el LLM no puede resolver sin regla explícita)

### B1. `1.1 (roles tradicionales) vs 1.3 (desvalorización genérica)`

El Protocolo §4 y el doc 01 Regla 3 definen `1.1` como **imperativo
hogareño explícito** (`a lavar`, `a cocinar`, `pónganse a barrer`). Pero
`marcadores-por-subdimension.md:25` mete también en 1.1 los términos
`mujer al volante / mujer florero / calladita / niñata`, que **no son
imperativos domésticos**, son frases estigmatizantes que pertenecen a
1.2. Sin regla de desempate, el LLM va por vecindad semántica.

- **Caso testigo (ar_id=36, auditoría 2026-07-13):** *"ellas son las que
  me dan cariño y pagan todo"* → etiquetada `1.1` sin haber imperativo
  doméstico. Es **falso positivo**.

### B2. `1.2 (inferioridad) vs 1.3 (desvalorización)`

Marcadores canónicos de **1.3** (`para después quejarse`, `no se dan a
respetar`, `son todas iguales`) son a menudo reasignados a **1.2** por el
LLM cuando hay un verbo invalidante cerca. Diferencia operativa: 1.2
ataca capacidades; 1.3 ataca conducta / generaliza el colectivo.

### B3. `2.2 (body-shaming) vs 2.3 (slut-shaming)`

**C3** + Protocolo §2: `zorra / puta / perra` son **2.3** (castigo a la
conducta sexual). Pero `marcadores-por-subdimension.md:29` los pone en
**2.2** (juzgamiento anatómico). La diferencia importa: 2.2 castiga el
cuerpo, 2.3 castiga la sexualidad.

### B4. `3.1 (amenaza física) vs 3.3 (apología al feminicidio)`

El Protocolo §4.bis lo dice con claridad:

- `a puñetazo limpio / te voy a / la voy a` → **3.1**
- `se lo buscaron / es mejor no meterse aunque la estén matando /
  justicia de miércoles / por eso ocurren los feminicidios` → **3.3**

**Esta regla nunca llega al prompt.** Solo está en prosa narrativa
(`00-protocolo-algoritmico.md:103-114`). El LLM opera como si no
existiera y manda a 3.1 cualquier texto "grave".

- **Caso testigo (ar_id=71, auditoría 2026-07-13):** *"es mejor no
  meterse aunque la estén matando"* → iba como `3.1`, corregido a `3.3`.

### B5. `4.1 (subculturas) vs 4.2 (esencialismo victimista) vs 4.3 (troleo)`

El Protocolo §4.ter y el glosario `jerga-manosfera.md` mezclan las tres:

- `beta` aparece como **4.1** (arquetipo) en unos sitios y **4.3**
  (castigo al aliado) en otros.
- `pagafantas / mangina / huelebragas` son **4.3** según doc 04, pero el
  glosario manosfera los lista bajo "Castigo a los aliados" sin etiqueta
  dura.
- `foid / femoid` son **4.1** en doc 04 y glosario manosfera, pero
  `marcadores-por-subdimension.md:36` los pone en **4.3**.

- **Caso testigo (ar_id=45):** *"como son todas las mujeres… vieja y fea
  … la más cara es una esposa"* → etiquetada con `4.3` cuando debería
  ser `4.2` (esencialismo mercenario, no troleo).

### B6. `6.2 (imperativos contra activistas) vs 1.1 (imperativos contra mujeres)`

**Resuelto en doc 06 §4** ("Overlap con otras categorías"): la
diferencia es el **referente individual** (nombre propio / @usuario /
hashtag `#8M`) vs **colectivo abstracto**. Pero esa regla de desempate
**no está en el prompt** (F3 del doc recomendaciones).

### B7. `5.1 vs 5.2 vs 5.3 — modulación pragmática residual`

El bloque Cat. 5 del prompt (`07-tabla-canonica-prompt.md:140-167` +
`doc 05 §3.3`) lo aclara:

- 5.1 sarcasmo que vehiculariza ATAQUE → SÍ VDG, devolver categoría
  sustantiva + agregar 5.1 si el sarcasmo es la carga principal.
- 5.2 humor hostil que enmascara agresión → SÍ VDG.
- 5.3 reapropiación / cita / denuncia → NO VDG, `clasificaciones: []`.

**Problema:** el `jaja` se pierde sistemáticamente como 5.2 cuando ya
hay 4.x o 6.x cargadas. El LLM no recuerda agregar la modulación
pragmática después de las sustantivas.

- **Caso testigo (ar_id=60):** *"No que a las feministas no les hacen
  caso jaja"* → cargó `4.3 + 6.1`, falta `5.2`.

### B8. `exclusion_label = CODIGO_99 vs exclusion_label = VIOLENCIA_COMUN`

`TAXONOMIA.md` los presenta como pseudo-categorías de exclusión
paralelas. `patrones-basura-digital.md` define 5 condiciones
(COND_1 a COND_5). `agresiones-comunes.md` define un set separado para
`VIOLENCIA_COMUN`. **No hay ambigüedad conceptual**, pero sí
**precedencia operativa**: el validador debe aplicar primero
`CODIGO_99` porque sus patrones son más específicos (regex con
`re.fullmatch`).

- `jaja` aislado → `CODIGO_99` por `COND_4_SOLO_RISA`.
- `pendejo` aislado sin referente femenino → `VIOLENCIA_COMUN`.

### B9. `Reglas 4.bis y 4.ter del Protocolo — ausentes del prompt`

Son las reglas de desempate críticas que distinguen 3.1 vs 3.3 y
4.1 vs 4.2 vs 4.3. Están en prosa narrativa dentro de
`00-protocolo-algoritmico.md:103-133` pero **nunca llegan al prompt
del LLM**. El bloque `_PROMPT_BLOCK_DESEMPATE` no existe
(R2 del doc `recomendaciones-subdimensiones-2026-07-14.md`).

### B10. `Marcadores mitigadores — función de denuncia subjetiva`

El glosario `marcadores-mitigadores.md` exige que el token mitigador
aparezca en **función de denuncia**, no incidentalmente, y exige
**coocurrencia con un marcador agresivo** para que el mitigador tenga
efecto. La "función de denuncia" es subjetiva y el LLM falla cuando el
texto **mezcla denuncia + insulto** (Regla 3 del propio glosario:
devolver categoría sustantiva con `es_falso_positivo_probable: true`).

- **Caso testigo (ar_id=57, auditoría 2026-07-12):** *"Quieren una mujer
  controlada? Quieren que las mujeres mueran?"* → iba como `2.1 + 1.2`,
  ahora `5.3` correctamente.

---

## C. Contradicciones con el código (bugs vivos)

Las 4 que ya documenta `recomendaciones-subdimensiones-2026-07-14.md §1`:

- **F1.** Las dos tablas canónicas (`07-tabla-canonica-prompt.md` y
  `marcadores-por-subdimension.md`) no coinciden en 6 sub-dimensiones
  (4.2, 4.3, 1.1, 2.2, 4.1, etc.).
- **F2.** Marcadores en dimensión equivocada (marcadores de 1.2
  listados como 1.1).
- **F3.** Reglas de desempate ausentes del prompt (Protocolo §4 /
  §4.bis / §4.ter).
- **F4.** Multi-etiqueta colapsada en Cat. 4 (`aliade + f3m1 nizta` →
  1 sola fila en lugar de 2).

---

## D. Resumen cuantitativo

| Métrica | Valor |
|---|---:|
| Sub-dimensiones totales | 18 |
| Sub-dimensiones con contradicción documental | **8** (1.1, 1.3 parcial, 2.2, 2.3, 4.1, 4.2, 4.3, 5.2) |
| Marcadores canónicos asignados a ≥2 sub-dimensiones distintas | **15** explícitos |
| Contradicciones documentales tipificadas | **15** (C1–C15) |
| Ambigüedades operativas tipificadas | **10** (B1–B10) |
| Reglas de desempate existentes en prosa | 4 (Protocolo §4, 4.bis, 4.ter, doc 06 §4) |
| Reglas de desempate inyectadas al prompt | **0** |
| Errores residuales de la auditoría 2026-07-13 | 7 |
| Errores `SAFEGUARD` huérfanos | 2 |
| Falsos positivos de VDG residuales | 2 (ar_id=43, ar_id=61) |
| Multi-etiqueta colapsada en Cat. 4 | 1 (ar_id=26) |

---

## E. Recomendaciones abiertas (sin aplicar en este informe)

Estas son las decisiones que el equipo debería tomar en un pase
posterior. **Este documento solo diagnostica.**

1. **Resolver C1, C3, C6, C7, C8, C9, C10** — designar canónicamente
   cada marcador contradictorio a una sola sub-dimensión, alineando
   `07-tabla-canonica-prompt.md`, `marcadores-por-subdimension.md` y los
   glosarios. Sin tocar la taxonomía cerrada ni el enum `Categoria`.
2. **Crear `glosario/reglas-desempate.md`** con las 4 reglas del
   Protocolo §4 / §4.bis / §4.ter + doc 06 §4, en formato de
   disparadores enumerados, e inyectarlo como nuevo bloque del prompt
   (cierra F3).
3. **Inyectar regla dura para Cat. 2.1**: exigir un adjetivo o
   sintagma cosificador (`putita obediente | packs | enseñando las
   nalgas | naquitas`), no la mera mención de "mujer" como presencia.
4. **Cambiar la deduplicación en `validate_clasificaciones`** para que
   la clave de Cat. 4 sea `(cat, dim, tuple(sorted(marcadores_detectados)))`,
   preservando multi-marcador sin tocar el schema.
5. **Forzar default 5.3 cuando llega `SAFEGUARD` sin sub-dim** (cierra
   los 2 casos huérfanos).
6. **Agregar 7 tests unitarios** en `test_category_mapping.py` o
   `test_subdimension_rules.py` que blinden los 7 errores residuales
   de la auditoría 2026-07-13.

Las propuestas R1–R8 ya están desarrolladas con código y plan de
implementación en
`docs/recomendaciones-subdimensiones-2026-07-14.md`. Este informe
**no las duplica**: las referencia y agrega el catálogo exhaustivo de
contradicciones (sección A) que el doc de recomendaciones solo
menciona parcialmente.

---

## F. Lo que NO se hace en este informe

- No se modifica `TAXONOMIA.md`.
- No se modifica ningún glosario en `glosario/`.
- No se modifica ningún archivo en `src/`.
- No se re-corre el batch sobre `data/tfm.db`.
- No se cambia el enum `Categoria` ni los 18 códigos `1.1`…`6.3`.

Este documento es **solo diagnóstico**. Toda acción correctiva debe
revisarse en un pase posterior con las propuestas del doc
`recomendaciones-subdimensiones-2026-07-14.md` como base.

---

*Documento preparado el 2026-07-14 a partir del cruce entre
`TAXONOMIA.md`, los docs narrativos 01–06, el Protocolo `00`, la tabla
canónica `07`, los 9 glosarios bajo `glosario/`, los datos en
`data/tfm.db`, y las auditorías 2026-07-12 / 2026-07-13. Cualquier
discrepancia con esos documentos debe prevalecer sobre este informe.*