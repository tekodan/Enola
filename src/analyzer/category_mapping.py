"""Canonical mapping of digital gender violence categories and sub-dimensions.

The taxonomy of digital gender violence is **homogeneous and alphabetic for
categories** and **numeric for sub-dimensions**. The LLM is instructed via
the system prompt to pick one of the 18 valid combinations — never invent.

Single source of truth for:

- The 6 valid category codes (alphabetic, ``VDG_*``)
- The 18 valid sub-dimension codes (numeric, ``1.1``..``6.3``)
- Validation/normalization of LLM output
- The compact canonical table that gets injected into the prompt
- A severity scale normalizer (``"baja-media"`` → ``Severity.BAJA``, etc.)

Located in ``src/analyzer/`` because it is consumed by the classifier; it
has no dependency on ChromaDB.
"""

from __future__ import annotations

import logging
from enum import StrEnum

from src.analyzer.violence_types import Severity

logger = logging.getLogger(__name__)


class Categoria(StrEnum):
    """Canonical alphabetic codes for the 6 categories of digital gender violence.

    These are the ONLY valid values for ``ClassificationResult.categoria``.
    The LLM is forced to pick one (or ``NINGUNA``). Any other string is
    rejected and logged as a warning.
    """

    VDG_VIOLENCIA_SIMBOLICA = "VDG_VIOLENCIA_SIMBOLICA"
    VDG_COSIFICACION_SLUTSHAMING = "VDG_COSIFICACION_SLUTSHAMING"
    VDG_HOSTILIDAD_FEMINICIDIO = "VDG_HOSTILIDAD_FEMINICIDIO"
    VDG_MANOSFERA_ANTIFEMINISMO = "VDG_MANOSFERA_ANTIFEMINISMO"
    VDG_SALVAGUARDA_FALSO_POSITIVO = "VDG_SALVAGUARDA_FALSO_POSITIVO"
    VDG_DESACREDITACION_ACTIVISTAS = "VDG_DESACREDITACION_ACTIVISTAS"
    NINGUNA = "ninguna"


# 18 valid (categoria, dimension) combinations
SUBDIMENSIONES_POR_CATEGORIA: dict[str, list[str]] = {
    Categoria.VDG_VIOLENCIA_SIMBOLICA.value: ["1.1", "1.2", "1.3"],
    Categoria.VDG_COSIFICACION_SLUTSHAMING.value: ["2.1", "2.2", "2.3"],
    Categoria.VDG_HOSTILIDAD_FEMINICIDIO.value: ["3.1", "3.2", "3.3"],
    Categoria.VDG_MANOSFERA_ANTIFEMINISMO.value: ["4.1", "4.2", "4.3"],
    Categoria.VDG_SALVAGUARDA_FALSO_POSITIVO.value: ["5.1", "5.2", "5.3"],
    Categoria.VDG_DESACREDITACION_ACTIVISTAS.value: ["6.1", "6.2", "6.3"],
}


# One-line description of each sub-dimension, used in the prompt table
DESCRIPCION_SUBDIMENSION: dict[str, str] = {
    # cat 1
    "1.1": "Roles y estereotipos de género",
    "1.2": "Mandatos de sumisión y reclusión",
    "1.3": "Adjetivación despectiva / deshumanización",
    # cat 2
    "2.1": "Cosificación corporal / hipersexualización",
    "2.2": "Slut-shaming / deslegitimación sexual",
    "2.3": "Packs / exhibición no consentida",
    # cat 3
    "3.1": "Amenazas de agresión o letalidad",
    "3.2": "Justificación de la violencia",
    "3.3": "Apología del feminicidio",
    # cat 4
    "4.1": "Ideología antifeminista declarada",
    "4.2": "Jerga de subculturas (Incel/MGTOW/PUA/MRA)",
    "4.3": "Deshumanización / animalización",
    # cat 5 — ortogonal: salvaguarda contra falsos positivos
    "5.1": "Sarcasmo / ironía",
    "5.2": "Reapropiación / uso endogrupal",
    "5.3": "Marcadores mitigadores / cita / denuncia",
    # cat 6
    "6.1": "Deslegitimación de feministas en abstracto",
    "6.2": "Ataques a activistas específicas",
    "6.3": "Desinformación sobre feminismo",
}


