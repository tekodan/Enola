"""Landing page — Enola Investigadora Digital.

Streamlit entry point for the project's public dashboard. Shows KPIs,
violent vs non-violent breakdown, per-category distribution and a
content inspector backed by the SQLite analysis database.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.ui.adjusted_report import (  # noqa: E402
    build_adjusted_analysis,
    compute_adjustment_breakdown,
    compute_validation_breakdown,
)
from src.ui.labels import CATEGORIA_LABELS  # noqa: E402
from src.ui.utils import (  # noqa: E402
    CONTACT_EMAIL,
    GITHUB_FORK_URL,
    GITHUB_REPO_URL,
    LOGO_PATH,
    UGR_LOGO_PATH,
    build_bar_chart,
    build_knowledge_zip,
    build_pie_chart,
    compute_bar_data,
    compute_kpis,
    compute_pie_data,
    filter_by_content_type,
    knowledge_summary,
    knowledge_zip_filename,
    label_for,
    load_data,
)

st.set_page_config(
    page_title="Enola Investigadora Digital",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .enola-hero {
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #2c3e50 0%, #4a235a 100%);
        color: #fff;
        margin-bottom: 1.2rem;
    }
    .enola-hero h1 { color: #fff; margin: 0; font-size: 1.9rem; }
    .enola-hero p  { color: #ecf0f1; margin: 0.4rem 0 0 0; }
    .enola-quote {
        border-left: 4px solid #e91e63;
        padding: 0.6rem 1rem;
        background: #fdf2f8;
        border-radius: 6px;
        margin: 1rem 0;
    }
    .enola-card {
        padding: 1rem 1.2rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background: #fafafa;
        height: 100%;
    }
    .enola-card h3 { margin-top: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar() -> str:
    """Render the shared sidebar and return the selected content type."""
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=120)
        st.markdown("### 🔍 Enola")
        st.caption("Investigadora Digital")
        st.divider()

        st.markdown("#### 🎯 Menú")
        st.page_link("landing.py", label="🏠 Inicio", icon="🏠")
        st.page_link("pages/1_📚_Documentacion.py", label="📚 Documentación", icon="📚")

        st.divider()
        st.markdown("#### 🎛️ Filtros")
        content_type = st.radio(
            "Ver datos de:",
            options=["all", "post", "comment"],
            format_func=lambda x: {"all": "Todos", "post": "Posts", "comment": "Comments"}[x],
            index=0,
            key="content_type_filter",
        )

        st.divider()
        st.link_button("⭐ Ver repo en GitHub", GITHUB_REPO_URL, width="stretch")
        st.link_button("🔀 Fork en GitHub", GITHUB_FORK_URL, width="stretch", type="secondary")

        st.divider()
        st.markdown("#### 👥 Créditos")
        st.markdown(
            """
            - **🔬 Investigadora:** Kimberly Michell Luna Eraso
            - **🎓 Tutora de proyecto:** María del Mar García Vita
            """
        )

        st.divider()
        st.markdown("#### 🎓 Universidad de Granada")
        if UGR_LOGO_PATH.exists():
            st.image(str(UGR_LOGO_PATH), width=120)

    return content_type


def render_hero() -> None:
    """Render the hero banner with the project tagline."""
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width="stretch")

    st.markdown(
        """
        <div class="enola-hero">
            <h1>🔍 Enola Investigadora Digital</h1>
            <p>
                Sistema RAG de detección de <strong>violencia de género digital</strong> en Facebook.
                Inspirado en Enola Holmes, analiza conversaciones con una taxonomía
                canónica de 6 categorías y 19 subdimensiones, asistida por Ollama y ChromaDB.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(
    kpis: dict[str, object],
    adjustment: dict[str, object] | None = None,
    validation: dict[str, object] | None = None,
) -> None:
    """Render the headline KPI cards.

    Row 1: Análisis totales, % con violencia, % ajustado por humanos,
    % validado por humanos.
    Row 2: Categorías canónicas, Páginas scrapeadas.

    ``adjustment`` (from :func:`compute_adjustment_breakdown`) only
    counts rows where the reviewer *disagreed* — it answers "¿cuánto
    corrigió la humana?". ``validation`` (from
    :func:`compute_validation_breakdown`) counts rows with ANY human
    feedback — it answers "¿cuánto se revisó?". Both are surfaced.
    """
    if adjustment is None:
        adjustment = {
            "adjusted_pct": 0.0,
            "autonomous_pct": 0.0,
            "adjusted_count": 0,
            "total": 0,
        }
    if validation is None:
        validation = {
            "validated_pct": 0.0,
            "pending_pct": 100.0,
            "validated_count": 0,
            "agreed_count": 0,
            "disagreed_count": 0,
            "pending_count": adjustment.get("total", 0),
            "total": adjustment.get("total", 0),
        }

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📄 Análisis totales", kpis["total"])
    col2.metric("🚨 % con violencia", f"{kpis['violent_pct']}%", help="Del total analizado")
    col3.metric(
        "🧑 % Validado por humanos",
        f"{validation['validated_pct']}%",
        help=(
            f"{validation.get('validated_count', 0)} de {validation.get('total', 0)} "
            f"análisis revisados (acuerdo + corrección). "
            f"Sobre ellos: {validation.get('agreed_count', 0)} de acuerdo, "
            f"{validation.get('disagreed_count', 0)} corregidos."
        ),
    )
    col4.metric(
        "🤖 % Autónomo",
        f"{validation['pending_pct']}%",
        help="Sin revisión humana — clasificación sólo de la IA",
    )

    col5, col6, _, _ = st.columns(4)
    col5.metric(
        "📚 Categorías canónicas",
        kpis["categories"],
        help="Taxonomía cerrada VDG_*",
    )
    col6.metric("🗄️ Páginas scrapeadas", kpis["pages"])


