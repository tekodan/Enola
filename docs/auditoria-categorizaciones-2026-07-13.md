# Auditoría de categorizaciones — `data/tfm.db` (segundo proceso)

**Fecha de revisión:** 2026-07-13
**Alcance:** 78 filas de `analysis_results` (25 con etiquetas VDG en `analysis_labels`).
**Documentos de referencia:** `knowledge/categorias-violencia-genero-digital/` (00-protocolo + cat. 1–6 + glosarios).

> **Identificador usado en esta auditoría.** Igual que en la auditoría 2026-07-12, se usa **`content_id`** como clave primaria localizable desde la página `/validacion` de NiceGUI. El `id` numérico de `analysis_results` se conserva entre paréntesis `(ar_id = N)` para auditoría técnica.

> **Convención de etiquetas.** Misma convención que la auditoría previa: `Cat. 1` = Violencia simbólica · `Cat. 2` = Cosificación / slut-shaming · `Cat. 3` = Hostilidad y apología al feminicidio · `Cat. 4` = Manosfera / antifeminismo · `Cat. 5` = Salvaguarda, sarcasmo y falsos positivos · `Cat. 6` = Desacreditación de activistas. La `Regla de exclusión de violencia común` se aplica como filtro previo.

> **Comparativa con la auditoría 2026-07-12.** Este proceso ya incorpora la mayoría de las correcciones del primer informe (multi-etiqueta vía tabla lateral `analysis_labels`, decodificación de leetspeak `aliade`/`f3m1 nizta`, reclasificación de falsos positivos `a1478d1dd8727dd4`, `1f09dfc016268ce8`, `52dda3c28962f918`, `94a5252cf77e41e6`, reclasificación de falsos negativos `e355f12847ca56e7`, `7e6c8887fea366de`, `d160eac77321b71d`, `5fbccd33967c9c0b`, recategorización de `b177ef1b0bf960bf` a 3.3 y de `6ac63c8dd7b3dbcd` a 1.3). El presente documento audita el **nuevo estado** e identifica los errores residuales.

---

## 1. Resumen ejecutivo

| Bloque | Cantidad | % |
|--------|---------:|---:|
| Categorizaciones con las que **estoy de acuerdo** | 71 | 91 % |
| Categorizaciones que **recategorizaría** (acuerdo parcial / corrección) | 7 | 9 % |
| Categorizaciones que considero **erróneas** (falso positivo de VDG) | 0 | 0 % |
| Categorizaciones que considero **incompletas** (falta etiqueta) | 2 | — |
| **Total auditado** | **78** | **100 %** |

**Evaluación global.** El nuevo proceso corrige prácticamente todos los errores graves del primero. Los falsos positivos `a1478d1dd8727dd4`, `1f09dfc016268ce8`, `52dda3c28962f918` y `94a5252cf77e41e6` ahora se marcan `SAFEGUARD` o `ninguna`; los falsos negativos `e355f12847ca56e7`, `7e6c8887fea366de`, `d160eac77321b71d` y `5fbccd33967c9c0b` ahora disparan Cat. 1 / Cat. 4 / Cat. 6; el caso emblemático de apología al feminicidio (`b177ef1b0bf960bf`) ahora se clasifica correctamente como **3.3** y no como 3.1; y el comentario `6ac63c8dd7b3dbcd` deja Cat. 3 (incorrecta) y pasa a **1.3** con multi-etiqueta.

**Errores residuales detectados** (ordenados por gravedad):

1. **`b7aff28bc7d3c1de` — falso positivo de Cat. 2.1.** "A mí me da igual con mujer o sin mujer la paja no falta" → no cosifica ni hipersexualiza; es un comentario coloquial vulgar sin marcador VDG. Debe ser `ninguna`.
2. **`6ac63c8dd7b3dbcd` — Cat. 4.3 donde corresponde Cat. 4.2.** El texto del varón de 67 años desvaloriza y cosifica mujeres con léxico mercenario ("un negocio es un negocio", "la más cara es una esposa", "como son todas las mujeres") — eso es desinformación victimista (4.2), no troleo de género (4.3). Falta también 4.2 en el set multi-etiqueta.
3. **`9e768e369f38ae29` — falso positivo de Cat. 1.3.** "No es tan así si tenés más de 60 años y andas con una muchacha joven..." — sin desvalorización genérica del colectivo femenino, es respuesta matizada al comentario anterior sobre el "plan A". Debe ser `ninguna`.
4. **`d09fd0fa741fd562` — falso positivo de Cat. 1.1.** "ellas son las que me dan cariño y pagan todo" — sin imperativo doméstico; el hablante agradece a las mujeres, no prescribe roles. La generalización esencialista roza Cat. 4.2 pero el contexto es de *alivio*, no de ataque. Sugerencia: `ninguna` (o `4.2` baja si se quiere registrar el esencialismo).
5. **`2020cf0150b86856` — multi-etiqueta incompleta.** El texto sobre "actitudes de hombre blanco" merece `4.2` + `1.3` (doble estándar: las mujeres valoran al varón por sus actitudes como objeto a "valuar"). Hoy solo carga `4.2`.
6. **`ed489d3558a69eef` — multi-etiqueta incompleta.** "Para el aliade y la f3m1 nizta" tiene **dos** marcadores Cat. 4.3 independientes (`aliade` → aliado emasculado; `f3m1 nizta` → feminazi). El primario carga solo una entrada 4.3 — debería ser 4.3 × 2 para preservar la trazabilidad del doble troleo.
7. **`7e6c8887fea366de` — falta Cat. 5.2.** El "jaja" final es humor hostil y debería figurar como tercera etiqueta junto al `4.3` + `6.1` ya asignados.

**Patrones de acierto del nuevo proceso:**

