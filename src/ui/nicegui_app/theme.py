"""Design system 'Tinta y Rosa' for the Enola NiceGUI app.

Centralised palette, typography, spacing, and Quasar/NiceGUI theme
hooks. Every component in :mod:`src.ui.nicegui_app` imports from here
so the visual identity is enforced from a single source of truth.

Palette inspiration: Enola Holmes reimagined — detective mystery meets
refined feminine editorial. Ink + rose + cream + brass (sparing).

Tokens are exposed as:

* Plain Python constants (``PLUM``, ``ROSE`` ...).
* A single :func:`apply_theme` call that registers them with Quasar's
  color system via ``ui.colors()`` and injects a small CSS layer for
  fonts + CSS variables the rest of the app references.

The CSS layer provides:

* Theme tokens (palette, spacing, radii, shadows, typography).
* A global ``body.body--light`` / ``body.body--dark`` baseline.
* Reusable utility classes for KPI cards, sections, heroes, alerts,
  badges, expandable cards, tabs, buttons, inputs, tables and the
  drawer navigation.
* Subtle motion (fade-in, lift on hover) that respects
  ``prefers-reduced-motion``.
"""

from __future__ import annotations

from typing import Final

from nicegui import ui

# --- Palette -----------------------------------------------------------------

PLUM: Final[str] = "#6B4E71"  # primary — mystery (soft aubergine)
PLUM_DEEP: Final[str] = "#5B3B5C"  # primary pressed / hover
ROSE: Final[str] = "#C08497"  # accent — refined feminine
ROSE_SOFT: Final[str] = "#D4A5A5"  # accent muted
BLUSH: Final[str] = "#F2E3E3"  # surface — cards / hover
CREAM: Final[str] = "#FAF6F0"  # background light (parchment)
CREAM_DEEP: Final[str] = "#F4ECE0"  # background deeper
INK: Final[str] = "#231E2E"  # background dark (detective at night)
INK_SOFT: Final[str] = "#2D2640"  # surface dark
CHARCOAL: Final[str] = "#3A3142"  # body text (soft black)
CHARCOAL_LIGHT: Final[str] = "#6B5E73"  # muted text
BRASS: Final[str] = "#BFA181"  # sparing gold accent (clues, dividers)
BRASS_DEEP: Final[str] = "#9D845F"

# Severity palette — kept inside the same hue family for cohesion.
SEVERITY_BAJA: Final[str] = ROSE_SOFT
SEVERITY_MEDIA: Final[str] = BRASS
SEVERITY_ALTA: Final[str] = "#7B3B5C"
SEVERITY_NINGUNA: Final[str] = CHARCOAL_LIGHT

# Reliability alert colors (Regla 1).
RELIABILITY_OK: Final[str] = "#8FA68E"  # sage
RELIABILITY_PREVENTIVA: Final[str] = BRASS
RELIABILITY_CRITICA: Final[str] = "#9D4E5B"  # burgundy

# Category colors — preserved from the Streamlit version so charts stay
# recognisable. Re-mapped to the new palette family for consistency.
CATEGORIA_COLORS: Final[dict[str, str]] = {
    "VDG_VIOLENCIA_SIMBOLICA": "#D49B6A",  # warm amber
    "VDG_COSIFICACION_SLUTSHAMING": ROSE,  # rose
    "VDG_HOSTILIDAD_FEMINICIDIO": "#9D4E5B",  # burgundy
    "VDG_MANOSFERA_ANTIFEMINISMO": "#7B8E8E",  # sage
    "VDG_SALVAGUARDA_FALSO_POSITIVO": CHARCOAL_LIGHT,
    "VDG_DESACREDITACION_ACTIVISTAS": PLUM,
}


# Category labels — centralised in src.ui.labels (reads from taxonomy YAML
# + optional SQLite overrides). The final dict is built at import time so
# theme consumers get a stable snapshot for the session lifetime.
def _build_categoria_labels() -> dict[str, str]:  # pragma: no cover - trivial
    from src.ui.labels import CATEGORIA_LABELS as _central_labels  # noqa: N811

    return dict(_central_labels)


CATEGORIA_LABELS: Final[dict[str, str]] = _build_categoria_labels()


# Subdimension palette — 3 tonalidades derivadas de cada categoría padre.
# Las claves son los 18 códigos canónicos "X.Y"; los valores son hex que
# comparten familia cromática con el color base de su categoría para que
# drill-down (toggle) sea visualmente coherente.
SUBDIMENSION_COLORS: Final[dict[str, str]] = {
    # cat 1 — amber (claro / base / oscuro)
    "1.1": "#E7C79B",
    "1.2": "#D49B6A",
    "1.3": "#A86B36",
    # cat 2 — rose
    "2.1": "#E1B6C2",
    "2.2": "#C08497",
    "2.3": "#8E4B5F",
    # cat 3 — burgundy
    "3.1": "#C28A95",
    "3.2": "#9D4E5B",
    "3.3": "#6E2F38",
    # cat 4 — sage
    "4.1": "#B5C2C2",
    "4.2": "#7B8E8E",
    "4.3": "#506464",
    "4.4": "#6A7A7A",
    # cat 5 — plum (desacreditación de activistas)
    "5.1": "#A488B0",
    "5.2": "#6B4E71",
    "5.3": "#3F2F44",
    # cat 6 — ortogonal (sin jerarquía tonal para no implicar severidad)
    "6.1": "#9D94A3",
    "6.2": CHARCOAL_LIGHT,
    "6.3": "#4A4253",
}


# Labels legibles para las 19 subdimensiones. Se construyen a partir de
# ``DESCRIPCION_SUBDIMENSION`` cuando los nombres canónicos ya están en
# ``category_mapping.py``. Se importan diferidamente para evitar ciclos.
def _build_subdimension_labels() -> dict[str, str]:  # pragma: no cover - trivial
    from src.analyzer.category_mapping import (
        DESCRIPCION_SUBDIMENSION,
        SUBDIMENSIONES_POR_CATEGORIA,
    )

    labels: dict[str, str] = {}
    for cat, dims in SUBDIMENSIONES_POR_CATEGORIA.items():
        cat_label = CATEGORIA_LABELS.get(cat, cat)
        for d in dims:
            desc = DESCRIPCION_SUBDIMENSION.get(d, "")
            labels[d] = f"{d} — {desc} ({cat_label})"
    return labels


SUBDIMENSION_LABELS: Final[dict[str, str]] = _build_subdimension_labels()


# Re-export de la lista canónica de 19 subdimensiones desde
# ``category_mapping`` para que la UI consuma la misma fuente de verdad
# que el resto del proyecto.
def _build_subdimensiones_ordenadas() -> list[str]:  # pragma: no cover - trivial
    from src.analyzer.category_mapping import SUBDIMENSIONES_ORDENADAS as sufdims  # noqa: N811

    return list(sufdims)


SUBDIMENSIONES_ORDENADAS: Final[list[str]] = _build_subdimensiones_ordenadas()


def categoria_de_subdimension(code: str) -> str | None:
    """Resolver código ``"X.Y"`` → código de categoría padre ``VDG_*``.

    Devuelve ``None`` si el código no tiene el formato esperado.
    """
    from src.analyzer.category_mapping import CATEGORIA_POR_SUBDIMENSION

    return CATEGORIA_POR_SUBDIMENSION.get(code or "")


def subdimension_color(code: str) -> str:
    """Devuelve el color de paleta para un código de subdimensión."""
    return SUBDIMENSION_COLORS.get(code, CHARCOAL_LIGHT)