def render_reliability_banner(analysis: list[dict]) -> dict[str, object]:
    """Render the Regla 1 reliability banner with the missing-values report.

    Shows the percentage of CODIGO_99 / basura digital rows and the
    alert level (ok / preventiva / crítica). Returns the dict so it
    can also be referenced by other panels.
    """
    from src.report.reliability import calcular_valores_perdidos

    st.divider()
    st.subheader("🛡 Reporte de fiabilidad (Regla 1 — Valores perdidos)")

    report = calcular_valores_perdidos(analysis)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total de análisis", report.total)
    col_b.metric(
        "🗑 % Basura digital (CÓDIGO 99)",
        f"{report.pct_basura}%",
        help=f"{report.n_basura_digital} de {report.total} registros",
    )
    col_c.metric(
        "🧯 % Violencia común (sin sesgo)",
        f"{report.pct_violencia_comun}%",
        help=f"{report.n_violencia_comun} de {report.total} registros",
    )

    if report.nivel == "critica":
        st.error(f"🚨 {report.mensaje}")
    elif report.nivel == "preventiva":
        st.warning(f"⚠️ {report.mensaje}")
    else:
        st.success(f"✅ {report.mensaje}")

    if report.detalle_basura_codigos:
        with st.expander("🔍 Detalle de códigos de basura digital"):
            codigos_df = pd.DataFrame(
                [
                    {
                        "Código": codigo,
                        "Cantidad": cant,
                        "Porcentaje": round(cant / max(report.n_basura_digital, 1) * 100, 1),
                    }
                    for codigo, cant in sorted(
                        report.detalle_basura_codigos.items(),
                        key=lambda x: -x[1],
                    )
                ]
            )
            st.dataframe(codigos_df, width="stretch", hide_index=True)

    return report.to_dict()


