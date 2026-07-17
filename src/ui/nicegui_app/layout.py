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

Responsive drawer: the drawer is created with ``value=None`` so
Quasar's ``q-drawer`` automatically shows it on desktop (≥ 1024px)
and hides it on mobile — where the header's hamburger button
calls :meth:`Drawer.toggle` to reveal it.
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
    NavItem("Cargar (admin)", "cloud_upload", "/conocimiento/cargar"),
    NavItem("Explorar (admin)", "travel_explore", "/conocimiento/explorar"),
    NavItem("Editor MD (admin)", "edit_note", "/conocimiento/editor"),
    NavItem("Validación", "task_alt", "/validacion"),
)


# --- Drawer state ------------------------------------------------------------
#
# The drawer is created inside :func:`side_drawer` (which is called from
# :func:`page_scaffold`). The hamburger button in :func:`page_header`
# needs a reference to it so it can call ``toggle()`` on mobile. We
# stash the most-recent drawer in a module-level slot keyed by the
# current client so each tab gets its own handle.

_DRAWER_REF: dict[int, object] = {}


def _set_drawer(drawer) -> None:
    """Register the drawer for the current client (used by hamburger)."""
    try:
        _DRAWER_REF[ui.context.client.id] = drawer
    except (LookupError, AttributeError):
        _DRAWER_REF[id(drawer)] = drawer


def _current_drawer():
    """Return the drawer registered for the current client (or any)."""
    client_id = None
    try:
        client_id = ui.context.client.id
    except (LookupError, AttributeError):
        pass
    drawer = _DRAWER_REF.get(client_id) if client_id is not None else None
    if drawer is None:
        # Fallback: any drawer we've registered (last one wins).
        drawer = next(iter(_DRAWER_REF.values()), None) if _DRAWER_REF else None
    return drawer


def _toggle_drawer() -> None:
    """Toggle the side drawer (called by the hamburger on mobile)."""
    drawer = _current_drawer()
    if drawer is not None and hasattr(drawer, "toggle"):
        drawer.toggle()


def _hide_drawer() -> None:
    """Close the drawer after a nav-item is clicked on mobile."""
    drawer = _current_drawer()
    if drawer is not None and hasattr(drawer, "hide"):
        drawer.hide()


def _nav_click(path: str, label: str) -> None:
    """Navigate to ``path`` and close the drawer (mobile UX).

    Closing is a no-op on desktop where the drawer is permanently
    visible — :meth:`Drawer.hide` still works but is overridden by
    Quasar's ``show-if-above`` prop.
    """
    _hide_drawer()
    ui.navigate.to(path)


# --- Page chrome -------------------------------------------------------------


