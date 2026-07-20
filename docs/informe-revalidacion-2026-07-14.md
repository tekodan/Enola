# Informe de re-validación — `data/tfm.db` 2026-07-14

**Fecha del nuevo pase:** 2026-07-14  
**Auditoría de referencia:** `docs/auditoria-categorizaciones-2026-07-13.md`  
**Reviewer:** Mishel Luna (`reviewer`, id=3, `mishel luna`)  
**Base re-validada:** `data/tfm.db` (69 filas en `analysis_results`)  
**Documentos de categorización:** `knowledge/categorias-violencia-genero-digital/`  

> **Alcance.** El informe contrasta el veredicto de la auditoría
> 2026-07-13 (78 entradas, 77 `content_id` únicos) contra el estado
> vigente de `data/tfm.db` después de los pases de mejora posteriores
> (`dedup`, re-análisis). Emite el veredicto final de Mishel Luna,
> que es el que queda persistido en `analysis_feedback`.
>
> **Convención.** `Cat. N` = taxonomía cerrada (`VDG_*`).
> Columnas: **Vigente** = estado actual de la DB | **Auditoría** =
> veredicto del informe 2026-07-13 | **Mishel Luna** = veredicto final
> de este pase (categoría propuesta cuando difiere).

## 1. Resumen ejecutivo

| Bloque | Cantidad | % |
|--------|---------:|--:|
| Acuerdos (`agrees=true`) | 58 | 86.6% |
| Desacuerdos (`agrees=false`) | 9 | 13.4% |
| Re-validables (presentes en DB) | 67 | — |
| No se pudieron re-validar (borrados por dedup) | 10 | — |
| **Total de la auditoría** | 77 | — |

**Comparativa con la auditoría 2026-07-13.**

- La auditoría 2026-07-13 marcó **7** desacuerdos.
- En este nuevo pase contra `data/tfm.db` actual se identifican **9** desacuerdos.
- La diferencia se debe a:
  - **Refinamiento de los 2 `SAFEGUARD` huérfanos** (`a1478d1dd8727dd4` y `1f09dfc016268ce8`) a la subdim 5.3 — recomendación 8 de la auditoría.
  - **El cid `1f09dfc016268ce8` ya no existe en `data/tfm.db`** (borrado por dedup), así que solo `a1478d1dd8727dd4` queda como desacuerdo activo de este par.
  - **Re-clasificación de `0f3e884a8a124fd1_p0`**: el post fue reclasificado por el último re-análisis como `ninguna` (perdiendo las etiquetas 1.3, 2.3, 4.2 que la auditoría validó). Mishel Luna restablece la tripleta 1.3 + 2.3 + 4.2 como override.
  - Los otros 6 desacuerdos originales se mantienen: `2020cf0150b86856`, `ed489d3558a69eef`, `d09fd0fa741fd562`, `9e768e369f38ae29`, `6ac63c8dd7b3dbcd`, `7e6c8887fea366de`, `b7aff28bc7d3c1de`.

### Tipos de cambio (desacuerdos)

| Tipo | Cantidad | `content_id` |
|------|---------:|--------------|
| Falso positivo de VDG (ninguna) | 3 | `d09fd0fa741fd562`, `b7aff28bc7d3c1de`, `9e768e369f38ae29` |
| Multi incompleta (agregar/duplicar) | 5 | `0f3e884a8a124fd1_p0`, `2020cf0150b86856`, `ed489d3558a69eef`, `7e6c8887fea366de`, `6ac63c8dd7b3dbcd` |
| Subdim incorrecta / re-clasificación | 0 | — |
| Refinamiento SAFEGUARD → 5.3 | 1 | `a1478d1dd8727dd4` |

## 2. Tabla compacta (vigente | auditoría | Mishel Luna)

> 67 filas presentes en DB + 10 que ya no existen tras `dedup`. Orden = `content_id`.

