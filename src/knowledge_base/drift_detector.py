"""Drift detector for narrative MD files.

Scans the narrative ``01-categoria-*.md`` … ``06-categoria-*.md`` files
plus ``00-protocolo-algoritmico.md`` and ``07-tabla-canonica-prompt.md``
for explicit ``marker → X.Y`` assignments that contradict the canonical
TAXONOMIA.md frontmatter.

This is a *warning-only* tool — the narrative files are hand-written
and may legitimately reference past or future mappings. The detector
just surfaces inconsistencies so reviewers can decide whether the
narrative needs updating.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from src.analyzer.taxonomy_loader import Taxonomy, load_taxonomy, reset_cache

_KNOWLEDGE_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge"
    / "categorias-violencia-genero-digital"
)


def _normalize(m: str) -> str:
    nfkd = unicodedata.normalize("NFKD", m.lower())
    no = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(no.split())


def find_drift(md_path: Path, tx: Taxonomy) -> list[dict]:
    """Scan ``md_path`` for explicit ``<marker> → X.Y`` assignments that
    disagree with the canonical taxonomy.

    Returns a list of ``{"marker", "narrative_subdim", "canonical_subdim"}``
    dicts. Empty list = no drift.
    """
    if not md_path.exists():
        return []

    text = md_path.read_text(encoding="utf-8")

    # Pattern: "`mujer al volante` → 1.2" or "→ **1.2**"
    pat = re.compile(r"`(?P<marker>[^`]+?)`\s*→\s*\*?\*?(?P<subdim>\d\.\d)\*?\*?")

    # Build inverted index: normalized marker → canonical sub-dim.
    marker_to_subdim: dict[str, str] = {}
    for cat in tx.categorias:
        for dim in cat.subdimensiones:
            for marker in dim.marcadores_canonicos:
                marker_to_subdim[_normalize(marker)] = dim.code
    declared_overlaps: set[tuple[str, str]] = set()
    for cat in tx.categorias:
        for dim in cat.subdimensiones:
            for ov in dim.marcadores_overlap:
                declared_overlaps.add((_normalize(ov.marker), ov.subdim_secundaria))

    drift: list[dict] = []
    for m in pat.finditer(text):
        marker = m.group("marker").strip()
        narrative_subdim = m.group("subdim")
        canonical_subdim = marker_to_subdim.get(_normalize(marker))
        if (
            canonical_subdim is not None
            and canonical_subdim != narrative_subdim
            and (_normalize(marker), narrative_subdim) not in declared_overlaps
        ):
            drift.append(
                {
                    "marker": marker,
                    "narrative_subdim": narrative_subdim,
                    "canonical_subdim": canonical_subdim,
                    "line": text[: m.start()].count("\n") + 1,
                }
            )
    return drift


def scan_all_narrative() -> dict[str, list[dict]]:
    """Scan every narrative MD file for drift. Return ``{relpath: drift}``."""
    reset_cache()
    tx = load_taxonomy()
    out: dict[str, list[dict]] = {}
    targets = [
        "00-protocolo-algoritmico.md",
        "01-categoria-1-violencia-simbolica.md",
        "02-categoria-2-cosificacion-slutshaming.md",
        "03-categoria-3-hostilidad-feminicidio.md",
        "04-categoria-4-manosfera-antifeminismo.md",
        "05-categoria-5-desacreditacion-activistas.md",
        "06-categoria-6-sarcasmo-falsos-positivos.md",
        "07-tabla-canonica-prompt.md",
    ]
    for rel in targets:
        path = _KNOWLEDGE_ROOT / rel
        out[rel] = find_drift(path, tx)
    return out