def subdimension_label(code: str) -> str:
    """Devuelve la etiqueta legible para un código de subdimensión.

    Si el código no está canónico, devuelve el código crudo.
    """
    return SUBDIMENSION_LABELS.get(code, code)


# --- Typography --------------------------------------------------------------

FONT_DISPLAY: Final[str] = "Lora, 'Cormorant Garamond', Georgia, serif"
FONT_UI: Final[str] = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
FONT_MONO: Final[str] = "'JetBrains Mono', 'SF Mono', Menlo, monospace"


# --- Spacing & radii ---------------------------------------------------------

RADIUS_SM: Final[str] = "0.5rem"
RADIUS_MD: Final[str] = "0.875rem"
RADIUS_LG: Final[str] = "1.25rem"
RADIUS_XL: Final[str] = "1.75rem"

SHADOW_SM: Final[str] = "0 1px 2px 0 rgba(35, 30, 46, 0.04)"
SHADOW_MD: Final[str] = (
    "0 4px 12px -2px rgba(35, 30, 46, 0.08), 0 2px 4px -2px rgba(35, 30, 46, 0.04)"
)
SHADOW_LG: Final[str] = (
    "0 12px 32px -8px rgba(35, 30, 46, 0.16), 0 4px 8px -4px rgba(35, 30, 46, 0.06)"
)
SHADOW_XL: Final[str] = (
    "0 32px 64px -16px rgba(35, 30, 46, 0.22), 0 12px 24px -12px rgba(35, 30, 46, 0.10)"
)
SHADOW_INSET: Final[str] = "inset 0 0 0 1px rgba(191, 161, 129, 0.20)"


# --- Motion ------------------------------------------------------------------

EASE_OUT: Final[str] = "cubic-bezier(0.16, 1, 0.3, 1)"
EASE_IN_OUT: Final[str] = "cubic-bezier(0.65, 0, 0.35, 1)"
MOTION_FAST: Final[str] = "150ms"
MOTION_BASE: Final[str] = "220ms"
MOTION_SLOW: Final[str] = "420ms"


# --- Quasar registration -----------------------------------------------------

FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap"
    rel="stylesheet">
"""

CSS_LAYER = f"""
<style id="enola-tokens">
:root {{
    --enola-plum: {PLUM};
    --enola-plum-deep: {PLUM_DEEP};
    --enola-rose: {ROSE};
    --enola-rose-soft: {ROSE_SOFT};
    --enola-blush: {BLUSH};
    --enola-cream: {CREAM};
    --enola-cream-deep: {CREAM_DEEP};
    --enola-ink: {INK};
    --enola-ink-soft: {INK_SOFT};
    --enola-charcoal: {CHARCOAL};
    --enola-charcoal-light: {CHARCOAL_LIGHT};
    --enola-brass: {BRASS};
    --enola-brass-deep: {BRASS_DEEP};
    --enola-radius-sm: {RADIUS_SM};
    --enola-radius-md: {RADIUS_MD};
    --enola-radius-lg: {RADIUS_LG};
    --enola-radius-xl: {RADIUS_XL};
    --enola-shadow-sm: {SHADOW_SM};
    --enola-shadow-md: {SHADOW_MD};
    --enola-shadow-lg: {SHADOW_LG};
    --enola-shadow-xl: {SHADOW_XL};
    --enola-shadow-inset: {SHADOW_INSET};
    --enola-font-display: {FONT_DISPLAY};
    --enola-font-ui: {FONT_UI};
    --enola-font-mono: {FONT_MONO};
    --enola-ease-out: {EASE_OUT};
    --enola-ease-in-out: {EASE_IN_OUT};
    --enola-motion-fast: {MOTION_FAST};
    --enola-motion-base: {MOTION_BASE};
    --enola-motion-slow: {MOTION_SLOW};
}}

* {{
    box-sizing: border-box;
}}

/* Selection */
::selection {{
    background: rgba(192, 132, 151, 0.30);
    color: var(--enola-charcoal);
}}
body.body--dark ::selection {{
    background: rgba(192, 132, 151, 0.42);
    color: var(--enola-cream);
}}

html, body, .q-layout {{
    font-family: var(--enola-font-ui);
    font-feature-settings: "ss01", "cv11";
    letter-spacing: -0.005em;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}}

body.body--light {{
    background:
        radial-gradient(
            ellipse at top right,
            rgba(192, 132, 151, 0.06) 0%,
            transparent 55%
        ),
        radial-gradient(
            ellipse at bottom left,
            rgba(191, 161, 129, 0.05) 0%,
            transparent 60%
        ),
        var(--enola-cream);
    background-attachment: fixed;
    color: var(--enola-charcoal);
}}

body.body--dark {{
    background:
        radial-gradient(
            ellipse at top right,
            rgba(192, 132, 151, 0.10) 0%,
            transparent 55%
        ),
        radial-gradient(
            ellipse at bottom left,
            rgba(191, 161, 129, 0.08) 0%,
            transparent 60%
        ),
        var(--enola-ink);
    background-attachment: fixed;
    color: rgba(250, 246, 240, 0.92);
}}

/* Subtle scrollbar that respects the palette */
* {{
    scrollbar-width: thin;
    scrollbar-color: rgba(191, 161, 129, 0.45) transparent;
}}
*::-webkit-scrollbar {{
    width: 10px;
    height: 10px;
}}
*::-webkit-scrollbar-track {{
    background: transparent;
}}
*::-webkit-scrollbar-thumb {{
    background: rgba(191, 161, 129, 0.35);
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: padding-box;
}}
*::-webkit-scrollbar-thumb:hover {{
    background: rgba(192, 132, 151, 0.55);
    background-clip: padding-box;
}}

/* Display utility */
.enola-display {{
    font-family: var(--enola-font-display);
    font-weight: 500;
    letter-spacing: -0.02em;
}}
.enola-mono {{
    font-family: var(--enola-font-mono);
}}

.enola-brass-divider {{
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        var(--enola-brass) 20%,
        var(--enola-brass) 80%,
        transparent 100%
    );
    opacity: 0.85;
}}

/* ============================================================
 * KPI cards — refined surface with subtle gradient + lift
 * ============================================================ */
.enola-kpi {{
    position: relative;
    background:
        linear-gradient(
            150deg,
            rgba(255, 255, 255, 0.85) 0%,
            var(--enola-cream) 60%
        );
    border: 1px solid rgba(191, 161, 129, 0.18);
    border-radius: var(--enola-radius-lg);
    padding: 1.25rem 1.5rem;
    box-shadow: var(--enola-shadow-sm);
    transition:
        box-shadow var(--enola-motion-base) var(--enola-ease-out),
        transform var(--enola-motion-base) var(--enola-ease-out),
        border-color var(--enola-motion-base) var(--enola-ease-out);
    height: 100%;
    overflow: hidden;
}}
.enola-kpi::after {{
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(
        180deg,
        var(--enola-rose) 0%,
        var(--enola-plum) 100%
    );
    opacity: 0.4;
    transition: opacity var(--enola-motion-base) var(--enola-ease-out);
}}
.enola-kpi:hover {{
    box-shadow: var(--enola-shadow-md);
    transform: translateY(-2px);
    border-color: rgba(192, 132, 151, 0.35);
}}
.enola-kpi:hover::after {{
    opacity: 0.85;
}}
body.body--dark .enola-kpi {{
    background: linear-gradient(
        150deg,
        rgba(45, 38, 64, 0.85) 0%,
        var(--enola-ink-soft) 60%
    );
    border-color: rgba(191, 161, 129, 0.12);
}}
body.body--dark .enola-kpi:hover {{
    border-color: rgba(192, 132, 151, 0.30);
}}

