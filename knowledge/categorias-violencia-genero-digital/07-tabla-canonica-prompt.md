---
tipo: Tabla canónica para prompt
proposito: Single source of truth para category_mapping.py y los bloques del prompt
fecha: 2026-07-12
---

# Tabla canónica de prompt — sub-dimensiones y marcadores

Este documento es la **fuente de verdad** entre los glosarios de
`knowledge/categorias-violencia-genero-digital/glosario/` y la tabla
compacta que `RAGClassifier._build_prompt()` inyecta en el prompt del
LLM.

Cada fila tiene:

- **definición** alineada con los documentos 01-06.
- **marcadores canónicos** — lista cerrada de palabras/frases que el
  LLM debe buscar primero; extraídas del glosario correspondiente.
- **anti-marcadores** — tokens que, si están presentes, _anulan_ la
  categoría (van a Cat. 5.3 si funcionan como denuncia).
- **leetspeak** — variantes tipográficas conocidas.

---

## Categoría 1 — Violencia simbólica

### 1.1 — Roles tradicionales y de sumisión (imperativos doméstico-privados)

- **Definición (doc 01, Regla 1):** imperativos hacia el ámbito privado
  (cocina, cuidado, estética). REQUIERE imperativo explícito.
- **Marcadores:** `a lavar`, `a limpiar`, `cuidar de sus hijos`,
  `cocinar`, `criar al bebé`, `pónganse a barrer`, `tener recogido`,
  `mujer al volante`, `mujer florero`, `calladita`, `niñata`,
  `a la mujer le toca…`.
- **Errores típicos (auditoría 2026-07-12):** el LLM usó 1.1 para
  descalificaciones genéricas (`como son todas las mujeres`) — esas van
  a 1.3.

### 1.2 — Incompetencia e inferioridad intelectual o física

- **Definición (doc 01, Regla 2):** atributos peyorativos sobre
  capacidades cognitivas, físicas, de conducción, etc. Caso bíblico
  arquetípico: Eva.
- **Marcadores:** `estupidez`, `incapaz`, `tonta`, `inútil`,
  `mujer al volante`, `no sabe`, `se golpeó la cabeza`,
  `le falta un hervor`.
- **Errores típicos:** el LLM usó 1.2 para frases como
  *"No debes amar por completo ni confiar en una mujer"* — eso es 1.3
  (desvalorización genérica), no 1.2 (atribución de incapacidad).

### 1.3 — Doble estándar moral / desvalorización genérica del colectivo femenino

- **Definición (doc 01, Regla 3):** generalizaciones desvalorizantes,
  patologización o inversión de responsabilidad. La frase "para después
  quejarse" / "no se dan a respetar" es la firma.
- **Marcadores:** `son todas iguales`, `no se dan a respetar`,
  `para después quejarse`, `locas`, `ridículas`, `viejas webonas`,
  `como son todas las mujeres`, `no debes confiar en una mujer`.
- **Errores típicos:** este código fue sistemáticamente sub-usado; el
  LLM prefería 1.1 por defecto.

---

## Categoría 2 — Cosificación / slut-shaming

### 2.1 — Cosificación corporal o hipersexualización no consentida

- **Marcadores:** `packs`, `enseñando las nalgas`, `naquitas`,
  `mostrá las tetas`, `para eso estás`, `objetivar`.

### 2.2 — Slut-shaming / juzgamiento anatómico

- **Marcadores:** `zorra`, `puta`, `perra`, `guarra`, `subió de peso`,
  `está re gorda`, `está re flaca`, `no tiene tetas`, `no tiene culo`,
  `vieja fea`.

### 2.3 — Doble estándar sexual / juzgar la conducta sexual femenina

- **Marcadores:** `calza ajustada`, `en la cama piden`,
  `siempre están enculada`, `les duele la cabeza`, `consentida`.
- **Caso auditor 2026-07-12:** el comentario
  *"siempre están enculada o les duele la cabeza"* (ar_id=78) estaba
  mal clasificado como Cat. 3.1; va a 2.3 + 1.3 + 4.2.

---

## Categoría 3 — Hostilidad y apología al feminicidio

### 3.1 — Amenaza explícita de agresión física o letal

