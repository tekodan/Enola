"""Login page — public entry point for the NiceGUI dashboard.

Renders a centered login card. On success, caches the user dict via
:func:`src.ui.nicegui_app.auth.login_user` and navigates to ``/inicio``.

The page intentionally does NOT use :func:`page_scaffold` (no chrome /
drawer) so the visual focus is on the form. Bad credentials never leak
which field failed — the message is generic.

Password reset is admin-managed (``python -m src.cli users
set-password <username>``).
"""

from __future__ import annotations

import logging

from nicegui import ui

from src.ui.nicegui_app import auth, theme

logger = logging.getLogger(__name__)


def _render_login_body() -> None:
    """Render the login form inside a centered card."""
    with (
        ui.element("div")
        .classes("w-full flex items-center justify-center")
        .style("min-height: calc(100vh - 4rem); padding: 2rem;")
    ):
        with (
            ui.element("div")
            .classes("enola-login-card")
            .style(
                "width: 100%; max-width: 28rem; "
                "background: var(--enola-cream); "
                "border: 1px solid rgba(191, 161, 129, 0.30); "
                "border-radius: 1.25rem; "
                "padding: 2.25rem 2rem 1.75rem 2rem; "
                f"box-shadow: 0 12px 32px -8px {theme.PLUM}22;"
            )
        ):
            # Brand block
            with ui.element("div").classes("w-full flex flex-col items-center gap-2 mb-5"):
                with ui.avatar(
                    color=theme.PLUM,
                    text_color=theme.CREAM,
                    size="56px",
                ):
                    ui.icon("search", size="28px")
                ui.label("Enola").classes("text-2xl font-semibold enola-display").style(
                    f"color: {theme.PLUM}; line-height: 1;"
                )
                ui.label("Investigadora Digital").classes("text-xs").style(
                    "color: var(--enola-charcoal-light); letter-spacing: 0.16em; "
                    "text-transform: uppercase;"
                )

            ui.separator().style(
                "background: linear-gradient(90deg, transparent, "
                "rgba(191, 161, 129, 0.45), transparent); margin: 0 0 1.5rem 0;"
            )

            username_input = (
                ui.input("Username").props("outlined dense autofocus").classes("w-full")
            )
            password_input = (
                ui.input("Password", password=True, password_toggle_button=True)
                .props("outlined dense")
                .classes("w-full mt-2")
            )

            error_label = (
                ui.label("")
                .classes("text-sm mt-3")
                .style(f"color: {theme.RELIABILITY_CRITICA}; min-height: 1.25rem;")
            )

            def _submit() -> None:
                username = (username_input.value or "").strip()
                password = password_input.value or ""
                if not username or not password:
                    error_label.text = "Completá usuario y contraseña."
                    return
                user = auth._service().authenticate(username, password)
                if not user:
                    logger.warning("Login fallido para username=%r", username)
                    error_label.text = "Usuario o contraseña incorrectos."
                    return
                auth.login_user(user)
                logger.info("Login exitoso: %s (rol=%s)", user["username"], user["role"])
                ui.navigate.to("/inicio")

            def _on_enter() -> None:
                _submit()

            password_input.on("keydown.enter", _on_enter)
            username_input.on("keydown.enter", _on_enter)

            (
                ui.button("Iniciar sesión", on_click=_submit)
                .props("unelevated color=primary")
                .classes("w-full mt-5")
                .style(
                    "background: var(--enola-plum); "
                    "color: var(--enola-cream); border-radius: 0.625rem;"
                )
            )

            ui.label("¿No tenés cuenta? Hablá con el administrador.").classes(
                "text-xs text-center mt-4"
            ).style("color: var(--enola-charcoal-light);")


@ui.page("/login")
def page_login() -> None:
    """Public login page — no auth gate."""
    # If the user is already authenticated, bounce to the home page.
    if auth.current_user() is not None:
        ui.navigate.to("/inicio")
        return

    theme.apply_theme()

    with ui.element("div").classes("w-full").style("background: var(--enola-cream);"):
        _render_login_body()


__all__ = ["page_login"]