.enola-kpi-label {{
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--enola-charcoal-light);
    font-weight: 600;
}}
body.body--dark .enola-kpi-label {{
    color: rgba(250, 246, 240, 0.55);
}}
.enola-kpi-value {{
    font-family: var(--enola-font-display);
    font-size: 2.25rem;
    line-height: 1.1;
    margin-top: 0.4rem;
    color: var(--enola-plum);
    font-weight: 500;
    letter-spacing: -0.025em;
}}
body.body--dark .enola-kpi-value {{
    color: var(--enola-rose);
}}
.enola-kpi-sub {{
    font-size: 0.82rem;
    color: var(--enola-charcoal-light);
    margin-top: 0.45rem;
    line-height: 1.45;
}}
body.body--dark .enola-kpi-sub {{
    color: rgba(250, 246, 240, 0.55);
}}
.enola-kpi-icon {{
    width: 36px; height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition:
        transform var(--enola-motion-base) var(--enola-ease-out),
        box-shadow var(--enola-motion-base) var(--enola-ease-out);
}}
.enola-kpi:hover .enola-kpi-icon {{
    transform: rotate(-6deg) scale(1.05);
}}

/* ============================================================
 * Section header — eyebrow + title + brass divider
 * ============================================================ */

/* ============================================================
 * Premium-dark KPI cards — used by /inicio Resumen row
 * Four inner visualisations: sparkline, gauge, list, progress+avatars.
 * All visuals (SVG, list, bar, avatars) are sized inside this card's
 * baseline grid. Styles are independent from .enola-kpi (the light
 * card variant) so both can coexist.
 * ============================================================ */
.enola-kpi-dark {{
    position: relative;
    background:
        linear-gradient(
            155deg,
            rgba(91, 59, 92, 0.95) 0%,
            rgba(35, 30, 46, 0.95) 100%
        );
    border: 1px solid rgba(191, 161, 129, 0.20);
    border-radius: var(--enola-radius-lg);
    padding: 1.25rem 1.4rem 1.1rem 1.4rem;
    box-shadow: 0 12px 32px -16px rgba(35, 30, 46, 0.55);
    color: rgba(250, 246, 240, 0.92);
    min-height: 180px;
    overflow: hidden;
    isolation: isolate;
}}
.enola-kpi-dark::after {{
    /* brass accent stripe at top, matches light .enola-kpi */
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 2px;
    background: linear-gradient(
        90deg,
        var(--enola-brass) 0%,
        var(--enola-rose) 50%,
        var(--enola-plum) 100%
    );
    opacity: 0.55;
    z-index: 0;
}}
.enola-kpi-dark > * {{
    position: relative;
    z-index: 1;
}}
.enola-kpi-dark__corner {{
    position: absolute;
    top: 12px;
    right: 12px;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(191, 161, 129, 0.22);
    border: 1px solid rgba(191, 161, 129, 0.35);
    z-index: 2;
}}
.enola-kpi-dark__label {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: 0.45rem;
}}
.enola-kpi-dark__label > :first-child {{
    font-family: var(--enola-font-ui);
    font-size: 0.84rem;
    font-weight: 600;
    color: rgba(250, 246, 240, 0.92);
    line-height: 1.2;
    letter-spacing: -0.005em;
}}
.enola-kpi-dark__label > :nth-child(2) {{
    font-size: 0.68rem;
    font-weight: 500;
    color: var(--enola-brass);
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}
.enola-kpi-dark__value {{
    font-family: var(--enola-font-display);
    font-size: 1.85rem;
    font-weight: 600;
    line-height: 1.1;
    color: var(--enola-rose);
    letter-spacing: -0.018em;
    margin: 0.05rem 0 0.6rem 0;
}}
.enola-kpi-dark__chart {{
    margin: 0.25rem 0 0.5rem 0;
    line-height: 0;
}}
.enola-kpi-dark__spark {{
    display: block;
    width: 100%;
    height: 40px;
}}
.enola-kpi-dark__gauge {{
    position: relative;
    width: 96px;
    height: 96px;
    margin: 0 auto 0.4rem auto;
}}
.enola-kpi-dark__gauge-svg {{
    width: 100%;
    height: 100%;
    display: block;
    transform: rotate(-90deg);
}}
.enola-kpi-dark__gauge-track {{
    fill: none;
    stroke: rgba(191, 161, 129, 0.15);
    stroke-width: 8;
}}
.enola-kpi-dark__gauge-fill {{
    fill: none;
    stroke: var(--enola-brass);
    stroke-width: 8;
    stroke-linecap: round;
    transition: stroke-dashoffset var(--enola-motion-slow) var(--enola-ease-out);
    filter: drop-shadow(0 0 6px rgba(191, 161, 129, 0.55));
}}
.enola-kpi-dark__gauge-text {{
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--enola-font-display);
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--enola-rose);
}}
.enola-kpi-dark__list {{
    list-style: none;
    padding: 0;
    margin: 0.25rem 0 0.5rem 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
}}
.enola-kpi-dark__list li {{
    font-size: 0.74rem;
    line-height: 1.35;
    color: rgba(250, 246, 240, 0.78);
    padding-left: 14px;
    position: relative;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.enola-kpi-dark__list li::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 6px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--enola-brass);
    box-shadow: 0 0 4px rgba(191, 161, 129, 0.55);
}}
.enola-kpi-dark__progress {{
    width: 100%;
    height: 10px;
    border-radius: 999px;
    background: rgba(191, 161, 129, 0.18);
    overflow: hidden;
    margin: 0.5rem 0 0.65rem 0;
    border: 1px solid rgba(191, 161, 129, 0.25);
}}
.enola-kpi-dark__progress-fill {{
    height: 100%;
    background: linear-gradient(
        90deg,
        var(--enola-brass) 0%,
        var(--enola-rose) 100%
    );
    box-shadow: 0 0 8px rgba(191, 161, 129, 0.55);
    transition: width var(--enola-motion-slow) var(--enola-ease-out);
}}
.enola-kpi-dark__avatars {{
    display: inline-flex;
    align-items: center;
    margin-top: 0.65rem;
    padding: 2px 0;
}}
.enola-kpi-dark__avatar {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--enola-rose) 0%, var(--enola-plum) 100%);
    color: var(--enola-cream);
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    border: 2px solid rgba(35, 30, 46, 0.95);
    margin-left: -8px;
    box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.30);
    text-transform: uppercase;
}}
.enola-kpi-dark__avatar:first-child {{
    margin-left: 0;
}}
.enola-kpi-dark__sub {{
    font-size: 0.72rem;
    color: rgba(250, 246, 240, 0.55);
    margin-top: 0.55rem;
    line-height: 1.4;
}}
@media (max-width: 768px) {{
    .enola-kpi-dark {{
        min-height: 160px;
        padding: 1rem 1.1rem 0.95rem 1.1rem;
    }}
    .enola-kpi-dark__value {{
        font-size: 1.5rem;
    }}
    .enola-kpi-dark__list li {{
        font-size: 0.7rem;
    }}
}}

