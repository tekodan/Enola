"""Pre-classification exclusion filter.

Implements the documentation ``INSTRUCCIÓN DE SISTEMA: FILTRO DE EXCLUSIÓN
PREVIA (BASURA DIGITAL Y VALORES PERDIDOS)`` and the ``REGLA DE EXCLUSIÓN:
FILTRO DE DISCRIMINACIÓN DE VIOLENCIA COMÚN (SIN SESGO DE GÉNERO)``.

The filter runs **before** the LLM (and before the rule-based fallback) to:

1. **Detectar CÓDIGO 99 — Basura digital**: empty/NaN text, orphan links
   (URLs with no other alphanumeric words), pure typographic noise
   (only punctuation/emojis/repeated chars, no lexical structure),
   laughs (jajaja/jeje/haha/rsrs/lol/xd) and very short reactions /
   interjections (ok/si/no/ya/dale/je/ah).
2. **Detectar Violencia Común / sin sesgo de género**: input that is
   aggressive but carries no gender markers — political insults, sports
   rants, customer complaints, etc. These are tagged with
   ``exclusion_label = "VIOLENCIA_COMUN"`` and excluded from the
   violence-incidence calculation while still being persisted.

The detector is deterministic (regex + lexical analysis) so it is safe
to run outside of Ollama. Heuristic-only — the LLM provides the more
nuanced judgement during prompt execution.
"""

from __future__ import annotations

import logging
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


AGRESIONES_MARKDOWN = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge"
    / "categorias-violencia-genero-digital"
    / "glosario"
    / "agresiones-comunes.md"
)

MARCADORES_DE_GENERO_MARKDOWN = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge"
    / "categorias-violencia-genero-digital"
    / "glosario"
    / "marcadores-de-genero.md"
)

PATRONES_BASURA_DIGITAL_MARKDOWN = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge"
    / "categorias-violencia-genero-digital"
    / "glosario"
    / "patrones-basura-digital.md"
)


# Sentinel labels stored in ``analysis_results.exclusion_label``.
EXCLUSION_BASURA_DIGITAL = "CODIGO_99"
EXCLUSION_VIOLENCIA_COMUN = "VIOLENCIA_COMUN"

EXCLUSION_LABELS: tuple[str, ...] = (
    EXCLUSION_BASURA_DIGITAL,
    EXCLUSION_VIOLENCIA_COMUN,
)

# Whole-URL regex (used by Condición 2 to strip the entire URL from
# the text before checking what remains).
_FULL_URL = re.compile(
    r"https?://[^\s]+|www\.[^\s]+|t\.co/[^\s]+",
    re.IGNORECASE,
)

# URL hostname markers per the spec — used only to detect the *presence*
# of a URL.
_URL_HOST_PATTERN = re.compile(
    r"(https?://|www\.|t\.co/)",
    re.IGNORECASE,
)

# A "word" is a run of 2+ letters (latin/Spanish incl. accents). Used
# to decide whether an entry has lexical structure.
_LEXICAL_WORD = re.compile(r"\b[A-Za-zÁÉÍÓÚáéíóúÑñÜü]{2,}\b")


_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def _read_glosario_tokens(
    markdown_path: Path,
    warning_label: str,
) -> frozenset[str]:
    """Read a fenced ``plain`` block from ``markdown_path`` and return its
    tokens as a frozenset.

    Shared implementation for ``_load_aggression_keywords`` and
    ``_load_gender_markers``. Both glosario markdowns share the
    contract: a single ``plain`` fenced block with one canonical
    token per line. To add or remove tokens, edit the glosario file
    — do not hardcode them in this module.
    """
    try:
        text = markdown_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "No se pudo leer %s (%s) — usando fallback vacío: %s",
            markdown_path,
            warning_label,
            exc,
        )
        return frozenset()

    fence = _FENCE_RE.search(text)
    if not fence:
        logger.warning(
            "Glosario %s (%s) no contiene bloque fenced — usando fallback vacío",
            markdown_path,
            warning_label,
        )
        return frozenset()

    tokens: set[str] = set()
    for line in fence.group(1).splitlines():
        cleaned = line.strip().strip("`").strip().lower()
        if not cleaned or cleaned.startswith("#"):
            continue
        if cleaned in tokens:
            continue
        tokens.add(unicodedata.normalize("NFC", cleaned))
    return frozenset(tokens)