def page_header(title: str, *, subtitle: str | None = None) -> None:
    """Render the top header bar (brand + title + dark-mode + user menu).

    Adds a user chip when a session user is present: shows the
    ``@username`` + role badge and a *Cerrar sesión* button. Anonymous
    users see a link to ``/login`` instead. The header uses a
    frosted-glass surface (translucent cream + backdrop blur) that
    gains elevation once the user scrolls past the top.

    On mobile (≤ 768px) the brand mark badge collapses (becomes
    visible only inside the drawer) and the GitHub link + "Modo
    oscuro" label hide via CSS. The drawer becomes an overlay opened
    by a hamburger button rendered in the header.
    """
    user = auth.current_user()
    header = ui.header(elevated=False).classes(
        "enola-header items-center justify-between px-6 py-3 no-wrap"
    )

    # Scroll-aware shadow: toggle the ``enola-header--scrolled`` class
    # on the header once the page scrolls past 12px. Implemented via
    # tiny JS so it stays smooth on long pages (no Python callbacks).
    ui.run_javascript(
        """
        (() => {
            const h = document.querySelector('.enola-header');
            if (!h) return;
            const apply = () => {
                if (window.scrollY > 12) h.classList.add('enola-header--scrolled');
                else h.classList.remove('enola-header--scrolled');
            };
            apply();
            window.addEventListener('scroll', apply, { passive: true });
        })();
        """
    )

    with header:
        with ui.row().classes("items-center gap-3 no-wrap"):
            # Hamburger — visible only on mobile via CSS.
            ui.button(
                icon="menu",
                on_click=lambda: _toggle_drawer(),
            ).props("flat dense round").classes("enola-hamburger").style(
                "color: var(--enola-plum);"
            )

            with (
                ui.element("div")
                .classes("enola-brand-mark")
                .style(
                    "width: 40px; height: 40px; border-radius: 10px; overflow: hidden; "
                    "box-shadow: 0 4px 12px -4px rgba(107, 78, 113, 0.35);"
                )
            ):
                ui.html(
                    '<img src="/static/logo-enola-new.png" '
                    'alt="Enola Investigadora Digital" '
                    'style="display: block; width: 100%; height: 100%; '
                    'object-fit: cover; object-position: center 30%;" />',
                    sanitize=False,
                )
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-lg font-semibold enola-display").style(
                    "color: var(--enola-cream); line-height: 1.1; letter-spacing: -0.015em;"
                )
                if subtitle:
                    ui.label(subtitle).classes("text-xs").style(
                        "color: rgba(250, 246, 240, 0.78); letter-spacing: 0.02em;"
                    )

        with ui.row().classes("items-center gap-3"):
            ui.link(
                "GitHub",
                GITHUB_REPO_URL,
                new_tab=True,
            ).classes("text-sm enola-header__github").style(
                "color: var(--enola-cream); font-weight: 500; opacity: 0.85;"
            )

            # Dark-mode toggle — NiceGUI persists the choice per-session.
            # The label is hidden on mobile via CSS; the switch stays.
            with ui.row().classes("items-center gap-2 no-wrap enola-dark-toggle-row"):
                ui.switch(value=False).props("dense color=primary").classes("enola-dark-toggle")
                ui.label("Modo oscuro").classes("text-sm enola-dark-toggle-label").style(
                    "color: var(--enola-cream); letter-spacing: 0.01em;"
                )

            # User chip OR login link
            if user:
                _render_user_chip(user)
            else:
                ui.link("Iniciar sesión", "/login").classes("text-sm").style(
                    f"color: {theme.CREAM}; font-weight: 600;"
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
        .classes("items-center gap-2 no-wrap enola-user-chip")
        .style("padding-left: 0.65rem; border-left: 1px solid rgba(250, 246, 240, 0.20);")
    ):
        with ui.element("div").style(
            "width: 32px; height: 32px; border-radius: 10px; "
            f"background: linear-gradient(135deg, {theme.ROSE} 0%, {theme.BRASS} 100%); "
            "display: flex; align-items: center; justify-content: center; "
            "box-shadow: 0 2px 8px -2px rgba(0, 0, 0, 0.30);"
        ):
            ui.icon("person", size="16px").style(f"color: {theme.CREAM};")
        with ui.column().classes("gap-0"):
            ui.label(f"@{username}").classes("text-sm font-medium").style(
                "color: var(--enola-cream); line-height: 1.1; letter-spacing: -0.005em;"
            )
            role_color = theme.BRASS if role == "admin" else "rgba(250, 246, 240, 0.75)"
            ui.label(role).classes("text-xs").style(
                f"color: {role_color}; letter-spacing: 0.14em; text-transform: uppercase; "
                "font-weight: 600; line-height: 1.1;"
            )
        ui.button("Salir", on_click=_logout, icon="logout").props("flat dense size=sm").style(
            f"color: {theme.CREAM}; font-weight: 500; opacity: 0.85;"
        )


# Display dimensions for the side-drawer logos.
#
# We bypass NiceGUI's ``ui.image`` (Quasar q-img default ``fit="cover"``
# clips bitmaps) and render a raw ``<img>`` via ``ui.html``. CSS
# ``aspect-ratio`` sizes the element to the natural proportions of each
# PNG and ``object-fit: contain`` guarantees no clipping. The dark-mode
# toggle swaps ``src`` (and ``aspect-ratio`` for the Enola logo, whose
# dark variant has a different natural ratio) via JavaScript.
#
# Source PNG dimensions (verified with PIL):
#   enola_logo_light.png — 1616x528 (ratio 3.06:1)
#   enola_logo_dark.png  — 1652x452 (ratio 3.66:1)
#   ugr-light.png        — 4724x4724 (ratio 1:1)
#   ugr_dark.png         — 4724x4724 (ratio 1:1)
_LOGO_RATIO = 2048 / 1032  # ~1.984 — logo-enola-new.png
_LOGO_MAX_WIDTH_PX = 220  # CSS px — sharp at 1x and 2x displays
_UGR_SIZE_PX = 128  # square, matches the 4724x4724 source


def _logo_img_html(elem_id: str, src: str, aspect: float, max_w: int, alt: str) -> str:
    """Return a centered ``<img>`` HTML snippet for the side drawer.

    Fixed CSS ``aspect-ratio`` matching the source PNG forces the rendered
    box to the natural proportions of the asset — no clipping, no
    distortion. ``width: 100%; max-width: <px>`` keeps it responsive.
    """
    return (
        f'<img id="{elem_id}" src="{src}" alt="{alt}" '
        f'style="display: block; margin: 0 auto; width: 100%; '
        f"max-width: {max_w}px; aspect-ratio: {aspect:.4f}; "
        f'object-fit: contain; object-position: center;" />'
    )


