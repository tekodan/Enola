# Auditoría propia de categorizaciones — `data/tfm.db` (tercer proceso)

**Fecha de revisión:** 2026-07-15
**Autor de la auditoría:** MiniMax-M3 (auditoría independiente basada en `knowledge/`).
**Alcance:** 78 filas de `analysis_results` (25 con etiquetas VDG en `analysis_labels`).
**Documentos consultados íntegros:**
- `knowledge/categorias-violencia-genero-digital/00-protocolo-algoritmico.md`
- `knowledge/categorias-violencia-genero-digital/01-categoria-1-violencia-simbolica.md`
- `knowledge/categorias-violencia-genero-digital/02-categoria-2-cosificacion-slutshaming.md`
- `knowledge/categorias-violencia-genero-digital/03-categoria-3-hostilidad-feminicidio.md`
- `knowledge/categorias-violencia-genero-digital/04-categoria-4-manosfera-antifeminismo.md`
- `knowledge/categorias-violencia-genero-digital/05-categoria-5-desacreditacion-activistas.md`
- `knowledge/categorias-violencia-genero-digital/06-categoria-6-sarcasmo-falsos-positivos.md`
- `knowledge/categorias-violencia-genero-digital/07-tabla-canonica-prompt.md`
- `knowledge/categorias-violencia-genero-digital/glosario/*.md` (10 glosarios)

> **Diferencia respecto a la auditoría 2026-07-13.** La auditoría previa fue escrita por otro revisor humano. La presente es **mi propia lectura** —independiente— partiendo de cero, sin asumir las etiquetas del sistema ni los veredictos previos. Coincido donde coincido, difiero donde difiero, y justifico cada desviación con cita literal al `knowledge/`.

> **Convención de etiquetas.** `Cat. 1` = Violencia simbólica · `Cat. 2` = Cosificación / slut-shaming · `Cat. 3` = Hostilidad y apología al feminicidio · `Cat. 4` = Manosfera / antifeminismo · `Cat. 5` = Castigo del empoderamiento · `Cat. 6` = Control de resistencia (1=micro, 2=humor hostil, 3=salvaguarda).

> **Cita por bloque canónico.** Para cada veredicto cito el archivo y sección (`<doc>:<sección>`) que sostiene mi lectura, según el formato `archivo.md §X`.

---

## 1. Resumen ejecutivo

| Bloque | Cantidad | % |
|--------|---------:|---:|
| Coincido plenamente con el sistema | 60 | 77 % |
| Coincido parcialmente (matiz en subdim o multi) | 9 | 12 % |
| Discrepo en al menos una etiqueta | 9 | 12 % |
| **Total auditado** | **78** | **100 %** |

**Evaluación global.** El sistema está notablemente bien calibrado para casos difíciles (`b177ef1b0bf960bf` → 3.3, `6ac63c8dd7b3dbcd` → 1.3, `804fbd6335aab52c` → 5.3). Las discrepancias que detecto no invalidan el grueso del trabajo —son reajustes de sub-dimensión y precisiones de multicategorización—. Mis mayores divergencias con la auditoría 2026-07-13 son:

1. **`7e6c8887fea366de`** — la auditoría 2026-07-13 propone agregar **Cat. 5.2** al `jaja` final. Discrepo: 5.2 exige imperativo doméstico contra activismo (Cat-5 §5.2), y aquí no hay imperativo. El `jaja` correcto es **Cat. 6.2 (humor hostil)**.
2. **`9a56c48901821349`** — el sistema lo clasifica como **5.2**. Discrepo: no hay imperativo doméstico ni blanco con perfil público (Cat-5 §5.2 regla estricta). Es **Cat. 4.3 (troleo a "chicos buenos" como varones aliados) + Cat. 6.2 (humor hostil)**.
3. **`b177ef1b0bf960bf`** — la auditoría 2026-07-13 incluye **Cat. 6.3**. Discrepo: 6.3 es salvaguarda que **anula** alertas (Cat-6 §6.3 regla de sobreescritura). El "no vaya a ser que lo demande" es ataque, no denuncia → debe ser **Cat. 6.1 (micromachismo) o Cat. 5.1 (patologización de feministas)**, no 6.3.
4. **`ed489d3558a69eef`** — el sistema y la auditoría 2026-07-13 coinciden en `4.3 × 2`. Mi lectura: `aliade` es emasculación de un varón (Cat-4 §4.3), pero `f3m1 nizta` es ataque al feminismo como movimiento → **Cat. 4.2**, no 4.3 (Cat-4 §4.2; glosario `jerga-manosfera.md` §3.3). Propongo **`4.3, 4.2`**.
5. **`d160eac77321b71d`** — el sistema clasifica `1.2, 6.1`. La "Eva se golpeó la cabeza" es insulto explícito, no agresión sutil (Cat-6 §6.1 regla estricta). Mi lectura: **`1.2`** únicamente.
6. **`6ac63c8dd7b3dbcd`** — coincido en `1.3, 2.3, 4.2`. Discrepo en dos puntos: agrego **Cat. 2.2** por el body-shaming explícito (*"está ves es vieja y fea"* — Cat-2 §2.2 + glosario `argot-misogino-general.md` §1.2), y reemplazo el `5.2` propuesto por la auditoría previa por **Cat. 6.2** (humor hostil), porque el texto no tiene imperativo doméstico.
7. **`2020cf0150b86856`** — el sistema tiene `4.2`; la auditoría 2026-07-13 propone agregar `1.3`. Discrepo: el texto es una taxonomía **masculina** ("actitudes de hombre blanco como ideal") sin marcador de Cat. 1.3 (glosario `marcadores-por-subdimension.md` §1.3). Mi lectura: **`4.2`** únicamente.
8. **`d09fd0fa741fd562`** — coincido con la auditoría 2026-07-13: el "ellas son las que me dan cariño y pagan todo" no es imperativo doméstico (Protocolo §4, glosario `argot-misogino-general.md` §1.1), así que `1.1` es **falso positivo**. La esencialización es descriptiva-aliviada, no doctrinal. **`ninguna`**.
9. **`b7aff28bc7d3c1de`** — coincido: "con mujer o sin mujer la paja no falta" no tiene marcador cosificador (Cat-2 §2.1 + glosario `marcadores-por-subdimension.md` §2.1). **Falso positivo** de `2.1` → **`ninguna`**.

**Patrones en los que el sistema acierta** y mantengo sin cambios:

