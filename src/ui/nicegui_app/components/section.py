"""Section header component — replaces Streamlit's ``st.divider()`` + ``st.header()``.

Renders a typographically rich header with:

* an *eyebrow* label (small, uppercase, brass-tinted, wide-tracked) +
  decorative rule,
* a *title* in display serif (Lora),
* an optional subtitle / description line,
* a thin brass gradient divider underneath.
"""

from __future__ import annotations

from nicegui import ui


def section_header(
    eyebrow: str,
    title: str,
    *,
    subtitle: str | None = None,
) -> None:
    """Render a premium section header.

    Example::

        section_header(
            "Regla 1",
            "Reporte de fiabilidad",
            subtitle="Detección de valores perdidos (CÓDIGO 99).",
        )
    """
    with ui.element("div").classes("enola-section"):
        if eyebrow:
            ui.label(eyebrow).classes("enola-section-eyebrow")
        ui.label(title).classes("enola-section-title")
        if subtitle:
            ui.label(subtitle).classes("enola-section-subtitle")
    ui.element("div").classes("enola-brass-divider")
