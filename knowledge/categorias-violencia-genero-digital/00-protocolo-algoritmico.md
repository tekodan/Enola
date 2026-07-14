---
tipo: Protocolo técnico transversal
aplica_a: Todas las categorías
---

# Protocolo Algorítmico General

Este documento recopila los criterios técnicos de procesamiento de lenguaje natural (PLN) que aplican transversalmente a las seis categorías de violencia de género digital. Su objetivo es homogeneizar el comportamiento del modelo de IA ante fenómenos recurrentes (evasión de filtros, ambigüedad contextual, etc.) independientemente de la categoría que se esté clasificando.

---

## 1. Criterio de coocurrencia semántica

**Aplica a:** todas las categorías **excepto Cat. 4 (manosfera) y Cat. 5 (sarcasmo/reapropiación)**, que pueden dispararse sin referente femenino explícito.

**Descripción:** El mensaje debe presentar la coocurrencia (proximidad sintáctica en el texto) entre:

- **Sustantivos o pronombres femeninos**: *ellas, las mujeres, la vieja, la niña, la tipa, la piba, féminas, fémina, esposa, novia, madre, hermana, tía, feminazi, feministas, colectivo feminista, Eva, María, stacy*.
- **Adjetivos, verbos o sintagmas de inferioridad, minorización o servidumbre**, propios de la categoría que se esté evaluando (ver reglas de cada categoría).

**Acción algorítmica:** si el texto **NO contiene** ningún referente femenino y no es Cat. 4 ni Cat. 5, devolver `clasificaciones: []` con `tiene_violencia: false`. Esta regla elimina falsos positivos como *"Nadie vendrá a salvarte, estás a cargo de tu vida"* (sin referente femenino, era marcado falsamente como Cat. 1.2) y *"Los hombres usan IA para representar escenarios imaginarios"* (crítica al varón, no VDG).

**Justificación teórica:** Basado en los estudios de procesamiento de lenguaje natural enfocados en la detección de discursos de odio de García-Díaz et al. (2021).

---

## 2. Criterio de evasión algorítmica (Leetspeak y mutaciones ortográficas)

**Aplica a:** Categoría 3 (Hostilidad explícita y apología al feminicidio) — y, preventivamente, a cualquier categoría donde el agresor pueda intentar evadir filtros. **Crítico para Cat. 4** (manosfera usa leetspeak sistemáticamente).

**Descripción:** El software debe estar entrenado para identificar no solo las palabras clave tal como aparecen en el diccionario, sino también sus **mutaciones alfanuméricas y ortográficas** diseñadas para eludir la moderación automática.

**Patrones de evasión documentados:**

| Patrón | Ejemplo original | Mutación |
|--------|------------------|----------|
| Sustitución numérica de vocales | muerte | `mu3rte`, `m4tar`, `asesin0s` |
| Inserción de caracteres especiales | hija de puta | `hij@ de pút@` |
| Separación silábica | feminista | `fe-mi-nis-ta` |
| Variantes tipográficas | feminazi | `feminaz1`, `feminachy`, `f3m1 nizta` |
| Uso de sinónimos eufemísticos | asesinato | `sacrificio`, `eliminación` |
| Vocal → símbolo | puta | `pút@`, `pvt@` |
| Variantes tipográficas | maricón | `m4ric0n`, `marikon` |
| Emasculación | aliado | `aliade` |

**Acción algorítmica OBLIGATORIA:** Antes de evaluar cualquier marcador, decodificar todas las variantes leetspeak del input. La regla 4.3 ("troleo de género") debe activarse automáticamente ante `f3m1 nizta` o `aliade` — auditoría 2026-07-12 halló que el LLM desconocía estas variantes y las enviaba a Cat. 1.3.

**Justificación teórica:** Las plataformas aplican estrictos "niveles de moderación de contenido" orientados a la remoción inmediata de amenazas letales (Corte Constitucional, 2025, citado en Boletín temático de jurisprudencia 5, p. 49). Como respuesta, los agresores mutan tecnológicamente el discurso.

---

## 3. Criterio de contexto pragmático (antídoto contra falsos positivos)