@lru_cache(maxsize=1)
def _load_aggression_keywords() -> frozenset[str]:
    """Read the aggression-words list from the glosario markdown.

    Source of truth:
    ``knowledge/categorias-violencia-genero-digital/glosario/agresiones-comunes.md``.
    """
    return _read_glosario_tokens(
        AGRESIONES_MARKDOWN,
        warning_label="agresiones-comunes",
    )


@lru_cache(maxsize=1)
def _load_gender_markers() -> frozenset[str]:
    """Read the gender-markers list from the glosario markdown.

    Source of truth:
    ``knowledge/categorias-violencia-genero-digital/glosario/marcadores-de-genero.md``.

    The markdown contains a single ``plain`` fenced block whose lines
    are the canonical tokens, one per row. Mirrors the structure of
    ``agresiones-comunes.md`` so the same parser can consume both.
    """
    return _read_glosario_tokens(
        MARCADORES_DE_GENERO_MARKDOWN,
        warning_label="marcadores-de-genero",
    )


# Patterns for "muy corto" / "riese puro" detection (COND_4 and COND_5).
# Loaded from ``patrones-basura-digital.md`` (mirrors the design of
# ``_load_gender_markers`` and ``_load_aggression_keywords``): a fenced
# ``plain`` block with one regex pattern per line. Lines starting with
# ``#`` or empty are ignored. Patterns are matched against the input
# text via ``re.fullmatch`` after normalization (see
# :func:`_matches_basura_pattern`).
_COMMENT_LINE = re.compile(r"^\s*#")


def _read_basura_digital_patterns(
    markdown_path: Path,
) -> tuple[str, ...]:
    """Return the regex patterns declared in ``markdown_path``.

    Each non-comment, non-empty line inside the fenced ``plain`` block
    is treated as a complete regex pattern. The list is cached via
    :func:`_load_basura_digital_patterns`.
    """
    try:
        text = markdown_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "No se pudo leer %s — usando fallback vacío: %s",
            markdown_path,
            exc,
        )
        return ()

    fence = _FENCE_RE.search(text)
    if not fence:
        logger.warning(
            "Patrones basura digital: %s no contiene bloque fenced — fallback vacío",
            markdown_path,
        )
        return ()

    patterns: list[str] = []
    for line in fence.group(1).splitlines():
        cleaned = line.strip()
        if not cleaned or _COMMENT_LINE.match(cleaned):
            continue
        patterns.append(cleaned)
    return tuple(patterns)


@lru_cache(maxsize=1)
def _load_basura_digital_patterns() -> tuple[str, ...]:
    """Return the canonical regex patterns for basura digital.

    Source of truth:
    ``knowledge/categorias-violencia-genero-digital/glosario/patrones-basura-digital.md``.

    The fenced ``plain`` block lists one regex per line. Each pattern
    is matched against the normalized input via
    :func:`_matches_basura_pattern` — invalid regexes are skipped with a
    warning at first call. Use :func:`reset_basura_patterns_cache` in
    tests after editing the file.
    """
    raw_patterns = _read_basura_digital_patterns(PATRONES_BASURA_DIGITAL_MARKDOWN)

    valid: list[str] = []
    for pat in raw_patterns:
        try:
            re.compile(pat)
        except re.error as exc:
            logger.warning(
                "Patrón basura digital inválido %r — descartado: %s",
                pat,
                exc,
            )
            continue
        valid.append(pat)
    return tuple(valid)


def reset_basura_patterns_cache() -> None:
    """Drop the cached patterns (test helper)."""
    _load_basura_digital_patterns.cache_clear()


