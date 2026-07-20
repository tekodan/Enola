"""Centralized text cleaning for Facebook posts and comments.

This module consolidates all regex-based cleaning of Facebook post and
comment bodies in one place, so the same rules are applied both at
scrape-time (``CommentInteractor._parse_element``,
``FacebookPreprocessor._clean_post_text``) and by the bulk cleaning
script (``scripts/clean_texts.py``).

Two public entry points:

* ``strip_post_noise(text, author="")`` — Aggressive cleaning for post
  bodies. Strips leading anti-scrape obfuscation, trailing Facebook nav
  repetitions, "Ver más" / "Comentar" buttons, URL-spam + author
  duplications and the embedded-comment fragments the scraper
  sometimes captures inline.
* ``strip_comment_noise(text, known_author=None)`` — Lighter cleaning
  for comment bodies. Preserves the trailing UI pattern (``N sem Me
  gusta Responder [Editado] <count>``) by extracting it into a
  separate ``(body, time_ago, responses)`` tuple.

Everything else is internal. The functions are idempotent — calling
them twice on the same input produces the same output as calling them
once.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Editorial pattern: leftover Facebook navigation text injected by the
# anti-scraping layer.
_FB_NAV_LEAD = re.compile(r"^(?:Facebook\s*){2,}")
_FB_NAV_TRAIL = re.compile(r"(?:Facebook\s*){2,}\s*$")

# Anti-scraping obfuscation: a long sequence of single chars separated
# by spaces. Threshold 10 keeps legitimate short-word text intact.
_OBFUSCATION = re.compile(r"(?:\s+[a-zA-Z0-9]\s*){10,}")

# Leading anti-scrape: 3+ single chars (letters / digits) separated by
# spaces followed by an optional middle dot. Catches the classic
# ``t 0 6 8 5 4 9 2 1 ·`` header.
_LEADING_ANTISCRAPE = re.compile(r"^(?:\s*[a-zA-Z0-9]\s*){3,}.*?·\s*")

# Trailing anti-scrape: a block of scattered chars + numbers with no
# real lexical structure, possibly followed by Facebook repetitions.
# Two flavors are stripped:
#
# * Long form: scattered letters + 3 large numbers + Facebook reps.
# * Short form: a run of single-letter / single-digit tokens separated
#   by single spaces at the very end of the text. Real text rarely
#   ends with 7+ such tokens in a row, so the false-positive risk is
#   low. We require each token to be either a digit-run or a single
#   letter (so "Estamos de lanzamiento." is preserved).
_TRAILING_ANTISCRAPE = re.compile(
    r"\s*r\s*n\s*a\s*0\s*o\s*i\s*l\s*m\s*\d+\s*\d+\s*\d+\s*(?:Facebook\s*){2,}\s*$"
)
# Second trailing form: alternating letters / short numbers like
# ``s 7 0 m 9 1 2 a 112 13 9``, optionally followed by Facebook
# repetitions. We require at least 4 letters and 4 numbers in the
# tail to keep false positives low.
_TRAILING_ANTISCRAPE_ALT = re.compile(
    r"\s+(?:[a-zA-Z]\s+\d+\s+|\d+\s+[a-zA-Z]\s+){4,}"
    r"(?:\d+\s+(?:Facebook\s*)+|\d+|\d+\s+\d+\s+\d+)\s*$"
)
# Trailing anti-scrape tail when no ``Facebook Facebook`` is
# present at the very end. We use a token-based function instead of
# a single regex because the tail may contain 1-3 digit numbers
# (``112``, ``13``) in addition to single chars. The function strips
# the trailing token run when 7+ consecutive tokens are all short
# (single char, 1-3 digit number, or literal ``Facebook``).
_SHORT_TOKEN_RE = re.compile(r"^[a-zA-Z0-9]$|^\d{1,3}$|^Facebook$")


def _strip_short_token_tail(text: str, min_tokens: int = 7) -> str:
    """Strip a run of short tokens at the end of ``text``.

    A "short" token is a single alphanumeric char, a 1-3 digit
    number, or the literal ``Facebook``. When the last ``min_tokens``
    tokens are all short, they are dropped. The function is
    deliberately restricted: if EVERY token in the text is short
    (e.g. someone wrote ``a b c d e f g``) we don't strip.

    Args:
        text: Cleaned post body.
        min_tokens: Minimum number of consecutive short tokens at the
            end required to trigger the strip. Defaults to 7.

    Returns:
        ``text`` with the trailing short-token tail removed when the
        threshold is met, unchanged otherwise.
    """
    tokens = text.split(" ")
    if len(tokens) < min_tokens:
        return text

    suffix_len = 0
    for tok in reversed(tokens):
        if _SHORT_TOKEN_RE.match(tok):
            suffix_len += 1
        else:
            break
    if suffix_len < min_tokens:
        return text
    if len(tokens) == suffix_len:
        return text
    return " ".join(tokens[: len(tokens) - suffix_len]).rstrip()


# "Compartido con: Público" share-marker Facebook injects.
_SHARED_PUBLIC = re.compile(r"\s*Compartido con:\s*P[úu]blico\s*")

# Single "Ver más" surrounded by whitespace or ellipsis. This is the
# standalone button-text form (not the user-written truncation marker
# appended at the end of a long comment, which is preserved by the
# comment cleaner).
_VER_MAS_INLINE = re.compile(r"(?:…|\.{3}|·)\s*Ver más\s*")

# Mid-text "Ver más URL Author" between two segments of body content
# (e.g. after Facebook truncates a long post and prepends a See-more link).
_VER_MAS_URL_AUTHOR = re.compile(r"\s*(?:\.{3}|…|·)\s*Ver más\s+[^\s]+\s+[A-Z][a-zA-Z]*\s+")

# Truncated URL like "mGBr281.com" + capitalized author. The author name
# comes from the Facebook link wrapping the URL. Looks like::
#
#     Ver más mGBr281.com Dani <body content repeated>
#
# We match the URL+author as a unit so we can detect where the body
# starts being repeated.
_URL_SPAM_AUTHOR = re.compile(
    r"\s*(?:\.{3}|…|·)?\s*Ver más\s+"
    r"[A-Za-z0-9]{5,12}\.(?:com|net|org|io|co|info|biz|xyz|site|store|shop|me|to|app)\s+"
    r"[A-Z][\w\.\-áéíóúñÁÉÍÓÚüÜ]{1,30}\s+",
    re.UNICODE,
)

# Variant: URL + author appearing WITHOUT a preceding "Ver más".
# Observed in some posts where the body is followed directly by
# ``<URL>.<Author>``. Example::
#
#     Muchos así... RWjubmCD.com Dani Muchos así...
_URL_AUTHOR_INLINE = re.compile(
    r"\s+(?:…|\.{3})?\s*"
    r"[A-Za-z0-9]{5,12}\.(?:com|net|org|io|co|info|biz|xyz|site|store|shop|me|to|app)\s+"
    r"[A-Z][\w\.\-áéíóúñÁÉÍÓÚüÜ]{1,30}\s+",
    re.UNICODE,
)

# Embedded "Ver más comentarios <Author> ..." sub-comment Facebook
# injects into the post body when a long comment thread is rendered.
_VER_MAS_COMENTARIOS = re.compile(
    r"\s*Ver más comentarios\s+[A-Z][\w\.\-áéíóúñÁÉÍÓÚüÜ]{1,30}"
    r"(?:\s+[A-Z][\w\.\-áéíóúñÁÉÍÓÚüÜ]{1,30}){0,2}\s+(?=[A-Za-zÀ-ÿ])",
    re.UNICODE,
)

# "Comentar como <Author>" — the comment-as-author button.
_COMENTAR_COMO = re.compile(
    r"\s*Comentar como\s+[A-Z][\w\.\-áéíóúñÁÉÍÓÚüÜ]+(?:\s+[A-Z][\w\.\-áéíóúñÁÉÍÓÚüÜ]+){0,3}\s+",
    re.UNICODE,
)

# Count + Comentar (e.g. "27 5 Comentar") — engagement counter followed
# by the comment button.
_COUNT_COMENTAR = re.compile(r"\s+\d+\s+\d+\s+(?=Comentar\b)", re.UNICODE)

# Standalone action button words. Only stripped when not part of a longer
# phrase.
_ACTION_BUTTONS = re.compile(r"\s+\b(?:Compartir|Enviar|Reportar)\b\s+", re.UNICODE)

# Bare digit tokens. Word boundary on both sides means we never touch
# digits that are part of a longer token (URL hash, alphanumeric id).
_BARE_NUMBERS = re.compile(r"\b\d+\b")

# ---------------------------------------------------------------------------
# Comment-specific constants
# ---------------------------------------------------------------------------

# Trailing UI bits Facebook appends after every comment. Captures::
#
#     group 1: relative time ("18 sem", "5 min", "3 días" ...)
#     group 2: optional "Editado" marker
#     group 3: trailing reply count (optional, may be empty)
_TIME_TOKEN = r"(\d+\s*(?:sem|min|h|días?|semanas?|horas?)(?:\s+y\s*medias?)?)"
_TRAILING_UI = re.compile(
    rf"\s+{_TIME_TOKEN}\s+M?e\s+gusta\s+Responder\s*(Editado\s+)?(\d+)?\s*$",
    re.IGNORECASE,
)

# Corrupted trailing noise: "e g", "e gusta", "e gusta Responder" —
# forms the obfuscation layer uses when "Me gusta Responder" is split
# across spans.
_CORRUPTED_TRAIL = [
    re.compile(r"\s+e\s+gusta\s+Responder\s*$", re.IGNORECASE),
    re.compile(r"\s+e\s+gusta\s*$", re.IGNORECASE),
    re.compile(r"\s+e\s+g\s*$", re.IGNORECASE),
]

# 1-3 capitalized tokens at start (last-resort author guess). The
# known-author branch below is preferred because it doesn't risk
# stripping the start of a real sentence.
_AUTHOR_GUESS = re.compile(
    r"^(?:Fan\s+destacado\s+)?"
    r"(?P<author>(?:[A-Z][\w\.\-áéíóúñÑÁÉÍÓÚüÜ]{1,30}\s+){0,3})"
    r"(?=\S)",
    re.UNICODE,
)

# Collapses runs of whitespace.
_WHITESPACE = re.compile(r"\s+")

# Ver-más button forms specific to the comments thread (``comentarios``
# / ``respuestas``) — never stripped from a comment body when it is
# the user-written truncation indicator.
_VER_MAS_BUTTON = re.compile(r"\s*Ver más (?:comentarios|respuestas)\s*", re.UNICODE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def strip_standalone_numbers(text: str) -> str:
    """Remove bare digit tokens from ``text``.

    A "bare" digit is one whose surrounding characters are non-word
    characters (whitespace, punctuation, start/end of string). Digits
    that are part of longer tokens — e.g. inside URLs, hashes, or
    alphanumeric identifiers — are preserved.

    Returns ``""`` for empty input.
    """
    if not text:
        return ""
    return _BARE_NUMBERS.sub("", text)


def _strip_body_duplication(text: str) -> str:
    """Detect and remove a body duplication Facebook injects after a
    truncated URL+author link.

    Pattern observed in scraped posts after stripping the
    ``Ver más URL Author`` boundary::

        <intro sentence>. <continuation>. <intro sentence>. <continuation>. <body…>

    where the first two sentences are repeated verbatim and the rest is
    the body. We detect the repeated pair and replace it with just the
    first occurrence followed by the unique body content that follows.

    Detection is conservative:

    * The intro must be at least 25 chars and end with ``.``
      (or ``!`` / ``?`` / ``…``).
    * The intro must appear again later in the text, with at least
      one non-empty chunk (>=15 chars) between the two occurrences.
    * The chunk between the two intros is detected as duplicated when
      it also appears right after the second intro; in that case the
      duplicated chunk is dropped from both sides.

    Args:
        text: Post body after leading / trailing noise and the
            ``Ver más URL Author`` boundary have been stripped.

    Returns:
        ``text`` with the duplicated intro (+ duplicated continuation)
        removed when detected, unchanged otherwise.
    """
    if len(text) < 80:
        return text

    # Locate the first sentence (>=25 chars): the intro.
    m_intro = re.match(r"^([^.!?…]{25,}[.!?…])\s+", text)
    if not m_intro:
        return text

    intro = m_intro.group(1)
    intro_end = m_intro.end()

    # Locate the second occurrence of the intro. It must be at least
    # 15 chars past the first intro for the dupe to be a real
    # "Ver más URL Author <body>" structure rather than adjacent text.
    second_pos = text.find(intro, intro_end + 15)
    if second_pos < 0:
        return text

    # Text between the two intros is the "continuation".
    between = text[intro_end:second_pos].rstrip()
    body_after = text[second_pos + len(intro) :].lstrip()

    if not between:
        # Pure two-intro pattern with nothing between them. Replace the
        # second intro + body_after is kept verbatim.
        return intro + (" " + body_after if body_after else "")

    # Detect whether the continuation itself is duplicated right after
    # the second intro.
    if body_after.startswith(between + " ") or body_after == between:
        body_after = body_after[len(between) :].lstrip()

    return intro + " " + between + (" " + body_after if body_after else "")


def strip_post_noise(text: str, author: str = "") -> str:
    """Strip Facebook-specific noise from a post body.

    Applies every pattern in the post-noise family in a fixed order:

    1. Leading Facebook navigation repetitions (``Facebook Facebook …``).
    2. Leading anti-scrape obfuscation prefix (``t 0 6 8 5 4 9 2 1 ·``).
    3. URL-spam + author + body-duplication segment.
    4. ``… Ver más <URL> <Author>`` form.
    5. ``Ver más comentarios <Author> …`` embedded sub-comment.
    6. Standalone ``Ver más`` between content segments.
    7. ``<N> <N> Comentar`` count pair.
    8. ``Comentar como <Author>`` button.
    9. Standalone ``Compartir`` / ``Enviar`` / ``Reportar`` buttons.
    10. Trailing anti-scrape + Facebook repetition.
    11. Generic single-char obfuscation.
    12. ``Compartido con: Público`` marker.
    13. Body duplication detection (after URL-spam + trailing noise
        are stripped, so the prefix doesn't include anti-scrape noise).
    14. Known author prefix (only when ``author`` is not empty and not
        ``"Unknown"``).
    15. Whitespace collapse + consecutive short-word dedupe.

    Idempotent: calling twice produces the same result as calling once.

    Args:
        text: Raw post body as scraped.
        author: Optional author name to strip from the prefix.

    Returns:
        Cleaned body. ``""`` for empty input.
    """
    if not text:
        return ""

    clean = text

    # 1. Leading Facebook nav
    clean = _FB_NAV_LEAD.sub("", clean)

    # 2. Leading anti-scrape
    clean = _LEADING_ANTISCRAPE.sub("", clean)

    # 3. URL-spam + author duplication segment (must run before the more
    # generic Ver-mas rules so we catch the URL form first).
    clean = _URL_SPAM_AUTHOR.sub(" ", clean)
    clean = _URL_AUTHOR_INLINE.sub(" ", clean)

    # 4. Generic "Ver más URL Author" between content segments
    clean = _VER_MAS_URL_AUTHOR.sub(" ", clean)

    # 5. Embedded sub-comment fragment ("Ver más comentarios <Author>")
    clean = _VER_MAS_COMENTARIOS.sub(" ", clean)

    # 6. Standalone "Ver más" with a leading ellipsis
    clean = _VER_MAS_INLINE.sub(" ", clean)

    # 7. "<N> <N> Comentar" count pair right before the comment button
    clean = _COUNT_COMENTAR.sub(" ", clean)

    # 8. "Comentar como <Author>" button
    clean = _COMENTAR_COMO.sub(" ", clean)

    # 9. Standalone "Compartir" / "Enviar" / "Reportar"
    clean = _ACTION_BUTTONS.sub(" ", clean)

    # 10. Trailing anti-scrape + Facebook rep
    clean = _TRAILING_ANTISCRAPE.sub("", clean)
    clean = _TRAILING_ANTISCRAPE_ALT.sub("", clean)
    clean = _strip_short_token_tail(clean)
    clean = _FB_NAV_TRAIL.sub("", clean)

    # 11. Generic single-char obfuscation
    clean = _OBFUSCATION.sub(" ", clean)

    # 12. Compartido con: Público
    clean = _SHARED_PUBLIC.sub(" ", clean)

    # 13. Body duplication detection (after leading/trailing noise is
    # stripped so the prefix doesn't include anti-scrape markers).
    clean = _strip_body_duplication(clean)

    # 14. Known author prefix
    if author and author != "Unknown":
        clean = re.sub(r"^\s*" + re.escape(author) + r"\s*", "", clean, flags=re.UNICODE)

    # 15. Whitespace collapse + short-word dedupe
    clean = _WHITESPACE.sub(" ", clean).strip()
    words = clean.split()
    deduped: list[str] = []
    for w in words:
        if not deduped or deduped[-1] != w or len(w) > 4:
            deduped.append(w)
    clean = " ".join(deduped)

    return clean


def strip_comment_noise(
    text: str,
    known_author: str | None = None,
) -> tuple[str, str | None, int]:
    """Strip noise from a Facebook comment body.

    Returns a ``(body, time_ago, responses)`` tuple. ``body`` is the
    cleaned comment text suitable for storage in ``Comment.text``;
    ``time_ago`` and ``responses`` are the metadata extracted from the
    trailing UI segment.

    Pattern application order:

    1. Extract trailing UI: ``N sem Me gusta Responder [Editado] <count>``.
    2. Strip corrupted trailing noise (``e g`` / ``e gusta`` / ``e gusta Responder``).
    3. Strip ``Ver más comentarios`` / ``Ver más respuestas`` button
       forms — these are *always* UI buttons, never user content.
    4. Strip bare digit tokens (NOT glued to letters).
    5. Strip the author prefix — preferred path uses ``known_author``
       for an exact match; fallback uses a 1–3 capitalized token guess.
    6. Collapse whitespace.

    The user-written truncation marker (``… Ver más`` at the end of a
    long body, before the trailing UI) is preserved: by the time we
    reach step 2 it is already part of ``body`` and untouched because
    it doesn't match any of the patterns.

    Args:
        text: Raw comment text as scraped.
        known_author: Optional author name. When supplied, the author
            prefix is stripped by exact comparison rather than the
            guess heuristic.

    Returns:
        ``(body, time_ago, responses)``. ``body`` is ``""`` and the
        metadata is ``(None, 0)`` for empty input.
    """
    if not text:
        return "", None, 0

    body = text.strip()
    time_ago: str | None = None
    responses = 0

    # 1. Trailing UI
    trail = _TRAILING_UI.search(body)
    if trail:
        time_ago = trail.group(1)
        if trail.group(3):
            try:
                responses = int(trail.group(3))
            except (TypeError, ValueError):
                responses = 0
        body = body[: trail.start()].rstrip()

    # 2. Corrupted trailing
    for pat in _CORRUPTED_TRAIL:
        new_body = pat.sub("", body)
        if new_body != body:
            body = new_body.rstrip()

    # 3. Ver-mas button forms (comments / respuestas) — never user content
    body = _VER_MAS_BUTTON.sub(" ", body)

    # 4. Bare digit tokens (preserves things like "1ª" or "URL1.com")
    body = strip_standalone_numbers(body)

    # 5. Author prefix
    if known_author:
        prefix_options = [
            "Fan destacado " + known_author + " ",
            known_author + " ",
            known_author,
            "Fan destacado " + known_author,
        ]
        for prefix in prefix_options:
            if body == prefix:
                body = ""
                break
            if body.startswith(prefix):
                body = body[len(prefix) :]
                break
    else:
        m = _AUTHOR_GUESS.match(body)
        if m:
            body = body[m.end() :]

    # 6. Whitespace collapse
    body = _WHITESPACE.sub(" ", body).strip()

    return body, time_ago, responses