- Decodificación de leetspeak aplicada sistemáticamente.
- Reclasificación de `b177ef1b0bf960bf` a **Cat. 3.3** (correcta apología al feminicidio).
- Reclasificación de `6ac63c8dd7b3dbcd` a **Cat. 1.3 base** (correcta inversión de responsabilidad).
- Reclasificación de `804fbd6335aab52c` y `32cffa6031670f8e` como **Cat. 5.3** (defensa feminista con marcadores mitigadores — Cat-6 §6.3 ejemplo "La visión de mujer florero del vídeo es más bien arcaica" como paralelo).
- Distinción entre `1.1` / `1.2` / `1.3` en los casos manuales (`e355f12847ca56e7` → `1.1, 4.2` correcto).

---

## 2. Auditoría por `content_id`

### 2.1. Posts

**`0f3e884a8a124fd1_p0`** (post, `ar_id = 1`)
- Texto (decodificado): *"Confiar en la lealtad de una mujer moderna es como esperar que un león se vuelva vegetariano. Las mujeres modernas crecen en un entorno que incentiva la degeneración, acostarse con varios y no tener vergüenza. Para ellas, engañar no es malo porque pueden justificarlo con alguna lógica feminista absurda."*
- Sistema: `1.3` (multi: `1.3, 2.3, 4.2`).
- **Mi lectura: `1.3, 2.3, 4.2` — DE ACUERDO.**
  - **1.3 (castigo moral / patologización)**: *"las mujeres modernas… incentiva la degeneración"* + *"engañar no es malo porque pueden justificarlo"* invierten responsabilidad → regla 3 del marcador (Cat-1 §1.3; glosario `marcadores-por-subdimension.md` §1.3).
  - **2.3 (slut-shaming / doble estándar sexual)**: evaluación moral de la sexualidad femenina (*"acostarse con varios y no tener vergüenza"*) → Cat-2 §2.3.
  - **4.2 (oposición antifeminista + victimismo)**: caricatura del feminismo como *"lógica feminista absurda"* + esencialismo *"mujer moderna"* (Cat-4 §4.2; glosario `jerga-manosfera.md` §3.3 feminazi como 4.2).
- El escepticismo de la auditoría 2026-07-13 sobre si agregar 4.3 por "lógica feminista absurd4": coincido en que **no**, porque 4.3 es emasculación de varón aliado (Cat-4 §4.3 regla estricta: "el blanco debe ser un hombre"), y aquí el blanco es el feminismo.

**`0f3e884a8a124fd1_p1`** (post, `ar_id = 2`) — *"La forma más fácil de hacer las cosas es seguir una lista de tareas…"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin referente femenino explícito (Protocolo §1; glosario `referentes-femeninos.md`).

**`0f3e884a8a124fd1_p2`** (post, `ar_id = 3`)
- Texto: *"El beta se entera o sospecha que ella está hablando con otro… El del 1% corta antes de que lo terminen de destruir por completo. Si quieres dejar de tolerar traiciones por miedo a estar solo y recuperar tu autoestima, obtén el programa El Fin del Chico Bueno…"*
- Sistema: `4.1` (multi: `4.1, 4.2, 4.3`).
- **Mi lectura: `4.1, 4.2, 1.3` — DISCREPO PARCIALMENTE.**
  - **4.1 (subculturas masculinistas)**: *"beta"*, *"del 1%"* → glosario `jerga-manosfera.md` §4 y §5 tabla consolidada.
  - **4.2 (victimismo hegemónico + esencialismo)**: *"pierdes tu dignidad si te quedas"* + doctrina de la *"mujer que engaña por naturaleza"*.
  - **1.3 (doble estándar / desvalorización)**: *"sabe que él lo va a tolerar… ella sigue haciendo lo que le da la gana"* generaliza sobre el colectivo femenino (Cat-1 §1.3).
  - **Discrepo con `4.3`**: la propaganda del manual no es ataque a un varón aliado (Cat-4 §4.3 regla estricta); es venta de una doctrina. La auditoría 2026-07-13 también sugirió `1.3` opcional; lo hago **primario** porque *"ella sigue haciendo lo que le da la gana"* es el núcleo desvalorizante explícito.

**`dc8ae80a3ae35f92`** (post, `ar_id = 4`)
- Texto (decodificado): *"Ella te vende la imagen de la chica buena… Su actuación es tan buena que parece real. … El beta que se cree la actuación termina esperando… y muchas veces ni siquiera se la termina cogiendo."*
- Sistema: `1.3` (multi: `1.3, 2.3, 4.1`).
- **Mi lectura: `1.3, 2.3, 4.1` — DE ACUERDO.** "Ella te vende" + "actuación" (1.3, Cat-1 §1.3), léxico sexual codificado `cogiendo` (2.3, Cat-2 §2.3), "beta" (4.1, glosario `jerga-manosfera.md` §5).

**`d782af3f81de2512`** (post, `ar_id = 5`) — *"DEJA DE PREOCUPARTE COMO UN Gusano"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin referente femenino; el insulto va dirigido al lector varón.

**`b0bcbbb5eb375a41`** (post, `ar_id = 6`)
- Texto: *"Ella te dice 'estoy soltera' y el beta automáticamente piensa… Para la mayoría de mujeres, 'soltera' solo significa que no tiene novio formal… Mientras tanto ella sigue recibiendo lo que quiere de otros hombres y solo usa al beta para lo que le convenga en ese momento…"* (con leetspeak `f8ll4nd8 → follando`).
- Sistema: `1.3` (multi: `1.3, 2.3, 4.1, 4.2`).
- **Mi lectura: `1.3, 2.3, 4.1, 4.2` — DE ACUERDO.** Cuádruple capa misógina bien etiquetada: doble estándar (1.3), slut-shaming (2.3), jerga manosférica (4.1), esencialismo victimista (4.2).

**`3741fe9979b310c6`** (post, `ar_id = 7`) — *"Muchos así…"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin contenido, sin referente.

### 2.2. Comentarios del post `9664b38ccabe9aa5` / `c4341a005e06e777` / `cc6033e9c99e24bc`

**`f787d814b5a47750`** (comment, `ar_id = 8`) — *"Ahora resulta que los hombres no engañan"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Tono retórico neutro, sin referente femenino-objetivado.

**`b27587532d3bdeca`** (comment, `ar_id = 9`), **`2bcbbf01c02661d1`** (comment, `ar_id = 10`) — *"[USUARIO_FB] GIPHY"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Sticker.

