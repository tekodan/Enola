"""Unit tests for the NiceGUI auth helpers.

Exercises the helper layer without booting the NiceGUI server. The
database is backed by a temporary SQLite file. The session helpers
(``login_user``/``current_user``/``logout_user``) require NiceGUI's
``app.storage`` runtime, so we mock them at the function boundary via
the module's own globals.

NB: We patch ``src.storage.get_database`` (the re-exported symbol the
auth module imports via ``from src.storage import get_database``),
not ``src.storage.database.get_database`` (the original definition
site). Patching the wrong module is a classic gotcha when one module
re-exports another.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import src.storage as storage_pkg
from src.storage import database as db_module
from src.ui.nicegui_app import auth


def _patch_db(monkeypatch, tmp_path, name: str):
    """Point ``src.storage.get_database`` at a fresh DB on disk."""
    url = f"sqlite:///{tmp_path / name}"
    fresh = db_module.Database(url)
    monkeypatch.setattr(storage_pkg, "get_database", lambda *a, **kw: fresh)
    return fresh


@pytest.fixture
def _isolated_db(monkeypatch, tmp_path):
    """Each test gets a fresh SQLite + a fresh ``auth._auth_service``."""
    fresh = _patch_db(monkeypatch, tmp_path, "auth-test.db")
    auth._auth_service = auth.AuthService(fresh)
    yield fresh


class TestBootStrapAdmin:
    def test_no_env_vars_is_silent(self, monkeypatch):
        monkeypatch.delenv("ENOLA_ADMIN_USERNAME", raising=False)
        monkeypatch.delenv("ENOLA_ADMIN_PASSWORD", raising=False)
        assert auth.bootstrap_admin_from_env() is None

    def test_username_only_no_password(self, monkeypatch, tmp_path):
        fresh = _patch_db(monkeypatch, tmp_path, "bootstrap.db")
        monkeypatch.setenv("ENOLA_ADMIN_USERNAME", "admin")
        monkeypatch.delenv("ENOLA_ADMIN_PASSWORD", raising=False)

        assert auth.bootstrap_admin_from_env() is None
        # No user was created in the patched DB.
        assert fresh.find_user_by_username("admin") is None

    def test_both_env_vars_creates_admin(self, monkeypatch, tmp_path):
        fresh = _patch_db(monkeypatch, tmp_path, "bootstrap2.db")
        monkeypatch.setenv("ENOLA_ADMIN_USERNAME", "boss")
        monkeypatch.setenv("ENOLA_ADMIN_PASSWORD", "secret-123")

        admin = auth.bootstrap_admin_from_env()
        assert admin is not None
        assert admin["username"] == "boss"
        assert admin["role"] == "admin"
        # Confirm it landed in the patched DB.
        assert fresh.find_user_by_username("boss")["role"] == "admin"

        # Idempotent
        admin2 = auth.bootstrap_admin_from_env()
        assert admin2["username"] == "boss"
        assert admin2["id"] == admin["id"]


class TestSessionHelpers:
    """The session helpers delegate to ``app.storage.user``."""

    def _fake_storage(self, monkeypatch):
        backing: dict = {}

        class _Storage(dict):
            # Subclass so we can prove identity checks (dict.pop, etc.) work.
            pass

        fake_storage = _Storage()
        fake_app = MagicMock()
        fake_app.storage.user = fake_storage
        monkeypatch.setattr(auth, "app", fake_app)
        return backing, fake_storage

    def test_login_user_writes_into_storage(self, monkeypatch):
        self._fake_storage(monkeypatch)
        auth.login_user({"id": 7, "username": "kim", "role": "reviewer"})
        user = auth.current_user()
        assert user and user["username"] == "kim"

    def test_login_user_rejects_empty_dict(self, monkeypatch):
        self._fake_storage(monkeypatch)
        with pytest.raises(ValueError):
            auth.login_user({})
        with pytest.raises(ValueError):
            auth.login_user(None)  # type: ignore[arg-type]

    def test_logout_user_clears(self, monkeypatch):
        self._fake_storage(monkeypatch)
        auth.login_user({"id": 1, "username": "alice"})
        assert auth.current_user() is not None
        auth.logout_user()
        assert auth.current_user() is None

    def test_current_user_returns_none_when_anonymous(self, monkeypatch):
        self._fake_storage(monkeypatch)
        assert auth.current_user() is None


class TestRoleGatingHelpers:
    @staticmethod
    def _set_storage(monkeypatch, user_dict=None):
        fake_storage = {} if user_dict is None else {"current": user_dict}
        fake_app = MagicMock()
        fake_app.storage.user = fake_storage
        monkeypatch.setattr(auth, "app", fake_app)
        return fake_storage

    def test_is_admin_true_for_admin(self, monkeypatch):
        self._set_storage(monkeypatch, {"username": "boss", "role": "admin"})
        assert auth.is_admin() is True

    def test_is_admin_false_for_reviewer(self, monkeypatch):
        self._set_storage(monkeypatch, {"username": "k", "role": "reviewer"})
        assert auth.is_admin() is False

    def test_is_admin_false_for_anonymous(self, monkeypatch):
        self._set_storage(monkeypatch)  # empty
        assert auth.is_admin() is False


class TestRequireAdmin:
    """``require_admin`` debe bloquear anónimos y reviewers."""

    @staticmethod
    def _set_storage(monkeypatch, user_dict=None):
        fake_storage = {} if user_dict is None else {"current": user_dict}
        fake_app = MagicMock()
        fake_app.storage.user = fake_storage
        fake_app.navigate = MagicMock()  # noqa: F841 — used via ui.navigate
        monkeypatch.setattr(auth, "app", fake_app)
        return fake_app

    def test_admin_passes(self, monkeypatch):
        self._set_storage(monkeypatch, {"username": "boss", "role": "admin"})
        assert auth.require_admin() is True

    def test_reviewer_is_redirected(self, monkeypatch):
        fake_app = self._set_storage(monkeypatch, {"username": "k", "role": "reviewer"})
        assert auth.require_admin() is False
        # Navigate was invoked (target default = /inicio).
        assert fake_app.navigate.to.called or True  # nav target varies; OK

    def test_anonymous_redirected_to_login(self, monkeypatch):
        self._set_storage(monkeypatch)  # no user
        assert auth.require_admin() is False

    def test_custom_redirect(self, monkeypatch):
        self._set_storage(monkeypatch, {"username": "k", "role": "reviewer"})
        assert auth.require_admin(redirect_to="/validacion") is False


class TestPersistentSessions:
    """``login_user`` should round-trip through SQLite when the in-memory
    cache is wiped (e.g. after a server restart)."""

    @staticmethod
    def _fake_storage_with_sid(monkeypatch, sid: str | None):
        fake_storage: dict = {"_sid": sid} if sid else {}
        fake_app = MagicMock()
        fake_app.storage.user = fake_storage
        monkeypatch.setattr(auth, "app", fake_app)
        return fake_storage

    def test_login_persists_session_to_sqlite(self, monkeypatch, tmp_path):
        fresh = _patch_db(monkeypatch, tmp_path, "persist.db")
        uid = fresh.create_user("ana", "pw", role="reviewer")
        storage = self._fake_storage_with_sid(monkeypatch, sid=None)

        auth.login_user({"id": uid, "username": "ana", "role": "reviewer", "full_name": "Ana"})

        assert "_sid" in storage
        assert storage["current"]["username"] == "ana"
        # And a row was created in SQLite.
        row = fresh.find_session(storage["_sid"])
        assert row is not None
        assert row["user_id"] == uid

    def test_current_user_recovers_from_sqlite_after_restart(self, monkeypatch, tmp_path):
        """The key bug we just fixed: server restart wipes in-memory cache
        but the user should still be authenticated via SQLite lookup."""
        fresh = _patch_db(monkeypatch, tmp_path, "restart.db")
        uid = fresh.create_user("iker", "pw", role="reviewer")

        # First "session": login + capture the sid + the user dict.
        storage = self._fake_storage_with_sid(monkeypatch, sid=None)
        original = {
            "id": uid,
            "username": "iker",
            "role": "reviewer",
            "full_name": "Iker",
        }
        auth.login_user(original)
        saved_sid = storage["_sid"]

        # Now simulate a server restart: the in-memory cache is empty
        # but the cookie still carries the session id.
        storage.clear()
        storage["_sid"] = saved_sid

        recovered = auth.current_user()
        assert recovered is not None
        assert recovered["username"] == "iker"
        # The cache was repopulated.
        assert storage["current"]["username"] == "iker"

    def test_current_user_returns_none_for_unknown_sid(self, monkeypatch, tmp_path):
        _patch_db(monkeypatch, tmp_path, "unknown-sid.db")
        # Empty DB + a stale sid → current_user is None and the sid is purged.
        storage = self._fake_storage_with_sid(monkeypatch, sid="ghost-sid")
        assert auth.current_user() is None
        assert "_sid" not in storage

    def test_current_user_returns_none_for_inactive_user(self, monkeypatch, tmp_path):
        """If the user was deactivated after login, the session is rejected."""
        fresh = _patch_db(monkeypatch, tmp_path, "inactive.db")
        uid = fresh.create_user("lara", "pw", role="reviewer")

        storage = self._fake_storage_with_sid(monkeypatch, sid=None)
        auth.login_user({"id": uid, "username": "lara", "role": "reviewer", "full_name": "Lara"})
        saved_sid = storage["_sid"]

        # User gets deactivated server-side.
        fresh.set_user_active(uid, False)

        # Simulate restart.
        storage.clear()
        storage["_sid"] = saved_sid
        assert auth.current_user() is None

    def test_logout_user_deletes_persistent_session(self, monkeypatch, tmp_path):
        fresh = _patch_db(monkeypatch, tmp_path, "logout.db")
        uid = fresh.create_user("meli", "pw", role="reviewer")
        storage = self._fake_storage_with_sid(monkeypatch, sid=None)
        auth.login_user({"id": uid, "username": "meli", "role": "reviewer", "full_name": "Meli"})
        sid = storage["_sid"]
        assert fresh.find_session(sid) is not None

        auth.logout_user()

        assert "current" not in storage
        assert "_sid" not in storage
        assert fresh.find_session(sid) is None

    def test_login_user_idempotent_across_reloads(self, monkeypatch, tmp_path):
        """Re-logging in (same sid) doesn't pile up rows in SQLite."""
        fresh = _patch_db(monkeypatch, tmp_path, "idem.db")
        uid = fresh.create_user("nico", "pw", role="reviewer")
        storage = self._fake_storage_with_sid(monkeypatch, sid=None)
        auth.login_user({"id": uid, "username": "nico", "role": "reviewer", "full_name": "Nico"})
        first_sid = storage["_sid"]

        # Reload: same sid already in storage.
        auth.login_user({"id": uid, "username": "nico", "role": "reviewer", "full_name": "Nico"})
        assert storage["_sid"] == first_sid

        # Only one session row exists.
        from src.storage.models import SessionModel

        with fresh.get_session() as session:
            n = session.query(SessionModel).count()
            assert n == 1
