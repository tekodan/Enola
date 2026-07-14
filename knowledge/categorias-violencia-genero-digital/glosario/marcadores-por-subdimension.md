---
tipo: Glosario de marcadores canónicos
proposito: Inyectado en el prompt del clasificador como bloque
  MARCADORES_CANONICOS para reducir las confusiones 1.1/1.3, 2.1/2.3 y 4.x
fecha_origen: 2026-07-12 (refactor reglas-codigo → reglas-markdown)
fuente_original: knowledge/categorias-violencia-genero-digital/glosario/argot-misogino-general.md
                  + glosario/jerga-manosfera.md
---

# Marcadores canónicos por subdimensión (inyectables al prompt)

Lista cerrada de **palabras y frases textuales** que el clasificador
debe buscar primero antes de asignar cada par
`(categoria, dimension)`. Es el contrato cerrado del LLM: si el texto
contiene un marcador de una sub-dimensión y la sintaxis lo permite,
ESA sub-dimensión es la candidata primaria.

## Bloque para prompt

```
MARCADORES_CANONICOS (listas cerradas — si una palabra del texto está acá, la
sub-dimensión correspondiente es la candidata primaria, salvo que el contexto
indique otra cosa):

- 1.1 (VDG_VIOLENCIA_SIMBOLICA): a lavar, a limpiar, cuidar de sus hijos, cocinar, criar, pónganse a barrer, tener recogido, mujer al volante, mujer florero, calladita, niñata
- 1.2 (VDG_VIOLENCIA_SIMBOLICA): estupidez, incapaz, tonta, inútil, se golpeó la cabeza, no sirve para nada
- 1.3 (VDG_VIOLENCIA_SIMBOLICA): son todas iguales, no se dan a respetar, para después quejarse, locas, ridículas, viejas webonas, como son todas las mujeres
- 2.1 (VDG_COSIFICACION_SLUTSHAMING): packs, enseñando las nalgas, naquitas, mostrá las tetas, para eso estás
- 2.2 (VDG_COSIFICACION_SLUTSHAMING): zorra, puta, perra, guarra, subió de peso, está re gorda, no tiene tetas, vieja fea
- 2.3 (VDG_COSIFICACION_SLUTSHAMING): calza ajustada, en la cama piden, siempre están enculada, les duele la cabeza, consentida
- 3.1 (VDG_HOSTILIDAD_FEMINICIDIO): a puñetazo limpio, golpeen su cara, disciplina, hija de puta, la voy a, te voy a
- 3.2 (VDG_HOSTILIDAD_FEMINICIDIO): mu3rte, m4tar, asesin0s, corte la cabeza, muere
- 3.3 (VDG_HOSTILIDAD_FEMINICIDIO): por mujeres como estas, por eso ocurren los feminicidios, justicia de miércoles, se lo buscaron, es mejor no meterse, asi la estén matando
- 4.1 (VDG_MANOSFERA_ANTIFEMINISMO): redpill, red pill, pastilla roja, beta, chico bueno, del 1%, mgtow, incel, mra, pua, white knight, energía masculina
- 4.2 (VDG_MANOSFERA_ANTIFEMINISMO): mentalidad 1%, alpha, hipergamia, gold digger, actitudes de hombre blanco, matriz
- 4.3 (VDG_MANOSFERA_ANTIFEMINISMO): feminazi, f3m1 nizta, feminachy, hembrista, mangina, pagafantas, huelebragas, aliade, femoid, foid, perra, gata, gallina, foca, mono, cabra
- 5.1 (VDG_SALVAGUARDA_FALSO_POSITIVO): calladita te ves más bonita, tenías que ser mujer, las mujeres no saben, tú haz lo que yo te diga
- 5.2 (VDG_SALVAGUARDA_FALSO_POSITIVO): jajaja, jajajaja, es solo humor, era una broma, generación de cristal
- 5.3 (VDG_SALVAGUARDA_FALSO_POSITIVO): denuncia, repudiar, rechazar, deconstruir, visibilizar, #NiUnaMenos, #8M, #VivasNosQueramos, patriarcal, machista, arcaica, retrógrada
- 6.1 (VDG_DESACREDITACION_ACTIVISTAS): traumada, ardida, tóxicas, feminismo radical, exageradas, histéricas
- 6.2 (VDG_DESACREDITACION_ACTIVISTAS): viejas webonas, ridículas, váyanse a lavar
- 6.3 (VDG_DESACREDITACION_ACTIVISTAS): doble moral, victimización invertida, feminismo busca, ellas mismas se lo buscan, es consejo de ellas
```

## Reglas de uso

1. **Búsqueda case-insensitive y sin acentos.** El código en
   `src/analyzer/category_mapping.py::load_prompt_block()` que lo
   parsea aplica `unicodedata.normalize("NFKD", ...)` antes de
   comparar.
2. **Substring match dentro de palabra.** El LLM matchea
   `degenerac18n` contra `degeneración` vía el decoder leetspeak,
   NO contra esta lista. Esta lista captura la palabra **canónica**.
3. **Overlaps críticos** (marcadores compartidos entre categorías):
   - `perra` aparece en 2.2 (slut-shaming) y 4.3 (animalización
     manosférica). El contexto sintáctico decide.
   - `viejas webonas` aparece en 1.3 y 6.2. El referente
     (feministas vs. mujeres en general) decide.
   - `ridículas` aparece en 1.3 y 6.2. Mismo criterio.
4. **Los marcadores 5.3** NO son palabras agresivas — son palabras
   que **invierten el sentido** de un marcador agresivo. Por eso
   viven en este archivo pero se inyectan en otro bloque del prompt
   (`MARCADORES_MITIGADORES`, ver `glosario/marcadores-mitigadores.md`).

## Cambios recientes

- **2026-07-12.** Refactor: la lista vivía hardcoded en
  `src/analyzer/category_mapping.py::MARCADORES_POR_SUBDIMENSION`.
  Hoy se carga desde este markdown. Mejora de la auditoría 2026-07-12:
  cerrado el bucle de "reglas en código vs. reglas en documento".
