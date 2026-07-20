"""Inicio — premium landing page.

Composes the hero banner, the headline KPI grid and the Regla 1
reliability banner. All data flows from the SQLite database via the
existing ``build_adjusted_analysis`` pipeline — no business logic
changes, just a premium presentation.
"""

from __future__ import annotations

import logging

from nicegui import app, ui

from src.chat import RAGChat
from src.report.reliability import ReliabilityReport, calcular_valores_perdidos
from src.storage import get_database
from src.ui.adjusted_report import (
    build_adjusted_analysis,
    compute_adjustment_breakdown,
    compute_validation_breakdown,
)
from src.ui.labels import CATEGORIA_LABELS
from src.ui.nicegui_app import theme
from src.ui.nicegui_app.components.kpi_card import empty_state, kpi_grid, premium_dark_grid
from src.ui.nicegui_app.components.section import section_header
from src.ui.nicegui_app.layout import page_scaffold

logger = logging.getLogger(__name__)


@ui.page("/")
def _root_redirect() -> None:
    """Root path — redirect to the landing page."""
    ui.navigate.to("/inicio")


def _strip_thinking(text: str) -> str:
    """Remove reasoning artifacts emitted by thinking models.

    Reasoning models (gemma4 asst-think, qwen3 think, ornith) emit either:
      - a well-formed ``<think>…</think>`` block followed by the answer
      - an unbalanced ``<think>`` that leaks reasoning into the answer
      - a leading English paragraph that begins with "The user …" or
        similar reasoning-style preambles (no tags)

    We always strip ``<think>…</think>`` and additionally drop everything
    from an unmatched opening tag to the first paragraph break, plus any
    leading paragraphs that match the reasoning preamble pattern.
    """
    import re

    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # Drop an unmatched trailing <think>… (no closing tag) up to the
    # first blank-line paragraph break.
    leftover = re.search(r"<think>(?!.*</think>)", cleaned, flags=re.DOTALL)
    if leftover:
        tail = cleaned[leftover.start() :].split("\n\n", 1)
        cleaned = cleaned[: leftover.start()] + (tail[1] if len(tail) > 1 else "")

    # Drop leading paragraphs that look like English reasoning preamble
    # ("The user is asking …", "Let me analyze …", etc.) until we hit a
    # paragraph that doesn't match the pattern.  Conservative: only strips
    # if the first paragraph matches AND it is NOT followed by another
    # non-matching one with Spanish content.
    preamble_re = re.compile(
        r"^\s*(?:the user|let me|i need to|i should|i will|"
        r"my (?:task|role|job)|analyzing|analyse|analysis:)\b",
        re.IGNORECASE,
    )
    paragraphs = cleaned.split("\n\n")
    while paragraphs and preamble_re.match(paragraphs[0]):
        paragraphs.pop(0)
    if paragraphs != cleaned.split("\n\n"):
        cleaned = "\n\n".join(paragraphs)

    return cleaned.strip()


def _md(text: str) -> str:
    """Convert markdown to safe HTML for the chat bubble.

    Uses a permissive Markdown renderer so the model's markdown (**bold**,
    *italic*, lists, code) renders properly.  We escape user-controlled content
    only when injecting manually — for the LLM response we trust the markup.
    """
    import bleach
    import markdown as md_lib

    html = md_lib.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
        output_format="html",
    )
    allowed_tags = [
        "p",
        "br",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "s",
        "ul",
        "ol",
        "li",
        "code",
        "pre",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "a",
        "hr",
    ]
    allowed_attrs = {"a": ["href", "title", "target", "rel"]}
    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)


def _get_rag_chat() -> RAGChat:
    """Get the RAGChat singleton from the NiceGUI app state."""
    return app.RAG_CHAT  # type: ignore[no-any-return]


@app.post("/api/chat")
async def api_chat(request: dict) -> dict:
    """RAG-enabled chat endpoint — retrieves from ChromaDB and calls the LLM."""
    text = (request or {}).get("message", "") if isinstance(request, dict) else ""

    rag_chat = _get_rag_chat()
    result = await rag_chat.chat(text)

    response_html = _md(result.text) if result.text else ""
    return {
        "response": result.text,
        "response_html": response_html,
        "sources": result.sources,
        "error": result.error,
    }


