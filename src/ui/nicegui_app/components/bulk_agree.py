"""Bulk agree helper for the /validacion page.

Provides a small API for the page-level controller to mark many rows
as "agreed" in a single action. The renderer (checkbox column +
button bar) lives in :mod:`src.ui.nicegui_app.pages.validacion` —
this module focuses on the pure-Python batch logic so it can be
unit-tested.

Batch strategy:

* The page passes the *full row dicts* (already in memory) so we
  don't need to re-fetch them from the DB.
* For each selected row we check if a feedback row already exists.
  If yes, we skip (we don't silently overwrite an existing
  correction).
* Otherwise we build a feedback payload with ``agrees=True`` and
  call ``save_feedback`` — the same path the single-row form uses.

The function returns a result summary that the renderer uses to
show a toast like "Marcaste 5 filas como de acuerdo · 2 ya estaban
revisadas y se omitieron".
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from src.storage import get_database
from src.ui import validacion as val_helpers

logger = logging.getLogger(__name__)


@dataclass
class BulkAgreeResult:
    """Summary of a bulk-agree batch."""

    saved: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    @property
    def total(self) -> int:
        return self.saved + self.skipped + self.failed

    def as_toast(self) -> str:
        """Return a one-line summary suitable for ``ui.notify``."""
        if self.total == 0:
            return "Nada para marcar — ninguna fila seleccionada."
        parts = [f"✅ {self.saved} marcada/s como de acuerdo"]
        if self.skipped:
            parts.append(f"⏭ {self.skipped} omitida/s (ya revisadas)")
        if self.failed:
            parts.append(f"❌ {self.failed} con error")
        return " · ".join(parts)


def bulk_agree(
    *,
    rows: Iterable[dict],
    user: dict,
    db=None,
) -> BulkAgreeResult:
    """Mark each ``row`` as ``agrees=True`` in a single batch.

    Skips rows that already carry a ``feedback_row`` — the reviewer
    can open them individually if they want to override the existing
    verdict. Returns a :class:`BulkAgreeResult` summarising what
    happened.

    Args:
        rows: Analysis row dicts (must have ``id``, ``content_type``,
            ``content_id``, ``text_snapshot``).
        user: Authenticated user dict (must have ``id`` + ``username``).
        db: Optional database override (used by tests).
    """
    if db is None:
        # Fall through to the imported singleton — only useful in
        # production. Tests should pass ``db`` explicitly because the
        # monkeypatched `database.get_database` is NOT visible here
        # (we imported the name into this module's namespace at
        # import time).
        db = get_database()
    result = BulkAgreeResult()

    for row in rows:
        ar_id = row.get("id")
        if not isinstance(ar_id, int):
            result.failed += 1
            result.errors.append("row sin id válido")
            continue
        if row.get("feedback_row"):
            result.skipped += 1
            continue
        payload = val_helpers.build_feedback_payload(
            analysis_result_id=ar_id,
            content_type=str(row.get("content_type") or "post"),
            content_id=str(row.get("content_id") or ""),
            text_snapshot=str(row.get("text_snapshot") or ""),
            agrees=True,
            reason=None,
            reviewer=user.get("username"),
            corrected_labels=None,
        )
        payload["reviewer_user_id"] = user.get("id")
        payload["reviewer_username"] = user.get("username")
        try:
            db.save_feedback(payload)
            result.saved += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.errors.append(f"#{ar_id}: {exc}")
            logger.exception("bulk_agree save_feedback failed for %s", ar_id)

    return result


__all__ = ["BulkAgreeResult", "bulk_agree"]
