# Decisions — Registro de Decisiones de Diseño

---

## 2026-07-15 — Marcadores léxicos como ejemplos ilustrativos, no patrones exactos

### Problema

El LLM clasificador (`RAGClassifier`) no detectaba categorías cuando el texto
exhibía el **mismo patrón semántico** que los marcadores pero sin usar la palabra
exacta. Ejemplo:

- **1.1**: texto mencionaba "lo está engañando" (sospecha de infidelidad como
  incumplimiento del rol de sumisión) — ningún marcador literal de 1.1 estaba
  presente, pero el patrón semántico sí.
- **2.3**: texto mencionaba "hablando con otro", "viéndose con alguien más" —
  no había insultos sexuales explícitos (zorra, puta), pero sí slut-shaming
  implícito por presunción de infidelidad.
- **4.3**: el marcador `beta` estaba presente pero el LLM lo interpretó como
  descriptor taxonómico (4.1) en lugar de insulto de emasculación.

### Decisión

Se adoptó la **Opción D (B + C)**:

- **(C)** Modificar la instrucción global en `rag_classifier.py`:
  "si una palabra del texto está en la lista" → "si el texto exhibe el mismo
  patrón semántico que los ejemplos listados".
- **(B)** Agregar descripción de patrón semántico por subdimensión en
  `marcadores-por-subdimension.md`, dejando los marcadores léxicos como
  ejemplos ilustrativos.

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `rag_classifier.py` | Instrucción de "palabra exacta" → "patrón semántico" |
| `knowledge/.../marcadores-por-subdimension.md` | Header del bloque + descripciones de patrón por subdimensión |
| `knowledge/taxonomia/TAXONOMIA.md` | Descripciones de 1.1, 2.3, 4.3 ajustadas para reflejar patrón semántico |

### Kata de verificación

Post `0f3e884a8a124fd1_p2`: "El beta se entera o sospecha que ella está
hablando con otro..." → debe clasificarse como 1.1, 2.3, 4.1, 4.3.
