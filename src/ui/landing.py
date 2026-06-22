"""Landing page — Enola Investigadora Digital.

Streamlit entry point for the project's public dashboard. Shows KPIs,
violent vs non-violent breakdown, per-category distribution and a
content inspector backed by the SQLite analysis database.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

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
                canónica de 6 categorías y 18 subdimensiones, asistida por Ollama y ChromaDB.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(kpis: dict[str, object]) -> None:
    """Render the four headline KPI cards."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📄 Análisis totales", kpis["total"])
    col2.metric("🚨 % con violencia", f"{kpis['violent_pct']}%", help="Del total analizado")
    col3.metric(
        "📚 Categorías canónicas",
        kpis["categories"],
        help="Taxonomía cerrada VDG_*",
    )
    col4.metric("🗄️ Páginas scrapeadas", kpis["pages"])


def render_chart_tabs(results: list[dict]) -> None:
    """Render the pie + bar charts inside a post/comment/all tab."""
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
                with st.expander("Ver tabla con valores"):
                    st.dataframe(
                        bar_df[["Categoría", "Cantidad", "Porcentaje"]],
                        width="stretch",
                        hide_index=True,
                    )


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
    fpp = selected.get("es_falso_positivo_probable", "false")
    marcadores = selected.get("marcadores_detectados") or "—"
    evidencia = (selected.get("evidencia") or "").strip() or "—"
    justificacion = (selected.get("justificacion") or "").strip() or "—"

    sev_emoji = {"baja": "🟢", "media": "🟡", "alta": "🔴", "ninguna": "⚪"}.get(sev, "⚪")
    tiene_emoji = "🚨" if tiene == "true" else "✅"

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Violencia", f"{tiene_emoji} {tiene}")
    col_b.metric("Categoría", label_for(cat))
    col_c.metric("Dimensión", dim)
    col_d.metric("Severidad", f"{sev_emoji} {sev}")

    if fpp == "true":
        st.warning("⚠️ Marcado como **falso positivo probable** por la categoría 5 (Salvaguarda).")

    with st.expander("📋 Detalle completo del análisis", expanded=False):
        st.markdown(f"**Regla disparada:** `{selected.get('regla_disparada') or '—'}`")
        st.markdown(f"**Marcadores detectados:** `{marcadores}`")
        st.markdown(f"**Score de ajuste:** `{selected.get('score_ajuste') or '—'}`")
        st.markdown("**Evidencia:**")
        st.write(evidencia)
        st.markdown("**Justificación:**")
        st.write(justificacion)


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
        homogeneidad: las 6 categorías `VDG_*` son las únicas válidas y cada
        una tiene 3 subdimensiones numeradas (1.1–6.3).
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

    stats, analysis, posts, pages = load_data()
    kpis = compute_kpis(stats, analysis, knowledge_summary())
    render_kpis(kpis)

    st.divider()
    st.header("📈 Resultados del análisis")
    st.caption(
        f"Mostrando: **{ {'all': 'todos', 'post': 'posts', 'comment': 'comentarios'}[content_type] }** · "
        f"Categoría más frecuente con violencia: **{kpis['top_category']}**"
    )
    render_chart_tabs(analysis)

    render_inspector(analysis, posts, [])
    render_knowledge_section()
    render_about_section()
    render_contact_footer()
    render_powered_by_footer()


main()
