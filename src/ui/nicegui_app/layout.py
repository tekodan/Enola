"""Shared layout primitives for the Enola NiceGUI app.

Provides the consistent chrome that wraps every page:

* :func:`page_header` — top bar with title, dark-mode toggle and the
  magnifying-glass brand mark.
* :func:`side_drawer` — left navigation drawer with the page links.
* :func:`page_footer` — compact credits footer.
* :func:`page_scaffold` — convenience wrapper that registers the theme,
  mounts the header + drawer, optionally enforces auth, and yields
  control to the caller for the page body.

Auth-gating: pass ``requires_auth=False`` for public pages
(``/login``, ``/inicio``). All other pages default to authenticated
mode — anonymous users are redirected to ``/login``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nicegui import ui

from src.ui.nicegui_app import auth, theme
from src.ui.utils import GITHUB_REPO_URL

# --- Navigation --------------------------------------------------------------


@dataclass(frozen=True)
class NavItem:
    """A single entry in the side drawer."""

    label: str
    icon: str
    path: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("Inicio", "home", "/inicio"),
    NavItem("Estadística", "insights", "/estadistica"),
    NavItem("IA & Confiabilidad", "psychology", "/ia"),
    NavItem("Inspector", "search", "/inspector"),
    NavItem("Conocimiento", "menu_book", "/conocimiento"),
    NavItem("Validación", "task_alt", "/validacion"),
)


# --- Page chrome -------------------------------------------------------------


def page_header(title: str, *, subtitle: str | None = None) -> None:
    """Render the top header bar (brand + title + dark-mode + user menu).

    Adds a user chip when a session user is present: shows the
    ``@username`` + role badge and a *Cerrar sesión* button. Anonymous
    users see a link to ``/login`` instead.
    """
    user = auth.current_user()
    with (
        ui.header(elevated=False)
        .classes("items-center justify-between px-6 py-3")
        .style(
            "background: var(--enola-cream); border-bottom: 1px solid rgba(191, 161, 129, 0.22);"
        )
    ):
        with ui.row().classes("items-center gap-3 no-wrap"):
            with ui.avatar(
                color=theme.PLUM,
                text_color=theme.CREAM,
                size="36px",
            ).classes("shadow-sm"):
                ui.icon("search", size="20px")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-lg font-semibold enola-display").style(
                    "color: var(--enola-charcoal); line-height: 1;"
                )
                if subtitle:
                    ui.label(subtitle).classes("text-xs").style(
                        "color: var(--enola-charcoal-light);"
                    )

        with ui.row().classes("items-center gap-3"):
            ui.link(
                "GitHub",
                GITHUB_REPO_URL,
                new_tab=True,
            ).classes("text-sm").style("color: var(--enola-plum);")

            # Dark-mode toggle — NiceGUI persists the choice per-session.
            ui.dark_mode(value=False).bind_value(
                ui.switch("Modo oscuro").props("dense color=primary").classes("text-sm")
            )

            # User chip OR login link
            if user:
                _render_user_chip(user)
            else:
                ui.link("Iniciar sesión", "/login").classes("text-sm").style(
                    f"color: {theme.PLUM}; font-weight: 500;"
                )


def _render_user_chip(user: dict) -> None:
    """Render the ``@username · rol · cerrar sesión`` chip in the header."""
    username = str(user.get("username") or "?")
    role = str(user.get("role") or "reviewer")

    def _logout() -> None:
        from nicegui import ui as _ui

        auth.logout_user()
        _ui.navigate.to("/login")

    with (
        ui.row()
        .classes("items-center gap-2 no-wrap")
        .style("padding-left: 0.5rem; border-left: 1px solid rgba(191, 161, 129, 0.25);")
    ):
        with ui.avatar(color=theme.PLUM, text_color=theme.CREAM, size="32px"):
            ui.icon("person", size="18px")
        with ui.column().classes("gap-0"):
            ui.label(f"@{username}").classes("text-sm font-medium").style(
                "color: var(--enola-charcoal); line-height: 1.1;"
            )
            role_color = theme.RELIABILITY_CRITICA if role == "admin" else theme.CHARCOAL_LIGHT
            ui.label(role).classes("text-xs").style(
                f"color: {role_color}; letter-spacing: 0.1em; text-transform: uppercase; "
                "line-height: 1.1;"
            )
        ui.button("Cerrar sesión", on_click=_logout, icon="logout").props(
            "flat dense size=sm"
        ).style(f"color: {theme.CHARCOAL_LIGHT};")


def side_drawer(current_path: str) -> None:
    """Render the left navigation drawer.

    ``current_path`` is matched against each :class:`NavItem`'s path
    so the active page gets the ``active-link`` class (styled in
    :mod:`theme`).
    """
    with ui.left_drawer(top_corner=True, bottom_corner=True, value=True).classes("w-64 no-wrap"):
        # Brand block
        with ui.row().classes("w-full items-center gap-2 px-4 py-4"):
            with ui.avatar(
                color=theme.PLUM,
                text_color=theme.CREAM,
                size="36px",
                square=True,
            ):
                ui.icon("auto_stories", size="20px")
            with ui.column().classes("gap-0"):
                ui.label("Enola").classes("text-base font-semibold enola-display").style(
                    "color: var(--enola-plum); line-height: 1;"
                )
                ui.label("Investigadora Digital").classes("text-xs").style(
                    "color: var(--enola-charcoal-light);"
                )

        ui.separator().style("background: rgba(191, 161, 129, 0.35);")

        # Navigation items — each is a clickable Quasar QItem.
        with ui.column().classes("w-full px-2 gap-0"):
            for item in NAV_ITEMS:
                is_active = current_path == item.path
                item_cls = "enola-nav-item"
                if is_active:
                    item_cls += " active-link"
                with (
                    ui.item(
                        on_click=lambda p=item.path: ui.navigate.to(p),
                    )
                    .classes(item_cls)
                    .props("clickable")
                ):
                    with ui.item_section().props("avatar"):
                        ui.icon(
                            item.icon,
                            color=theme.PLUM if is_active else theme.CHARCOAL_LIGHT,
                            size="20px",
                        )
                    with ui.item_section():
                        ui.item_label(item.label).classes("font-medium").style(
                            "color: " + (theme.PLUM if is_active else theme.CHARCOAL) + ";"
                        )

        ui.separator().style("background: rgba(191, 161, 129, 0.35);")

        # Credits footer inside the drawer
        with ui.column().classes("w-full p-4 gap-1"):
            ui.label("Universidad de Granada").classes("text-xs font-semibold").style(
                "color: var(--enola-brass-deep); letter-spacing: 0.18em; text-transform: uppercase;"
            )
            ui.label("TFM 2026 — Detección de violencia de género digital con RAG").classes(
                "text-xs leading-snug"
            ).style("color: var(--enola-charcoal-light);")


def page_footer() -> None:
    """Render the compact page footer."""
    with (
        ui.column()
        .classes("w-full mt-12 pt-6 gap-1")
        .style("border-top: 1px solid rgba(191, 161, 129, 0.25);")
    ):
        ui.label("Inspirado en Enola Holmes, la detective en pro de la justicia.").classes(
            "text-xs enola-display"
        ).style("color: var(--enola-charcoal-light); letter-spacing: 0.01em;")
        ui.label("Stack · Python 3.12 · NiceGUI · Ollama · ChromaDB · LangChain · SQLite").classes(
            "text-xs"
        ).style("color: var(--enola-charcoal-light); opacity: 0.75;")


def page_scaffold(
    title: str,
    *,
    subtitle: str | None = None,
    current_path: str = "/",
    body: Callable[[], None] | None = None,
    requires_auth: bool = True,
) -> None:
    """One-call scaffold: apply theme + mount chrome + run body.

    Example::

        @ui.page("/")
        def inicio() -> None:
            page_scaffold(
                "Enola Investigadora Digital",
                subtitle="Detección de violencia de género digital",
                current_path="/",
                body=render_inicio_body,
                requires_auth=False,   # /inicio is the public landing
            )

    Auth gating: when ``requires_auth=True`` (default) and the current
    tab has no cached user, the function issues a client-side redirect
    to ``/login`` and returns without rendering anything else. Public
    pages must opt-out by passing ``requires_auth=False``.
    """
    # Apply theme INSIDE the page function so ui.add_head_html() is not
    # executed at the script's global scope (NiceGUI rejects that).
    theme.apply_theme()

    if requires_auth and auth.current_user() is None:
        from nicegui import ui as _ui

        _ui.navigate.to("/login")
        return

    side_drawer(current_path)
    page_header(title, subtitle=subtitle)

    if body is not None:
        with ui.column().classes("w-full max-w-screen-2xl mx-auto px-8 py-6 gap-2"):
            body()

        page_footer()