def render_reliability_metrics_section(analysis: list[dict]) -> None:
    """Render the Regla 6 reliability/validity section.

    Computes the confusion matrix and Precision/Recall/F1 from human
    feedback (which is the ground truth per the document). Shows the
    matrix, the three metrics, and the supporting sample size.
    """
    from src.report.metrics import render_metrics_report

    st.divider()
    st.subheader("🔬 Confiabilidad y validez de la IA (Regla 6)")

    # Load feedback from the DB.
    from src.storage import get_database

    db = get_database()
    feedback_rows = db.list_feedback()
    raw_analysis = db.get_analysis_results()

    # Las métricas deben comparar la predicción original de la IA con el feedback;
    # no usar ``analysis`` porque puede contener overrides humanos.
    analysis_lookup: dict = {}
    for a in raw_analysis:
        aid = a.get("id") or a.get("analysis_id")
        if aid is not None:
            analysis_lookup[aid] = a

    if not feedback_rows:
        st.info(
            "Sin feedback humano todavía. Marcá análisis en la pestaña "
            "**Validación** de `app.py` para alimentar esta métrica."
        )
        return

    report = render_metrics_report(feedback_rows, analysis_lookup=analysis_lookup)
    cm_dict = report["confusion_matrix"]
    metrics = report["metrics"]

    st.caption(f"**Soporte (n)**: {report['soporte']} análisis con feedback humano.")

    # --- Confusion matrix ---
    st.markdown("**Matriz de confusión (Paso 6.1)**")
    cm_df = report["confusion_matrix_df"]
    st.dataframe(cm_df, width="stretch", hide_index=True)

    col_vp, col_vn, col_fp, col_fn = st.columns(4)
    col_vp.metric("Verdaderos Positivos", cm_dict["VP"])
    col_vn.metric("Verdaderos Negativos", cm_dict["VN"])
    col_fp.metric("Falsos Positivos", cm_dict["FP"])
    col_fn.metric("Falsos Negativos", cm_dict["FN"])

    # --- Reliability metrics ---
    st.markdown("**Métricas de fiabilidad algorítmica (Paso 6.2)**")
    col_p, col_r, col_f = st.columns(3)
    col_p.metric(
        "🎯 Precisión",
        f"{metrics['Precisión'] * 100:.1f}%",
        help="VP / (VP + FP)",
    )
    col_r.metric(
        "📡 Sensibilidad (Recall)",
        f"{metrics['Sensibilidad (Recall)'] * 100:.1f}%",
        help="VP / (VP + FN)",
    )
    col_f.metric(
        "⚖ F1-Score",
        f"{metrics['F1-Score'] * 100:.1f}%",
        help="Media armónica de precisión y sensibilidad",
    )

    st.caption(
        "Paso 6.3 del documento: estas métricas certifican que los resultados "
        "descriptivos provienen de un instrumento válido y confiable."
    )


