# src/knowledge_base/__main__.py
"""CLI entry point for knowledge-base operations.

Usage::

    python -m src.knowledge_base stats
    python -m src.knowledge_base discover-categories
    python -m src.knowledge_base discover-categories --no-llm --diff-with-enum
    python -m src.knowledge_base discover-categories --n-results 50 \\
        --query "hostigamiento sexista categorías" --out data/taxonomy.json
    python -m src.knowledge_base reingest \\
        --source /home/ronin/Downloads/Documentos/CATEGORIAS\\ TFM\\ CONSOLIDADO.md
    python -m src.knowledge_base add --source /path/to/nuevo.md
    python -m src.knowledge_base add --source /path/to/nuevo.md --tags "jurisprudencia,2024"
    python -m src.knowledge_base add --source /path/to/nuevo.md --replace
    python -m src.knowledge_base add-dir --source-dir /path/to/knowledge/
    python -m src.knowledge_base delete-collection
    python -m src.knowledge_base delete-source --source "CATEGORIAS TFM CONSOLIDADO.md"
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when invoked as a module
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.analyzer.llm_client import OllamaClient  # noqa: E402
from src.config.settings import get_settings  # noqa: E402
from src.knowledge_base.discovery import (  # noqa: E402
    DEFAULT_DISCOVERY_QUERY,
    diff_with_legacy_enum,
    discover_categories,
    render_discovery_report,
)
from src.knowledge_base.text_processor import process_text  # noqa: E402
from src.knowledge_base.vector_store import VectorStoreManager, get_vector_store  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_MARCO_PATH = "/home/ronin/Downloads/Documentos/CATEGORIAS TFM CONSOLIDADO.md"


def _build_vector_store() -> VectorStoreManager:
    settings = get_settings()
    return get_vector_store(
        persist_directory=settings.knowledge_base.persist_directory,
        collection_name=settings.knowledge_base.collection_name,
    )


def _build_llm_client() -> OllamaClient:
    settings = get_settings()
    return OllamaClient(
        base_url=settings.ollama.base_url,
        model=settings.ollama.llm_model,
        temperature=settings.analyzer.temperature,
        timeout=settings.ollama.timeout,
    )


def cmd_stats(_args: argparse.Namespace) -> None:
    """Print vector store collection stats."""
    vs = _build_vector_store()
    vs.create_collection()
    stats = vs.get_collection_stats()
    print("=" * 50)
    print("CHROMADB COLLECTION")
    print("=" * 50)
    print(f"  Nombre:     {stats['name']}")
    print(f"  Documentos: {stats['count']}")
    print("=" * 50)


def cmd_delete_collection(args: argparse.Namespace) -> None:
    """Drop the entire ChromaDB collection (USE WITH CARE)."""
    vs = _build_vector_store()
    vs.create_collection()
    before = vs.get_collection_stats()
    print(f"Antes:  {before['count']} documentos en '{before['name']}'")

    if not args.yes:
        confirm = input(
            f"¿Borrar TODA la colección '{before['name']}'? Escribí 'si' para confirmar: "
        )
        if confirm.strip().lower() not in {"si", "sí", "s", "yes", "y"}:
            print("Cancelado.")
            return

    vs.delete_collection()
    print(f"✓ Colección '{before['name']}' eliminada.")
    print("  (se recreará vacía en el próximo `create_collection`)")


def cmd_delete_source(args: argparse.Namespace) -> None:
    """Delete all chunks whose ``source`` metadata matches a given name.

    Surgical alternative to ``delete-collection``: removes only the chunks
    of one document, leaving the rest of the collection intact.
    """
    vs = _build_vector_store()
    vs.create_collection()

    source = args.source
    print(f"Buscando chunks con source={source!r}...")
    try:
        existing = vs.collection.get(where={"source": source})
    except Exception as e:
        print(f"ERROR al consultar ChromaDB: {e}", file=sys.stderr)
        sys.exit(1)

    ids: list[str] = list(existing.get("ids", [])) if existing else []
    metadatas = existing.get("metadatas", []) if existing else []

    if not ids:
        print(f"No se encontraron chunks con source={source!r}. Nada que borrar.")
        return

    print(f"Encontrados: {len(ids)} chunks")
    if metadatas and isinstance(metadatas[0], dict):
        total_chunks_meta = {m.get("total_chunks") for m in metadatas if m.get("total_chunks")}
        if total_chunks_meta:
            print(f"  (de un total de {max(total_chunks_meta)} chunks del documento)")

    if not args.yes:
        confirm = input(f"¿Borrar {len(ids)} chunks de {source!r}? Escribí 'si' para confirmar: ")
        if confirm.strip().lower() not in {"si", "sí", "s", "yes", "y"}:
            print("Cancelado.")
            return

    vs.collection.delete(ids=ids)
    after = vs.get_collection_stats()
    print(
        f"✓ {len(ids)} chunks de {source!r} eliminados. "
        f"Total en colección: {after['count']} (antes: {after['count'] + len(ids)})"
    )


def cmd_reingest(args: argparse.Namespace) -> None:
    """Re-ingest the theoretical framework into ChromaDB.

    By default operates in **replace mode**: it deletes the existing
    chunks whose ``source`` metadata matches the filename, then
    re-chunks the file and re-adds them. With ``--full`` it drops the
    whole collection first (clean slate).
    """
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"ERROR: no existe el archivo: {source_path}", file=sys.stderr)
        sys.exit(1)

    file_format = source_path.suffix.lstrip(".").lower()
    if file_format not in {"md", "txt"}:
        print(
            f"ERROR: formato no soportado ({file_format}). "
            "Usá .md o .txt (PDF: procesalo con el script save_facebook_session "
            "o el UI de Streamlit).",
            file=sys.stderr,
        )
        sys.exit(1)

    vs = _build_vector_store()
    vs.create_collection()

    before = vs.get_collection_stats()
    print(f"Estado inicial: {before['count']} documentos en '{before['name']}'")
    print(f"Fuente:         {source_path}")
    print(f"Formato:        {file_format}")
    print()

    if args.full:
        print("[--full] Borrando colección completa...")
        vs.delete_collection()
        vs.create_collection()
        print(f"  → colección vacía (count={vs.get_collection_stats()['count']})")
    else:
        print(f"[replace] Borrando chunks existentes con source={source_path.name!r}...")
        try:
            existing = vs.collection.get(where={"source": source_path.name})
            existing_ids = existing.get("ids", []) if existing else []
        except Exception as e:
            logger.warning("No pude listar chunks existentes: %s", e)
            existing_ids = []

        if existing_ids:
            vs.collection.delete(ids=existing_ids)
            print(f"  → {len(existing_ids)} chunks eliminados")
        else:
            print("  → no había chunks previos de esa fuente")

    print()
    print(f"Procesando {source_path.name}...")
    content = source_path.read_text(encoding="utf-8")
    settings = get_settings()
    chunks = process_text(
        content=content,
        source=source_path.name,
        file_format=file_format,
        chunk_size=settings.knowledge_base.chunk_size,
        chunk_overlap=settings.knowledge_base.chunk_overlap,
    )

    if not chunks:
        print("ERROR: process_text devolvió 0 chunks.", file=sys.stderr)
        sys.exit(1)

    print(
        f"  → {len(chunks)} chunks generados "
        f"(chunk_size={settings.knowledge_base.chunk_size}, "
        f"overlap={settings.knowledge_base.chunk_overlap})"
    )

    vs.add_documents(
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )

    after = vs.get_collection_stats()
    print()
    print("=" * 50)
    print("RE-INGEST COMPLETADO")
    print("=" * 50)
    print(f"  Antes:    {before['count']} documentos")
    print(f"  Después:  {after['count']} documentos")
    print(
        f"  Delta:    +{after['count'] - before['count'] + len(existing_ids) if not args.full else after['count']}"
    )
    print("=" * 50)


def cmd_add_dir(args: argparse.Namespace) -> None:
    """Recursively add every .md/.txt file in a directory to ChromaDB."""
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    dir_path = Path(args.source_dir)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"ERROR: no es un directorio válido: {dir_path}", file=sys.stderr)
        sys.exit(1)

    extensions = {".md", ".txt"}
    files = sorted(p for p in dir_path.rglob("*") if p.is_file() and p.suffix.lower() in extensions)
    if not files:
        print(f"ERROR: no se encontraron archivos .md/.txt en {dir_path}", file=sys.stderr)
        sys.exit(1)

    tags_list = [t.strip() for t in (args.tags or "").split(",") if t.strip()]

    print(f"Directorio:  {dir_path}")
    print(f"Archivos:    {len(files)} (.md/.txt)")
    if tags_list:
        print(f"Tags:        {tags_list}")
    print()

    vs = _build_vector_store()
    vs.create_collection()
    before = vs.get_collection_stats()
    print(f"Estado inicial: {before['count']} documentos")
    print()

    settings = get_settings()
    total_added = 0
    total_skipped = 0
    total_replaced = 0
    summary: list[tuple[str, int, str]] = []

    for fp in files:
        source_name = fp.name
        try:
            existing = vs.collection.get(where={"source": source_name})
            existing_ids: list[str] = list(existing.get("ids", [])) if existing else []
        except Exception as e:
            logger.warning("No pude listar chunks de %s: %s", source_name, e)
            existing_ids = []

        if existing_ids and not args.replace:
            print(
                f"  [skip] {source_name} (ya existe, {len(existing_ids)} chunks — "
                f"usá --replace para sobrescribir)"
            )
            total_skipped += 1
            summary.append((source_name, 0, "skipped"))
            continue

        if existing_ids and args.replace:
            vs.collection.delete(ids=existing_ids)
            total_replaced += len(existing_ids)

        content = fp.read_text(encoding="utf-8")
        file_format = fp.suffix.lstrip(".").lower()
        chunks = process_text(
            content=content,
            source=source_name,
            file_format=file_format,
            chunk_size=settings.knowledge_base.chunk_size,
            chunk_overlap=settings.knowledge_base.chunk_overlap,
        )

        if not chunks:
            print(f"  [warn] {source_name} — 0 chunks generados, skipping")
            total_skipped += 1
            summary.append((source_name, 0, "empty"))
            continue

        if tags_list:
            for c in chunks:
                c["metadata"]["tags"] = ",".join(tags_list)

        vs.add_documents(
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        total_added += len(chunks)
        action = "replaced" if existing_ids else "added"
        print(f"  [ok]   {source_name} → {len(chunks)} chunks ({action})")
        summary.append((source_name, len(chunks), action))

    after = vs.get_collection_stats()
    print()
    print("=" * 60)
    print("ADD-DIR COMPLETADO")
    print("=" * 60)
    print(f"  Archivos procesados:  {len(files)}")
    print(f"  Chunks agregados:     {total_added}")
    print(f"  Chunks reemplazados:  {total_replaced}")
    print(f"  Archivos omitidos:    {total_skipped}")
    print(f"  Antes:                {before['count']} documentos")
    print(f"  Después:              {after['count']} documentos")
    print("=" * 60)


def cmd_add(args: argparse.Namespace) -> None:
    """Add a new document to ChromaDB (append, no replace)."""
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"ERROR: no existe el archivo: {source_path}", file=sys.stderr)
        sys.exit(1)
    if not source_path.is_file():
        print(f"ERROR: no es un archivo: {source_path}", file=sys.stderr)
        sys.exit(1)

    file_format = source_path.suffix.lstrip(".").lower()
    if file_format not in {"md", "txt"}:
        print(
            f"ERROR: formato no soportado ({file_format}). "
            "Usá .md o .txt (PDF: usá el UI de Streamlit).",
            file=sys.stderr,
        )
        sys.exit(1)

    source_name = source_path.name
    tags_list = [t.strip() for t in (args.tags or "").split(",") if t.strip()]

    vs = _build_vector_store()
    vs.create_collection()

    before = vs.get_collection_stats()
    print(f"Estado inicial:    {before['count']} documentos en '{before['name']}'")
    print(f"Fuente a agregar:  {source_path}")
    print(f"Formato:           {file_format}")
    if tags_list:
        print(f"Tags:              {tags_list}")
    print()

    print("Verificando si la fuente ya existe...")
    try:
        existing = vs.collection.get(where={"source": source_name})
        existing_ids: list[str] = list(existing.get("ids", [])) if existing else []
    except Exception as e:
        logger.warning("No pude listar chunks existentes: %s", e)
        existing_ids = []

    if existing_ids and not args.replace:
        print(
            f"ERROR: ya existen {len(existing_ids)} chunks con source={source_name!r}.\n"
            "       Usá --replace para sobrescribirlos, o --source con otro archivo.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif existing_ids and args.replace:
        print(f"[--replace] Borrando {len(existing_ids)} chunks previos de '{source_name}'...")
        vs.collection.delete(ids=existing_ids)

    print()
    print(f"Procesando {source_name}...")
    content = source_path.read_text(encoding="utf-8")
    settings = get_settings()
    chunks = process_text(
        content=content,
        source=source_name,
        file_format=file_format,
        chunk_size=settings.knowledge_base.chunk_size,
        chunk_overlap=settings.knowledge_base.chunk_overlap,
    )

    if not chunks:
        print("ERROR: process_text devolvió 0 chunks.", file=sys.stderr)
        sys.exit(1)

    if tags_list:
        for c in chunks:
            c["metadata"]["tags"] = ",".join(tags_list)

    print(
        f"  → {len(chunks)} chunks generados "
        f"(chunk_size={settings.knowledge_base.chunk_size}, "
        f"overlap={settings.knowledge_base.chunk_overlap})"
    )

    vs.add_documents(
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )

    after = vs.get_collection_stats()
    print()
    print("=" * 50)
    print("ADD COMPLETADO")
    print("=" * 50)
    print(f"  Fuente agregada:  {source_name}")
    print(f"  Chunks agregados: {len(chunks)}")
    print(f"  Antes:            {before['count']} documentos")
    print(f"  Después:          {after['count']} documentos")
    print("=" * 50)


def cmd_discover_categories(args: argparse.Namespace) -> None:  # noqa: C901
    """Discover the categories of digital gender violence in ChromaDB."""
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    vs = _build_vector_store()
    vs.create_collection()

    llm_client = None
    if not args.no_llm:
        llm_client = _build_llm_client()
        print(f"Usando LLM: {llm_client.model}")
    else:
        print("Modo retrieval-only (sin LLM).")

    query = args.query or DEFAULT_DISCOVERY_QUERY
    print(f"Query umbrella: {query!r}")
    print(f"n_results: {args.n_results}")
    print()

    result = asyncio.run(
        discover_categories(
            vector_store=vs,
            llm_client=llm_client,
            n_results=args.n_results,
            query=query,
        )
    )

    diff = None
    if args.diff_with_enum:
        taxonomy = result.get("taxonomy")
        diff = diff_with_legacy_enum(taxonomy)

    report = render_discovery_report(result, diff=diff)
    print(report)
    print()

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": result.get("mode"),
            "n_results": result.get("n_results"),
            "chunks": result.get("chunks", []),
            "taxonomy": result.get("taxonomy"),
            "diff": diff,
        }
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Resultado guardado en: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Knowledge base operations for TFM Violencia de Género"
    )
    parser.add_argument("--log-level", default="INFO", help="Log level (DEBUG, INFO, etc.)")
    subparsers = parser.add_subparsers(dest="command", help="Subcomando")

    sp_stats = subparsers.add_parser("stats", help="Muestra estadísticas de la colección ChromaDB")
    sp_stats.set_defaults(func=cmd_stats)

    sp_disc = subparsers.add_parser(
        "discover-categories",
        help="Descubre la taxonomía de violencia de género digital en ChromaDB",
    )
    sp_disc.add_argument("--n-results", type=int, default=30, help="Cantidad de chunks a recuperar")
    sp_disc.add_argument(
        "--no-llm",
        action="store_true",
        help="Salta la llamada al LLM y devuelve solo los chunks recuperados",
    )
    sp_disc.add_argument("--query", type=str, default=None, help="Query custom (default: umbrella)")
    sp_disc.add_argument("--out", type=Path, default=None, help="Guarda el resultado a un JSON")
    sp_disc.add_argument(
        "--diff-with-enum",
        action="store_true",
        help="Compara la taxonomía descubierta con el enum legacy hardcoded",
    )
    sp_disc.set_defaults(func=cmd_discover_categories)

    sp_reingest = subparsers.add_parser(
        "reingest",
        help="Re-carga el marco teórico en ChromaDB (replace mode por defecto)",
    )
    sp_reingest.add_argument(
        "--source",
        type=str,
        default=DEFAULT_MARCO_PATH,
        help=f"Path al archivo .md/.txt a re-cargar (default: {DEFAULT_MARCO_PATH})",
    )
    sp_reingest.add_argument(
        "--full",
        action="store_true",
        help="Borra TODA la colección antes de re-cargar (clean slate)",
    )
    sp_reingest.set_defaults(func=cmd_reingest)

    sp_add = subparsers.add_parser(
        "add",
        help="Agrega un documento NUEVO a ChromaDB (append, no reemplaza)",
    )
    sp_add.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path al archivo .md/.txt a agregar",
    )
    sp_add.add_argument(
        "--tags",
        type=str,
        default=None,
        help="Tags separados por coma, opcionales (ej: 'jurisprudencia,2024')",
    )
    sp_add.add_argument(
        "--replace",
        action="store_true",
        help="Si el source ya existe, borra los chunks previos antes de agregar",
    )
    sp_add.set_defaults(func=cmd_add)

    sp_add_dir = subparsers.add_parser(
        "add-dir",
        help="Agrega recursivamente todos los .md/.txt de un directorio",
    )
    sp_add_dir.add_argument(
        "--source-dir",
        type=str,
        required=True,
        help="Path al directorio a procesar (recursivo)",
    )
    sp_add_dir.add_argument(
        "--tags",
        type=str,
        default=None,
        help="Tags separados por coma, opcionales",
    )
    sp_add_dir.add_argument(
        "--replace",
        action="store_true",
        help="Sobrescribir sources que ya existan",
    )
    sp_add_dir.set_defaults(func=cmd_add_dir)

    sp_delete = subparsers.add_parser(
        "delete-collection",
        help="Borra TODA la colección ChromaDB (irreversible, pide confirmación)",
    )
    sp_delete.add_argument(
        "--yes",
        action="store_true",
        help="Saltea la confirmación interactiva",
    )
    sp_delete.set_defaults(func=cmd_delete_collection)

    sp_delete_src = subparsers.add_parser(
        "delete-source",
        help="Borra los chunks cuyo 'source' metadata coincide con un nombre",
    )
    sp_delete_src.add_argument(
        "--source",
        type=str,
        required=True,
        help="Nombre del source a borrar (ej: 'CATEGORIAS TFM CONSOLIDADO.md')",
    )
    sp_delete_src.add_argument(
        "--yes",
        action="store_true",
        help="Saltea la confirmación interactiva",
    )
    sp_delete_src.set_defaults(func=cmd_delete_source)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