- **Marcadores:** `a puñetazo limpio`, `golpeen su cara`, `disciplina`,
  `hija de puta` (en contexto amenazante), `la voy a…`, `te voy a…`.

### 3.2 — Léxico letal mutado / deseo de muerte explícito

- **Marcadores:** `mu3rte`, `m4tar`, `asesin0s`, `corte la cabeza`,
  `muere`.
- **Leetspeak crítico:** `m4tar`/`mu3rte`/`ases1n0s` suelen aparecer
  deliberadamente para evadir filtros simples.

### 3.3 — Apología al feminicidio / normalización o minimización de la violencia

- **Marcadores:** `por mujeres como estas`,
  `por eso ocurren los feminicidios`, `justicia de miércoles`,
  `se lo buscaron`, `es mejor no meterse aunque la estén matando`,
  `asi la estén matando`.
- **Caso auditor:** el comentario *"es mejor no meterse aunque la
  estén matando"* (ar_id=53) estaba mal como 3.1; va a 3.3.

---

## Categoría 4 — Manosfera / antifeminismo

### 4.1 — Subculturas masculinistas y taxonomías de dominación

- **Marcadores:** `redpill`, `red pill`, `pastilla roja`, `beta`,
  `chico bueno`, `del 1%`, `mgtow`, `incel`, `mra`, `pua`,
  `white knight`, `energía masculina`, `mangina`, `pagafantas`,
  `huelebragas`.

### 4.2 — Desinformación de género / victimismo masculino

- **Marcadores:** `mentalidad 1%`, `alpha`, `hipergamia`,
  `gold digger`, `actitudes de hombre blanco`, `matriz`,
  `mujeres modernas`, `degeneración`.

### 4.3 — Troleo de género / jerga feminazi-aliade / animalización

- **Marcadores:** `feminazi`, `hembrista`, `mangina`, `pagafantas`,
  `huelebragas`, `femoid`, `foid`, `perra`, `gata`, `gallina`, `foca`,
  `mono`, `cabra`.
- **Leetspeak crítico:** `f3m1 nizta` (feminazi), `aliade`
  (aliado emasculado), `fe-mi-nis-ta`.
- **Caso auditor:** el comentario `Para el aliade y la f3m1 nizta`
  (ar_id=34) estaba mal como 1.3 + 2.2; va a 4.3 (×2).

---

## Categoría 5 — Salvaguarda, sarcasmo y falsos positivos

### 5.1 — Sarcasmo / ironía que vehiculariza un ataque

- **Marcadores:** `calladita te ves más bonita`, `tenías que ser mujer`,
  `las mujeres no saben`, `tú haz lo que yo te diga`.
- **Decisión:** esta categoría SÍ es VDG; devolver siempre la categoría
  sustantiva (1.x, 2.x, etc.) y agregar 5.1 solo si el sarcasmo ES la
  carga agresiva principal.

### 5.2 — Humor hostil que enmascara una agresión

- **Marcadores:** `jajaja`, `es solo humor`, `era una broma`,
  `generación de cristal`.
- **Decisión:** análoga a 5.1 — VDG real.

### 5.3 — Reapropiación / cita / denuncia con marcadores mitigadores

- **Marcadores mitigadores:** `arcaica`, `retrógrada`, `patriarcal`,
  `machista`, `denunciar`, `repudiar`, `visibilizar`,
  `#NiUnaMenos`, `#8M`, `#VivasNosQueramos`, comillas, paréntesis,
  `según`, `como dice`.
- **Decisión:** NO es VDG; devolver `clasificaciones: []` con
  `es_falso_positivo_probable: true`.
- **Caso auditor 2026-07-12:**
  - *"Quieren una mujer controlada? Quieren que las mujeres mueran?"*
    (ar_id=57) — defensa feminista — iba como 2.1/1.2; va a 5.3.
  - *"La mía les cobraba jajaja"* (ar_id=71) — chiste coloquial — iba
    como 5.1; va a 5.3.

---

## Categoría 6 — Desacreditación de activistas

### 6.1 — Deslegitimación ideológica del feminismo en abstracto

- **Marcadores:** `traumada`, `ardida`, `tóxicas`,
  `feminismo radical`, `exageradas`, `histéricas`, `ridículas`,
  `misándricas`.

### 6.2 — Ataque a activista específica (nombre propio)