@ui.page("/inicio")
def page_inicio() -> None:
    """Premium landing — hero, KPIs, Regla 1 reliability banner.

    Public page (no auth gate): the landing is the same for logged-in
    reviewers and anonymous visitors. Logging in unlocks the rest of
    the navigation and the validation tab.
    """
    page_scaffold(
        "Enola Investigadora Digital",
        subtitle="Detección de violencia de género digital con RAG",
        current_path="/inicio",
        body=render_inicio_body,
        requires_auth=False,
    )


# --- Data loading ------------------------------------------------------------


def _load_data() -> tuple[list[dict], list[dict], dict, ReliabilityReport, dict, dict]:
    """Pull everything the Inicio page needs in one shot."""
    db = get_database()
    raw_analysis = db.get_analysis_results()
    feedback_rows = db.list_feedback()

    analysis = build_adjusted_analysis(raw_analysis, feedback_rows)
    adjustment = compute_adjustment_breakdown(analysis)
    reliability = calcular_valores_perdidos(raw_analysis)

    # Validation breakdown — counts reviewed rows (agreement OR
    # disagreement). Used by the Estado de Validación Humana card.
    validation = compute_validation_breakdown(analysis)

    # Reliability metrics (Precisión, Recall, F1) — used by the
    # Precisión del Modelo RAG card. Wrapped in try/except because
    # the sklearn pipeline can raise on degenerate datasets.
    metrics_payload: dict[str, object] = {}
    try:
        from src.report.metrics import compute_reliability_metrics

        analysis_lookup = {
            row.get("analysis_result_id") or row.get("id"): row for row in raw_analysis
        }
        rm = compute_reliability_metrics(feedback_rows, analysis_lookup=analysis_lookup)
        metrics_payload = {
            "Precisión": rm.precision,
            "Sensibilidad (Recall)": rm.sensibilidad,
            "F1-Score": rm.f1_score,
            "Soporte": rm.soporte,
        }
    except Exception:
        logger.exception("compute_reliability_metrics falló — card usará fallback")

    return raw_analysis, analysis, adjustment, reliability, validation, metrics_payload


# --- Components --------------------------------------------------------------