**Aplica a:** Categoría 5 (Control de resistencia, sarcasmos y falsos positivos) — y como salvaguarda general.

**Descripción:** El algoritmo debe entrenarse bajo perspectivas pragmáticas y de contexto para distinguir entre:

- **Ataque misógino** (uso despectivo del marcador).
- **Denuncia feminista** (uso irónico o crítico del marcador, generalmente con marcadores atenuantes). → **NO es VDG.**
- **Reapropiación coloquial** (uso humorístico o de camaradería, sin intención agresiva). → **NO es VDG.**

**Marcadores de contexto mitigador (revisar antes de clasificar como ataque):**

- Vocabulario valorativo negativo sobre el marcador: *arcaica, ridícula, falsa, absurda, retrógrada, patriarcal, machista*.
- Verbos de denuncia o crítica explícita: *denunciar, criticar, evidenciar, rechazar, repudiar, desmontar, deconstruir*.
- Conectores de negación o contraposición: *no es verdad que, en realidad, sin embargo, no, jamás, nunca, no debería*.
- Formato de cita o referencia: comillas, paréntesis, hashtags de campaña (`#NiUnaMenos`, `#8M`, `#VivasNosQueramos`).
- Tono coloquial-afectivo: *eres un crack, te amo, hermana, mi vida* (en insultos reapropiados).
- **Preguntas retóricas de desafío**: ¿Quieren una mujer controlada? ¿Quieren que las mujeres mueran?

**Caso de la auditoría 2026-07-12 (ar_id=57):** un comentario como *"Pues en los carteles veo cosas logicas. A quien le molesta eso? Quieren a una mujer controlada? Quieren que las mujeres mueran? Les importa la opinión de otros sobre su cuerpo? Yo creo que todos pensamos lo mismo que dicen los carteles"* es una **defensa feminista del derecho a protestar**. Las preguntas retóricas y el rechazo al escrutinio corporal son marcadores mitigadores. El LLM lo había marcado erróneamente como Cat. 2.1 + Cat. 1.2; debe ser `clasificaciones: []` con `es_falso_positivo_probable: true`.

**Justificación teórica:** Syafi-Muhammad y Ruldeviyani (2020, citados en Suárez-Álvarez et al., 2025) advierten que la codificación automática presenta graves limitaciones para decodificar expresiones irónicas y frases con doble sentido. Úbeda Cuspinera (2025) documenta empíricamente que los mensajes de denuncia feminista suelen reutilizar los mismos marcadores misóginos con intención opuesta.

---

## 4. Criterio de enunciados imperativos hacia el ámbito privado

**Aplica a:** Categorías 1.1 y 6 (roles de sumisión y ridiculización).

**Descripción:** Siguiendo los trece criterios propuestos por Schmeisser-Nieto et al. (2022) para identificar contenido sexista, la máquina debe marcar textos que utilicen "enunciados imperativos, exhortativos o llamadas a la acción" (citado en Úbeda Cuspinera, 2025, p. 200) que ordenen a la mujer retroceder al espacio doméstico para invalidar sus opiniones o participación pública.

**Patrones verbales a detectar (REQUIEREN imperativo o prescripción explícita):**

- Modo imperativo en segunda persona: *vete a lavar, ponte a barrer, deja de opinar*.
- Modo imperativo en tercera persona (prescripción colectiva): *que vayan a cuidar, pónganse a trabajar, déjenlo para los hombres*.
- Exhortaciones disfrazadas de consejo: *deberías estar en tu casa, mejor dedicate a los tuyos*.
- Prescripción de rol doméstico con verbo conjugado en indicativo: *"a la mujer es quien le toca cocinar y criar al bebé"* (caso ar_id=41 de la auditoría 2026-07-12).

**ATENCIÓN — diferencia crítica 1.1 vs 1.3 (auditoría 2026-07-12):**

