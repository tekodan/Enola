"""Canonical mapping of digital gender violence categories and sub-dimensions.

The taxonomy of digital gender violence is **homogeneous and alphabetic for
categories** and **numeric for sub-dimensions**. The LLM is instructed via
the system prompt to pick up to ``MAX_LABELS`` valid combinations — never
invent.

The **structural data** (6 categories, 19 sub-dimensions, severity bands
and per-dimension descriptions) is the MD-canonical taxonomy at
``knowledge/taxonomia/TAXONOMIA.md``, loaded on import via
:mod:`src.analyzer.taxonomy_loader`.

The **alphabetic codes** themselves (``VDG_*``) are the closure language
the LLM must respect. They are encoded as :class:`Categoria` (StrEnum)
here in code because Python enums cannot be created dynamically while
preserving stable ``.name``/``.value`` attributes (which the rest of the
codebase relies on). At import time we verify that the MD's category
codes match the enum members; mismatches raise :class:`RuntimeError`.

This module is the **facade** of the taxonomy in the codebase:

- :class:`Categoria` — the closure enum (code)
- :data:`CATEGORIAS_ORDENADAS`, :data:`SUBDIMENSIONES_POR_CATEGORIA`,
  :data:`DESCRIPCION_SUBDIMENSION`, :data:`GRAVEDAD_POR_CATEGORIA`,
  :data:`SUBDIMENSIONES_ORDENADAS`, :data:`CATEGORIA_POR_SUBDIMENSION` —
  derived views from the MD (data)
- :func:`normalize_categoria`, :func:`normalize_dimension`,
  :func:`validate_codigo`, :func:`map_gravedad`,
  :func:`validate_clasificaciones` — validation/normalization of LLM
  output (deterministic)
- :func:`render_tabla_canonica_prompt`,
  :func:`render_severidad_prompt` — prompt builders (rendered from the
  loaded data)
- :func:`load_prompt_block` — load rule blocks from the markdown
  glossary under :data:`KNOWLEDGE_ROOT`.

Display-only data (UI labels, color hexes) was previously in
``src/ui/utils.py`` and ``src/ui/nicegui_app/theme.py``, but is now
centralized in ``src.ui.labels`` (which reads from the taxonomy's
``label`` field and optionally from the ``category_display`` table in
SQLite).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from src.analyzer.taxonomy_loader import (
    DEFAULT_TAXONOMY_PATH,
    Taxonomy,
    get_taxonomy,
    reload_taxonomy,
)
from src.analyzer.violence_types import Severity

if TYPE_CHECKING:
    from src.analyzer.rag_classifier import LabelAssignment

logger = logging.getLogger(__name__)


# Root of the knowledge-base directory (for the rule glossaries under
# glosario/). Resolved relative to this file so the loader doesn't
# depend on CWD.
KNOWLEDGE_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge"
    / "categorias-violencia-genero-digital"
)


#: Hard cap on the number of labels the LLM may emit per content. The
#: order in which labels are returned determines which are kept when
#: the LLM overshoots.
MAX_LABELS: int = 5


class Categoria(StrEnum):
    """Canonical alphabetic codes for the 6 categories of digital gender violence.

    These are the **closure** codes the LLM must respect. They live in
    code (not the MD) because Python's enum machinery gives them stable
    ``.name``/``.value`` that the rest of the codebase imports. The MD
    must declare the same set of codes; an alignment check runs at
    import time via :func:`_build_taxonomy_views`.
    """

    VDG_VIOLENCIA_SIMBOLICA = "VDG_VIOLENCIA_SIMBOLICA"
    VDG_COSIFICACION_SLUTSHAMING = "VDG_COSIFICACION_SLUTSHAMING"
    VDG_HOSTILIDAD_FEMINICIDIO = "VDG_HOSTILIDAD_FEMINICIDIO"
    VDG_MANOSFERA_ANTIFEMINISMO = "VDG_MANOSFERA_ANTIFEMINISMO"
    VDG_SALVAGUARDA_FALSO_POSITIVO = "VDG_SALVAGUARDA_FALSO_POSITIVO"
    VDG_DESACREDITACION_ACTIVISTAS = "VDG_DESACREDITACION_ACTIVISTAS"
    NINGUNA = "ninguna"


# Categories that have a real taxonomy identity (excludes 'ninguna').
# Used to verify MD/enum alignment.
_TAXONOMY_CATEGORIAS: set[str] = {c.value for c in Categoria if c is not Categoria.NINGUNA}


def _build_taxonomy_views() -> tuple[
    list[str],
    dict[str, list[str]],
    dict[str, str],
    dict[str, str],
    list[str],
    dict[str, str],
]:
    """Build derived views from the MD taxonomy.

    Validates that the MD's category codes match :class:`Categoria`'s
    closure set. Returns six structures used across the codebase:

    - ``CATEGORIAS_ORDENADAS``
    - ``SUBDIMENSIONES_POR_CATEGORIA``
    - ``DESCRIPCION_SUBDIMENSION``
    - ``GRAVEDAD_POR_CATEGORIA``
    - ``SUBDIMENSIONES_ORDENADAS``
    - ``CATEGORIA_POR_SUBDIMENSION``
    """
    tx: Taxonomy = get_taxonomy()
    md_codes = set(tx.ordered_codes())
    if md_codes != _TAXONOMY_CATEGORIAS:
        missing_in_md = _TAXONOMY_CATEGORIAS - md_codes
        extra_in_md = md_codes - _TAXONOMY_CATEGORIAS
        raise RuntimeError(
            "TAXONOMIA.md categories do not match Categoria enum. "
            f"Missing in MD: {sorted(missing_in_md) or '∅'}; "
            f"Extra in MD: {sorted(extra_in_md) or '∅'}. "
            f"Either update {DEFAULT_TAXONOMY_PATH} or extend the Categoria enum."
        )
    return (
        tx.ordered_codes(),
        tx.subdims_by_category(),
        tx.descripcion_subdim(),
        tx.gravedad_por_categoria(),
        tx.ordered_subdimensions(),
        tx.categoria_por_subdimension(),
    )


(
    CATEGORIAS_ORDENADAS,
    SUBDIMENSIONES_POR_CATEGORIA,
    DESCRIPCION_SUBDIMENSION,
    GRAVEDAD_POR_CATEGORIA,
    SUBDIMENSIONES_ORDENADAS,
    CATEGORIA_POR_SUBDIMENSION,
) = _build_taxonomy_views()


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

    # SPECIAL CASE: VIOLENCIA_COMUN is a valid exclusion label, not a violence category
    if raw.upper() == "VIOLENCIA_COMUN":
        return "VIOLENCIA_COMUN"

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

    R5 (docs/recomendaciones-subdimensiones-2026-07-14.md): when the
    category is ``VDG_SALVAGUARDA_FALSO_POSITIVO`` and the LLM emits
    no valid sub-dim, fall back to ``"6.3"`` (salvaguarda / falsos
    positivos). This closes the "SAFEGUARD sin subdim" gap.
    """
    if dimension is None:
        if categoria == Categoria.VDG_SALVAGUARDA_FALSO_POSITIVO.value:
            logger.warning("SAFEGUARD sin sub-dim — aplicando default 6.3")
            return "6.3"
        return None
    raw = str(dimension).strip()
    if not raw or raw.lower() in {"null", "none", "ninguna"}:
        if categoria == Categoria.VDG_SALVAGUARDA_FALSO_POSITIVO.value:
            logger.warning("SAFEGUARD sin sub-dim — aplicando default 6.3")
            return "6.3"
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


