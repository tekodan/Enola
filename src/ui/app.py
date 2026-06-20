"""Streamlit app — Upload markdown/PDF documents to ChromaDB."""

import sys
import tempfile
from pathlib import Path

import streamlit as st

# Ensure project root is on sys.path so "from src" works
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Redirigir a la landing page si no hay parámetro de ruta
if not st.query_params:
    st.switch_page("src/ui/landing.py")

from src.analyzer.batch_analyzer import BatchAnalyzer  # noqa: E402
from src.config.settings import get_settings  # noqa: E402
from src.knowledge_base.pdf_processor import PDFProcessor  # noqa: E402
from src.knowledge_base.text_processor import process_text  # noqa: E402
from src.knowledge_base.vector_store import get_vector_store  # noqa: E402
from src.storage import get_database as get_sqlite_db  # noqa: E402

st.set_page_config(
    page_title="Cargar conocimiento — TFM Violencia de Género",
    page_icon="📚",
    layout="wide",
)

settings = get_settings()
vector_store = get_vector_store(
    persist_directory=settings.knowledge_base.persist_directory,
    collection_name=settings.knowledge_base.collection_name,
)
chunk_size = settings.knowledge_base.chunk_size
chunk_overlap = settings.knowledge_base.chunk_overlap

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf"}
MAX_FILE_SIZE_MB = 20


def get_collection_count() -> int:
    try:
        vector_store.create_collection()
        stats = vector_store.get_collection_stats()
        return int(stats["count"])
    except Exception:
        return 0


def reset_vector_store() -> bool:
    try:
        vector_store.create_collection()
        vector_store.delete_collection()
        st.session_state["collection_count"] = 0
        return True
    except Exception as e:
        st.error(f"Error al borrar la colección: {e}")
        return False


st.title("📚 Base de conocimiento — ChromaDB")

st.markdown(
    """
Subí archivos **Markdown (.md)**, **PDF (.pdf)** o **texto plano (.txt)**
con contenido sobre violencia de género para poblar la base de conocimiento
vectorial. El clasificador RAG usará estos documentos como contexto.
"""
)

# ------ Sidebar stats ------
with st.sidebar:
    st.header("📊 Estado de ChromaDB")

    if "collection_count" not in st.session_state:
        st.session_state["collection_count"] = get_collection_count()

    col_count = st.session_state["collection_count"]
    st.metric("Documentos en colección", col_count)

    st.divider()

    st.caption("Configuración activa")
    st.code(
        f"Chunk size: {chunk_size}\n"
        f"Overlap: {chunk_overlap}\n"
        f"Colección: {settings.knowledge_base.collection_name}\n"
        f"Persistencia: {settings.knowledge_base.persist_directory}",
        language="text",
    )

    st.divider()

    if st.button("🗑️ Vaciar colección", type="secondary", width="stretch"):
        if reset_vector_store():
            st.success("Colección borrada")
            st.rerun()

    # ------ Database stats ------
    st.divider()
    st.header("🗄️ Base de datos SQLite")

    try:
        db = get_sqlite_db()
        db_stats = db.get_stats()
        st.metric("Páginas", db_stats["pages_count"])
        st.metric("Posts", db_stats["posts_count"])
        st.metric("Comments", db_stats["comments_count"])
        st.metric("Análisis", db_stats["analysis_results_count"])
    except Exception:
        pass

# ------ Main tabs ------
tab_upload, tab_explore, tab_reports = st.tabs(
    ["📤 Cargar documentos", "🔍 Explorar base", "📊 Reportes"]
)