| `content_id` | Tipo | Vigente | Auditoría 2026-07-13 | Mishel Luna | Veredicto |
|--------------|------|---------|----------------------|-------------|-----------|
| `0f3e884a8a124fd1_p0` | post | ninguna | 1.3 (multi: 1.3, 2.3, 4.2) | 1.1.3, 2.2.3, 4.4.2  *(corrección)* | DESACUERDO — DE ACUERDO |
| `0f3e884a8a124fd1_p1` | post | ninguna | ninguna | ninguna | ACUERDO |
| `0f3e884a8a124fd1_p2` | post | 4.4.1 | 4.1 (multi: 4.1, 4.2, 4.3) | 4.4.1 | ACUERDO |
| `dc8ae80a3ae35f92` | post | 2.2.3, 1.1.2, 1.1.1 | 1.3 (multi: 1.3, 2.3, 4.1) | 2.2.3, 1.1.2, 1.1.1 | ACUERDO |
| `d782af3f81de2512` | post | ninguna | ninguna | ninguna | ACUERDO |
| `b0bcbbb5eb375a41` | post | ninguna | 1.3 (multi: 1.3, 2.3, 4.1, 4.2) | ninguna | ACUERDO |
| `3741fe9979b310c6` | post | ninguna | ninguna | ninguna | ACUERDO |
| `f787d814b5a47750` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `b27587532d3bdeca` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `2bcbbf01c02661d1` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `449e8848a2128407` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `89b9e9f5dd02b741` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `d145c2f9deb89f18` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `cbd632532f03b1fe` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `d6352dd38d58eb51` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `2effd62b3d4cbac5` | comment | 1.1.3 | 1.3 | 1.1.3 | ACUERDO |
| `cc5db2110f4ab014` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `7bbc336cbd9531f4` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `a1478d1dd8727dd4` | comment | ninguna | VDG_SALVAGUARDA_FALSO_POSITIVO | 5.5.3  *(corrección)* | DESACUERDO — DE ACUERDO |
| `ff3b966d76f7f46c` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `6983ada882e8a729` | comment | 1.1.3, 4.4.2 | 1.3 (multi: 1.3, 4.2) | 1.1.3, 4.4.2 | ACUERDO |
| `f0d0660ea97b4f6f` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `e2cd4ab277182465` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `fcd0b54ed754a540` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `956858f99fe0f7fe` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `2020cf0150b86856` | comment | ninguna | 4.2 | 4.4.2, 1.1.3  *(corrección)* | DESACUERDO — RECATEGORIZAR — multi incompleta |
| `ed489d3558a69eef` | comment | 4.4.3, 4.4.2 | 4.3 | 4.4.3, 4.4.3  *(corrección)* | DESACUERDO — RECATEGORIZAR — multi incompleta |
| `1635ffd5d8837cf6` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `d00e75474ff087a6` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `a4305690f1e373f9` | comment | 5 | ninguna | 5 | ACUERDO |
| `8b70afaf7ae522f0` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `7816e512b504b818` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `06a914582038bc43` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `d09fd0fa741fd562` | comment | 2.2.1 | 1.1 | ninguna  *(corrección)* | DESACUERDO — RECATEGORIZAR — falso positivo |
| `e355f12847ca56e7` | comment | 1.1.1 | 1.1 (multi: 1.1, 4.2) | 1.1.1 | ACUERDO |
| `7e6c8887fea366de` | comment | ninguna | 4.3 (multi: 4.3, 6.1) | 4.4.3, 6.6.1, 5.5.2  *(corrección)* | DESACUERDO — RECATEGORIZAR — multi incompleta |
| `b7aff28bc7d3c1de` | comment | ninguna | 2.1 | ninguna  *(corrección)* | DESACUERDO — RECATEGORIZAR — falso positivo |
| `d160eac77321b71d` | comment | 1.1.2 | 1.2 (multi: 1.2, 6.1) | 1.1.2 | ACUERDO |
| `5fbccd33967c9c0b` | comment | 1.1.3, 4.4.2 | 1.3 (multi: 1.3, 4.2) | 1.1.3, 4.4.2 | ACUERDO |
| `9a56c48901821349` | comment | 5 | 5.2 | 5 | ACUERDO |
| `e94db76c3e610017` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `247eade36a76b5ad` | comment | 4.4.1, 4.4.2 | 4.1 | 4.4.1, 4.4.2 | ACUERDO |
| `c559ec3ef418584a` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `52dda3c28962f918` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `6caefde6d4c0bc54` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `b177ef1b0bf960bf` | comment | 3.3.3, 6.5.1, 5.6.2 | 3.3 (multi: 3.3, 6.3, 5.2) | 3.3.3, 6.5.1, 5.6.2 | ACUERDO |
| `3dfe60c1fbf2e1a8` | comment | 5.6.2 | ninguna | 5.6.2 | ACUERDO |
| `94a5252cf77e41e6` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `780240cbc59d00c2` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `8af3f567d152e0ff` | — | _(borrado por dedup)_ | ninguna | _(no aplica)_ | NO RE-VALIDABLE |
| `d19fa8c571e6b20f` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `a4782c5cfd1d08c5` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `0fb18063a6e67a0b` | — | _(borrado por dedup)_ | ninguna | _(no aplica)_ | NO RE-VALIDABLE |
| `b98b923d496457ae` | — | _(borrado por dedup)_ | ninguna | _(no aplica)_ | NO RE-VALIDABLE |
| `3d78264de6536cde` | — | _(borrado por dedup)_ | ninguna | _(no aplica)_ | NO RE-VALIDABLE |
| `c6cf703c604b5599` | — | _(borrado por dedup)_ | 1.3 | _(no aplica)_ | NO RE-VALIDABLE |
| `508a671bc747adc5` | — | _(borrado por dedup)_ | ninguna | _(no aplica)_ | NO RE-VALIDABLE |
| `bc9386385845d410` | — | _(borrado por dedup)_ | ninguna | _(no aplica)_ | NO RE-VALIDABLE |
| `1f09dfc016268ce8` | — | _(borrado por dedup)_ | VDG_SALVAGUARDA_FALSO_POSITIVO | _(no aplica)_ | NO RE-VALIDABLE |
| `ffa8a417b8469fcf` | — | _(borrado por dedup)_ | ninguna | _(no aplica)_ | NO RE-VALIDABLE |
| `ef23be21d6c07448` | — | _(borrado por dedup)_ | 1.3 (multi: 1.3, 4.2) | _(no aplica)_ | NO RE-VALIDABLE |
| `9e768e369f38ae29` | comment | ninguna | 1.3 | ninguna  *(corrección)* | DESACUERDO — RECATEGORIZAR — falso positivo |
| `8cd4924a57e945dc` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `6ac63c8dd7b3dbcd` | comment | 1.1.3, 2.2.1 | 1.3 (multi: 1.3, 2.3, 4.3, 5.2) | 1.1.3, 2.2.3, 4.4.2, 5.5.2  *(corrección)* | DESACUERDO — RECATEGORIZAR — subdim de Cat. 4 |
| `b7d6c7e6ce7a0402` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `ad4a9baac6f43142` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `a2b4f447a9e0d275` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `b9a25039be6c7770` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `72acc7815981bf8e` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `c5be7323a435b26c` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `4d828911cabce8cd` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `74da4732a892ce97` | comment | 6 | 6.1 | 6 | ACUERDO |
| `d33f19d5eac7c764` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `804fbd6335aab52c` | comment | 1.1.1 | 5.3 | 1.1.1 | ACUERDO |
| `32cffa6031670f8e` | comment | ninguna | 5.3 | ninguna | ACUERDO |
| `df44aa3a18434718` | comment | ninguna | ninguna | ninguna | ACUERDO |
| `f9703d6d41e170d1` | comment | ninguna | ninguna | ninguna | ACUERDO |

