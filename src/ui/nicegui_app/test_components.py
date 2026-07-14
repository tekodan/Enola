"""Static-analysis tests for shared UI components.

Catches the kind of bug where a helper like ``section_header`` is
called with the wrong number of arguments. Without these tests,
malformed calls only surface when a user navigates to a specific
page — exactly what happened with ``ia.py`` shipping a 1-arg call.
"""

from __future__ import annotations

import ast
import glob


def _find_calls(tree: ast.AST, target: str) -> list[ast.Call]:
    """Return all ``target(...)`` calls inside ``tree``."""
    out: list[ast.Call] = []

    class _V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == target:
                out.append(node)
            self.generic_visit(node)

    _V().visit(tree)
    return out


class TestSectionHeaderSignature:
    """Every ``section_header`` call must pass at least 2 positional args."""

    def test_all_section_header_calls_pass_eyebrow_and_title(self):
        issues: list[str] = []
        for path in glob.glob("src/ui/nicegui_app/pages/*.py"):
            with open(path) as f:
                tree = ast.parse(f.read())
            for node in _find_calls(tree, "section_header"):
                posargs = node.args
                kwargs = {kw.arg for kw in node.keywords}
                # Required: eyebrow, title (both positional). subtitle is kw-only.
                if len(posargs) < 2 and "title" not in kwargs and "eyebrow" not in kwargs:
                    issues.append(f"{path}:{node.lineno} — {ast.unparse(node)}")
        assert not issues, "Malformed section_header() calls:\n" + "\n".join(issues)


class TestPageScaffoldSignature:
    """Every ``page_scaffold`` must include ``current_path`` so the drawer
    can highlight the active link."""

    def test_page_scaffold_calls_have_current_path(self):
        issues: list[str] = []
        for path in glob.glob("src/ui/nicegui_app/pages/*.py"):
            with open(path) as f:
                tree = ast.parse(f.read())
            for node in _find_calls(tree, "page_scaffold"):
                kwargs = {kw.arg for kw in node.keywords}
                if "current_path" not in kwargs:
                    issues.append(f"{path}:{node.lineno} — {ast.unparse(node)}")
        assert not issues, "page_scaffold() calls missing current_path:\n" + "\n".join(issues)


class TestNiceGuiApiUsage:
    """Catch calls to NiceGUI symbols that don't exist in 3.6.

    These bugs only surface at runtime when the page renders — and
    they break pages silently with ``AttributeError``. Static checks
    catch them at test time.
    """

    # Symbols that DON'T exist on ``nicegui.ui``. Use the documented
    # alternative instead.
    _FORBIDDEN: dict[str, str] = {
        "expander": "expansion",
    }

    def test_no_forbidden_nicegui_calls(self):
        # Import the real ui so we can check existence.
        from nicegui import ui as real_ui

        missing = set(self._FORBIDDEN)
        for name, alt in self._FORBIDDEN.items():
            assert not hasattr(real_ui, name), (
                f"FORBIDDEN list says ui.{name} is missing, but it actually exists. "
                f"Update the test list to reflect reality."
            )

        issues: list[str] = []
        for path in glob.glob("src/ui/nicegui_app/pages/*.py"):
            with open(path) as f:
                tree = ast.parse(f.read())
            for node in _find_calls(tree, "ui"):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Attribute) and func.attr in missing:
                        alt = self._FORBIDDEN[func.attr]
                        issues.append(
                            f"{path}:{node.lineno} uses ui.{func.attr}() → use ui.{alt}() instead"
                        )
        assert not issues, "Forbidden NiceGUI calls found:\n" + "\n".join(issues)