def render_descriptive_statistics(
    analysis: list[dict],
    posts: list[dict] | None = None,
) -> None:
    """Render the descriptive statistics section (Reglas 2, 3 y 4).

    Includes:
    * Tabla de Distribución de Frecuencias (4 columnas, Regla 2).
    * Moda con detección bimodal y texto automatizado (Regla 3).
    * Tabulaciones cruzadas: categoría × subdimensión / página / fecha
      (Regla 4) con porcentajes marginales de columna.
    """
    from src.report.stats import (
        compute_crosstabs,
        compute_frequency_distribution,
        compute_mode,
    )

    st.divider()
    st.header("📊 Estadística descriptiva (Reglas 2, 3 y 4)")

    # --- Regla 2: Tabla de Distribución de Frecuencias ---
    st.subheader("Regla 2 · Distribución de frecuencias")
    ft = compute_frequency_distribution(analysis, categoria_labels=CATEGORIA_LABELS)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("📑 Válidos analizados", ft.total_validos)
    col_b.metric("🚫 Excluidos (basura+común)", ft.n_excluidos)
    col_c.metric("📐 Categorías detectadas", sum(1 for r in ft.rows if r.frecuencia_absoluta > 0))

    st.caption(
        "El **porcentaje válido** excluye los valores perdidos (CÓDIGO 99) y la "
        "violencia común, y se calcula sobre los registros válidos. El "
        "**porcentaje acumulado** suma progresivamente de mayor a menor hasta 100%."
    )
    st.dataframe(ft.to_dataframe(), width="stretch", hide_index=True)

    # --- Regla 3: Moda ---
    st.subheader("Regla 3 · Moda (medida de tendencia central)")
    mode = compute_mode(analysis, categoria_labels=CATEGORIA_LABELS)

    if mode.modas:
        if mode.es_multimodal:
            cualif = "bimodal" if len(mode.modas) == 2 else "multimodal"
            st.warning(
                f"⚠️ La distribución es **{cualif}** ({len(mode.modas)} categorías "
                f"empatan en {max(mode.frecuencias.values())} casos)."
            )
        nombres = [CATEGORIA_LABELS.get(m, m) for m in mode.modas]
        st.markdown("**Categorías modales:** " + ", ".join(f"*{n}*" for n in nombres))
    st.info(mode.texto_descriptivo)

    # --- Regla 4: Tabulaciones cruzadas ---
    st.subheader("Regla 4 · Análisis bivariado (tablas de contingencia)")

    tab_sub, tab_page, tab_date = st.tabs(
        ["Categoría × Subdimensión", "Categoría × Página", "Categoría × Mes"]
    )

    with tab_sub:
        ct = compute_crosstabs(
            analysis, dimension="subdimension", categoria_labels=CATEGORIA_LABELS
        )
        if not ct.filas:
            st.info("Sin datos válidos para el cruce.")
        else:
            st.caption("**Frecuencias observadas (n):**")
            st.dataframe(ct.to_dataframe(), width="stretch")
            st.caption(
                "**Porcentajes marginales de columna (%):** "
                "'Del total de la subdimensión X, qué porcentaje cae en cada categoría.'"
            )
            st.dataframe(ct.to_porcentajes_dataframe(), width="stretch")
            if ct.alerta_patron:
                st.success(f"🎯 **Patrón relacional:** {ct.alerta_patron}")

    with tab_page:
        page_lookup: dict[str, str] = {}
        for p in posts or []:
            pid = p.get("id")
            if pid:
                page_lookup[pid] = p.get("title") or "Sin título"
            page_id = p.get("page_id")
            if page_id:
                page_lookup[page_id] = p.get("title") or "Sin título"
        ct = compute_crosstabs(
            analysis,
            dimension="pagina",
            posts=posts or [],
            page_lookup=page_lookup,
            categoria_labels=CATEGORIA_LABELS,
        )
        if not ct.filas:
            st.info("Sin datos válidos para el cruce por página.")
        else:
            st.caption("**Frecuencias observadas (n):**")
            st.dataframe(ct.to_dataframe(), width="stretch")
            st.caption("**Porcentajes marginales de columna (%):**")
            st.dataframe(ct.to_porcentajes_dataframe(), width="stretch")
            if ct.alerta_patron:
                st.success(f"🎯 **Patrón relacional:** {ct.alerta_patron}")

    with tab_date:
        ct = compute_crosstabs(
            analysis,
            dimension="fecha",
            posts=posts or [],
            categoria_labels=CATEGORIA_LABELS,
        )
        if not ct.filas:
            st.info("Sin datos válidos para el cruce por mes.")
        else:
            st.caption("**Frecuencias observadas (n):**")
            st.dataframe(ct.to_dataframe(), width="stretch")
            st.caption("**Porcentajes marginales de columna (%):**")
            st.dataframe(ct.to_porcentajes_dataframe(), width="stretch")
            if ct.alerta_patron:
                st.success(f"🎯 **Patrón relacional:** {ct.alerta_patron}")


