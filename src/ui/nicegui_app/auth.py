"""Authentication helpers for the NiceGUI dashboard.

Wraps :class:`src.storage.database.Database` user CRUD + bcrypt password
verification behind a session-aware API. The session is **browser-only**
(no persistent cookie, no ``storage_secret``) per the project's auth
decisions: re-opening a tab or switching browsers means logging in again.

Public surface:

* :class:`AuthService` — thin facade around the DB user methods.
* :func:`current_user` — return the cached user dict for the active tab.
* :func:`login_user` / :func:`logout_user` — session mutators.
* :func:`require_auth` — helper to gate ``@ui.page`` functions; redirects
  unauthenticated requests to ``/login``.
"""

from __future__ import annotations

import logging
from typing import Any

from nicegui import app

logger = logging.getLogger(__name__)


class AuthService:
    """Username/password authentication backed by the SQLite users table."""

    def __init__(self, db: Any | None = None) -> None:
        from src.storage import get_database

        self._db = db if db is not None else get_database()

    def authenticate(self, username: str, password: str) -> dict | None:
        """Return ``{"id", "username", "role", "full_name", ...}`` on success.

        ``None`` for unknown user **or** wrong password **or** inactive
        account — the same generic message is rendered by the login UI
        so we don't leak which case it was.
        """
        return self._db.verify_credentials(username, password)

    def is_admin(self, user_dict: dict | None) -> bool:
        """Return ``True`` if ``user_dict`` has the ``admin`` role."""
        return bool(user_dict) and user_dict.get("role") == "admin"


# Module-level singleton — the DB is itself a singleton and the API is
# stateless besides the in-memory password hash verification.
_auth_service: AuthService | None = None


def _service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# --- Session helpers ---------------------------------------------------------
#
# Two layers of state:
#
# 1. ``app.storage.user`` (NiceGUI in-memory) — a per-tab dict keyed by
#    the signed session cookie. Holds a fast cache of the user dict
#    under ``"current"`` and the session id under ``"_sid"``.
#
# 2. ``Database.sessions`` (SQLite) — the source of truth. Survives
#    server restarts, which ``app.storage.user`` does not. Lookups fall
#    through to SQLite whenever the in-memory cache misses (e.g. right
#    after a restart when the cookie still references a valid session).
#
# Browser-only intent: closing the tab drops the cookie → next visit
# shows anonymous. The SQLite row remains harmless until its 24h TTL
# (or ``Database.purge_expired_sessions()`` reaps it).


def _safe_storage():
    """Return ``app.storage.user`` or ``None`` if storage isn't ready."""
    try:
        return app.storage.user
    except Exception:
        return None


def current_user() -> dict | None:
    """Return the user dict for the current tab, or ``None`` if anonymous."""
    storage = _safe_storage()
    if storage is None:
        return None

    cached = storage.get("current")
    if isinstance(cached, dict):
        return cached

    # In-memory cache missed — try the persistent session row.
    sid = storage.get("_sid")
    if not sid:
        return None

    try:
        from src.storage import get_database

        db = get_database()
        sess = db.find_session(str(sid))
    except Exception:
        return None
    if not sess:
        # Stale cookie whose session was revoked or expired.
        storage.pop("_sid", None)
        return None

    user = db.find_user_by_id(int(sess["user_id"]))
    if not user or str(user.get("is_active", "true")).lower() != "true":
        storage.pop("_sid", None)
        return None

    # Re-populate the in-memory cache so subsequent reads are fast.
    storage["current"] = user
    try:
        db.touch_session(str(sid))
    except Exception:
        pass
    return user


def login_user(user: dict) -> None:
    """Persist ``user`` in BOTH in-memory storage and SQLite.

    A row is created in ``sessions`` keyed by a UUID stored under
    ``app.storage.user["_sid"]``. The user dict is cached under
    ``app.storage.user["current"]`` for fast reads within the same tab.

    Raises:
        ValueError: when ``user`` isn't a dict with a username.
    """
    if not isinstance(user, dict) or not user.get("username"):
        raise ValueError("login_user requires a user dict with at least 'username'")
    if not user.get("id"):
        raise ValueError("login_user requires a user dict with 'id'")

    storage = _safe_storage()
    if storage is None:
        # Storage not initialized yet — server might be running without
        # storage_secret. The page_scaffold would also fail; surface a
        # clear error to the caller.
        raise RuntimeError(
            "app.storage.user is not available — check that ui.run() was "
            "called with a storage_secret. See src/ui/nicegui_app/__main__.py."
        )

    from src.storage import get_database

    db = get_database()
    # Reuse an existing sid if one is already on this tab — keeps the
    # login idempotent across reloads.
    sid = storage.get("_sid")
    if sid and db.find_session(str(sid)):
        # Already logged in; just refresh the cached user dict.
        storage["current"] = user
        db.touch_session(str(sid))
        return

    row = db.create_session(int(user["id"]), str(user["username"]))
    storage["_sid"] = row["id"]
    storage["current"] = user


