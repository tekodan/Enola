"""Streamlit app — Upload markdown/PDF documents to ChromaDB."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure project root is on sys.path so "from src" works
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.analyzer.batch_analyzer import BatchAnalyzer  # noqa: E402
from src.analyzer.category_mapping import MAX_LABELS  # noqa: E402
from src.config.settings import get_settings  # noqa: E402
from src.knowledge_base.feedback_store import (  # noqa: E402
    FeedbackStore,
    get_feedback_store,
)
from src.knowledge_base.pdf_processor import PDFProcessor  # noqa: E402
from src.knowledge_base.text_processor import process_text  # noqa: E402
from src.knowledge_base.vector_store import get_vector_store  # noqa: E402
from src.storage import get_database as get_sqlite_db  # noqa: E402
from src.ui.adjusted_report import (  # noqa: E402
    join_feedback_with_analysis,
)
from src.ui.validacion import (  # noqa: E402
    build_feedback_payload,
    categoria_choices,
    dimension_options_for,
    feedback_status_label,
    filter_analysis_for_validation,
    is_valid_categoria_for_dimension,
)

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
tab_upload, tab_explore, tab_reports, tab_validacion = st.tabs(
    ["📤 Cargar documentos", "🔍 Explorar base", "📊 Reportes", "✅ Validación"]
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
                        "Subdimensión": a.get("dimension", "") or "",
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

    # === Sub-section: Análisis corregidos (raw view + export) ===
    st.divider()
    st.subheader("📋 Análisis corregidos (vista cruda)")
    st.caption(
        "Comparativa lado a lado entre la salida cruda de la IA y la corrección "
        "(si existe) validada por un humano. Esta es la **vista cruda** — la "
        "versión ajustada se muestra en el landing (Enola)."
    )

    fb_raw_rows = db.list_feedback()
    fb_joined = db.get_feedback_joined_with_analysis()
    rows_for_report = join_feedback_with_analysis(fb_joined)

    if not rows_for_report:
        st.info("Todavía no hay revisiones. Cargá correcciones desde el tab ✅ Validación.")
    else:
        # Filters
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
        with col_f1:
            fb_filter_type = st.selectbox(
                "Tipo",
                options=["Todos", "post", "comment"],
                key="rpt_fb_type",
            )
        with col_f2:
            fb_filter_agrees = st.selectbox(
                "Decisión",
                options=["Todos", "De acuerdo", "Corregido"],
                key="rpt_fb_agrees",
            )
        with col_f3:
            fb_filter_indexed = st.selectbox(
                "Estado ChromaDB",
                options=["Todos", "Indexado", "Pendiente"],
                key="rpt_fb_indexed",
            )

        filtered_rows = rows_for_report
        if fb_filter_type != "Todos":
            filtered_rows = [r for r in filtered_rows if r.get("content_type") == fb_filter_type]
        if fb_filter_agrees == "De acuerdo":
            filtered_rows = [r for r in filtered_rows if r.get("agrees") == "true"]
        elif fb_filter_agrees == "Corregido":
            filtered_rows = [r for r in filtered_rows if r.get("agrees") == "false"]
        if fb_filter_indexed == "Indexado":
            filtered_rows = [r for r in filtered_rows if r.get("indexed_in_chromadb") == "true"]
        elif fb_filter_indexed == "Pendiente":
            filtered_rows = [r for r in filtered_rows if r.get("indexed_in_chromadb") == "false"]

        if filtered_rows:
            df_compare = pd.DataFrame(
                [
                    {
                        "Tipo": r.get("content_type"),
                        "ID": str(r.get("content_id") or "")[:18],
                        "Decisión": "✅ De acuerdo"
                        if r.get("agrees") == "true"
                        else "❌ Corregido",
                        "Cat. IA": str(r.get("original_categoria") or "—"),
                        "Cat. Humano": str(r.get("corrected_categoria") or "—"),
                        "Dim. IA": str(r.get("original_dimension") or "—"),
                        "Dim. Humano": str(r.get("corrected_dimension") or "—"),
                        "ChromaDB": "🟢" if r.get("indexed_in_chromadb") == "true" else "🟡",
                    }
                    for r in filtered_rows
                ]
            )
            st.dataframe(df_compare, width="stretch", hide_index=True)

            # Per-row expandable detail
            with st.expander(f"🔍 Detalle completo ({len(filtered_rows)} filas)", expanded=False):
                for r in filtered_rows[:50]:
                    st.markdown(
                        f"**[{r.get('content_type')}/{r.get('content_id')}]** — "
                        f"`{r.get('analysis_id')}`"
                    )
                    st.markdown(f"&nbsp;&nbsp;📝 Texto: *{r.get('text_snapshot') or ''}*")
                    st.markdown(
                        f"&nbsp;&nbsp;🤖 IA: `{r.get('original_categoria') or '—'}` / "
                        f"`{r.get('original_dimension') or '—'}` — *"
                        f"{r.get('original_justificacion') or '—'}*"
                    )
                    st.markdown(
                        f"&nbsp;&nbsp;🧑 Humano: `{r.get('corrected_categoria') or '—'}` / "
                        f"`{r.get('corrected_dimension') or '—'}` — *"
                        f"{r.get('corrected_justificacion') or '—'}*"
                    )
                    if r.get("reason"):
                        st.markdown(f"&nbsp;&nbsp;💬 Motivo: {r.get('reason')}")
                    st.divider()

            # Export buttons
            st.divider()
            col_dl1, col_dl2, _ = st.columns([2, 2, 4])
            with col_dl1:
                csv_bytes = df_compare.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Descargar CSV",
                    data=csv_bytes,
                    file_name="analisis_corregidos.csv",
                    mime="text/csv",
                    key="rpt_fb_csv",
                )
            with col_dl2:
                json_bytes = json.dumps(
                    filtered_rows, ensure_ascii=False, indent=2, default=str
                ).encode("utf-8")
                st.download_button(
                    "⬇️ Descargar JSON",
                    data=json_bytes,
                    file_name="analisis_corregidos.json",
                    mime="application/json",
                    key="rpt_fb_json",
                )
        else:
            st.info("Sin filas para los filtros seleccionados.")

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


# ===== TAB 4: Validación =====
with tab_validacion:
    # Migrated to the NiceGUI dashboard — feature flag controls fallback.
    if not os.environ.get("ENOLA_SHOW_DEPRECATED_TAB"):
        st.warning(
            "⚠️ Esta pestaña migró a la app NiceGUI en `/validacion` "
            "(login + ChromaDB + trazabilidad por usuario).\n\n"
            f"Abrí **{settings.app.nicegui_url}/validacion** en otra pestaña "
            "para revisar y corregir análisis. Necesitás un usuario — "
            "pedíselo al administrador (`python -m src.cli users add ...`)."
        )
        st.stop()

    st.subheader("✅ Validación humana de análisis (DEPRECATED — usar NiceGUI)")
    st.caption(
        "Este formulario queda accesible sólo con "
        "`ENOLA_SHOW_DEPRECATED_TAB=true`. La versión soportada vive en "
        "`python -m src.ui.nicegui_app` → /validacion."
    )

    # ------- Stats header -------
    feedback_count = db_stats.get("feedback_count", 0)
    feedback_agreement = db_stats.get("feedback_agreement_count", 0)
    feedback_disagreement = db_stats.get("feedback_disagreement_count", 0)
    feedback_pending = db_stats.get("feedback_pending_index_count", 0)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📝 Total revisiones", feedback_count)
    k2.metric("✅ De acuerdo", feedback_agreement)
    k3.metric("❌ Corregido", feedback_disagreement)
    k4.metric("⏳ Pendientes de indexar", feedback_pending)

    # ------- ChromaDB feedback panel -------
    st.divider()
    with st.expander("🔧 Colección `feedback_corrections` (ChromaDB)"):
        try:
            fb_store: FeedbackStore = get_feedback_store(
                persist_directory=settings.knowledge_base.persist_directory,
                collection_name=settings.knowledge_base.feedback_collection_name,
            )
            fb_count = fb_store.get_count()
            st.metric("Correcciones indexadas", fb_count)
            if st.button("🚀 Indexar todas las correcciones pendientes", key="btn_index_all"):
                pending = db.list_feedback(only_pending_index=True)
                if not pending:
                    st.info("No hay correcciones pendientes de indexar.")
                else:
                    progress = st.progress(0.0, text="Indexando…")
                    ok = 0
                    for idx, p in enumerate(pending, start=1):
                        try:
                            original_text = p.get("text_snapshot") or db.get_original_text(
                                p.get("content_type") or "post",
                                p.get("content_id") or "",
                            )
                            if not original_text:
                                continue
                            ar_id = p["analysis_result_id"]
                            analysis_row = db.get_analysis_result_by_content(
                                p.get("content_type") or "post",
                                p.get("content_id") or "",
                            )
                            original_cat = (analysis_row or {}).get("categoria")
                            cid = fb_store.add_correction(
                                feedback_id=p["id"],
                                text=original_text,
                                corrected_categoria=p.get("corrected_categoria")
                                or original_cat
                                or "ninguna",
                                corrected_dimension=p.get("corrected_dimension"),
                                corrected_justificacion=p.get("corrected_justificacion")
                                or "Revisado por humano",
                                original_categoria=original_cat,
                                content_type=p.get("content_type") or "post",
                                content_id=p.get("content_id") or "",
                                reason=p.get("reason"),
                                id=p.get("chromadb_id"),
                            )
                            db.mark_feedback_indexed(p["id"], cid)
                            ok += 1
                        except Exception as ex:
                            st.warning(f"Error indexando feedback {p.get('id')}: {ex}")
                        progress.progress(idx / len(pending))
                    progress.empty()
                    st.success(f"✅ {ok} correcciones indexadas en ChromaDB")
                    st.rerun()
        except Exception as e:
            st.error(f"Error accediendo a feedback store: {e}")

    # ------- Filters + table -------
    st.divider()
    st.subheader("Análisis pendientes de revisar")

    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    with col_f1:
        v_content_type = st.selectbox(
            "Tipo",
            options=["all", "post", "comment"],
            format_func={
                "all": "Todos",
                "post": "Posts",
                "comment": "Comments",
            }.get,
            key="v_type",
        )
    with col_f2:
        v_state = st.selectbox(
            "Estado de revisión",
            options=[
                "all",
                "pending",
                "agreed",
                "disagreed",
            ],
            format_func={
                "all": "Todos",
                "pending": "⏳ Pendientes",
                "agreed": "✅ De acuerdo",
                "disagreed": "❌ Corregidos",
            }.get,
            key="v_state",
        )
    with col_f3:
        v_only_violent = st.checkbox(
            "Solo con violencia",
            value=False,
            key="v_only_violent",
        )

    # Refresh button
    if st.button("🔄 Refrescar", width="stretch"):
        st.rerun()

    all_analysis: list[dict[str, object]] = db.get_analysis_results()
    all_fb: list[dict[str, object]] = db.list_feedback()
    filtered = filter_analysis_for_validation(
        all_analysis,
        all_fb,
        content_type=None if v_content_type == "all" else v_content_type,
        review_state=v_state,
        only_violent=v_only_violent,
    )

    if not filtered:
        st.info("No hay análisis con los filtros seleccionados.")
    else:
        st.caption(f"{len(filtered)} filas mostradas")
        for row in filtered:
            with st.expander(
                f"[{row.get('content_type')}] "
                f"{str(row.get('content_id') or '')[:20]} — "
                f"IA: *{row.get('categoria') or '—'}* / "
                f"`{row.get('dimension') or '—'}` — "
                f"{feedback_status_label(row.get('feedback_row') or {})}",
                expanded=False,
            ):
                # ------- Show original text -------
                original_text = row.get("text_snapshot") or db.get_original_text(
                    row.get("content_type") or "post",
                    row.get("content_id") or "",
                )
                if not original_text:
                    original_text = f"(Texto original no disponible — ID {row.get('content_id')})"
                st.markdown("**Texto original:**")
                st.info(original_text[:800] + ("…" if len(original_text) > 800 else ""))

                # ------- Show AI classification -------
                st.markdown("**🤖 Clasificación de la IA:**")
                ai_labels = list(row.get("labels") or [])
                ai_cols = st.columns(4)
                ai_cols[0].markdown(f"**Violencia:** `{row.get('tiene_violencia') or '—'}`")
                ai_cols[1].markdown(f"**Categoría (primaria):** `{row.get('categoria') or '—'}`")
                ai_cols[2].markdown(f"**Subdimensión (primaria):** `{row.get('dimension') or '—'}`")
                ai_cols[3].markdown(f"**Severidad global:** `{row.get('severidad') or '—'}`")
                if ai_labels:
                    with st.expander(
                        f"Etiquetas detectadas ({len(ai_labels)})",
                        expanded=len(ai_labels) > 1,
                    ):
                        for i, lbl in enumerate(ai_labels, start=1):
                            st.markdown(
                                f"**#{i} — {lbl.get('categoria')} / "
                                f"{lbl.get('dimension') or '—'} "
                                f"(sev: {lbl.get('severidad') or '—'})**"
                            )
                            st.write(f"  - Justificación: {lbl.get('justificacion') or '—'}")
                            st.write(f"  - Evidencia: {lbl.get('evidencia') or '—'}")
                            st.write(f"  - Marcadores: {lbl.get('marcadores_detectados') or '—'}")
                else:
                    with st.expander("Justificación / evidencia / marcadores", expanded=False):
                        st.write("**Justificación:**", row.get("justificacion") or "—")
                        st.write("**Evidencia:**", row.get("evidencia") or "—")
                        st.write(
                            "**Marcadores detectados:**",
                            row.get("marcadores_detectados") or "—",
                        )

                st.divider()

                # ------- Feedback form (multi-label) -------
                ar_id = row.get("id")
                existing_fb = row.get("feedback_row") or {}
                existing_fb_labels: list[dict] = list(existing_fb.get("labels") or [])

                # Backwards-compat: if no multi-label rows but flat
                # corrected_* fields are present, synthesize a 1-row list.
                if not existing_fb_labels and existing_fb.get("corrected_categoria"):
                    existing_fb_labels = [
                        {
                            "categoria": existing_fb.get("corrected_categoria"),
                            "dimension": existing_fb.get("corrected_dimension"),
                            "severidad": "media",
                            "justificacion": existing_fb.get("corrected_justificacion") or "",
                        }
                    ]

                st.markdown("**✅ Tu revisión:**")
                with st.form(key=f"fb_form_{ar_id}"):
                    default_agrees = (
                        "yes"
                        if str(existing_fb.get("agrees", "")).lower() == "true"
                        else ("no" if str(existing_fb.get("agrees", "")).lower() == "false" else "")
                    )
                    agrees_choice = st.radio(
                        "¿Coincidís con la IA?",
                        options=["yes", "no"],
                        format_func={"yes": "✅ Sí, coincido", "no": "❌ No, corregir"}.get,
                        index=(
                            0 if default_agrees == "yes" else (1 if default_agrees == "no" else 0)
                        ),
                        key=f"agrees_{ar_id}",
                    )

                    show_corrections = agrees_choice == "no"
                    reason = ""
                    label_rows_widget: list[dict] = []

                    # State initializer: keep the row count in sync with
                    # the existing feedback so edits feel stable across
                    # rerenders. Streamlit forbids changing widget keys
                    # mid-form, so we use a session-state copy that the
                    # add/remove buttons mutate.
                    n_key = f"n_labels_{ar_id}"
                    if n_key not in st.session_state:
                        st.session_state[n_key] = max(1, len(existing_fb_labels))
                    n_labels = st.session_state[n_key]

                    if show_corrections:
                        reason = st.text_input(
                            "¿Por qué no coincidís? (opcional)",
                            value=str(existing_fb.get("reason") or ""),
                            key=f"reason_{ar_id}",
                        )

                        st.caption(
                            f"Edición multi-etiqueta — agregá hasta {MAX_LABELS} "
                            f"categorías que apliquen al texto."
                        )
                        cat_pairs = categoria_choices()

                        for idx in range(n_labels):
                            existing_row = (
                                existing_fb_labels[idx] if idx < len(existing_fb_labels) else {}
                            )
                            with st.expander(
                                f"🏷 Etiqueta {idx + 1}"
                                + (
                                    f" — {existing_row.get('categoria')}"
                                    if existing_row.get("categoria")
                                    else ""
                                ),
                                expanded=True,
                            ):
                                cols_top = st.columns([2, 2])
                                with cols_top[0]:
                                    default_cat_idx = (
                                        list(cat_pairs.keys()).index(existing_row.get("categoria"))
                                        if existing_row.get("categoria") in cat_pairs
                                        else 0
                                    )
                                    cat_choice = st.selectbox(
                                        "Categoría",
                                        options=list(cat_pairs.keys()),
                                        format_func=lambda v: cat_pairs.get(v, "—"),
                                        index=default_cat_idx,
                                        key=f"cat_{ar_id}_{idx}",
                                    )
                                with cols_top[1]:
                                    dim_pairs = dimension_options_for(cat_choice)
                                    default_dim_idx = (
                                        list(dim_pairs.keys()).index(existing_row.get("dimension"))
                                        if existing_row.get("dimension") in dim_pairs
                                        else 0
                                    )
                                    dim_choice = st.selectbox(
                                        "Subdimensión",
                                        options=list(dim_pairs.keys()),
                                        format_func=lambda v: dim_pairs.get(v, "—"),
                                        index=default_dim_idx,
                                        key=f"dim_{ar_id}_{idx}",
                                    )

                                cols_mid = st.columns([1, 3])
                                with cols_mid[0]:
                                    sev_choices = ["baja", "media", "alta", "ninguna"]
                                    default_sev = str(existing_row.get("severidad") or "media")
                                    sev_idx = (
                                        sev_choices.index(default_sev)
                                        if default_sev in sev_choices
                                        else 1
                                    )
                                    sev_choice = st.selectbox(
                                        "Severidad",
                                        options=sev_choices,
                                        index=sev_idx,
                                        key=f"sev_{ar_id}_{idx}",
                                    )
                                with cols_mid[1]:
                                    fpp_choice = st.checkbox(
                                        "Falso positivo probable",
                                        value=bool(existing_row.get("es_falso_positivo_probable")),
                                        key=f"fpp_{ar_id}_{idx}",
                                    )

                                justif = st.text_area(
                                    "Justificación (por qué esta categoría aplica)",
                                    value=str(existing_row.get("justificacion") or ""),
                                    key=f"justif_{ar_id}_{idx}",
                                )
                                evidencia = st.text_area(
                                    "Evidencia (cita del texto)",
                                    value=str(existing_row.get("evidencia") or ""),
                                    key=f"evid_{ar_id}_{idx}",
                                )

                                label_rows_widget.append(
                                    {
                                        "categoria": cat_choice,
                                        "dimension": dim_choice,
                                        "severidad": sev_choice,
                                        "es_falso_positivo_probable": fpp_choice,
                                        "justificacion": justif,
                                        "evidencia": evidencia,
                                    }
                                )

                        add_col, rm_col, _sp = st.columns([1, 1, 4])
                        with add_col:
                            if (
                                st.form_submit_button(
                                    "➕ Agregar etiqueta",
                                    disabled=n_labels >= MAX_LABELS,
                                )
                                and n_labels < MAX_LABELS
                            ):
                                st.session_state[n_key] = n_labels + 1
                                st.rerun()
                        with rm_col:
                            if (
                                st.form_submit_button(
                                    "➖ Quitar última",
                                    disabled=n_labels <= 1,
                                )
                                and n_labels > 1
                            ):
                                st.session_state[n_key] = n_labels - 1
                                st.rerun()

                    reviewer = st.text_input(
                        "Revisor (opcional)",
                        value="",
                        key=f"rev_{ar_id}",
                    )

                    saved_col, indexed_col = st.columns(2)
                    with saved_col:
                        submit_save = st.form_submit_button(
                            "💾 Guardar feedback",
                            type="primary",
                            width="stretch",
                        )
                    with indexed_col:
                        submit_save_index = st.form_submit_button(
                            "💾+🔎 Guardar y enviar a ChromaDB",
                            width="stretch",
                        )

                # ------- Persist -------
                if submit_save or submit_save_index:
                    payload = build_feedback_payload(
                        analysis_result_id=ar_id,
                        content_type=row.get("content_type") or "post",
                        content_id=row.get("content_id") or "",
                        text_snapshot=original_text,
                        agrees=(agrees_choice == "yes"),
                        reason=reason,
                        reviewer=reviewer,
                        corrected_labels=label_rows_widget,
                    )
                    # Cross-row validation: every (categoria, dimension)
                    # must be a valid pair.
                    invalid = False
                    for lbl in payload.get("corrected_labels") or []:
                        if not is_valid_categoria_for_dimension(
                            str(lbl.get("categoria") or ""),
                            str(lbl.get("dimension") or ""),
                        ):
                            invalid = True
                            break
                    if payload["agrees"] == "false" and invalid:
                        st.error(
                            "❌ Alguna etiqueta tiene una dimensión que no "
                            "corresponde a su categoría — revisá antes de "
                            "guardar."
                        )
                    else:
                        try:
                            new_fb_id = db.save_feedback(payload)
                            st.success("✅ Feedback guardado")
                            if submit_save_index and payload["agrees"] == "false":
                                # Push to ChromaDB right away (multi-label aware).
                                try:
                                    cid = fb_store.add_correction(
                                        feedback_id=new_fb_id,
                                        text=original_text,
                                        corrected_categoria=str(
                                            payload.get("corrected_categoria")
                                            or row.get("categoria")
                                            or "ninguna"
                                        ),
                                        corrected_dimension=payload.get("corrected_dimension"),
                                        corrected_justificacion=str(
                                            payload.get("corrected_justificacion")
                                            or "Revisado por humano"
                                        ),
                                        original_categoria=row.get("categoria"),
                                        content_type=row.get("content_type") or "post",
                                        content_id=row.get("content_id") or "",
                                        reason=str(payload.get("reason") or ""),
                                        corrected_labels=list(
                                            payload.get("corrected_labels") or []
                                        ),
                                    )
                                    db.mark_feedback_indexed(new_fb_id, cid)
                                    st.success("🔎 Indexado en ChromaDB")
                                except Exception as ex:
                                    st.warning(f"No se pudo indexar en ChromaDB: {ex}")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ Error guardando feedback: {ex}")