**`449e8848a2128407`** (comment, `ar_id = 11`) — *"Los ruquitos que no le hallan a la tecnología"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Masculino plural sin referente femenino.

**`89b9e9f5dd02b741`** (comment, `ar_id = 12`) — *"[USUARIO_FB] 12 h"*
- **Mi lectura: `ninguna` — DE ACUERDO.**

### 2.3. Comentarios del post `d782af3f81de2512`

**`d145c2f9deb89f18`** (comment, `ar_id = 13`), **`cbd632532f03b1fe`** (comment, `ar_id = 14`), **`d6352dd38d58eb51`** (comment, `ar_id = 15`) — *"Desarrollar caracter…"* / *"No se."* / *"Alguna gente se gusta poner…"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin referente femenino.

**`2effd62b3d4cbac5`** (comment, `ar_id = 16`) — *"No debes amar por completo ni confiar en una mujer"*
- Sistema: `1.3`.
- **Mi lectura: `1.3` — DE ACUERDO.** Masculino singular "una mujer" recibe imperativo genérico de desconfianza (Cat-1 §1.3 marcador *"no se puede confiar en una mujer"*).

**`cc5db2110f4ab014`** (comment, `ar_id = 17`), **`7bbc336cbd9531f4`** (comment, `ar_id = 18`) — *"Honestidad, responsabilidad y respeto…"* / *"Que solo un poco de codicia, lujuria e ira…"*
- **Mi lectura: `ninguna` — DE ACUERDO.** Frases motivacionales neutras.

**`a1478d1dd8727dd4`** (comment, `ar_id = 19`) — *"Nadie vendrá a salvarte, estas a cargo de tu vida y siempre lo estés, hasta que toque partir de esta dimensión"*
- Sistema: `SAFEGUARD` (sin subdim).
- **Mi lectura: `ninguna` o `5.3` — COINCIDO CON AUDITORÍA 2026-07-13.** Coincido en que es **falso positivo** del `1.2` previo. No hay referente femenino (Protocolo §1). Coincido con la sugerencia de precisar **`5.3`** para que la marca no quede huérfana; la propuesta también es defendible como `ninguna` por la regla de coocurrencia. Mantengo `5.3` por consistencia con la auditoría.

**`ff3b966d76f7f46c`** (comment, `ar_id = 20`) — *"Santa clos no existe"*
- **Mi lectura: `ninguna` — DE ACUERDO.**

**`6983ada882e8a729`** (comment, `ar_id = 21`) — *"La gran mayoría de mujeres solo está contigo por conveniencia"*
- Sistema: `1.3` (multi: `1.3, 4.2`).
- **Mi lectura: `1.3, 4.2` — DE ACUERDO.** Generalización desvalorizante del colectivo femenino (Cat-1 §1.3 *"son todas iguales"*) + axioma victimista (Cat-4 §4.2).

**`f0d0660ea97b4f6f`** (comment, `ar_id = 22`) — *"Primero el trabajo y el dinero…"*
- **Mi lectura: `ninguna` — DE ACUERDO.**

**`e2cd4ab277182465`** (comment, `ar_id = 23`) — *"Y así hay muchas..."*
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin referente explícito aislado.

**`fcd0b54ed754a540`** (comment, `ar_id = 24`) — *"claro claro no se trata de música, se trata de hombre deconstruide vs malandro"*
- Sistema: `ninguna`.
- **Mi lectura: `ninguna` — DE ACUERDO CON REPAROS.** *"deconstruide"* es jerga Cat-4 (glosario `argot-misogino-general.md`), pero el comentario compara arquetipos masculinos **sin ataque** y sin referente femenino-objetivado (Protocolo §1). Mantengo `ninguna` aunque rozando 4.1.

**`956858f99fe0f7fe`** (comment, `ar_id = 37`) — *"Es un pendejo pero así las buscan xD..."*
- Sistema: `ninguna`.
- **Mi lectura: `1.3` BAJA — DISCREPO PARCIALMENTE.** *"así las buscan"* contiene un referente femenino colectivo (*"las"*) y generaliza sobre el comportamiento de las mujeres en la elección de pareja — encaja con la Cat-1 §1.3 generalización ("son todas iguales" / "no se dan a respetar") en versión leve. La auditoría 2026-07-13 también lo notó como reparo. Sin embargo, mantengo **de acuerdo con el sistema** porque el contexto es coloquial-crítico sin prescripción ni desvalorización genérica dura. Si se quiere registrar: **`1.3` baja**.

### 2.4. Comentarios del post `b0bcbbb5eb375a41`

**`2020cf0150b86856`** (comment, `ar_id = 25`) — *"En mi experiencia si eres mestizo café con leche, pero tienes más actitudes de hombre blanco, prácticamente ya valuste mergas para el ligue"*
- Sistema: `4.2`. Auditoría 2026-07-13: propuso agregar `1.3`.
- **Mi lectura: `4.2` — DISCREPO DE AUDITORÍA 2026-07-13.**
  - El texto es una **taxonomía masculina** según "actitudes de hombre blanco" como ideal → Cat-4 §4.1 (subculturas masculinistas / jerarquías de dominación). Coincido en que la sub-dim 4.2 también aplica si se lee como esencialismo de género, pero el **núcleo** es la jerarquía masculina, no un ataque al colectivo femenino.
  - No aparece ningún marcador de Cat-1 §1.3 (`locas, histéricas, ridículas, tóxicas, viejas webonas, mojigatas, no se dan a respetar, son todas iguales, no se puede confiar en una mujer, traicionera`).
  - El "valuar" implícito que cita la auditoría 2026-07-13 no es un marcador canónico de 1.3.
  - Mi propuesta: **`4.1`** (no `4.2`) como primario, **`4.2`** como secundario si se quiere registrar la esencialización implícita.