- **Marcadores:** nombre propio de feministas + adjetivo peyorativo.
  Ej.: `Victoria Zanón + insulto`, `Ofelia Fernández + …`.

### 6.3 — Tergiversación: feminismo como perseguidor

- **Marcadores:** `doble moral`, `victimización invertida`,
  `feminismo busca`, `ellas mismas se lo buscan`,
  `es consejo de ellas mismas`, `que lo demande por ayudarla`.
- **Caso auditor 2026-07-12:** el comentario *"no vaya a ser que lo
  demande a usted por ayudarla sin su consentimiento"* (ar_id=53) es
  claramente 6.3 — feminismo como perseguidor.

---

## Marcadores universales de presencia femenina (para Cat. 1/2/3/6)

El prompt exige coocurrencia semántica antes de asignar cualquier
categoría sustantiva. Si el texto no contiene NINGUNO de los siguientes
tokens ni un nombre propio femenino, devolver `clasificaciones: []`.

```
ella(s), mujer(es), chica(s), pibas, vieja(s), fémina(s),
esposa(s), novia(s), madre(s), hija(s), hermana(s), tía,
stacy, karen, becky,
feminazi, hembrista, feministas, activista(s), colectivo feminista,
eva, maría
```

Excepción: Cat. 4 (manosfera pura) y Cat. 5 (sarcasmo/reapropiación)
pueden dispararse sin referente femenino explícito.

---

## Leetspeak decoder (catálogo cerrado)

```
f3m1 nizta       → feminazi
fe-mi-nis-ta     → feminista
f3minista        → feminista
mu3rte           → muerte
m4tar            → matar
asesin0s         → asesinos
ases1n0s         → asesinos
marikon / m4ric0n → maricón
h1j4 d3 put4 / h1j4 d3 pvt4 → hija de puta
put@ / pvt@      → puta
muj3r / mvj3r    → mujer
degenerac18n     → degeneración
acost4rs3        → acostarse
cog13nd8 / c8g1d8 → cogiendo / cogida
f8ll9 / f8ll4    → follar
acv3sta          → acuesta
mvjeres          → mujeres
```

Aplicar ANTES de evaluar marcadores canónicos.

---

## Marcadores mitigadores (anti-falsos positivos)

Si el texto contiene UNO O MÁS de los siguientes en función de
denuncia/cita/reapropiación, devolver `clasificaciones: []` con
`es_falso_positivo_probable: true`:

```
arcaica, retrógrada, falsa, absurda, ridícula, obsoleta, patética,
patriarcal, machista, conservadora
denunciar, denuncia, evidenciar, rechazar, repudiar, desmontar,
deconstruir, criticar, señalar, visibilizar, luchar, lucha
no es verdad que, en realidad, sin embargo, jamás, nunca,
pero, aunque, a diferencia de
", (, #NiUnaMenos, #8M, #VivasNosQueramos, #FeminismoEs
según, como dice
eres un crack, te amo, hermana, mi vida, amiga, reírse de, ja ja
```

---

## Estadísticas de uso en la auditoría 2026-07-12

| Categoría | Casos auditados | Notas |
|-----------|----------------:|-------|
| 1.1 | 1 (ar_id=41) | Falso negativo — el LLM no detectó el imperativo doméstico. |
| 1.2 | 1 (ar_id=44) | Falso negativo — esencialismo bíblico. |
| 1.3 | 9 | Categoría más frecuente en correcciones (era sub-usada). |
| 2.3 | 2 | Slut-shaming mal clasificado como 2.2. |
| 3.3 | 1 (ar_id=53) | Apología al fem. mal como 3.1. |
| 4.1 | 2 | "Energía masculina" / "beta" mal como 1.1. |
| 4.3 | 2 | `f3m1 nizta` / feministas como chivos expiatorios. |
| 5.1 | 1 (ar_id=46) | Difícil: `chicos buenos` como blanco. |
| 5.3 | 4 | Falsos positivos (chistes coloquiales / defensas feministas). |
| 6.1 | 1 (ar_id=55) | "El patriarcado me da patriarcado". |
| ninguna | 4 | Falsos positivos sobre textos sin referente femenino. |
| VIOLENCIA_COMUN | 1 (ar_id=72) | Insulto genérico sin sesgo de género. |