# ===== TAB 1: Upload =====
with tab_upload:
    uploaded_files = st.file_uploader(
        "Seleccioná uno o más archivos",
        type=list(ALLOWED_EXTENSIONS),
        accept_multiple_files=True,
        help=f"Archivos permitidos: {', '.join(ALLOWED_EXTENSIONS)}. "
        f"Máximo {MAX_FILE_SIZE_MB} MB por archivo.",
    )

    if not uploaded_files:
        st.info("Subí archivos .md, .txt o .pdf para comenzar.")
        st.stop()

    # ------ File validation ------
    valid_files = []
    errors = []

    for f in uploaded_files:
        ext = Path(f.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"'{f.name}' — extensión no soportada ({ext})")
            continue
        if f.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            errors.append(
                f"'{f.name}' — demasiado grande "
                f"({f.size / 1024 / 1024:.1f} MB, límite {MAX_FILE_SIZE_MB} MB)"
            )
            continue
        valid_files.append(f)

    if errors:
        for err in errors:
            st.warning(err)

    if not valid_files:
        st.stop()

    # ------ Upload mode ------
    col1, col2 = st.columns([2, 1])
    with col1:
        replace_mode = st.checkbox(
            "Reemplazar documentos existentes",
            value=False,
            help="Si está activo, borra los documentos con el mismo nombre antes de insertar.",
        )
    with col2:
        tags_input = st.text_input(
            "Tags (opcional, separados por coma)",
            placeholder="ley, violencia, psicológica",
        )

    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []

    st.divider()

    # ------ Preview ------
    with st.expander("📄 Vista previa de archivos", expanded=len(valid_files) <= 3):
        for f in valid_files:
            st.markdown(f"**{f.name}** ({f.size / 1024:.1f} KB)")
            content = f.getvalue().decode("utf-8", errors="replace")
            if f.name.endswith(".md"):
                preview = content[:500]
            else:
                preview = content[:500]
            st.code(preview, language="text" if not f.name.endswith(".md") else "markdown")
            st.caption(f"Primeros {len(preview)} caracteres — {len(content)} total")
            st.divider()

    # ------ Upload button ------
    total_chunks = 0
    total_files = len(valid_files)

    if st.button("🚀 Subir a ChromaDB", type="primary", width="stretch"):
        progress_bar = st.progress(0, text="Iniciando...")
        status_text = st.empty()
        all_chunks_added = 0

        for idx, f in enumerate(valid_files):
            fname = f.name
            ext = Path(fname).suffix.lower()
            status_text.text(f"Procesando {fname} ({idx + 1}/{total_files})...")

            # Replace mode: delete existing documents with same source
            if replace_mode:
                try:
                    vector_store.create_collection()
                    if vector_store.collection:
                        existing_ids = vector_store.collection.get(where={"source": fname})["ids"]
                        if existing_ids:
                            vector_store.collection.delete(ids=existing_ids)
                            status_text.text(
                                f"Reemplazando {len(existing_ids)} chunks previos de '{fname}'..."
                            )
                except Exception:
                    pass

            if ext == ".pdf":
                # Save PDF to temp file, process, delete
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(f.getvalue())
                    tmp_path = tmp.name

                try:
                    pdf_proc = PDFProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                    docs = pdf_proc.process_document(tmp_path, source_name=fname)
                except Exception as e:
                    st.error(f"Error procesando PDF '{fname}': {e}")
                    docs = []
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
            else:
                raw = f.getvalue().decode("utf-8", errors="replace")
                fmt = "md" if ext == ".md" else "txt"
                docs = process_text(
                    content=raw,
                    source=fname,
                    file_format=fmt,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )

            if not docs:
                st.warning(f"'{fname}' no generó chunks (vacío o sin texto extraíble).")
                progress_bar.progress((idx + 1) / total_files)
                continue

            # Add tags to metadata
            if tags:
                for doc in docs:
                    doc["metadata"]["tags"] = ",".join(tags)

            texts = [d["text"] for d in docs]
            metadatas = [d["metadata"] for d in docs]

            try:
                vector_store.create_collection()
                vector_store.add_documents(
                    documents=texts,
                    metadatas=metadatas,
                )
                all_chunks_added += len(docs)
                progress_bar.progress((idx + 1) / total_files)
            except Exception as e:
                st.error(f"Error al subir '{fname}' a ChromaDB: {e}")

        # Finalize
        progress_bar.empty()
        status_text.empty()

        st.session_state["collection_count"] = get_collection_count()

        if all_chunks_added > 0:
            st.success(
                f"✅ {all_chunks_added} chunks de {total_files} archivos agregados a ChromaDB."
            )
        else:
            st.warning("No se agregó ningún chunk.")

        with st.expander("📋 Resumen de la operación", expanded=True):
            st.json(
                {
                    "archivos_procesados": total_files,
                    "chunks_agregados": all_chunks_added,
                    "modo": "reemplazar" if replace_mode else "agregar",
                    "tags": tags if tags else "ninguno",
                    "total_coleccion": st.session_state["collection_count"],
                }
            )

# ===== TAB 2: Explore =====
with tab_explore:
    st.subheader("🔍 Contenido de ChromaDB")

    col_count = st.session_state["collection_count"]

    if col_count == 0:
        st.info("La colección está vacía. Subí documentos desde la pestaña anterior.")
        st.stop()

    st.metric("Total documentos en colección", col_count)

    # Search
    st.divider()
    query = st.text_input(
        "Buscar en la base de conocimiento",
        placeholder="Ej: violencia psicológica, ley 26485, tipos de violencia...",
    )

    n_results = st.slider("Resultados a mostrar", 1, 20, 5)

    if query:
        try:
            vector_store.create_collection()
            results = vector_store.search(query, n_results=n_results)

            if not results:
                st.warning("Sin resultados.")
            else:
                st.success(f"Se encontraron {len(results)} resultados")

                for i, r in enumerate(results):
                    with st.expander(
                        f"#{i + 1} — {r['metadata'].get('source', 'desconocido')} "
                        f"(distancia: {r['distance']:.4f})"
                    ):
                        st.markdown(r["text"])
                        st.caption(f"ID: {r['id']}")
                        st.json(r["metadata"])
        except Exception as e:
            st.error(f"Error al buscar: {e}")
    else:
        # Show random sample
        st.divider()
        st.subheader("Muestra aleatoria")

        try:
            vector_store.create_collection()
            if vector_store.collection and vector_store.collection.count() > 0:
                sample = vector_store.collection.get(limit=5)
                for i in range(len(sample["ids"])):
                    with st.expander(f"Documento {sample['ids'][i]}"):
                        text = sample["documents"][i]
                        st.markdown(text)
                        meta = sample["metadatas"][i]
                        st.caption(f"Metadata: {meta}")
            else:
                st.info("No hay documentos para mostrar.")
        except Exception as e:
            st.error(f"Error al obtener muestra: {e}")

    # Sources list
    st.divider()
    if st.button("📋 Listar fuentes", width="stretch"):
        try:
            vector_store.create_collection()
            if vector_store.collection:
                all_data = vector_store.collection.get()
                sources = {}
                for meta in all_data["metadatas"]:
                    src = meta.get("source", "desconocido")
                    sources[src] = sources.get(src, 0) + 1

                st.json(dict(sorted(sources.items())))
        except Exception as e:
            st.error(f"Error: {e}")