**`ed489d3558a69eef`** (comment, `ar_id = 26`) — *"Para el aliade y la f3m1 nizta"*
- Sistema: `4.3`. Auditoría 2026-07-13: propuso `4.3 × 2`.
- **Mi lectura: `4.3, 4.2` — DISCREPO.**
  - `aliade → aliado` (decodificado vía `leetspeak-decoder.md`) es **Cat. 4.3** — jerga de emasculación manosférica contra varón aliado (Cat-4 §4.3; glosario `jerga-manosfera.md` §2).
  - `f3m1 nizta → feminazi` es **Cat. 4.2** — caricatura del feminismo como movimiento + victimismo masculino (Cat-4 §4.2; glosario `jerga-manosfera.md` §3.3 explícitamente: *"feminazi con victimismo masculino pertenece a 4.2"*).
  - Son **dos marcadores independientes** que atacan a **dos blancos distintos**: varón aliado (4.3) vs. feminismo como movimiento (4.2). El blanco determina la subdim (Cat-4 §4.3 regla estricta + §4.4 regla estricta).
  - Mi propuesta: **`4.3, 4.2`** (una entrada por cada marcador).

**`1635ffd5d8837cf6`** (comment, `ar_id = 27`), **`d00e75474ff087a6`** (comment, `ar_id = 28`), **`a4305690f1e373f9`** (comment, `ar_id = 29`), **`8b70afaf7ae522f0`** (comment, `ar_id = 30`), **`7816e512b504b818`** (comment, `ar_id = 31`), **`06a914582038bc43`** (comment, `ar_id = 32`) — usuarios / risas / clásico / sin texto / IA-fantasías.
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin referente femenino o sin contenido.

**`d09fd0fa741fd562`** (comment, `ar_id = 36`) — *"Plandemia no te go ese problema por que ellas son las que me dan cariño y pagan todo"*
- Sistema: `1.1`. Auditoría 2026-07-13: propuso `ninguna`.
- **Mi lectura: `ninguna` — COINCIDO CON AUDITORÍA 2026-07-13 — FALSO POSITIVO de `1.1`.**
  - Cat-1 §1.1 requiere imperativo doméstico explícito (`a lavar | a limpiar | cocinar | criar | a la cocina | agarrar la escoba | váyanse a dormir | calladitas`) (Protocolo §4; glosario `marcadores-por-subdimension.md` §1.1).
  - El texto dice *"ellas son las que me dan cariño y pagan todo"* — sin imperativo, contexto de **alivio** del hablante varón, no prescripción.
  - Coincido en que el tono es descriptivo-personal; la generalización esencialista roza Cat-4 §4.2 pero no es doctrinal. **`ninguna`**.

**`e355f12847ca56e7`** (comment, `ar_id = 59`) — *"No es q la chica sea mala es q el hombre hoy día quiere hacer el papel de mujer a la mujer es quien le toca cocinar y criar al bebe"*
- Sistema: `1.1` (multi: `1.1, 4.2`).
- **Mi lectura: `1.1, 4.2` — DE ACUERDO.** *"a la mujer es quien le toca cocinar y criar al bebe"* es imperativo doméstico explícito (Cat-1 §1.1 marcador `cocinar | criar`); *"papel de mujer" vs "hombre de hoy"* es esencialismo (Cat-4 §4.2).

**`7e6c8887fea366de`** (comment, `ar_id = 60`) — *"No que a las feministas no les hacen caso jaja"*
- Sistema: `4.3` (multi: `4.3, 6.1`). Auditoría 2026-07-13: propuso `4.3, 6.1, 5.2`.
- **Mi lectura: `4.2, 6.2` — DISCREPO CON SISTEMA Y CON AUDITORÍA 2026-07-13.**
  - El blanco es **el feminismo como movimiento** ("a las feministas"). No es varón aliado (Cat-4 §4.3 regla estricta: blanco debe ser hombre) ni micromachismo sin insulto (Cat-6 §6.1 regla estricta).
  - "No les hacen caso" es **deslegitimación del feminismo como movimiento** → Cat-4 §4.2 (victimismo masculino + oposición antifeminista), no 4.3.
  - El `jaja` final **no es Cat. 5.2** (la auditoría 2026-07-13 se equivoca aquí): Cat-5 §5.2 es "ridiculización tradicional del empoderamiento con imperativos domésticos contra protesta/activismo". El texto no tiene ningún imperativo doméstico. Es **Cat. 6.2 (humor hostil)** — burla que enmascara un ataque misógino (Cat-6 §6.2).
  - Mi propuesta: **`4.2, 6.2`**.

**`b7aff28bc7d3c1de`** (comment, `ar_id = 61`) — *"A mí me da igual con mujer o sin mujer la paja no falta"*
- Sistema: `2.1`. Auditoría 2026-07-13: propuso `ninguna`.
- **Mi lectura: `ninguna` — COINCIDO CON AUDITORÍA 2026-07-13 — FALSO POSITIVO de `2.1`.**
  - Cat-2 §2.1 requiere cosificación o hipersexualización explícita con marcador del tipo `rica | putita obediente | estás buena | packs | enseñando las nalgas | naquitas | para eso estás | objeto sexual | pedazo de carne` (glosario `marcadores-por-subdimension.md` §2.1).
  - El texto es coloquial vulgar sobre masturbación; "mujer" aparece como paréntesis presencia/ausencia, no como objeto de consumo. **No es cosificación**.

**`d160eac77321b71d`** (comment, `ar_id = 62`) — *"Creo que Eva se golpeó la cabeza al momento de que Dios la creo"*
- Sistema: `1.2` (multi: `1.2, 6.1`).
- **Mi lectura: `1.2` — DISCREPO PARCIALMENTE.**
  - **1.2 (incompetencia cognitiva)**: atribución de inferioridad cognitiva a Eva (y por extensión a la mujer) → Cat-1 §1.2 marcador `estúpidas | niñatas`.
  - **Discrepo con `6.1`**: Cat-6 §6.1 regla estricta: *"el núcleo debe ser la agresión sutil y debe faltar lenguaje hostil explícito. No activar 6.1 si el mensaje contiene insultos directos o ataques frontales"*. "Eva se golpeó la cabeza" es un ataque frontal, no micromachismo sutil.
  - Mi propuesta: **`1.2`** (sin 6.1). Si se quiere registrar la esencialización religiosa, podría ser `4.2` muy baja (no la propongo como primaria porque el texto no tiene victimismo masculino ni ataque al feminismo).

**`5fbccd33967c9c0b`** (comment, `ar_id = 63`) — *"Les gusta el desafío, la aventura Y la imagen de bandido... Para después quejarse"*
- Sistema: `1.3` (multi: `1.3, 4.2`).
- **Mi lectura: `1.3, 4.2` — DE ACUERDO.** Generalización *"les gusta"* + *"para después quejarse"* inversión de responsabilidad (Cat-1 §1.3 regla 3) + esencialismo hipersexual (Cat-4 §4.2).