def render_chart_tabs(results: list[dict]) -> None:
    """Render the pie + bar charts inside a post/comment/all tab.

    Per Regla 5.4 the frequency distribution table is rendered BELOW the
    visualisations (not in a side expander).
    """
    from src.report.stats import compute_frequency_distribution

    tab_all, tab_posts, tab_comments = st.tabs(["Todos", "Posts", "Comments"])
    tabs = {
        "all": tab_all,
        "post": tab_posts,
        "comment": tab_comments,
    }
    for key, tab in tabs.items():
        with tab:
            subset = filter_by_content_type(results, key)
            if not subset:
                st.info("No hay resultados para este filtro.")
                continue
            col_pie, col_bar = st.columns(2)
            with col_pie:
                st.subheader("🥧 Violentos vs No violentos")
                pie_df = compute_pie_data(subset)
                total = int(pie_df["Cantidad"].sum())
                st.caption(f"Total: **{total}** contenidos analizados")
                st.altair_chart(build_pie_chart(pie_df), width="stretch")
            with col_bar:
                st.subheader("📊 Distribución por categoría")
                bar_df = compute_bar_data(subset)
                st.altair_chart(build_bar_chart(bar_df), width="stretch")

            # Tabla de Distribución de Frecuencias (Regla 5.4) — debajo
            # de las gráficas, no en un expander lateral.
            st.markdown("---")
            st.markdown("**Tabla de distribución de frecuencias (Regla 2)**")
            ft = compute_frequency_distribution(subset, categoria_labels=CATEGORIA_LABELS)
            st.caption(
                "Porcentaje válido excluye los registros con CÓDIGO 99 / "
                "VIOLENCIA_COMUN. Porcentaje acumulado suma de mayor a menor."
            )
            st.dataframe(ft.to_dataframe(), width="stretch", hide_index=True)


def render_inspector(analysis: list[dict], posts: list[dict], comments: list[dict]) -> None:
    """Render the drill-down inspector for a single analyzed item."""
    st.divider()
    st.header("🔎 Inspector de contenido")
    st.caption(
        "Elegí un post o comentario analizado para ver el detalle de la "
        "clasificación (categoría, dimensión, severidad, evidencia)."
    )

    col_type, col_id = st.columns([1, 3])
    with col_type:
        item_type = st.selectbox("Tipo", options=["post", "comment"], index=0)
    available = [a for a in analysis if a.get("content_type") == item_type]
    if not available:
        st.info(f"No hay {item_type}s analizados todavía.")
        return
    with col_id:
        item_id = st.selectbox(
            "ID",
            options=[a.get("content_id", "") for a in available],
            index=0,
        )

    selected = next((a for a in available if a.get("content_id") == item_id), None)
    if not selected:
        return

    source_pool = (
        {p["id"]: p for p in posts} if item_type == "post" else {c["id"]: c for c in comments}
    )
    original = source_pool.get(item_id, {})
    original_text = (original.get("text") or "").strip() or "(sin texto)"

    st.markdown("**Texto original:**")
    st.info(original_text[:1500] + ("…" if len(original_text) > 1500 else ""))

    cat = selected.get("categoria", "ninguna")
    dim = selected.get("dimension") or "—"
    sev = selected.get("severidad", "ninguna")
    tiene = selected.get("tiene_violencia", "unknown")
    labels = list(selected.get("labels") or [])

    sev_emoji = {"baja": "🟢", "media": "🟡", "alta": "🔴", "ninguna": "⚪"}.get(sev, "⚪")
    tiene_emoji = "🚨" if tiene == "true" else "✅"

    # Show the data source: AI vs human-adjusted
    if selected.get("adjusted_by_human"):
        st.info(
            "🧑 **Esta categoría/dimensión/justificación fue corregida por un humano.** "
            "El reporte del landing refleja la versión ajustada."
        )
    elif selected.get("has_feedback"):
        st.caption("✅ Revisado por humano — coincide con la IA.")
    else:
        st.caption("🤖 Aún sin revisión humana.")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Violencia", f"{tiene_emoji} {tiene}")
    col_b.metric("Categoría (primaria)", label_for(cat))
    col_c.metric("Subdimensión (primaria)", dim)
    col_d.metric("Severidad global", f"{sev_emoji} {sev}")

    if labels:
        with st.expander(
            f"🏷 Etiquetas detectadas ({len(labels)})",
            expanded=len(labels) > 1,
        ):
            for i, lbl in enumerate(labels, start=1):
                lc = lbl.get("categoria") or "ninguna"
                ld = lbl.get("dimension") or "—"
                ls = lbl.get("severidad") or "ninguna"
                lsev_emoji = {"baja": "🟢", "media": "🟡", "alta": "🔴", "ninguna": "⚪"}.get(
                    ls, "⚪"
                )
                st.markdown(f"**#{i} — {label_for(lc)} / {ld}** {lsev_emoji} `{ls}`")
                if lbl.get("es_falso_positivo_probable") in (True, "true", "True", 1):
                    st.caption("⚠️ Marcado como **falso positivo probable**.")
                st.write(f"  - **Justificación:** {lbl.get('justificacion') or '—'}")
                st.write(f"  - **Evidencia:** {lbl.get('evidencia') or '—'}")
                st.write(f"  - **Marcadores:** {lbl.get('marcadores_detectados') or '—'}")
    else:
        fpp = selected.get("es_falso_positivo_probable", "false")
        if fpp == "true":
            st.warning(
                "⚠️ Marcado como **falso positivo probable** por la categoría 6 (Salvaguarda)."
            )
        with st.expander("📋 Detalle completo del análisis", expanded=False):
            st.markdown(f"**Regla disparada:** `{selected.get('regla_disparada') or '—'}`")
            st.markdown(
                f"**Marcadores detectados:** `{selected.get('marcadores_detectados') or '—'}`"
            )
            st.markdown(f"**Score de ajuste:** `{selected.get('score_ajuste') or '—'}`")
            st.markdown("**Evidencia:**")
            st.write((selected.get("evidencia") or "").strip() or "—")
            st.markdown("**Justificación:**")
            st.write((selected.get("justificacion") or "").strip() or "—")


