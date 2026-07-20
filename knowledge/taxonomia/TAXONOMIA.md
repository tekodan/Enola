---
version: "2.1.0"
schema: "taxonomia-v2"
descripcion: "Taxonomía canónica de violencia de género digital en seis categorías operativas y diecinueve subdimensiones. Catálogo alineado con finalfix.md. La categoría 4 incorpora cuatro subdimensiones; las categorías restantes tienen tres. La sección categorias_exclusion documenta las pseudo-categorías pre-clasificatorias CODIGO_99 y VIOLENCIA_COMUN."

categorias:
  - code: VDG_VIOLENCIA_SIMBOLICA
    label: "Violencia Simbólica"
    orden: 1
    gravedad: "baja-media"
    subdimensiones:
      - code: "1.1"
        descripcion: "Roles tradicionales y de sumisión"
      - code: "1.2"
        descripcion: "Incompetencia e inferioridad intelectual o física"
      - code: "1.3"
        descripcion: "Castigo moral y patologización"

  - code: VDG_COSIFICACION_SLUTSHAMING
    label: "Mercantilización Corporal"
    orden: 2
    gravedad: "media"
    subdimensiones:
      - code: "2.1"
        descripcion: "Cosificación e hipersexualización"
      - code: "2.2"
        descripcion: "Escrutinio corporal y body-shaming"
      - code: "2.3"
        descripcion: "Doble estándar sexual y slut-shaming"

  - code: VDG_HOSTILIDAD_FEMINICIDIO
    label: "Hostilidad / Feminicidio"
    orden: 3
    gravedad: "alta-extrema"
    subdimensiones:
      - code: "3.1"
        descripcion: "Castigos disciplinantes no sexuales"
      - code: "3.2"
        descripcion: "Deseos de violencia letal"
      - code: "3.3"
        descripcion: "Apología al feminicidio"

  - code: VDG_MANOSFERA_ANTIFEMINISMO
    label: "Manosfera / Antifeminismo"
    orden: 4
    gravedad: "media-alta"
    subdimensiones:
      - code: "4.1"
        descripcion: "Subculturas masculinistas y jerarquías de dominación"
      - code: "4.2"
        descripcion: "Oposición antifeminista y victimismo hegemónico"
      - code: "4.3"
        descripcion: "Trolleo, castigo y emasculación"
      - code: "4.4"
        descripcion: "Arquetipos femeninos deshumanizantes"

  - code: VDG_DESACREDITACION_ACTIVISTAS
    label: "Castigo Del Empoderamiento Femenino"
    orden: 5
    gravedad: "media-alta"
    subdimensiones:
      - code: "5.1"
        descripcion: "Deslegitimación del empoderamiento"
      - code: "5.2"
        descripcion: "Ridiculización tradicional del empoderamiento"
      - code: "5.3"
        descripcion: "Falacia de superioridad moral"

  - code: VDG_SALVAGUARDA_FALSO_POSITIVO
    label: "Salvaguarda (Falso Positivo)"
    orden: 6
    gravedad: "ortogonal"
    subdimensiones:
      - code: "6.1"
        descripcion: "Micromachismos y mansplaining"
      - code: "6.2"
        descripcion: "Humor hostil"
      - code: "6.3"
        descripcion: "Salvaguarda y falsos positivos"

categorias_exclusion:
  - code: EXC_BASURA_DIGITAL
    codigo_canonico: CODIGO_99
    descripcion: "Pseudo-categoría pre-clasificatoria para payloads vacíos, enlaces huérfanos, ruido tipográfico, risas puras, reacciones cortas y menciones a persona sin comentario. Las filas persisten para el reporte de valores perdidos y se excluyen de los denominadores de violencia."
  - code: EXC_VIOLENCIA_COMUN
    codigo_canonico: VIOLENCIA_COMUN
    descripcion: "Pseudo-categoría pre-clasificatoria para agresiones sin sesgo de género. Las filas persisten para auditoría y se excluyen de la distribución de categorías operativas."
---

# Taxonomía canónica de violencia de género digital

Esta taxonomía es la fuente de verdad estructural que consumen el clasificador RAG, la validación de códigos, la interfaz de revisión y los reportes. Las categorías operativas son seis y sus combinaciones válidas son las diecinueve subdimensiones numeradas del 1.1 al 6.3, con la excepción de la subdimensión adicional 4.4.

La multicategorización está permitida hasta el límite definido por `MAX_LABELS`. Las reglas de exclusión, los ejemplos y los marcadores detallados se mantienen en los documentos narrativos y glosarios de `knowledge/categorias-violencia-genero-digital/`.

## Criterios estructurales

- Las categorías operativas tienen códigos `VDG_*` estables.
- La categoría 4 contiene cuatro subdimensiones; las categorías 1, 2, 3, 5 y 6 contienen tres.
- La categoría 5 se reserva para ataques contra activistas, manifestantes, periodistas, políticas, presentadoras u otras mujeres con perfil público.
- La categoría 6 funciona como control de resistencia, humor hostil y salvaguarda contextual; la subdimensión 6.3 puede anular alertas cuando el uso es una denuncia, cita o reapropiación no agresiva.
- Las etiquetas `CODIGO_99` y `VIOLENCIA_COMUN` no son categorías operativas.

## Documentación complementaria

- `01-categoria-1-violencia-simbolica.md`
- `02-categoria-2-cosificacion-slutshaming.md`
- `03-categoria-3-hostilidad-feminicidio.md`
- `04-categoria-4-manosfera-antifeminismo.md`
- `05-categoria-5-desacreditacion-activistas.md`
- `06-categoria-6-sarcasmo-falsos-positivos.md`
- `07-tabla-canonica-prompt.md`

## Cómo editar la taxonomía

1. Modificar este archivo y los documentos narrativos correspondientes.
2. Mantener sincronizados los códigos `VDG_*`, los códigos de subdimensión y sus descripciones.
3. Actualizar los marcadores y reglas de desempate en `glosario/` cuando cambie una frontera semántica.
4. Reindexar ChromaDB con `python -m src.knowledge_base add --source knowledge/taxonomia/TAXONOMIA.md` y los documentos narrativos actualizados.
