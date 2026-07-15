"""Prompt renderers for the RAG classifier (SSoT-driven).

Generates the canonical prompt blocks the LLM consumes, derived
100% from the loaded :class:`Taxonomy`. The classifiers pass these
strings verbatim into the final prompt.

Blocks produced:

- :func:`render_tabla_canonica` — closed table of (categoria,
  dimension, descripcion) for the LLM's closure set.
- :func:`render_marcadores_bloque` — canonical markers per
  sub-dimension with overlap notes.
- :func:`render_desempate_bloque` — tie-breaker rules (R2 + R3
  of the recomendaciones doc).
- :func:`render_leetspeak_bloque` — leetspeak→canonical
  equivalences.
- :func:`render_mitigadores_bloque` — anti-false-positive markers.
- :func:`render_referentes_bloque` — female referent co-occurrence
  rule.
- :func:`render_multi_etiqueta_bloque` — multi-label instruction
  for Cat. 4 (R6).
"""

from __future__ import annotations

from src.analyzer.category_mapping import CATEGORIAS_ORDENADAS, MAX_LABELS
from src.analyzer.taxonomy_loader import (
    ReglaDesempateMD,
    Taxonomy,
    get_taxonomy,
)


def _tx() -> Taxonomy:
    """Return the cached taxonomy (test-friendly indirection)."""
    return get_taxonomy()


def render_tabla_canonica() -> str:
    """Render the canonical (categoria, dimension, descripcion) table."""
    tx = _tx()
    out: list[str] = [
        f"CATEGORÍAS VÁLIDAS (elegí HASTA {MAX_LABELS} filas — una por cada "
        "categoría que aplique; usá 'ninguna' SOLO en la lista vacía):",
        "",
        "| categoria | dimension | descripcion |",
        "|---|---|---|",
    ]
    for cat_code in CATEGORIAS_ORDENADAS:
        cat = next(c for c in tx.categorias if c.code == cat_code)
        for i, dim in enumerate(cat.subdimensiones):
            cat_cell = cat.code if i == 0 else ""
            out.append(f"| {cat_cell:<34} | {dim.code:<9} | {dim.descripcion} |")
    out.append("")
    out.append(
        "Si el texto no encaja en ninguna categoría: devolve `clasificaciones: []` "
        "y `tiene_violencia: false`."
    )
    return "\n".join(out)


def render_marcadores_bloque() -> str:
    """Render the canonical markers per sub-dimension with overlap notes."""
    tx = _tx()
    out: list[str] = [
        "MARCADORES_CANONICOS (ejemplos ilustrativos de patrones semánticos — la lista "
        "NO es cerrada; si el texto exhibe el MISMO PATRÓN SEMÁNTICO que los ejemplos "
        "listados, la sub-dimensión correspondiente es candidata):",
        "",
    ]
    for cat_code in CATEGORIAS_ORDENADAS:
        cat = next(c for c in tx.categorias if c.code == cat_code)
        for dim in cat.subdimensiones:
            title = dim.descripcion.split(".")[0][:60]
            markers = ", ".join(dim.marcadores_canonicos[:8])
            extra = (
                f" (y {len(dim.marcadores_canonicos) - 8} más)"
                if len(dim.marcadores_canonicos) > 8
                else ""
            )
            out.append(f"- {dim.code} ({cat.code}) — {title}: {markers}{extra}")
            for ov in dim.marcadores_overlap:
                out.append(
                    f"    ↳ overlap con {ov.subdim_secundaria}: "
                    f"si aparece «{ov.marker}» → {ov.regla}"
                )
    out.append("")
    out.append(
        "Cada marcador puede disparar a UNA sub-dimensión salvo que esté declarado "
        "explícitamente en `marcadores_overlap` (ver entradas ↳ arriba)."
    )
    return "\n".join(out)


