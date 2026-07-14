# Auditoría de categorizaciones — `data/tfm.db`

**Fecha de revisión:** 2026-07-12
**Alcance:** 78 filas de `analysis_results` (39 con etiquetas multi-`analysis_labels`).
**Documentos de referencia:** `knowledge/categorias-violencia-genero-digital/` (00-protocolo + cat. 1–6 + glosarios).

> **Identificador usado en esta auditoría.** Para que cada entrada sea localizable desde la página `/validacion` de NiceGUI (que muestra `content_id` y no el `id` numérico interno), en todas las tablas y referencias se usa **`content_id`** como clave primaria. El `id` numérico de `analysis_results` se conserva entre paréntesis `(ar_id = N)` para auditoría técnica.

> **Convención de etiquetas.** Se usa el nombre corto del documento de categorización:
> `Cat. 1` = Violencia simbólica · `Cat. 2` = Cosificación / slut-shaming · `Cat. 3` = Hostilidad y apología al feminicidio · `Cat. 4` = Manosfera / antifeminismo · `Cat. 5` = Salvaguarda, sarcasmo y falsos positivos · `Cat. 6` = Desacreditación de activistas. La sub-dimensión se indica con el código del doc (p. ej. `1.3` = doble estándar moral). La `Regla de exclusión de violencia común` se aplica como filtro previo (exclusión, no borrado).

---

## 1. Resumen ejecutivo

| Bloque | Cantidad | % |
|--------|---------:|---:|
| Categorizaciones con las que **estoy de acuerdo** | 50 | 64 % |
| Categorizaciones que **recategorizaría** (acuerdo parcial / corrección) | 22 | 28 % |
| Categorizaciones que considero **erróneas** (falso positivo de VDG) | 6 | 8 % |
| **Total** | **78** | **100 %** |

**Patrones de error más frecuentes** detectados al cruzar contra los documentos:

1. **Confusión 1.1 ↔ 1.3.** Se usa *Roles tradicionales y de sumisión* (1.1) donde el texto en realidad activa la regla 3 — *Doble estándar moral y desvalorización* (1.3): frases del tipo *"la mayoría de mujeres solo está contigo por conveniencia"*, *"las mujeres engañan por naturaleza"*, *"para después quejarse"*. 1.1 exige imperativos hacia el ámbito privado (marcadores `a lavar`, `a limpiar`, `cuidar de sus hijos`); 1.3 exige adjetivos patologizantes o inversión de responsabilidad (`no se dan a respetar`, `locas`, `ridículas`).
2. **Cat. 5 mal aplicada como "sello de cautela" genérico.** La base trata `VDG_SALVAGUARDA_FALSO_POSITIVO` casi como un *tag* residual, pero el documento Cat. 5 distingue tres sub-dimensiones muy distintas: 5.1 sexismo implícito (ataque), 5.2 humor hostil (ataque), 5.3 falsos positivos por reapropiación (NO es ataque). Varios `content_id` llevan `5.1` siendo el texto explícito, no implícito.
3. **Cat. 3 usada como cajón de "lo grave".** Se etiqueta como `3.1` (hostilidad física no sexual) cualquier contenido que suene fuerte, aunque no contenga amenazas ni léxico letal. La sub-dim. correcta en esos casos suele ser 1.3, 4.2 o, en los textos con `jajaja` + normalización de la violencia, **3.3** (apología al feminicidio).
4. **Argot manosférico detectado como Cat. 1 / 2.** Marcadores como `f3m1 nizta` (= *feminazi*, Cat. 4.3), `aliade` (= *aliade*, jerga de emasculación, Cat. 4.3), `beta / del 1%` (Cat. 4.1 / 4.2) están siendo clasificados en violencia simbólica cuando pertenecen claramente a la **Cat. 4** según el glosario de jerga manosférica.
5. **Falsos negativos en comentarios sexistas cortos.** La base marca como `ninguna` comentarios que contienen prescripción de rol doméstico (`e355f12847ca56e7`: *"a la mujer es quien le toca cocinar y criar al bebé"*) o esencialismo religioso (`d160eac77321b71d`: *"Creo que Eva se golpeó la cabeza al momento de que Dios la creó"*).

---

## 2. Auditoría por `content_id`

Formato de cada entrada:

```
content_id — fragmento representativo (tipo, ar_id = N)
Categoría actual → Categoría(s) propuesta(s)
[VEREDICTO] justificación corta basada en el/los doc(s) de categorización.
```

### 2.1. Posts