# ===== TAB 3: Reports =====
with tab_reports:
    st.subheader("📊 Reporte de análisis")

    db = get_sqlite_db()
    db_stats = db.get_stats()
    analysis = db.get_analysis_results()

    col1, col2, col3 = st.columns(3)
    col1.metric("Posts analizados", db_stats["analysis_results_count"])
    col2.metric(
        "Posts con violencia", len([a for a in analysis if a.get("tiene_violencia") == "true"])
    )
    col3.metric("Comments analizados", db_stats["comments_count"])

    st.divider()

    if db_stats["analysis_results_count"] == 0:
        st.warning(
            "No hay resultados de análisis. Ejecutá el análisis batch desde el botón de abajo."
        )
    else:
        # Filters
        filter_type = st.selectbox(
            "Filtrar por tipo",
            ["Todos", "post", "comment"],
        )
        filter_violence = st.selectbox(
            "Filtrar por violencia",
            ["Todos", "Con violencia", "Sin violencia"],
        )

        filtered = analysis
        if filter_type != "Todos":
            filtered = [a for a in filtered if a.get("content_type") == filter_type]
        if filter_violence == "Con violencia":
            filtered = [a for a in filtered if a.get("tiene_violencia") == "true"]
        elif filter_violence == "Sin violencia":
            filtered = [a for a in filtered if a.get("tiene_violencia") == "false"]

        if filtered:
            st.dataframe(
                [
                    {
                        "ID": a.get("content_id", "")[:16],
                        "Tipo": a.get("content_type", ""),
                        "Violencia": a.get("tiene_violencia", ""),
                        "Categoría": a.get("categoria", ""),
                        "Dimensión": a.get("dimension", "") or "",
                        "Código": a.get("codigo", "") or "",
                        "Severidad": a.get("severidad", ""),
                        "Evidencia": a.get("evidencia", "")[:50],
                    }
                    for a in filtered
                ],
                width="stretch",
            )

            # Group by category
            st.divider()
            st.subheader("Distribución por categoría de violencia (taxonomía ChromaDB)")

            from collections import Counter

            categorias = Counter(
                a.get("categoria")
                for a in analysis
                if a.get("tiene_violencia") == "true" and a.get("categoria")
            )
            if categorias:
                st.bar_chart(categorias)
            else:
                st.info("No se detectaron categorías de violencia específicas.")
        else:
            st.info("Sin resultados con los filtros seleccionados.")

    st.divider()

    # Batch analysis button
    st.subheader("Análisis batch")

    col_a, col_b = st.columns(2)
    with col_a:
        reanalyze = st.checkbox(
            "Re-analizar existentes",
            value=False,
            help="Si está activo, analiza todo de nuevo (incluso lo ya analizado).",
        )
    with col_b:
        posts_only = st.checkbox(
            "Solo posts",
            value=False,
            help="Si está activo, analiza solo posts, sin comentarios.",
        )

    if st.button("🚀 Ejecutar análisis batch", type="primary", width="stretch"):
        with st.spinner("Analizando contenido..."):
            try:
                analyzer = BatchAnalyzer(
                    database=db,
                    reanalyze_existing=reanalyze,
                    analyze_comments=not posts_only,
                )
                stats = analyzer.analyze_all()
                st.success(
                    f"Análisis completado: {stats.posts_analyzed} posts, "
                    f"{stats.comments_analyzed} comments, "
                    f"{stats.violence_detected_posts + stats.violence_detected_comments} con violencia "
                    f"({stats.execution_time_seconds:.1f}s)"
                )
                if stats.errors:
                    st.warning(f"{stats.errors} errores durante el análisis")
                st.rerun()
            except Exception as e:
                st.error(f"Error en análisis batch: {e}")