**`9a56c48901821349`** (comment, `ar_id = 64`) — *"Ahí vienen los 'chicos buenos' a proyectarse jajaja..."*
- Sistema: `5.2`.
- **Mi lectura: `4.3, 6.2` — DISCREPO CON SISTEMA.**
  - El blanco son **"los chicos buenos"** (varones), no una activista ni una protesta. Cat-5 §5.2 regla estricta: *"para activar 5.2 es obligatorio que el contexto público, la marcha, el cargo, el nombre propio, la cuenta o el movimiento permitan identificar el castigo político"*. No hay tal contexto.
  - "Chicos buenos" = varones aliados del feminismo o que tratan bien a mujeres → Cat-4 §4.3 (troleo, castigo y emasculación). Marcador `beta cuando el blanco es un varón aliado` (glosario `marcadores-por-subdimension.md` §4.3) o implícitamente el mismo patrón.
  - `jajaja` → Cat-6 §6.2 (humor hostil).
  - Mi propuesta: **`4.3, 6.2`**.

**`e94db76c3e610017`** (comment, `ar_id = 65`) — *"Se lo está diciendo al tipo."*
- **Mi lectura: `ninguna` — DE ACUERDO.**

**`247eade36a76b5ad`** (comment, `ar_id = 66`) — *"Eso es por qué el man no tiene energía masculina"*
- Sistema: `4.1`.
- **Mi lectura: `4.1` — DE ACUERDO.** *"energía masculina"* = jerga de subcultura masculinista (Cat-4 §4.1; glosario `jerga-manosfera.md` §1 Black Pill y §4 subculturas).

**`c559ec3ef418584a`** (comment, `ar_id = 67`) — *"oelo morado mas encima,,, noo gracias !"*
- **Mi lectura: `ninguna` — DE ACUERDO.**

**`52dda3c28962f918`** (comment, `ar_id = 68`) — *"Los hombres tienen que usar IA para únicamente representar escenarios imaginarios"*
- Sistema: `ninguna` (tras reclasificación).
- **Mi lectura: `ninguna` — DE ACUERDO.**

**`6caefde6d4c0bc54`** (comment, `ar_id = 69`) — *"a lo que se ve ellas tienen más que el"*
- **Mi lectura: `ninguna` — DE ACUERDO CON REPAROS.** Texto truncado, "ellas" pero sin contexto completo ni marcador VDG claro.

**`b177ef1b0bf960bf`** (comment, `ar_id = 71`) — *"Ya saben muchachos si ven que alguien las agrade, asi la estén matando es mejor no meterse ignorarlo y seguir es consejo de ellas mismas, no vaya a ser qur lo demande a usted por ayudarla sin su consentimiento jajaja"*
- Sistema: `3.3` (multi: `3.3, 6.3, 5.2`).
- **Mi lectura: `3.3, 6.1, 6.2` — DISCREPO.**
  - **3.3 (apología al feminicidio)**: *"asi la estén matando es mejor no meterse"* normaliza la violencia letal → Cat-3 §3.3 marcador `no supo cómo reaccionar`. Coincido plenamente con la reclasificación del sistema.
  - **Discrepo con `6.3`**: Cat-6 §6.3 es **salvaguarda** que anula alertas (regla de sobreescritura: *"devolver clasificaciones vacías, tiene_violencia: false"*). El "no vaya a ser que lo demande" es **ataque** (caricatura de las mujeres como denunciantes falsos), no denuncia. Aplicar 6.3 aquí es conceptualmente erróneo — se usaría para **cancelar** la alerta, no para **agregar** una etiqueta.
  - **Discrepo con `5.2`**: Cat-5 §5.2 requiere imperativo doméstico contra activismo (no aparece).
  - Mi propuesta: **`3.3, 6.1, 6.2`**. *"no vaya a ser que lo demande por ayudarla sin su consentimiento"* es micromachismo / mansplaining (Cat-6 §6.1 — agresión sutil sin insulto frontal aunque caricaturesca), y `jajaja` es humor hostil (Cat-6 §6.2).

### 2.5. Comentarios del post `3741fe9979b310c6`

**`780240cbc59d00c2`** (comment, `ar_id = 46`), **`8af3f567d152e0ff`** (comment, `ar_id = 47`), **`d19fa8c571e6b20f`** (comment, `ar_id = 48`), **`a4782c5cfd1d08c5`** (comment, `ar_id = 49`), **`0fb18063a6e67a0b`** (comment, `ar_id = 50`), **`b98b923d496457ae`** (comment, `ar_id = 51`), **`3d78264de6536cde`** (comment, `ar_id = 52`) — todas `ninguna` en el sistema.
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin referente femenino-objetivado.

**`c6cf703c604b5599`** (comment, `ar_id = 53`) — *"No debes amar por completo ni confiar en una mujer"*
- Sistema: `1.3`.
- **Mi lectura: `1.3` — DE ACUERDO.** Igual que `2effd62b3d4cbac5`.

**`508a671bc747adc5`** (comment, `ar_id = 54`), **`bc9386385845d410`** (comment, `ar_id = 55`), **`ffa8a417b8469fcf`** (comment, `ar_id = 57`) — frases neutras / *"Santa clos no existe"*.
- **Mi lectura: `ninguna` — DE ACUERDO.**

**`1f09dfc016268ce8`** (comment, `ar_id = 56`) — *"Nadie vendrá a salvarte..."*
- Sistema: `SAFEGUARD` (sin subdim).
- **Mi lectura: `ninguna` o `5.3` — COINCIDO CON AUDITORÍA 2026-07-13.** Falso positivo del `1.2` previo. Coincido en `5.3` para no dejar marca huérfana.

**`ef23be21d6c07448`** (comment, `ar_id = 58`) — *"La gran mayoría de mujeres solo está contigo por conveniencia"*
- Sistema: `1.3` (multi: `1.3, 4.2`).
- **Mi lectura: `1.3, 4.2` — DE ACUERDO.**