**`0f3e884a8a124fd1_p0`** — *"Confiar en la lealtad de una muj3r moderna es como esperar que un león se vuelva vegetariano. Las mvjeres modernas crecen en un entorno que incentiva la degenerac18n…"* (post, `ar_id = 1`)
- Actual: `1.1`, `2.1`, `4` (sin subdim), `5.1`.
- Propuesta: `1.3`, `2.3`, `4.2`, *quitar `5.1`*.
- **[RECATEGORIZAR]** El texto no contiene imperativos hacia el ámbito privado (no aplica 1.1); activa la **Regla 3 de Cat. 1** (doble estándar moral: *"no es malo porque pueden justificarlo con alguna lógica feminista absurd4"* → inversión de responsabilidad). El léxico `degenerac18n / acost4rs3` configura **slut-shaming (Cat. 2.3)** — no cosificación estética (2.1). El discurso esencialista sobre la "mujer moderna" es desinformación victimista (Cat. 4.2). La etiqueta `5.1` sobra: el texto es explícitamente agresivo, no hay sexismo implícito.

**`0f3e884a8a124fd1_p1`** — *"La forma más fácil de hacer las cosas es seguir una lista de tareas…"* (post, `ar_id = 2`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino, sin marcadores.

**`0f3e884a8a124fd1_p2`** — *"El beta se entera o sospecha que ella está hablando con otro… Y por eso no cambia. Al contrario, muchas veces se pone peor. […] El del 1% corta antes de que lo terminen de destruir por completo."* (post, `ar_id = 3`)
- Actual: `3.1`.
- Propuesta: `1.3`, `4.1`, `4.2`.
- **[RECATEGORIZAR — error grave]** No hay amenaza de daño físico ni léxico letal (Regla 1 / 2 / 3 de Cat. 3), por lo que **3.1 no aplica**. El contenido es **manosfera pura**: el arquetipo `beta` vs. `del 1%` corresponde a la **sub-dim. 4.1** (subculturas masculinistas / taxonomías de dominación), y la narrativa *"la mujer engaña por naturaleza"* corresponde a la **4.2** (desinformación de género y victimismo hegemónico). El componente de doble estándar moral hacia las mujeres cabe en **1.3**.

**`dc8ae80a3ae35f92`** — *"Ella te vende la imagen de la chica buena, correcta, que 'no es f4cil' […] El beta que se cree la actuación termina esperando… y muchas veces ni siquiera se la termina cog13nd8."* (post, `ar_id = 4`)
- Actual: `1.1`, `5.1`.
- Propuesta: `1.3`, `4.1`, `4.2`, *quitar `5.1`*.
- **[RECATEGORIZAR]** Mismo patrón que `0f3e884a8a124fd1_p0` y `0f3e884a8a124fd1_p2`: no hay imperativo doméstico → 1.1 incorrecto, debe ser **1.3** (desvalorización: la mujer "vende una imagen", "actuación"). Además carga **4.1** (`beta`, `tipo del KFC`, `chico bueno`) y **4.2** (la mujer como manipuladora interesada). La etiqueta `5.1` sobra: el contenido es explícitamente agresivo.

**`d782af3f81de2512`** — *"DEJA DE PREOCUPARTE COMO UN GvS4N8"* (post, `ar_id = 5`)
- Actual: `ninguna` + `exclusion_label=VIOLENCIA_COMUN`.
- **[DE ACUERDO]** Sin referente femenino, sin marcadores VDG. `VIOLENCIA_COMUN` bien aplicada.

**`b0bcbbb5eb375a41`** — *"Ella te dice 'estoy soltera' y el beta automáticamente piensa que no está con nadie. […] Sabe que probablemente hay alguien más en la ecuación."* (post, `ar_id = 6`)
- Actual: `1.1`, `2.2`, `5.1`.
- Propuesta: `1.3`, `2.3`, `4.2`, *quitar `5.1`*.
- **[RECATEGORIZAR]** Mismo patrón: no hay imperativo doméstico (1.1 → **1.3** por inversión de responsabilidad: *"mientras tanto ella sigue recibiendo lo que quiere de otros"*). El contenido es slut-shaming (2.3) — *"acostándose con varios"*, no body-shaming (2.2). Es narrativa manosférica (4.2): "el del 1% no se deja engañar". `5.1` sobra.

**`3741fe9979b310c6`** — *"Muchos así…"* (post, `ar_id = 7`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

### 2.2. Comentarios del post `dc8ae80a3ae35f92`

**`780240cbc59d00c2`** — *"he visto muchas personas así también"* (comment, `ar_id = 8`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

### 2.3. Comentarios del post `d782af3f81de2512`

**`8af3f567d152e0ff`** — *"Los ruquitos que no le hallan a la tecnología e gusta"* (comment, `ar_id = 9`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino.

**`d19fa8c571e6b20f`** — *"[USUARIO_FB] 13 h"* (comment, `ar_id = 10`)
- Actual: `ninguna` (la fila guardó `Error parsing response`, pero el contenido es solo un nombre + tiempo).
- **[DE ACUERDO]**

**`d145c2f9deb89f18`** — *"Desarrollar caracter y personalidad lo mejor posible"* (comment, `ar_id = 11`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`cbd632532f03b1fe`** — *"No se."* (comment, `ar_id = 12`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`d6352dd38d58eb51`** — *"Alguna gente se gusta poner en una posición importante en tu vida por solo decir que te envía un 'mensaje'…"* (comment, `ar_id = 13`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino.

**`2effd62b3d4cbac5`** — *"No debes amar por completo ni confiar en una mujer"* (comment, `ar_id = 14`)
- Actual: `1.2`.
- Propuesta: `1.3`.
- **[RECATEGORIZAR]** El texto no invalida capacidades intelectuales/físicas de las mujeres (no es 1.2 según la *Regla 2* de Cat. 1, cuyos marcadores son `mujer al volante`, `mujer florero`, `calladita`, `niñata`, `estupidez`). Es una prescripción moral desvalorizante — el masculino singular "una mujer" recibe un imperativo genérico de desconfianza, lo que encaja con la **Regla 3 / 1.3** (doble estándar moral). Severidad al menos *baja*.

**`cc5db2110f4ab014`** — *"Honestidad, responsabilidad y respeto son valores que te llevarán lejos…"* (comment, `ar_id = 15`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`7bbc336cbd9531f4`** — *"Que solo un poco de codicia, lujuria e ira pueden arruinar décadas de esfuerzo"* (comment, `ar_id = 16`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`a1478d1dd8727dd4`** — *"Nadie vendrá a salvarte, estas a cargo de tu vida y siempre lo estarás, hasta que toque partir de esta dimensión"* (comment, `ar_id = 17`)
- Actual: `1.2` (justificación: *"control y dependencia que refleja la imposición de roles tradicionales sobre la responsabilidad de la mujer"*).
- Propuesta: `ninguna`.
- **[RECATEGORIZAR — falso positivo]** No hay ningún referente femenino (sustantivos ni pronombres). El texto es una frase motivacional neutra al género. El protocolo exige **coocurrencia semántica** entre pronombres/sustantivos femeninos y los adjetivos de la regla activada (Protocolo §1) — no se cumple.

**`ff3b966d76f7f46c`** — *"Santa clos no existe"* (comment, `ar_id = 18`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`6983ada882e8a729`** — *"La gran mayoría de mujeres solo está contigo por conveniencia"* (comment, `ar_id = 19`)
- Actual: `1.1`.
- Propuesta: `1.3`, `4.2`.
- **[RECATEGORIZAR]** No hay imperativo doméstico, no prescribe roles: el texto **desvaloriza** a las mujeres como colectivo (marcador de la **Regla 3 / 1.3**, doble estándar moral). Además es desinformación victimista (4.2): "mayoría de mujeres" como axioma misógino.

**`f0d0660ea97b4f6f`** — *"Primero el trabajo y el dinero, es lo más importante…"* (comment, `ar_id = 20`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`a4782c5cfd1d08c5`** — *"Tienen que trabajar"* (comment, `ar_id = 21`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`0fb18063a6e67a0b`** — *"Desarrollar caracter y personalidad lo mejor posible"* (comment, `ar_id = 22`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`b98b923d496457ae`** — *"No se."* (comment, `ar_id = 23`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`3d78264de6536cde`** — *"Alguna gente se gusta poner en una posición importante en tu vida…"* (comment, `ar_id = 24`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`c6cf703c604b5599`** — *"No debes amar por completo ni confiar en una mujer"* (comment, `ar_id = 25`)
- Actual: `1.2`.
- Propuesta: `1.3`.
- **[RECATEGORIZAR]** Igual que `2effd62b3d4cbac5`.

**`508a671bc747adc5`** — *"Honestidad, responsabilidad y respeto son valores…"* (comment, `ar_id = 26`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`bc9386385845d410`** — *"Que solo un poco de codicia, lujuria e ira pueden arruinar décadas…"* (comment, `ar_id = 27`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`1f09dfc016268ce8`** — *"Nadie vendrá a salvarte…"* (comment, `ar_id = 28`)
- Actual: `1.2`.
- Propuesta: `ninguna`.
- **[RECATEGORIZAR — falso positivo]** Sin referente femenino. Igual que `a1478d1dd8727dd4`.

**`ffa8a417b8469fcf`** — *"Santa clos no existe"* (comment, `ar_id = 29`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`ef23be21d6c07448`** — *"La gran mayoría de mujeres solo está contigo por conveniencia"* (comment, `ar_id = 30`)
- Actual: `1.1`.
- Propuesta: `1.3`, `4.2`.
- **[RECATEGORIZAR]** Igual que `6983ada882e8a729`.

### 2.4. Comentarios del post `b0bcbbb5eb375a41`

**`e2cd4ab277182465`** — *"Y así hay muchas..."* (comment, `ar_id = 31`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente explícito, aislado.

**`fcd0b54ed754a540`** — *"claro claro no se trata de música, se trata de hombre deconstruide vs malandro"* (comment, `ar_id = 32`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Borderline — *"deconstruide"* es jerga de manosfera Cat. 4.3, pero el comentario no construye un ataque. Sin referente femenino explícito. Mantengo `ninguna`.

**`2020cf0150b86856`** — *"En mi experiencia si eres mestizo café con leche, pero tienes más actitudes de hombre blanco, prácticamente ya valiste mergas para el ligue"* (comment, `ar_id = 33`)
- Actual: `1.1`, `5.1`.
- Propuesta: `1.3`, `4.2`, *quitar `5.1`*.
- **[RECATEGORIZAR]** El texto no prescribe roles domésticos (no es 1.1). Construye una **jerarquía masculina** según actitudes ("hombre blanco" como ideal) — encaja con **4.2** (desinformación / taxonomías de dominación). El sesgo hacia "actitudes" como valor de ligue también activa **1.3** (doble estándar, tratamiento asimétrico de la mujer como objeto a "valuar"). `5.1` sobra: el contenido es explícito.

**`ed489d3558a69eef`** — *"Para el aliade y la f3m1 nizta"* (comment, `ar_id = 34`)
- Actual: `1.3`, `2.2`.
- Propuesta: `4.3`, `4.3`.
- **[RECATEGORIZAR — error grave]** `f3m1 nizta` es leetspeak directo de **feminazi** (marcador algorítmico explícito de Cat. 4.3 en el glosario manosférico, §3.3) y `aliade` es la forma leetspeak de **aliado** emasculado (Cat. 4.3 según jerga-manosfera §2). No hay referente al cuerpo (2.2 era body-shaming — fuera). La categoría correcta es **4.3** dos veces (o una entrada cubriendo ambas con etiqueta *feminazi* + *aliade*).

**`1635ffd5d8837cf6`** — *"[USUARIO_FB]"* (comment, `ar_id = 35`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`d00e75474ff087a6`** — *"Es chistoso por qué es cierto..."* (comment, `ar_id = 36`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`a4305690f1e373f9`** — *"jajajaja"* (comment, `ar_id = 37`)
- Actual: `VDG_SALVAGUARDA_FALSO_POSITIVO` sin subdim.
- Propuesta: `5.3` (explícito) o `ninguna`.
- **[DE ACUERDO en espíritu]** Es un caso canónico de Cat. 5.3: la presencia de `jajaja` no es por sí misma violencia. Sugiero precisar la sub-dimensión como **5.3** (falso positivo por risa suelta) para que el label no quede huérfano.

**`8b70afaf7ae522f0`** — *"Un clasico"* (comment, `ar_id = 38`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`7816e512b504b818`** — (sin texto, `ar_id = 39`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`06a914582038bc43`** — *"Los escenarios que tienen que crear en IA para sus fantasías están bien raros"* (comment, `ar_id = 40`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino.

**`e355f12847ca56e7`** — *"No es q la chica sea mala es q el hombre hoy día quiere hacer el papel de mujer a la mujer es quien le toca cocinar y criar al bebe"* (comment, `ar_id = 41`)
- Actual: `ninguna`.
- Propuesta: `1.1`, `4.2`.
- **[RECATEGORIZAR — falso negativo]** Aquí aparece explícitamente la **Regla 1 de Cat. 1**: imperativo de reclusión doméstica *"a la mujer es quien le toca cocinar y criar al bebe"* + diagnóstico del varón (prescripción recíproca). También carga **4.2**: la división esencialista del "papel de mujer" como opuesto al "hombre de hoy" es narrativa manosférica de victimismo. Severidad al menos *baja-media*.

**`7e6c8887fea366de`** — *"No que a las feministas no les hacen caso jaja"* (comment, `ar_id = 42`)
- Actual: `ninguna` (con error de parseo).
- Propuesta: `4.3`, `6.1`.
- **[RECATEGORIZAR — falso negativo]** El comentario minimiza/deslegitima a las feministas como colectivo. Activaría la **Regla 3 de Cat. 4** (troleo de género) y la **Regla 1 de Cat. 6** (deslegitimación ideológica: *"traumada / ardida / exageradas"* — el marcador genérico es *caricatura del feminismo*). El `jaja` final es Cat. 5.2 (humor hostil). En el peor caso, al menos **6.1**.

**`b7aff28bc7d3c1de`** — *"A mí me da igual con mujer o sin mujer la paja no falta"* (comment, `ar_id = 43`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Vulgareo pero sin referente femenino-objetivado ni marcador VDG.

**`d160eac77321b71d`** — *"Creo que Eva se golpeó la cabeza al momento de que Dios la creo"* (comment, `ar_id = 44`)
- Actual: `ninguna`.
- Propuesta: `1.2`, `6.1`.
- **[RECATEGORIZAR — falso negativo]** Atribución directa de **inferioridad cognitiva** a la mujer (Eva = toda mujer) — encaja con la **Regla 2 / 1.2** (marcadores: *estupidez*, *niñata*). Adicionalmente, la cita bíblica funciona como **deslegitimación del feminismo por esencialismo religioso** (Cat. 6.1). Severidad *baja-media*.

**`5fbccd33967c9c0b`** — *"Les gusta el desafío, la aventura Y la imagen de bandido... Para después quejarse"* (comment, `ar_id = 45`)
- Actual: `ninguna`.
- Propuesta: `1.3`, `4.2`.
- **[RECATEGORIZAR — falso negativo]** Triple inferencia misógina: (a) generalización de "les gusta X" → colectivo femenino; (b) esencialismo hipersexual; (c) *"para después quejarse"* invierte la responsabilidad (marcador Cat. 1 Regla 3). Es desinformación victimista (Cat. 4.2). Severidad *baja*.

**`9a56c48901821349`** — *"Ahí vienen los 'chicos buenos' a proyectarse jajaja..."* (comment, `ar_id = 46`)
- Actual: `5.1`.
- Propuesta: `5.2` o `ninguna`.
- **[RECATEGORIZAR]** El blanco son los "chicos buenos" (varones que 'proyectan' sobre las mujeres), no las mujeres. No encuentro un ataque directo hacia mujeres en este enunciado; sí hay **humor hostil** (5.2) hacia la masculinidad idealizada. Si el contexto del hilo apunta a una crítica feminsta del discurso manosférico, el contenido se acerca a una reapropiación/crítica y debería caer en **5.3** (falso positivo). Sugiero `5.2` con `5.3` como segunda etiqueta.

**`e94db76c3e610017`** — *"Se lo está diciendo al tipo."* (comment, `ar_id = 47`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`247eade36a76b5ad`** — *"Eso es por qué el man no tiene energía masculina"* (comment, `ar_id = 48`)
- Actual: `1.1`.
- Propuesta: `4.1`, `4.2`.
- **[RECATEGORIZAR]** El texto es una invocación al concepto de *"energía masculina"* — léxico propio de la **sub-cultura masculinista** (Cat. 4.1). Además patologiza al varón que no encaja (Cat. 4.2, victimismo invertido del varón "débil"). No prescribe roles femeninos, por lo que 1.1 no aplica.

**`c559ec3ef418584a`** — *"oelo morado mas encima,,, noo gracias !"* (comment, `ar_id = 49`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`52dda3c28962f918`** — *"Los hombres tienen que usar IA para únicamente representar escenarios imaginarios"* (comment, `ar_id = 50`)
- Actual: `1.1`.
- Propuesta: `ninguna`.
- **[RECATEGORIZAR — falso positivo]** Sin referente femenino, sin marcadores de la Cat. 1. La crítica se dirige a los hombres (uso de IA), no a las mujeres. El comentario no encaja en ninguna regla de las categorías 1–6.

### 2.5. Comentarios del post `3741fe9979b310c6`

**`6caefde6d4c0bc54`** — *"a lo que se ve ellas tienen más que el"* (comment, `ar_id = 51`)
- Actual: `1.1` con `tiene_violencia=false`.
- Propuesta: `ninguna`.
- **[RECATEGORIZAR]** Texto truncado, sin referente femenino claro y sin marcadores. La propia base marca `tiene_violencia=false`, lo que valida la reclasificación a `ninguna`.

**`8bd862e36f3735c0`** — *"[USUARIO_FB]"* (comment, `ar_id = 52`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`b177ef1b0bf960bf`** — *"Ya saben muchachos si ven que alguien las agrade, asi la estén matando es mejor no meterse ignorarlo y seguir es consejo de ellas mismas , no vaya a ser qur lo demande a usted por ayudarla sin su consentimiento jajaja"* (comment, `ar_id = 53`)
- Actual: `3.1`, `1.2`, `5.1`.
- Propuesta: `3.3`, `6.3`, `5.2`.
- **[RECATEGORIZAR — error grave]** No hay promesa de agresión física ni léxico de golpiza (no es 3.1). El texto **normaliza la violencia letal** al recomendar *"es mejor no meterse […] asi la estén matando"* → **Regla 3 / 3.3 (Apología al feminicidio y deshumanización)**. La coletilla *"es consejo de ellas mismas"* invierte la responsabilidad (3.3). El cierre *"no vaya a ser que lo demande por ayudarla sin su consentimiento"* es **Cat. 6 Regla 3** (tergiversación: acusa a las feministas de perseguir al varón por ayudar). El `jajaja` es **Cat. 5.2 (humor hostil)**.

**`4d828911cabce8cd`** — *"yo veo puros wasones jajajajaa"* (comment, `ar_id = 54`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`74da4732a892ce97`** — *"El patriarcado me da patriarcado??"* (comment, `ar_id = 55`)
- Actual: `1.1`.
- Propuesta: `6.1` (con texto de denuncia) o `4.2`.
- **[RECATEGORIZAR]** El enunciado ironiza/desestima el concepto de patriarcado — es **deslegitimación ideológica** (Cat. 6.1: *"traumadas, exageradas, histéricas"* → caricatura del feminismo). Sin imperativo doméstico ni marcador de Cat. 1, por lo que 1.1 no aplica. Severidad *baja*.

**`d33f19d5eac7c764`** — *"Ni la IA entiende el feminismo"* (comment, `ar_id = 56`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Es una broma genérica sin marcador VDG.

**`804fbd6335aab52c`** — *"Pues en los carteles veo cosas logicas, a quien le molesta eso? Quieren a una mujer controlada? Quieren que las mujeres mueran? Les importa la opinión de otros sobre su cuerpo? Yo creo que todos pensamos lo mismo que dicen los carteles, o quien no? Cual es el lio?"* (comment, `ar_id = 57`)
- Actual: `2.1`, `1.2`, `5.1`.
- Propuesta: `5.3` (falso positivo por denuncia) o `ninguna`.
- **[RECATEGORIZAR — falso positivo]** El comentario es una **defensa feminista** del derecho a protestar: las preguntas retóricas *"¿Quieren una mujer controlada? ¿Quieren que las mujeres mueran?"* y el rechazo al escrutinio corporal funcionan como **marcadores mitigadores de Cat. 5.3** (verbo de denuncia + cuestionamiento de la cosificación). Cat. 2.1 / 1.2 no aplican porque no hay ningún adjetivo cosificador ni invalidante *propio del comentario* — la mención *"opinión de otros sobre su cuerpo"* es **crítica** del body-shaming, no body-shaming. La fila debería reclasificarse como **Cat. 5.3** (reapropiación / denuncia) y no como VDG.

**`32cffa6031670f8e`** — *"Yo por las únicas que lucho, es por las nutrias, ni una menos, vivas las queremos."* (comment, `ar_id = 58`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Hashtags y consignas feministas — reapropiación positiva (Cat. 5.3).

**`df44aa3a18434718`** — *"Suban a ponerle al jale acá las esperamos ...."* (comment, `ar_id = 59`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`f9703d6d41e170d1`** — *"Usando IA porque no puede encontrar un imagen real: Conservadores enojándose por cosas imaginarias"* (comment, `ar_id = 60`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Crítica política, sin marcador VDG.

### 2.6. Comentarios sueltos (otros posts)

**`f787d814b5a47750`** — *"Ahora resulta que los hombres no engañan"* (comment, `ar_id = 61`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Sin referente femenino-objetivado.

**`b27587532d3bdeca`** — *"[USUARIO_FB] GIPHY"* (comment, `ar_id = 62`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`2bcbbf01c02661d1`** — *"[USUARIO_FB] GIPHY"* (comment, `ar_id = 63`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`449e8848a2128407`** — *"Los ruquitos que no le hallan a la tecnología"* (comment, `ar_id = 64`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`89b9e9f5dd02b741`** — *"[USUARIO_FB] 12 h"* (comment, `ar_id = 65`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`b7d6c7e6ce7a0402`** — *"Gracias por tus consejos xd"* (comment, `ar_id = 66`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`ad4a9baac6f43142`** — *"[USUARIO_FB]"* (comment, `ar_id = 67`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

### 2.7. Comentarios del post `3aa02333fdc6e34e`

**`a2b4f447a9e0d275`** — *"Autor Mentalidad 1% Revisa el manual aquí https://mentalidad1.com/"* (comment, `ar_id = 68`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Auto-promoción del autor de la página.

**`d09fd0fa741fd562`** — *"Plandemia no te go ese problema por que ellas son las que me dan cariño y pagan todo"* (comment, `ar_id = 69`)
- Actual: `ninguna`.
- **[DE ACUERDO con reparos]** Borderline — generalización sobre mujeres ("ellas… pagan todo"). Podría discutirse como Cat. 1.3, pero al ser un comentario de *alivio* y no de ataque, lo dejo en `ninguna`.

**`956858f99fe0f7fe`** — *"Es un pendejo pero así las buscan xD..."* (comment, `ar_id = 70`)
- Actual: `ninguna`.
- **[DE ACUERDO]** Crítica al autor/página.

**`3dfe60c1fbf2e1a8`** — *"Jajajajajaja, noo, ni madres!! La mía les cobraba."* (comment, `ar_id = 71`)
- Actual: `5.1`.
- Propuesta: `5.3` (reapropiación) o `ninguna`.
- **[RECATEGORIZAR]** El texto es un comentario de un varón que bromea sobre su esposa cobrando — chiste coloquial sin marcadores VDG. No hay sexismo implícito hacia mujeres (5.1). El `jajaja` solo es Cat. 5.3 o `ninguna`. Si el contexto del hilo apunta a crítica del discurso de la página, lo correcto es **5.3**.

**`94a5252cf77e41e6`** — *"Todos los días sale un pendejo a la calle el que lo atrape es de el"* (comment, `ar_id = 72`)
- Actual: `VDG_VIOLENCIA_SIMBOLICA` (sin subdim). La propia justificación dice *"aunque la agresión no está estrictamente motivada por el género"*.
- Propuesta: `VIOLENCIA_COMUN` o `ninguna`.
- **[RECATEGORIZAR — error grave]** La propia nota reconoce que **no hay motivación de género** y, además, no hay referente femenino. Por el protocolo `Regla de exclusión de violencia común`, este comentario **no debe** estar en Cat. 1. Lo correcto: marcar `exclusion_label = VIOLENCIA_COMUN` (como `d782af3f81de2512` y `c5be7323a435b26c`) o, en su defecto, `ninguna`.

**`b9a25039be6c7770`** — *"Hola.correto.excelente.mensaje.maestro.me.reflejo.cracias"* (comment, `ar_id = 73`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`72acc7815981bf8e`** — *"[USUARIO_FB] GIPHY"* (comment, `ar_id = 74`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`c5be7323a435b26c`** — *"Por eso un cafesito"* (comment, `ar_id = 75`)
- Actual: `ninguna` + `exclusion_label=VIOLENCIA_COMUN`.
- **[DE ACUERDO]** Sin referente femenino, correctamente excluido.

**`9e768e369f38ae29`** — *"No es tan así si tenés más de 60 años y andas con una muchacha joven…"* (comment, `ar_id = 76`)
- Actual: `ninguna`.
- **[DE ACUERDO con reparos]** Es respuesta a otro comentario y no contiene marcadores por sí mismo.

**`8cd4924a57e945dc`** — *"Jajajaja muy cierto suele suceder"* (comment, `ar_id = 77`)
- Actual: `ninguna`.
- **[DE ACUERDO]**

**`6ac63c8dd7b3dbcd`** — *"No es tan así si tenés más de 60 años y andas con una muchacha joven… tampoco es que hay que pagar todo Pero por joven y hermoso que ya no sos no tenes más chances cuando ya estás viejo y feo jajaja si no colaboras con nada no se te acerca ninguna, un negocio es un negocio... Viva la jubilación que en el bolsillo no te la vas a llevar jajajaja jajajaja Ese sería el plan l plan B es andar con una vieja mas fea que vos que también rompe las pelotas, se quejan, te piden y te consumen tiempo, salud y dinero como son todas las mujeres Pero está ves es vieja y fea y por eso a ningún hombre le interesa... Nada es gratis en esta vida algo tiene que costar, la más cara es una esposa que ya tuve y siempre están enculada o les duele la cabeza... Ustedes no se Pero yo que ya tengo 67 me quedo con el plan A que no falla..."* (comment, `ar_id = 78`)
- Actual: `3.1` (justificación: *"insultos directos dirigidos a los hombres basados en su edad y apariencia física"*).
- Propuesta: `1.3`, `4.2`, `2.3`.
- **[RECATEGORIZAR — error grave]** La justificación está invertida: el texto no insulta a los hombres, **desvaloriza a las mujeres** (3.1 no aplica porque no hay amenaza de daño físico, solo menosprecio). Contiene:
  - **Cat. 1.3 / Regla 3** (doble estándar moral y desvalorización): *"como son todas las mujeres"*, *"rompe las pelotas, se quejan, te piden"*, *"un negocio es un negocio"*, *"nada es gratis en esta vida"*, *"la más cara es una esposa"*.
  - **Cat. 4.2** (desinformación victimista): la división esencialista mujeres-mercancía.
  - **Cat. 2.3** (slut-shaming / doble estándar sexual): *"siempre están enculada o les duele la cabeza"*, *"una vieja más fea"*.
  - Severidad *media*.

---

## 3. Resumen de cambios sugeridos (vista rápida)

| `content_id` | `ar_id` | Categoría actual | Categoría(s) propuesta(s) | Tipo de cambio |
|--------------|--------:|------------------|---------------------------|----------------|
| `0f3e884a8a124fd1_p0` | 1 | `1.1`, `2.1`, `4`, `5.1` | `1.3`, `2.3`, `4.2` | Corrección de sub-dim + quitar `5.1` |
| `0f3e884a8a124fd1_p2` | 3 | `3.1` | `1.3`, `4.1`, `4.2` | Re-categorización completa (no es Cat. 3) |
| `dc8ae80a3ae35f92` | 4 | `1.1`, `5.1` | `1.3`, `4.1`, `4.2` | Sub-dim + quitar `5.1` |
| `b0bcbbb5eb375a41` | 6 | `1.1`, `2.2`, `5.1` | `1.3`, `2.3`, `4.2` | Sub-dim + quitar `5.1` |
| `2effd62b3d4cbac5` | 14 | `1.2` | `1.3` | Sub-dim |
| `a1478d1dd8727dd4` | 17 | `1.2` | `ninguna` | **Falso positivo** |
| `6983ada882e8a729` | 19 | `1.1` | `1.3`, `4.2` | Sub-dim + agregar 4.2 |
| `c6cf703c604b5599` | 25 | `1.2` | `1.3` | Sub-dim |
| `1f09dfc016268ce8` | 28 | `1.2` | `ninguna` | **Falso positivo** |
| `ef23be21d6c07448` | 30 | `1.1` | `1.3`, `4.2` | Sub-dim + agregar 4.2 |
| `2020cf0150b86856` | 33 | `1.1`, `5.1` | `1.3`, `4.2` | Re-categorización + quitar `5.1` |
| `ed489d3558a69eef` | 34 | `1.3`, `2.2` | `4.3` (×2) | **Manosfera no Cat. 1/2** |
| `a4305690f1e373f9` | 37 | `SAFEGUARD` (sin subdim) | `5.3` o `ninguna` | Precisar sub-dim |
| `e355f12847ca56e7` | 41 | `ninguna` | `1.1`, `4.2` | **Falso negativo** |
| `7e6c8887fea366de` | 42 | `ninguna` | `4.3`, `6.1`, `5.2` | **Falso negativo** |
| `d160eac77321b71d` | 44 | `ninguna` | `1.2`, `6.1` | **Falso negativo** |
| `5fbccd33967c9c0b` | 45 | `ninguna` | `1.3`, `4.2` | **Falso negativo** |
| `9a56c48901821349` | 46 | `5.1` | `5.2` o `ninguna` | Re-categorización |
| `247eade36a76b5ad` | 48 | `1.1` | `4.1`, `4.2` | Re-categorización (no es Cat. 1) |
| `52dda3c28962f918` | 50 | `1.1` | `ninguna` | **Falso positivo** |
| `6caefde6d4c0bc54` | 51 | `1.1` (`tiene_violencia=false`) | `ninguna` | Coherencia interna |
| `b177ef1b0bf960bf` | 53 | `3.1`, `1.2`, `5.1` | `3.3`, `6.3`, `5.2` | **Error grave — apología al fem.** |
| `74da4732a892ce97` | 55 | `1.1` | `6.1` (o `4.2`) | Re-categorización |
| `804fbd6335aab52c` | 57 | `2.1`, `1.2`, `5.1` | `5.3` o `ninguna` | **Falso positivo (es defensa fem.)** |
| `3dfe60c1fbf2e1a8` | 71 | `5.1` | `5.3` o `ninguna` | Re-categorización |
| `94a5252cf77e41e6` | 72 | `VDG_VIOLENCIA_SIMBOLICA` | `VIOLENCIA_COMUN` o `ninguna` | **Error grave** |
| `6ac63c8dd7b3dbcd` | 78 | `3.1` | `1.3`, `4.2`, `2.3` | **Error grave — no es Cat. 3** |

---

## 4. Recomendaciones de calibración

1. **Endurecer la coocurrencia semántica.** Forzar que toda clasificación en Cat. 1 / 2 / 3 / 6 requiera un pronombre o sustantivo femenino **explícito** en el mismo enunciado. Eliminaría de raíz los falsos positivos tipo `a1478d1dd8727dd4`, `1f09dfc016268ce8`, `52dda3c28962f918`, `94a5252cf77e41e6`.
2. **Mapa imperativo ↔ marcador.** Antes de asignar `1.1`, exigir al menos uno de los marcadores `a lavar | a limpiar | cuidar de sus hijos | pónganse a barrer | tener recogido`. Si no aparece, descartar 1.1 y evaluar 1.2 / 1.3.
3. **Tabla de jerga manosférica como diccionario dedicado.** `f3m1 nizta`, `aliade`, `beta`, `del 1%`, `red pill`, `chico bueno`, `energía masculina`, `tipo del KFC`, `blue pill`, `mangina` deben mapear **primero** a Cat. 4 antes de evaluar las demás. Esto corrige `0f3e884a8a124fd1_p0`, `0f3e884a8a124fd1_p2`, `dc8ae80a3ae35f92`, `b0bcbbb5eb375a41`, `2020cf0150b86856`, `ed489d3558a69eef`, `247eade36a76b5ad`, `6ac63c8dd7b3dbcd`.
4. **Distinción 5.1 / 5.2 / 5.3.** Separar el output del clasificador Cat. 5 en tres *buckets*:
   - `5.1` → conserva como ataque (severidad baja).
   - `5.2` → conserva como ataque (humor hostil).
   - `5.3` → marca como **no VDG** (reapropiación / denuncia) para alimentar el feedback de falsos positivos.
5. **Cat. 3 con cautela.** Solo asignar `3.x` cuando aparezca léxico letal, marcador mutado (leetspeak) o la construcción *"por mujeres como estas / por eso ocurren los feminicidios / justicia de miércoles / se lo buscaron"*. Para textos que invocan la violencia pero la **minimizan** (*"es mejor no meterse aunque la estén matando"*), forzar sub-dim `3.3`, no `3.1`.
6. **Detección de defensas feministas.** Añadir un clasificador auxiliar binario `es_defensa_feminista` que se dispare con marcadores mitigadores del glosario (sección 3: *"arcaica, retrógrada, denunciar, repudiar, #NiUnaMenos, eres un crack"*) y obligue a sobreescribir la categoría a `5.3` o `ninguna`. Resolvería `7e6c8887fea366de`, `d33f19d5eac7c764`, `804fbd6335aab52c`.

---

*Auditoría preparada a partir de los documentos en `knowledge/categorias-violencia-genero-digital/` (versión junio 2026). Cualquier discrepancia con el documento de categorización debe prevalecer sobre el veredicto aquí expresado.*
