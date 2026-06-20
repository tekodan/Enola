---
id: cat-6
numero: 6
titulo: Desacreditación de activistas y mujeres con perfil público
subdimensiones: 3
reglas: 3
gravedad: media-alta
---

# Categoría 6: Desacreditación de activistas y mujeres con perfil público

## 1. Definición Conceptual

La desacreditación en el ecosistema digital constituye una forma de violencia política orientada a anular el ejercicio efectivo de los derechos de las mujeres en la esfera pública. Autores como Domínguez Arteaga (2021) exponen que la ciberviolencia dirigida a activistas, periodistas y académicas opera como un mecanismo disciplinario y de castigo social ante su irrupción en los espacios de debate, utilizando la intimidación para forzarlas a regresar al espacio doméstico y a los roles tradicionales (p. 41).

En esta misma línea, investigaciones recientes publicadas en la Revista Punto Género (2024) demuestran que los discursos de odio sexista en plataformas virtuales no buscan argumentar frente a los postulados del feminismo, sino que emplean tácticas de polarización emocional negativa para caricaturizar a las activistas y destruir su credibilidad pública. En consecuencia, investigadoras como Frezzotti (2024) advierten que este hostigamiento sistemático vulnera la intimidad y genera un profundo efecto de autocensura, restringiendo el derecho a la libre manifestación y perpetuando la exclusión democrática de las mujeres en el entorno digital (p. 238).

## 2. Subdimensiones Analíticas

En cuanto a las subdivisiones analíticas, investigadoras como Kemekenidou (2020) y Amalia Toledo (2016) exponen que la ciberviolencia contra las mujeres en la esfera pública opera a través de tácticas específicas diseñadas para silenciar su activismo e invalidar sus argumentos. De acuerdo con la revisión de la literatura, esta categoría se subdivide en tres dinámicas de hostigamiento:

### 6.1. Deslegitimación ideológica y encasillamiento extremista

En las redes sociales, los agresores atacan frecuentemente a las feministas tildándolas de *"traumadas"*, *"exageradas"* o *"histéricas"* con el fin de deslegitimar su mensaje y forzar su autocensura. Autoras como Bonilla Sánchez (2024) evidencian en sus estudios que los atacantes utilizan recurrentemente términos como *"feminismo radical"* o *"hembrismo"* para caricaturizar los argumentos de las activistas y expulsarlas del debate público.

### 6.2. Imposición de roles tradicionales y ridiculización

Esta táctica se basa en expresiones denigrantes dirigidas a las mujeres con perfil público, en las cuales se les ordena regresar al espacio doméstico (como mandarlas *"a la cocina"*), operando como un castigo social por irrumpir en la esfera política y pública. Diferentes análisis sobre las interacciones digitales durante las manifestaciones del 8M confirman que los usuarios utilizan el sarcasmo y los insultos estereotipados para invalidar el derecho a la protesta de las mujeres.

### 6.3. Falsa superioridad moral y tergiversación

Constituye una estrategia discursiva en la que los atacantes acusan a las activistas de ejercer una *"doble moral"*, tergiversando los conceptos del propio movimiento igualitario para acusarlas de odiar a los hombres y desvirtuar así la legitimidad de sus reivindicaciones.

## 3. Reglas de Inclusión Algorítmica

### Regla 1: Deslegitimación ideológica y encasillamiento extremista

**Descripción algorítmica:** El algoritmo debe identificar adjetivos patológicos y sustantivos que retratan a las activistas como personas inestables emocionalmente o generadoras de conflictos irracionales.

**Marcadores para el algoritmo:** *traumada, ardida, tóxicos, feminismo radical*.

**Unidades de análisis (ejemplos reales):**

- "canal de una mujer traumada y ardida , no me importa una mierda lo de arrieta , y voy a repartir mierda en todos estos videos TOXICOS Y PARCIALES" (Bonilla Sánchez, 2024, p. 357).

---

### Regla 2: Imposición de roles tradicionales y ridiculización

**Descripción algorítmica:** La máquina debe localizar verbos imperativos que mandan a las mujeres a realizar labores de limpieza o cuidado, combinados con sustantivos que ofenden su movilización política.

**Marcadores para el algoritmo:** *váyanse a lavar, viejas webonas, ridículas*.

**Unidades de análisis (ejemplos reales):**

- Registros de comentarios opositores a las marchas del 8M: *"Vallanse a lavar los calzones"*, *"Pónganse a trabajas viejas webonas"*, *"Váyanse a dormir...ridículas"* (patrón algorítmico recurrente en análisis de interacciones digitales).

---

### Regla 3: Falsa superioridad moral y tergiversación

**Descripción algorítmica:** El sistema debe detectar expresiones estructuradas donde el agresor invoca conceptos de *"igualdad"* para acusar a las feministas de faltar al respeto o ser hipócritas ("Igualadas. Discursos de odio sexista", 2024). El análisis mediante minería de texto identificó que los agresores utilizan frecuentemente el término *"igualdad de género"* dentro de comentarios de polaridad negativa, instrumentalizándolo como un arma discursiva para tergiversar el debate ("Igualadas. Discursos de odio sexista", 2024).

**Marcadores para el algoritmo:** *doble moral, falta de respeto, igualdad de género, lucha por la igualdad*.

**Unidades de análisis (ejemplos reales):**

- "...me parece un falta de respeto con el sexo masculino, el feminismo lucha por la igualdad\! [...] Si son tan feministas no recaigan en faltas tan terribles como las del machismo" ("Igualadas. Discursos de odio sexista", 2024).
- "...si una mujer me fue infiel una no significa que todos sean infieles y me vayan a engañar. Y después están pidiendo igualdad de genero." ("Igualadas. Discursos de odio sexista", 2024).

## 4. Reglas Generales de Inclusión Algorítmica

- **Criterio de coocurrencia semántica** (ver [Protocolo algorítmico general](./00-protocolo-algoritmico.md), sección 1).
- **Criterio de enunciados imperativos hacia el ámbito privado** (ver [Protocolo algorítmico general](./00-protocolo-algoritmico.md), sección 4): la Regla 2 activa este criterio cuando aparecen imperativos colectivos contra mujeres en contextos de protesta o activismo.
- **Criterio de contexto pragmático** (ver [Protocolo algorítmico general](./00-protocolo-algoritmico.md), sección 3): la Regla 3 (tergiversación) es la que presenta mayor riesgo de falso positivo, porque términos como *"igualdad de género"* o *"doble moral"* pueden aparecer en textos genuinamente críticos. El algoritmo debe verificar que la mención esté vinculada a una acusación deslegitimadora contra la persona, no a una reflexión abstracta sobre el concepto.

> **Overlap con otras categorías:** los marcadores de la Regla 2 (Subdimensión 6.2) coinciden parcialmente con los de la [Categoría 1 — Regla 1](./01-categoria-1-violencia-simbolica.md). La diferencia operativa es: en Cat. 1 los imperativos se dirigen a *cualquier mujer* en tanto que representante del género; en Cat. 6 van dirigidos a *mujeres específicas con perfil público* (activistas, periodistas, políticas) como castigo por su irrupción en el debate. El algoritmo debe incorporar como feature la presencia del sustantivo con referente individual (nombre propio, "@", cargo) para diferenciar ambos casos.
