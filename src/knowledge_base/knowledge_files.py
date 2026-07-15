"""Servicio de gestión de archivos Markdown del directorio ``knowledge/``.

Usado por la UI NiceGUI para listar, leer, crear, editar y borrar los
``.md`` que componen la base de conocimiento canónica del proyecto.
Expone una API pequeña con validación de rutas (*path-traversal safe*):

* :func:`list_markdown_files` — árbol relativo del directorio ``knowledge/``.
* :func:`read_markdown_file` — contenido UTF-8 + metadatos.
* :func:`write_markdown_file` — alta/edición con backup automático.
* :func:`create_markdown_file` — alta con validación de unicidad.
* :func:`delete_markdown_file` — baja con confirmación previa.

Todos los métodos validan que la ruta resuelta caiga dentro del
directorio ``knowledge/`` raíz para impedir *path traversal*
(``..``/``~``/enlaces simbólicos fuera del árbol).
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Directorio raíz de la base de conocimiento (relativo al proyecto).
DEFAULT_KNOWLEDGE_ROOT = Path("knowledge")

# Tope blando para el contenido editable — protege la UI de cargas
# accidentales (logs binarios, JSONs enormes). Coincide con el límite
# histórico del upload de Streamlit (20 MB).
MAX_FILE_BYTES = 20 * 1024 * 1024

# Backup rotativo conservado junto al archivo original: ``foo.md`` →
# ``foo.md.bak``. Solo se conserva el último snapshot.
_BACKUP_SUFFIX = ".bak"

# Patrón de nombre seguro para archivos nuevos: letras, dígitos,
# guiones, puntos, subguión ``_``. Sin espacios ni acentos para evitar
# problemas de URL/encoding. Mínimo 1 carácter antes de la extensión.
_VALID_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.md$")


@dataclass(frozen=True)
class MarkdownEntry:
    """Metadatos de un archivo ``.md`` dentro de ``knowledge/``."""

    rel_path: str  # ruta POSIX relativa al root (p.ej. ``glosario/jerga.md``)
    abs_path: Path  # ruta absoluta resuelta
    size_bytes: int
    modified_at: str  # ISO 8601


class KnowledgeFileError(ValueError):
    """Error de validación del servicio de archivos de conocimiento."""


def _resolve_root(root: Path | str | None) -> Path:
    """Resolver el directorio raíz y verificar que exista."""
    base = Path(root) if root is not None else DEFAULT_KNOWLEDGE_ROOT
    base = base.resolve()
    if not base.exists():
        raise KnowledgeFileError(f"El directorio raíz '{base}' no existe.")
    if not base.is_dir():
        raise KnowledgeFileError(f"La ruta raíz '{base}' no es un directorio.")
    return base


def _validate_within(root: Path, target: Path) -> None:
    """Asegurar que ``target`` está dentro de ``root`` (path-traversal)."""
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise KnowledgeFileError(f"Ruta fuera del directorio de conocimiento: {target}") from exc


def _to_relative(root: Path, path: Path) -> str:
    """Devolver la ruta como string POSIX relativo al root."""
    return path.relative_to(root).as_posix()


def _validate_filename(name: str) -> str:
    """Validar que ``name`` sea un nombre de archivo Markdown seguro."""
    if not name or not isinstance(name, str):
        raise KnowledgeFileError("El nombre del archivo es obligatorio.")
    if "/" in name or "\\" in name:
        raise KnowledgeFileError("El nombre no puede contener separadores.")
    if name.startswith("."):
        raise KnowledgeFileError("El nombre no puede empezar con punto.")
    if not _VALID_NAME_RE.match(name):
        raise KnowledgeFileError(
            f"Nombre inválido '{name}'. Usá letras, dígitos, "
            "guiones, puntos o subguión, y terminá en '.md'."
        )
    return name


def _resolve_target(root: Path, rel: str) -> Path:
    """Resolver ``rel`` dentro de ``root`` y validar que no escape."""
    if not rel or not isinstance(rel, str):
        raise KnowledgeFileError("La ruta relativa es obligatoria.")
    # Normalizar separadores a POSIX.
    posix_rel = rel.replace("\\", "/").strip("/")
    candidate = (root / posix_rel).resolve()
    _validate_within(root, candidate)
    return candidate


def list_markdown_files(root: Path | str | None = None) -> list[MarkdownEntry]:
    """Listar todos los archivos ``.md`` del árbol ``knowledge/``.

    Retorna una lista ordenada por ruta relativa. Los archivos de backup
    (``*.md.bak``) se ignoran.
    """
    base = _resolve_root(root)
    entries: list[MarkdownEntry] = []
    for path in sorted(base.rglob("*.md")):
        if path.name.endswith(_BACKUP_SUFFIX):
            continue
        try:
            stat = path.stat()
        except OSError as exc:
            logger.warning("No se pudo leer stat de %s: %s", path, exc)
            continue
        entries.append(
            MarkdownEntry(
                rel_path=_to_relative(base, path),
                abs_path=path,
                size_bytes=int(stat.st_size),
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            )
        )
    return entries


def _is_markdown(rel: str) -> bool:
    return rel.lower().endswith(".md") and not rel.endswith(_BACKUP_SUFFIX)


def read_markdown_file(rel_path: str, root: Path | str | None = None) -> str:
    """Leer el contenido UTF-8 de un archivo ``.md`` validado."""
    base = _resolve_root(root)
    if not _is_markdown(rel_path):
        raise KnowledgeFileError(f"Solo se admiten archivos .md (recibido: '{rel_path}').")
    target = _resolve_target(base, rel_path)
    if not target.exists():
        raise KnowledgeFileError(f"Archivo inexistente: '{rel_path}'.")
    if not target.is_file():
        raise KnowledgeFileError(f"La ruta '{rel_path}' no es un archivo.")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise KnowledgeFileError(f"El archivo '{rel_path}' no es UTF-8 válido: {exc}") from exc
    return content


def _atomic_write(target: Path, content: str) -> None:
    """Escribir ``content`` en ``target`` de forma atómica (tmp + rename)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(target)


