---
id: cat-6
numero: 6
titulo: Control de resistencia, sarcasmos y falsos positivos
subdimensiones: 3
reglas: 3
gravedad: ortogonal (modula la detección de las demás categorías)
naturaleza: categoria-ortogonal
---

# Categoría 6: Control de resistencia, sarcasmos y falsos positivos

> **Naturaleza especial:** a diferencia de las categorías 1, 2, 3, 4 y 5, que describen formas sustantivas de violencia, esta categoría opera de manera **transversal y ortogonal**: describe una *modalidad de expresión* (micromachismos, sarcasmo, reapropiación) que puede vehicular contenido de cualquier otra categoría, a la vez que delimita el principal riesgo técnico del modelo: los falsos positivos por falta de contexto pragmático. Por este motivo, no tiene "gravedad" propia sino que modula la detección de las demás.

## 1. Definición Conceptual

El control de resistencia y los sarcasmos en los entornos virtuales constituyen mecanismos encubiertos de violencia simbólica, mediante los cuales los agresores emplean el humor, la ironía y la falsa cortesía para disciplinar a las mujeres y atacar al movimiento feminista sin asumir el costo social de una agresión directa. Investigadores como Campillo Muñoz (2022) señalan que la ironía es un recurso ampliamente utilizado en las redes sociales para cometer violencia verbal no explícita, operando como un conducto que permite a los usuarios expulsar su rechazo e ira de forma disfrazada (p. 27). En este sentido, autoras como Crosas Remón y Medina-Bravo (2019) exponen que el tono humorístico en las plataformas digitales se emplea estratégicamente para invisibilizar el daño y hacer que la agresión machista resulte socialmente aceptable.

A nivel computacional y forense, estas expresiones representan un desafío crítico, puesto que su naturaleza implícita genera constantes errores (falsos positivos y falsos negativos) en la Inteligencia Artificial. Tal y como advierten Syafi-Muhammad y Ruldeviyani (2020, citados en Suárez-Álvarez et al., 2025), la codificación automática presenta graves limitaciones estructurales para decodificar las expresiones sarcásticas, la cultura memética y las frases con doble sentido, lo que exige entrenar a los sistemas bajo perspectivas pragmáticas y de contexto para evitar que el algoritmo clasifique un ataque sutil como un comentario inofensivo.

## 2. Subdimensiones Analíticas

### 6.1. Micromachismos y Mansplaining

Comprende aquellos mensajes que no utilizan un vocabulario abiertamente hostil o insultos directos, sino que recurren a presuposiciones o implicaturas para denigrar a las mujeres.

Identificar mensajes con dobles sentidos, falsos elogios o en un tono de condescendencia machista (mansplaining). La interpretación de estos mensajes implícitos requiere extraer significados inferidos que no derivan directamente del material lingüístico literal.

El sistema debe identificar y extraer construcciones semánticas aparentemente inofensivas, refranes populares o frases disfrazadas de consejos que escondan una intención de subordinación, silenciamiento o condescendencia hacia la mujer. Se debe evaluar el contexto pragmático del texto para detectar la violencia machista implícita (ej. *mansplaining* o micromachismos), validando la agresión incluso en ausencia absoluta de groserías o insultos evidentes.

**Regla estricta de exclusión para evitar solapamientos:** El núcleo absoluto de esta regla es la **ausencia de lenguaje hostil explícito**. Este sistema **tiene estrictamente prohibido** activar esta etiqueta si el mensaje contiene groserías, insultos directos o ataques frontales (ej. llamar a una mujer *zorra, feminazi, loca o inútil*). Estos ataques deben ir en otras categorías que correspondan. La etiqueta **6.1** está reservada de forma exclusiva para la agresión sutil, el "mansplaining" o los "micromachismos", donde el agresor mantiene una falsa cortesía para atacar sin asumir el costo social de un insulto.

**Ejemplos:**
- *"Calladita te ves más bonita"*. **Análisis:** A nivel literal, la frase no contiene ninguna grosería e incluso incluye el adjetivo "bonita". Sin embargo, pragmáticamente, el agresor utiliza un refrán popular disfrazado de consejo para ejercer violencia simbólica. El mensaje oculto es una orden de silenciamiento, asumiendo con condescendencia que la opinión de la mujer carece de valor y que su único aporte debe ser estético.

### 6.2. Humor Hostil

Identificar cuando el agresor instrumentaliza la burla y el formato de la comedia para enmascarar su violencia. Al presentarse como una simple "broma", el atacante busca eludir la sanción social y técnica. El uso del tono humorístico, el sarcasmo o la cultura memética se emplea estratégicamente para invisibilizar el daño, logrando que el acto de agresión machista resulte "socialmente aceptable" para el resto de las personas.

