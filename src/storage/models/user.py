"""UserModel — reviewer/admin accounts for the NiceGUI validation UI.

The login system is admin-managed (no public signup). Roles:

* ``"admin"`` — can create / disable other users via the CLI
  (``python -m src.cli users ...``) and via the admin panel in NiceGUI.
* ``"reviewer"`` — can only submit feedback on the validation page.

Passwords are stored as bcrypt hashes via :mod:`passlib`. Active
flag defaults to ``"true"`` so new accounts are usable immediately;
set to ``"false"`` to revoke without deleting the row.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from src.storage.base import Base


class UserModel(Base):
    """SQLAlchemy model for the ``users`` table."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="reviewer")
    full_name = Column(String, nullable=True)
    is_active = Column(String, nullable=False, default="true")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_login = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Convert ``UserModel`` to a JSON-friendly dict.

        ``password_hash`` is intentionally omitted — it is never returned
        to the UI or the CLI.
        """
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