.enola-section {{
    margin: 2.75rem 0 1.25rem 0;
}}
.enola-section-eyebrow {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.20em;
    color: var(--enola-brass-deep);
    font-weight: 600;
    margin-bottom: 0.4rem;
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
}}
.enola-section-eyebrow::before {{
    content: "";
    width: 24px; height: 1px;
    background: var(--enola-brass);
    opacity: 0.7;
}}
body.body--dark .enola-section-eyebrow {{
    color: var(--enola-brass);
}}
.enola-section-title {{
    font-family: var(--enola-font-display);
    font-size: 1.7rem;
    font-weight: 500;
    color: var(--enola-charcoal);
    margin: 0;
    letter-spacing: -0.018em;
}}
body.body--dark .enola-section-title {{
    color: rgba(250, 246, 240, 0.92);
}}
.enola-section-subtitle {{
    font-size: 0.92rem;
    color: var(--enola-charcoal-light);
    margin-top: 0.4rem;
    max-width: 72ch;
    line-height: 1.55;
}}
body.body--dark .enola-section-subtitle {{
    color: rgba(250, 246, 240, 0.60);
}}

/* ============================================================
 * Hero — gradient plum with rose radial accents
 * ============================================================ */
.enola-hero {{
    position: relative;
    background:
        radial-gradient(
            ellipse at top right,
            rgba(192, 132, 151, 0.28) 0%,
            transparent 55%
        ),
        radial-gradient(
            ellipse at bottom left,
            rgba(191, 161, 129, 0.22) 0%,
            transparent 60%
        ),
        linear-gradient(
            135deg,
            var(--enola-plum) 0%,
            var(--enola-plum-deep) 100%
        );
    color: var(--enola-cream);
    border-radius: var(--enola-radius-xl);
    padding: 3.25rem 3rem 2.75rem 3rem;
    overflow: hidden;
    box-shadow: var(--enola-shadow-xl);
    isolation: isolate;
}}
.enola-hero::before {{
    content: "";
    position: absolute;
    top: -40px;
    right: -40px;
    width: 220px;
    height: 220px;
    border: 1px solid rgba(250, 246, 240, 0.18);
    border-radius: 50%;
    z-index: -1;
}}
.enola-hero::after {{
    content: "";
    position: absolute;
    bottom: -60px;
    left: -60px;
    width: 180px;
    height: 180px;
    border: 1px solid rgba(191, 161, 129, 0.22);
    border-radius: 50%;
    z-index: -1;
}}
.enola-hero h1 {{
    font-family: var(--enola-font-display);
    font-size: 2.75rem;
    font-weight: 500;
    line-height: 1.05;
    margin: 0 0 0.6rem 0;
    letter-spacing: -0.025em;
}}
.enola-hero p {{
    font-size: 1.02rem;
    line-height: 1.6;
    margin: 0;
    color: rgba(250, 246, 240, 0.88);
    max-width: 68ch;
}}
.enola-hero-badge {{
    display: inline-block;
    font-size: 0.7rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    background: rgba(191, 161, 129, 0.28);
    color: var(--enola-brass);
    padding: 0.38rem 0.95rem;
    border-radius: 999px;
    border: 1px solid rgba(191, 161, 129, 0.5);
    margin-bottom: 1.1rem;
    font-weight: 600;
}}

/* ============================================================
 * Hero image — responsive variant switching
 * Desktop (≥ 769px)  → enola_banner.jpg      (3620x1184 wide)
 * Mobile  (≤ 768px)  → enola_banner_vertical.png (572x1024 tall)
 *
 * Targets raw ``<img>`` HTML rendered via ``ui.html`` to bypass
 * NiceGUI's ``<nicegui-image>`` Vue wrapper (which left the slot
 * empty in some renders).
 * ============================================================ */
img.enola-hero-image-desktop {{
    display: block;
    width: 100%;
    height: auto;
}}
img.enola-hero-image-mobile {{
    display: none;
}}
@media (max-width: 768px) {{
    img.enola-hero-image-desktop {{
        display: none;
    }}
    img.enola-hero-image-mobile {{
        display: block;
        width: 100%;
        max-width: 480px;
        height: auto;
        margin-left: auto;
        margin-right: auto;
    }}
}}

/* ============================================================
 * Hero overlay — banner with text overlay (referente mockup)
 * Grid 2-column desktop with the banner as full background and
 * text positioned above; simplified single-column mobile.
 * ============================================================ */