# Strong aggression markers (groserías/profanities). When present in
# isolation without any GENDER_MARKERS, the input is treated as generic
# violence rather than gender violence.
#
# As of 2026-07-12 the canonical list is owned by
# ``knowledge/categorias-violencia-genero-digital/glosario/agresiones-comunes.md``.
# This module reads it once (lru_cache) and keeps the frozenset for O(1)
# membership tests. To add or remove words, edit the glosario — do not
# hardcode them here.
_AGGRESSION_KEYWORDS = _load_aggression_keywords()


# Gender markers that signal male-supremacist communities AND gendered
# attack patterns. The list is owned by
# ``knowledge/categorias-violencia-genero-digital/glosario/marcadores-de-genero.md``
# and loaded once via ``_load_gender_markers`` (lru_cache). To add or
# remove words, edit the glosario — do not hardcode them here.
#
# Updated 2026-07-12 — closing the last pass of the
# "reglas-en-codigo → reglas-en-markdown" refactor. The list was
# directly hardcoded as ``_GENDER_MARKERS = frozenset(...)`` (28
# tokens) before this change.
_GENDER_MARKERS = _load_gender_markers()


@dataclass(frozen=True)
class ExclusionResult:
    """Result of the pre-filter evaluation.

    When ``etiqueta`` is ``None``, the text passed the filter and normal
    classification should proceed. Otherwise the matching exclusion
    sentinel (or "CODIGO_99" / "VIOLENCIA_COMUN") should be persisted
    in ``analysis_results.exclusion_label`` and the LLM/rule-based
    classifiers should be bypassed.
    """

    etiqueta: str | None
    codigo: str | None
    justificacion: str

    @property
    def excluded(self) -> bool:
        return self.etiqueta is not None


def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _strip_emojis_and_punctuation(s: str) -> str:
    """Return only the letters-and-spaces skeleton of ``s``.

    Drops Unicode marks, separator characters (emojis are categorised
    under 'So'/'Sk' generally) and any non-alphanumeric byte.
    Useful for the typographic-noise check.
    """
    out: list[str] = []
    for ch in s:
        if ch.isspace():
            out.append(" ")
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            out.append(ch)
        elif cat in {"Nd", "No"}:
            out.append(ch)
    return "".join(out).strip()


def _has_only_url_payload(text: str) -> bool:
    """Return ``True`` when ``text`` contains a URL and has no other
    legible alphabetic word (orphan hyperlink per the spec).
    """
    if not _URL_HOST_PATTERN.search(text):
        return False
    no_url = _FULL_URL.sub(" ", text)
    return not _LEXICAL_WORD.search(no_url)


def _has_lexical_structure(text: str) -> bool:
    """Return ``True`` when ``text`` contains at least one legible word.

    A "legible word" is a run of 2+ distinct alphabetic characters
    (latin/Spanish incl. accents). A single repeated character
    (``"aaaaaaaaa"``) does NOT count.
    """
    match = _LEXICAL_WORD.search(text)
    if not match:
        return False
    token = match.group(0)
    return len(set(token.lower())) >= 2


def _is_repeated_char_payload(text: str) -> bool:
    """``True`` when ``text`` is composed of a single repeated character."""
    skeleton = text.strip()
    if len(skeleton) < 3:
        return False
    return len(set(skeleton.replace(" ", ""))) == 1


# Tagging categories for the regex patterns. Each pattern in
# ``patrones-basura-digital.md`` may carry a category keyword after the
# raw pattern (separated by ``#``), so the detector can emit the
# correct ``condigo`` for the exclusion_label
# (``COND_4_SOLO_RISA`` vs ``COND_5_REACCION_CORTA``).
#
# Backwards compat: patterns that don't carry a category keyword are
# treated as :data:`_RISA_TAG` (the old default before COND_5 was
# introduced).
_RISA_TAG = "COND_4_SOLO_RISA"
_REACCION_TAG = "COND_5_REACCION_CORTA"


