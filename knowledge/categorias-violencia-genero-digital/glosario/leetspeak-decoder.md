---
tipo: Glosario de leetspeak → vocabulario canónico
proposito: Cerrar el set de mutaciones alfanuméricas/ortográficas que
  los agresores digitales usan para evadir filtros. Se inyecta en el
  prompt como bloque `DESCODIFICACIÓN OBLIGATORIA DE LEETSPEAK`
  que el LLM aplica ANTES de evaluar marcadores.
fecha_origen: 2026-07-12 (refactor reglas-codigo → reglas-markdown)
---

# Leetspeak decoder

Tabla cerrada de variantes tipográficas/alfanuméricas → palabra
canónica en español. El LLM debe aplicar este mapeo **mentalmente**
antes de buscar marcadores canónicos. El decoder también está
implementado en `category_mapping.load_prompt_block()` para que el
bloque se inyecte verbatim en el prompt.

## Bloque para prompt

```
DESCODIFICACIÓN OBLIGATORIA DE LEETSPEAK ANTES DE BUSCAR MARCADORES:
(Si una variante leetspeak del input está abajo, reemplazala mentalmente
por la palabra canónica antes de evaluar marcadores).

- f3m1 nizta → feminazi
- f3minista → feminista
- fe-mi-nis-ta → feminista
- mu3rte → muerte
- m4tar → matar
- asesin0s → asesinos
- ases1n0s → asesinos
- marikon → maricón
- m4ric0n → maricón
- h1j4 d3 put4 → hija de puta
- h1j4 d3 pvt4 → hija de puta
- put@ → puta
- pvt@ → puta
- muj3r → mujer
- mvj3r → mujer
- degenerac18n → degeneración
- acost4rs3 → acostarse
- cog13nd8 → cogiendo
- c8g1d8 → cogida
- f8ll9 → follar
- f8ll4 → follar
- acv3sta → acuesta
- mvjeres → mujeres
- aliade → aliado
```

## Caso emblemático de la auditoría 2026-07-12

El comentario `Para el aliade y la f3m1 nizta` (ar_id=34) era
clasificado como Cat. 1.3 + Cat. 2.2 por el LLM. Con este decoder,
se decodifica a:

- `aliade` → `aliado` → Cat. 4.3 (jerga de emasculación manosférica).
- `f3m1 nizta` → `feminazi` → Cat. 4.3 (troleo de género).

Regla explícita en el prompt: **tras decodificar, las dos
ocurrencias dan Cat. 4.3** (×2).

## Patrones soportados

| Patrón | Original | Mutación |
|--------|----------|----------|
| Vocal → número | muerte | `mu3rte`, `m4tar`, `asesin0s` |
| Vocal → símbolo | puta | `pút@`, `pvt@` |
| Separación silábica | feminista | `fe-mi-nis-ta` |
| Consonante → número | mujer | `muj3r`, `mvj3r` |

## Cambios recientes

- **2026-07-12.** Refactor: la lista vivía hardcoded en
  `category_mapping.py::LEETSPEAK_MAPPER`. Hoy vive en este markdown
  y el código solo la lee desde el archivo. Se agrega `aliade` →
  `aliado` y `aliado` → `aliade` al mapeo.
