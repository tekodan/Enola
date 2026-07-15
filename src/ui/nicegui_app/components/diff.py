"""Diff helper for the /validacion page.

Given the AI's classification labels and the reviewer's override
labels, produce a structured diff that the UI can render inline. The
diff covers the ``(categoria, dimension)`` pairs — both views may
carry multiple labels.

Diff semantics:

* ``"added"`` — the reviewer added a label the AI didn't produce.
* ``"removed"`` — the AI produced a label the reviewer dropped.
* ``"kept"`` — both views include the same ``(cat, dim)`` pair.
* ``"changed"`` — same category but different dimension.

The output is a list of dicts so the renderer can decide how to
visualize each operation. Pure-Python so it ships with tests.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from nicegui import ui

from src.ui.nicegui_app import theme
from src.ui.utils import label_for

DiffOp = Literal["added", "removed", "kept", "changed"]


def _normalize(label: dict) -> tuple[str, str] | None:
    cat = str(label.get("categoria") or "").strip()
    if not cat:
        return None
    dim = str(label.get("dimension") or "").strip() or ""
    return (cat, dim)


def compute_label_diff(
    ai_labels: Iterable[dict] | None,
    corrected_labels: Iterable[dict] | None,
) -> list[dict]:
    """Return a diff between the AI's labels and the reviewer's overrides.

    Output schema::

        [
          {"op": "kept",    "cat": ..., "dim": ...},
          {"op": "added",   "cat": ..., "dim": ...},
          {"op": "removed", "cat": ..., "dim": ...},
          {"op": "changed", "cat": ..., "dim": ..., "ai_dim": ...},
          ...
        ]

    The order is: kept pairs first, then added, then removed, then
    changed. Within each group, entries are sorted by ``(cat, dim)``
    for stable output.
    """
    ai_pairs: set[tuple[str, str]] = set()
    ai_by_cat: dict[str, str] = {}
    for label in ai_labels or []:
        pair = _normalize(label)
        if pair is None:
            continue
        ai_pairs.add(pair)
        ai_by_cat.setdefault(pair[0], pair[1])

    corrected_pairs: set[tuple[str, str]] = set()
    corrected_by_cat: dict[str, str] = {}
    for label in corrected_labels or []:
        pair = _normalize(label)
        if pair is None:
            continue
        corrected_pairs.add(pair)
        corrected_by_cat.setdefault(pair[0], pair[1])

    kept: list[tuple[str, str]] = []
    added: list[tuple[str, str]] = []
    removed: list[tuple[str, str]] = []
    changed: list[dict] = []

    all_cats = {cat for cat, _ in ai_pairs | corrected_pairs}

    for cat in sorted(all_cats):
        ai_dim = ai_by_cat.get(cat, "")
        corr_dim = corrected_by_cat.get(cat, "")
        if ai_dim and corr_dim and ai_dim == corr_dim:
            kept.append((cat, ai_dim))
        elif ai_dim and not corr_dim:
            removed.append((cat, ai_dim))
        elif corr_dim and not ai_dim:
            added.append((cat, corr_dim))
        else:
            changed.append(
                {
                    "cat": cat,
                    "dim": corr_dim,
                    "ai_dim": ai_dim,
                }
            )

    def _sort_key(pair: tuple[str, str]) -> tuple[str, str]:
        return pair

    result: list[dict] = []
    for cat, dim in sorted(kept, key=_sort_key):
        result.append({"op": "kept", "cat": cat, "dim": dim})
    for cat, dim in sorted(added, key=_sort_key):
        result.append({"op": "added", "cat": cat, "dim": dim})
    for cat, dim in sorted(removed, key=_sort_key):
        result.append({"op": "removed", "cat": cat, "dim": dim})
    for entry in sorted(changed, key=lambda e: (e["cat"], e["dim"])):
        result.append({**entry, "op": "changed"})
    return result


def has_changes(diff: list[dict]) -> bool:
    """Return True if any entry isn't ``"kept"``."""
    return any(entry.get("op") != "kept" for entry in diff)


# --- Renderer --------------------------------------------------------------


_OP_STYLES: dict[str, dict[str, str]] = {
    "kept": {
        "bg": "rgba(143, 166, 142, 0.14)",
        "border": "rgba(143, 166, 142, 0.35)",
        "color": "#4a6a4a",
        "icon": "✓",
    },
    "added": {
        "bg": "rgba(143, 166, 142, 0.18)",
        "border": "rgba(143, 166, 142, 0.55)",
        "color": "#3d5d3d",
        "icon": "+",
    },
    "removed": {
        "bg": "rgba(157, 78, 91, 0.10)",
        "border": "rgba(157, 78, 91, 0.45)",
        "color": "#7B3B5C",
        "icon": "−",
    },
    "changed": {
        "bg": "rgba(193, 132, 151, 0.12)",
        "border": "rgba(192, 132, 151, 0.45)",
        "color": theme.PLUM,
        "icon": "↻",
    },
}


def render_diff(diff: list[dict]) -> None:
    """Render a list of diff entries as small chips in a row.

    No-op when the diff is empty. Kept entries are muted; changes are
    highlighted with their semantic color.
    """
    if not diff:
        return
    with (
        ui.element("div")
        .classes("enola-diff")
        .style(
            "display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin-top: 0.4rem;"
        )
    ):
        for entry in diff:
            style = _OP_STYLES.get(entry.get("op", "kept"), _OP_STYLES["kept"])
            with ui.element("div").style(
                f"display: inline-flex; align-items: center; gap: 0.3rem; "
                f"padding: 0.2rem 0.55rem; border-radius: 999px; "
                f"background: {style['bg']}; "
                f"border: 1px solid {style['border']}; "
                f"font-size: 0.7rem; letter-spacing: 0.02em;"
            ):
                ui.label(style["icon"]).style(f"color: {style['color']}; font-weight: 700;")
                ui.label(label_for(entry.get("cat") or "")).style(
                    f"color: {style['color']}; font-weight: 600;"
                )
                dim = entry.get("dim") or ""
                ai_dim = entry.get("ai_dim") or ""
                if dim:
                    if entry.get("op") == "changed" and ai_dim:
                        ui.label(f"{ai_dim} → {dim}").classes("text-xs font-mono").style(
                            f"color: {style['color']}; opacity: 0.85;"
                        )
                    else:
                        ui.label(dim).classes("text-xs font-mono").style(
                            f"color: {style['color']}; opacity: 0.85;"
                        )


__all__ = ["compute_label_diff", "has_changes", "render_diff"]