| Caso | Sub-dimensión correcta | Por qué |
|------|------------------------|---------|
| *"a la mujer es quien le toca cocinar y criar al bebe"* | **1.1** | Imperativo de reclusión doméstica explícito. |
| *"como son todas las mujeres"* / *"para después quejarse"* | **1.3** | NO hay imperativo doméstico; es desvalorización genérica del colectivo. |
| *"la mayoría de mujeres solo está contigo por conveniencia"* | **1.3** | NO prescribe roles; generaliza desvalorizando. |
| *"no debes amar por completo ni confiar en una mujer"* | **1.3** | Prescripción moral negativa, no doméstico-privada. |

Regla nemotécnica: **1.1 exige imperativo HOGAREÑO; 1.3 cubre todo lo demás que sea descalificación genérica o doble estándar**.

---

## 4.bis. Criterio de discriminación entre Cat. 3.x (hostilidad letal)

**Aplica a:** Categoría 3 completa.

**Descripción:** La auditoría 2026-07-12 detectó que el LLM asignaba 3.1 (amenaza física) a textos que NO contienen amenaza — la regla 3.1 se usaba como cajón genérico de "lo grave".

| Sub-dim. | Disparador obligatorio | Ejemplo |
|----------|------------------------|---------|
| **3.1** | Verbo de agresión física O amenaza contra una persona específica | *"te voy a", "la voy a", "voy a golpear"* |
| **3.2** | Léxico letal explícito o mutado (matar, muerte, asesinato, *leetspeak*) | *"mu3rte", "m4tar", "corte la cabeza"* |
| **3.3** | Apología, normalización o minimización de la violencia | *"se lo buscaron", "es mejor no meterse aunque la estén matando", "justicia de miércoles"* |

**Caso ar_id=53:** *"ya saben muchachos si ven que alguien las agrade, asi la estén matando es mejor no meterse"* — NO es 3.1 (no hay amenaza directa); es **3.3 (apología al feminicidio)**. Además carga **6.3 (tergiversación: feminismo como perseguidor)** por el cierre *"no vaya a ser que lo demande por ayudarla"*.

---

## 4.ter. Criterio de discriminación entre Cat. 4.x (manosfera)

**Aplica a:** Categoría 4 completa.

**Descripción:** La auditoría 2026-07-12 detectó que el LLM confundía léxico manosférico con Cat. 1 (roles tradicionales) cuando en realidad pertenece a Cat. 4. Regla:

| Sub-dim. | Disparador obligatorio |
|----------|------------------------|
| **4.1** | Taxonomías masculinistas (`beta`, `chico bueno`, `del 1%`, `red pill`, `mgtow`, `incel`, `pua`, `mra`, `energía masculina`, `mentalidad 1%`) |
| **4.2** | Desinformación victimista del varón + esencialismo femenino ("mujeres modernas", "degeneración", "actitudes de hombre blanco") |
| **4.3** | Jerga feminazi, animalización, troleo de género (`feminazi`, `hembrista`, `mangina`, `pagafantas`, `aliade`, `perra`, `zorra`, `foid`, `femoid`) |

**Caso ar_id=34:** *"Para el aliade y la f3m1 nizta"* — es **4.3 (×2)**, NO Cat. 1.3 + Cat. 2.2 como etiquetaba el LLM.

---

## 5. Pipeline general de clasificación

Para cada mensaje recibido por el modelo, se sugiere el siguiente flujo:

1. **Preprocesamiento:** normalización, lematización, detección de leetspeak (aplicar Criterio 2).
2. **Detección de entidades:** identificar pronombres, sustantivos y referentes femeninos (Criterio 1).
3. **Análisis pragmático:** buscar marcadores mitigadores antes de clasificar como ataque (Criterio 3).
4. **Match contra reglas:** evaluar las 3 reglas de cada categoría y devolver la categoría con mayor score.
5. **Validación de subdimensionar:** dentro de la categoría ganadora, identificar la subdimensión activada.
6. **Salida estructurada:**

```json
{
  "categoria": 1,
  "subdimension": "1.1",
  "regla_disparada": "Regla 1",
  "score": 0.87,
  "marcadores_detectados": ["a lavar", "cuidar de sus hijos"],
  "es_falso_positivo_probable": false,
  "evidencia": "Que vayan a limpiar sus casas..."
}
```