def logout_user() -> None:
    """Clear the cached user dict AND remove the persistent session row."""
    storage = _safe_storage()
    if storage is None:
        return
    sid = storage.pop("_sid", None)
    if "current" in storage:
        del storage["current"]
    if sid:
        try:
            from src.storage import get_database

            get_database().delete_session(str(sid))
        except Exception:
            pass


def require_auth(redirect_to: str = "/login") -> bool:
    """Return True if the request is authenticated; navigate away otherwise.

    Use inside page functions::

        @ui.page('/inspector')
        def inspector():
            if not require_auth():
                return
            ...

    Returns ``True`` when the user is logged in, ``False`` after issuing
    a client-side redirect (callers should ``return`` immediately).
    """
    if current_user() is not None:
        return True
    from nicegui import ui

    ui.navigate.to(redirect_to)
    return False


def require_admin(redirect_to: str = "/inicio") -> bool:
    """Return True if the current user has ``admin`` role.

    Three outcomes:

    * Logged in **and** admin → ``True`` (page renders normally).
    * Logged in **but not** admin → navigates to ``redirect_to`` and
      returns ``False`` (caller should ``return`` immediately).
    * Not logged in → navigates to ``/login`` and returns ``False``.

    Use inside page functions for destructive features (subir a
    ChromaDB, editar ``knowledge/*.md``, etc.)::

        @ui.page('/conocimiento/editor')
        def editor():
            if not require_admin():
                return
            ...
    """
    user = current_user()
    if user is None:
        from nicegui import ui

        ui.navigate.to("/login")
        return False
    if user.get("role") != "admin":
        logger.warning(
            "Acceso denegado a feature admin para user=%s (role=%s)",
            user.get("username"),
            user.get("role"),
        )
        from nicegui import ui

        ui.navigate.to(redirect_to)
        return False
    return True


def is_admin() -> bool:
    """Return True if the current user is an admin (convenience wrapper)."""
    return _service().is_admin(current_user())


def list_users() -> list[dict]:
    """Return all users for the admin panel."""
    return _service()._db.list_users()


def set_user_active(user_id: int, active: bool) -> bool:
    """Activate / deactivate a user; admin-only callers should gate."""
    return _service()._db.set_user_active(user_id, active)


def set_user_role(user_id: int, role: str) -> bool:
    """Change a user's role. Raises ``ValueError`` for unknown roles."""
    return _service()._db.set_user_role(user_id, role)


def create_user(
    username: str,
    password: str,
    role: str = "reviewer",
    full_name: str | None = None,
) -> int:
    """Create a user; returns the (new or existing) PK."""
    return _service()._db.create_user(
        username=username, password=password, role=role, full_name=full_name
    )


def set_user_password(user_id: int, password: str) -> bool:
    """Rotate a user's password."""
    return _service()._db.set_user_password(user_id, password)


def bootstrap_admin_from_env() -> dict | None:
    """Create an initial admin if ``ENOLA_ADMIN_USERNAME`` is set.

    Reads ``ENOLA_ADMIN_USERNAME`` and ``ENOLA_ADMIN_PASSWORD`` from
    the process environment. If both are present and no user with that
    name exists yet, the admin is created and the function returns the
    user dict. Otherwise it returns ``None`` (silent no-op).

    Idempotent: calling ``bootstrap_admin_from_env`` on subsequent
    boots is harmless.
    """
    import os

    from src.storage import get_database

    username = os.environ.get("ENOLA_ADMIN_USERNAME")
    password = os.environ.get("ENOLA_ADMIN_PASSWORD")
    if not username:
        return None

    db = get_database()
    if db.find_user_by_username(username):
        return db.find_user_by_username(username)
    if not password:
        # Username set but password missing — refuse rather than
        # silently creating a user we can't authenticate.
        import logging

        logging.getLogger(__name__).warning(
            "ENOLA_ADMIN_USERNAME=%s pero ENOLA_ADMIN_PASSWORD ausente — admin NO creado.",
            username,
        )
        return None
    db.create_user(username=username, password=password, role="admin", full_name=username)
    return db.find_user_by_username(username)


__all__ = [
    "AuthService",
    "bootstrap_admin_from_env",
    "create_user",
    "current_user",
    "is_admin",
    "list_users",
    "login_user",
    "logout_user",
    "require_admin",
    "require_auth",
    "set_user_active",
    "set_user_password",
    "set_user_role",
]