El sistema debe identificar, extraer y evaluar el contexto pragmático de mensajes o comentarios que escudan la estigmatización y la misoginia detrás del formato de la comedia. También debe procesar el uso de ironía, sarcasmo o la repetición de onomatopeyas de risa (ej. *jajaja*) no como indicadores de un texto inofensivo, sino como **mecanismos de enmascaramiento** diseñados para eludir filtros, validando la agresión oculta.

**Ejemplos:**
- *"Habría menos feminicidios si no salieran de la cocina jajaja"* (Cicua Castro y Calderón López, 2024). **Análisis:** El agresor instrumentaliza el sarcasmo y el formato memético para justificar y banalizar la violencia letal bajo la máscara de una "simple broma". ENOLA debe detectar la incongruencia y sancionar el uso del humor hostil como escudo.
- *"Pura licenciada jajaja... ya póngase a chambear!"* (Domínguez Arteaga, 2023). **Análisis:** Utiliza la onomatopeya de la risa ("jajaja") y el sarcasmo para ridiculizar a las activistas en el espacio público (marcha 8M), intentando restar valor político a sus demandas al enmascarar la deslegitimación como comedia.

**Regla de multicategorización:** Por lo general, esta regla de violencia encubierta en la comedia no se presenta de forma aislada, sino que viene acompañada de otras expresiones de agresividad explícita que van en otras categorías del manual. En estos casos, ENOLA **debe multicategorizar** el mensaje separando las capas de violencia. **Por ejemplo:** Si un usuario escribe *"Habría menos feminicidios si no salieran de la cocina jajaja"*, el algoritmo deberá aplicar una **triple clasificación**: activará la **Subdimensión 3.3** (por hacer apología al feminicidio justificando la violencia letal), activará la **Subdimensión 1.1** (por imponer la sumisión y el mandato de reclusión femenina en la "cocina"), y, de manera simultánea, activará la **Subdimensión 6.2** para sancionar el uso de la risa ("jajaja") como un agravante de burla y escudo cómico.

### 6.3. Salvaguarda y Falsos Positivos

Identifica cuando las propias activistas o víctimas emplean términos teóricamente ofensivos (como repetir un insulto que recibieron para denunciarlo públicamente, o usar palabras estigmatizantes desde el empoderamiento y la ironía defensiva).

El sistema debe operar como un "sello de salvaguarda". Al detectar palabras teóricamente ofensivas, insultos o arquetipos sexistas, se debe evaluar obligatoriamente el contexto pragmático de la oración en busca de *marcadores mitigadores*, refutaciones o consignas feministas. El algoritmo debe ser capaz de identificar cuándo una palabra estigmatizante se está utilizando para denunciar un acto sexista o como crítica feminista, evitando así censurar y castigar a la propia víctima.

**Regla estricta de exclusión y sobreescritura (Override protector):** El sistema **tiene estrictamente prohibido** clasificar como ciberviolencia machista un mensaje que contenga marcadores de mitigación o denuncia. Si el sistema detecta un estereotipo (ej. "mujer florero") o un insulto, pero identifica que está enmarcado en una refutación (ej. usar el adjetivo "arcaica" para criticarlo) o en una pregunta retórica de defensa, esta regla (6.3) **sobreescribe y anula** cualquier alerta de violencia de las Categorías 1, 2, 3, 4 o 5. El mensaje deberá ser clasificado como un uso legítimo del lenguaje (falso positivo) y descartado como agresión.

**Ejemplos:**
- *"Mira que me gusta el trabajo de @xxxx pero su versión de [...] La visión de mujer florero del vídeo es más bien arcaica"*. **Análisis:** Un algoritmo básico clasificaría este texto erróneamente como violencia simbólica por contener la etiqueta "mujer florero". Sin embargo, el sistema debe identificar que el adjetivo "arcaica" actúa como un marcador mitigador que invierte el sentido de la oración, convirtiéndola en una crítica feminista legítima y, por ende, en un falso positivo.

## 3. Reglas de Inclusión Algorítmica

### Regla 1: Sexismo implícito y micromachismos

**Descripción algorítmica:** El algoritmo debe ser calibrado para detectar construcciones semánticas que aparentemente son inofensivas o se disfrazan de consejos, pero que en el fondo esconden subordinación y condescendencia hacia la mujer. Por ejemplo, en su investigación computacional sobre misoginia en México, Vera Lagos (2021) documenta el uso de refranes populares o frases hechas que perpetúan la discriminación de género en redes sociales, tales como la expresión *"calladita te ves más bonita"* (p. 23). La IA debe identificar que, aunque no existan groserías en la oración, hay una clara intención de silenciamiento.