def render_hero() -> None:
    """The premium hero — banner with text overlay (referente mockup).

    Replaces the bare image banner with a positioned overlay that floats
    wordmark logo (left column), then badge + headline + bullets +
    "Powered by..." + avatar chips (right column). Mobile collapses to
    a simplified single-column with only badge + headline + powered-by.

    Implementation uses raw ``<img>`` HTML to bypass NiceGUI's
    ``<nicegui-image>`` Vue wrapper. The CSS lives in
    :mod:`src.ui.nicegui_app.theme` under the
    ``.enola-hero-overlay-*`` classes.

    Falls back to the legacy text-only hero when no banner asset is
    found.
    """
    from pathlib import Path

    static_dir = Path(__file__).resolve().parent.parent / "static"
    banner = static_dir / "banner-background.png"

    if banner.exists():
        with (
            ui.element("div")
            .classes("enola-hero-overlay enola-fade-in")
            .style("max-width: 100%; background: transparent; margin: 0 0 1.75rem 0;")
        ):
            # Background banner PNG — raw <img> for reliable render.
            # Position absolute taken from CSS (.enola-hero-overlay__bg).
            ui.html(
                '<img src="/static/banner-background.png?v=4" '
                'class="enola-hero-overlay__bg" '
                'alt="Enola Investigadora Digital — banner" '
                'loading="eager" decoding="sync" />',
                sanitize=False,
            )

            # Overlay content — 2 columns desktop, 1 column mobile
            # (CSS controls which side is visible per breakpoint).
            with ui.element("div").classes("enola-hero-overlay__content"):
                # Left column: decorative bubbles (Material icons) — desktop only.
                with ui.element("div").classes("enola-hero-overlay__decor"):
                    ui.html(
                        '<span class="decor-bubble decor-bubble--lupa" aria-hidden="true">'
                        '<span class="material-icons">search</span></span>'
                        '<span class="decor-bubble decor-bubble--gato" aria-hidden="true">'
                        '<span class="material-icons">pets</span></span>'
                        '<span class="decor-bubble decor-bubble--gato2" aria-hidden="true">'
                        '<span class="material-icons">pets</span></span>'
                        '<span class="decor-bubble decor-bubble--check" aria-hidden="true">'
                        '<span class="material-icons">check</span></span>'
                        '<span class="decor-bubble decor-bubble--hex" aria-hidden="true">'
                        '<span class="material-icons">view_in_ar</span></span>'
                        '<span class="decor-bubble decor-bubble--pin" aria-hidden="true">'
                        '<span class="material-icons">place</span></span>',
                        sanitize=False,
                    )

                # Right column: badge + headline + bullets + powered by
                with ui.element("div").classes("enola-hero-overlay__right"):
                    ui.html(
                        '<span class="enola-hero-badge">TFM 2026 · UNIVERSIDAD DE GRANADA</span>',
                        sanitize=False,
                    )
                    ui.html(
                        '<h2 class="enola-hero-headline">'
                        "UN ENFOQUE RAG DE DETECCIÓN DE VIOLENCIA "
                        "DE GÉNERO DIGITAL EN FACEBOOK"
                        "</h2>",
                        sanitize=False,
                    )
                    ui.html(
                        '<ul class="enola-hero-bullets">'
                        "<li>Inspirado en Enola Holmes, este sistema avanzado "
                        "de investigación digital analiza conversaciones de Facebook "
                        "con una <strong>taxonomía canónica</strong> de "
                        "<strong>6 categorías</strong> y <strong>19 subdimensiones</strong>.</li>"
                        "<li>Asistida por tecnologías de vanguardia como "
                        "<strong>Ollama y ChromaDB</strong>, con validación humana "
                        "en el circuito para <strong>asegurar precisión y ética</strong>.</li>"
                        "</ul>",
                        sanitize=False,
                    )
                    with ui.element("div").classes("enola-hero-powered"):
                        ui.icon("auto_awesome", size="14px").style(
                            "color: var(--enola-brass-deep);"
                        )
                        ui.label("Powered by RAG + Ollama + ChromaDB").style(
                            "color: var(--enola-charcoal); "
                            "font-weight: 500; letter-spacing: 0.04em;"
                        )
                        ui.html(
                            '<span class="enola-hero-avatars" aria-label="Equipo">'
                            "<span></span><span></span><span></span><span></span>"
                            "</span>",
                            sanitize=False,
                        )
        return

    # Fallback — text-only hero (kept identical to legacy version).
    with ui.element("div").classes("enola-hero enola-fade-in"):
        ui.label("TFM 2026 · Universidad de Granada").classes("enola-hero-badge")
        ui.label("Enola Investigadora Digital").classes("enola-display")
        ui.label(
            "Sistema RAG de detección de violencia de género digital en Facebook. "
            "Inspirado en Enola Holmes, analiza conversaciones con una taxonomía "
            "canónica de 6 categorías y 19 subdimensiones, asistida por Ollama "
            "y ChromaDB, con validación humana en el circuito."
        )
        with ui.row().classes("items-center gap-2 mt-3 no-wrap"):
            ui.icon("auto_awesome", size="14px").style("color: var(--enola-brass);")
            ui.label("Powered by RAG + Ollama + ChromaDB + SQLite").classes("text-xs").style(
                "color: rgba(250, 246, 240, 0.78); letter-spacing: 0.04em;"
            )


def _rag_precision_pct(metrics: dict | None) -> float:
    """Extract the model's RAG precision percentage from a metrics dict.

    Returns ``0.0`` when no metrics are available, when ``Precisión`` is
    missing, or when the value is not parseable as a float. Used by
    :func:`render_kpis` for the "Precisión del Modelo RAG" card and by
    :mod:`tests.test_adjusted_report` for landing wiring validation.

    The function is intentionally permissive: any string that can be
    coerced to a float is accepted (e.g. ``"94.2"``, ``"94.2%"``); the
    caller is responsible for clamping the result to the 0..100 range.
    """
    if not metrics:
        return 0.0
    raw = metrics.get("Precisión")
    if raw is None:
        return 0.0
    try:
        value = float(str(raw).rstrip("%").strip())
    except (TypeError, ValueError):
        return 0.0
    if value <= 1.0 and value > 0.0:
        # Already a ratio in [0, 1] — scale to percentage.
        value *= 100.0
    return round(value, 1)