def _normalize_for_pattern_match(text: str) -> str:
    """Normalize ``text`` for ``_matches_basura_pattern``.

    Returns lowercase, accent-stripped, left/right-stripped. Internal
    whitespace is collapsed to a single space.
    """
    norm = _strip_accents(text.lower())
    return " ".join(norm.split())


def _classify_basura_pattern(pattern: str) -> tuple[str, str]:
    """Split ``pattern`` into ``(regex_str, condigo_tag)``.

    Recognises the inline ``# COND_5_REACCION_CORTA`` (or
    ``# COND_4_SOLO_RISA``) suffix. The tag defaults to
    :data:`_RISA_TAG` for back-compat with the original single-bucket
    design.
    """
    raw = pattern.strip()
    if "#" in raw:
        regex_str, _, tag = raw.partition("#")
        regex_str = regex_str.strip()
        tag = tag.strip()
        if tag not in {_RISA_TAG, _REACCION_TAG}:
            logger.warning(
                "Patrón basura digital con tag desconocido %r — usando default",
                tag,
            )
            tag = _RISA_TAG
        return regex_str, tag
    return raw, _RISA_TAG


def _matches_basura_pattern(text: str) -> ExclusionResult | None:
    """Return an exclusion if ``text`` matches a cached basura pattern.

    The input is normalized via :func:`_normalize_for_pattern_match`
    (lowercase, accent-stripped, single-spaced) before being matched
    against each compiled regex with :func:`re.fullmatch` (whole-string
    anchor). Returns ``None`` when no pattern matches.

    Two condigos are emitted based on the inline tag:

    - ``COND_4_SOLO_RISA`` — pure laughter (jajaja/jeje/haha/rsrs/lol/…)
    - ``COND_5_REACCION_CORTA`` — short one-/two-char reactions
      (ok/si/no/ya/dale/je/ah)

    Both map to the same exclusion_label ``CODIGO_99``; the ``codigo``
    field is preserved for traceability in the missing-values report.
    """
    norm = _normalize_for_pattern_match(text)
    if not norm:
        return None
    for raw_pattern in _load_basura_digital_patterns():
        regex_str, tag = _classify_basura_pattern(raw_pattern)
        try:
            compiled = re.compile(regex_str)
        except re.error:
            continue
        if compiled.fullmatch(norm):
            if tag == _RISA_TAG:
                msg = "Basura digital: risa o expresión onomatopéyica sin contenido clasificable."
            else:
                msg = "Basura digital: reacción o muletilla corta sin contenido clasificable."
            return ExclusionResult(
                etiqueta=EXCLUSION_BASURA_DIGITAL,
                codigo=tag,
                justificacion=msg,
            )
    return None