- El **decodificador de leetspeak** ya se aplica correctamente: `degenerac18n → degeneración`, `acost4rs3 → acostarse`, `aliade → aliado`, `f3m1 nizta → feminazi`, `cog13nd8 → cogiendo`, `c8g1d8 → cogida`, `f8ll4nd8 → follando`, `GvS4N8 → Gusano`, `1nútil → inútil`. Se ve aplicado en todas las justificaciones.
- La **regla 1.1 vs 1.3** ya no se confunde masivamente: posts como `0f3e884a8a124fd1_p0/p2` y `dc8ae80a3ae35f92`, `b0bcbbb5eb375a41` ahora se etiquetan correctamente con 1.3 cuando no hay imperativo doméstico.
- **Cat. 4 (manosfera)** se aplica correctamente a `2020cf0150b86856` (4.2), `ed489d3558a69eef` (4.3), `247eade36a76b5ad` (4.1).
- **Cat. 6 (desacreditación)** se aplica correctamente a `74da4732a892ce97` (6.1) y como complemento en `7e6c8887fea366de` y `d160eac77321b71d`.
- **Cat. 5 (salvaguarda)** diferencia ahora 5.3 (`804fbd6335aab52c`, `32cffa6031670f8e`) de 5.2 (`9a56c48901821349`) y de la marca genérica `SAFEGUARD` sin subdim (`a1478d1dd8727dd4`, `1f09dfc016268ce8`).
- **Regla de exclusión de violencia común** se aplica correctamente a `3dfe60c1fbf2e1a8` (sin referente femenino + comentario vulgar) — `exclusion_label = VIOLENCIA_COMUN`.

---

## 2. Auditoría por `content_id`

Formato de cada entrada:

```
content_id — fragmento representativo (tipo, ar_id = N)
Categoría actual → Categoría(s) propuesta(s)
[VEREDICTO] justificación corta basada en el/los doc(s) de categorización.
```

### 2.1. Posts

**`0f3e884a8a124fd1_p0`** — *"Confiar en la lealtad de una muj3r moderna es como esperar que un león se vuelva vegetariano. Las mvjeres modernas crecen en un entorno que incentiva la degenerac18n, acost4rs3 con var1os y no tener vergüenza. Para ellas, engañar no es malo porque pueden justificarlo con alguna lógica feminista absurd4."* (post, `ar_id = 1`)
- Actual: `1.3` (multi: `1.3, 2.3, 4.2`).
- **[DE ACUERDO]** El texto no contiene imperativo doméstico (no aplica 1.1) y activa la **Regla 3 / 1.3** por inversión de responsabilidad ("engañar no es malo porque pueden justificarlo"). El léxico leetspeak decodificado `degenerac18n → degeneración`, `acost4rs3 → acostarse` configura **slut-shaming (Cat. 2.3)**. El esencialismo "mujer moderna" + victimismo hegemónico es **4.2**. Se podría discutir agregar `4.3` por la caricatura de "lógica feminista absurd4", pero la dominante sigue siendo 4.2.

