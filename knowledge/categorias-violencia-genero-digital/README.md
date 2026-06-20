---
proyecto: Sistema de Categorización de Violencia de Género Digital
tipo: Documento maestro
estado: Borrador estructurado
---

# Sistema de Categorización de Violencia de Género Digital

Este sistema de categorías tiene como objetivo operacionalizar la detección algorítmica de la ciberviolencia contra las mujeres a partir de un marco teórico sustentado en estudios de violencia de género digital, lingüística computacional y análisis del discurso.

## Arquitectura del sistema

El sistema se organiza en **6 categorías operativas**, cada una con:

- **Definición conceptual** anclada en literatura académica.
- **3 subdimensiones analíticas** que delimitan el fenómeno.
- **3 reglas de inclusión algorítmica** con marcadores léxicos y unidades de análisis empíricas.
- Reglas generales de inclusión específicas de la categoría (cuando aplica).

## Índice de categorías

| # | Categoría | Subdimensiones | Reglas | Gravedad |
|---|-----------|---------------|--------|----------|
| 1 | [Violencia simbólica y estereotipos de dominación](./01-categoria-1-violencia-simbolica.md) | 3 | 3 | Baja-Media |
| 2 | [Cosificación corporal y slut-shaming](./02-categoria-2-cosificacion-slutshaming.md) | 3 | 3 | Media |
| 3 | [Hostilidad explícita y apología al feminicidio](./03-categoria-3-hostilidad-feminicidio.md) | 3 | 3 | Alta-Extrema |
| 4 | [Discurso ideológico antifeminista y manosfera](./04-categoria-4-manosfera-antifeminismo.md) | 3 | 3 | Media-Alta |
| 5 | [Control de resistencia, sarcasmos y falsos positivos](./05-categoria-5-sarcasmo-falsos-positivos.md) | 3 | 3 | Baja (alta complejidad técnica) |
| 6 | [Desacreditación de activistas y mujeres con perfil público](./06-categoria-6-desacreditacion-activistas.md) | 3 | 3 | Media-Alta |

## Documentos transversales

- [Protocolo algorítmico general](./00-protocolo-algoritmico.md) — criterios técnicos que aplican a todas las categorías (leetspeak, coocurrencia semántica, etc.).
- [Glosario de jerga de la manosfera](./glosario/jerga-manosfera.md) — diccionario de neologismos, acrónimos y taxonomías deshumanizantes.
- [Glosario de argot misógino general](./glosario/argot-misogino-general.md) — marcadores léxicos organizados por categoría.

## Estructura de cada categoría

Cada archivo de categoría sigue el siguiente esquema unificado:

1. **Definición Conceptual** — delimitación teórica con citas académicas.
2. **Subdimensiones Analíticas** — desglose del fenómeno en 3 dimensiones operativas.
3. **Reglas de Inclusión Algorítmica** — 3 reglas con la estructura:
   - Descripción algorítmica
   - Marcadores léxicos (argot)
   - Unidades de análisis (ejemplos empíricos)
4. **Reglas Generales de Inclusión Algorítmica** — criterios técnicos específicos de la categoría (cuando aplica).

## Referencias marco

- Bourdieu, P. (1991). *El sentido práctico*.
- Cobo, R. (2020). *Cosificación y vulnerabilidad*.
- García-Díaz et al. (2021). Detección de discurso de odio mediante PLN.
- Lizaralo-Ojeda, Y. y Yanez-Peñúñuri (2021). Ciberviolencia y dominación masculina.
- Özkula, S. y Prieto-Blanco, P. (2025). Manosfera y tecnoculturas reaccionarias.
- Úbeda Cuspinera, M. (2025). Detección algorítmica de discurso sexista.