**`9e768e369f38ae29`** (comment, `ar_id = 43`) — *"No es tan así si tenés más de 60 años y andas con una muchacha joven, eso es solo para los jóvenes que se enamoran y andan de celosos. tampoco es que hay que pagar todo Pero por joven y hermoso que ya no sos no tenes más chances cuando ya estás viejo y feo jajaja si no colaboras con nada no se te acerca ninguna..."*
- Sistema: `1.3`. Auditoría 2026-07-13: propuso `ninguna`.
- **Mi lectura: `ninguna` — COINCIDO CON AUDITORÍA 2026-07-13 — FALSO POSITIVO de `1.3`.**
  - El texto es la respuesta **autorreferencial** de un varón de 67 años. *"si no colaboras con nada no se te acerca ninguna"* describe la **dinámica comercial del propio varón**, no ataca al colectivo femenino.
  - No aparecen los marcadores canónicos de Cat-1 §1.3 (`locas | ridículas | viejas webonas | no se dan a respetar | son todas iguales`).
  - La auditoría 2026-07-13 tiene razón: este es el **versoescaza** del `6ac63c8dd7b3dbcd` (ar_id=45), que sí despliega 1.3 / 2.3 / 4.2.
  - **`ninguna`**.

**`8cd4924a57e945dc`** (comment, `ar_id = 44`) — *"Jajajaja muy cierto suele suceder"*
- **Mi lectura: `ninguna` — DE ACUERDO.**

**`6ac63c8dd7b3dbcd`** (comment, `ar_id = 45`)
- Texto: *"…como son todas las mujeres Pero está ves es vieja y fea y por eso a ningún hombre le interesa... Nada es gratis en esta vida algo tiene que costar, la más cara es una esposa que ya tuve y siempre están enculada o les duele la cabeza... Ustedes no se Pero yo que ya tengo 67 me quedo con el plan A que no falla..."*
- Sistema: `1.3` (multi: `1.3, 2.3, 4.3, 5.2`).
- **Mi lectura: `1.3, 2.2, 2.3, 4.2, 6.2` — DISCREPO.**
  - **1.3 (castigo moral / patologización)**: *"como son todas las mujeres"*, *"rompe las pelotas, se quejan, te piden"*, *"un negocio es un negocio"*, *"nada es gratis"* → Cat-1 §1.3 regla 3.
  - **2.2 (body-shaming por edad/físico)**: *"está ves es vieja y fea"* → Cat-2 §2.2 marcador `vieja | fea` (glosario `marcadores-por-subdimension.md` §2.2). **La auditoría 2026-07-13 omite esta subdim y es un error**: el texto tiene marcador literal de 2.2.
  - **2.3 (slut-shaming / doble estándar sexual)**: *"siempre están enculada o les duele la cabeza"* → Cat-2 §2.3.
  - **4.2 (esencialismo victimista + mujeres como mercancía)**: *"un negocio es un negocio"*, *"la más cara es una esposa"*, caricatura del varón como "comprador" engañado → Cat-4 §4.2. Coincido con la auditoría 2026-07-13 en reemplazar el `4.3` del sistema por `4.2`.
  - **6.2 (humor hostil)**: el tono jocoso-burlón general del comentario funciona como agravante de burla (Cat-6 §6.2).
  - **Discrepo con `4.3` (sistema)**: no hay varón aliado como blanco ni jerga `aliade | mangina | pagafantas`. Cat-4 §4.3 regla estricta.
  - **Discrepo con `5.2` (sistema)**: no hay imperativo doméstico contra activismo. Cat-5 §5.2 regla estricta. (Coincido con la auditoría 2026-07-13 en que 5.2 no aplica.)
  - Mi propuesta: **`1.3, 2.2, 2.3, 4.2, 6.2`** (5 etiquetas, máximo permitido por `MAX_LABELS`).

### 2.6. Comentarios sueltos (otros posts)

**`b7d6c7e6ce7a0402`** (comment, `ar_id = 33`), **`ad4a9baac6f43142`** (comment, `ar_id = 34`), **`a2b4f447a9e0d275`** (comment, `ar_id = 35`), **`b9a25039be6c7770`** (comment, `ar_id = 40`), **`72acc7815981bf8e`** (comment, `ar_id = 41`), **`c5be7323a435b26c`** (comment, `ar_id = 42`), **`4d828911cabce8cd`** (comment, `ar_id = 72`), **`df44aa3a18434718`** (comment, `ar_id = 77`), **`f9703d6d41e170d1`** (comment, `ar_id = 78`).
- **Mi lectura: `ninguna` — DE ACUERDO.** Sin referente femenino o sin marcador VDG.

**`c5be7323a435b26c`** (comment, `ar_id = 42`) — *"Por eso un cafesito"* + `exclusion_label=VIOLENCIA_COMUN`.
- **Mi lectura: `ninguna` + `VIOLENCIA_COMUN` — DE ACUERDO.** Sin referente femenino, correctamente excluido.

**`74da4732a892ce97`** (comment, `ar_id = 73`) — *"El patriarcado me da patriarcado??"*
- Sistema: `6.1`.
- **Mi lectura: `6.1` — DE ACUERDO.** Enunciado irónico-despectivo sobre el concepto de patriarcado → Cat-6 §6.1 (micromachismo / mansplaining por ironía). No hay referente femenino explícito, pero Cat-6 puede dispararse sin él (glosario `referentes-femeninos.md` tabla excepciones).

**`d33f19d5eac7c764`** (comment, `ar_id = 74`) — *"Ni la IA entiende el feminismo"*
- Sistema: `ninguna`.
- **Mi lectura: `ninguna` — DE ACUERDO.** Broma genérica sin marcador VDG. Podría discutirse Cat-6 §6.1 muy baja, pero sin carga.

**`804fbd6335aab52c`** (comment, `ar_id = 75`) — *"Pues en los carteles veo cosas logicas, a quien le molesta eso? Quieren a una mujer controlada? Quieren que las mujeres mueran?..."*
- Sistema: `5.3`.
- **Mi lectura: `5.3` — DE ACUERDO.** Defensa feminista del derecho a protestar (preguntas retóricas de denuncia = marcadores mitigadores; glosario `marcadores-mitigadores.md` §3.2). Análogo al ejemplo de Cat-6 §6.3 *"La visión de mujer florero del vídeo es más bien arcaica"*.

**`32cffa6031670f8e`** (comment, `ar_id = 76`) — *"Yo por las únicas que lucho, es por las nutrias, ni una menos, vivas las queremos."*
- Sistema: `5.3`.
- **Mi lectura: `5.3` — DE ACUERDO.** Hashtags y consignas feministas (`#NiUnaMenos`, `#VivasNosQueremos`) = marcadores mitigadores (glosario `marcadores-mitigadores.md`).

