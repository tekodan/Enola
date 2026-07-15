"""Tests for the SSoT drift detector and the prompt renderer consistency."""

from __future__ import annotations

from src.analyzer.prompt_renderer import (
    render_desempate_bloque,
    render_marcadores_bloque,
    render_tabla_canonica,
)
from src.analyzer.taxonomy_loader import (
    Taxonomy,
    load_taxonomy,
    reset_cache,
)
from src.knowledge_base.drift_detector import find_drift, scan_all_narrative


def _tx() -> Taxonomy:
    reset_cache()
    return load_taxonomy()


# ── Renderer consistency ──


def test_renderer_tabla_canonica_includes_all_subdims() -> None:
    """Every sub-dimension declared in the taxonomy must appear in the table."""
    tx = _tx()
    rendered = render_tabla_canonica()
    for cat in tx.categorias:
        for dim in cat.subdimensiones:
            assert dim.code in rendered, f"{dim.code} missing from rendered tabla"


def test_renderer_marcadores_includes_every_canonical_marker() -> None:
    """The rendered marcadores block must contain every canonical marker.

    Markers declared in overlaps are also part of the canonical
    set; they appear as 'overlap' notes. We assert that the marker
    text itself is reachable.
    """
    tx = _tx()
    by_subdim = tx.markers_by_subdimension()
    rendered = render_marcadores_bloque()
    flat = tx.all_canonical_markers()
    for marker in flat:
        for code, markers in by_subdim.items():
            if marker in markers:
                if markers.index(marker) < 8:
                    assert marker in rendered, (
                        f"{marker!r} (in {code}) missing from rendered marcadores block"
                    )
                else:
                    # Truncated — the line for this sub-dim mentions "(y N más)".
                    assert f"- {code} (" in rendered
                break


def test_renderer_desempate_includes_every_rule() -> None:
    """Every tie-breaker rule must appear in the rendered block."""
    tx = _tx()
    rendered = render_desempate_bloque()
    for r in tx.desempate_rules():
        assert r.id in rendered, f"Rule {r.id} missing from rendered desempate block"
        assert r.subdim_ganadora in rendered, f"Rule {r.id} missing subdim_ganadora"


# ── Drift detector ──


def test_drift_detector_returns_list() -> None:
    """The detector returns a list (possibly empty) of drift entries."""
    drift = scan_all_narrative()
    assert isinstance(drift, dict)
    # Every target should be in the dict (even if drift list is empty).
    assert "00-protocolo-algoritmico.md" in drift
    assert "01-categoria-1-violencia-simbolica.md" in drift


def test_drift_detector_finds_known_drift() -> None:
    """A synthetic MD with explicit `marker → X.Y` for a marker that
    belongs elsewhere should be flagged.
    """
    import tempfile
    from pathlib import Path

    # Inject a marker manually (TAXONOMIA.md may not have marcadores_canonicos yet).
    tx = _tx()
    # Mutate the taxonomy in-memory to include a canonical marker.
    cat = next(c for c in tx.categorias if c.orden == 1)
    dim = next(d for d in cat.subdimensiones if d.code == "1.2")
    dim.marcadores_canonicos.append("mujer al volante")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        # "mujer al volante" is canonically 1.2. Drift to 1.1.
        f.write("`mujer al volante` → 1.1 — drift de prueba\n")
        path = Path(f.name)
    try:
        drift = find_drift(path, tx)
        assert any(d["marker"] == "mujer al volante" for d in drift), drift
    finally:
        path.unlink()