def side_drawer(current_path: str) -> None:
    """Render the left navigation drawer.

    ``current_path`` is matched against each :class:`NavItem`'s path
    so the active page gets the ``active-link`` class (styled in
    :mod:`theme`).

    Responsive behaviour:

    * **Desktop (≥ 768 px):** Quasar docks the drawer on the left
      and keeps it permanently visible (``value=True`` + the default
      ``mode="desktop"`` semantics at this breakpoint).
    * **Mobile (< 768 px):** Quasar converts the drawer to an
      overlay that's closed by default. The hamburger button in the
      header calls :meth:`Drawer.toggle` to open it; clicking a nav
      item or the close button calls :meth:`Drawer.hide`.
    """
    # Logo + UGR URLs — served by `app.add_static_files('/static', ...)`
    # configured in :mod:`src.ui.nicegui_app.__main__`.
    logo_url = "/static/logo-enola-new.png"
    ugr_light_url = "/static/ugr-light.png"
    ugr_dark_url = "/static/ugr_dark.png"

    drawer = (
        ui.left_drawer(top_corner=True, bottom_corner=True, value=True)
        .props("mode=desktop breakpoint=768")
        .classes("w-64 no-wrap enola-drawer")
    )
    _set_drawer(drawer)

    with drawer:
        # Brand block — Enola logo via raw <img> (no q-img wrapper, no
        # possible cropping). Single asset for both light and dark mode.
        with ui.column().classes("w-full items-center px-4 pt-6 pb-5 relative-position"):
            ui.html(
                _logo_img_html(
                    "enola-logo",
                    logo_url,
                    _LOGO_RATIO,
                    _LOGO_MAX_WIDTH_PX,
                    "Enola Investigadora Digital",
                ),
                sanitize=False,
            )

            # Close button — visible only on mobile so the user can
            # dismiss the overlay with a familiar X.
            ui.button(
                icon="close",
                on_click=lambda: _hide_drawer(),
            ).props("flat dense round").classes("enola-drawer-close").style(
                f"position: absolute; top: 6px; right: 6px; color: {theme.CHARCOAL_LIGHT};"
            )

        ui.element("div").classes("enola-brass-divider").style("margin: 0 16px 4px 16px;")

        with ui.row().classes("w-full items-center justify-between px-4 mt-3 mb-1"):
            ui.label("NAVEGACIÓN").classes("text-xs uppercase font-semibold").style(
                "color: #5C4530; letter-spacing: 0.22em; font-weight: 700;"
            )
            # Inline close on mobile — small × next to the section label.
            ui.button(
                icon="close",
                on_click=lambda: _hide_drawer(),
            ).props("flat dense round size=sm").classes("enola-drawer-close").style(
                f"color: {theme.CHARCOAL_LIGHT};"
            )

        # Navigation items — each is a clickable Quasar QItem with refined hover.
        with ui.column().classes("w-full px-3 gap-1 py-2"):
            for item in NAV_ITEMS:
                is_active = current_path == item.path
                item_cls = "enola-nav-item"
                if is_active:
                    item_cls += " active-link"
                with (
                    ui.item(
                        on_click=lambda p=item.path, i=item.label: _nav_click(p, i),
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
                            "color: "
                            + (theme.PLUM if is_active else theme.CHARCOAL)
                            + "; letter-spacing: -0.005em;"
                        )

        ui.separator().style("background: rgba(191, 161, 129, 0.30); margin: 12px 16px 4px 16px;")

        # Credits footer — UGR source PNG is square (4724x4724), so the
        # <img> uses a 1:1 box. Same JS-swap trick for the dark-mode toggle.
        with ui.column().classes("w-full px-4 py-4 items-center text-center gap-1"):
            with ui.element("div").style(
                "padding: 6px 14px; border-radius: 999px; "
                "background: rgba(191, 161, 129, 0.10); "
                "border: 1px solid rgba(191, 161, 129, 0.30);"
            ):
                ui.label("Universidad de Granada").style(
                    "color: var(--enola-brass-deep); letter-spacing: 0.18em; "
                    "text-transform: uppercase; font-size: 0.62rem; font-weight: 700;"
                )
            ui.html(
                f'<img id="ugr-logo" src="{ugr_light_url}" alt="Universidad de Granada" '
                f'style="display: block; margin: 10px auto 0; width: {_UGR_SIZE_PX}px; '
                f"height: {_UGR_SIZE_PX}px; max-width: 100%; object-fit: contain; "
                f'filter: drop-shadow(0 2px 6px rgba(35, 30, 46, 0.10));" />',
                sanitize=False,
            )

            def _toggle_ugr_logo() -> None:
                is_dark = bool(ui.dark_mode.value)
                src = ugr_dark_url if is_dark else ugr_light_url
                ui.run_javascript(
                    f"const e = document.getElementById('ugr-logo');if (e) {{ e.src = '{src}'; }}"
                )

            ui.dark_mode().on_value_change(lambda _: _toggle_ugr_logo())

            ui.label("TFM 2026").classes("font-semibold").style(
                "color: var(--enola-plum); font-size: 0.72rem; letter-spacing: 0.10em; "
                "margin-top: 8px; font-weight: 600;"
            )
            ui.label("Detección de violencia de género digital").style(
                "color: var(--enola-charcoal-light); font-size: 0.68rem; "
                "line-height: 1.35; opacity: 0.85; letter-spacing: 0.01em;"
            )

            ui.separator().style(
                "background: rgba(191, 161, 129, 0.25); margin: 10px 24px 6px; width: auto;"
            )

            with ui.row().classes("items-center gap-1 justify-center no-wrap"):
                ui.icon("auto_stories", size="13px", color=theme.PLUM)
                ui.label("Investigadora").style(
                    "color: var(--enola-plum); font-size: 0.66rem; "
                    "font-weight: 600; letter-spacing: 0.10em; text-transform: uppercase;"
                )
            ui.label("Kimberly Michell Luna Eraso").style(
                "color: var(--enola-charcoal-light); font-size: 0.70rem; "
                "opacity: 0.88; font-style: italic; line-height: 1.3;"
            )

            with ui.row().classes("items-center gap-1 justify-center no-wrap mt-1"):
                ui.icon("workspace_premium", size="13px", color=theme.BRASS_DEEP)
                ui.label("Tutora").style(
                    "color: var(--enola-brass-deep); font-size: 0.66rem; "
                    "font-weight: 600; letter-spacing: 0.10em; text-transform: uppercase;"
                )
            ui.label("María del Mar García Vita").style(
                "color: var(--enola-charcoal-light); font-size: 0.70rem; "
                "opacity: 0.88; font-style: italic; line-height: 1.3;"
            )

            ui.separator().style(
                "background: rgba(191, 161, 129, 0.20); margin: 8px 24px 4px; width: auto;"
            )

            ui.label("Máster en Cultura de Paz · DDHH").style(
                "color: var(--enola-charcoal-light); font-size: 0.62rem; "
                "opacity: 0.70; line-height: 1.4; font-style: italic; "
                "letter-spacing: 0.02em;"
            )


def page_footer() -> None:
    """Render the compact page footer."""
    with (
        ui.column()
        .classes("w-full mt-12 pt-7 gap-2")
        .style(
            "border-top: 1px solid rgba(191, 161, 129, 0.25); "
            "background: linear-gradient(180deg, transparent 0%, "
            "rgba(191, 161, 129, 0.04) 100%);"
        )
    ):
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.icon("auto_stories", size="14px", color=theme.PLUM)
            ui.label("Inspirado en Enola Holmes, la detective en pro de la justicia.").classes(
                "text-xs enola-display"
            ).style(
                "color: var(--enola-charcoal-light); letter-spacing: 0.01em; font-style: italic;"
            )
        ui.label("Stack · Python 3.12 · NiceGUI · Ollama · ChromaDB · LangChain · SQLite").classes(
            "text-xs"
        ).style("color: var(--enola-charcoal-light); opacity: 0.70; letter-spacing: 0.02em;")
        with ui.row().classes("items-center gap-1"):
            ui.label("Powered by").classes("text-xs").style(
                "color: var(--enola-charcoal-light); opacity: 0.55;"
            )
            ui.link(
                "danialva.com",
                "https://danialva.com",
                new_tab=True,
            ).classes("text-xs").style("color: var(--enola-plum); opacity: 0.85; font-weight: 500;")


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
    from src.ui.nicegui_app.theme import apply_theme

    apply_theme()

    if requires_auth and auth.current_user() is None:
        from nicegui import ui as _ui

        _ui.navigate.to("/login")
        return

    side_drawer(current_path)
    page_header(title, subtitle=subtitle)

    if body is not None:
        with ui.element("main").classes(
            "enola-fade-in w-full max-w-screen-2xl mx-auto px-8 py-7 flex flex-col gap-3"
        ):
            body()

        page_footer()