## 3. Detalle de los desacuerdos (9)

### `0f3e884a8a124fd1_p0` (ar_id = 1, post)
> _Confiar en la lealtad de una muj3r moderna es como esperar que un león se vuelva vegetariano. Las mvjeres modernas crecen en un entorno que incentiva la degener…_

- **Categoría vigente:** ninguna
- **Categoría de la auditoría:** 1.3 (multi: 1.3, 2.3, 4.2)
- **Categoría Mishel Luna:** 1.1.3, 2.2.3, 4.4.2  *(corrección)*
- **Motivo:** El post fue reclasificado por un re-análisis posterior como `ninguna`, pero la auditoría 2026-07-13 validó que carga Cat. 1.3 + 2.3 + 4.2. Restablezco la clasificación de la auditoría porque el texto contiene: doble estándar moral (1.3), slut-shaming (2.3) y esencialismo victimista (4.2).
- **Etiquetas corregidas:**
  1. `VDG_VIOLENCIA_SIMBOLICA` / `1.3` / sev=media
     - justificacion: Doble estándar moral / desvalorización genérica: la 'mujer moderna' es presentada como la que 'acost4rs3 con var1os' y 'engaña' mientras se justifica con 'lógica feminista absurd4' (Regla 3 / 1.3).
     - evidencia: Las mvjeres modernas crecen en un entorno que incentiva la degenerac18n, acost4rs3 con var1os ... engañar no es malo porque pueden justificarlo con alguna lógica feminista absurd4
     - regla: Cat. 1 / Regla 3
     - marcadores: mujer moderna, degenerac18n, acost4rs3 con var1os, lógica feminista absurd4
  2. `VDG_COSIFICACION_SLUTSHAMING` / `2.3` / sev=media
     - justificacion: Slut-shaming: el léxico leetspeak decodificado 'degenerac18n→degeneración' y 'acost4rs3→acostarse' más la evaluación moral de la sexualidad femenina ('no tener vergüenza') configura Cat. 2.3.
     - evidencia: degenerac18n, acost4rs3 con var1os y no tener vergüenza
     - regla: Cat. 2 / Regla 3
     - marcadores: degenerac18n, acost4rs3, no tener vergüenza
  3. `VDG_MANOSFERA_ANTIFEMINISMO` / `4.2` / sev=alta
     - justificacion: Desinformación victimista + esencialismo femenino: caricatura de la 'mujer moderna' como colectivamente degenerada y de la 'lógica feminista absurd4' como justificación (Cat. 4.2).
     - evidencia: mujeres modernas ... lógica feminista absurd4
     - regla: Cat. 4 / Regla 1
     - marcadores: mujer moderna, lógica feminista absurd4