.enola-hero-overlay {{
    position: relative;
    overflow: hidden;
    border-radius: var(--enola-radius-xl);
    box-shadow: var(--enola-shadow-xl);
    isolation: isolate;
    min-height: 360px;
}}
img.enola-hero-overlay__bg {{
    display: block;
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
    border-radius: var(--enola-radius-xl);
    z-index: 0;
}}
.enola-hero-overlay__content {{
    position: relative;
    z-index: 1;
    padding: 1.5rem 2rem;
    display: grid;
    grid-template-columns: 1fr 1.3fr;
    gap: 1.5rem;
    align-items: center;
    min-height: 360px;
    width: 100%;
    box-sizing: border-box;
}}
.enola-hero-overlay__right {{
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    color: var(--enola-plum-deep);
    max-width: 100%;
    overflow: hidden;
    padding-right: 20px;
}}
.enola-hero-overlay__decor {{
    position: relative;
    height: 360px;
    width: 100%;
    display: grid;
    place-items: center;
}}
.enola-hero-overlay__decor .decor-bubble {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    color: rgba(255, 255, 255, 0.65);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(2px);
}}
.enola-hero-overlay__decor .decor-bubble i {{
    font-style: normal;
}}
.enola-hero-overlay__decor .decor-bubble--lupa   {{ position: absolute; top: 18%; left: 70%;  width: 56px; height: 56px; font-size: 22px; }}
.enola-hero-overlay__decor .decor-bubble--gato   {{ position: absolute; top: 8%;  left: 8%;   width: 44px; height: 44px; font-size: 18px; }}
.enola-hero-overlay__decor .decor-bubble--gato2  {{ position: absolute; top: 50%; left: 4%;   width: 44px; height: 44px; font-size: 18px; }}
.enola-hero-overlay__decor .decor-bubble--check  {{ position: absolute; bottom: 12%; left: 14%; width: 40px; height: 40px; font-size: 16px; }}
.enola-hero-overlay__decor .decor-bubble--hex    {{ position: absolute; bottom: 28%; right: 4%; width: 40px; height: 40px; font-size: 16px; }}
.enola-hero-overlay__decor .decor-bubble--pin    {{ position: absolute; bottom: 6%;  left: 10%; width: 32px; height: 32px; font-size: 14px; }}
.enola-hero-badge {{
    display: inline-block;
    align-self: flex-start;
    margin-right: auto;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.20em;
    text-transform: uppercase;
    color: #4A3520;
    background: linear-gradient(135deg, #E8D4A8 0%, #C9A875 100%);
    padding: 0.45rem 1.1rem;
    border-radius: 999px;
    border: 1px solid rgba(101, 67, 33, 0.30);
    box-shadow: 0 2px 6px -2px rgba(101, 67, 33, 0.35);
}}
.enola-hero-headline {{
    font-family: var(--enola-font-display);
    font-size: clamp(1.05rem, 2.4vw, 1.55rem);
    font-weight: 700;
    line-height: 1.12;
    letter-spacing: -0.018em;
    color: var(--enola-plum-deep);
    margin: 0;
    text-shadow: 0 1px 0 rgba(255, 245, 235, 0.45);
    text-wrap: balance;
    max-width: 28ch;
}}
.enola-hero-bullets {{
    font-size: 0.88rem;
    line-height: 1.50;
    color: var(--enola-charcoal);
    margin: 0;
    padding-left: 1.1rem;
}}
.enola-hero-bullets li {{
    margin-bottom: 0.30rem;
}}
.enola-hero-bullets strong {{
    color: var(--enola-plum-deep);
    font-weight: 700;
}}
.enola-hero-powered {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.78rem;
    color: var(--enola-charcoal-light);
    letter-spacing: 0.04em;
    margin-top: 0.4rem;
    flex-wrap: wrap;
}}
.enola-hero-avatars {{
    display: inline-flex;
    align-items: center;
    margin-left: 0.4rem;
}}
.enola-hero-avatars > span {{
    display: inline-block;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 2px solid #f4e0d0;
    margin-left: -8px;
    background-size: cover;
    background-position: center;
    box-shadow: 0 2px 4px -1px rgba(35, 30, 46, 0.20);
}}
.enola-hero-avatars > span:first-child {{
    margin-left: 0;
}}
.enola-hero-avatars > span:nth-child(1) {{ background: linear-gradient(135deg, #C08497 0%, #6B4E71 100%); }}
.enola-hero-avatars > span:nth-child(2) {{ background: linear-gradient(135deg, #BFA181 0%, #5B3B5C 100%); }}
.enola-hero-avatars > span:nth-child(3) {{ background: linear-gradient(135deg, #D4A5A5 0%, #6B4E71 100%); }}
.enola-hero-avatars > span:nth-child(4) {{ background: linear-gradient(135deg, #E1B6C2 0%, #BFA181 100%); }}

@media (max-width: 768px) {{
    .enola-hero-overlay,
    .enola-hero-overlay__content,
    .enola-hero-overlay__decor {{
        min-height: 220px;
    }}
    .enola-hero-overlay__content {{
        grid-template-columns: 1fr;
        padding: 1.25rem 1.25rem;
        align-items: flex-start;
    }}
    .enola-hero-overlay__decor {{
        display: none;
    }}
    .enola-hero-overlay__right {{
        gap: 0.5rem;
    }}
    .enola-hero-headline {{
        font-size: 1.0rem;
        max-width: 22ch;
    }}
    .enola-hero-bullets {{
        display: none;
    }}
    .enola-hero-powered {{
        font-size: 0.68rem;
    }}
}}

/* ============================================================
 * Reliability banner — semantic colors via border-left + tint
 * ============================================================ */
.enola-alert {{
    border-radius: var(--enola-radius-md);
    padding: 1.1rem 1.35rem;
    border-left: 4px solid var(--enola-brass);
    background: rgba(191, 161, 129, 0.08);
    display: flex;
    align-items: flex-start;
    gap: 0.95rem;
    box-shadow: var(--enola-shadow-sm);
}}
.enola-alert--ok {{
    border-left-color: {RELIABILITY_OK};
    background: rgba(143, 166, 142, 0.10);
}}
.enola-alert--preventiva {{
    border-left-color: {RELIABILITY_PREVENTIVA};
    background: rgba(191, 161, 129, 0.12);
}}
.enola-alert--critica {{
    border-left-color: {RELIABILITY_CRITICA};
    background: rgba(157, 78, 91, 0.10);
}}

/* ============================================================
 * Editorial quote — refined serif blockquote
 * ============================================================ */
.enola-quote {{
    padding: 1.5rem 1.75rem;
    border-radius: var(--enola-radius-md);
    background:
        linear-gradient(
            135deg,
            rgba(191, 161, 129, 0.10) 0%,
            rgba(192, 132, 151, 0.06) 100%
        );
    border-left: 3px solid var(--enola-brass);
    font-family: var(--enola-font-display);
    font-style: italic;
    font-size: 1.08rem;
    color: var(--enola-charcoal);
    line-height: 1.55;
    max-width: 72ch;
    position: relative;
}}
.enola-quote::before {{
    content: "\u201c";
    position: absolute;
    top: -10px; left: 10px;
    font-size: 4rem;
    color: var(--enola-brass);
    opacity: 0.35;
    font-family: var(--enola-font-display);
    line-height: 1;
}}
.enola-quote-cite {{
    font-style: normal;
    font-family: var(--enola-font-ui);
    font-size: 0.75rem;
    color: var(--enola-charcoal-light);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.85rem;
    display: block;
}}

/* ============================================================
 * Pills / chips — refined badges
 * ============================================================ */
.enola-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-family: var(--enola-font-mono);
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    background: rgba(192, 132, 151, 0.12);
    border: 1px solid rgba(192, 132, 151, 0.30);
    color: var(--enola-plum);
    white-space: nowrap;
}}
.enola-pill--brass {{
    background: rgba(191, 161, 129, 0.14);
    border-color: rgba(191, 161, 129, 0.42);
    color: var(--enola-brass-deep);
}}
.enola-pill--ink {{
    background: rgba(58, 49, 66, 0.10);
    border-color: rgba(58, 49, 66, 0.22);
    color: var(--enola-charcoal);
}}
body.body--dark .enola-pill {{
    background: rgba(192, 132, 151, 0.18);
    border-color: rgba(192, 132, 151, 0.38);
    color: var(--enola-rose);
}}

/* ============================================================
 * Panels — standardised surface for repeatable blocks
 * ============================================================ */
.enola-panel {{
    background: linear-gradient(
        180deg,
        rgba(255, 255, 255, 0.70) 0%,
        var(--enola-cream) 100%
    );
    border: 1px solid rgba(191, 161, 129, 0.18);
    border-radius: var(--enola-radius-md);
    padding: 1.5rem 1.75rem;
    box-shadow: var(--enola-shadow-sm);
}}
body.body--dark .enola-panel {{
    background: linear-gradient(
        180deg,
        rgba(45, 38, 64, 0.70) 0%,
        var(--enola-ink-soft) 100%
    );
    border-color: rgba(191, 161, 129, 0.12);
}}

.enola-panel--rose {{
    background: var(--enola-blush);
    border-left: 3px solid var(--enola-rose);
}}
.enola-panel--brass {{
    background: rgba(191, 161, 129, 0.10);
    border-left: 3px solid var(--enola-brass);
}}
.enola-panel--plum {{
    background: linear-gradient(
        135deg,
        rgba(107, 78, 113, 0.06) 0%,
        rgba(192, 132, 151, 0.10) 100%
    );
    border-left: 3px solid var(--enola-plum);
}}

/* ============================================================
 * Tabs — refined
 * ============================================================ */
.q-tabs {{
    border-bottom: 1px solid rgba(191, 161, 129, 0.25);
    margin-bottom: 1.25rem;
}}
.q-tab {{
    font-weight: 500;
    letter-spacing: 0.01em;
    text-transform: none;
    color: var(--enola-charcoal-light);
    padding: 0.75rem 1rem;
    transition: color var(--enola-motion-fast) var(--enola-ease-out);
}}
.q-tab--active {{
    color: var(--enola-plum);
}}
.q-tab__indicator {{
    background: linear-gradient(
        90deg,
        var(--enola-rose) 0%,
        var(--enola-plum) 100%
    ) !important;
    height: 3px !important;
    border-radius: 3px 3px 0 0;
}}

/* ============================================================
 * Tables — refined header + hover rows
 * ============================================================ */
.q-table {{
    border-radius: var(--enola-radius-md);
    overflow: hidden;
    border: 1px solid rgba(191, 161, 129, 0.20);
    background: linear-gradient(
        180deg,
        rgba(255, 255, 255, 0.70) 0%,
        var(--enola-cream) 100%
    );
}}
body.body--dark .q-table {{
    background: linear-gradient(
        180deg,
        rgba(45, 38, 64, 0.70) 0%,
        var(--enola-ink-soft) 100%
    );
    border-color: rgba(191, 161, 129, 0.12);
}}
.q-table thead tr th {{
    font-family: var(--enola-font-ui);
    font-weight: 600 !important;
    font-size: 0.74rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: rgba(191, 161, 129, 0.12) !important;
    color: var(--enola-plum) !important;
    border-bottom: 1px solid rgba(191, 161, 129, 0.30) !important;
    padding: 0.85rem 1rem !important;
}}
body.body--dark .q-table thead tr th {{
    background: rgba(191, 161, 129, 0.08) !important;
    color: var(--enola-brass) !important;
}}
.q-table tbody tr {{
    transition: background var(--enola-motion-fast) var(--enola-ease-out);
}}
.q-table tbody tr:hover {{
    background: rgba(192, 132, 151, 0.05) !important;
}}
body.body--dark .q-table tbody tr:hover {{
    background: rgba(192, 132, 151, 0.10) !important;
}}
.q-table tbody td {{
    padding: 0.7rem 1rem !important;
    font-size: 0.875rem;
    border-bottom: 1px solid rgba(191, 161, 129, 0.10) !important;
}}

/* ============================================================
 * Sidebar / drawer
 * ============================================================ */
.q-drawer {{
    border-right: 1px solid rgba(101, 67, 33, 0.35) !important;
    box-shadow:
        inset -4px 0 10px -4px rgba(58, 36, 18, 0.40),
        6px 0 28px -10px rgba(35, 30, 46, 0.18) !important;
    background: transparent !important;
}}
.q-drawer__inner {{
    background:
        url('/static/wood_sidebar.png') center top / 100% auto repeat-y,
        #D4B896 !important;
    background-color: #D4B896 !important;
    background-attachment: local !important;
    border-left: 1px solid rgba(255, 255, 255, 0.30) !important;
}}
body.body--dark .q-drawer {{
    background: transparent !important;
}}
body.body--dark .q-drawer__inner {{
    background:
        linear-gradient(180deg, rgba(45, 38, 64, 0.60) 0%, rgba(35, 30, 46, 0.70) 100%),
        url('/static/wood_sidebar.png') center top / 100% auto repeat-y,
        #2D2640 !important;
    background-color: #2D2640 !important;
    background-attachment: local !important;
    border-left-color: rgba(255, 255, 255, 0.10) !important;
}}

.enola-nav-item {{
    border-radius: var(--enola-radius-sm);
    margin: 2px 0;
    padding: 9px 12px !important;
    transition:
        background var(--enola-motion-fast) var(--enola-ease-out),
        color var(--enola-motion-fast) var(--enola-ease-out),
        transform var(--enola-motion-fast) var(--enola-ease-out);
    min-height: 42px;
}}
.enola-nav-item .q-item__label,
.enola-nav-item .q-item__section {{
    color: var(--enola-charcoal) !important;
    text-shadow: 0 1px 0 rgba(255, 255, 255, 0.45);
}}
.enola-nav-item:hover {{
    background: rgba(250, 246, 240, 0.75) !important;
    transform: translateX(2px);
}}
.enola-nav-item .q-icon {{
    color: var(--enola-charcoal) !important;
    transition:
        color var(--enola-motion-fast) var(--enola-ease-out),
        transform var(--enola-motion-fast) var(--enola-ease-out);
}}
.enola-nav-item:hover .q-icon {{
    transform: scale(1.1);
}}
.q-item.q-router-link--active,
.q-item.active-link {{
    background: rgba(107, 78, 113, 0.92) !important;
    color: var(--enola-cream) !important;
    border-radius: var(--enola-radius-sm);
    border-left: 3px solid var(--enola-brass);
    padding-left: 9px !important;
    box-shadow: var(--enola-shadow-md);
}}
.q-item.q-router-link--active .q-item__label,
.q-item.q-router-link--active .q-item__section,
.q-item.active-link .q-item__label,
.q-item.active-link .q-item__section {{
    color: var(--enola-cream) !important;
    text-shadow: none;
}}
.q-item.active-link .q-icon {{
    color: var(--enola-cream) !important;
}}
body.body--dark .q-item.active-link {{
    background: rgba(192, 132, 151, 0.85) !important;
    color: var(--enola-cream) !important;
    border-left-color: var(--enola-brass);
}}
body.body--dark .enola-nav-item:hover {{
    background: rgba(250, 246, 240, 0.18) !important;
}}

/* Sidebar brand logos — keep their natural aspect ratio, cap on width & height. */
.enola-brand-logo,
.enola-ugr-logo {{
    display: block;
    width: auto;
    height: auto;
    max-width: 168px;
    object-fit: contain;
    margin-left: auto;
    margin-right: auto;
}}
.enola-brand-logo {{ max-height: 72px; }}
.enola-ugr-logo {{
    max-height: 56px;
    margin-top: 8px;
    margin-bottom: 8px;
    opacity: 0.9;
}}

/* ============================================================
 * Header — refined top bar with scroll elevation
 * ============================================================ */
.q-header {{
    transition:
        background var(--enola-motion-base) var(--enola-ease-out),
        box-shadow var(--enola-motion-base) var(--enola-ease-out),
        border-color var(--enola-motion-base) var(--enola-ease-out) !important;
}}
.enola-header {{
    background: var(--enola-plum) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    border-bottom: 1px solid rgba(191, 161, 129, 0.28);
    box-shadow: 0 2px 8px -4px rgba(0, 0, 0, 0.20);
    color: var(--enola-cream);
}}
.enola-header--scrolled {{
    background: var(--enola-plum-deep) !important;
    border-bottom-color: rgba(191, 161, 129, 0.40);
    box-shadow: 0 4px 12px -4px rgba(0, 0, 0, 0.30);
}}
body.body--dark .enola-header {{
    background: var(--enola-ink-soft) !important;
}}
body.body--dark .enola-header--scrolled {{
    background: var(--enola-ink) !important;
}}

/* ============================================================
 * Inputs — refined outlines
 * ============================================================ */
.q-field--outlined .q-field__control {{
    border-radius: var(--enola-radius-sm) !important;
    transition:
        border-color var(--enola-motion-fast) var(--enola-ease-out),
        box-shadow var(--enola-motion-fast) var(--enola-ease-out);
}}
.q-field--outlined .q-field__control:before {{
    border-color: rgba(191, 161, 129, 0.35) !important;
    border-width: 1px !important;
}}
.q-field--outlined.q-field--focused .q-field__control,
.q-field--outlined:hover .q-field__control {{
    box-shadow: 0 0 0 4px rgba(192, 132, 151, 0.12);
}}
.q-field--outlined.q-field--focused .q-field__control:before {{
    border-color: var(--enola-rose) !important;
    border-width: 1.5px !important;
}}

.q-field--standard .q-field__label {{
    color: var(--enola-charcoal-light);
    font-weight: 500;
}}

/* ============================================================
 * Buttons — rounded, refined hover, brass-rose gradient option
 * ============================================================ */
.q-btn--standard {{
    border-radius: var(--enola-radius-sm) !important;
    text-transform: none !important;
    letter-spacing: 0.005em !important;
    font-weight: 500 !important;
    transition:
        transform var(--enola-motion-fast) var(--enola-ease-out),
        box-shadow var(--enola-motion-fast) var(--enola-ease-out),
        background-color var(--enola-motion-fast) var(--enola-ease-out),
        color var(--enola-motion-fast) var(--enola-ease-out) !important;
}}
.q-btn--standard:hover {{
    transform: translateY(-1px);
}}
.q-btn--standard:active {{
    transform: translateY(0);
}}

/* ============================================================
 * Toggle / switches — refined
 * ============================================================ */
.q-toggle__inner {{
    color: var(--enola-rose-soft) !important;
}}
.q-toggle__inner--truthy {{
    background: var(--enola-plum) !important;
}}

/* ============================================================
 * Expansion cards — soft hover affordance
 * ============================================================ */
.q-expansion-item {{
    background: transparent !important;
    border: 1px solid rgba(191, 161, 129, 0.20) !important;
    border-radius: var(--enola-radius-md) !important;
    box-shadow: var(--enola-shadow-sm);
    transition: box-shadow var(--enola-motion-base) var(--enola-ease-out);
}}
.q-expansion-item:hover {{
    box-shadow: var(--enola-shadow-md);
}}

/* ============================================================
 * Dialog / modal — refined surfaces
 * ============================================================ */
.q-dialog__inner > .q-card,
.q-dialog .q-card {{
    border-radius: var(--enola-radius-lg) !important;
    box-shadow: var(--enola-shadow-xl) !important;
    border: 1px solid rgba(191, 161, 129, 0.20);
}}

/* ============================================================
 * Loading dot / skeleton — tasteful keyframe
 * ============================================================ */
@keyframes enola-fade-in {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
.enola-fade-in {{
    animation: enola-fade-in var(--enola-motion-slow) var(--enola-ease-out) both;
}}
.enola-fade-in-1 {{ animation-delay: 60ms; }}
.enola-fade-in-2 {{ animation-delay: 120ms; }}
.enola-fade-in-3 {{ animation-delay: 180ms; }}
.enola-fade-in-4 {{ animation-delay: 240ms; }}

@keyframes enola-pulse {{
    0%, 100% {{ opacity: 0.55; }}
    50% {{ opacity: 1; }}
}}
.enola-pulse {{
    animation: enola-pulse 1.6s ease-in-out infinite;
}}

/* ============================================================
 * Empty states
 * ============================================================ */
.enola-empty {{
    padding: 2.5rem 2rem;
    border-radius: var(--enola-radius-md);
    background: rgba(191, 161, 129, 0.06);
    border: 1px dashed rgba(191, 161, 129, 0.35);
    color: var(--enola-charcoal-light);
    text-align: center;
}}
.enola-empty-title {{
    font-family: var(--enola-font-display);
    font-weight: 500;
    color: var(--enola-plum);
    font-size: 1.1rem;
    margin-top: 0.75rem;
}}
body.body--dark .enola-empty-title {{
    color: var(--enola-rose);
}}

/* ============================================================
 * Responsive grid system — collapses on mobile
 * ============================================================ */
.enola-grid {{
    display: grid;
    gap: 1rem;
}}
.enola-grid--c1 {{ grid-template-columns: 1fr; }}
.enola-grid--c2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.enola-grid--c3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.enola-grid--c4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}

/* Hamburger — only shown on mobile */
.enola-hamburger {{
    display: none;
}}

/* Close button inside the drawer — only shown on mobile so users
   have a familiar × to dismiss the overlay. On desktop the drawer
   is permanently visible. */
.enola-drawer-close {{
    display: none;
}}

/* Quasar mobile drawer scrim — tinted backdrop when the overlay is
   visible on mobile. Quasar injects a ``q-drawer__backdrop`` element
   that we just tint with the plum hue. */
.q-drawer__backdrop {{
    background: rgba(35, 30, 46, 0.45) !important;
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
}}

/* ============================================================
 * Knowledge editor — file tree rows + markdown preview
 * Used by /conocimiento/editor and /conocimiento/cargar.
 * ============================================================ */
.enola-file-row {{
    transition: background 120ms ease, transform 120ms ease;
}}
.enola-file-row:hover {{
    background: rgba(191, 161, 129, 0.18) !important;
    transform: translateX(2px);
}}
.enola-file-row--active {{
    border-left: 3px solid var(--enola-plum);
}}
.enola-file-row--active:hover {{
    background: rgba(107, 78, 113, 0.16) !important;
}}
.enola-markdown {{
    color: var(--enola-charcoal);
    line-height: 1.55;
    font-size: 0.92rem;
}}
.enola-markdown h1,
.enola-markdown h2,
.enola-markdown h3 {{
    color: var(--enola-plum);
    letter-spacing: -0.01em;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}}
.enola-markdown h1 {{
    font-size: 1.4rem;
    border-bottom: 2px solid rgba(191, 161, 129, 0.40);
    padding-bottom: 0.25rem;
}}
.enola-markdown h2 {{
    font-size: 1.15rem;
}}
.enola-markdown h3 {{
    font-size: 1rem;
}}
.enola-markdown p {{
    margin: 0.5rem 0;
}}
.enola-markdown code {{
    background: rgba(191, 161, 129, 0.18);
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    font-family: var(--enola-font-mono);
    font-size: 0.85em;
}}
.enola-markdown pre {{
    background: rgba(35, 30, 46, 0.06);
    padding: 0.75rem 1rem;
    border-radius: 8px;
    overflow-x: auto;
    font-family: var(--enola-font-mono);
    font-size: 0.82em;
    border-left: 3px solid var(--enola-brass);
}}
.enola-markdown blockquote {{
    margin: 0.75rem 0;
    padding: 0.5rem 1rem;
    border-left: 3px solid var(--enola-rose);
    background: rgba(192, 132, 151, 0.08);
    color: var(--enola-charcoal);
    border-radius: 0 8px 8px 0;
}}
.enola-markdown ul,
.enola-markdown ol {{
    padding-left: 1.5rem;
    margin: 0.5rem 0;
}}
.enola-markdown a {{
    color: var(--enola-plum);
    text-decoration: underline;
    text-decoration-color: rgba(191, 161, 129, 0.50);
    text-underline-offset: 2px;
}}
.enola-markdown table {{
    border-collapse: collapse;
    margin: 0.75rem 0;
    width: 100%;
}}
.enola-markdown th,
.enola-markdown td {{
    border: 1px solid rgba(191, 161, 129, 0.30);
    padding: 0.4rem 0.6rem;
    text-align: left;
}}
.enola-markdown th {{
    background: rgba(191, 161, 129, 0.18);
    font-weight: 600;
}}
body.body--dark .enola-markdown {{
    color: var(--enola-cream);
}}
body.body--dark .enola-markdown code {{
    background: rgba(191, 161, 129, 0.20);
}}
body.body--dark .enola-markdown pre {{
    background: rgba(0, 0, 0, 0.30);
}}
body.body--dark .enola-markdown blockquote {{
    background: rgba(192, 132, 151, 0.15);
}}

/* ============================================================
 * Reduce motion — respect user preference
 * ============================================================ */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
    }}
}}

/* ============================================================
 * Responsive — tablet (≤ 992px)
 * Just shrink the hero a bit and trim drawer shadow. The full
 * responsive pass (hamburger / hidden elements) fires at ≤ 768px.
 * ============================================================ */
@media (max-width: 992px) {{
    .enola-hero {{
        padding: 2.25rem 2rem 1.75rem;
    }}
    .enola-hero h1 {{
        font-size: 2.1rem;
    }}
    .enola-hero p {{
        font-size: 0.96rem;
    }}
    .enola-section-title {{
        font-size: 1.45rem;
    }}
    .q-drawer {{
        box-shadow: none !important;
    }}
}}

/* ============================================================
 * Responsive — mobile (≤ 768px)
 * Compress everything: 4-col KPI → 2-col, 2-col grids → 1-col,
 * shrink typography, hamburger menu, full-width tables
 * ============================================================ */
@media (max-width: 768px) {{
    /* Global content padding */
    main.enola-fade-in,
    main {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }}

    /* Header — tighter and hide brand mark + GitHub link on mobile */
    .q-header {{
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }}
    .enola-header {{
        padding: 0.6rem 0.75rem !important;
    }}
    .enola-brand-mark {{
        display: none;
    }}
    .enola-header__github {{
        display: none !important;
    }}
    .enola-hamburger {{
        display: inline-flex !important;
    }}

    /* Drawer close button — visible on mobile only */
    .enola-drawer-close {{
        display: inline-flex !important;
    }}

    /* Hide the "Modo oscuro" label, keep just the switch */
    .enola-dark-toggle-label {{
        display: none !important;
    }}

    /* User chip — tighter */
    .enola-user-chip {{
        padding-left: 0.5rem !important;
    }}

    /* Hero */
    .enola-hero {{
        padding: 1.75rem 1.25rem 1.5rem;
        border-radius: var(--enola-radius-md);
    }}
    .enola-hero::before,
    .enola-hero::after {{
        display: none;
    }}
    .enola-hero h1 {{
        font-size: 1.7rem;
        letter-spacing: -0.02em;
    }}
    .enola-hero p {{
        font-size: 0.92rem;
        line-height: 1.5;
    }}
    .enola-hero-badge {{
        font-size: 0.62rem;
        padding: 0.32rem 0.75rem;
        letter-spacing: 0.18em;
    }}

    /* KPI cards — stack nicely */
    .enola-kpi {{
        padding: 1rem 1.15rem;
        border-radius: var(--enola-radius-md);
    }}
    .enola-kpi-value {{
        font-size: 1.7rem;
        letter-spacing: -0.02em;
    }}
    .enola-kpi-sub {{
        font-size: 0.78rem;
    }}

    /* KPI grids — collapse to ≤ 2 columns on mobile */
    .enola-grid--c3,
    .enola-grid--c4 {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    }}
    .enola-grid--c2 {{
        grid-template-columns: 1fr !important;
    }}

    /* Section headers */
    .enola-section {{
        margin: 2rem 0 1rem 0;
    }}
    .enola-section-title {{
        font-size: 1.3rem;
        line-height: 1.2;
    }}
    .enola-section-subtitle {{
        font-size: 0.85rem;
        line-height: 1.45;
    }}
    .enola-section-eyebrow {{
        font-size: 0.65rem;
        letter-spacing: 0.16em;
    }}
    .enola-section-eyebrow::before {{
        width: 18px;
    }}

    /* Quote */
    .enola-quote {{
        padding: 1.25rem 1.25rem 1.1rem;
        font-size: 0.96rem;
    }}
    .enola-quote::before {{
        font-size: 3rem;
        top: -6px;
    }}

    /* Panels */
    .enola-panel,
    .enola-panel--rose,
    .enola-panel--brass,
    .enola-panel--plum {{
        padding: 1.1rem 1.25rem;
        border-radius: var(--enola-radius-md);
    }}

    /* Alerts */
    .enola-alert {{
        padding: 0.95rem 1.05rem;
        gap: 0.75rem;
    }}

    /* Footer */
    main {{
        gap: 1.5rem !important;
    }}
    footer {{
        margin-top: 3rem !important;
        padding: 1rem !important;
    }}

    /* Drawer — Quasar's mode="desktop" already collapses the drawer
       to an overlay below 1024px. We just tighten the open width. */
    .q-drawer {{
        width: 260px !important;
    }}

    /* Modal — full width with minimal padding */
    .q-dialog__inner > .q-card,
    .q-dialog .q-card {{
        max-width: 100vw !important;
        margin: 0.5rem !important;
        border-radius: var(--enola-radius-md) !important;
    }}

    /* Tables — tighter cells + horizontal scroll (Quasar already
       wraps with overflow-x:auto; we just tighten padding). */
    .q-table thead tr th {{
        padding: 0.65rem 0.6rem !important;
        font-size: 0.66rem !important;
    }}
    .q-table tbody td {{
        padding: 0.55rem 0.6rem !important;
        font-size: 0.82rem;
    }}

    /* Inline `grid-template-columns` in page sections — collapse
       side-by-side layouts to vertical stacks. The selectors are
       intentionally broad so any ad-hoc 1fr 1fr / 1fr 2fr
       collapses cleanly. */
    [style*="grid-template-columns: 1fr 2fr"],
    [style*="grid-template-columns: 2fr 1fr"],
    [style*="grid-template-columns: 1fr 1fr"],
    [style*="grid-template-columns: 3fr 1fr"],
    [style*="grid-template-columns: 1fr 3fr"] {{
        grid-template-columns: 1fr !important;
    }}

    /* Tabs — smaller text */
    .q-tab {{
        padding: 0.6rem 0.7rem;
        font-size: 0.85rem;
    }}

    /* Step cards (conocimiento page) — shrink the numeric badge */
    .enola-panel .enola-kpi-icon,
    .enola-panel [style*="width: 56px"] {{
        width: 44px !important;
        height: 44px !important;
        font-size: 1.2rem !important;
    }}
}}

/* ============================================================
 * Responsive — small phone (≤ 480px)
 * Final compression pass
 * ============================================================ */
@media (max-width: 480px) {{
    .enola-hero {{
        padding: 1.5rem 1rem 1.25rem;
    }}
    .enola-hero h1 {{
        font-size: 1.45rem;
    }}
    .enola-kpi {{
        padding: 0.85rem 1rem;
    }}
    .enola-kpi-value {{
        font-size: 1.45rem;
    }}
    .enola-section-title {{
        font-size: 1.15rem;
    }}
    .enola-login-card {{
        padding: 1.5rem 1.25rem !important;
    }}
    .enola-login-card .text-3xl {{
        font-size: 1.6rem !important;
    }}
    /* All KPI grids go single-column on tiny screens */
    .enola-grid--c2,
    .enola-grid--c3,
    .enola-grid--c4 {{
        grid-template-columns: 1fr !important;
    }}
}}
</style>
"""


def apply_theme() -> None:
    """Register the Quasar colors, inject fonts and CSS tokens.

    Call once from each NiceGUI page (idempotent — safe to call
    repeatedly). Sets the global Quasar primary/secondary colors and
    installs the ``.body--light`` / ``.body--dark`` token CSS.
    """
    # Inject Google Fonts and the CSS token layer at the document head.
    ui.add_head_html(FONT_LINKS + CSS_LAYER)

    # Register Quasar's brand palette so q-btn / q-icon etc. pick up
    # our colors automatically.
    ui.colors(
        primary=PLUM,
        secondary=ROSE,
        accent=BRASS,
        positive=RELIABILITY_OK,
        negative=RELIABILITY_CRITICA,
        warning=RELIABILITY_PREVENTIVA,
        info="#7B8E8E",
        dark=INK,
    )


def severity_color(severidad: str | None) -> str:
    """Return the palette color for a severity level."""
    return {
        "baja": SEVERITY_BAJA,
        "media": SEVERITY_MEDIA,
        "alta": SEVERITY_ALTA,
        "ninguna": SEVERITY_NINGUNA,
    }.get((severidad or "ninguna").lower(), SEVERITY_NINGUNA)


def reliability_color(nivel: str) -> str:
    """Return the palette color for a Regla 1 alert level."""
    return {
        "ok": RELIABILITY_OK,
        "preventiva": RELIABILITY_PREVENTIVA,
        "critica": RELIABILITY_CRITICA,
    }.get(nivel, RELIABILITY_OK)
