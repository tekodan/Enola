---
id: cat-5
numero: 5
titulo: Control de resistencia, sarcasmos y falsos positivos
subdimensiones: 3
reglas: 3
gravedad: baja (alta complejidad técnica)
naturaleza: categoria-ortogonal
---

# Categoría 5: Control de resistencia, sarcasmos y falsos positivos

> **Naturaleza especial:** a diferencia de las categorías 1-4 y 6, que describen formas sustantivas de violencia, esta categoría opera de manera **transversal y ortogonal**: describe una *modalidad de expresión* (ironía, sarcasmo, micromachismos) que puede vehicular contenido de cualquier otra categoría, a la vez que delimita el principal riesgo técnico del modelo: los falsos positivos por falta de contexto pragmático. Por este motivo, no tiene "gravedad" propia sino que modula la detección de las demás.

## 1. Definición Conceptual

El control de resistencia y los sarcasmos en los entornos virtuales constituyen mecanismos encubiertos de violencia simbólica, mediante los cuales los agresores emplean el humor, la ironía y la falsa cortesía para disciplinar a las mujeres y atacar al movimiento feminista sin asumir el costo social de una agresión directa. Investigadores como Campillo Muñoz (2022) señalan que la ironía es un recurso ampliamente utilizado en las redes sociales para cometer violencia verbal no explícita, operando como un conducto que permite a los usuarios expulsar su rechazo e ira de forma disfrazada (p. 27). En este sentido, autoras como Crosas Remón y Medina-Bravo (2019) exponen que el tono humorístico en las plataformas digitales se emplea estratégicamente para invisibilizar el daño y hacer que la agresión machista resulte socialmente aceptable.

A nivel computacional y forense, estas expresiones representan un desafío crítico, puesto que su naturaleza implícita genera constantes errores (falsos positivos y falsos negativos) en la Inteligencia Artificial. Tal y como advierten Syafi-Muhammad y Ruldeviyani (2020, citados en Suárez-Álvarez et al., 2025), la codificación automática presenta graves limitaciones estructurales para decodificar las expresiones sarcásticas, la cultura memética y las frases con doble sentido, lo que exige entrenar a los sistemas bajo perspectivas pragmáticas y de contexto para evitar que el algoritmo clasifique un ataque sutil como un comentario inofensivo.

## 2. Subdimensiones Analíticas

### 5.1. Sexismo implícito y presuposiciones

Comprende aquellos mensajes que no utilizan un vocabulario abiertamente hostil o insultos directos, sino que recurren a presuposiciones o implicaturas para denigrar a las mujeres. Como explica Sbisà (2021), en estos casos la agresión se oculta en dobles sentidos, falsos elogios o en un tono de condescendencia machista (mansplaining). A nivel computacional, estas tácticas de resistencia discursiva exigen un elevado esfuerzo para su procesamiento, ya que los sistemas básicos no logran leer "entre líneas" la intención coercitiva del emisor (Yus, 2010).

### 5.2. Humor hostil, ironía y sarcasmo

Agrupa las dinámicas donde el agresor instrumentaliza la burla y el formato de la comedia para enmascarar su violencia. Al presentarse como una simple "broma", el atacante busca eludir la sanción social y técnica. Rodríguez-Sánchez, Carrillo-de-Albornoz y Plaza (2024) advierten empíricamente que estas estrategias complican severamente la detección automática, debido a la profunda incongruencia que existe entre el significado literal de las palabras utilizadas y la verdadera intención denigrante del agresor.

### 5.3. Reapropiación del lenguaje y falsos positivos algorítmicos

Identifica una de las mayores limitaciones de la Inteligencia Artificial frente a los textos cortos: la incapacidad temporal de comprender el contexto de denuncia. Ocurre cuando las propias activistas o víctimas emplean términos teóricamente ofensivos (como repetir un insulto que recibieron para denunciarlo públicamente, o usar palabras estigmatizantes desde el empoderamiento y la ironía defensiva). Al limitarse a buscar un "diccionario de malas palabras", el algoritmo marca erróneamente el mensaje de la víctima como si fuera un ataque, generando lo que en la ingeniería de datos se conoce como un **falso positivo**.

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

- **Criterio de contexto pragmático** (ver [Protocolo algorítmico general](./00-protocolo-algoritmico.md), sección 3): toda clasificación de las categorías 1-4 y 6 debe pasar por un filtro pragmático antes de confirmarse como ataque. La Regla 3 de esta categoría es la implementación concreta de ese filtro.

> **Recomendación de implementación:** entrenar un clasificador binario auxiliar `es_ataque_real | es_reapropiación` que se ejecute *después* de que el clasificador principal haya marcado un mensaje como positivo en cualquiera de las otras cinco categorías. El objetivo es reducir la tasa de falsos positivos que castigan a víctimas y activistas.

## Bloque para prompt

```
USO DE Cat. 5 (ortogonal):
- 5.1 sarcasmo/ironía que vehiculariza un ATAQUE → es VDG, devolve la
  categoría sustantiva correspondiente (1.x, 2.x, etc.) y agregá 5.1
  SOLO si el sarcasmo ES la carga agresiva principal.
- 5.2 humor hostil que ENMASCARA una agresión → es VDG, mismo criterio.
- 5.3 reapropiación endogrupal / cita / denuncia con marcadores
  mitigadores → NO es VDG, devolvé `clasificaciones: []` con
  `es_falso_positivo_probable: true`. Esta categoría casi nunca
  coexiste con otra sustantiva.
Si NO estás seguro entre 5.x y otra categoría, priorizá la categoría
sustantiva (1.x, 2.x, etc.) y dejá `es_falso_positivo_probable: true`
en lugar de inventar una 5.x.
```