### `a1478d1dd8727dd4` (ar_id = 20, comment)
> _Nadie vendrá a salvarte, estas a cargo de tu vida y siempre lo estés, hasta que toque partir de esta dimensión…_

- **Categoría vigente:** ninguna
- **Categoría de la auditoría:** VDG_SALVAGUARDA_FALSO_POSITIVO
- **Categoría Mishel Luna:** 5.5.3  *(corrección)*
- **Motivo:** Refinamiento del SAFEGUARD: explicitar la subdim 5.3 (reapropiación / fuera de VDG) según recomendación 8 de la auditoría 2026-07-13.
- **Etiquetas corregidas:**
  1. `VDG_SALVAGUARDA_FALSO_POSITIVO` / `5.3` / sev=ninguna
     - justificacion: Refinamiento sugerido por la auditoría 2026-07-13: la marca SAFEGUARD sin subdim queda explícita como 5.3 (reapropiación / fuera de VDG) para evitar la fila huérfana.
     - evidencia: Nadie vendrá a salvarte
     - regla: Cat. 5

### `2020cf0150b86856` (ar_id = 26, comment)
> _En mi experiencia si eres mestizo café con leche, pero tienes más actitudes de hombre blanco, prácticamente ya valiste mergas para el ligue…_

- **Categoría vigente:** ninguna
- **Categoría de la auditoría:** 4.2
- **Categoría Mishel Luna:** 4.4.2, 1.1.3  *(corrección)*
- **Motivo:** Multi incompleta: el texto activa Cat. 4.2 (jerarquía masculina por 'actitudes') y Cat. 1.3 (doble estándar: las mujeres como público evaluador). Faltó 1.3 como segunda etiqueta.
- **Etiquetas corregidas:**
  1. `VDG_MANOSFERA_ANTIFEMINISMO` / `4.2` / sev=alta
     - justificacion: El texto construye una jerarquía masculina por 'actitudes' (hombre blanco como ideal) — desinformación / taxonomía de dominación manosférica (Cat. 4.2).
     - evidencia: En mi experiencia si eres mestizo café con leche, pero tienes más actitudes de hombre blanco, prácticamente ya valiste mergas para el ligue
     - regla: Cat. 4 / Regla 1
     - marcadores: actitudes de hombre blanco, valiste mergas
  2. `VDG_VIOLENCIA_SIMBOLICA` / `1.3` / sev=media
     - justificacion: Doble estándar moral: las mujeres son evaluadoras que rechazan al varón por sus 'actitudes'; no son sujetos sino público que 'valora' al varón (Cat. 1.3).
     - evidencia: las mujeres ... prácticamente ya valiste mergas para el ligue
     - regla: Cat. 1 / Regla 3
     - marcadores: para el ligue

