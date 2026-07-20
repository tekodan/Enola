---
tipo: Tabla canónica para prompt
proposito: Tabla de cierre para category_mapping.py y los bloques del prompt
fecha: 2026-07-15
---

# Tabla canónica de prompt

La tabla contiene las diecinueve combinaciones válidas. Las reglas narrativas y los glosarios determinan el contexto de aplicación.

| categoria | dimension | nombre canónico | núcleo de decisión |
|---|---|---|---|
| VDG_VIOLENCIA_SIMBOLICA | 1.1 | Roles tradicionales y de sumisión | Mandato doméstico, cuidado, silencio u obediencia |
| VDG_VIOLENCIA_SIMBOLICA | 1.2 | Incompetencia e inferioridad | Incapacidad intelectual, física o técnica atribuida a mujeres |
| VDG_VIOLENCIA_SIMBOLICA | 1.3 | Castigo moral y patologización | Locura, irracionalidad, falta de decoro o deslealtad atribuida |
| VDG_COSIFICACION_SLUTSHAMING | 2.1 | Cosificación e hipersexualización | Deseo, consumo o uso sexual del cuerpo femenino |
| VDG_COSIFICACION_SLUTSHAMING | 2.2 | Escrutinio corporal y body-shaming | Ataque a físico, edad, peso o anatomía |
| VDG_COSIFICACION_SLUTSHAMING | 2.3 | Doble estándar sexual y slut-shaming | Castigo moral por sexualidad, parejas, intimidad o vestimenta |
| VDG_HOSTILIDAD_FEMINICIDIO | 3.1 | Castigos disciplinantes | Golpes, tortura o castigo físico no letal sin connotación sexual |
| VDG_HOSTILIDAD_FEMINICIDIO | 3.2 | Deseos de violencia letal | Matar, asesinar o aniquilar, incluidas mutaciones leetspeak |
| VDG_HOSTILIDAD_FEMINICIDIO | 3.3 | Apología al feminicidio | Justificar, celebrar o banalizar el asesinato de mujeres |
| VDG_MANOSFERA_ANTIFEMINISMO | 4.1 | Subculturas masculinistas y jerarquías de dominación | MRA, MGTOW, PUA, Incel, Red Pill, hipergamia y determinismo |
| VDG_MANOSFERA_ANTIFEMINISMO | 4.2 | Oposición antifeminista y victimismo hegemónico | Misandria, feminazi, ideología de género y victimismo masculino |
| VDG_MANOSFERA_ANTIFEMINISMO | 4.3 | Trolleo, castigo y emasculación | Ataque a varones aliados, débiles o sumisos |
| VDG_MANOSFERA_ANTIFEMINISMO | 4.4 | Arquetipos femeninos deshumanizantes | Foid, femoid, Stacy, tradwives y animalización de mujeres |
| VDG_DESACREDITACION_ACTIVISTAS | 5.1 | Deslegitimación del empoderamiento | Patologización de activistas y mujeres con perfil público |
| VDG_DESACREDITACION_ACTIVISTAS | 5.2 | Ridiculización tradicional del empoderamiento | Mandato doméstico para silenciar activismo o protesta |
| VDG_DESACREDITACION_ACTIVISTAS | 5.3 | Falacia de superioridad moral | Hipocresía política invocando igualdad, respeto o doble moral |
| VDG_SALVAGUARDA_FALSO_POSITIVO | 6.1 | Micromachismos y mansplaining | Agresión sutil sin insulto explícito |
| VDG_SALVAGUARDA_FALSO_POSITIVO | 6.2 | Humor hostil | Burla o risa usada para enmascarar una agresión |
| VDG_SALVAGUARDA_FALSO_POSITIVO | 6.3 | Salvaguarda y falsos positivos | Denuncia, cita, refutación o reapropiación no agresiva |

## Instrucción de cierre

El LLM debe devolver hasta `MAX_LABELS` etiquetas y conservar todas las capas independientes. Si el uso de un marcador ofensivo es una denuncia, cita o crítica feminista, 6.3 sobreescribe las alertas y debe devolver una lista vacía con `es_falso_positivo_probable: true`.