def detectar_basura_digital(text: object) -> ExclusionResult:
    """Return an ``ExclusionResult`` with ``CODIGO_99`` if ``text`` is
    digital garbage, otherwise an empty result.

    Implements the five algorithmic conditions from the spec:

    * **Condición 1**: missing/empty/NaN payload.
    * **Condición 2**: orphan hyperlink (only a URL, no other word).
    * **Condición 3**: pure typographic noise (punctuation / emojis,
      no lexical words).
    * **Condición 4**: pure laughter (jajaja/jeje/haha/rsrs/lol/xd).
    * **Condición 5**: short one-/two-char reactions or interjections
      (ok/si/no/ya/dale/je/ah).

    Patterns for COND_4/COND_5 are loaded from
    ``glosario/patrones-basura-digital.md``; if the glosario is
    missing, the two conditions fall back to a silent no-op (the rest
    of the filter keeps working).
    """
    if text is None:
        return ExclusionResult(
            etiqueta=EXCLUSION_BASURA_DIGITAL,
            codigo="COND_1_NA",
            justificacion="Valor perdido: entrada nula.",
        )
    if isinstance(text, float):
        if math.isnan(text):
            return ExclusionResult(
                etiqueta=EXCLUSION_BASURA_DIGITAL,
                codigo="COND_1_NAN",
                justificacion="Valor perdido: NaN.",
            )
        text = str(text)
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return ExclusionResult(
                etiqueta=EXCLUSION_BASURA_DIGITAL,
                codigo="COND_1_NOTEXT",
                justificacion="Valor perdido: payload no convertible a texto.",
            )

    if not text.strip():
        return ExclusionResult(
            etiqueta=EXCLUSION_BASURA_DIGITAL,
            codigo="COND_1_VACIO",
            justificacion="Basura digital: mensaje vacío (sticker, GIF o imagen sin texto).",
        )

    if _is_repeated_char_payload(text):
        return ExclusionResult(
            etiqueta=EXCLUSION_BASURA_DIGITAL,
            codigo="COND_3_RUIDO_TIPOGRAFICO",
            justificacion=("Basura digital: caracteres repetidos sin sentido léxico."),
        )

    if _has_only_url_payload(text):
        return ExclusionResult(
            etiqueta=EXCLUSION_BASURA_DIGITAL,
            codigo="COND_2_ENLACE_HUERFANO",
            justificacion=(
                "Basura digital: enlace huérfano (URL sin contenido textual adicional)."
            ),
        )

    text_skeleton = _strip_emojis_and_punctuation(text)
    if not _has_lexical_structure(text_skeleton):
        return ExclusionResult(
            etiqueta=EXCLUSION_BASURA_DIGITAL,
            codigo="COND_3_RUIDO_TIPOGRAFICO",
            justificacion=("Basura digital: ruido tipográfico o emojis sin estructura léxica."),
        )

    pattern_match = _matches_basura_pattern(text)
    if pattern_match is not None:
        return pattern_match

    return ExclusionResult(etiqueta=None, codigo=None, justificacion="")


def detectar_violencia_comun_heuristica(text: str) -> ExclusionResult:
    """Rule-based heuristic for the gender-bias discrimination step.

    Returns an exclusion with ``VIOLENCIA_COMUN`` when the input is
    clearly aggressive but does **not** carry any gender marker. The
    primary responsibility for this judgement belongs to the LLM, but
    the heuristic gives the rule-based fallback path a deterministic
    counterpart.
    """
    if not isinstance(text, str) or not text.strip():
        return ExclusionResult(etiqueta=None, codigo=None, justificacion="")

    norm = _strip_accents(text.lower())

    has_gender_marker = any(marker in norm for marker in _GENDER_MARKERS)
    if has_gender_marker:
        return ExclusionResult(etiqueta=None, codigo=None, justificacion="")

    has_aggression = any(kw in norm for kw in _AGGRESSION_KEYWORDS)
    if not has_aggression:
        return ExclusionResult(etiqueta=None, codigo=None, justificacion="")

    return ExclusionResult(
        etiqueta=EXCLUSION_VIOLENCIA_COMUN,
        codigo="VIOLENCIA_COMUN_HEURISTICA",
        justificacion=(
            "Violencia común / sin sesgo de género: la agresividad detectada "
            "no ataca a la víctima por su condición de mujer y carece de "
            "marcadores de las seis dimensiones de ciberviolencia."
        ),
    )


def evaluar_exclusiones(text: object) -> ExclusionResult:
    """Run the pre-filter on ``text`` and return the basura digital match.

    The violencia-común discrimination is intentionally NOT executed
    here. The ``Regla de exclusión`` (FILTRO DE DISCRIMINACIÓN DE
    VIOLENCIA COMÚN) is primarily an LLM judgement — the prompt tells
    the model to mark hostile but ungendered inputs with
    ``exclusion_label = "VIOLENCIA_COMUN"``. The heuristic for the
    rule-based fallback (when no LLM is available) lives in
    :func:`detectar_violencia_comun_heuristica` and is invoked by the
    fallback path, not by the LLM classifier.

    Returning a benign result here means "let the LLM see this text".
    """
    return detectar_basura_digital(text)
