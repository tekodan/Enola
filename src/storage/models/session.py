"""SessionModel — persistent login sessions for the NiceGUI dashboard.

Sessions live in SQLite so they survive server restarts. Each tab's
session is identified by a random opaque ID that NiceGUI's
``app.storage.user`` carries in its signed cookie. The mapping
``session_id → user_id`` lets us reconstruct the authenticated user on
the next request without relying on in-memory process state.

Sessions auto-expire after ``SESSION_TTL_HOURS`` (default 24h).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from src.storage.base import Base

# Sessions default to 24h. The user originally chose "browser-only"
# (close tab → logout). We honor that intent: when the browser tab
# closes, NiceGUI drops the cookie, so the session row is orphaned
# but harmless. The TTL is a defensive bound for users who don't close
# their tabs.
SESSION_TTL_HOURS: int = 24


def _new_session_id() -> str:
    return uuid.uuid4().hex


class SessionModel(Base):
    """SQLAlchemy model for the ``sessions`` table."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_new_session_id)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.now)
    user_agent = Column(String, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }

    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at