def _backup_existing(target: Path) -> None:
    """Crear un backup ``.bak`` del archivo previo (idempotente)."""
    if not target.exists():
        return
    backup = target.with_name(target.name + _BACKUP_SUFFIX)
    try:
        shutil.copy2(target, backup)
    except OSError as exc:
        logger.warning("No se pudo crear backup %s: %s", backup, exc)


def write_markdown_file(
    rel_path: str,
    content: str,
    root: Path | str | None = None,
    *,
    create_backup: bool = True,
) -> MarkdownEntry:
    """Editar (o crear) un archivo ``.md`` validado.

    Crea un ``.bak`` rotativo del contenido previo por seguridad.
    Devuelve la :class:`MarkdownEntry` actualizada.
    """
    base = _resolve_root(root)
    if not _is_markdown(rel_path):
        raise KnowledgeFileError(f"Solo se admiten archivos .md (recibido: '{rel_path}').")
    if not isinstance(content, str):
        raise KnowledgeFileError("El contenido debe ser texto UTF-8.")
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise KnowledgeFileError(
            f"El contenido excede el límite de {MAX_FILE_BYTES // (1024 * 1024)} MB."
        )

    target = _resolve_target(base, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if create_backup and target.exists():
        _backup_existing(target)

    _atomic_write(target, content)

    stat = target.stat()
    logger.info("Markdown escrito: %s (%d bytes)", rel_path, stat.st_size)
    return MarkdownEntry(
        rel_path=_to_relative(base, target),
        abs_path=target,
        size_bytes=int(stat.st_size),
        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    )


def create_markdown_file(
    rel_path: str,
    content: str,
    root: Path | str | None = None,
) -> MarkdownEntry:
    """Crear un archivo ``.md`` nuevo.

    ``rel_path`` puede ser un nombre simple (``foo.md``) o una ruta
    relativa (``glosario/nuevo.md``). Las carpetas intermedias se crean
    automáticamente. Falla si el archivo ya existe.
    """
    base = _resolve_root(root)
    posix_rel = rel_path.replace("\\", "/").strip("/")
    if posix_rel.endswith(".md"):
        # Ruta con subcarpetas: validar cada segmento de carpeta.
        parts = posix_rel.split("/")
        filename = parts[-1]
        _validate_filename(filename)
        for folder in parts[:-1]:
            if not folder or folder in (".", ".."):
                raise KnowledgeFileError(f"Subcarpeta inválida: '{folder}'.")
    else:
        # Solo nombre → exigir .md.
        _validate_filename(posix_rel)

    target = _resolve_target(base, posix_rel)
    if target.exists():
        raise KnowledgeFileError(f"Ya existe un archivo en '{posix_rel}'.")
    return write_markdown_file(posix_rel, content, root=base, create_backup=False)


def delete_markdown_file(rel_path: str, root: Path | str | None = None) -> bool:
    """Borrar un archivo ``.md``. Devuelve ``True`` si eliminó."""
    base = _resolve_root(root)
    if not _is_markdown(rel_path):
        raise KnowledgeFileError(f"Solo se admiten archivos .md (recibido: '{rel_path}').")
    target = _resolve_target(base, rel_path)
    if not target.exists():
        return False
    if not target.is_file():
        raise KnowledgeFileError(f"La ruta '{rel_path}' no es un archivo.")
    target.unlink()
    # Limpiar backup huérfano si quedó.
    backup = target.with_name(target.name + _BACKUP_SUFFIX)
    backup.unlink(missing_ok=True)
    logger.info("Markdown borrado: %s", rel_path)
    return True


def compute_summary(root: Path | str | None = None) -> dict[str, int | list[str]]:
    """Resumen agregado: cantidad de archivos y lista de subcarpetas."""
    entries = list_markdown_files(root)
    folders: set[str] = set()
    for entry in entries:
        parent = entry.abs_path.parent
        try:
            parent.relative_to(_resolve_root(root))
            folders.add(str(parent.relative_to(_resolve_root(root)).as_posix()))
        except (ValueError, KnowledgeFileError):
            pass
    return {
        "files": len(entries),
        "size_bytes": sum(e.size_bytes for e in entries),
        "folders": sorted(folders),
    }


__all__ = [
    "DEFAULT_KNOWLEDGE_ROOT",
    "KnowledgeFileError",
    "MarkdownEntry",
    "MAX_FILE_BYTES",
    "compute_summary",
    "create_markdown_file",
    "delete_markdown_file",
    "list_markdown_files",
    "read_markdown_file",
    "write_markdown_file",
]