def _severity_rank(sev: Severity) -> int:
    """Numeric rank for sorting severities (alta=3, media=2, baja=1, ninguna=0)."""
    order = {
        Severity.NINGUNA: 0,
        Severity.BAJA: 1,
        Severity.MEDIA: 2,
        Severity.ALTA: 3,
    }
    return order.get(sev, 0)


def max_severity(values: list[Severity]) -> Severity:
    """Return the highest ``Severity`` in ``values`` (empty ⇒ ``NINGUNA``)."""
    if not values:
        return Severity.NINGUNA
    return max(values, key=_severity_rank)


_PRIMARY_LABEL_DEFAULTS: dict[str, object] = {
    "categoria": "ninguna",
    "dimension": None,
    "severidad": "ninguna",
    "justificacion": "",
    "evidencia": "",
    "regla_disparada": None,
    "marcadores_detectados": None,
    "confianza": None,
    "score_ajuste": None,
    "es_falso_positivo_probable": "false",
}


def primary_label(labels: list[dict]) -> dict[str, object]:
    """Return the primary label dict (highest severity; ties keep order).

    Used to mirror a multi-label ``analysis_labels`` row into the flat
    ``analysis_results`` columns (``categoria``/``dimension``/
    ``justificacion``/etc.). Empty input returns neutral defaults so
    callers can ``.get(...)`` safely.

    Severity ranking (descending): ``alta`` > ``media`` > ``baja`` >
    ``ninguna``. Unknown values fall back to ``ninguna``.
    """
    if not labels:
        return dict(_PRIMARY_LABEL_DEFAULTS)

    rank = {"alta": 3, "media": 2, "baja": 1, "ninguna": 0}

    def _rank(label: dict) -> int:
        sev = str(label.get("severidad") or "ninguna").lower()
        return rank.get(sev, 0)

    chosen = max(labels, key=lambda lbl: (_rank(lbl), 1))
    return {
        "categoria": chosen.get("categoria") or "ninguna",
        "dimension": chosen.get("dimension"),
        "severidad": chosen.get("severidad") or "ninguna",
        "justificacion": chosen.get("justificacion") or "",
        "evidencia": chosen.get("evidencia") or "",
        "regla_disparada": chosen.get("regla_disparada"),
        "marcadores_detectados": chosen.get("marcadores_detectados"),
        "confianza": chosen.get("confianza"),
        "score_ajuste": chosen.get("score_ajuste"),
        "es_falso_positivo_probable": (
            "true" if _coerce_bool(chosen.get("es_falso_positivo_probable")) else "false"
        ),
    }