**Marcadores para el algoritmo:** *calladita, te ves más bonita, las mujeres no saben, tenías que ser mujer*.

**Unidades de análisis (ejemplos reales):**

- "calladita te ves más bonita" (Vera Lagos, 2021, p. 23) — ejemplo prototípico de micromachismo encapsulado en forma de consejo estético.

---

### Regla 2: Sarcasmo, ironía y humor hostil

**Descripción algorítmica:** El sistema debe identificar aquellos mensajes donde la violencia y la estigmatización se escudan detrás de la comedia. Investigadoras como Cicua Castro y Calderón López (2024) advierten que el humor se utiliza habitualmente como excusa para dañar a activistas y mujeres, lo cual normaliza la agresión. Asimismo, Calderón-Suárez et al. (2024) señalan que el lenguaje abusivo suele ocultarse a través de chistes o comentarios sarcásticos, logrando evadir los filtros algorítmicos convencionales (p. 242).

**Marcadores para el algoritmo:** *jajaja, es solo humor, era una broma, generación de cristal*.

**Unidades de análisis (ejemplos reales):**

- Imagen viral con la frase "Habría menos feminicidios si no salieran de la cocina" — ejemplo de instrumentalización del sarcasmo para justificar la violencia letal bajo la máscara de una simple broma (Cicua Castro y Calderón López, 2024).

---

### Regla 3: Falsos positivos por reapropiación del lenguaje o denuncia

**Descripción algorítmica:** El algoritmo debe ser capaz de identificar cuándo una palabra teóricamente ofensiva se está utilizando para denunciar un acto sexista o para expresar camaradería, evitando así castigar a la víctima (falso positivo). Al respecto, Úbeda Cuspinera (2025) demuestra empíricamente que los mensajes de denuncia feminista suelen incorporar los mismos estereotipos machistas, como las expresiones *"mujer florero"* o *"mujer al volante"*, pero con el objetivo de criticarlos, lo que genera confusión en la Inteligencia Artificial (p. 196). De igual manera, ocurren falsos positivos cuando se emplean insultos en contextos positivos o de confianza; por ejemplo, la investigadora Ramos-Pérez (2025) documenta en su análisis de redes sociales cómo frases del tipo *"¡La puta eres un crack!"* utilizan una palabra malsonante sin ninguna intención de herir, sino como un halago coloquial.

**Marcadores de contexto mitigador (NO son ataques):** *visión arcaica, denuncia, no es verdad que, eres un crack*.

**Unidades de análisis (ejemplos de falsos positivos a evitar):**

- "La visión de mujer florero del vídeo es más bien arcaica" (Úbeda Cuspinera, 2025, p. 200). Un algoritmo básico clasificaría este texto erróneamente como misógino por contener la etiqueta *"mujer florero"*, pero un algoritmo entrenado pragmáticamente identificará que la palabra *"arcaica"* invierte el sentido de la oración, convirtiéndola en una crítica feminista legítima.

## 4. Reglas Generales de Inclusión Algorítmica

Esta categoría opera como **módulo de salvaguarda** del sistema. Aplica de forma obligatoria:

- **Criterio de contexto pragmático** (ver [Protocolo algorítmico general](./00-protocolo-algoritmico.md), sección 3): toda clasificación de las categorías 1, 2, 3, 4 y 5 debe pasar por un filtro pragmático antes de confirmarse como ataque. La Regla 3 de esta categoría es la implementación concreta de ese filtro.

> **Recomendación de implementación:** entrenar un clasificador binario auxiliar `es_ataque_real | es_reapropiación` que se ejecute *después* de que el clasificador principal haya marcado un mensaje como positivo en cualquiera de las otras cinco categorías. El objetivo es reducir la tasa de falsos positivos que castigan a víctimas y activistas.

## Bloque para prompt

```
USO DE Cat. 6 (ortogonal):
- 6.1 sarcasmo/ironía que vehiculariza un ATAQUE → es VDG, devolve la
  categoría sustantiva correspondiente (1.x, 2.x, etc.) y agregá 6.1
  SOLO si el sarcasmo ES la carga agresiva principal.
- 6.2 humor hostil que ENMASCARA una agresión → es VDG, mismo criterio.
- 6.3 reapropiación endogrupal / cita / denuncia con marcadores
  mitigadores → NO es VDG, devolvé `clasificaciones: []` con
  `es_falso_positivo_probable: true`. Esta categoría casi nunca
  coexiste con otra sustantiva.
Si NO estás seguro entre 6.x y otra categoría, priorizá la categoría
sustantiva (1.x, 2.x, etc.) y dejá `es_falso_positivo_probable: true`
en lugar de inventar una 6.x.
```