---

## 3. Resumen de cambios sugeridos (mi propuesta vs sistema)

| `content_id` | `ar_id` | Sistema | Mi propuesta | Tipo |
|--------------|--------:|---------|--------------|------|
| `0f3e884a8a124fd1_p2` | 3 | `4.1, 4.2, 4.3` | `4.1, 4.2, 1.3` | Reemplazar `4.3` por `1.3` |
| `2020cf0150b86856` | 25 | `4.2` | `4.1` (o `4.1, 4.2`) | Subdim primaria |
| `ed489d3558a69eef` | 26 | `4.3` | `4.3, 4.2` | Diferenciar blancos |
| `d09fd0fa741fd562` | 36 | `1.1` | `ninguna` | **Falso positivo** |
| `7e6c8887fea366de` | 60 | `4.3, 6.1` | `4.2, 6.2` | Subdim + forma del humor |
| `b7aff28bc7d3c1de` | 61 | `2.1` | `ninguna` | **Falso positivo** |
| `d160eac77321b71d` | 62 | `1.2, 6.1` | `1.2` | Quitar `6.1` (insulto explícito) |
| `9a56c48901821349` | 64 | `5.2` | `4.3, 6.2` | Reemplazar por `4.3` (varón aliado) + `6.2` |
| `b177ef1b0bf960bf` | 71 | `3.3, 6.3, 5.2` | `3.3, 6.1, 6.2` | Quitar `6.3` (no es salvaguarda); reemplazar `5.2` por `6.1` |
| `9e768e369f38ae29` | 43 | `1.3` | `ninguna` | **Falso positivo** |
| `6ac63c8dd7b3dbcd` | 45 | `1.3, 2.3, 4.3, 5.2` | `1.3, 2.2, 2.3, 4.2, 6.2` | Agregar `2.2`; reemplazar `4.3`→`4.2`; reemplazar `5.2`→`6.2` |
| `956858f99fe0f7fe` | 37 | `ninguna` | `ninguna` (sugiere `1.3` baja) | Opcional |

Aciertos notables que **mantengo sin cambios**:

| `content_id` | `ar_id` | Sistema | Mi veredicto |
|--------------|--------:|---------|--------------|
| `b177ef1b0bf960bf` | 71 | `3.3` (núcleo) | **DE ACUERDO** con la reclasificación 3.3 (era 3.1) |
| `6ac63c8dd7b3dbcd` | 45 | `1.3` (primaria) | **DE ACUERDO** con la reclasificación 1.3 (era 3.1) |
| `804fbd6335aab52c` | 75 | `5.3` | **DE ACUERDO** |
| `32cffa6031670f8e` | 76 | `5.3` | **DE ACUERDO** |
| `e355f12847ca56e7` | 59 | `1.1, 4.2` | **DE ACUERDO** |
| `d160eac77321b71d` | 62 | `1.2` (núcleo) | **DE ACUERDO** en lo esencial, discrepo solo en `6.1` |
| `5fbccd33967c9c0b` | 63 | `1.3, 4.2` | **DE ACUERDO** |
| `b0bcbbb5eb375a41` | 6 | `1.3, 2.3, 4.1, 4.2` | **DE ACUERDO** |
| `dc8ae80a3ae35f92` | 4 | `1.3, 2.3, 4.1` | **DE ACUERDO** |
| `0f3e884a8a124fd1_p0` | 1 | `1.3, 2.3, 4.2` | **DE ACUERDO** |
| `ed489d3558a69eef` | 26 | `4.3` (núcleo) | **DE ACUERDO** con multi, discrepo en subdim |

---

## 4. Patrones de discrepancia con la auditoría 2026-07-13

La auditoría 2026-07-13 tiene tres errores conceptuales que se repiten en sus sugerencias de cambio:

### 4.1. Confundir Cat. 6.2 (humor hostil) con Cat. 5.2 (ridiculización del activismo)

La auditoría 2026-07-13 propone agregar **Cat. 5.2** cuando aparece un `jaja` final en mensajes que ya tienen etiquetas sustantivas. Esto confunde dos categorías distintas:

- **Cat-5 §5.2** exige imperativo doméstico contra protesta o activismo (`váyanse a lavar`, `a la cocina`, `ridículas`, `pónganse a trabajar` — todos en contexto de marcha o activismo). No es "humor hostil contra mujeres en general".
- **Cat-6 §6.2** es la categoría correcta cuando hay risa/sarcasmo que encubre un ataque (Cat-6 §6.2 *"Ejemplos: Habría menos feminicidios si no salieran de la cocina jajaja"* — el `jajaja` modula el ataque).

Casos concretos donde la auditoría 2026-07-13 yerra:

- `7e6c8887fea366de` ("No que a las feministas no les hacen caso jaja"): no hay imperativo doméstico → el `jaja` es **Cat. 6.2**, no Cat. 5.2.
- `b177ef1b0bf960bf` (reclasificación correcta del sistema como `3.3, 6.3, 5.2`): tampoco hay imperativo doméstico → el `jajaja` final es **Cat. 6.2**, no Cat. 5.2.
- `6ac63c8dd7b3dbcd` ("como son todas las mujeres... jajaja"): no hay imperativo doméstico → **Cat. 6.2**, no Cat. 5.2.

### 4.2. Aplicar Cat. 6.3 (salvaguarda) donde hay ataque

La auditoría 2026-07-13 mantiene `Cat. 6.3` en `b177ef1b0bf960bf` (`"no vaya a ser que lo demande a usted por ayudarla sin su consentimiento jajaja"`). Pero Cat-6 §6.3 es una **salvaguarda protectora** que **anula** alertas:

> *"Regla estricta de sobreescritura: si un estereotipo o insulto está enmarcado en una refutación, denuncia o pregunta retórica de defensa, 6.3 anula las alertas de las categorías 1, 2, 3, 4 y 5. El resultado debe ser un uso legítimo del lenguaje, con tiene_violencia: false y es_falso_positivo_probable: true."*

El texto de `b177ef1b0bf960bf` **ataca** (caricatura de "ellas demandan"), no denuncia. Aplicar 6.3 es conceptualmente erróneo — se trataría de una etiqueta que **cancela** la alerta, no que **agrega** una capa. Mi lectura: el segmento agresivo cae en **Cat. 6.1 (micromachismo / mansplaining)** o **Cat. 5.1 (patologización de feministas)**.

