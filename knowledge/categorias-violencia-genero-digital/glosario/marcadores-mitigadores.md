---
tipo: Glosario de marcadores mitigadores (anti-falsos positivos)
proposito: Cerrar el set de tokens que, en función de denuncia / cita /
  reapropiación endogrupal, invierten el sentido de un marcador
  agresivo. Si el texto contiene UNO de estos tokens en función de
  denuncia, el LLM debe devolver `clasificaciones: []` con
  `es_falso_positivo_probable: true`.
fecha_origen: 2026-07-12 (refactor reglas-codigo → reglas-markdown)
excepciones:
  - Si el texto CITA el marcador mitigador SIN usarlo en función
    denunciante (p. ej. una cita burlesca tipo "son unas retrógradas"
    SIN contexto denunciante), mantener la clasificación VDG con
    `es_falso_positivo_probable: true` para señalar la duda.
---

# Marcadores mitigadores (anti-falsos positivos)

Lista cerrada de **tokens y frases** que, usados en función de
denuncia / cita / reapropiación endogrupal, invierten el sentido
de un marcador agresivo y devuelven el texto a `clasificaciones: []`.

## Bloque para prompt

```
MARCADORES_MITIGADORES → NO_VDG:
Si el texto contiene UNO O MÁS de los siguientes tokens (en cualquier
posición) CUMPLiendo función de denuncia / cita / reapropiación
endogrupal / crítica, devolvé `clasificaciones: []` y marcá
`es_falso_positivo_probable: true` para la lista vacía.

Lista cerrada (tokens y frases exactas):

- arcaica, retrógrada, falsa, absurda, ridícula, obsoleta, patética, patriarcal, machista, conservadora
- denunciar, denuncia, evidenciar, rechazar, repudiar, desmontar, deconstruir, criticar, señalar, visibilizar, luchar, lucha
- no es verdad que, en realidad, sin embargo, jamás, nunca, pero, aunque, a diferencia de
- ", (, #NiUnaMenos, #8M, #VivasNosQueramos, #FeminismoEs, según, como dice
- eres un crack, te amo, hermana, mi vida, amiga, reírse de, ja ja, ja ja ja, jaja

EXCEPCIÓN: si el texto cita el término mitigador pero NO lo usa en
función de denuncia (p.ej. una cita burlesca tipo "son unas
retrógradas" SIN contexto denunciante), mantené la clasificación VDG
con `es_falso_positivo_probable: true` para señalar la duda.
```

## Caso emblemático de la auditoría 2026-07-12

El comentario (ar_id=57):

> *"Pues en los carteles veo cosas logicas, a quien le molesta eso?
> Quieren a una mujer controlada? Quieren que las mujeres mueran?
> Les importa la opinión de otros sobre su cuerpo?
> Yo creo que todos pensamos lo mismo que dicen los carteles,
> o quien no? Cual es el lio?"*

Es una **defensa feminista del derecho a protestar**. Las
preguntas retóricas funcionan como marcador mitigador (función de
desafío). El LLM lo había marcado como Cat. 2.1 + Cat. 1.2. Con
este glosario debe devolver `clasificaciones: []` con
`es_falso_positivo_probable: true`.

## Reglas de uso

1. **Detección semántica, no léxica pura.** El clasificador
   debe evaluar si el token actúa en función de **denuncia** /
   **cita** / **crítica**. Una mención incidental tipo *"jaja
   patriarcal"* sin contexto denunciante NO es mitigador.
2. **Coocurrencia con marcador agresivo.** Un mitigador sólo
   tiene efecto si el texto también contiene al menos UN marcador
   agresivo de los listados en `marcadores-por-subdimension.md`.
   Sin marcador agresivo, no hay nada que mitigar.
3. **Sobreescritura protectora.** Si el marcador agresivo aparece dentro
   de una denuncia, refutación o crítica feminista coherente, activar 6.3 y
   devolver la lista vacía. Solo mantener una categoría sustantiva cuando
   exista un segmento agresivo independiente que no dependa del marcador
   citado o refutado.

## Cambios recientes

- **2026-07-12.** Refactor: la lista vivía hardcoded en
  `category_mapping.py::MARCADORES_MITIGADORES`. Hoy vive en este
  markdown y el código solo la lee.
