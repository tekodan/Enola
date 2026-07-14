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

CATEGORIA_LABELS: Final[dict[str, str]] = {
    "VDG_VIOLENCIA_SIMBOLICA": "Violencia Simbólica",
    "VDG_COSIFICACION_SLUTSHAMING": "Cosificación / Slut-shaming",
    "VDG_HOSTILIDAD_FEMINICIDIO": "Hostilidad / Feminicidio",
    "VDG_MANOSFERA_ANTIFEMINISMO": "Manosfera / Antifeminismo",
    "VDG_SALVAGUARDA_FALSO_POSITIVO": "Salvaguarda (Falso Positivo)",
    "VDG_DESACREDITACION_ACTIVISTAS": "Desacreditación de Activistas",
}


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
    # cat 5 — charcoal / ortogonal (sin jerarquía tonal para no implicar severidad)
    "5.1": "#9D94A3",
    "5.2": CHARCOAL_LIGHT,
    "5.3": "#4A4253",
    # cat 6 — plum
    "6.1": "#A488B0",
    "6.2": "#6B4E71",
    "6.3": "#3F2F44",
}


# Labels legibles para las 18 subdimensiones. Se construyen a partir de
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


# Re-export de la lista canónica de 18 subdimensiones desde
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


# --- Spacing -----------------------------------------------------------------

RADIUS_SM: Final[str] = "0.5rem"
RADIUS_MD: Final[str] = "0.875rem"
RADIUS_LG: Final[str] = "1.25rem"

SHADOW_SM: Final[str] = "0 1px 2px 0 rgba(35, 30, 46, 0.04)"
SHADOW_MD: Final[str] = (
    "0 4px 12px -2px rgba(35, 30, 46, 0.08), 0 2px 4px -2px rgba(35, 30, 46, 0.04)"
)
SHADOW_LG: Final[str] = (
    "0 12px 32px -8px rgba(35, 30, 46, 0.16), 0 4px 8px -4px rgba(35, 30, 46, 0.06)"
)


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
    --enola-ink: {INK};
    --enola-ink-soft: {INK_SOFT};
    --enola-charcoal: {CHARCOAL};
    --enola-charcoal-light: {CHARCOAL_LIGHT};
    --enola-brass: {BRASS};
    --enola-brass-deep: {BRASS_DEEP};
    --enola-radius-sm: {RADIUS_SM};
    --enola-radius-md: {RADIUS_MD};
    --enola-radius-lg: {RADIUS_LG};
    --enola-shadow-sm: {SHADOW_SM};
    --enola-shadow-md: {SHADOW_MD};
    --enola-shadow-lg: {SHADOW_LG};
    --enola-font-display: {FONT_DISPLAY};
    --enola-font-ui: {FONT_UI};
    --enola-font-mono: {FONT_MONO};
}}

html, body, .q-layout {{
    font-family: var(--enola-font-ui);
    font-feature-settings: "ss01", "cv11";
    letter-spacing: -0.005em;
}}

body.body--light {{
    background: var(--enola-cream);
    color: var(--enola-charcoal);
}}

body.body--dark {{
    background: var(--enola-ink);
    color: rgba(250, 246, 240, 0.92);
}}

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
    opacity: 0.6;
}}

/* KPI cards */
.enola-kpi {{
    background: var(--enola-cream);
    border: 1px solid rgba(191, 161, 129, 0.18);
    border-radius: var(--enola-radius-lg);
    padding: 1.25rem 1.5rem;
    box-shadow: var(--enola-shadow-sm);
    transition: box-shadow 220ms ease, transform 220ms ease,
        border-color 220ms ease;
    height: 100%;
}}
.enola-kpi:hover {{
    box-shadow: var(--enola-shadow-md);
    transform: translateY(-2px);
    border-color: rgba(192, 132, 151, 0.35);
}}
body.body--dark .enola-kpi {{
    background: var(--enola-ink-soft);
    border-color: rgba(191, 161, 129, 0.12);
}}
body.body--dark .enola-kpi:hover {{
    border-color: rgba(192, 132, 151, 0.3);
}}
.enola-kpi-label {{
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--enola-charcoal-light);
    font-weight: 500;
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
}}
body.body--dark .enola-kpi-value {{
    color: var(--enola-rose);
}}
.enola-kpi-sub {{
    font-size: 0.82rem;
    color: var(--enola-charcoal-light);
    margin-top: 0.4rem;
}}
body.body--dark .enola-kpi-sub {{
    color: rgba(250, 246, 240, 0.55);
}}

