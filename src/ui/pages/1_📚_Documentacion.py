"""Sub-página de documentación — renderiza el README, SPEC y la taxonomía."""  # noqa: N999

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.ui.utils import (  # noqa: E402
    CATEGORIA_LABELS,
    GITHUB_FORK_URL,
    GITHUB_REPO_URL,
    LOGO_PATH,
    README_PATH,
    SPEC_PATH,
)

st.set_page_config(
    page_title="Documentación — Enola Investigadora Digital",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_sidebar() -> None:
    """Render the shared sidebar with logo + page navigation."""
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
        st.link_button("⭐ Ver repo en GitHub", GITHUB_REPO_URL, width="stretch")
        st.link_button(
            "🔀 Fork en GitHub",
            GITHUB_FORK_URL,
            width="stretch",
            type="secondary",
        )


def read_text(path: Path) -> str:
    """Read a UTF-8 text file or return a friendly fallback."""
    if not path.exists():
        return f"_(Archivo no encontrado: `{path.name}`)_"
    return path.read_text(encoding="utf-8")


def render_taxonomy_section() -> None:
    """Render the 6 canonical categories with one-line descriptions."""
    st.subheader("🗂️ Las 6 categorías canónicas")
    st.markdown(
        """
        La taxonomía de **Enola** es **cerrada y homogénea**: el LLM solo puede
        elegir entre estas 6 categorías (códigos `VDG_*`), cada una con 3
        subdimensiones numeradas. La tabla completa se inyecta en el prompt
        del clasificador para garantizar homogeneidad.
        """
    )

    rows: list[dict[str, str]] = [
        {
            "Código": "VDG_VIOLENCIA_SIMBOLICA",
            "Nombre": CATEGORIA_LABELS["VDG_VIOLENCIA_SIMBOLICA"],
            "Subdims": "1.1 Roles tradicionales y sumisión · 1.2 Incompetencia e inferioridad · 1.3 Castigo moral y patologización",
            "Gravedad": "baja-media",
        },
        {
            "Código": "VDG_COSIFICACION_SLUTSHAMING",
            "Nombre": CATEGORIA_LABELS["VDG_COSIFICACION_SLUTSHAMING"],
            "Subdims": "2.1 Cosificación e hipersexualización · 2.2 Body-shaming · 2.3 Doble estándar sexual y slut-shaming",
            "Gravedad": "media",
        },
        {
            "Código": "VDG_HOSTILIDAD_FEMINICIDIO",
            "Nombre": CATEGORIA_LABELS["VDG_HOSTILIDAD_FEMINICIDIO"],
            "Subdims": "3.1 Castigos disciplinantes · 3.2 Deseos de violencia letal · 3.3 Apología al feminicidio",
            "Gravedad": "alta-extrema",
        },
        {
            "Código": "VDG_MANOSFERA_ANTIFEMINISMO",
            "Nombre": CATEGORIA_LABELS["VDG_MANOSFERA_ANTIFEMINISMO"],
            "Subdims": "4.1 Subculturas y jerarquías · 4.2 Oposición antifeminista y victimismo hegemónico · 4.3 Trolleo y emasculación · 4.4 Arquetipos deshumanizantes",
            "Gravedad": "media-alta",
        },
        {
            "Código": "VDG_DESACREDITACION_ACTIVISTAS",
            "Nombre": CATEGORIA_LABELS["VDG_DESACREDITACION_ACTIVISTAS"],
            "Subdims": "5.1 Deslegitimación · 5.2 Ridiculización tradicional · 5.3 Superioridad moral",
            "Gravedad": "media-alta",
        },
        {
            "Código": "VDG_SALVAGUARDA_FALSO_POSITIVO",
            "Nombre": CATEGORIA_LABELS["VDG_SALVAGUARDA_FALSO_POSITIVO"],
            "Subdims": "6.1 Micromachismos y mansplaining · 6.2 Humor hostil · 6.3 Salvaguarda y falsos positivos",
            "Gravedad": "ortogonal (flag de salvaguarda)",
        },
    ]

    for row in rows:
        with st.container(border=True):
            st.markdown(f"### `{row['Código']}` — {row['Nombre']}")
            st.markdown(f"**Subdimensiones:** {row['Subdims']}")
            st.caption(f"Gravedad típica: *{row['Gravedad']}*")


def render_contribute_section() -> None:
    """Render a 'how to contribute' section."""
    st.subheader("🤝 Cómo contribuir")
    st.markdown(
        """
        1. **Fork-eá** el repositorio desde el botón en la sidebar.
        2. **Cloná** tu fork y configurá el entorno:
           ```bash
           python -m venv .venv
           source .venv/bin/activate
           pip install -e ".[dev]"
           playwright install chromium
           ```
        3. **Corré los tests** antes de proponer cambios:
           ```bash
           pytest
           ruff check --fix .
           ruff format .
           ```
        4. **Abrí un PR** con una descripción clara del cambio y referencia
           al issue asociado.
        5. **Sumá conocimiento** a la base: el cargador vive en otra app
           Streamlit (`streamlit run src/ui/app.py`) — ahí podés subir PDFs,
           Markdown o TXT con marcos teóricos sobre violencia de género
           digital.

        ---

        **Principios del proyecto:**

        - 🌍 **Castellano argentino** (voseo) en todo el código, prompts, fixtures
          y UI. Sin localismos forzados, pero sin tuteur español.
        - 🔬 **Rigor académico**: cada categoría cita fuentes teóricas
          (ley 26.485, Butler, Bourdieu, conexiones con el protocolo
          algorítmico).
         - 🛡️ **Salvaguarda contra falsos positivos**: categoría 6 ortogonal
           para micromachismos, humor hostil y cita/denuncia.

        - 🧩 **Homogeneidad**: la taxonomía es cerrada, no abierta. El LLM
          nunca "inventa" categorías.
        """
    )


def main() -> None:
    render_sidebar()

    st.title("📚 Documentación — Enola Investigadora Digital")
    st.markdown(
        """
        Acá vas a encontrar el detalle del proyecto: la arquitectura del
        pipeline, la taxonomía canónica, y cómo replicar o contribuir al
        proyecto.
        """
    )

    tab_overview, tab_readme, tab_spec, tab_tax, tab_help = st.tabs(
        ["🚀 Overview", "📖 README", "📐 SPEC", "🗂️ Taxonomía", "🤝 Contribuir"]
    )

    with tab_overview:
        st.markdown(
            """
            ## ¿Qué es Enola?

            **Enola Investigadora Digital** es un sistema RAG (Retrieval-Augmented
            Generation) que detecta violencia de género digital en Facebook.
            Como su homónima, la detective **Enola Holmes**, esta herramienta
            investiga con rigor y en pro de la justicia social: analiza
            conversaciones en redes sociales y las clasifica con una taxonomía
             cerrada de 6 categorías y 19 subdimensiones, asistida por un LLM

            local (Ollama) y una base vectorial de conocimiento teórico
            (ChromaDB).

            ## Componentes principales

            | Componente | Responsabilidad |
            |---|---|
            | **Scraper** | Login Facebook + extracción de posts y comentarios (Playwright) |
            | **Storage** | Persistencia jerárquica en SQLite (página → posts → comments) |
            | **Knowledge base** | Marco teórico vectorizado en ChromaDB (RAG) |
            | **Analyzer** | Clasificador RAG con Ollama + fallback rule-based |
            | **Pipeline** | Orquestación end-to-end (scraping → análisis → reporte) |
            | **UI** | Inspección, carga de conocimiento y reportes visuales (Streamlit) |

            ## Stack tecnológico

            - **Python 3.12** · **Streamlit 1.30+** · **Ollama** (LLM local)
            - **ChromaDB** (vector store) · **LangChain** (orquestación RAG)
            - **SQLAlchemy 2.0** (SQLite) · **Playwright** (scraping)
            - **Pytest** + **Ruff** + **Mypy** (testing y calidad)
            """
        )

    with tab_readme:
        st.caption(f"Renderizado desde `{README_PATH.relative_to(_project_root)}`")
        st.markdown(read_text(README_PATH))

    with tab_spec:
        st.caption(f"Renderizado desde `{SPEC_PATH.relative_to(_project_root)}`")
        st.markdown(read_text(SPEC_PATH))

    with tab_tax:
        render_taxonomy_section()

    with tab_help:
        render_contribute_section()

    st.divider()
    st.page_link("landing.py", label="← Volver al inicio", icon="🏠")


main()
