---
tipo: Glosario de marcadores canónicos
proposito: Inyectado en el prompt del clasificador como bloque MARCADORES_CANONICOS
fecha_origen: 2026-07-15
---

# Marcadores canónicos por subdimensión

Los marcadores son ejemplos de patrones semánticos. El contexto, el blanco del ataque y las reglas de exclusión prevalecen sobre una coincidencia literal.

## Bloque para prompt

```
MARCADORES_CANONICOS:

- 1.1 (VDG_VIOLENCIA_SIMBOLICA): madre, esposa, cuidadora, fiel, cariñosa, calladitas, obedientes, acomedidas, a lavar, a limpiar, cocinar, criar, a la cocina, agarrar la escoba, váyanse a dormir, mujer debe quedarse en casa
- 1.2 (VDG_VIOLENCIA_SIMBOLICA): mujer al volante, sexo débil, sin cerebro, niñatas, estúpidas, inútiles, incapaz, no sabe razonar, no sabe conducir, el hombre es más fuerte
- 1.3 (VDG_VIOLENCIA_SIMBOLICA): locas, histéricas, ridículas, tóxicas, viejas webonas, mojigatas, no se dan a respetar, son todas iguales, no se puede confiar en una mujer, traicionera
- 2.1 (VDG_COSIFICACION_SLUTSHAMING): rica, putita obediente, estás buena, packs, enseñando las nalgas, para eso estás, objeto sexual, pedazo de carne
- 2.2 (VDG_COSIFICACION_SLUTSHAMING): vieja, fea, gorda, flaca, anoréxica, subió de peso, está re gorda, está re flaca, no tiene tetas, no tiene culo
- 2.3 (VDG_COSIFICACION_SLUTSHAMING): zorra, puta, perra, cualquiera, promiscua, se acuesta con varios, tiene mucho kilometraje, se viste como una puta, doble moral sexual
- 3.1 (VDG_HOSTILIDAD_FEMINICIDIO): a puñetazo limpio, golpeen su cara, a punta de golpes, paliza, tortura, sin dormir ni comer, limpiar fango, te voy a golpear
- 3.2 (VDG_HOSTILIDAD_FEMINICIDIO): matar, m4tar, mu3rte, morir, muere, asesin4rl4, asesin0s, córtenle la cabeza, ojalá te maten
- 3.3 (VDG_HOSTILIDAD_FEMINICIDIO): por mujeres como estas ocurren los feminicidios, se lo buscaron, se lo merecía, no supo cómo reaccionar, la mató porque le fue infiel, hombres que no lo resistan
- 4.1 (VDG_MANOSFERA_ANTIFEMINISMO): MRA, MGTOW, PUA, Incel, Red Pill, Black Pill, beta, hipergamia, genéticamente programada, mejor macho, interés material o genético
- 4.2 (VDG_MANOSFERA_ANTIFEMINISMO): feminazi, hembrista, misandria, ideología de género, leyes que criminalizan a los hombres, criminalizan al hombre, supremacismo femenino, feminismo totalitario
- 4.3 (VDG_MANOSFERA_ANTIFEMINISMO): aliade, mangina, pagafantas, huelebragas, calzonazos, blandengue, parguelón, beta cuando el blanco es un varón aliado
- 4.4 (VDG_MANOSFERA_ANTIFEMINISMO): foid, femoid, Stacy, tradwives, #TeamAlienadas, mujer objeto, monos, perras, gallinas, focas
- 5.1 (VDG_DESACREDITACION_ACTIVISTAS): traumada, ardida, histérica, loca, exagerada, tóxica, busca atención, feminismo radical, hembrismo, dirigido a activista o mujer pública
- 5.2 (VDG_DESACREDITACION_ACTIVISTAS): váyanse a lavar, a la cocina, limpien sus casas, cuiden a sus hijos, váyanse a dormir, ridículas, viejas webonas, pónganse a trabajar, en contexto de marcha o activismo
- 5.3 (VDG_DESACREDITACION_ACTIVISTAS): doble moral política, falta de respeto, pidiendo igualdad, lucha por la igualdad, hipócritas, dirigido contra una activista o el movimiento igualitario
- 6.1 (VDG_SALVAGUARDA_FALSO_POSITIVO): calladita te ves más bonita, tenías que ser mujer, las mujeres no saben, tú haz lo que yo te diga, falsa cortesía, consejo condescendiente
- 6.2 (VDG_SALVAGUARDA_FALSO_POSITIVO): jajaja, jaja, es solo humor, era una broma, sarcasmo, meme, generación de cristal, cuando encubre una agresión
- 6.3 (VDG_SALVAGUARDA_FALSO_POSITIVO): arcaica, retrógrada, patriarcal, machista, denunciar, repudiar, visibilizar, criticar, desmontar, no es verdad que, sin embargo, #NiUnaMenos, #8M, #VivasNosQueremos, comillas y citas de denuncia
```

## Reglas de uso

1. La búsqueda es insensible a mayúsculas y acentos.
2. Un marcador no basta cuando la regla exige contexto: 2.2 requiere ataque al físico; 2.3 requiere juicio sexual; 4.3 requiere que el blanco sea un hombre; 5.1, 5.2 y 5.3 requieren perfil público o movimiento.
3. `mujer al volante` no es 1.1 por sí sola: si atribuye incapacidad técnica o cognitiva, es 1.2. Los imperativos domésticos son 1.1.
4. Body-shaming siempre es 2.2; slut-shaming siempre es 2.3; no intercambiar estas etiquetas.
5. `feminazi` usado para victimismo masculino y ataque al movimiento es 4.2. `foid`, `Stacy`, `tradwives` y animalización manosférica dirigidas a mujeres son 4.4.
6. Las subdimensiones 5.x requieren una receptora pública. La misma orden doméstica dirigida a una mujer común es 1.1.
7. Si un marcador ofensivo aparece en una denuncia, cita, refutación o reapropiación no agresiva, 6.3 anula las alertas sustantivas.
