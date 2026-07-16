---
proyecto: Sistema de Categorización de Violencia de Género Digital
tipo: Documento maestro
estado: Taxonomía canónica v2
---

# Sistema de Categorización de Violencia de Género Digital

El sistema operacionaliza la detección algorítmica de ciberviolencia contra las mujeres mediante análisis del discurso, recuperación de conocimiento y clasificación multi-etiqueta.

## Arquitectura del sistema

El sistema se organiza en **6 categorías operativas y 19 subdimensiones**:

- Las categorías 1, 2, 3, 5 y 6 tienen tres subdimensiones.
- La categoría 4 tiene cuatro subdimensiones e incorpora los arquetipos femeninos deshumanizantes como 4.4.
- La categoría 5 se reserva para castigos dirigidos a activistas y mujeres con perfil público.
- La categoría 6 es transversal: micromachismos, humor hostil y salvaguarda contra falsos positivos.
- `MAX_LABELS` permite conservar varias capas independientes de un mismo mensaje.

## Índice de categorías

| # | Categoría | Subdimensiones | Reglas | Gravedad |
|---|-----------|---------------:|------:|----------|
| 1 | [Violencia simbólica y estereotipos de dominación](./01-categoria-1-violencia-simbolica.md) | 3 | 3 | Baja-Media |
| 2 | [Mercantilización corporal](./02-categoria-2-cosificacion-slutshaming.md) | 3 | 3 | Media |
| 3 | [Hostilidad explícita y apología al feminicidio](./03-categoria-3-hostilidad-feminicidio.md) | 3 | 3 | Alta-Extrema |
| 4 | [Discurso ideológico antifeminista y manosfera](./04-categoria-4-manosfera-antifeminismo.md) | 4 | 4 | Media-Alta |
| 5 | [Castigo del empoderamiento femenino](./05-categoria-5-desacreditacion-activistas.md) | 3 | 3 | Media-Alta |
| 6 | [Control de resistencia, sarcasmos y falsos positivos](./06-categoria-6-sarcasmo-falsos-positivos.md) | 3 | 3 | Ortogonal |

## Documentos transversales

- [Protocolo algorítmico general](./00-protocolo-algoritmico.md)
- [Glosario de jerga de la manosfera](./glosario/jerga-manosfera.md)
- [Glosario de argot misógino general](./glosario/argot-misogino-general.md)
- [Marcadores por subdimensión](./glosario/marcadores-por-subdimension.md)
- [Reglas de desempate](./glosario/reglas-desempate.md)
- [Tabla canónica del prompt](./07-tabla-canonica-prompt.md)

## Fronteras principales

- 2.2 es body-shaming por físico, edad, peso o anatomía; 2.3 es slut-shaming por sexualidad, intimidad o vestimenta sancionada.
- 3.1 es castigo físico no letal; 3.2 es deseo directo de muerte; 3.3 es apología o justificación sin amenaza directa.
- 4.1 es jerga y jerarquías manosféricas; 4.2 es oposición antifeminista y victimismo hegemónico; 4.3 castiga a varones aliados; 4.4 deshumaniza a mujeres.
- 1.1 se aplica a mujeres en general; 5.2 exige un ataque público contra activistas, manifestantes, periodistas o políticas.
- 6.3 anula las alertas cuando el marcador ofensivo aparece en denuncia, cita, refutación o reapropiación no agresiva.
