---
id: cat-6
numero: 6
titulo: Control de resistencia, sarcasmos y falsos positivos
subdimensiones: 3
reglas: 3
gravedad: ortogonal
naturaleza: categoria-ortogonal
---

# Categoría 6: Control de resistencia, sarcasmos y falsos positivos

Esta categoría identifica la forma pragmática del mensaje: agresión sutil, humor hostil o uso legítimo de términos ofensivos en una denuncia. Funciona como capa transversal y puede multicategorizarse con las categorías sustantivas. La subdimensión 6.3 es una salvaguarda protectora, no una etiqueta de ciberviolencia.

## 6.1. Micromachismos y mansplaining

Identifica mensajes que no usan vocabulario abiertamente hostil ni insultos directos, sino presuposiciones, dobles sentidos, falsos elogios, refranes o consejos condescendientes para subordinar, silenciar o invalidar a una mujer. Requiere evaluar el contexto pragmático y detectar la agresión implícita incluso sin groserías.

**Regla estricta:** el núcleo debe ser la agresión sutil y debe faltar lenguaje hostil explícito. No activar 6.1 si el mensaje contiene insultos directos o ataques frontales como `zorra`, `feminazi`, `loca` o `inútil`; esas expresiones deben clasificarse en la categoría sustantiva correspondiente.

**Ejemplo:** `Calladita te ves más bonita`. Literalmente parece un elogio, pero funciona como orden de silenciamiento y reduce el aporte de la mujer a su apariencia.

## 6.2. Humor hostil

Identifica cuando la burla, la ironía, el sarcasmo, la cultura memética o la risa enmascaran una agresión machista. El agresor presenta el ataque como simple broma para eludir la sanción social y técnica. `Jajaja`, `jaja`, `es solo humor` o `era una broma` no vuelven inofensivo el mensaje cuando existe un núcleo agresivo.

**Ejemplos:** `Habría menos feminicidios si no salieran de la cocina jajaja`; `Pura licenciada jajaja, ya póngase a chambear`.

La primera frase debe multicategorizarse en 3.3 por apología al feminicidio, 1.1 por el mandato doméstico y 6.2 por el humor hostil. La segunda puede activar 5.2 y 6.2 cuando está dirigida a una protesta o activista.

## 6.3. Salvaguarda y falsos positivos

Identifica el uso de palabras ofensivas, estereotipos o arquetipos sexistas dentro de una denuncia, refutación, cita, crítica feminista, reapropiación defensiva o expresión de solidaridad. El sistema debe buscar marcadores mitigadores, negaciones, preguntas retóricas de defensa y consignas feministas antes de confirmar una alerta.

**Marcadores mitigadores:** `arcaica`, `retrógrada`, `patriarcal`, `machista`, `denunciar`, `repudiar`, `visibilizar`, `criticar`, `desmontar`, `no es verdad que`, `en realidad`, `sin embargo`, `#NiUnaMenos`, `#8M`, `#VivasNosQueremos`, comillas y citas explícitas.

**Regla estricta de sobreescritura:** si un estereotipo o insulto está enmarcado en una refutación, denuncia o pregunta retórica de defensa, 6.3 anula las alertas de las categorías 1, 2, 3, 4 y 5. El resultado debe ser un uso legítimo del lenguaje, con `tiene_violencia: false` y `es_falso_positivo_probable: true`.

**Ejemplo:** `La visión de mujer florero del vídeo es más bien arcaica`. La palabra `mujer florero` aparece como objeto de crítica, no como ataque.

## Reglas de aplicación

- 6.1, 6.2 y 6.3 no deben confundirse: 6.1 es sutileza sin insulto, 6.2 es humor que oculta una agresión y 6.3 es denuncia o reapropiación no agresiva.
- La risa es un agravante de burla cuando existe ataque; no es una condición suficiente para clasificar un texto aislado.
- Cuando 6.3 se activa, no deben persistir etiquetas sustantivas que solo dependan del marcador citado o refutado.
- La clasificación debe conservar las capas independientes de violencia mediante multicategorización, salvo cuando la salvaguarda 6.3 anule el falso positivo.

## Bloque para prompt

```
USO DE Cat. 6 (control de resistencia, sarcasmos y falsos positivos):
- 6.1 micromachismos y mansplaining: agresión sutil sin insulto directo.
- 6.2 humor hostil: risa, sarcasmo o broma usada para enmascarar un ataque;
  multicategorizar con la categoría sustantiva.
- 6.3 salvaguarda: denuncia, cita, refutación o reapropiación no agresiva;
  sobreescribe las alertas y devuelve clasificaciones vacías.
- La risa aislada sin ataque no activa 6.2.
```