def _coerce_float(value: object) -> float | None:
    """Best-effort float coercion for confidence/score fields."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            return None
    return None


def _coerce_bool(value: object) -> bool:
    """Best-effort bool coercion for the false-positive flag."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "si", "sí"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _coerce_marcadores(value: object) -> list[str]:
    """Normalize ``marcadores_detectados`` from list / csv string / other."""
    if isinstance(value, list):
        return [str(m) for m in value if m]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        # Try JSON first
        try:
            import json

            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(m) for m in parsed if m]
        except (ValueError, TypeError):
            pass
        return [m.strip() for m in stripped.split(",") if m.strip()]
    return []


def validate_clasificaciones(
    data: object,
    max_labels: int = MAX_LABELS,
) -> list[LabelAssignment]:
    """Validate and normalize the ``clasificaciones`` array from the LLM.

    The input is expected to be a list of objects with at least
    ``categoria`` and ``dimension`` keys. Behavior:

    - Non-list input → empty list (with a warning).
    - Drops entries with category outside the canonical set or with
      ``dimension`` not allowed for that category.
    - Deduplicates by ``(categoria, dimension)`` (first occurrence wins).
      Two entries with the same ``(cat, dim)`` but **independent
      ``marcadores_detectados``** (R4 from
      ``docs/recomendaciones-subdimensiones-2026-07-14.md``) are
      preserved as separate rows so the audit can trace multi-marker
      hits (e.g. ``aliade`` + ``f3m1 nizta`` → 4.3 × 2).
    - Caps the result at ``max_labels`` entries. Truncation is by
      **severidad descending** (R3 of the plan) so high-severity labels
      survive when the LLM emits more than ``MAX_LABELS``.
    - Returns labels sorted by severity desc, ties broken by input
      order.
    """
    from src.analyzer.rag_classifier import LabelAssignment

    if not isinstance(data, list):
        if data not in (None, [], {}):
            logger.warning(
                "LLM devolvió 'clasificaciones' no-lista (%s) — descartando",
                type(data).__name__,
            )
        return []

    out: list[LabelAssignment] = []
    for raw in data:
        if not isinstance(raw, dict):
            logger.warning(
                "Elemento de 'clasificaciones' no es objeto (%s) — descartando",
                type(raw).__name__,
            )
            continue

        cat, dim = validate_codigo(raw.get("categoria"), raw.get("dimension"))
        if cat == Categoria.NINGUNA.value:
            continue

        marcadores = _coerce_marcadores(raw.get("marcadores_detectados"))
        # R4: dedupe by (cat, dim, sorted(marcadores)) so two
        # independent matches with the same (cat, dim) but different
        # markers coexist (e.g. aliade + f3m1 nizta → 4.3 × 2).
        dedupe_key = (cat, dim, tuple(sorted(marcadores)))
        # We dedupe later (after sort) to keep the original insertion
        # order for ties; just append here.

        out.append(
            LabelAssignment(
                categoria=cat,
                dimension=dim,
                justificacion=str(raw.get("justificacion") or "").strip(),
                evidencia=str(raw.get("evidencia") or "").strip(),
                regla_disparada=(
                    str(raw["regla_disparada"]).strip()
                    if raw.get("regla_disparada") is not None
                    else None
                ),
                marcadores_detectados=marcadores,
                confianza=_coerce_float(raw.get("confianza")),
                score_ajuste=_coerce_float(raw.get("score_ajuste")),
                es_falso_positivo_probable=_coerce_bool(
                    raw.get("es_falso_positivo_probable", False)
                ),
                severidad=map_gravedad(raw.get("severidad")),
            )
        )
        _ = dedupe_key  # silence unused; keep for documentation

    # Dedupe by (cat, dim, sorted(marcadores)) keeping the highest
    # severity per key (and the first occurrence on ties).
    deduped: dict[tuple[str, str | None, tuple[str, ...]], LabelAssignment] = {}
    for label in out:
        key = (label.categoria, label.dimension, tuple(sorted(label.marcadores_detectados)))
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = label
            continue
        if _severity_rank(label.severidad) > _severity_rank(existing.severidad):
            deduped[key] = label

    deduped_list = list(deduped.values())

    # Truncate by severity desc, ties broken by input order. The
    # ``-idx`` trick preserves the original LLM order on ties.
    indexed = list(enumerate(deduped_list))
    indexed.sort(
        key=lambda pair: (-_severity_rank(pair[1].severidad), pair[0]),
    )
    if len(indexed) > max_labels:
        dropped = indexed[max_labels:]
        dropped_summary = [
            (lbl.categoria, lbl.dimension, lbl.severidad.value) for _, lbl in dropped
        ]
        logger.debug(
            "validate_clasificaciones: LLM devolvio %d etiquetas tras dedupe; "
            "recortando a top-%d por severidad. Perdidas: %s",
            len(indexed),
            max_labels,
            dropped_summary,
        )
        indexed = indexed[:max_labels]

    return [lbl for _, lbl in indexed]