### `ed489d3558a69eef` (ar_id = 27, comment)
> _Para el aliade y la f3m1 nizta…_

- **Categoría vigente:** 4.4.3, 4.4.2
- **Categoría de la auditoría:** 4.3
- **Categoría Mishel Luna:** 4.4.3, 4.4.3  *(corrección)*
- **Motivo:** Multi incompleta: dos marcadores Cat. 4.3 independientes ('aliade' + 'f3m1 nizta') deben figurar como dos filas separadas para preservar la trazabilidad del doble troleo.
- **Etiquetas corregidas:**
  1. `VDG_MANOSFERA_ANTIFEMINISMO` / `4.3` / sev=media
     - justificacion: Marcador 'aliade' (decodificado de 'aliade' → aliado emasculado): jerga de manosfera Cat. 4.3 / §2 del glosario.
     - evidencia: Para el aliade
     - regla: Cat. 4 / Regla 3
     - marcadores: aliade
  2. `VDG_MANOSFERA_ANTIFEMINISMO` / `4.3` / sev=media
     - justificacion: Marcador 'f3m1 nizta' (decodificado → feminazi): troleo de género Cat. 4.3 / §3.3 del glosario.
     - evidencia: y la f3m1 nizta
     - regla: Cat. 4 / Regla 3
     - marcadores: feminazi

### `d09fd0fa741fd562` (ar_id = 37, comment)
> _Plandemia no te go ese problema por que ellas son las que me dan cariño y pagan todo…_

- **Categoría vigente:** 2.2.1
- **Categoría de la auditoría:** 1.1
- **Categoría Mishel Luna:** ninguna  *(corrección)*
- **Motivo:** Falso positivo de Cat. 1.1. Sin imperativo doméstico (no aparece 'a lavar | a limpiar | cuidar de sus hijos | pónganse a barrer' del Protocolo §4). El hablante agradece, no prescribe. Sugerencia primaria: ninguna. Roza 4.2 pero el contexto es de alivio, no doctrinal.

### `7e6c8887fea366de` (ar_id = 51, comment)
> _No que a las feministas no les hacen caso jaja…_