**`0f3e884a8a124fd1_p1`** — *"La forma más fácil de hacer las cosas es seguir una lista de tareas…"* (post, `ar_id = 2`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino, sin marcadores VDG.

**`0f3e884a8a124fd1_p2`** — *"El beta se entera o sospecha que ella está hablando con otro, que se está viendo con alguien más o que directamente lo está engañando… El del 1% corta antes de que lo terminen de destruir por completo. Si quieres dejar de tolerar traiciones por miedo a estar solo y recuperar tu autoestima, obtén el programa El Fin del Chico Bueno…"* (post, `ar_id = 3`)
- Actual: `4.1` (multi: `4.1, 4.2, 4.3`).
- **[DE ACUERDO con observación]** Las tres sub-dimensiones 4.x son correctas: el arquetipo `beta` vs `del 1%` es **4.1** (subculturas masculinistas / taxonomías), la narrativa "mujer engaña por naturaleza / pierdes tu dignidad si te quedas" es **4.2** (desinformación victimista + esencialismo), y la propaganda misma del manual `El Fin del Chico Bueno` se vende como doctrina de la subcultura (4.3 si se considera como arenga). Sin embargo, el texto carga también un componente de **doble estándar moral (1.3)** al presentar a la mujer como manipuladora interesada ("sabe que él lo va a tolerar… ella sigue haciendo lo que le da la gana") que hoy no queda etiquetado. Sugerencia opcional: añadir `1.3` como cuarta etiqueta. Acepto la priorización 4.1.

**`dc8ae80a3ae35f92`** — *"Ella te vende la imagen de la chica buena, correcta, que 'no es f4cil'… Su actuación es tan buena que parece real. … El beta que se cree la actuación termina esperando… y muchas veces ni siquiera se la termina cog13nd8."* (post, `ar_id = 4`)
- Actual: `1.3` (multi: `1.3, 2.3, 4.1`).
- **[DE ACUERDO]** "Ella te vende la imagen" + "actuación" es desvalorización genérica (Regla 3 / 1.3). El léxico `c8g1d8 → cogida`, `cog13nd8 → cogiendo`, `f8ll9 → follar` más la evaluación moral de la sexualidad femenina es **2.3 (slut-shaming)**. El arquetipo `beta` y `tipo del KFC` es **4.1**.

**`d782af3f81de2512`** — *"DEJA DE PREOCUPARTE COMO UN GvS4N8"* (post, `ar_id = 5`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino, sin marcadores VDG.

**`b0bcbbb5eb375a41`** — *"Ella te dice 'estoy soltera' y el beta automáticamente piensa que no está con nadie. Que está disponible. Que no hay otro hombre en su vida. Se equivoca. Para la mayoría de mujeres, 'soltera' solo significa que no tiene novio formal o al menos trata de ocultarlo. … Mientras tanto ella sigue recibiendo lo que quiere de otros hombres y solo usa al beta para lo que le convenga en ese momento…"* (post, `ar_id = 6`)
- Actual: `1.3` (multi: `1.3, 2.3, 4.1, 4.2`).
- **[DE ACUERDO]** Triple carga misógina bien etiquetada: doble estándar moral / desvalorización (1.3 por "ella sigue recibiendo lo que quiere de otros" + "solo usa al beta para lo que le convenga"), slut-shaming evaluativo (2.3 por `f8ll4nd8 regularmente`), taxonomías manosféricas (4.1 por `beta` / `del 1%`) y esencialismo victimista (4.2). Severidad media en la primaria, baja en 2.3.

**`3741fe9979b310c6`** — *"Muchos así…"* (post, `ar_id = 7`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

### 2.2. Comentarios del post `9664b38ccabe9aa5` / `c4341a005e06e777` / `cc6033e9c99e24bc`

**`f787d814b5a47750`** — *"Ahora resulta que los hombres no engañan"* (comment, `ar_id = 8`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino-objetivado. Tono retórico neutro.

**`b27587532d3bdeca`** — *"[USUARIO_FB] GIPHY"* (comment, `ar_id = 9`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`2bcbbf01c02661d1`** — *"[USUARIO_FB] GIPHY"* (comment, `ar_id = 10`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`449e8848a2128407`** — *"Los ruquitos que no le hallan a la tecnología"* (comment, `ar_id = 11`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino.

**`89b9e9f5dd02b741`** — *"[USUARIO_FB] 12 h"* (comment, `ar_id = 12`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

### 2.3. Comentarios del post `d782af3f81de2512`

**`d145c2f9deb89f18`** — *"Desarrollar caracter y personalidad lo mejor posible"* (comment, `ar_id = 13`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino.

**`cbd632532f03b1fe`** — *"No se."* (comment, `ar_id = 14`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`d6352dd38d58eb51`** — *"Alguna gente se gusta poner en una posición importante en tu vida por solo decir que te envía un 'mensaje' de ¿Como estas?… Y hacerte sentir que de esa manera están para ti."* (comment, `ar_id = 15`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino, sin marcadores.

**`2effd62b3d4cbac5`** — *"No debes amar por completo ni confiar en una mujer"* (comment, `ar_id = 16`)
- Actual: `1.3`.
- **[DE ACUERDO]** Masculino singular "una mujer" recibe imperativo genérico de desconfianza — **Regla 3 / 1.3 (doble estándar moral)**. Sin marcadores de 1.1 (no doméstico) ni 1.2 (no invalida capacidades). Severidad baja correcta.

**`cc5db2110f4ab014`** — *"Honestidad, responsabilidad y respeto son valores que te llevarán lejos en la vida. La verdad más dura es que debes aprender a valorarte a ti mismo"* (comment, `ar_id = 17`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Frase motivacional neutra al género.

**`7bbc336cbd9531f4`** — *"Que solo un poco de codicia, lujuria e ira pueden arruinar décadas de esfuerzo"* (comment, `ar_id = 18`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`a1478d1dd8727dd4`** — *"Nadie vendrá a salvarte, estas a cargo de tu vida y siempre lo estés, hasta que toque partir de esta dimensión"* (comment, `ar_id = 19`)
- Actual: `VDG_SALVAGUARDA_FALSO_POSITIVO` (sin subdim).
- **[DE ACUERDO]** Reclasificación correcta del falso positivo que la auditoría 2026-07-12 marcó como Cat. 1.2. No hay referente femenino. Sugiero precisar la sub-dim como **5.3** (reapropiación / fuera de VDG) para que la marca no quede huérfana; en cualquier caso la lectura "no es VDG" está bien capturada.

**`ff3b966d76f7f46c`** — *"Santa clos no existe"* (comment, `ar_id = 20`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`6983ada882e8a729`** — *"La gran mayoría de mujeres solo está contigo por conveniencia"* (comment, `ar_id = 21`)
- Actual: `1.3` (multi: `1.3, 4.2`).
- **[DE ACUERDO]** Sin imperativo doméstico (1.1 fuera) → **Regla 3 / 1.3** por generalización desvalorizante del colectivo femenino. Adicionalmente es desinformación victimista (4.2): axioma misógino sobre "la mayoría de mujeres". Severidad baja correcta.

**`f0d0660ea97b4f6f`** — *"Primero el trabajo y el dinero, es lo más importante tal vez no para la persona que lo posee, pero si para el mundo y si quieres que marche bien el tuyo dales lo que piden"* (comment, `ar_id = 22`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino-objetivado.

**`e2cd4ab277182465`** — *"Y así hay muchas..."* (comment, `ar_id = 23`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente explícito, aislado.

**`fcd0b54ed754a540`** — *"claro claro no se trata de música, se trata de hombre deconstruide vs malandro"* (comment, `ar_id = 24`)
- Actual: `ninguna`.
- **[DE ACUERDO con reparos]** *deconstruide* es jerga de manosfera Cat. 4.3, pero el comentario no construye un ataque — compara dos arquetipos masculinos sinレディースferente femenina. Mantengo `ninguna`.

**`956858f99fe0f7fe`** — *"Es un pendejo pero así las buscan xD..."* (comment, `ar_id = 37`)
- Actual: `ninguna`.
- **[DE ACUERDO con reparos]** *"así las buscan"* roza Cat. 1.3 (desvalorización genérica: "las mujeres buscan pendejos"), pero el contexto es coloquial-crítico, no doctrinal. Mantengo `ninguna`.

### 2.4. Comentarios del post `b0bcbbb5eb375a41`

**`2020cf0150b86856`** — *"En mi experiencia si eres mestizo café con leche, pero tienes más actitudes de hombre blanco, prácticamente ya valiste mergas para el ligue"* (comment, `ar_id = 25`)
- Actual: `4.2`.
- Propuesta: `4.2, 1.3`.
- **[RECATEGORIZAR — multi incompleta]** El texto no prescribe roles femeninos (1.1 fuera), pero construye una **jerarquía masculina** según actitudes ("hombre blanco" como ideal) — eso es **4.2** (desinformación / taxonomías de dominación). El sesgo implícito hacia las mujeres como evaluadoras que "valoran" al varón por sus "actitudes" también activa **1.3 (doble estándar)**: las mujeres son el público que rechaza, no sujetos. Sugerencia: añadir `1.3` como segunda etiqueta.

**`ed489d3558a69eef`** — *"Para el aliade y la f3m1 nizta"* (comment, `ar_id = 26`)
- Actual: `4.3`.
- Propuesta: `4.3` × 2 (multi: una entrada por cada marcador).
- **[RECATEGORIZAR — multi incompleta]** Tras decodificar: `aliade → aliado` (Cat. 4.3, jerga de emasculación manosférica, §2 del glosario) y `f3m1 nizta → feminazi` (Cat. 4.3, troleo de género, §3.3 del glosario). Son dos marcadores independientes que atacan a dos colectivos distintos (varón aliado vs. feminista). El clasificador carga solo una entrada 4.3 — debería ser 4.3 × 2 para preservar la trazabilidad del doble troleo (como propuso la auditoría 2026-07-12, sec. 2.4).

**`1635ffd5d8837cf6`** — *"[USUARIO_FB]"* (comment, `ar_id = 27`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`d00e75474ff087a6`** — *"Es chistoso por qué es cierto..."* (comment, `ar_id = 28`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`a4305690f1e373f9`** — *"jajajaja"* (comment, `ar_id = 29`)
- Actual: `ninguna`.
- **[DE ACUERDO]** En la auditoría 2026-07-12 figuraba como `SAFEGUARD` sin subdim; ahora se reclasificó como `ninguna`. Sugiero precisar como **5.3** si el contexto del hilo apunta a crítica del discurso de la página; en cualquier caso, sin contenido VDG.

**`8b70afaf7ae522f0`** — *"Un clasico"* (comment, `ar_id = 30`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`7816e512b504b818`** — sin texto (comment, `ar_id = 31`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`06a914582038bc43`** — *"Los escenarios que tienen que crear en IA para sus fantasías están bien raros"* (comment, `ar_id = 32`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino-objetivado.

**`d09fd0fa741fd562`** — *"Plandemia no te go ese problema por que ellas son las que me dan cariño y pagan todo"* (comment, `ar_id = 36`)
- Actual: `1.1`.
- Propuesta: `ninguna` (o `4.2` baja si se quiere registrar el esencialismo).
- **[RECATEGORIZAR — falso positivo]** Sin imperativo doméstico — la Cat. 1.1 exige `a lavar | a limpiar | cuidar de sus hijos | pónganse a barrer` (Protocolo §4). El texto dice "ellas son las que me dan cariño y pagan todo" en un contexto de **alivio** del hablante varón, no de prescripción de rol. La generalización esencialista ("las mujeres = cariño + pago") roza **Cat. 4.2** (desinformación victimista) pero el tono es descriptivo-personal, no doctrinal. Sugerencia primaria: `ninguna`. La auditoría 2026-07-12 coincidió con esta lectura.

**`e355f12847ca56e7`** — *"No es q la chica sea mala es q el hombre hoy día quiere hacer el papel de mujer a la mujer es quien le toca cocinar y criar al bebe"* (comment, `ar_id = 59`)
- Actual: `1.1` (multi: `1.1, 4.2`).
- **[DE ACUERDO]** Imperativo de reclusión doméstica **explícito** — *"a la mujer es quien le toca cocinar y criar al bebe"* — encaja con la **Regla 1 / 1.1** y el marcador de la unidad `a la mujer es quien le toca cocinar y criar al bebé` que el propio Protocolo §4 cita como caso ar_id=41 (idéntico al actual). La división esencialista *"papel de mujer"* vs *"hombre de hoy"* es además **4.2 (desinformación victimista)**. Severidad media correcta.

**`7e6c8887fea366de`** — *"No que a las feministas no les hacen caso jaja"* (comment, `ar_id = 60`)
- Actual: `4.3` (multi: `4.3, 6.1`).
- Propuesta: `4.3, 6.1, 5.2`.
- **[RECATEGORIZAR — multi incompleta]** La mención deslegitimadora del colectivo feminista activa **Cat. 6.1** (deslegitimación ideológica / caricatura) y **Cat. 4.3** (troleo de género — "feministas" como blanco). Falta el **`jaja` final como Cat. 5.2** (humor hostil) para preservar la modulación pragmática que la auditoría 2026-07-12 propuso.

**`b7aff28bc7d3c1de`** — *"A mí me da igual con mujer o sin mujer la paja no falta"* (comment, `ar_id = 61`)
- Actual: `2.1`.
- Propuesta: `ninguna`.
- **[RECATEGORIZAR — falso positivo]** El texto no cosifica ni hipersexualiza — vulgar coloquial sobre la masturbación sin marcador VDG. La auditoría 2026-07-12 ya había coincidido. **Cat. 2.1 exige** adjetivos o frases que reduzcan a la mujer a *"objeto de consumo visual o sexual"* (Protocolo §2.1): el texto solo dice *"con mujer o sin mujer"* (presencia/ausencia como paréntesis), no hay cosificación. Severidad media asignada es excesiva.

**`d160eac77321b71d`** — *"Creo que Eva se golpeó la cabeza al momento de que Dios la creo"* (comment, `ar_id = 62`)
- Actual: `1.2` (multi: `1.2, 6.1`).
- **[DE ACUERDO]** Atribución de **inferioridad cognitiva** a la mujer (Eva = toda mujer) — encaja con la **Regla 2 / 1.2** (marcadores: `estúpida`, `niñata`). Adicionalmente, la cita bíblica funciona como **deslegitimación por esencialismo religioso** (Cat. 6.1). Severidad media correcta.

**`5fbccd33967c9c0b`** — *"Les gusta el desafío, la aventura Y la imagen de bandido... Para después quejarse"* (comment, `ar_id = 63`)
- Actual: `1.3` (multi: `1.3, 4.2`).
- **[DE ACUERDO]** Triple inferencia misógina correctamente etiquetada: (a) generalización de "les gusta X" sobre colectivo femenino; (b) esencialismo hipersexual; (c) *"para después quejarse"* invierte la responsabilidad (marcador Cat. 1 Regla 3 / 1.3). La mano dura del esencialismo es **4.2**. Severidad baja correcta.

**`9a56c48901821349`** — *"Ahí vienen los 'chicos buenos' a proyectarse jajaja..."* (comment, `ar_id = 64`)
- Actual: `5.2`.
- **[DE ACUERDO]** El blanco son los "chicos buenos" (varones que 'proyectan' sobre las mujeres), no las mujeres. La auditoría 2026-07-12 discutió entre `5.2` y `5.3`. El `jaja` es humor hostil (5.2) — el término *"proyectarse"* es jerga de crítica feminista/psicológica del discurso manosférico, así que también podría leerse como **5.3** (reapropiación crítica). Mantengo `5.2`.

**`e94db76c3e610017`** — *"Se lo está diciendo al tipo."* (comment, `ar_id = 65`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`247eade36a76b5ad`** — *"Eso es por qué el man no tiene energía masculina"* (comment, `ar_id = 66`)
- Actual: `4.1`.
- **[DE ACUERDO]** Léxico *"energía masculina"* propio de la **sub-cultura masculinista** (Cat. 4.1). La auditoría 2026-07-12 sugirió añadir 4.2 (victimismo invertido) pero el texto es tan escueto que la única etiqueta clara es 4.1. Mantengo.

**`c559ec3ef418584a`** — *"oelo morado mas encima,,, noo gracias !"* (comment, `ar_id = 67`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`52dda3c28962f918`** — *"Los hombres tienen que usar IA para únicamente representar escenarios imaginarios"* (comment, `ar_id = 68`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino, crítica dirigida a los hombres (uso de IA). El comentario no encaja en ninguna regla 1–6.

**`6caefde6d4c0bc54`** — *"a lo que se ve ellas tienen más que el"* (comment, `ar_id = 69`)
- Actual: `ninguna`.
- **[DE ACUERDO con reparos]** Texto truncado, sin contexto completo. "ellas" aparece pero la frase se interrumpe. Sin marcadores claros de VDG. Mantengo `ninguna`.

**`b177ef1b0bf960bf`** — *"Ya saben muchachos si ven que alguien las agrade, asi la estén matando es mejor no meterse ignorarlo y seguir es consejo de ellas mismas, no vaya a ser qur lo demande a usted por ayudarla sin su consentimiento jajaja"* (comment, `ar_id = 71`)
- Actual: `3.3` (multi: `3.3, 6.3, 5.2`).
- **[DE ACUERDO]** Reclasificación correcta del error grave 2026-07-12. No hay amenaza directa (3.1 fuera): el texto **normaliza la violencia letal** al recomendar *"es mejor no meterse aunque la estén matando"* → **Regla 3 / 3.3 (Apología al feminicidio)**. La coletilla *"es consejo de ellas mismas"* invierte la responsabilidad (refuerza 3.3). El cierre *"no vaya a ser que lo demande por ayudarla sin su consentimiento"* es **Cat. 6.3 (tergiversación)**. El `jajaja` final es **Cat. 5.2 (humor hostil)**. Severidad alta correcta.

**`956858f99fe0f7fe`** — *"Es un pendejo pero así las buscan xD..."* (comment, `ar_id = 37`)
- Actual: `ninguna`.
- **[DE ACUERDO con reparos]** *"así las buscan"* — generalización coloquial sin prescripción. Mantengo `ninguna`.

**`3dfe60c1fbf2e1a8`** — *"Jajajajajaja, noo, ni madres!! La mía les cobraba."* (comment, `ar_id = 38`)
- Actual: `ninguna` + `exclusion_label=VIOLENCIA_COMUN`.
- **[DE ACUERDO]** Humor coloquial de un varón bromeando sobre su esposa cobrando. Sin marcador VDG. La marca `VIOLENCIA_COMUN` está bien aplicada.

**`94a5252cf77e41e6`** — *"Todos los días sale un pendejo a la calle el que lo atrape es de el"* (comment, `ar_id = 39`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino. La auditoría 2026-07-12 lo marcó como VDG_VIOLENCIA_SIMBOLICA con justificación contradictoria ("no hay motivación de género"); ahora correctamente reclasificado como `ninguna`.

### 2.5. Comentarios del post `3741fe9979b310c6`

**`780240cbc59d00c2`** — *"he visto muchas personas así también"* (comment, `ar_id = 46`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`8af3f567d152e0ff`** — *"Los ruquitos que no le hallan a la tecnología"* (comment, `ar_id = 47`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino.

**`d19fa8c571e6b20f`** — *"[USUARIO_FB] 13 h"* (comment, `ar_id = 48`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`a4782c5cfd1d08c5`** — *"Tienen que trabajar"* (comment, `ar_id = 49`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino explícito.

**`0fb18063a6e67a0b`** — *"Desarrollar caracter y personalidad lo mejor posible"* (comment, `ar_id = 50`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`b98b923d496457ae`** — *"No se."* (comment, `ar_id = 51`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`3d78264de6536cde`** — *"Alguna gente se gusta poner en una posición importante en tu vida por solo decir que te envía un 'mensaje'..."* (comment, `ar_id = 52`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`c6cf703c604b5599`** — *"No debes amar por completo ni confiar en una mujer"* (comment, `ar_id = 53`)
- Actual: `1.3`.
- **[DE ACUERDO]** Igual que `2effd62b3d4cbac5` — masculino singular recibe imperativo genérico de desconfianza → **Regla 3 / 1.3**.

**`508a671bc747adc5`** — *"Honestidad, responsabilidad y respeto son valores..."* (comment, `ar_id = 54`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`bc9386385845d410`** — *"Que solo un poco de codicia, lujuria e ira pueden arruinar décadas de esfuerzo"* (comment, `ar_id = 55`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`1f09dfc016268ce8`** — *"Nadie vendrá a salvarte..."* (comment, `ar_id = 56`)
- Actual: `VDG_SALVAGUARDA_FALSO_POSITIVO` (sin subdim).
- **[DE ACUERDO]** Igual que `a1478d1dd8727dd4` — reclasificación correcta. Sugiero precisar como **5.3** para que la marca no quede huérfana.

**`ffa8a417b8469fcf`** — *"Santa clos no existe"* (comment, `ar_id = 57`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`ef23be21d6c07448`** — *"La gran mayoría de mujeres solo está contigo por conveniencia"* (comment, `ar_id = 58`)
- Actual: `1.3` (multi: `1.3, 4.2`).
- **[DE ACUERDO]** Igual que `6983ada882e8a729`.

**`9e768e369f38ae29`** — *"No es tan así si tenés más de 60 años y andas con una muchacha joven, eso es solo para los jóvenes que se enamoran y andan de celosos. tampoco es que hay que pagar todo Pero por joven y hermoso que ya no sos no tenes más chances cuando ya estás viejo y feo jajaja si no colaboras con nada no se te acerca ninguna..."* (comment, `ar_id = 43`)
- Actual: `1.3`.
- Propuesta: `ninguna`.
- **[RECATEGORIZAR — falso positivo]** El texto es la respuesta matizada de un varón de 67 años al comentario del propio post. La primera parte matiza: "No es tan así si tenés más de 60 años...". La segunda parte ("por joven y hermoso que ya no sos no tenes más chances... si no colaboras con nada no se te acerca ninguna") desvaloriza al **propio varón** y a la relación transaccional — pero no contiene un ataque directo al colectivo femenino: no aparece ningún adjetivo de los marcadores de Cat. 1 Regla 3 (no `locas`, no `ridículas`, no `no se dan a respetar`), y la frase *"si no colaboras con nada no se te acerca ninguna"* describe una dinámica comercial sin desvalorización genérica. Mantengo `ninguna` para esta sub-muestra. *Nota: este comentario es la versión corta del `6ac63c8dd7b3dbcd` (ar_id=45), que sí contiene la carga plena de 1.3 / 2.3 / 4.2 — la diferencia es que aquí el hablante aún no despliega los insultos.*

**`8cd4924a57e945dc`** — *"Jajajaja muy cierto suele suceder"* (comment, `ar_id = 44`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`6ac63c8dd7b3dbcd`** — *"…como son todas las mujeres Pero está ves es vieja y fea y por eso a ningún hombre le interesa... Nada es gratis en esta vida algo tiene que costar, la más cara es una esposa que ya tuve y siempre están enculada o les duele la cabeza... Ustedes no se Pero yo que ya tengo 67 me quedo con el plan A que no falla..."* (comment, `ar_id = 45`)
- Actual: `1.3` (multi: `1.3, 2.3, 4.3, 5.2`).
- Propuesta: `1.3, 2.3, 4.2, 5.2` (reemplazar `4.3` por `4.2`).
- **[RECATEGORIZAR — subdim de Cat. 4]** Reclasificación correcta respecto a la auditoría 2026-07-12 (era 3.1, ahora 1.3) — pero la cuarta etiqueta `4.3` no corresponde. El texto contiene:
  - **Cat. 1.3 / Regla 3** (doble estándar moral): *"como son todas las mujeres"*, *"rompe las pelotas, se quejan, te piden"*, *"un negocio es un negocio"*, *"nada es gratis en esta vida"*, *"la más cara es una esposa"*.
  - **Cat. 4.2** (desinformación victimista + esencialismo femenino como mercancía): la división esencialista mujeres-mercancía y la caricatura del varón como *"comprador"* engañado.
  - **Cat. 2.3** (slut-shaming / doble estándar sexual): *"siempre están enculada o les duele la cabeza"*, *"una vieja más fea"*.
  - **Cat. 5.2** (humor hostil): los múltiples `jajaja` que modulan toda la intervención.
  - No aparece ningún troleo de género ni jerga feminazi/aliade — el `4.3` no se justifica. Sugerencia: `1.3, 2.3, 4.2, 5.2`. Severidad media correcta.

### 2.6. Comentarios sueltos (otros posts)

**`b7d6c7e6ce7a0402`** — *"Gracias por tus consejos xd"* (comment, `ar_id = 33`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`ad4a9baac6f43142`** — *"[USUARIO_FB]"* (comment, `ar_id = 34`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`a2b4f447a9e0d275`** — *"Autor Mentalidad 1% Revisa el manual aquí https://mentalidad1.com/"* (comment, `ar_id = 35`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Auto-promoción del autor.

**`b9a25039be6c7770`** — *"Hola.correto.excelente.mensaje.maestro.me.reflejo.cracias"* (comment, `ar_id = 40`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`72acc7815981bf8e`** — *"[USUARIO_FB] GIPHY"* (comment, `ar_id = 41`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`c5be7323a435b26c`** — *"Por eso un cafesito"* (comment, `ar_id = 42`)
- Actual: `ninguna` + `exclusion_label=VIOLENCIA_COMUN`.
- **[DE ACUERDO]** Sin referente femenino, correctamente excluido.

**`4d828911cabce8cd`** — *"yo veo puros wasones jajajajaa"* (comment, `ar_id = 72`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`74da4732a892ce97`** — *"El patriarcado me da patriarcado??"* (comment, `ar_id = 73`)
- Actual: `6.1`.
- **[DE ACUERDO]** Enunciado irónico/despectivo sobre el concepto de patriarcado → **Cat. 6.1 (deslegitimación ideológica)**. La auditoría 2026-07-12 discutió entre 6.1 y 4.2; acepto la elección por el tono de caricatura personal. Severidad baja correcta.

**`d33f19d5eac7c764`** — *"Ni la IA entiende el feminismo"* (comment, `ar_id = 74`)
- Actual: `ninguna`.
- **[DE ACUERDO con reparos]** Es una broma genérica sin marcador VDG. Podría discutirse como Cat. 6.1 (caricatura leve), pero sin marcadores claros.

**`804fbd6335aab52c`** — *"Pues en los carteles veo cosas logicas, a quien le molesta eso? Quieren a una mujer controlada? Quieren que las mujeres mueran? Les importa la opinión de otros sobre su cuerpo? Yo creo que todos pensamos lo mismo que dicen los carteles, o quien no? Cual es el lio? Hoy en dia los hombres no piensan inteligentemente, se dejan llevar por las redes como borregos, estudien chicos, lean, investiguen, mente analítica porfavor"* (comment, `ar_id = 75`)
- Actual: `5.3`.
- **[DE ACUERDO]** Reclasificación correcta del falso positivo que la auditoría 2026-07-12 marcó como Cat. 2.1 + Cat. 1.2. Las preguntas retóricas *"¿Quieren una mujer controlada? ¿Quieren que las mujeres mueran?"* y el rechazo al escrutinio corporal son **marcadores mitigadores de Cat. 5.3**. La mención *"opinión de otros sobre su cuerpo"* es crítica del body-shaming, no body-shaming. El cierre *"los hombres no piensan inteligentemente"* es crítica al varón. **Defensa feminista** correctamente identificada.

**`32cffa6031670f8e`** — *"Yo por las únicas que lucho, es por las nutrias, ni una menos, vivas las queremos."* (comment, `ar_id = 76`)
- Actual: `5.3`.
- **[DE ACUERDO]** Hashtags y consignas feministas → reapropiación positiva (Cat. 5.3).

**`df44aa3a18434718`** — *"Suban a ponerle al jale acá las esperamos ...."* (comment, `ar_id = 77`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`f9703d6d41e170d1`** — *"Usando IA porque no puede encontrar un imagen real: Conservadores enojándose por cosas imaginarias"* (comment, `ar_id = 78`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Crítica política, sin marcador VDG.

---

## 3. Resumen de cambios sugeridos (vista rápida)

| `content_id` | `ar_id` | Categoría actual | Categoría(s) propuesta(s) | Tipo de cambio |
|--------------|--------:|------------------|---------------------------|----------------|
| `2020cf0150b86856` | 25 | `4.2` | `4.2`, `1.3` | Multi incompleta |
| `ed489d3558a69eef` | 26 | `4.3` | `4.3` × 2 | Multi incompleta (doble marcador) |
| `d09fd0fa741fd562` | 36 | `1.1` | `ninguna` (o `4.2` baja) | **Falso positivo** |
| `9e768e369f38ae29` | 43 | `1.3` | `ninguna` | **Falso positivo** |
| `6ac63c8dd7b3dbcd` | 45 | `1.3`, `2.3`, `4.3`, `5.2` | `1.3`, `2.3`, `4.2`, `5.2` | Reemplazar `4.3` por `4.2` |
| `7e6c8887fea366de` | 60 | `4.3`, `6.1` | `4.3`, `6.1`, `5.2` | Multi incompleta (falta `jaja`) |
| `b7aff28bc7d3c1de` | 61 | `2.1` | `ninguna` | **Falso positivo** |

Aciertos notables respecto a la auditoría 2026-07-12 que **se mantienen correctamente** y no requieren cambio:

| `content_id` | `ar_id` | Antes (mal) | Ahora (bien) |
|--------------|--------:|-------------|--------------|
| `a1478d1dd8727dd4` | 19 | `1.2` | `SAFEGUARD` (sin subdim) |
| `1f09dfc016268ce8` | 56 | `1.2` | `SAFEGUARD` (sin subdim) |
| `52dda3c28962f918` | 68 | `1.1` | `ninguna` |
| `94a5252cf77e41e6` | 39 | `1.x` (sin subdim) | `ninguna` |
| `e355f12847ca56e7` | 59 | `ninguna` | `1.1`, `4.2` |
| `7e6c8887fea366de` | 60 | `ninguna` | `4.3`, `6.1` |
| `d160eac77321b71d` | 62 | `ninguna` | `1.2`, `6.1` |
| `5fbccd33967c9c0b` | 63 | `ninguna` | `1.3`, `4.2` |
| `b177ef1b0bf960bf` | 71 | `3.1`, `1.2`, `5.1` | `3.3`, `6.3`, `5.2` |
| `6ac63c8dd7b3dbcd` | 78→45 | `3.1` | `1.3` + multi |
| `804fbd6335aab52c` | 57→75 | `2.1`, `1.2`, `5.1` | `5.3` |
| `0f3e884a8a124fd1_p0` | 1 | `1.1`, `2.1`, `4` sin subdim, `5.1` | `1.3`, `2.3`, `4.2` |
| `0f3e884a8a124fd1_p2` | 3 | `3.1` | `4.1`, `4.2`, `4.3` |
| `dc8ae80a3ae35f92` | 4 | `1.1`, `5.1` | `1.3`, `2.3`, `4.1` |
| `b0bcbbb5eb375a41` | 6 | `1.1`, `2.2`, `5.1` | `1.3`, `2.3`, `4.1`, `4.2` |
| `2effd62b3d4cbac5` | 14→16 | `1.2` | `1.3` |
| `c6cf703c604b5599` | 25→53 | `1.2` | `1.3` |
| `6983ada882e8a729` | 19→21 | `1.1` | `1.3`, `4.2` |
| `ef23be21d6c07448` | 30→58 | `1.1` | `1.3`, `4.2` |
| `247eade36a76b5ad` | 48→66 | `1.1` | `4.1` |
| `ed489d3558a69eef` | 34→26 | `1.3`, `2.2` | `4.3` |
| `2020cf0150b86856` | 33→25 | `1.1`, `5.1` | `4.2` (parcial — falta `1.3`) |
| `9a56c48901821349` | 46→64 | `5.1` | `5.2` |

---

## 4. Recomendaciones de calibración (actualización 2026-07-13)

1. **Mantener el decodificador de leetspeak como pre-procesamiento obligatorio.** El nuevo proceso ya lo aplica sistemáticamente (`degenerac18n`, `acost4rs3`, `f8ll4nd8`, `cog13nd8`, `c8g1d8`, `aliade`, `f3m1 nizta`, `GvS4N8`, `1nútil`). El acierto más visible del nuevo proceso es que `ed489d3558a69eef` ya cae en Cat. 4.3 sin necesidad de corrección manual.
2. **Reforzar la regla "ningún marcador de Cat. 4 sin etiqueta 4.x".** El error residual `ed489d3558a69eef` perdió uno de los dos marcadores 4.3. El clasificador debería generar **una entrada `analysis_labels` por cada marcador 4.x independiente** (no fusionar `aliade` + `f3m1 nizta` en una sola fila).
3. **Endurecer el guardarraíl de coocurrencia para Cat. 1.1.** El error `d09fd0fa741fd562` ("ellas son las que me dan cariño y pagan todo") se etiquetó como 1.1 sin que aparezca ningún marcador de imperativo doméstico (`a lavar | a limpiar | cuidar de sus hijos | pónganse a barrer`). Sugerencia: añadir al prompt una frase explícita del estilo *"para asignar Cat. 1.1 el texto DEBE incluir al menos uno de estos marcadores; si no aparece ninguno, Cat. 1.1 queda descartada y se evalúan 1.2 / 1.3 / 4.2"*.
4. **Evitar Cat. 2.1 cuando el referente femenino aparece como paréntesis y no como objeto.** El error `b7aff28bc7d3c1de` ("con mujer o sin mujer la paja no falta") muestra que el clasificador confunde presencia/ausencia femenina con cosificación. Sugerencia: requerir en Cat. 2.1 un **adjetivo o sintagma cosificador** (marcadores del glosario: *putita obediente, packs, enseñando las nalgas, naquitas, buena*), no solo la mención de "mujer" como categoría.
5. **Para Cat. 1.3 multi, exigir referente femenino COLECTIVO o COMPARATIVO.** El error `9e768e369f38ae29` muestra que el clasificador dispara 1.3 con sólo "no se te acerca ninguna" — frase que describe la dinámica del propio varón. Sugerencia: para 1.3 multi, requerir uno de los patrones `como son todas las mujeres | la mayoría de mujeres | para después quejarse | no se dan a respetar | viejas webonas | locas`. Sin alguno de ellos, la sub-dim 1.3 no se asigna aunque el hablante se sienta rechazado.
6. **Para Cat. 4.3 multi, validar contra el glosario `jerga-manosfera.md` ANTES de evaluar.** Cuando el clasificador detecta un término del glosario (feminazi, aliade, mangina, femoid, stacy, pagafantas, beta, del 1%, red pill), debe generar **una entrada `analysis_labels` por cada match independiente**. Hoy `ed489d3558a69eef` quedó con un único 4.3 cuando hay dos matches.
7. **Detectar el "jaja" como Cat. 5.2 incluso cuando ya hay 4.x o 6.x cargados.** El error `7e6c8887fea366de` perdió la etiqueta 5.2 a pesar del "jaja" final. Sugerencia: el clasificador debería aplicar siempre el módulo de salvaguarda (Protocolo §3) y, si el mensaje contiene `jaja` en un contexto de ataque, agregar 5.2 como etiqueta complementaria.
8. **Marcar explícitamente la sub-dim 5.3 en falsos positivos claros.** Los dos casos `SAFEGUARD` sin subdim (`a1478d1dd8727dd4`, `1f09dfc016268ce8`) deberían etiquetarse como **5.3** para que la consulta SQL no requiera un filtro adicional por subdim nula.

---

*Auditoría preparada a partir de los documentos en `knowledge/categorias-violencia-genero-digital/` (versión julio 2026) y de la auditoría previa `docs/auditoria-categorizaciones-2026-07-12.md`. Cualquier discrepancia con los documentos de categorización debe prevalecer sobre el veredicto aquí expresado.*