# ---------------------------------------------------------------------------
# Loader genérico de bloques desde markdown
# ---------------------------------------------------------------------------
#
# Las reglas (marcadores, leetspeak, mitigadores, referentes femeninos)
# viven en archivos ``.md`` bajo ``glosario/``. Esta función carga
# una sección específica del markdown y la devuelve como string para
# que ``rag_classifier._build_prompt`` la inyecte verbatim en el
# prompt del LLM.
#
# Contrato del markdown:
#   - El archivo tiene UN solo bloque ``## Bloque para prompt``
#     con el contenido textual que se inyecta al prompt.
#   - El resto del markdown es prosa/documentación/explicación —
#     no se inyecta al prompt.

_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@lru_cache(maxsize=16)
def load_prompt_block(relpath: str, anchor: str = "Bloque para prompt") -> str:
    """Return the markdown content between ``## {anchor}`` and the next ``##`` heading.

    Args:
        relpath: Path relative to :data:`KNOWLEDGE_ROOT`.
        anchor: Heading text (without ``##``). Defaults to
            ``"Bloque para prompt"`` — the contract name used by the
            four rule-markdowns in ``glosario/``.

    Returns:
        The trimmed body of the section, verbatim. Empty string if
        the file or anchor is missing (with a warning logged once per
        session via lru_cache).

    The result is ``lru_cache``-d — repeated calls during a batch run
    are O(1).
    """
    path = KNOWLEDGE_ROOT / relpath
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "load_prompt_block: no se pudo leer %s — devolviendo '': %s",
            path,
            exc,
        )
        return ""

    lines = text.splitlines()
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == f"## {anchor}":
            start_idx = i + 1
            break

    if start_idx is None:
        logger.warning(
            "load_prompt_block: anchor %r no encontrado en %s",
            anchor,
            path,
        )
        return ""

    end_idx = len(lines)
    for j in range(start_idx, len(lines)):
        if lines[j].strip().startswith("## "):
            end_idx = j
            break

    body = "\n".join(lines[start_idx:end_idx]).strip()
    return body


