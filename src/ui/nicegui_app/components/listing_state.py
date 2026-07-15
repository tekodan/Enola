"""Centralised listing state for the /validacion page.

This module replaces the ad-hoc ``filter_state: dict`` that previously
lived inline inside ``_render_body``. The contract is:

* **Immutable snapshot**: callers receive a frozen dataclass instead of
  a mutable dict, so callbacks cannot accidentally introduce
  inconsistency between the filter widgets and the listing.
* **URL ↔ storage round-trip**: :func:`from_query` parses NiceGUI's
  ``app.url`` query string and :func:`to_query` produces a URL-safe
  representation. Persistence in ``app.storage.user`` keeps the state
  across navigations within the same browser tab.
* **Sort + pagination**: Ola 2 added ``sort_key``/``sort_dir`` and
  ``page``/``page_size`` so the listing stays performant on large
  datasets.

The state is pure-Python; rendering the widgets that mutate it lives
in :mod:`src.ui.nicegui_app.pages.validacion` (to keep this module
importable from tests without booting NiceGUI).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import parse_qs, urlencode

CONTENT_TYPE_ALL = "all"
CONTENT_TYPE_POST = "post"
CONTENT_TYPE_COMMENT = "comment"
CONTENT_TYPE_CHOICES: tuple[str, ...] = (
    CONTENT_TYPE_ALL,
    CONTENT_TYPE_POST,
    CONTENT_TYPE_COMMENT,
)

REVIEW_ALL = "all"
REVIEW_PENDING = "pending"
REVIEW_AGREED = "agreed"
REVIEW_DISAGREED = "disagreed"
REVIEW_STATE_CHOICES: tuple[str, ...] = (
    REVIEW_ALL,
    REVIEW_PENDING,
    REVIEW_AGREED,
    REVIEW_DISAGREED,
)

SORT_KEYS: tuple[str, ...] = (
    "content_type",
    "categoria",
    "estado",
    "severidad",
)
SORT_DIRS: tuple[str, ...] = ("asc", "desc")
DEFAULT_SORT_KEY = "estado"
DEFAULT_SORT_DIR = "asc"

PAGE_SIZE_CHOICES: tuple[int, ...] = (10, 25, 50, 100)
DEFAULT_PAGE_SIZE = 25


def _coerce_str(value: Any, choices: tuple[str, ...], default: str) -> str:
    if not isinstance(value, str):
        return default
    return value if value in choices else default


def _coerce_int(value: Any, choices: tuple[int, ...], default: int) -> int:
    try:
        n = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return n if n in choices else default


@dataclass(frozen=True)
class ListingState:
    """Immutable snapshot of the validation page filters.

    Build it via :func:`from_query` / :func:`from_storage` / :func:`default`
    and produce a new value via :func:`with_updates` whenever a widget
    mutates one of the fields.
    """

    content_type: str = CONTENT_TYPE_ALL
    review_state: str = REVIEW_PENDING
    only_violent: bool = False
    sort_key: str = DEFAULT_SORT_KEY
    sort_dir: str = DEFAULT_SORT_DIR
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    audit: dict[str, Any] = field(default_factory=dict)

    def to_query(self) -> str:
        """Return an URL-encoded query string (without leading ``?``)."""
        params: dict[str, str] = {
            "ct": self.content_type,
            "st": self.review_state,
            "ov": "1" if self.only_violent else "0",
            "sk": self.sort_key,
            "sd": self.sort_dir,
            "p": str(self.page),
            "ps": str(self.page_size),
        }
        return urlencode(params)

    def with_updates(self, **changes: Any) -> ListingState:
        """Return a new :class:`ListingState` with the given fields overridden.

        ``page`` is reset to ``1`` whenever a filter (content_type,
        review_state, only_violent) changes so the user always lands on
        the first page of the new result set. Sort/page-size changes
        also reset the page.
        """
        page_resetting_keys = {
            "content_type",
            "review_state",
            "only_violent",
            "sort_key",
            "sort_dir",
            "page_size",
        }
        if page_resetting_keys.intersection(changes):
            changes.setdefault("page", 1)
        return replace(self, **changes)


def default() -> ListingState:
    """Return the initial listing state."""
    return ListingState()


def from_query(query_string: str) -> ListingState:
    """Parse a ``?ct=...&st=...`` query string into a state.

    Unknown / invalid values fall back to :func:`default`.
    """
    if not query_string:
        return default()
    if query_string.startswith("?"):
        query_string = query_string[1:]
    raw = parse_qs(query_string, keep_blank_values=False)

    content_type = _coerce_str((raw.get("ct") or [None])[0], CONTENT_TYPE_CHOICES, CONTENT_TYPE_ALL)
    review_state = _coerce_str((raw.get("st") or [None])[0], REVIEW_STATE_CHOICES, REVIEW_PENDING)
    only_violent_raw = (raw.get("ov") or ["0"])[0]
    only_violent = str(only_violent_raw).lower() in {"1", "true", "yes", "si", "sí"}
    sort_key = _coerce_str((raw.get("sk") or [None])[0], SORT_KEYS, DEFAULT_SORT_KEY)
    sort_dir = _coerce_str((raw.get("sd") or [None])[0], SORT_DIRS, DEFAULT_SORT_DIR)
    try:
        page = max(1, int((raw.get("p") or ["1"])[0]))
    except (TypeError, ValueError):
        page = 1
    page_size = _coerce_int((raw.get("ps") or [None])[0], PAGE_SIZE_CHOICES, DEFAULT_PAGE_SIZE)
    return ListingState(
        content_type=content_type,
        review_state=review_state,
        only_violent=only_violent,
        sort_key=sort_key,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


def from_storage(storage: Any) -> ListingState:
    """Read the previously-persisted state from ``app.storage.user``.

    Returns :func:`default` if storage is unavailable or empty.
    """
    if storage is None:
        return default()
    saved = storage.get("listing_state")
    if not isinstance(saved, dict):
        return default()
    content_type = _coerce_str(saved.get("content_type"), CONTENT_TYPE_CHOICES, CONTENT_TYPE_ALL)
    review_state = _coerce_str(saved.get("review_state"), REVIEW_STATE_CHOICES, REVIEW_PENDING)
    sort_key = _coerce_str(saved.get("sort_key"), SORT_KEYS, DEFAULT_SORT_KEY)
    sort_dir = _coerce_str(saved.get("sort_dir"), SORT_DIRS, DEFAULT_SORT_DIR)
    only_violent = bool(saved.get("only_violent", False))
    try:
        page = max(1, int(saved.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    page_size = _coerce_int(saved.get("page_size"), PAGE_SIZE_CHOICES, DEFAULT_PAGE_SIZE)
    return ListingState(
        content_type=content_type,
        review_state=review_state,
        only_violent=only_violent,
        sort_key=sort_key,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


def save_to_storage(storage: Any, state: ListingState) -> None:
    """Persist the state into ``app.storage.user`` (no-op if unavailable)."""
    if storage is None:
        return
    storage["listing_state"] = {
        "content_type": state.content_type,
        "review_state": state.review_state,
        "only_violent": state.only_violent,
        "sort_key": state.sort_key,
        "sort_dir": state.sort_dir,
        "page": state.page,
        "page_size": state.page_size,
    }


def apply_sort(rows: list[dict], sort_key: str, sort_dir: str) -> list[dict]:
    """Return a NEW list sorted by ``sort_key`` / ``sort_dir``.

    Sorting is done in Python (small N — typically <500) to avoid
    hitting the DB twice. Unknown ``sort_key`` falls back to the input
    order. ``sort_dir`` is case-insensitive; anything other than
    ``"desc"`` is treated as ascending.
    """
    if sort_key not in SORT_KEYS:
        return list(rows)

    descending = sort_dir.lower() == "desc"

    def _key(row: dict) -> tuple:
        if sort_key == "content_type":
            return (str(row.get("content_type") or ""),)
        if sort_key == "categoria":
            return (str(row.get("categoria") or ""),)
        if sort_key == "severidad":
            order = {"alta": 3, "media": 2, "baja": 1, "ninguna": 0}
            sev = str(row.get("severidad") or "ninguna").lower()
            return (order.get(sev, -1),)
        if sort_key == "estado":
            order = {REVIEW_PENDING: 0, REVIEW_DISAGREED: 1, REVIEW_AGREED: 2}
            return (order.get(str(row.get("feedback_status") or REVIEW_PENDING), -1),)
        return ()

    return sorted(rows, key=_key, reverse=descending)


def paginate(rows: list[dict], page: int, page_size: int) -> tuple[list[dict], int]:
    """Return ``(slice_for_page, total_pages)`` for a page-numbered listing.

    ``page`` is 1-indexed. ``page_size`` must be a positive integer.
    The returned slice never includes out-of-range rows — callers
    should check that ``page <= total_pages`` before rendering.
    """
    total = len(rows)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return rows[start:end], total_pages


__all__ = [
    "CONTENT_TYPE_ALL",
    "CONTENT_TYPE_CHOICES",
    "CONTENT_TYPE_COMMENT",
    "CONTENT_TYPE_POST",
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_SORT_DIR",
    "DEFAULT_SORT_KEY",
    "ListingState",
    "PAGE_SIZE_CHOICES",
    "REVIEW_AGREED",
    "REVIEW_ALL",
    "REVIEW_DISAGREED",
    "REVIEW_PENDING",
    "REVIEW_STATE_CHOICES",
    "SORT_DIRS",
    "SORT_KEYS",
    "apply_sort",
    "default",
    "from_query",
    "from_storage",
    "paginate",
    "save_to_storage",
]
