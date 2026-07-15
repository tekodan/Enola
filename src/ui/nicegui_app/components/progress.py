"""Review progress bar + ETA estimator for the /validacion page.

Tracks how many analyses the reviewer has processed and estimates the
time remaining using a moving average of the last ``WINDOW`` review
durations. The state is kept per-tab in ``app.storage.user`` under
``"progress_state"``.

The pure-Python helpers (:func:`compute_progress`,
:func:`format_eta`, :func:`compute_reviewed_count`) are unit-tested
without NiceGUI. The NiceGUI renderer is exercised by the page smoke
tests in :mod:`test_validacion`.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nicegui import ui

from src.ui.nicegui_app import theme

logger = logging.getLogger(__name__)


PROGRESS_KEY = "progress_state"
WINDOW_SIZE = 10  # last N review timestamps used for ETA


def compute_reviewed_count(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Return ``(reviewed_count, total_count)`` from an analysis listing.

    A row counts as reviewed when its ``feedback_row`` has an ``id``.
    """
    total = len(rows)
    reviewed = sum(1 for r in rows if (r.get("feedback_row") or {}).get("id"))
    return reviewed, total


def compute_progress(reviewed: int, total: int) -> float:
    """Return the fraction reviewed (``0.0`` to ``1.0``).

    Empty listings report ``1.0`` so the bar shows "completed" rather
    than "0% of nothing".
    """
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, reviewed / total))


def format_eta(seconds: float | None) -> str:
    """Return a short human ETA label, or ``"—"`` when unknown.

    ``seconds`` of ``None`` (no data yet) renders as ``"—"``.
    Negative values are clamped to ``0``.
    """
    if seconds is None or math.isnan(seconds) or math.isinf(seconds):
        return "—"
    if seconds <= 0:
        return "Listo"
    if seconds < 60:
        return "<1 min"
    if seconds < 3600:
        minutes = max(1, int(seconds // 60))
        return f"~{minutes} min"
    if seconds < 86400:
        hours = max(1, int(seconds // 3600))
        return f"~{hours} h"
    days = max(1, int(seconds // 86400))
    return f"~{days} d"


@dataclass
class ProgressState:
    """Per-tab state for the review progress estimator.

    ``samples`` keeps the ISO timestamps of the last ``WINDOW_SIZE``
    reviews — older entries are pruned on insert. ``ema_seconds`` is
    an exponential moving average of inter-review durations so a
    burst of fast reviews quickly lowers the ETA estimate.
    """

    samples: deque[str] = field(default_factory=lambda: deque(maxlen=WINDOW_SIZE))
    ema_seconds: float | None = None
    ema_alpha: float = 0.5

    def record_review(self, *, now: datetime | None = None) -> None:
        """Record that a review just completed (at ``now``)."""
        ts = (now or datetime.now(UTC)).isoformat(timespec="seconds")
        if self.samples:
            last = datetime.fromisoformat(self.samples[-1])
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            current = now if now is not None else datetime.now(UTC)
            if current.tzinfo is None:
                current = current.replace(tzinfo=UTC)
            gap = (current - last).total_seconds()
            if gap > 0:
                if self.ema_seconds is None:
                    self.ema_seconds = gap
                else:
                    self.ema_seconds = (
                        self.ema_alpha * gap + (1 - self.ema_alpha) * self.ema_seconds
                    )
        self.samples.append(ts)

    def estimate_seconds_remaining(self, pending: int) -> float | None:
        """Return the estimated seconds to finish ``pending`` more rows.

        Returns ``None`` until we have at least one sample.
        """
        if self.ema_seconds is None or pending <= 0:
            return None
        return self.ema_seconds * pending


def save_state(storage: Any, state: ProgressState) -> None:
    """Persist the state into ``app.storage.user``."""
    if storage is None:
        return
    storage[PROGRESS_KEY] = {
        "samples": list(state.samples),
        "ema_seconds": state.ema_seconds,
        "ema_alpha": state.ema_alpha,
    }


def load_state(storage: Any) -> ProgressState:
    """Restore state from ``app.storage.user`` (returns fresh state if absent)."""
    if storage is None:
        return ProgressState()
    raw = storage.get(PROGRESS_KEY)
    if not isinstance(raw, dict):
        return ProgressState()
    samples_raw = raw.get("samples") or []
    samples: deque[str] = deque(maxlen=WINDOW_SIZE)
    for entry in samples_raw[-WINDOW_SIZE:]:
        if isinstance(entry, str):
            samples.append(entry)
    return ProgressState(
        samples=samples,
        ema_seconds=raw.get("ema_seconds")
        if isinstance(raw.get("ema_seconds"), (int, float))
        else None,
        ema_alpha=float(raw.get("ema_alpha", 0.5)),
    )


def render_progress_bar(
    *,
    reviewed: int,
    total: int,
    eta_seconds: float | None,
) -> None:
    """Render the progress bar + KPI row.

    Pure UI — does not mutate any state. The page wires the
    ``record_review`` callback via :func:`install_review_progress`.
    """
    pct = compute_progress(reviewed, total)
    pct_label = int(round(pct * 100))
    eta_label = format_eta(eta_seconds)
    with (
        ui.element("div")
        .classes("w-full enola-progress")
        .style(
            "display: flex; flex-direction: column; gap: 0.45rem; "
            "padding: 0.85rem 1.1rem; "
            "border: 1px solid rgba(191, 161, 129, 0.22); "
            "border-radius: 0.75rem; "
            "background: linear-gradient(180deg, rgba(255,255,255,0.75) 0%, "
            "var(--enola-cream) 100%);"
        )
    ):
        with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("insights", size="18px").style(f"color: {theme.PLUM};")
                ui.label("Progreso de revisión").classes("enola-kpi-label")
            with ui.row().classes("items-center gap-2"):
                ui.label(f"{reviewed}/{total} · {pct_label}%").classes(
                    "text-sm font-semibold"
                ).style(f"color: {theme.PLUM};")
                ui.label(f"ETA {eta_label}").classes("text-xs").style(
                    f"color: {theme.CHARCOAL_LIGHT}; letter-spacing: 0.04em;"
                )
        with ui.element("div").style(
            "height: 8px; width: 100%; border-radius: 999px; "
            "background: rgba(191, 161, 129, 0.18); overflow: hidden;"
        ):
            with ui.element("div").style(
                f"height: 100%; width: {pct_label}%; "
                f"background: linear-gradient(90deg, {theme.ROSE} 0%, {theme.PLUM} 100%); "
                "border-radius: 999px; transition: width 220ms cubic-bezier(0.16, 1, 0.3, 1);"
            ):
                pass


__all__ = [
    "ProgressState",
    "WINDOW_SIZE",
    "compute_progress",
    "compute_reviewed_count",
    "format_eta",
    "load_state",
    "render_progress_bar",
    "save_state",
]