GRAVEDAD_POR_CATEGORIA: dict[str, str] = {
    Categoria.VDG_VIOLENCIA_SIMBOLICA.value: "baja-media",
    Categoria.VDG_COSIFICACION_SLUTSHAMING.value: "media",
    Categoria.VDG_HOSTILIDAD_FEMINICIDIO.value: "alta-extrema",
    Categoria.VDG_MANOSFERA_ANTIFEMINISMO.value: "media-alta",
    Categoria.VDG_SALVAGUARDA_FALSO_POSITIVO.value: "ortogonal",
    Categoria.VDG_DESACREDITACION_ACTIVISTAS.value: "media-alta",
}


CATEGORIAS_ORDENADAS: list[str] = [
    Categoria.VDG_VIOLENCIA_SIMBOLICA.value,
    Categoria.VDG_COSIFICACION_SLUTSHAMING.value,
    Categoria.VDG_HOSTILIDAD_FEMINICIDIO.value,
    Categoria.VDG_MANOSFERA_ANTIFEMINISMO.value,
    Categoria.VDG_SALVAGUARDA_FALSO_POSITIVO.value,
    Categoria.VDG_DESACREDITACION_ACTIVISTAS.value,
]


def normalize_categoria(value: object) -> str:
    """Normalize a free-form category string to a canonical code.

    Accepts: ``"VDG_VIOLENCIA_SIMBOLICA"``, ``"violencia simbolica"``,
    ``"violencia-simbólica"``, ``"Violencia Simbólica"``, etc.
    Returns the canonical ``VDG_*`` code (or ``"ninguna"`` if it cannot
    be matched).

    Strategy: lowercase, strip accents, collapse non-alphanumerics to
    underscores, then try to match the suffix against each canonical
    value's normalized form.
    """
    import unicodedata

    if value is None:
        return Categoria.NINGUNA.value
    raw = str(value).strip()
    if not raw:
        return Categoria.NINGUNA.value

    if raw in {c.value for c in Categoria}:
        return raw

    def _norm(s: str) -> str:
        nfkd = unicodedata.normalize("NFKD", s)
        ascii_form = "".join(c for c in nfkd if not unicodedata.combining(c))
        lowered = ascii_form.lower()
        collapsed = "".join(c if c.isalnum() else "_" for c in lowered)
        return "_".join(part for part in collapsed.split("_") if part)

    target = _norm(raw)
    for cat in Categoria:
        canon_norm = _norm(cat.value)
        if target == canon_norm:
            return cat.value
        if target in canon_norm or canon_norm.endswith(target):
            return cat.value

    logger.warning(
        "LLM devolvió categoría fuera del set canónico: %r — normalizando a 'ninguna'",
        raw,
    )
    return Categoria.NINGUNA.value


def normalize_dimension(categoria: str, dimension: object) -> str | None:
    """Normalize and validate a sub-dimension against the category.

    Returns the canonical dimension (``"1.1"`` etc.) or ``None`` if:
    - the dimension is missing/empty
    - the category is ``"ninguna"``
    - the dimension is not in the valid list for that category
    """
    if dimension is None:
        return None
    raw = str(dimension).strip()
    if not raw or raw.lower() in {"null", "none", "ninguna"}:
        return None
    if categoria == Categoria.NINGUNA.value:
        return None

    valid = SUBDIMENSIONES_POR_CATEGORIA.get(categoria, [])
    if raw in valid:
        return raw

    if raw.startswith("0"):
        candidate = raw.lstrip("0") or "0"
        if candidate in valid:
            return candidate

    logger.warning(
        "LLM devolvió dimensión inválida %r para categoría %r — normalizando a null",
        raw,
        categoria,
    )
    return None