/* Section header */
.enola-section {{
    margin: 2.5rem 0 1.5rem 0;
}}
.enola-section-eyebrow {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: var(--enola-brass-deep);
    font-weight: 600;
    margin-bottom: 0.35rem;
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
    letter-spacing: -0.015em;
}}
body.body--dark .enola-section-title {{
    color: rgba(250, 246, 240, 0.92);
}}

/* Hero */
.enola-hero {{
    position: relative;
    background:
        radial-gradient(
            ellipse at top right,
            rgba(192, 132, 151, 0.18) 0%,
            transparent 55%
        ),
        radial-gradient(
            ellipse at bottom left,
            rgba(191, 161, 129, 0.16) 0%,
            transparent 60%
        ),
        linear-gradient(135deg, var(--enola-plum) 0%, var(--enola-plum-deep) 100%);
    color: var(--enola-cream);
    border-radius: var(--enola-radius-lg);
    padding: 3rem 3rem 2.5rem 3rem;
    overflow: hidden;
    box-shadow: var(--enola-shadow-lg);
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
}}
.enola-hero h1 {{
    font-family: var(--enola-font-display);
    font-size: 2.6rem;
    font-weight: 500;
    line-height: 1.1;
    margin: 0 0 0.6rem 0;
    letter-spacing: -0.02em;
}}
.enola-hero p {{
    font-size: 1.02rem;
    line-height: 1.55;
    margin: 0;
    color: rgba(250, 246, 240, 0.85);
    max-width: 64ch;
}}
.enola-hero-badge {{
    display: inline-block;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    background: rgba(191, 161, 129, 0.25);
    color: var(--enola-brass);
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    border: 1px solid rgba(191, 161, 129, 0.45);
    margin-bottom: 1.1rem;
}}

/* Reliability banner — semantic colors via border-left + tint */
.enola-alert {{
    border-radius: var(--enola-radius-md);
    padding: 1rem 1.25rem;
    border-left: 4px solid var(--enola-brass);
    background: rgba(191, 161, 129, 0.08);
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
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

/* Refined tables */
.q-table {{
    border-radius: var(--enola-radius-md);
    overflow: hidden;
}}
.q-table thead tr th {{
    font-family: var(--enola-font-ui);
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    background: rgba(191, 161, 129, 0.10) !important;
    color: var(--enola-plum) !important;
    border-bottom: 1px solid rgba(191, 161, 129, 0.25) !important;
}}
body.body--dark .q-table thead tr th {{
    background: rgba(191, 161, 129, 0.08) !important;
    color: var(--enola-brass) !important;
}}

/* Sidebar refinement */
.q-drawer {{
    background: var(--enola-cream) !important;
    border-right: 1px solid rgba(191, 161, 129, 0.22) !important;
}}
body.body--dark .q-drawer {{
    background: var(--enola-ink-soft) !important;
    border-right-color: rgba(191, 161, 151, 0.15) !important;
}}

/* Buttons */
.q-btn--standard {{
    border-radius: var(--enola-radius-sm) !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-weight: 500 !important;
}}

/* Drawer items */
.q-item.q-router-link--active,
.q-item.active-link {{
    background: rgba(192, 132, 151, 0.12) !important;
    color: var(--enola-plum) !important;
    border-radius: var(--enola-radius-sm);
}}
body.body--dark .q-item.active-link {{
    color: var(--enola-rose) !important;
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