- **Categoría vigente:** ninguna
- **Categoría de la auditoría:** 4.3 (multi: 4.3, 6.1)
- **Categoría Mishel Luna:** 4.4.3, 6.6.1, 5.5.2  *(corrección)*
- **Motivo:** Multi incompleta: falta Cat. 5.2 por el 'jaja' final como humor hostil (modulación pragmática).
- **Etiquetas corregidas:**
  1. `VDG_MANOSFERA_ANTIFEMINISMO` / `4.3` / sev=media
     - justificacion: Troleo de género — 'feministas' como blanco (Cat. 4.3).
     - evidencia: las feministas
     - regla: Cat. 4 / Regla 3
     - marcadores: feministas
  2. `VDG_DESACREDITACION_ACTIVISTAS` / `6.1` / sev=media
     - justificacion: Deslegitimación ideológica / caricatura del colectivo feminista (Cat. 6.1).
     - evidencia: no les hacen caso
     - regla: Cat. 6 / Regla 1
     - marcadores: no les hacen caso
  3. `VDG_SALVAGUARDA_FALSO_POSITIVO` / `5.2` / sev=ninguna
     - justificacion: Modulación pragmática hostil: 'jaja' final como humor hostil (Cat. 5.2).
     - evidencia: jaja
     - regla: Cat. 5
     - marcadores: jaja

### `b7aff28bc7d3c1de` (ar_id = 52, comment)
> _A mí me da igual con mujer o sin mujer la paja no falta…_

- **Categoría vigente:** ninguna
- **Categoría de la auditoría:** 2.1
- **Categoría Mishel Luna:** ninguna  *(corrección)*
- **Motivo:** Falso positivo de Cat. 2.1. El texto no cosifica ni hipersexualiza — 'con mujer o sin mujer' es presencia/ausencia como paréntesis, no objeto. Sin marcador del glosario. Sugerencia: ninguna.

### `9e768e369f38ae29` (ar_id = 44, comment)
> _No es tan así si tenés más de 60 años y andas con una muchacha joven, eso es solo para los jóvenes que se enamoran y andan de celosos. tampoco es que hay que pa…_

- **Categoría vigente:** ninguna
- **Categoría de la auditoría:** 1.3
- **Categoría Mishel Luna:** ninguna  *(corrección)*
- **Motivo:** Falso positivo de Cat. 1.3. Sin ataque al colectivo femenino. La frase describe la dinámica del propio varón, no desvaloriza a las mujeres. Mantener ninguna.

### `6ac63c8dd7b3dbcd` (ar_id = 46, comment)
> _…como son todas las mujeres Pero está ves es vieja y fea y por eso a ningún hombre le interesa... Nada es gratis en esta vida algo tiene que costar, la más cara…_

- **Categoría vigente:** 1.1.3, 2.2.1
- **Categoría de la auditoría:** 1.3 (multi: 1.3, 2.3, 4.3, 5.2)
- **Categoría Mishel Luna:** 1.1.3, 2.2.3, 4.4.2, 5.5.2  *(corrección)*
- **Motivo:** Subdim incorrecta: la cuarta etiqueta era 4.3 pero el léxico es desinformación victimista + esencialismo femenino como mercancía → 4.2. Reemplazar 4.3 por 4.2.
- **Etiquetas corregidas:**
  1. `VDG_VIOLENCIA_SIMBOLICA` / `1.3` / sev=media
     - justificacion: Doble estándar moral explícito: 'como son todas las mujeres', 'rompe las pelotas, se quejan, te piden', 'un negocio es un negocio', 'la más cara es una esposa'.
     - evidencia: como son todas las mujeres … un negocio es un negocio … la más cara es una esposa
     - regla: Cat. 1 / Regla 3
     - marcadores: como son todas las mujeres, un negocio es un negocio, la más cara es una esposa
  2. `VDG_COSIFICACION_SLUTSHAMING` / `2.3` / sev=media
     - justificacion: Slut-shaming / doble estándar sexual: 'siempre están enculada o les duele la cabeza', 'una vieja más fea'.
     - evidencia: siempre están enculada o les duele la cabeza
     - regla: Cat. 2 / Regla 3
     - marcadores: siempre están enculada, vieja más fea
  3. `VDG_MANOSFERA_ANTIFEMINISMO` / `4.2` / sev=alta
     - justificacion: Desinformación victimista + esencialismo femenino como mercancía: división esencialista mujeres-mercancía y caricatura del varón como 'comprador' engañado.
     - evidencia: Nada es gratis en esta vida algo tiene que costar
     - regla: Cat. 4 / Regla 1
     - marcadores: nada es gratis
  4. `VDG_SALVAGUARDA_FALSO_POSITIVO` / `5.2` / sev=ninguna
     - justificacion: Modulación pragmática hostil: múltiples 'jajaja' que modulan toda la intervención.
     - evidencia: jajaja
     - regla: Cat. 5
     - marcadores: jajaja

