---
tipo: Protocolo técnico transversal
aplica_a: Todas las categorías
---

# Protocolo Algorítmico General

Este documento recopila los criterios técnicos de procesamiento de lenguaje natural (PLN) que aplican transversalmente a las seis categorías de violencia de género digital. Su objetivo es homogeneizar el comportamiento del modelo de IA ante fenómenos recurrentes (evasión de filtros, ambigüedad contextual, etc.) independientemente de la categoría que se esté clasificando.

---

## 1. Criterio de coocurrencia semántica

**Aplica a:** todas las categorías.

**Descripción:** El mensaje debe presentar la coocurrencia (proximidad sintáctica en el texto) entre:

- **Sustantivos o pronombres femeninos**: *ellas, las mujeres, la vieja, la niña, la tipa, la piba, féminas, fémina*.
- **Adjetivos, verbos o sintagmas de inferioridad, minorización o servidumbre**, propios de la categoría que se esté evaluando (ver reglas de cada categoría).

**Justificación teórica:** Basado en los estudios de procesamiento de lenguaje natural enfocados en la detección de discursos de odio de García-Díaz et al. (2021).

---

## 2. Criterio de evasión algorítmica (Leetspeak y mutaciones ortográficas)

**Aplica a:** Categoría 3 (Hostilidad explícita y apología al feminicidio) — y, preventivamente, a cualquier categoría donde el agresor pueda intentar evadir filtros.

**Descripción:** El software debe estar entrenado para identificar no solo las palabras clave tal como aparecen en el diccionario, sino también sus **mutaciones alfanuméricas y ortográficas** diseñadas para eludir la moderación automática.

**Patrones de evasión documentados:**

| Patrón | Ejemplo original | Mutación |
|--------|------------------|----------|
| Sustitución numérica de vocales | muerte | `mu3rte`, `m4tar`, `asesin0s` |
| Inserción de caracteres especiales | hija de puta | `hij@ de pút@` |
| Separación silábica | feminista | `fe-mi-nis-ta` |
| Variantes tipográficas | feminazi | `feminaz1`, `feminachy` |
| Uso de sinónimos eufemísticos | asesinato | `sacrificio`, `eliminación` |

**Acción algorítmica:** ante la detección de un patrón que matchea parcialmente con un marcador de la categoría 3 (especialmente verbos de daño letal o sustantivos de víctima femenina), el clasificador debe activar la regla sin requerir coincidencia léxica exacta.

**Justificación teórica:** Las plataformas aplican estrictos "niveles de moderación de contenido" orientados a la remoción inmediata de amenazas letales (Corte Constitucional, 2025, citado en Boletín temático de jurisprudencia 5, p. 49). Como respuesta, los agresores mutan tecnológicamente el discurso.

---

## 3. Criterio de contexto pragmático (antídoto contra falsos positivos)

**Aplica a:** Categoría 5 (Control de resistencia, sarcasmos y falsos positivos) — y como salvaguarda general.

**Descripción:** El algoritmo debe entrenarse bajo perspectivas pragmáticas y de contexto para distinguir entre:

- **Ataque misógino** (uso despectivo del marcador).
- **Denuncia feminista** (uso irónico o crítico del marcador, generalmente con marcadores atenuantes).
- **Reapropiación coloquial** (uso humorístico o de camaradería, sin intención agresiva).

**Marcadores de contexto mitigador (revisar antes de clasificar como ataque):**

- Vocabulario valorativo negativo sobre el marcador: *arcaica, ridícula, falsa, absurda, retrógrada, patriarcal, machista*.
- Verbos de denuncia o crítica explícita: *denunciar, criticar, evidenciar, rechazar, repudiar, desmontar, deconstruir*.
- Conectores de negación o contraposición: *no es verdad que, en realidad, sin embargo, no, jamás, nunca, no debería*.
- Formato de cita o referencia: comillas, paréntesis, hashtags de campaña (`#NiUnaMenos`, `#8M`, `#VivasNosQueremos`).
- Tono coloquial-afectivo: *eres un crack, te amo, hermana, mi vida* (en insultos reapropiados).

**Justificación teórica:** Syafi-Muhammad y Ruldeviyani (2020, citados en Suárez-Álvarez et al., 2025) advierten que la codificación automática presenta graves limitaciones para decodificar expresiones irónicas y frases con doble sentido. Úbeda Cuspinera (2025) documenta empíricamente que los mensajes de denuncia feminista suelen reutilizar los mismos marcadores misóginos con intención opuesta.

---

## 4. Criterio de enunciados imperativos hacia el ámbito privado

**Aplica a:** Categorías 1 y 6 (roles de sumisión y ridiculización).

**Descripción:** Siguiendo los trece criterios propuestos por Schmeisser-Nieto et al. (2022) para identificar contenido sexista, la máquina debe marcar textos que utilicen "enunciados imperativos, exhortativos o llamadas a la acción" (citado en Úbeda Cuspinera, 2025, p. 200) que ordenen a la mujer retroceder al espacio doméstico para invalidar sus opiniones o participación pública.

**Patrones verbales a detectar:**

- Modo imperativo en segunda persona: *vete a lavar, ponte a barrer, deja de opinar*.
- Modo imperativo en tercera persona (prescripción colectiva): *que vayan a cuidar, pónganse a trabajar, déjenlo para los hombres*.
- Exhortaciones disfrazadas de consejo: *deberías estar en tu casa, mejor dedicate a los tuyos*.

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