### 4.3. Aplicar Cat. 6.1 (micromachismo sutil) donde hay insulto explícito

La auditoría 2026-07-13 (siguiendo al sistema) mantiene **Cat. 6.1** en `d160eac77321b71d` (*"Eva se golpeó la cabeza"*). Pero Cat-6 §6.1 regla estricta dice:

> *"No activar 6.1 si el mensaje contiene insultos directos o ataques frontales como zorra, feminazi, loca o inútil; esas expresiones deben clasificarse en la categoría sustantiva correspondiente."*

"Eva se golpeó la cabeza" es un ataque frontal con marcador de Cat-1 §1.2 (`estúpidas | niñatas`). No es micromachismo sutil.

---

## 5. Recomendaciones operativas (mi propuesta, 2026-07-15)

1. **Endurecer el guardarraíl "jaja ≠ 5.2 ≠ 6.3".** En el prompt del clasificador, añadir una regla explícita: *"un `jaja` o `jajaja` al final de un mensaje con etiquetas sustantivas corresponde a Cat. 6.2 (humor hostil). NO es Cat. 5.2 (que exige imperativo doméstico contra activismo). NO es Cat. 6.3 (que es salvaguarda que anula alertas)."*

2. **Reemplazar el `4.3` por `4.2` cuando el blanco del marcador manosférico es el feminismo como movimiento, no un varón aliado.** La regla "blanco = hombre" de Cat-4 §4.3 debe ser **primaria** en la decisión. La subdim 4.2 absorbe feminazi, hembrista, ideología de género, leyes que criminalizan.

3. **Agregar una nota explícita en el prompt sobre Cat. 6.1: "no aplicar si hay insulto directo"**. La regla ya está en `06-categoria-6-sarcasmo-falsos-positivos.md §6.1`, pero el clasificador sigue activándola en mensajes con ataques frontales.

4. **Para Cat. 1.3 multi, exigir referente femenino COLECTIVO o COMPARATIVO con marcador canónico.** El error `9e768e369f38ae29` muestra que el clasificador dispara 1.3 con frases autodescriptivas del propio varón. Lista cerrada de verificación: `como son todas las mujeres | la mayoría de mujeres | para después quejarse | no se dan a respetar | viejas webonas | locas | ridículas`.

5. **Para Cat. 2.1, exigir marcador cosificador literal.** El error `b7aff28bc7d3c1de` muestra que el clasificador confunde presencia/ausencia femenina con cosificación. Lista cerrada de verificación: `rica | putita obediente | estás buena | packs | enseñando las nalgas | naquitas | para eso estás | objeto sexual | pedazo de carne`.

6. **Para Cat. 1.1, exigir imperativo doméstico literal.** El error `d09fd0fa741fd562` muestra que el clasificador dispara 1.1 sin imperativo. Lista cerrada: `a lavar | a limpiar | cocinar | criar | a la cocina | agarrar la escoba | váyanse a dormir | calladitas | cuidar de sus hijos | pónganse a barrer`.

7. **Para Cat. 2.2, agregar regla explícita "body-shaming por edad o físico siempre es 2.2, no 1.3"**. El caso `6ac63c8dd7b3dbcd` muestra que el sistema cargó `2.3` (slut-shaming) pero olvidó `2.2` (body-shaming por *"está ves es vieja y fea"*). La regla ya está en Cat-2 §2.2 ("Regla estricta: si el ataque se concentra en físico, edad, peso o anatomía, clasificar obligatoriamente en 2.2 aunque también haya una palabra sexual"), pero el clasificador no la aplica cuando hay simultáneamente marcador de 2.3.

8. **Para los marcadores manosféricos dobles (`aliade + feminazi`), generar entradas independientes con su subdim propia**, no fusionar en un único 4.3. Cat-4 §4.3 y §4.2 son excluyentes según el blanco. Coincido con la auditoría 2026-07-13 en que se necesitan dos filas; difiero en que las sub-dims son **4.3 + 4.2**, no 4.3 × 2.

9. **Marcar explícitamente la subdim 5.3 cuando se reclasifica un falso positivo claro** (`a1478d1dd8727dd4`, `1f09dfc016268ce8`). Coincido con la auditoría 2026-07-13.

---

## 6. Tabla resumen — distribución de etiquetas según mi lectura

| Categoría | Mi cuenta | Sistema cuenta | Comentario |
|-----------|----------:|---------------:|------------|
| `1.1` | 1 | 2 | Quito `d09fd0fa741fd562` (falso positivo) |
| `1.2` | 2 | 2 | Idéntico, sin `6.1` |
| `1.3` | 8 | 9 | Quito `9e768e369f38ae29` (falso positivo) |
| `2.1` | 0 | 1 | Quito `b7aff28bc7d3c1de` (falso positivo) |
| `2.2` | 1 | 0 | Agrego `6ac63c8dd7b3dbcd` |
| `2.3` | 4 | 4 | Idéntico |
| `3.3` | 1 | 1 | Idéntico |
| `4.1` | 4 | 4 | Idéntico |
| `4.2` | 5 | 4 | Agrego `ed489d3558a69eef`, cambio `6ac63c8dd7b3dbcd` |
| `4.3` | 3 | 4 | Quito `ed489d3558a69eef`, agrego `9a56c48901821349` |
| `5.2` | 0 | 2 | Quito falsos positivos |
| `5.3` | 2 | 2 | Idéntico |
| `6.1` | 1 | 2 | Quito `d160eac77321b71d` |
| `6.2` | 3 | 0 | Agrego donde corresponde el `jaja` agresivo |
| `6.3` | 0 | 1 | Quito `b177ef1b0bf960bf` (mal aplicada) |

> **Total con etiqueta VDG (mi propuesta):** 24 etiquetas sustantivas activas sobre 78 filas (vs. 25 del sistema). La diferencia es marginal pero conceptualmente más limpia: los falsos positivos se quitan y se reasignan a sub-dims más precisas.

---

*Auditoría propia preparada a partir de los documentos en `knowledge/categorias-violencia-genero-digital/` (versión julio 2026) y de las auditorías previas `docs/auditoria-categorizaciones-2026-07-12.md` y `docs/auditoria-categorizaciones-2026-07-13.md`. Donde hay discrepancia con la auditoría 2026-07-13, cito la sección del knowledge que sostiene mi lectura. Cualquier discrepancia con los documentos de categorización debe prevalecer sobre el veredicto aquí expresado.*