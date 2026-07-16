---
id: cat-5
numero: 5
titulo: Castigo del empoderamiento femenino
subdimensiones: 3
reglas: 3
gravedad: media-alta
---

# Categoría 5: Castigo del empoderamiento femenino

## Regla de alcance

Toda esta categoría es exclusiva para ataques dirigidos a mujeres con perfil público o a movimientos de mujeres: periodistas, activistas, presentadoras, políticas, manifestantes y colectivos feministas. El sistema debe identificar a quién va dirigido el mensaje antes de asignar una subdimensión.

## 5.1. Deslegitimación del empoderamiento

Identifica ataques contra feministas y mujeres con perfil público que las tildan de `traumadas`, `exageradas`, `histéricas`, `locas`, `ardidas`, `tóxicas` o buscadoras de atención para invalidar sus denuncias, forzar su autocensura y expulsarlas del debate público. También incluye el uso de `feminismo radical` o `hembrismo` para caricaturizar el discurso de una activista concreta.

**Regla estricta:** no confundir con 1.3. La 1.3 ataca a mujeres comunes en su cotidianidad por irracionalidad o falta de decoro; la 5.1 exige una activista, figura pública o movimiento identificable. Tampoco confundir con 4.2: si el blanco es el feminismo como movimiento y el núcleo es la misandria, las leyes o la victimización masculina, corresponde a 4.2.

**Ejemplo:** `Canal de una mujer traumada y ardida, no me importa lo de Arrieta, todos estos videos son tóxicos y parciales`.

## 5.2. Ridiculización tradicional del empoderamiento

Identifica expresiones denigrantes dirigidas a activistas, manifestantes, periodistas o políticas que les ordenan regresar al espacio doméstico. Es un castigo social por irrumpir en la esfera política y pública, especialmente en marchas y protestas como el 8M.

El sistema debe localizar imperativos de limpieza, cocina, cuidado o retiro combinados con burla de la movilización: `váyanse a lavar`, `a la cocina`, `limpien sus casas`, `cuiden a sus hijos`, `váyanse a dormir`, `ridículas`, `viejas webonas`, `pónganse a trabajar`.

**Regla estricta:** si una mujer recibe una orden doméstica en su vida privada o cotidiana, corresponde a 1.1. Para activar 5.2 es obligatorio que el contexto público, la marcha, el cargo, el nombre propio, la cuenta o el movimiento permitan identificar el castigo político. Si ambos núcleos aparecen, multicategorizar 1.1 y 5.2.

**Ejemplos:** `Que vayan a limpiar sus casas y cuidar a sus hijos en vez de armar este borlote`; `Váyanse a lavar los calzones`; `Váyanse a dormir, ridículas`.

## 5.3. Falacia de superioridad moral

Identifica mensajes que acusan a activistas de hipocresía política y tergiversan conceptos del movimiento igualitario para desvirtuar sus reivindicaciones. El agresor invoca `igualdad`, `respeto` o `doble moral` para afirmar que las feministas son hipócritas y destruir su credibilidad pública.

**Regla estricta:** si acusa al feminismo de `misandria`, se queja de leyes de género o usa `feminazi` para presentar la igualdad como dictadura, corresponde a 4.2. Si `doble moral` juzga la vida sexual de una mujer, corresponde a 2.3. Para activar 5.3 el núcleo debe ser la acusación de hipocresía política contra una activista o movimiento público.

**Ejemplos:** `El feminismo lucha por la igualdad, pero ustedes faltan el respeto al sexo masculino`; `Después están pidiendo igualdad de género`.

## Multicategorización

Un comentario puede combinar 5.1, 5.2 y 5.3 si contiene ataques independientes. La categoría 6.2 puede agregarse cuando la deslegitimación se enmascara con risa, sarcasmo o formato de broma. Una cita o denuncia feminista con marcadores mitigadores debe pasar por 6.3 antes de confirmar cualquier alerta.

## Bloque para prompt

```
USO DE Cat. 5 (castigo del empoderamiento femenino):
- Es exclusiva para activistas, periodistas, políticas, presentadoras,
  manifestantes y mujeres con perfil público.
- 5.1 patologización o irracionalidad dirigida a una figura pública.
- 5.2 órdenes domésticas usadas para ridiculizar una protesta o activismo.
- 5.3 acusación de hipocresía política usando igualdad, respeto o doble moral.
- Si el blanco es una mujer común, usar 1.1 o 1.3 según el núcleo.
- Si el ataque invierte los roles y presenta a los hombres como víctimas
  del feminismo o de sus leyes, usar 4.2.
```
