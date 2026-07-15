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
            .classes("enola-fade-in enola-login-card")
            .style(
                "width: 100%; max-width: 30rem; "
                "background: linear-gradient(180deg, "
                "rgba(255, 255, 255, 0.96) 0%, var(--enola-cream) 100%); "
                "border: 1px solid rgba(191, 161, 129, 0.32); "
                "border-radius: 1.5rem; "
                "padding: 2.5rem 2.25rem 2rem 2.25rem; "
                "box-shadow: 0 24px 56px -16px rgba(35, 30, 46, 0.20), "
                "0 8px 16px -8px rgba(107, 78, 113, 0.10); "
                "position: relative; overflow: hidden;"
            )
        ):
            # Top brass accent bar — adds the "premium" sparkle.
            ui.element("div").style(
                "position: absolute; top: 0; left: 0; right: 0; height: 3px; "
                f"background: linear-gradient(90deg, {theme.PLUM} 0%, "
                f"{theme.ROSE} 50%, {theme.BRASS} 100%);"
            )

            # Brand block
            with ui.element("div").classes("w-full flex flex-col items-center gap-2 mb-5"):
                with ui.element("div").style(
                    "width: 72px; height: 72px; border-radius: 18px; "
                    f"background: linear-gradient(135deg, {theme.PLUM} 0%, "
                    f"{theme.ROSE} 100%); "
                    "display: flex; align-items: center; justify-content: center; "
                    f"box-shadow: 0 8px 20px -6px {theme.PLUM}66;"
                ):
                    ui.icon("auto_stories", size="34px").style(f"color: {theme.CREAM};")
                ui.label("Enola").classes("text-3xl font-semibold enola-display").style(
                    f"color: {theme.PLUM}; line-height: 1; "
                    "letter-spacing: -0.02em; margin-top: 4px;"
                )
                ui.label("Investigadora Digital").classes("text-xs").style(
                    "color: var(--enola-charcoal-light); letter-spacing: 0.22em; "
                    "text-transform: uppercase; font-weight: 600;"
                )

            ui.element("div").classes("enola-brass-divider").style("margin: 1.5rem 0 1.75rem 0;")

            username_input = ui.input("Usuario").props("outlined dense autofocus").classes("w-full")
            password_input = (
                ui.input("Contraseña", password=True, password_toggle_button=True)
                .props("outlined dense")
                .classes("w-full mt-3")
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
                ui.button("Iniciar sesión", on_click=_submit, icon="login")
                .props("unelevated color=primary")
                .classes("w-full mt-6")
                .style(
                    f"background: linear-gradient(135deg, {theme.PLUM} 0%, "
                    f"{theme.PLUM_DEEP} 100%); "
                    f"color: {theme.CREAM}; "
                    "border-radius: 0.625rem; "
                    "padding: 0.75rem 1rem; font-weight: 600; "
                    f"box-shadow: 0 4px 12px -2px {theme.PLUM}55; "
                    "letter-spacing: 0.01em;"
                )
            )

            with ui.element("div").classes("w-full flex items-center gap-3 mt-5"):
                ui.element("div").style(
                    "flex: 1; height: 1px; "
                    "background: linear-gradient(90deg, transparent, "
                    "rgba(191, 161, 129, 0.35), transparent);"
                )
                ui.label("Soporte").classes("text-xs uppercase font-semibold").style(
                    "color: var(--enola-brass-deep); letter-spacing: 0.18em;"
                )
                ui.element("div").style(
                    "flex: 1; height: 1px; "
                    "background: linear-gradient(90deg, transparent, "
                    "rgba(191, 161, 129, 0.35), transparent);"
                )

            ui.label("¿No tenés cuenta? Hablá con el administrador.").classes(
                "text-xs text-center mt-3"
            ).style("color: var(--enola-charcoal-light); font-style: italic;")


@ui.page("/login")
def page_login() -> None:
    """Public login page — no auth gate."""
    # If the user is already authenticated, bounce to the home page.
    if auth.current_user() is not None:
        ui.navigate.to("/inicio")
        return

    theme.apply_theme()

    with (
        ui.element("div")
        .classes("w-full enola-fade-in")
        .style(
            "background: linear-gradient(135deg, rgba(192, 132, 151, 0.06) 0%, "
            "rgba(191, 161, 129, 0.04) 50%, rgba(107, 78, 113, 0.05) 100%);"
        )
    ):
        _render_login_body()


__all__ = ["page_login"]
