"""Pre-classification exclusion filter.

Implements the documentation ``INSTRUCCIÓN DE SISTEMA: FILTRO DE EXCLUSIÓN
PREVIA (BASURA DIGITAL Y VALORES PERDIDOS)`` and the ``REGLA DE EXCLUSIÓN:
FILTRO DE DISCRIMINACIÓN DE VIOLENCIA COMÚN (SIN SESGO DE GÉNERO)``.

The filter runs **before** the LLM (and before the rule-based fallback) to:

1. **Detectar CÓDIGO 99 — Basura digital**: empty/NaN text, orphan links
   (URLs with no other alphanumeric words), pure typographic noise
   (only punctuation/emojis/repeated chars, no lexical structure).
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

logger = logging.getLogger(__name__)


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


# Baseline hostname-only / slang markers that signal male-supremacist
# communities AND gendered attack patterns. Used by the rule-based
# violence-common detector.
_GENDER_MARKERS = frozenset(
    (
        # manosfera / manosphere
        "feminazi",
        "foid",
        "femoid",
        "mangina",
        "incel",
        "mgtow",
        "redpill",
        "red pill",
        "pastilla roja",
        "hembrista",
        # attack on the body / sexuality
        "zorra",
        "puta",
        "perra",
        "guarra",
        "cosificar",
        # threats
        "matar",
        "violar",
        "violacion",
        "violación",
        "femicidio",
        # stereotypes / mandates
        "mujeres de cocina",
        "solo sirven",
        "para eso estas",
        "para eso estás",
    )
)

# Strong aggression markers (groserías/profanities). When present in
# isolation without any GENDER_MARKERS, the input is treated as generic
# violence rather than gender violence.
_AGGRESSION_KEYWORDS = frozenset(
    (
        "idiota",
        "imbecil",
        "imbécil",
        "estupido",
        "estúpido",
        "mierda",
        "carajo",
        "joder",
        "maldito",
        "maldita",
        "basura",
        "inutil",
        "inútil",
        "huevon",
        "huevón",
        "boludo",
        "pelotudo",
        "forro",
        "giles",
        "gil",
        "de mierda",
        "ctm",
        "ptm",
        "hdp",
        "hijueputa",
        "hp",
    )
)


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


def detectar_basura_digital(text: object) -> ExclusionResult:
    """Return an ``ExclusionResult`` with ``CODIGO_99`` if ``text`` is
    digital garbage, otherwise an empty result.

    Implements the three algorithmic conditions from the spec:

    * **Condición 1**: missing/empty/NaN payload.
    * **Condición 2**: orphan hyperlink (only a URL, no other word).
    * **Condición 3**: pure typographic noise (punctuation / emojis,
      no lexical words).
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
    ``exclusion_label = "VIOLENCIA_COMUN"``. A small heuristic for the
    rule-based fallback (when no LLM is available) lives in
    :func:`detectar_violencia_comun_heuristica` and is invoked by the
    fallback path, not by the LLM classifier.

    Returning a benign result here means "let the LLM see this text".
    """
    return detectar_basura_digital(text)