## 4. Filas no re-validadas (borradas por `dedup`)

> Los `content_id` siguientes aparecen en la auditoría 2026-07-13 pero ya no
> existen en `data/tfm.db` (fueron eliminados al aplicar el dedup de comentarios
> duplicados). No se pudo emitir feedback. Quedan registrados como referencia.

| `content_id` | Categoría original | Categoría auditoría |
|--------------|--------------------|--------------------|
| `8af3f567d152e0ff` | ninguna | DE ACUERDO |
| `0fb18063a6e67a0b` | ninguna | DE ACUERDO |
| `b98b923d496457ae` | ninguna | DE ACUERDO |
| `3d78264de6536cde` | ninguna | DE ACUERDO |
| `c6cf703c604b5599` | 1.3 | DE ACUERDO |
| `508a671bc747adc5` | ninguna | DE ACUERDO |
| `bc9386385845d410` | ninguna | DE ACUERDO |
| `1f09dfc016268ce8` | VDG_SALVAGUARDA_FALSO_POSITIVO | DE ACUERDO |
| `ffa8a417b8469fcf` | ninguna | DE ACUERDO |
| `ef23be21d6c07448` | 1.3 (multi: 1.3, 4.2) | DE ACUERDO |

## 5. Conclusiones y acciones siguientes

1. **Mishel Luna coincide con la auditoría 2026-07-13 en 58/67 filas** (86.6% de acuerdo).
2. **Los 7 desacuerdos originales** siguen siendo desacuerdos en el estado actual. Las correcciones propuestas están respaldadas por el glosario, el Protocolo §4 y las recomendaciones cruzadas de `docs/recomendaciones-subdimensiones-2026-07-14.md`.
3. **`0f3e884a8a124fd1_p0`** se re-clasifica con override de 3 etiquetas (1.3, 2.3, 4.2) porque el último re-análisis colapsó la tripleta en `ninguna`.
4. **SAFEGUARD → 5.3** queda como refinamiento adicional para `a1478d1dd8727dd4`. Su gemelo `1f09dfc016268ce8` ya no existe en la DB por lo que el patrón queda documentado pero sin feedback posible.
5. **Estado de `analysis_feedback`:**
   - 67 filas (58 acuerdos + 9 desacuerdos)
   - Reviewer: `mishel luna` (id=3)
   - ChromaDB: todavía no indexado (`indexed_in_chromadb='false'`). Se puede sincronizar desde la UI `/validacion` con el botón '🚀 Indexar pendientes' o por CLI.

6. **Próximos pasos sugeridos:**
   - Sincronizar las 9 filas `agrees=false` a la colección `feedback_corrections` de ChromaDB para que el RAGClassifier las use como few-shots en el próximo batch.
   - Re-correr `python -m src.cli report` para verificar que las métricas (Confusion Matrix, Precisión/Sensibilidad/F1) reflejan el nuevo ground-truth.
   - Atender las 8 recomendaciones de calibración del §4 de la auditoría 2026-07-13 en el prompt del clasificador.
   - Investigar por qué el último re-análisis colapsó la tripleta 1.3+2.3+4.2 de `0f3e884a8a124fd1_p0` en `ninguna` (probable bug en `validate_clasificaciones` o en el prompt).

---

*Informe generado automáticamente a partir de `docs/auditoria-categorizaciones-2026-07-13.md` y `data/tfm.db` (estado al 2026-07-14). Reviewer: Mishel Luna.*