def render_desempate_bloque() -> str:
    """Render the tie-breaker rules (reglas_desempate)."""
    tx = _tx()
    rules: list[ReglaDesempateMD] = tx.desempate_rules()
    if not rules:
        return "(Sin reglas de desempate definidas en TAXONOMIA.md.)"
    out: list[str] = [
        "REGLAS DE DESEMPATE (cuando dos sub-dimensiones compiten por el mismo marcador):",
        "",
    ]
    for r in rules:
        out.append(f"### {r.id} — {r.frontera}")
        if r.disparador_primario:
            out.append(
                "Disparadores primarios (gana "
                + r.subdim_ganadora
                + "): "
                + ", ".join(r.disparador_primario)
            )
        if r.disparador_obligatorio:
            out.append(
                "Disparadores obligatorios (sin ellos, descartar "
                + r.subdim_ganadora
                + "): "
                + ", ".join(r.disparador_obligatorio)
            )
        if r.fallback:
            out.append(f"Fallback: {r.fallback}")
        out.append("")
    return "\n".join(out)


def render_leetspeak_bloque() -> str:
    """Render the leetspeak decoder block."""
    tx = _tx()
    mapping = tx.leetspeak_map()
    if not mapping:
        return "(Sin equivalencias leetspeak definidas.)"
    lines = [
        "DESCODIFICACIÓN OBLIGATORIA DE LEETSPEAK ANTES DE BUSCAR MARCADORES:",
        "(Si una variante leetspeak del input contiene alguno de los símbolos de abajo, "
        "reemplazalo mentalmente por su carácter canónico antes de evaluar marcadores.)",
        "",
    ]
    for src, dst in sorted(mapping.items()):
        lines.append(f"- '{src}' → '{dst}'")
    lines.append("")
    lines.append(
        "Para mutaciones más complejas (palabras enteras como 'mu3rte' → 'muerte'), "
        "consultá la lista de `marcadores_canonicos` (ya contiene las variantes leetspeak conocidas)."
    )
    return "\n".join(lines)


def render_mitigadores_bloque() -> str:
    """Render the anti-false-positive markers block."""
    tx = _tx()
    tokens = sorted(tx.mitigadores_set())
    if not tokens:
        return "(Sin marcadores mitigadores definidos.)"
    out: list[str] = [
        "MARCADORES_MITIGADORES → posible NO_VDG:",
        "Si el texto contiene UNO O MÁS de los siguientes tokens (en cualquier "
        "posición) CUMPLIENDO función de denuncia / cita / reapropiación "
        "endogrupal / crítica, devolvé `clasificaciones: []` y marcá "
        "`es_falso_positivo_probable: true`.",
        "",
        "Lista cerrada (tokens y frases exactas):",
        "",
    ]
    for tok in tokens:
        out.append(f"- {tok}")
    out.append("")
    out.append(
        "EXCEPCIÓN: si el texto cita el término mitigador pero NO lo usa en "
        "función de denuncia (p.ej. una cita burlesca tipo 'son unas retrógradas' "
        "SIN contexto denunciante), mantené la clasificación VDG con "
        "`es_falso_positivo_probable: true`."
    )
    return "\n".join(out)


def render_referentes_bloque() -> str:
    """Render the female-referent co-occurrence rule."""
    tx = _tx()
    refs = sorted(tx.referentes_femeninos_set())
    if not refs:
        return "(Sin referentes femeninos definidos.)"
    out: list[str] = [
        "REGLA DE COOCURRENCIA SEMÁNTICA (OBLIGATORIA):",
        "Salvo en Cat. 4 (manosfera) y Cat. 5 (sarcasmo/reapropiación), toda "
        "asignación de categoría REQUIERE un referente femenino EXPLÍCITO en el "
        "mismo texto. Lista cerrada de referentes válidos:",
        "",
    ]
    for ref in refs:
        out.append(f"- {ref}")
    out.append("")
    out.append(
        "Si el texto NO contiene ninguno de estos referentes ni un nombre propio "
        "femenino reconocible, devolvé `clasificaciones: []` con `tiene_violencia: false`."
    )
    return "\n".join(out)


def render_multi_etiqueta_bloque() -> str:
    """Render the multi-label instruction (R6) for Cat. 4."""
    tx = _tx()
    inst = tx.multi_etiqueta_instruccion
    if not inst:
        return ""
    return f"INSTRUCCIÓN MULTI-ETIQUETA:\n{inst.strip()}"


__all__ = [
    "render_tabla_canonica",
    "render_marcadores_bloque",
    "render_desempate_bloque",
    "render_leetspeak_bloque",
    "render_mitigadores_bloque",
    "render_referentes_bloque",
    "render_multi_etiqueta_bloque",
]