def _precision_subtitle(metrics: dict, *, total: int) -> str:
    """Subtitle string for the Precisión del Modelo RAG card.

    Names the formal definition ``VP / (VP + FP)`` and surfaces the
    feedback coverage (soporte / total) so the percentage is never
    confusable with the AI-vs-human agreement ratio. Returns a string
    with sensible defaults when no metrics are present.
    """
    coverage_pct = 0.0
    if total > 0:
        try:
            soporte = float(metrics.get("Soporte", 0) or 0)
        except (TypeError, ValueError):
            soporte = 0.0
        coverage_pct = round(soporte / total * 100.0, 1)
    if not metrics:
        return "Sin feedback humano validado todavía"
    return f"VP / (VP + FP) · {metrics.get('Soporte', 0)}/{total} ({coverage_pct}% cobertura)"


def _validation_subtitle(validation: dict, *, adjusted_count: int) -> str:
    """Subtitle string for the Estado de Validación Humana card.

    Surfaces the breakdown of validated feedback rows so reviewers
    see how many cases were agreed vs corrected vs pending, plus the
    total reviewed count and denominator.
    """
    validated = int(validation.get("validated_count", 0) or 0)
    agreed = int(validation.get("agreed_count", 0) or 0)
    disagreed = int(validation.get("disagreed_count", 0) or 0)
    pending = int(validation.get("pending_count", 0) or 0)
    total = int(validation.get("total", 0) or 0)
    if total == 0 and adjusted_count == 0:
        return "Sin análisis · 0 revisados · 0 de acuerdo · 0 corregidos · 0 pendientes · 0 totales"
    return (
        f"{validated} revisados · {agreed} de acuerdo · "
        f"{disagreed} corregidos · {pending} pendientes · "
        f"{total} totales"
    )


def render_kpis(
    analysis: list[dict],
    adjustment: dict,
    *,
    validation: dict | None = None,
    metrics_payload: dict | None = None,
) -> None:
    """Render the four premium-dark headline KPI cards.

    Mirrors the referente mockup layout: Total de Casos Analizados,
    Precisión del Modelo RAG, Categorías de Violencia Detectadas and
    Estado de Validación Humana. All numeric data flows from the
    existing ``build_adjusted_analysis`` + ``compute_adjustment_breakdown``
    pipeline — only labels/wiring change here.
    """
    from collections import Counter

    total = len(analysis)
    # Basura digital (CÓDIGO 99) rows are pre-filtered out of the
    # Reglas 2-6 denominators but were still counted in the DB.
    # Subtract them from the headline "Análisis totales" so the KPI
    # reflects what the methodology actually analyses.
    basura_count = sum(1 for a in analysis if str(a.get("exclusion_label") or "") == "CODIGO_99")
    comun_count = sum(
        1 for a in analysis if str(a.get("exclusion_label") or "") == "VIOLENCIA_COMUN"
    )
    net_total = max(total - basura_count - comun_count, 0)
    violent_count = sum(
        1
        for a in analysis
        if str(a.get("tiene_violencia") or "") == "true"
        and str(a.get("exclusion_label") or "") not in {"CODIGO_99", "VIOLENCIA_COMUN"}
    )
    violent_pct = round(violent_count / net_total * 100.0, 1) if net_total else 0.0
    metrics_payload = metrics_payload or {}
    rag_precision_pct = _rag_precision_pct(metrics_payload)
    validation_payload = validation or {}

    # Top-N categorías from the adjusted view (fallback to empty list).
    categoria_counts = Counter(
        str(a.get("categoria") or "")
        for a in analysis
        if str(a.get("categoria") or "") and str(a.get("categoria") or "") != "ninguna"
    )
    top_categories = [
        CATEGORIA_LABELS.get(code, code) for code, _ in categoria_counts.most_common(4)
    ]

    premium_dark_grid(
        [
            {
                "title": "Total de Casos Analizados",
                "subtitle": "Métricas principales",
                "value": f"({net_total:,})".replace(",", "."),
                "sub": (
                    f"De {total} registros · {basura_count} basura digital + "
                    f"{comun_count} violencia común excluida"
                    if basura_count or comun_count
                    else f"{net_total} filas en analysis_results"
                ),
                "chart": "spark",
                "spark_points": [
                    float(basura_count),
                    float(net_total * 0.65),
                    float(net_total * 0.85),
                    float(net_total),
                ],
                "corner_icon": "trending_up",
            },
            {
                "title": "Precisión del Modelo RAG",
                "subtitle": "Validación cruzada",
                "value": f"({rag_precision_pct:.1f}%)",
                "sub": _precision_subtitle(metrics_payload, total=total),
                "chart": "gauge",
                "gauge_pct": rag_precision_pct,
                "corner_icon": "auto_awesome",
            },
            {
                "title": "Categorías de Violencia Detectadas",
                "subtitle": "Top en el dataset",
                "value": str(len(categoria_counts)),
                "sub": f"{violent_pct}% de los casos con sesgo de género",
                "chart": "list",
                "list_items": top_categories,
                "corner_icon": "category",
            },
            {
                "title": "Estado de Validación Humana",
                "subtitle": "Cobertura del equipo",
                "value": f"({validation_payload.get('validated_pct', 0.0):.0f}%)",
                "sub": _validation_subtitle(
                    validation_payload,
                    adjusted_count=int(validation_payload.get("validated_count", 0) or 0),
                ),
                "chart": "progress",
                "progress_pct": validation_payload.get("validated_pct", 0.0),
                "avatars": ["KL", "MV", "AB"],
                "avatar_more": 1
                if int(validation_payload.get("validated_count", 0) or 0) > 3
                else 0,
                "corner_icon": "task_alt",
            },
        ]
    )

    # Secondary row: 3 light-theme KPI cards (kept identical to the
    # legacy behaviour so the canonical taxonomy sub-dim + pages
    # counts stay visible).
    db = get_database()
    stats = db.get_stats()
    categories = 6  # canonical taxonomy
    kpi_grid(
        3,
        [
            {
                "label": "Categorías canónicas",
                "value": str(categories),
                "icon": "category",
                "sub": "Taxonomía cerrada VDG_*",
            },
            {
                "label": "Subdimensiones canónicas",
                "value": str(len(theme.SUBDIMENSIONES_ORDENADAS)),
                "icon": "workspaces",
                "sub": "3-4 subdimensiones por categoría (19 en total)",
            },
            {
                "label": "Páginas analizadas",
                "value": str(stats.get("pages_count", 0)),
                "icon": "public",
                "sub": "Fuentes de Facebook analizadas",
            },
        ],
    )


