"""Citation helper for the validation modal.

Renders a "📎 Citar selección" button that, when clicked, captures
the reviewer's current text selection within the snippet container
(``#enola-snippet-<id>``) and writes it into the label's evidence
field via the supplied callback.

The selection is read via ``window.getSelection().toString()`` —
works for any selection made with the mouse or keyboard inside the
snippet paragraph.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from nicegui import ui

logger = logging.getLogger(__name__)


def render_citation_button(
    *,
    analysis_id: int | str | None,
    on_cite: Callable[[str], None],
) -> None:
    """Render the citation button.

    Args:
        analysis_id: PK of the analysis row — used to scope the
            snippet query. ``None`` falls back to a global selector.
        on_cite: Callback fired with the captured selection text.
            Callers append it to the active label's evidence.
    """
    snippet_id = f"enola-snippet-{analysis_id}" if analysis_id is not None else "enola-snippet"

    def _handle() -> None:
        # Read the selection from JS, then call on_cite with the result.
        # The script runs asynchronously — NiceGUI's run_javascript
        # doesn't accept a callback, so we use a sentinel DOM element
        # to signal completion back to Python.
        ui.run_javascript(
            f"""
            (function() {{
                const el = document.getElementById('{snippet_id}');
                if (!el) {{
                    console.warn('Snippet not found: {snippet_id}');
                    return;
                }}
                const sel = window.getSelection ? window.getSelection().toString() : '';
                // Stash the captured text on the element so Python
                // can pick it up via a follow-up run_javascript round-trip.
                el.dataset.lastSelection = sel;
                // Trigger a custom event the page can listen for.
                el.dispatchEvent(new CustomEvent('enola-cite', {{detail: sel}}));
            }})();
            """
        )
        # Pull the cached value back synchronously — small enough for
        # a one-shot UI button.
        try:
            captured = ui.run_javascript(
                f"document.getElementById('{snippet_id}')?.dataset?.lastSelection || ''"
            )
        except Exception:  # noqa: BLE001
            captured = ""
        # NiceGUI's run_javascript returns whatever the expression
        # evaluates to. Some versions wrap it in a list — flatten.
        if isinstance(captured, list) and captured:
            captured = captured[0]
        text = str(captured or "").strip()
        if not text:
            ui.notify(
                "Seleccioná texto del snippet antes de citar.",
                type="info",
                position="top-right",
                timeout=2500,
            )
            return
        on_cite(text)
        ui.notify(
            f"📎 Cita insertada ({len(text)} caracteres)",
            type="positive",
            position="top-right",
            timeout=1800,
        )

    ui.button(
        "📎 Citar selección",
        icon="format_quote",
        on_click=_handle,
    ).props("outline size=sm color=brass-deep")


__all__ = ["render_citation_button"]