# ---------------------------------------------------------------------------
# Renderers que viven en código (taxonomía cerrada + escala de severidad)
# ---------------------------------------------------------------------------
#
# Estos renderers NO son reglas — son el **contrato cerrado** que el
# LLM debe respetar. Por eso viven en código, no en markdown.


def render_tabla_canonica_prompt() -> str:
    """Render the compact 19-row canonical table to inject into the prompt.

    The table is the single source of truth the LLM sees for valid
    categoria/dimension combinations. Built 100 % from the MD-loaded
    taxonomy (via :data:`SUBDIMENSIONES_POR_CATEGORIA` /
    :data:`DESCRIPCION_SUBDIMENSION`).
    """
    lines = [
        "CATEGORÍAS VÁLIDAS (elegí HASTA "
        + str(MAX_LABELS)
        + " filas — una por cada categoría que aplique; usá 'ninguna' SOLO en la lista vacía):",
        "",
        "| categoria | dimension | descripcion |",
        "|---|---|---|",
    ]
    for cat in CATEGORIAS_ORDENADAS:
        dims = SUBDIMENSIONES_POR_CATEGORIA[cat]
        for i, d in enumerate(dims):
            cat_cell = cat if i == 0 else ""
            desc = DESCRIPCION_SUBDIMENSION.get(d, "")
            lines.append(f"| {cat_cell:<34} | {d:<9} | {desc} |")
    lines.append("")
    lines.append(
        "Si el texto no encaja en ninguna categoría: devolve `clasificaciones: []` "
        "y `tiene_violencia: false`."
    )
    return "\n".join(lines)


def render_severidad_prompt() -> str:
    """Render the severity scale legend for the prompt."""
    return (
        "ESCALA DE SEVERIDAD (fija, por etiqueta):\n"
        '- "baja"     → violencia implícita, estereotipos, micromachismos\n'
        '- "media"    → insultos, cosificación, deslegitimación\n'
        '- "alta"     → amenazas, hostilidad letal, acoso coordinado\n'
        '- "ninguna"  → sin violencia detectada (o caso ortogonal)'
    )


__all__ = [
    "Categoria",
    "MAX_LABELS",
    "SUBDIMENSIONES_POR_CATEGORIA",
    "DESCRIPCION_SUBDIMENSION",
    "GRAVEDAD_POR_CATEGORIA",
    "CATEGORIAS_ORDENADAS",
    "SUBDIMENSIONES_ORDENADAS",
    "CATEGORIA_POR_SUBDIMENSION",
    "KNOWLEDGE_ROOT",
    "normalize_categoria",
    "normalize_dimension",
    "validate_codigo",
    "map_gravedad",
    "max_severity",
    "validate_clasificaciones",
    "load_prompt_block",
    "render_tabla_canonica_prompt",
    "render_severidad_prompt",
    # Re-export from the loader for convenience
    "reload_taxonomy",
    "get_taxonomy",
]