def _render_reliability_alert(report: ReliabilityReport) -> None:
    """Render the Regla 1 alert with semantic colors."""
    alert_cls = (
        "enola-alert enola-alert--critica"
        if report.nivel == "critica"
        else "enola-alert enola-alert--preventiva"
        if report.nivel == "preventiva"
        else "enola-alert enola-alert--ok"
    )
    icon_name = (
        "verified"
        if report.nivel == "ok"
        else "warning"
        if report.nivel == "preventiva"
        else "error"
    )
    icon_color = theme.reliability_color(report.nivel)

    with ui.element("div").classes(alert_cls):
        with ui.element("div").style(
            "width: 40px; height: 40px; border-radius: 12px; "
            f"background: {icon_color}26; color: {icon_color}; "
            "display: flex; align-items: center; justify-content: center; "
            "flex-shrink: 0;"
        ):
            ui.icon(icon_name, size="22px")
        with ui.column().classes("gap-1 flex-1"):
            ui.label(f"Nivel de alerta · {report.nivel.upper()}").classes(
                "text-xs uppercase font-semibold tracking-widest"
            ).style(f"color: {icon_color}; letter-spacing: 0.18em;")
            ui.label(report.mensaje).classes("text-sm leading-snug").style(
                "color: var(--enola-charcoal); line-height: 1.55;"
            )


def _render_basura_breakdown(report: ReliabilityReport) -> None:
    """Render the basura-digital codigos breakdown as small badges."""
    if not report.detalle_basura_codigos:
        return
    with ui.element("div").classes("w-full mt-5"):
        ui.label("Detalle de códigos de basura digital").classes(
            "text-xs uppercase tracking-widest font-semibold enola-section-eyebrow"
        ).style("margin-bottom: 0.75rem;")
        with ui.row().classes("gap-2 flex-wrap"):
            for codigo, cant in sorted(
                report.detalle_basura_codigos.items(),
                key=lambda x: -x[1],
            ):
                with ui.element("div").classes("enola-pill"):
                    ui.label(f"{codigo} · {cant}")


def render_reliability_section(report: ReliabilityReport) -> None:
    """Backwards-compatible alias for :func:`render_regla1`."""
    render_regla1(report)


