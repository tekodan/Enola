"""Loader for the canonical few-shot examples.

The examples live as JSON in ``src/analyzer/few_shot_examples.json``.
Each one teaches the LLM two things at once:

1. The **shape** of the multi-label JSON response
   (``clasificaciones: [...]`` with one entry per category).
2. The **content** — every example is grounded in audited cases from
   ``docs/auditoria-categorizaciones-2026-07-13.md`` so the labels are
   defensible against the manual.

The loader returns the list of dicts expected by
``RAGClassifier(few_shot_examples=...)``. See
``src/analyzer/rag_classifier.py`` for how each entry is rendered into
the prompt.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.analyzer.violence_types import Severity

DEFAULT_PATH = Path(__file__).resolve().parent / "few_shot_examples.json"


def _coerce_severity(raw: object) -> str:
    """Best-effort coerce a free-form severity string to a closed ``Severity`` value.

    Mirrors the mapping in ``src.analyzer.category_mapping.map_gravedad``
    but only returns the string value (the LLM example dicts use string
    severities directly).
    """
    if isinstance(raw, Severity):
        return raw.value
    s = str(raw or "").strip().lower()
    if not s or s in {"ninguna", "none", "null"}:
        return Severity.NINGUNA.value
    if "-" in s:
        s = s.split("-")[0]
    return {
        "baja": Severity.BAJA.value,
        "media": Severity.MEDIA.value,
        "alta": Severity.ALTA.value,
        "extrema": Severity.ALTA.value,
    }.get(s, Severity.NINGUNA.value)


def _normalize_label_entry(raw: dict) -> dict:
    """Return a cleaned dict ready to be emitted in the LLM payload.

    Strips metadata-only keys (``_id``) and coerces severity values to
    the canonical enum names. Keeps ``marcadores_detectados`` as a list
    of strings.
    """
    out = {
        "categoria": str(raw.get("categoria") or "").strip(),
        "dimension": raw.get("dimension"),
        "severidad": _coerce_severity(raw.get("severidad")),
        "justificacion": str(raw.get("justificacion") or "").strip(),
        "evidencia": str(raw.get("evidencia") or "").strip(),
        "regla_disparada": raw.get("regla_disparada"),
        "marcadores_detectados": [str(m) for m in (raw.get("marcadores_detectados") or []) if m],
    }
    return out


def _normalize_example(raw: dict) -> dict:
    """Turn one raw JSON entry into the dict shape ``_build_prompt`` expects.

    The internal ``_id`` keys are stripped. The legacy
    ``(categoria, dimension, severidad, justificacion, ...)`` top-level
    fields (used by the very first version of the JSON) are auto-wrapped
    into a 1-element ``clasificaciones`` list when present, so a partial
    JSON that mixes legacy and multi-label shapes still works.
    """
    text = str(raw.get("text") or "").strip()
    result_raw = raw.get("result") or {}

    cls_raw = result_raw.get("clasificaciones")
    if isinstance(cls_raw, list) and cls_raw:
        clasificaciones = [_normalize_label_entry(e) for e in cls_raw]
    elif result_raw.get("categoria") and result_raw.get("categoria") != "ninguna":
        clasificaciones = [
            _normalize_label_entry(
                {
                    "categoria": result_raw.get("categoria"),
                    "dimension": result_raw.get("dimension"),
                    "severidad": result_raw.get("severidad"),
                    "justificacion": result_raw.get("justificacion", ""),
                    "evidencia": result_raw.get("evidencia", ""),
                    "regla_disparada": result_raw.get("regla_disparada"),
                    "marcadores_detectados": result_raw.get("marcadores_detectados", []),
                }
            )
        ]
    else:
        clasificaciones = []

    severidad_global = result_raw.get("severidad_global") or result_raw.get("severidad", "ninguna")

    out: dict = {
        "text": text,
        "result": {
            "tiene_violencia": bool(result_raw.get("tiene_violencia", bool(clasificaciones))),
            "severidad": _coerce_severity(severidad_global),
            "clasificaciones": clasificaciones,
        },
    }
    if result_raw.get("exclusion_label"):
        out["result"]["exclusion_label"] = result_raw["exclusion_label"]
    return out


@lru_cache(maxsize=1)
def load_few_shot_examples(path: str | Path | None = None) -> tuple[dict, ...]:
    """Load and normalize the few-shot examples.

    The result is ``lru_cache``-d so repeated calls during a batch run
    are O(1).

    Returns:
        Tuple of dicts ready to be passed to
        ``RAGClassifier(few_shot_examples=...)``.

    Raises:
        FileNotFoundError: If the JSON file is missing.
        ValueError: If the JSON has no ``examples`` array or is empty.
    """
    p = Path(path) if path else DEFAULT_PATH
    if not p.exists():
        raise FileNotFoundError(f"few_shot_examples not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    raw_examples = data.get("examples") or []
    if not raw_examples:
        raise ValueError(
            f"few_shot_examples file {p} declares no examples — refusing empty payload"
        )
    return tuple(_normalize_example(e) for e in raw_examples)


def reset_cache() -> None:
    """Drop the cached examples (test helper)."""
    load_few_shot_examples.cache_clear()


__all__ = ["load_few_shot_examples", "reset_cache", "DEFAULT_PATH"]
