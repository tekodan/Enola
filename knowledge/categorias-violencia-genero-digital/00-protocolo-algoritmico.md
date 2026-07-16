---
tipo: Protocolo técnico transversal
aplica_a: Todas las categorías
---

# Protocolo algorítmico general

Este protocolo define las reglas transversales para las seis categorías y sus diecinueve subdimensiones.

## 1. Coocurrencia semántica

Salvo la categoría 4 y las señales de la categoría 6, las categorías sustantivas requieren un referente femenino explícito o un nombre propio reconocible. Referentes válidos incluyen `ella`, `mujer`, `chica`, `pibas`, `vieja`, `fémina`, `esposa`, `novia`, `madre`, `hija`, `hermana`, `feminista`, `activista`, `colectivo feminista`, `Eva` y `María`.

La ausencia de referente femenino debe producir `clasificaciones: []`, salvo cuando la jerga de la manosfera o el contexto transversal de 6.1/6.2 justifique otra evaluación.

## 2. Leetspeak y evasión algorítmica

Antes de buscar marcadores, normalizar sustituciones alfanuméricas y ortográficas: `mu3rte` → `muerte`, `m4tar` → `matar`, `asesin0s` → `asesinos`, `f3m1 nizta` → `feminazi`, `fe-mi-nis-ta` → `feminista`, `aliade` → `aliado`, `pvt@` → `puta`.

Las mutaciones de muerte y asesinato pertenecen a 3.2 cuando expresan un deseo letal directo. `feminazi` con victimismo masculino pertenece a 4.2; `aliade` dirigido a un varón pertenece a 4.3.

## 3. Contexto pragmático y salvaguarda

Antes de confirmar un ataque, distinguir:

- Ataque misógino: el marcador se usa para agredir.
- Denuncia feminista: el marcador se cita, critica o refuta y no es VDG.
- Reapropiación o camaradería: el marcador no busca dañar y no es VDG.

Marcadores mitigadores: `arcaica`, `retrógrada`, `patriarcal`, `machista`, `denunciar`, `criticar`, `rechazar`, `repudiar`, `desmontar`, `visibilizar`, `no es verdad que`, `en realidad`, `sin embargo`, `#NiUnaMenos`, `#8M`, `#VivasNosQueremos`, comillas y preguntas retóricas de defensa.

Cuando esos marcadores cumplen una función de denuncia o refutación, 6.3 sobreescribe y anula alertas de las categorías 1 a 5. El resultado es una lista vacía con `tiene_violencia: false` y `es_falso_positivo_probable: true`.

## 4. Imperativos domésticos

Los imperativos `a lavar`, `a limpiar`, `cocinar`, `criar`, `a la cocina`, `agarrar la escoba`, `váyanse a dormir` y `calladitas` activan 1.1 cuando se dirigen a mujeres en general.

Si esos mismos imperativos se dirigen a activistas, manifestantes, periodistas o políticas para castigar su presencia pública, activan 5.2 y pueden multicategorizarse con 1.1.

## 5. Fronteras obligatorias

| Frontera | Regla |
|---|---|
| 1.1 / 1.2 / 1.3 | Doméstico y sumisión / incapacidad intelectual o física / castigo moral y patologización |
| 2.1 / 2.2 / 2.3 | Consumo sexual / físico, edad, peso o anatomía / sexualidad, intimidad o vestimenta sancionada |
| 3.1 / 3.2 / 3.3 | Castigo físico no letal / deseo directo de matar / apología o justificación sin amenaza directa |
| 4.1 / 4.2 / 4.3 / 4.4 | Jerarquía manosférica / oposición antifeminista / castigo a varón aliado / arquetipo femenino deshumanizante |
| 5.1 / 5.2 / 5.3 | Patologización pública / orden doméstica contra activismo / hipocresía política |
| 6.1 / 6.2 / 6.3 | Sutileza sin insulto / humor que encubre ataque / denuncia o reapropiación no agresiva |

## 6. Flujo de clasificación

1. Normalizar texto y leetspeak.
2. Identificar referentes y blanco del ataque.
3. Evaluar mitigadores y aplicar 6.3 si corresponde.
4. Evaluar las seis categorías y todas las subdimensiones aplicables.
5. Resolver fronteras con la tabla y las reglas de desempate.
6. Devolver hasta cinco etiquetas con justificación, evidencia y marcadores propios.

La risa o el sarcasmo no neutralizan un ataque. Cuando el mensaje contiene humor hostil, agregar 6.2 junto con las categorías sustantivas independientes.