def render_regla1(report: ReliabilityReport) -> None:
    """Render the Regla 1 reliability section (3 mini KPIs + alert).

    Public so the canonical "Regla 1" tab in :mod:`estadistica` can
    reuse it without duplicating the markup.
    """
    section_header(
        "Regla 1",
        "Reporte de fiabilidad",
        subtitle=(
            "Detección de valores perdidos (CÓDIGO 99) y violencia común "
            "sin sesgo de género. Hernández-Sampieri y Mendoza Torres (2018)."
        ),
    )

    kpi_grid(
        3,
        [
            {
                "label": "Total de análisis",
                "value": f"{report.total:,}".replace(",", "."),
                "icon": "database",
                "sub": "Filas evaluadas",
            },
            {
                "label": "% Basura digital (CÓDIGO 99)",
                "value": f"{report.pct_basura}%",
                "icon": "delete_sweep",
                "accent": theme.RELIABILITY_CRITICA,
                "sub": f"{report.n_basura_digital} de {report.total} registros",
            },
            {
                "label": "% Violencia común (sin sesgo)",
                "value": f"{report.pct_violencia_comun}%",
                "icon": "block",
                "accent": theme.CHARCOAL_LIGHT,
                "sub": f"{report.n_violencia_comun} de {report.total} registros",
            },
        ],
    )

    with ui.element("div").classes("w-full mt-6"):
        _render_reliability_alert(report)
        _render_basura_breakdown(report)


def render_intro_quote() -> None:
    """Editorial quote — the detective-girl touch."""
    with ui.element("div").classes("enola-quote"):
        ui.label(
            "La violencia de género digital no se mide solo en likes "
            "y reportes: se mide en la intención pragmática del discurso, "
            "en quién ataca, por qué y con qué palabras."
        )
        ui.html(
            "— <span style='font-style: normal;'>Marco metodológico, Regla de exclusión</span>",
            sanitize=False,
        ).style(
            "color: var(--enola-charcoal-light); margin-top: 0.85rem; "
            "font-family: var(--enola-font-ui); font-size: 0.75rem; "
            "letter-spacing: 0.12em; text-transform: uppercase; "
            "font-weight: 600;"
        )


# --- Page entry --------------------------------------------------------------


def _render_ia_chat() -> None:
    """Chat with the AI using NiceGUI elements + JS for interactivity."""
    section_header(
        "💬 Chat con la IA",
        "Preguntá sobre la taxonomía, análisis de posts o por qué se clasificó de cierta forma",
        subtitle=(
            "Ejemplos: '¿en qué categorías clasificarías este texto?' · "
            "'analizá el post 0f3e884a8a124fd1_p2' · "
            "'¿por qué 4.1 y no 1.1?'"
        ),
    )

    with ui.element("div").style(
        "border: 1px solid rgba(191, 161, 129, 0.30); "
        "border-radius: 1rem; overflow: hidden; "
        "background: linear-gradient(180deg, rgba(255, 255, 255, 0.85) 0%, "
        "var(--enola-cream) 100%); "
        "box-shadow: 0 8px 20px -10px rgba(35, 30, 46, 0.08);"
    ):
        messages_el = (
            ui.element("div")
            .props("id=enola-chat-msgs")
            .style(
                "height: 360px; overflow-y: auto; padding: 1.25rem; "
                "display: flex; flex-direction: column; gap: 0.75rem;"
            )
        )
        with messages_el:
            ui.html(
                '<div style="color: #3a3142; font-style: italic; '
                "background: linear-gradient(135deg, rgba(107, 78, 113, 0.08), "
                "rgba(192, 132, 151, 0.06)); "
                "padding: 0.85rem 1.1rem; border-radius: 0.75rem; "
                "border-left: 3px solid #6b4e71; "
                'font-size: 0.875rem; line-height: 1.55;">'
                "¡Hola! Soy Enola, asistente del TFM. Tengo conocimiento basado en la taxonomía "
                "y las reglas de clasificación que podés descargar desde la base de conocimiento.</div>",
                sanitize=False,
            )
            ui.html(
                '<div style="color: #9d845f; font-size: 0.72rem; background: rgba(191, 161, 129, 0.10); '
                "padding: 0.5rem 0.85rem; border-radius: 0.5rem; margin-top: 0.25rem; "
                'letter-spacing: 0.04em; font-style: italic;">'
                "⚠️ La IA puede cometer errores. Mis respuestas se basan en las 6 categorías y 19 subdimensiones de la taxonomía.</div>",
                sanitize=False,
            )

        loading_el = (
            ui.label("⏳ Enola está pensando...")
            .props("id=enola-chat-loading")
            .style(
                "display: none; padding: 0.6rem 1.1rem; "
                "color: var(--enola-plum); font-size: 0.875rem; "
                "border-top: 1px solid rgba(191, 161, 129, 0.25); "
                "background: rgba(191, 161, 129, 0.04);"
            )
        )

        with ui.element("div").style(
            "padding: 0.85rem 1rem; "
            "border-top: 1px solid rgba(191, 161, 129, 0.25); "
            "background: rgba(250, 246, 240, 0.65); "
            "display: flex; gap: 0.5rem; align-items: flex-end;"
        ):
            chat_input = (
                ui.input(placeholder="Escribí tu pregunta y presioná Enter…")
                .style("flex: 1;")
                .props("outlined dense")
            )
            ui.button(
                "Enviar",
                icon="send",
                on_click=lambda: _chat_send(chat_input, messages_el, loading_el),
            ).props("color=primary unelevated").style(
                f"background: {theme.PLUM}; color: {theme.CREAM}; font-weight: 500;"
            )

        chat_input.on(
            "keydown",
            lambda _: _chat_send(chat_input, messages_el, loading_el),
            js_handler="(e) => { if(e.key === 'Enter') emit('keydown', {key: 'Enter'}); }",
        )


