"""Detect duplicate Facebook comments.

Facebook scrapes often produce two flavors of duplicates that need to be
collapsed before storage:

1. **Exact duplicates** — same text scraped twice (e.g. DOM path + LLM
   fallback, repeated polling, or two runs against different page URLs
   that resolve to different ``page_id`` hashes).
2. **Truncated duplicates** — same comment, but one of the two copies is
   a strict prefix of the other (the scraper only captured the first
   sentence before the "Ver más" link).

Both cases collapse to a single canonical row using ``pick_canonical``.
The detection is intentionally conservative: comments are only grouped
when they belong to the same ``post_id`` and ``author``. This avoids
false positives between unrelated comments that happen to share a few
words (e.g. two different users both writing "Excelente post.").

Threshold is intentionally high (``0.95`` by default) so that two
genuinely different comments by the same author on the same post stay
separate.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable

# Trailing pattern: " 17 min Me gusta Responder [3]" / " 2 h Me gusta" / "Me gusta 5".
# Case-insensitive because Facebook sometimes renders "Me gusta" / "ME GUSTA" / "me gusta"
# inconsistently within the same comment thread.
_TRAILING_META = re.compile(
    r"\s+\d+\s*(?:min|h|d|s|m|sem|mes(?:es)?|año|anos)\b"
    r"|\s+(?:[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+\s+)?[Gg]usta\b"
    r"|\s+[Rr]esponder(?:\s+\d+)?\s*$",
    re.IGNORECASE,
)

# Leading author pattern: 2–3 capitalized tokens (allow accented chars
# and internal hyphens), followed by whitespace. Facebook prepends the
# author name to the comment body, so "Meza Jose Honestidad…" begins
# with two capitalized tokens that are not part of the message itself.
# We require AT LEAST 2 tokens because a single capitalized word at
# the start (e.g. "Excelente post…") is indistinguishable from a
# 1-word body opener, and the actual FB author names in our dataset
# are always 2+ tokens ("Meza Jose", "Daniel Flores Soto", etc.).
_LEADING_AUTHOR = re.compile(
    r"^(?:[A-ZÁÉÍÓÚÑÜ][a-zA-ZÀ-ÿ\-]+"
    r"(?:\s+(?:de|del|la|las|los|y)\s+[a-zA-ZÀ-ÿ\-]+)?"
    r"\s+){2,3}"
)

_WHITESPACE = re.compile(r"\s+")
# Allow letters (incl. Spanish accents) and Spanish opening punctuation
# (``¿``/``¡``) at the boundaries; everything else is noise.
_NON_TEXT_PREFIX = re.compile(r"^[^\w¿¡ÁÉÍÓÚÑÜáéíóúñü]+")
_NON_TEXT_SUFFIX = re.compile(r"[^\w.!?¿¡ÁÉÍÓÚÑÜáéíóúñü]+$")

# "Fan destacado Author Name" is a Facebook badge prepended to the
# author name; strip it before identifying the author.
_FAN_BADGE = re.compile(r"^Fan destacado\s+", re.IGNORECASE)


def normalize_comment_text(text: str) -> str:
    """Return a canonical, comparable form of a Facebook comment body.

    The transformation is **injective for our purposes**: two comments
    that look the same to a human (modulo author prefix, timestamp
    suffix, whitespace and casing) produce the same normalized string,
    but two genuinely different comments do not.

    Steps applied, in order:

    1. Strip the "Fan destacado" badge at the start.
    2. Strip a leading author block (1–3 capitalized tokens).
    3. Strip trailing metadata ("17 min", "Me gusta", "Responder [n]").
    4. Strip non-text punctuation at both ends.
    5. Lowercase, collapse whitespace.
    """
    if not text:
        return ""

    t = text.strip()

    t = _FAN_BADGE.sub("", t)
    t = _LEADING_AUTHOR.sub("", t)
    t = _TRAILING_META.sub("", t)
    t = _NON_TEXT_PREFIX.sub("", t)
    t = _NON_TEXT_SUFFIX.sub("", t)
    t = _WHITESPACE.sub(" ", t).strip()
    return t.lower()


def _similarity(a: str, b: str) -> float:
    """Return SequenceMatcher ratio in [0.0, 1.0].

    ``difflib.SequenceMatcher.ratio()`` is O(n·m) but our normalized
    strings are short (<500 chars typically) and each group is bounded
    by the comments-per-post cap, so this is acceptable.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _is_duplicate_pair(a: str, b: str, threshold: float) -> bool:
    """Return True if two normalized texts describe the same comment.

    Three conditions, evaluated in order:

    1. Exact equality after normalization.
    2. Strict prefix relationship (one is a prefix of the other and the
       longer one is at least 1.5× the length of the shorter one). This
       catches truncated captures like "Primeras dos frases…" vs "Primeras
       dos frases… del comentario completo". The length ratio guards
       against grouping two short comments that happen to share a prefix
       (e.g. two different "Me gusta" one-liners).
    3. ``difflib.SequenceMatcher`` ratio >= ``threshold``.
    """
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 20 and longer.startswith(shorter) and len(longer) >= int(len(shorter) * 1.5):
        return True
    return _similarity(a, b) >= threshold


