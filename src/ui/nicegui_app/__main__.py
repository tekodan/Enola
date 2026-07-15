"""Module entry point: ``python -m src.ui.nicegui_app``.

This is the NiceGUI **script** (not a library import), so it must
NOT define ``@ui.page`` decorators, ``ui.add_head_html``,
``ui.colors`` or any other UI in the global scope — NiceGUI rejects
that with ``RuntimeError: ui.page cannot be used in NiceGUI scripts
when UI is defined in the global scope``.

All ``@ui.page`` definitions live in :mod:`src.ui.nicegui_app.pages`,
and the theme tokens are applied INSIDE each page function via
:func:`src.ui.nicegui_app.layout.page_scaffold`.

Importing the page modules here registers their routes before
``ui.run()`` starts the server.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from nicegui import app, ui

# Bootstrap admin BEFORE registering routes so the database schema
# (incl. the new ``users`` table) is ready when the first login
# arrives. Idempotent — safe across restarts.
logger = logging.getLogger(__name__)
try:
    from src.ui.nicegui_app.auth import bootstrap_admin_from_env

    admin = bootstrap_admin_from_env()
    if admin:
        logger.info("Bootstrap admin: %s (id=%s)", admin.get("username"), admin.get("id"))
except Exception:  # noqa: BLE001
    logger.exception("Bootstrap admin falló — continuando sin admin inicial")

# Import the page modules so their @ui.page decorators register the
# routes. This must happen BEFORE ui.run().
from src.ui.nicegui_app.pages import (  # noqa: E402,F401  -- registers @ui.page routes
    conocimiento,
    conocimiento_cargar,
    conocimiento_editor,
    conocimiento_explorar,
    estadistica,
    ia,
    inicio,
    inspector,
    login,
    validacion,
)

port = int(os.environ.get("ENOLA_PORT", "8080"))
host = os.environ.get("ENOLA_HOST", "127.0.0.1")
# storage_secret is required by NiceGUI to use `app.storage.user` /
# `app.storage.browser`. Without it, login state can't be persisted and
# every page refresh re-authenticates. Honor an explicit env var, fall
# back to a stable per-installation random secret in ~/.config.
_storage_secret = os.environ.get("ENOLA_STORAGE_SECRET")
if not _storage_secret:
    from pathlib import Path

    _secret_dir = Path.home() / ".config" / "enola"
    _secret_file = _secret_dir / "storage_secret.key"
    try:
        _storage_secret = _secret_file.read_text().strip()
    except FileNotFoundError:
        import secrets

        _storage_secret = secrets.token_urlsafe(32)
        try:
            _secret_dir.mkdir(parents=True, exist_ok=True)
            _secret_file.write_text(_storage_secret)
            _secret_file.chmod(0o600)
        except OSError:
            # If we can't persist, just use the ephemeral secret — every
            # boot re-authenticates, which is annoying but secure.
            pass


# Mount the logo directory (inside the package) at /static so the
# Enola / UGR PNGs are served at predictable URLs. ``layout.side_drawer``
# references these as ``/static/...``.
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    app.add_static_files("/static", str(_static_dir))


ui.run(
    title="Enola Investigadora Digital",
    favicon="🔍",
    port=port,
    host=host,
    reload=False,
    show=False,
    dark=False,
    storage_secret=_storage_secret,
)
