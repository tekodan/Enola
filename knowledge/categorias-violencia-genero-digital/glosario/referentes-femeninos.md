---
tipo: Glosario de referentes femeninos obligatorios
proposito: Cerrar el set de pronombres/sustantivos/nombres propios
  femeninos que satisfacen la regla de coocurrencia semántica (Protocolo §1)
  sin los cuales el LLM debe devolver `clasificaciones: []`.
fecha_origen: 2026-07-12 (refactor reglas-codigo → reglas-markdown)
excepciones:
  - Cat. 4 (manosfera): puede dispararse sin referente femenino explícito
  - Cat. 6 (control de resistencia): puede dispararse sin referente femenino explícito cuando se evalúa humor o micromachismo
---

# Referentes femeninos (lista cerrada)

Antes de asignar cualquier categoría salvo Cat. 4 / Cat. 6, el LLM debe
verificar que el texto contiene al menos **uno** de estos tokens
(o un nombre propio femenino que no figure en la lista pero pertenezca
al colectivo femenino). Si no hay ninguno, devolver
`clasificaciones: []` con `tiene_violencia: false`.

## Bloque para prompt

```
REGLA DE COOCURRENCIA SEMÁNTICA (OBLIGATORIA):
Salvo en Cat. 4 (manosfera) y Cat. 6 (control de resistencia), toda
asignación de categoría REQUIERE un referente femenino EXPLÍCITO en el
mismo texto. Lista cerrada de referentes válidos:

  ella, ellas, mujer, mujeres, chica, chicas, pibas, vieja, viejas,
  fémina, féminas, esposa, esposas, novia, novias, madre, madres,
  hija, hijas, hermana, hermanas, tía, stacy, karen, becky,
  feminazi, hembrista, feministas, feminista, activistas,
  colectivo feminista, eva, maría, …

Si el texto NO contiene ninguno de estos referentes ni un nombre
propio femenino (Eva, María, etc.), devolvé `clasificaciones: []` con
`tiene_violencia: false`. Esta regla mata los falsos positivos tipo
"Nadie vendrá a salvarte", "Los hombres usan IA para fantasías".
```

## Reglas de matching

- **Match case-insensitive y sin acentos.**
- **Sub-string match.** `mujeres` matchea contra `mujer`.
- **Nombre propio femenino** que NO esté en la lista pero sea
  reconocible (María, Ofelia, Victoria, etc.) también cuenta como
  referente válido.

## Excepciones

| Categoría | ¿Requiere referente femenino? |
|-----------|-------------------------------|
| Cat. 1 (violencia simbólica) | **Sí**. |
| Cat. 2 (cosificación / slut-shaming) | **Sí**. |
| Cat. 3 (hostilidad letal) | **Sí** — el referente puede ser implícito ("a las", "las mujeres"). |
| Cat. 4 (manosfera) | **No** — la jerga puede no nombrar un referente directo. |
| Cat. 5 (castigo del empoderamiento) | **Sí** — requiere una activista, figura pública o colectivo identificable. |
| Cat. 6 (control de resistencia) | **No siempre** — 6.1 y 6.2 pueden evaluarse por contexto pragmático. |

## Trazabilidad

- Decisión de diseño: este glosario se carga en `category_mapping.py`
  y se inyecta como bloque `REGLA_DE_COOCURRENCIA_SEMANTICA` en
  `_build_prompt()`.
- Última modificación: 2026-07-12 — refactor desde código a markdown.
  El contenido venía de `Protocolo algorítmico general` §1.
- Auditado en la auditoría `docs/auditoria-categorizaciones-2026-07-12.md`
  (entradas `a1478d1dd8727dd4`, `1f09dfc016268ce8`,
  `52dda3c28962f918`, `72`→`94a5252cf77e41e6`).