def find_duplicate_groups(
    comments: Iterable[dict],
    *,
    threshold: float = 0.95,
) -> list[list[dict]]:
    """Group comments that should be considered duplicates.

    Two comments are grouped iff:

    * they share the same ``post_id`` (or both have ``post_id == None``),
    * their ``author`` is equal (after stripping), and
    * their normalized texts are either identical **or** have a
      ``difflib.SequenceMatcher`` ratio ``>= threshold``.

    The grouping is per-cluster (transitive): if A ~ B and B ~ C, the
    three end up in the same group. Only groups of size ``>= 2`` are
    returned — singletons are not interesting for dedup.

    Args:
        comments: Iterable of comment dicts. Each must expose at least
            ``id``, ``text``, ``author``, ``post_id`` (other keys are
            preserved and passed through to the caller).
        threshold: Similarity threshold in ``[0.0, 1.0]``. ``1.0`` keeps
            only exact matches after normalization; lower values catch
            truncated variants but risk false positives. Default
            ``0.95`` matches the design discussion.

    Returns:
        List of groups (each a list of comment dicts). Order within a
        group matches input order. Group order is deterministic by the
        smallest ``id`` in each group.
    """
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"threshold must be in [0.0, 1.0], got {threshold}")

    buckets: dict[tuple[str, str], list[dict]] = {}
    for c in comments:
        post_id = (c.get("post_id") or "") or ""
        author = (c.get("author") or "").strip()
        buckets.setdefault((post_id, author), []).append(c)

    groups: list[list[dict]] = []
    for bucket in buckets.values():
        # Each cluster is a list of comments that we've decided are
        # duplicates of each other (transitive closure).
        clusters: list[list[dict]] = []

        for comment in bucket:
            norm_text = normalize_comment_text(comment.get("text", ""))
            if not norm_text:
                # Empty comments are noise; do not cluster.
                continue

            placed = False
            for cluster in clusters:
                representative = cluster[0]
                rep_norm = normalize_comment_text(representative.get("text", ""))
                if _is_duplicate_pair(norm_text, rep_norm, threshold):
                    cluster.append(comment)
                    placed = True
                    break

            if not placed:
                clusters.append([comment])

        for cluster in clusters:
            if len(cluster) >= 2:
                groups.append(cluster)

    # Deterministic ordering for tests and human-readable logs.
    groups.sort(key=lambda g: min(c.get("id") or "" for c in g))
    return groups


def pick_canonical(group: list[dict]) -> dict:
    """Return the comment that should survive the merge.

    Ranking, in order:

    1. Longest ``text`` (after stripping) — the truncated copy loses.
    2. Highest ``likes`` — engagement wins on ties.
    3. Earliest non-null ``created_at`` (string ISO or datetime) — older wins.

    Implementation note: we use ``min`` with negated keys so that
    "largest original" wins on the negated fields while "earliest
    date" wins on the date (no negation needed). Missing dates sort
    after dated rows via a sentinel.

    Raises ``ValueError`` for an empty group.
    """
    if not group:
        raise ValueError("group must be non-empty")

    def _date_key(c: dict) -> str:
        v = c.get("created_at")
        if v is None or v == "":
            return "9999-99-99"
        iso = getattr(v, "isoformat", None)
        if callable(iso):
            return str(iso())
        return str(v)

    def _likes(c: dict) -> int:
        try:
            return int(c.get("likes") or 0)
        except (TypeError, ValueError):
            return 0

    def _strip_len(c: dict) -> int:
        return len((c.get("text") or "").strip())

    def _sort_key(c: dict) -> tuple:
        return (
            -_strip_len(c),  # longer text first
            -_likes(c),  # more likes first
            _date_key(c),  # earlier date first (ISO 8601 sorts lexicographically)
        )

    return min(group, key=_sort_key)


def plan_merge(groups: list[list[dict]]) -> list[dict]:
    """Build a merge plan from duplicate groups.

    Returns one record per group::

        {
            "canonical_id": "...",
            "canonical_text": "...",
            "duplicate_ids": ["...", "..."],
            "removed_count": int,
        }

    Useful for CLI dry-run output and for the actual ``--apply``
    execution path.
    """
    plan = []
    for group in groups:
        canonical = pick_canonical(group)
        dups = [c for c in group if c.get("id") != canonical.get("id")]
        plan.append(
            {
                "canonical_id": canonical.get("id"),
                "canonical_text": (canonical.get("text") or "").strip(),
                "duplicate_ids": [d.get("id") for d in dups],
                "removed_count": len(dups),
            }
        )
    return plan