def _chat_send(
    chat_input: ui.Input,
    messages_el: ui.Element,
    loading_el: ui.Element,
) -> None:
    """Handle chat send — called from button click or Enter key."""
    text = chat_input.value.strip()
    if not text:
        return

    _append_msg(messages_el, text, is_user=True)
    chat_input.value = ""
    loading_el.style(
        "display: block; padding: 0.6rem 1.1rem; "
        "color: var(--enola-plum); font-size: 0.875rem; "
        "border-top: 1px solid rgba(191, 161, 129, 0.25);"
    )

    target_slot = messages_el.parent_slot

    import asyncio

    loop = asyncio.get_event_loop()

    chat_response: str = ""
    chat_response_html: str = ""
    chat_error: str = ""
    chat_sources: list[dict] = []

    def _show_response() -> None:
        loading_el.style("display: none;")
        with target_slot:
            _append_msg(
                messages_el,
                chat_response,
                is_user=False,
                content_html=chat_response_html or None,
                sources=chat_sources,
            )

    def _show_error() -> None:
        loading_el.style("display: none;")
        with target_slot:
            _append_msg(messages_el, f"Error: {chat_error}", is_user=False)

    def _blocking_request() -> None:
        nonlocal chat_response, chat_response_html, chat_error, chat_sources
        import json
        import urllib.request

        try:
            body = json.dumps({"message": text}).encode()
            req = urllib.request.Request(
                "http://localhost:8080/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
                chat_response = data.get("response", "Sin respuesta")
                chat_response_html = data.get("response_html") or ""
                chat_sources = data.get("sources") or []
                loop.call_soon_threadsafe(_show_response)
        except Exception as exc:
            logger.exception("Chat HTTP error")
            chat_error = str(exc)
            loop.call_soon_threadsafe(_show_error)

    loop.run_in_executor(None, _blocking_request)


def _append_msg(
    messages_el: ui.Element,
    text: str,
    is_user: bool,
    content_html: str | None = None,
    sources: list[dict] | None = None,
) -> None:
    if is_user:
        bg = "linear-gradient(135deg, rgba(107, 78, 113, 0.18) 0%, rgba(192, 132, 151, 0.14) 100%)"
        color = "var(--enola-plum)"
        align = "flex-end"
        tail_radius = "border-bottom-right-radius: 0.25rem;"
    else:
        bg = "linear-gradient(135deg, rgba(191, 161, 129, 0.16) 0%, rgba(192, 132, 151, 0.10) 100%)"
        color = "var(--enola-charcoal)"
        align = "flex-start"
        tail_radius = "border-bottom-left-radius: 0.25rem;"

    if content_html:
        body = content_html
    else:
        import html as html_lib

        body = html_lib.escape(text).replace("\n", "<br>")

    # Append sources block for bot messages
    sources_html = ""
    if sources and not is_user:
        src_items = []
        for i, s in enumerate(sources, start=1):
            src_name = s.get("source", "?")
            dist = s.get("distance")
            dist_str = f" (dist={dist:.3f})" if isinstance(dist, (int, float)) else ""
            snippet = s.get("text", "")
            src_items.append(
                f'<li style="margin-bottom: 0.35rem; font-size: 0.78rem; '
                f'color: var(--enola-charcoal-light);">'
                f"<strong>[{i}]</strong> {src_name}{dist_str}"
                f'<br><span style="opacity: 0.75;">{snippet}...</span></li>'
            )
        if src_items:
            sources_html = (
                '<details style="margin-top: 0.5rem; font-size: 0.78rem;">'
                '<summary style="cursor: pointer; color: var(--enola-plum); '
                'font-weight: 500;">📚 Fuentes consultadas</summary>'
                f'<ol style="padding-left: 1.2rem; margin-top: 0.3rem;">'
                f"{''.join(src_items)}</ol></details>"
            )

    msg_html = (
        f'<div style="padding: 0.7rem 1rem; border-radius: 0.875rem; max-width: 82%;'
        f" font-size: 0.875rem; line-height: 1.55; background: {bg}; color: {color};"
        f" align-self: {align}; {tail_radius} word-break: break-word;"
        f' box-shadow: 0 1px 3px rgba(35, 30, 46, 0.05);">{body}{sources_html}</div>'
    )
    ui.html(msg_html, sanitize=False).move(messages_el)


def render_inicio_body() -> None:
    """Render the Inicio page body. Called by the page_scaffold wrapper."""
    with ui.column().classes("w-full gap-8"):
        render_hero()

        try:
            raw_analysis, analysis, adjustment, reliability, validation, metrics_payload = (
                _load_data()
            )
        except Exception as exc:  # pragma: no cover - DB may not be seeded
            logger.exception("Failed to load landing data: %s", exc)
            empty_state(
                "inbox",
                "No se pudo cargar la base de datos",
                hint=(
                    "Asegurate de que el análisis haya corrido al menos "
                    "una vez. Probá correr la pipeline de la herramienta."
                ),
            )
            return

        # Row 1 — KPI grid
        section_header(
            "Resumen",
            "Indicadores clave del análisis",
            subtitle=("Métricas principales calculadas sobre el dataset original de la IA."),
        )
        render_kpis(
            raw_analysis, adjustment, validation=validation, metrics_payload=metrics_payload
        )

        # Editorial interlude
        render_intro_quote()

        # Regla 1 reliability section
        render_reliability_section(reliability)

        _render_ia_chat()

        # Friendly CTA pointing to the rest of the app
        with ui.element("div").style(
            "padding: 1.75rem 2rem; border-radius: 1.25rem; "
            "background: linear-gradient(135deg, rgba(107, 78, 113, 0.06) 0%, "
            "rgba(192, 132, 151, 0.10) 50%, rgba(191, 161, 129, 0.08) 100%); "
            "border: 1px solid rgba(191, 161, 129, 0.30); "
            "box-shadow: 0 8px 24px -10px rgba(35, 30, 46, 0.08); "
            "display: flex; align-items: center; justify-content: space-between; "
            "gap: 1.5rem; flex-wrap: wrap;"
        ):
            with ui.column().classes("gap-1"):
                ui.label("¿Querés profundizar?").classes("enola-display").style(
                    "color: var(--enola-plum); font-size: 1.4rem; "
                    "font-weight: 500; letter-spacing: -0.015em;"
                )
                ui.label(
                    "Explorá las pestañas del menú lateral: estadística "
                    "completa, métricas de la IA, inspector por contenido "
                    "y la base de conocimiento."
                ).classes("text-sm").style(
                    "color: var(--enola-charcoal-light); max-width: 60ch; line-height: 1.55;"
                )
            with ui.row().classes("gap-2"):
                ui.button(
                    "Estadística",
                    icon="insights",
                    on_click=lambda: ui.navigate.to("/estadistica"),
                ).props("color=primary outline").style("font-weight: 500;")
                ui.button(
                    "IA & Confiabilidad",
                    icon="psychology",
                    on_click=lambda: ui.navigate.to("/ia"),
                ).props("color=primary").style("font-weight: 500;")