def render_knowledge_section() -> None:
    """Render the download + collaboration CTA section."""
    st.divider()
    st.header("📚 Conocimiento & Comunidad")

    col_dl, col_gh = st.columns(2)
    knowledge = knowledge_summary()
    zip_bytes = build_knowledge_zip()

    with col_dl:
        st.markdown('<div class="enola-card">', unsafe_allow_html=True)
        st.subheader("📥 Base de conocimiento")
        st.markdown(
            f"**{knowledge['files']} archivos** · **{knowledge['size_bytes'] / 1024:.0f} KB**"
        )
        st.write(
            "Taxonomía canónica de las 6 categorías VDG_*, glosarios de jerga "
            "manosfera y protocolo algorítmico. Descargá el corpus completo para "
            "reproducir el análisis en tu propia instalación."
        )
        st.download_button(
            label="📥 Descargar taxonomía (.zip)",
            data=zip_bytes,
            file_name=knowledge_zip_filename(),
            mime="application/zip",
            type="primary",
            width="stretch",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_gh:
        st.markdown('<div class="enola-card">', unsafe_allow_html=True)
        st.subheader("🐙 Código abierto")
        st.markdown(
            """
            <div class="enola-quote">
                <strong>Tú también podés colaborar: unite, replicá y mejorá el proyecto.</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write(
            "Este proyecto es open source. Abrí un issue, mandá un PR, o fork-ealo "
            "para adaptarlo a tu propia investigación."
        )
        gh1, gh2 = st.columns(2)
        with gh1:
            st.link_button(
                "⭐ Ver repo",
                GITHUB_REPO_URL,
                type="primary",
                width="stretch",
            )
        with gh2:
            st.link_button(
                "🔀 Fork",
                GITHUB_FORK_URL,
                type="secondary",
                width="stretch",
            )
        st.markdown("</div>", unsafe_allow_html=True)


def render_about_section() -> None:
    """Render the methodology + external loader hint."""
    st.divider()
    st.header("🛠️ Sobre la herramienta")

    st.markdown(
        """
        **Pipeline RAG end-to-end:**

        1. **Scraping** de páginas de Facebook con ScrapeGraphAI + Playwright
        2. **Preprocesamiento** del HTML → jerarquía `página → posts → comentarios`
        3. **Embeddings** con Ollama (`nomic-embed-text`) → ChromaDB
        4. **Clasificación** con LLM local (Ollama) y taxonomía cerrada de 6 categorías
        5. **Persistencia** en SQLite para análisis posterior

        La taxonomía se inyecta en el prompt del LLM para garantizar
         homogeneidad: las 6 categorías `VDG_*` son las únicas válidas y el
         catálogo contiene 19 subdimensiones numeradas (1.1–6.3, incluida 4.4).

        """
    )

    with st.expander("🛠️ ¿Querés cargar más conocimiento a la base?"):
        st.markdown(
            """
            El cargador de documentos (Markdown / PDF / TXT) vive en otra
            aplicación Streamlit. Para usarla, abrí una terminal y ejecutá:

            ```bash
            streamlit run src/ui/app.py
            ```
            """
        )
        st.caption("Te queda abierta en una pestaña aparte en `http://localhost:8501`.")


def render_contact_footer() -> None:
    """Render the contact / credits footer."""
    st.divider()

    if UGR_LOGO_PATH.exists():
        ugr_col, txt_col = st.columns([1, 9])
        with ugr_col:
            st.image(str(UGR_LOGO_PATH), width=80)
        with txt_col:
            st.markdown("### 🎓 TFM — Universidad de Granada")
            st.caption(
                "Trabajo Final de Máster en detección de violencia de género digital "
                "con RAG. Máster Interuniversitario en Cultura de Paz, Conflictos, "
                "Educación y Derechos Humanos, Universidad de Granada."
            )

    st.markdown("### ✉️ Contacto y créditos")
    st.markdown(
        f"""
        - **Email:** [{CONTACT_EMAIL}](mailto:{CONTACT_EMAIL})
        - **Repositorio:** [github.com/investigador/tfm-violencia-genero]({GITHUB_REPO_URL})
        - **TFM 2026** — Detección de violencia de género digital con RAG
        - **Stack:** Python 3.12 · Streamlit · Ollama · ChromaDB · LangChain · SQLite
        """
    )
    st.caption("Inspirado en Enola Holmes, la detective en pro de la justicia.")


def render_powered_by_footer() -> None:
    """Render a small 'powered by' credit at the very bottom of the page."""
    st.markdown(
        """
        <div style="text-align: center; font-size: 0.75rem; color: #888; margin-top: 2rem;">
            Powered by <a href="https://danialva.com" target="_blank" style="color: #888;">danialva.com</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    content_type = render_sidebar()
    render_hero()

    stats, raw_analysis, posts, pages = load_data()

    # Build the *adjusted* dataset by merging raw analysis with the
    # latest human feedback. All KPIs / charts below operate on this
    # merged view so the public dashboard reflects the reviewed truth.
    from src.storage import get_database as get_sqlite_db

    db = get_sqlite_db()
    feedback_rows = db.list_feedback()
    analysis = build_adjusted_analysis(raw_analysis, feedback_rows)
    adjustment = compute_adjustment_breakdown(analysis)
    validation = compute_validation_breakdown(analysis)

    kpis = compute_kpis(stats, analysis, knowledge_summary())
    render_kpis(kpis, adjustment, validation)

    render_reliability_banner(analysis)

    st.divider()
    st.header("📈 Resultados del análisis (ajustados)")
    adj_pct = adjustment.get("adjusted_pct", 0.0)
    val_pct = validation.get("validated_pct", 0.0)
    aut_pct = validation.get("pending_pct", 100.0)
    st.caption(
        f"Mostrando: **{ {'all': 'todos', 'post': 'posts', 'comment': 'comentarios'}[content_type] }** · "
        f"Categoría más frecuente con violencia: **{kpis['top_category']}** · "
        f"Validado por humanos: **{val_pct}%** ({adj_pct}% corregido) · "
        f"Autónomo: **{aut_pct}%**"
    )
    render_chart_tabs(analysis)

    render_descriptive_statistics(analysis, posts)

    render_reliability_metrics_section(analysis)

    render_inspector(analysis, posts, [])
    render_knowledge_section()
    render_about_section()
    render_contact_footer()
    render_powered_by_footer()


main()
