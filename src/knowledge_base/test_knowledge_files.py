"""Unit tests for :mod:`src.knowledge_base.knowledge_files`.

Cubren el ciclo CRUD completo + las validaciones de seguridad
(path-traversal, nombres inválidos, contenido excesivo).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.knowledge_base import knowledge_files as kf
from src.knowledge_base.knowledge_files import (
    KnowledgeFileError,
    MarkdownEntry,
    compute_summary,
    create_markdown_file,
    delete_markdown_file,
    list_markdown_files,
    read_markdown_file,
    write_markdown_file,
)


@pytest.fixture
def knowledge_root(tmp_path: Path) -> Path:
    """Crea un árbol ``knowledge/`` sintético para los tests."""
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "README.md").write_text("# raíz\n", encoding="utf-8")
    glosario = root / "glosario"
    glosario.mkdir()
    (glosario / "manosfera.md").write_text(
        "# manosfera\n\nDefinición operativa.\n", encoding="utf-8"
    )
    (glosario / "leetspeak.md").write_text(
        "# leetspeak\n\nTabla de conversión.\n", encoding="utf-8"
    )
    nested = root / "categorias" / "vdg1"
    nested.mkdir(parents=True)
    (nested / "definicion.md").write_text("## VDG1\nCuerpo del documento.\n", encoding="utf-8")
    return root


class TestListMarkdownFiles:
    def test_returns_all_markdown_files(self, knowledge_root: Path) -> None:
        entries = list_markdown_files(knowledge_root)
        rel_paths = sorted(e.rel_path for e in entries)
        assert rel_paths == [
            "README.md",
            "categorias/vdg1/definicion.md",
            "glosario/leetspeak.md",
            "glosario/manosfera.md",
        ]

    def test_includes_size_and_modified(self, knowledge_root: Path) -> None:
        entries = list_markdown_files(knowledge_root)
        assert all(e.size_bytes > 0 for e in entries)
        assert all("T" in e.modified_at or " " in e.modified_at for e in entries)

    def test_ignores_backup_files(self, knowledge_root: Path) -> None:
        (knowledge_root / "README.md.bak").write_text("snapshot", encoding="utf-8")
        entries = list_markdown_files(knowledge_root)
        rel_paths = [e.rel_path for e in entries]
        assert "README.md.bak" not in rel_paths

    def test_empty_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        assert list_markdown_files(root) == []

    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            list_markdown_files(tmp_path / "does_not_exist")


class TestReadMarkdownFile:
    def test_reads_existing(self, knowledge_root: Path) -> None:
        content = read_markdown_file("glosario/manosfera.md", knowledge_root)
        assert "Definición operativa" in content

    def test_reads_nested(self, knowledge_root: Path) -> None:
        content = read_markdown_file("categorias/vdg1/definicion.md", knowledge_root)
        assert "VDG1" in content

    def test_nonexistent_raises(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            read_markdown_file("no-existe.md", knowledge_root)

    def test_rejects_non_markdown(self, knowledge_root: Path) -> None:
        (knowledge_root / "foo.txt").write_text("hola", encoding="utf-8")
        with pytest.raises(KnowledgeFileError):
            read_markdown_file("foo.txt", knowledge_root)

    def test_path_traversal_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            read_markdown_file("../secrets.md", knowledge_root)
        with pytest.raises(KnowledgeFileError):
            read_markdown_file("../../etc/passwd.md", knowledge_root)

    def test_absolute_path_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            read_markdown_file(str(knowledge_root / "README.md"), knowledge_root)

    def test_empty_rel_path_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            read_markdown_file("", knowledge_root)


class TestWriteMarkdownFile:
    def test_create_new(self, knowledge_root: Path) -> None:
        entry = write_markdown_file("nuevo.md", "# Nuevo\n", knowledge_root, create_backup=False)
        assert entry.rel_path == "nuevo.md"
        assert (knowledge_root / "nuevo.md").exists()
        assert "Nuevo" in (knowledge_root / "nuevo.md").read_text(encoding="utf-8")

    def test_overwrite_creates_backup(self, knowledge_root: Path) -> None:
        original = (knowledge_root / "README.md").read_text(encoding="utf-8")
        write_markdown_file("README.md", "# reemplazado\n", knowledge_root, create_backup=True)
        backup = knowledge_root / "README.md.bak"
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == original

    def test_overwrite_without_backup(self, knowledge_root: Path) -> None:
        write_markdown_file("README.md", "# reemplazado\n", knowledge_root, create_backup=False)
        assert not (knowledge_root / "README.md.bak").exists()
        assert "reemplazado" in (knowledge_root / "README.md").read_text(encoding="utf-8")

    def test_creates_parent_dirs(self, knowledge_root: Path) -> None:
        entry = write_markdown_file(
            "nuevo/path/doc.md",
            "hola",
            knowledge_root,
            create_backup=False,
        )
        assert entry.rel_path == "nuevo/path/doc.md"
        assert (knowledge_root / "nuevo" / "path" / "doc.md").exists()

    def test_path_traversal_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            write_markdown_file("../escaped.md", "x", knowledge_root)
        with pytest.raises(KnowledgeFileError):
            write_markdown_file("foo/../../escaped.md", "x", knowledge_root)

    def test_size_limit_enforced(self, knowledge_root: Path) -> None:
        huge = "x" * (kf.MAX_FILE_BYTES + 1)
        with pytest.raises(KnowledgeFileError):
            write_markdown_file("huge.md", huge, knowledge_root, create_backup=False)

    def test_non_string_content_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            write_markdown_file("foo.md", 12345, knowledge_root)  # type: ignore[arg-type]


class TestCreateMarkdownFile:
    def test_create_simple(self, knowledge_root: Path) -> None:
        entry = create_markdown_file("nuevo.md", "contenido", knowledge_root)
        assert isinstance(entry, MarkdownEntry)
        assert entry.rel_path == "nuevo.md"
        assert (knowledge_root / "nuevo.md").exists()

    def test_create_with_subdir(self, knowledge_root: Path) -> None:
        entry = create_markdown_file("glosario/nuevo-termino.md", "definición", knowledge_root)
        assert entry.rel_path == "glosario/nuevo-termino.md"
        assert (knowledge_root / "glosario" / "nuevo-termino.md").exists()

    def test_existing_file_raises(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            create_markdown_file("README.md", "duplicado", knowledge_root)

    def test_invalid_name_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            create_markdown_file("foo bar.md", "x", knowledge_root)
        with pytest.raises(KnowledgeFileError):
            create_markdown_file("foo", "x", knowledge_root)
        with pytest.raises(KnowledgeFileError):
            create_markdown_file(".hidden.md", "x", knowledge_root)

    def test_path_traversal_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            create_markdown_file("../escape.md", "x", knowledge_root)


class TestDeleteMarkdownFile:
    def test_delete_existing(self, knowledge_root: Path) -> None:
        assert delete_markdown_file("README.md", knowledge_root) is True
        assert not (knowledge_root / "README.md").exists()

    def test_delete_cleans_backup(self, knowledge_root: Path) -> None:
        (knowledge_root / "README.md.bak").write_text("snap", encoding="utf-8")
        delete_markdown_file("README.md", knowledge_root)
        assert not (knowledge_root / "README.md.bak").exists()

    def test_delete_nonexistent_returns_false(self, knowledge_root: Path) -> None:
        assert delete_markdown_file("no.md", knowledge_root) is False

    def test_path_traversal_rejected(self, knowledge_root: Path) -> None:
        with pytest.raises(KnowledgeFileError):
            delete_markdown_file("../important.md", knowledge_root)


class TestComputeSummary:
    def test_returns_files_and_folders(self, knowledge_root: Path) -> None:
        summary: dict = compute_summary(knowledge_root)
        assert summary["files"] == 4
        assert "glosario" in summary["folders"]
        assert "categorias/vdg1" in summary["folders"]
        assert summary["size_bytes"] > 0

    def test_empty_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        summary: dict = compute_summary(root)
        assert summary["files"] == 0
        assert summary["size_bytes"] == 0
        assert summary["folders"] == []


class TestAtomicRoundTrip:
    """Garantiza que leer/escribir/borrar de forma consecutiva funciona."""

    def test_full_crud_cycle(self, knowledge_root: Path) -> None:
        create_markdown_file("ciclo.md", "estado 1", knowledge_root)
        assert read_markdown_file("ciclo.md", knowledge_root) == "estado 1"

        write_markdown_file("ciclo.md", "estado 2", knowledge_root, create_backup=True)
        assert read_markdown_file("ciclo.md", knowledge_root) == "estado 2"
        backup = knowledge_root / "ciclo.md.bak"
        assert backup.read_text(encoding="utf-8") == "estado 1"

        assert delete_markdown_file("ciclo.md", knowledge_root) is True
        assert not (knowledge_root / "ciclo.md").exists()
        assert not backup.exists()
