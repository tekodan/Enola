---
tipo: Reglas de desempate entre subdimensiones
proposito: Inyectado en el prompt del clasificador para resolver fronteras ambiguas
fecha_origen: 2026-07-15
---

# Reglas de desempate

## Bloque para prompt

```
REGLAS DE DESEMPATE:

1) FRONTERA 1.1 vs 1.3 vs 5.2:
   - Imperativo doméstico o de silencio dirigido a mujeres en general → 1.1.
   - Generalización, patologización o juicio moral sin imperativo → 1.3.
   - El mismo imperativo dirigido a activistas, manifestantes, periodistas o políticas por su actividad pública → 5.2; multicategorizar 1.1 + 5.2 si ambos núcleos están presentes.

2) FRONTERA 1.2 vs 1.3:
   - Si se afirma incapacidad intelectual, racional, física, técnica o de conducción → 1.2.
   - Si se castiga la conducta, estabilidad mental, decoro o lealtad → 1.3.

3) REGLA DURA PARA 2.1 — FRONTERA 2.1 vs 2.2 vs 2.3:
   - Deseo, consumo o uso sexual del cuerpo → 2.1.
   - Ataque al físico, edad, peso o anatomía → 2.2.
   - Condena de sexualidad, intimidad o vestimenta → 2.3.

4) FRONTERA 3.1 vs 3.3 (con 3.2 como frontera letal):
   - Golpes, tortura o castigo no letal sin connotación sexual → 3.1.
   - Deseo directo, futuro o imperativo de matar o aniquilar, incluidas mutaciones leetspeak → 3.2.
   - Justificación, celebración o banalización del feminicidio sin amenaza directa → 3.3.

5) FRONTERA 4.1 vs 4.2 vs 4.3 vs 4.4:
   - Autoidentificación masculinista, jerarquía, hipergamia o determinismo biológico → 4.1.
   - Ataque político al feminismo con victimismo masculino, misandria, ideología de género o leyes que criminalizan → 4.2.
   - Castigo verbal dirigido a un varón aliado, débil o sumiso → 4.3.
   - Arquetipo o etiqueta deshumanizante dirigida a una mujer → 4.4.

6) FRONTERA 4.1 vs 1.1:
   - La jerga manosférica y el determinismo biológico/económico → 4.1.
   - Una exigencia tradicional de fidelidad o sumisión sin jerga manosférica → 1.1 o 1.3.

7) FRONTERA 4.2 vs 5.1 vs 5.3:
   - Victimismo masculino, inversión de roles o ataque al feminismo como movimiento → 4.2.
   - Patologización dirigida a una activista o mujer pública → 5.1.
   - Acusación de hipocresía política mediante igualdad, respeto o doble moral → 5.3.

8) FRONTERA 4.3 vs 4.4:
   - El blanco de aliade, mangina, pagafantas o beta-insulto es un hombre → 4.3.
   - El blanco de foid, femoid, Stacy, tradwives o animalización es una mujer → 4.4.

9) HUMOR HOSTIL:
   - Si hay ataque y risa, sarcasmo o formato de broma, agregar 6.2 sin anular la categoría sustantiva.
   - La risa aislada sin ataque no es 6.2 y puede ser basura digital según el pre-filtro.

10) SALVAGUARDA:
   - Si los marcadores sexistas aparecen en denuncia, cita, refutación o crítica feminista, 6.3 sobreescribe y anula las alertas sustantivas.
   - Devolver `clasificaciones: []`, `tiene_violencia: false` y `es_falso_positivo_probable: true`.
```