def validate_codigo(categoria: object, dimension: object) -> tuple[str, str | None]:
    """Validate and normalize a (categoria, dimension) pair.

    Returns ``(canonical_categoria, canonical_dimension_or_None)``.

    This is the **only** function the rest of the codebase should call
    to validate LLM output for these two fields.
    """
    cat = normalize_categoria(categoria)
    dim = normalize_dimension(cat, dimension)
    return cat, dim


def map_gravedad(value: object) -> Severity:
    """Map a free-form severity string to the closed ``Severity`` enum.

    The taxonomy in ``knowledge/`` uses compound labels like
    ``"baja-media"`` or ``"alta-extrema"``; the classifier's enum is
    closed. This function picks the **lower** bound of the compound
    (the conservative choice — don't over-flag):

    - ``"baja"`` / ``"baja-media"`` → ``Severity.BAJA``
    - ``"media"`` / ``"media-alta"`` → ``Severity.MEDIA``
    - ``"alta"`` / ``"alta-extrema"`` / ``"extrema"`` → ``Severity.ALTA``
    - anything else (``"ninguna"``, ``""``, ``None``) → ``Severity.NINGUNA``
    """
    if value is None:
        return Severity.NINGUNA
    raw = str(value).strip().lower()
    if not raw or raw in {"ninguna", "none", "null"}:
        return Severity.NINGUNA
    # Compound "X-Y" → take the lower bound (X) to be conservative.
    if "-" in raw:
        raw = raw.split("-")[0]
    if raw == "baja":
        return Severity.BAJA
    if raw == "media":
        return Severity.MEDIA
    if raw in {"alta", "extrema"}:
        return Severity.ALTA
    logger.warning("Gravedad fuera del set: %r — normalizando a NINGUNA", value)
    return Severity.NINGUNA


def render_tabla_canonica_prompt() -> str:
    """Render the compact 18-row canonical table to inject into the prompt.

    The table is the single source of truth the LLM sees for valid
    categoria/dimension combinations. It is intentionally short to keep
    the prompt small (~600 tokens).
    """
    lines = [
        "CATEGORÍAS VÁLIDAS (elegí EXACTAMENTE una fila, o 'ninguna' si no encaja):",
        "",
        "| categoria                          | dimension | descripcion                                |",
        "|------------------------------------|-----------|--------------------------------------------|",
    ]
    for cat in CATEGORIAS_ORDENADAS:
        dims = SUBDIMENSIONES_POR_CATEGORIA[cat]
        for i, d in enumerate(dims):
            cat_cell = cat if i == 0 else ""
            desc = DESCRIPCION_SUBDIMENSION.get(d, "")
            lines.append(f"| {cat_cell:<34} | {d:<9} | {desc:<42} |")
    lines.append("")
    lines.append(
        "Si el texto no encaja en ninguna categoría: 'categoria': 'ninguna', 'dimension': null."
    )
    return "\n".join(lines)


def render_severidad_prompt() -> str:
    """Render the severity scale legend for the prompt."""
    return (
        "ESCALA DE SEVERIDAD (fija):\n"
        '- "baja"     → violencia implícita, estereotipos, micromachismos\n'
        '- "media"    → insultos, cosificación, deslegitimación\n'
        '- "alta"     → amenazas, hostilidad letal, acoso coordinado\n'
        '- "ninguna"  → sin violencia detectada (o caso ortogonal)'
    )


__all__ = [
    "Categoria",
    "SUBDIMENSIONES_POR_CATEGORIA",
    "DESCRIPCION_SUBDIMENSION",
    "GRAVEDAD_POR_CATEGORIA",
    "CATEGORIAS_ORDENADAS",
    "normalize_categoria",
    "normalize_dimension",
    "validate_codigo",
    "map_gravedad",
    "render_tabla_canonica_prompt",
    "render_severidad_prompt",
]
