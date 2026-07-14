"""Facebook HTML preprocessor to extract hierarchical structure.

Preprocesses raw Facebook HTML to extract:
- Page metadata (title, URL)
- Posts with text, author, date, likes, comments_count, shares
- Comments with text, author, date, likes

Reduces HTML size significantly before sending to LLM.
"""

import json
import logging
import re
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.scraper.text_cleaner import strip_post_noise

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Centralized selectors — adjust here when Facebook changes their DOM
# ---------------------------------------------------------------------------

# Small LRU cache for parsed BeautifulSoup objects so back-to-back
# extract_posts / extract_comments / extract_page_metadata / preprocess_for_llm
# calls on the same HTML don't re-parse the same 4-7 MB document 4 times.
# Keyed by ``id(html)`` since BeautifulSoup objects aren't hashable.
# The cache holds strong references to the HTML strings; cap size to
# keep memory bounded for long-running scrape sessions.
_MAX_SOUP_CACHE = 16
_soup_cache: OrderedDict[int, tuple[str, "BeautifulSoup"]] = OrderedDict()


def _get_cached_soup(html: str) -> "BeautifulSoup":
    """Return a cached ``BeautifulSoup`` for ``html``, parsing if needed."""
    key = id(html)
    cached = _soup_cache.get(key)
    if cached is not None and cached[0] is html:
        _soup_cache.move_to_end(key)
        return cached[1]
    soup = BeautifulSoup(html, "html.parser")
    _soup_cache[key] = (html, soup)
    while len(_soup_cache) > _MAX_SOUP_CACHE:
        _soup_cache.popitem(last=False)
    return soup


FACEBOOK_SELECTORS: dict[str, list[dict[str, Any]]] = {
    "post_strategies": [
        {
            "name": "aria-label",
            "method": "aria-label",
            "pattern": re.compile(r"(publicaci.n de|Acciones en esta)", re.IGNORECASE),
        },
        {"name": "data-testid", "method": "data-testid", "value": "post_message"},
        {"name": "userContent", "method": "class", "value": "userContent"},
        {"name": "role-article", "method": "role", "value": "article"},
        {"name": "data-pagelet", "method": "attr", "attr": "data-pagelet"},
        {
            "name": "aria-generic",
            "method": "aria-label",
            "pattern": re.compile(r"Publicaci.n", re.IGNORECASE),
        },
    ],
    "comment_strategies": [
        {
            "name": "data-testid",
            "method": "data-testid",
            "pattern": re.compile(r"comment", re.IGNORECASE),
        },
        {"name": "reply-text", "method": "text", "pattern": re.compile(r"Responder")},
    ],
    "metadata": [
        {"name": "og:title", "property": "og:title"},
        {"name": "og:description", "property": "og:description"},
        {"name": "og:site_name", "property": "og:site_name"},
    ],
}


class FacebookPreprocessor:
    """Preprocess Facebook HTML to extract structured content."""

    # ------------------------------------------------------------------
    # Public API: receives raw HTML, creates soup once
    # ------------------------------------------------------------------

    @staticmethod
    def extract_page_metadata(html: str, url: str) -> dict[str, Any]:
        """Extract page-level metadata from Facebook HTML."""
        soup = _get_cached_soup(html)
        return FacebookPreprocessor._extract_page_metadata_from_soup(soup, url)

    @staticmethod
    def extract_posts(html: str, base_url: str) -> list[dict[str, Any]]:
        """Extract posts from Facebook HTML using multiple DOM strategies."""
        soup = _get_cached_soup(html)
        posts = FacebookPreprocessor._extract_posts_from_soup(soup, base_url)
        if not posts:
            # Fallback: reel/video content lives inside embedded JSON
            # blocks (e.g. ``{"message": {"text": "..."}}``) rather than
            # in the rendered DOM, so DOM-based strategies miss it.
            posts = FacebookPreprocessor._extract_reels_from_json(html, base_url)
        return posts

    @staticmethod
    def extract_comments(html: str, base_url: str) -> list[dict[str, Any]]:
        """Extract comments from Facebook HTML."""
        soup = _get_cached_soup(html)
        return FacebookPreprocessor._extract_comments_from_soup(soup, base_url)

    @staticmethod
    def _strip_internal_refs(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove non-serializable internal references (e.g. _element)."""
        cleaned = []
        for item in data:
            clean = {k: v for k, v in item.items() if not k.startswith("_")}
            if "comments" in clean:
                clean["comments"] = [
                    {k: v for k, v in c.items() if not k.startswith("_")} for c in clean["comments"]
                ]
            cleaned.append(clean)
        return cleaned

    @staticmethod
    def create_hierarchical_json(html: str, url: str) -> dict[str, Any]:
        """Create hierarchical JSON structure from Facebook HTML."""
        soup = _get_cached_soup(html)
        page_meta = FacebookPreprocessor._extract_page_metadata_from_soup(soup, url)
        posts = FacebookPreprocessor._extract_posts_from_soup(soup, url)
        comments = FacebookPreprocessor._extract_comments_from_soup(soup, url)
        posts = FacebookPreprocessor._assign_comments_by_proximity(posts, comments)
        posts = FacebookPreprocessor._strip_internal_refs(posts)
        return {"page": page_meta, "posts": posts}

    @staticmethod
    def preprocess_for_llm(html: str, url: str) -> str:
        """Preprocess HTML for LLM consumption."""
        hierarchical = FacebookPreprocessor.create_hierarchical_json(html, url)
        return FacebookPreprocessor._hierarchy_to_text(hierarchical)

    @staticmethod
    def reduce_html_size(html: str, max_chars: int = 50000) -> str:
        """Reduce HTML size by removing unnecessary elements."""
        if len(html) <= max_chars:
            return html

        soup = _get_cached_soup(html)

        # Remove script, style, iframe, noscript
        for tag in soup(["script", "style", "iframe", "noscript"]):
            tag.decompose()

        # Remove meta tags except useful ones
        keep_meta = ["og:title", "og:description", "og:site_name"]
        for meta in soup.find_all("meta"):
            prop = meta.get("property", "")
            if prop not in keep_meta:
                meta.decompose()

        # Remove external links
        for link in soup.find_all("link"):
            if link.get("rel") != ["stylesheet"]:
                link.decompose()

        result = str(soup)
        if len(result) > max_chars:
            body = soup.find("body")
            if body:
                result = str(body)

        if len(result) > max_chars:
            result = result[:max_chars] + "... [TRUNCATED]"

        logger.info("Reduced HTML from %d to %d chars", len(html), len(result))
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_soup(html: str) -> BeautifulSoup:
        """Parse HTML into BeautifulSoup once."""
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def _extract_page_metadata_from_soup(soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Extract page metadata from an already-parsed soup."""
        result: dict[str, Any] = {"url": url, "title": "", "post_count": 0, "metadata": {}}

        title_tag = soup.find("title")
        if title_tag:
            result["title"] = title_tag.get_text(strip=True)

        for sel in FACEBOOK_SELECTORS["metadata"]:
            meta = soup.find("meta", property=sel["property"])
            if isinstance(meta, Tag):
                result["metadata"][sel["name"]] = meta.get("content", "")

        return result

    @staticmethod
    def _extract_posts_from_soup(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
        """Try multiple strategies to find posts in the parsed soup."""
        posts: list[dict[str, Any]] = []

        strategies = FACEBOOK_SELECTORS["post_strategies"]

        for strategy in strategies:
            if posts:
                break  # Stop once we find posts

            name = strategy["name"]
            method = strategy["method"]
            candidates: list[Tag] = []

            try:
                if method == "aria-label":
                    pattern = strategy.get("pattern")
                    candidates = soup.find_all(
                        "div",
                        attrs={
                            "aria-label": lambda x: x and pattern.search(x) if pattern else False
                        },
                    )
                elif method == "data-testid":
                    value = strategy.get("value", "")
                    candidates = soup.find_all(attrs={"data-testid": value})
                elif method == "class":
                    value = strategy.get("value", "")
                    candidates = soup.find_all(class_=value)
                elif method == "role":
                    value = strategy.get("value", "")
                    candidates = soup.find_all(attrs={"role": value})
                elif method == "attr":
                    attr = strategy.get("attr", "")
                    candidates = soup.find_all(attrs={attr: True})
            except Exception as e:
                logger.debug("Strategy %s failed: %s", name, e)
                continue

            logger.debug("Strategy %s found %d candidates", name, len(candidates))

            for idx, candidate in enumerate(candidates):
                try:
                    post_data = FacebookPreprocessor._parse_generic_post(candidate, idx, base_url)
                    if post_data and post_data.get("text") and len(post_data["text"]) >= 10:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug("Failed to parse candidate %d with strategy %s: %s", idx, name, e)

        # Remove duplicates by text content
        seen_texts: set[str] = set()
        unique_posts = []
        for post in posts:
            text = post.get("text", "").strip()[:200]
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_posts.append(post)

        logger.info("Extracted %d unique posts from HTML", len(unique_posts))
        return unique_posts

    @staticmethod
    def _extract_reels_from_json(html: str, base_url: str) -> list[dict[str, Any]]:
        """Extract reel/video posts from JSON-embedded data in the HTML.

        Facebook's reel and single-post pages ship the post body, owner
        and engagement metadata inside ``<script>`` JSON, not the rendered
        DOM. We look for the canonical ``{"message": {"text": "..."}}``
        shape and walk back to the enclosing object to pull author,
        creation time, post id and feedback counts.

        Args:
            html: Raw page HTML.
            base_url: Original page URL (used to build the post URL).

        Returns:
            List of post dicts in the same shape as DOM-extracted posts.
        """
        # Capture the text (no escapes), the start position, and the
        # opening brace of the enclosing object. We allow backslash
        # escapes (e.g. ``\u00e9``) inside the text value by matching
        # ``\\.`` as part of the capture group.
        pattern = re.compile(
            r'"message"\s*:\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.){10,2000}?)"',
            re.DOTALL,
        )

        posts: list[dict[str, Any]] = []
        seen_texts: set[str] = set()

        for match in pattern.finditer(html):
            raw_text = match.group(1)
            text = FacebookPreprocessor._decode_json_string(raw_text)
            text = text.strip()
            if len(text) < 10:
                continue
            if text in seen_texts:
                continue
            seen_texts.add(text)

            enclosing = FacebookPreprocessor._find_enclosing_object(html, match.start())
            if enclosing is None:
                continue
            enclosing_str = enclosing

            # Wider window: some metadata (e.g. feedback.total_comment_count)
            # lives in sibling objects, not the immediate enclosing block.
            window_end = match.start() + 200000
            window = html[match.start() : min(window_end, len(html))]

            # Author
            author = (
                FacebookPreprocessor._extract_json_field(enclosing_str, "name", scope='"owner"')
                or FacebookPreprocessor._extract_json_field(enclosing_str, "name", scope='"actor"')
                or "Unknown"
            )

            # creation_time (epoch seconds)
            creation_time = FacebookPreprocessor._extract_json_int(enclosing_str, "creation_time")
            publish_time = FacebookPreprocessor._extract_json_int(enclosing_str, "publish_time")
            epoch = creation_time or publish_time
            date_str = ""
            if epoch:
                try:
                    date_str = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()  # noqa: UP017
                except (ValueError, OSError):
                    date_str = ""

            # post_id
            post_id = (
                FacebookPreprocessor._extract_json_field(enclosing_str, "post_id")
                or FacebookPreprocessor._extract_json_field(enclosing_str, "id", scope='"feedback"')
                or FacebookPreprocessor._extract_json_field(enclosing_str, "video_id")
                or ""
            )

            # comment_count from feedback (search broader window)
            comment_count = FacebookPreprocessor._extract_json_int(
                window, "total_comment_count", scope='"feedback"'
            )
            if not comment_count:
                comment_count = FacebookPreprocessor._extract_json_int(window, "comment_count")

            url = base_url
            if post_id:
                url = f"{base_url.rsplit('#', 1)[0]}#post_{post_id}"

            posts.append(
                {
                    "text": text,
                    "author": author,
                    "date": date_str,
                    "likes": 0,
                    "comments_count": comment_count,
                    "shares": 0,
                    "url": url,
                    "post_id": post_id,
                }
            )

        logger.info("Extracted %d reel posts from JSON", len(posts))
        return posts

    @staticmethod
    def _find_enclosing_object(html: str, pos: int, max_back: int = 200000) -> str | None:
        """Return the substring of the top-level ``{...}`` that encloses ``pos``.

        Walks backwards balancing braces, ignoring braces inside JSON
        string literals. Caps the search at ``max_back`` chars to avoid
        pathological scans on huge pages.
        """
        start = None
        depth = 0
        i = pos
        in_string = False
        escape = False
        while i > 0 and pos - i < max_back:
            i -= 1
            ch = html[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "}":
                depth += 1
            elif ch == "{":
                if depth == 0:
                    start = i
                    break
                depth -= 1
        if start is None:
            return None

        end = None
        # We start ``pos`` already inside the enclosing object
        # (typically the inner ``{"message":{...}}``), so we begin at
        # depth 1 and look for the matching closing ``}``.
        depth = 1
        in_string = False
        escape = False
        i = pos
        while i < len(html):
            ch = html[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
            i += 1
        if end is None:
            return None
        return html[start:end]

    @staticmethod
    def _extract_json_field(haystack: str, key: str, scope: str | None = None) -> str | None:
        """Extract the first string value for ``key`` in a JSON blob.

        If ``scope`` is given (e.g. ``'"feedback"'``), only look for ``key``
        after the first occurrence of ``scope`` so we don't accidentally
        hit a same-named field in an unrelated nested object.
        """
        search_from = 0
        if scope:
            idx = haystack.find(scope)
            if idx == -1:
                return None
            search_from = idx + len(scope)
        pattern = re.compile(rf'"{re.escape(key)}"\s*:\s*"((?:[^"\\]|\\.)*)"')
        match = pattern.search(haystack, search_from)
        if not match:
            return None
        return FacebookPreprocessor._decode_json_string(match.group(1))

    @staticmethod
    def _extract_json_int(haystack: str, key: str, scope: str | None = None) -> int:
        """Extract the first integer value for ``key`` in a JSON blob."""
        search_from = 0
        if scope:
            idx = haystack.find(scope)
            if idx == -1:
                return 0
            search_from = idx + len(scope)
        pattern = re.compile(rf'"{re.escape(key)}"\s*:\s*(\d+)')
        match = pattern.search(haystack, search_from)
        if not match:
            return 0
        try:
            return int(match.group(1))
        except ValueError:
            return 0

    @staticmethod
    def _decode_json_string(raw: str) -> str:
        """Decode a JSON string fragment (handles ``\\u00xx``, ``\\n``, etc.).

        Uses ``json.loads`` so the input is parsed as a real JSON string
        literal — that correctly handles unicode escapes (``\u00e9``),
        surrogate pairs (``\ud83d\udea8``), control characters and
        embedded quotes without the latin-1 / mojibake pitfalls of
        ``str.encode().decode('unicode_escape')``.

        Falls back to the raw string when the fragment isn't valid JSON.
        """
        try:
            decoded = json.loads(f'"{raw}"')
        except (json.JSONDecodeError, ValueError):
            return raw
        # Merge any lone UTF-16 surrogate pairs (e.g. ``\ud83d\udea8`` →
        # ``🚨``) so downstream code never sees unpaired surrogates.
        try:
            return decoded.encode("utf-16", "surrogatepass").decode("utf-16")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return decoded

    @staticmethod
    def _extract_comments_from_soup(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
        """Try multiple strategies to find comments in the parsed soup."""
        comments: list[dict[str, Any]] = []

        strategies = FACEBOOK_SELECTORS["comment_strategies"]

        for strategy in strategies:
            if comments:
                break

            name = strategy["name"]
            method = strategy["method"]
            candidates: list[Tag] = []

            try:
                if method == "data-testid":
                    pattern = strategy.get("pattern")
                    candidates = soup.find_all(
                        attrs={
                            "data-testid": lambda x: x and pattern.search(x) if pattern else False
                        }
                    )
                elif method == "text":
                    pattern = strategy.get("pattern")
                    candidates = [
                        p.parent
                        for p in soup.find_all(
                            string=lambda s: (
                                bool(s and pattern.search(str(s))) if pattern else False
                            )  # type: ignore[arg-type]
                        )
                        if isinstance(p.parent, Tag)
                    ]
            except Exception as e:
                logger.debug("Comment strategy %s failed: %s", name, e)
                continue

            for idx, candidate in enumerate(candidates):
                try:
                    comment_data = FacebookPreprocessor._parse_generic_comment(
                        candidate, idx, base_url
                    )
                    if comment_data and comment_data.get("text") and len(comment_data["text"]) >= 5:
                        comments.append(comment_data)
                except Exception as e:
                    logger.debug("Failed to parse comment %d with strategy %s: %s", idx, name, e)

        logger.info("Extracted %d comments from HTML", len(comments))
        return comments

    # ------------------------------------------------------------------
    # Generic parsers (consolidated from old specific parsers)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_generic_post(elem: Tag, idx: int, base_url: str) -> dict[str, Any] | None:
        """Parse a generic Facebook post element using heuristics."""
        full_text = elem.get_text(" ", strip=True)
        if len(full_text) < 10:
            return None

        # Extract author from aria-label if present
        author = "Unknown"
        aria_label = str(elem.get("aria-label", ""))
        if aria_label:
            match = re.search(r"publicaci[óo]n de ([^\"]+?)(?:\"|$)", aria_label, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
            else:
                match = re.search(r"Publicaci[óo]n de (.+)$", aria_label, re.IGNORECASE)
                if match:
                    author = match.group(1).strip()

        # Fallback: look for first link inside the element as author
        if author == "Unknown":
            author_link = elem.find("a", href=re.compile(r"/[^/]+"))
            if author_link:
                author_text = author_link.get_text(strip=True)
                if author_text and len(author_text) < 100:
                    author = author_text

        # Extract date from relative time patterns
        date_str = ""
        relative_patterns = [
            r"(\d+)\s*h\b",
            r"(\d+)\s*min\b",
            r"(\d+)\s*d[ií]as?",
            r"(\d+)\s*sem",
        ]
        for pattern in relative_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                break

        # Try to find absolute date in time tags
        time_elem = elem.find("time")
        if isinstance(time_elem, Tag):
            dt_attr = time_elem.get("datetime")
            if dt_attr:
                date_str = str(dt_attr)

        # Extract engagement counts
        likes = FacebookPreprocessor._extract_number(
            full_text,
            [
                r"(\d+)\s*reacciones?",
                r"(\d+)\s*me gusta",
                r"(\d+)\s*likes?",
            ],
        )
        comments_count = FacebookPreprocessor._extract_number(
            full_text,
            [
                r"(\d+)\s*comentarios?",
            ],
        )
        shares = FacebookPreprocessor._extract_number(
            full_text,
            [
                r"(\d+)\s*compartidos?",
                r"(\d+)\s*veces compartido",
            ],
        )

        # Clean text
        clean_text = strip_post_noise(full_text, author=author)

        return {
            "text": clean_text,
            "author": author,
            "date": date_str,
            "likes": likes,
            "comments_count": comments_count,
            "shares": shares,
            "url": f"{base_url}#post_{idx}",
            "_element": elem,
        }

    @staticmethod
    def _parse_generic_comment(elem: Tag, idx: int, base_url: str) -> dict[str, Any] | None:
        """Parse a generic Facebook comment element using heuristics."""
        text = elem.get_text(" ", strip=True)
        if not text or len(text) < 5:
            return None

        # Extract author
        author = "Unknown"
        author_link = elem.find("a", href=re.compile(r"/[^/]+"))
        if author_link:
            author_text = author_link.get_text(strip=True)
            if author_text and len(author_text) < 100:
                author = author_text

        # Extract date
        date_str = ""
        time_elem = elem.find("time")
        if isinstance(time_elem, Tag):
            dt_attr = time_elem.get("datetime")
            if dt_attr:
                date_str = str(dt_attr)

        # Extract likes
        likes = FacebookPreprocessor._extract_number(
            text,
            [r"(\d+)\s*(?:Me gusta|Like|likes)"],
        )

        return {
            "text": text,
            "author": author,
            "date": date_str,
            "likes": likes,
            "url": f"{base_url}#comment_{idx}",
            "_element": elem,
        }

    # ------------------------------------------------------------------
    # Text cleaning and utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_post_text(full_text: str, author: str) -> str:
        """Clean Facebook post text by removing noise.

        Thin wrapper kept for backwards compatibility — the actual
        cleaning lives in :func:`src.scraper.text_cleaner.strip_post_noise`
        so the same rules apply at scrape time and in the bulk cleaning
        script (``scripts/clean_texts.py``).
        """
        return strip_post_noise(full_text, author=author)

    @staticmethod
    def _extract_number(text: str, patterns: list[str]) -> int:
        """Extract the first number matching any of the given patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return 0

    # ------------------------------------------------------------------
    # Comment-to-post assignment by DOM proximity
    # ------------------------------------------------------------------

    @staticmethod
    def _get_ancestors(elem: Tag | None) -> list[Tag]:
        """Return list of ancestors from element up to body."""
        ancestors: list[Tag] = []
        if elem is None:
            return ancestors
        current: Tag | None = elem
        while current and current.name != "body":
            ancestors.append(current)
            parent = current.parent
            current = parent if isinstance(parent, Tag) else None
        return ancestors

    @staticmethod
    def _dom_distance(post_elem: Tag | None, comment_elem: Tag | None) -> float:
        """Calculate DOM distance between a post element and a comment element."""
        if post_elem is None or comment_elem is None:
            return float("inf")
        post_ancestors = FacebookPreprocessor._get_ancestors(post_elem)
        comment_ancestors = FacebookPreprocessor._get_ancestors(comment_elem)
        for i, p_anc in enumerate(post_ancestors):
            for j, c_anc in enumerate(comment_ancestors):
                if p_anc is c_anc:
                    return float(i + j)
        return float("inf")

    @staticmethod
    def _assign_comments_by_proximity(
        posts: list[dict[str, Any]], comments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Assign each comment to the closest post in the DOM tree."""
        if not posts or not comments:
            return posts

        for post in posts:
            post.setdefault("comments", [])

        for comment in comments:
            comment_elem = comment.get("_element")
            if comment_elem is None:
                posts[0]["comments"].append(comment)
                continue

            best_idx = 0
            best_dist = float("inf")
            for idx, post in enumerate(posts):
                post_elem = post.get("_element")
                dist = FacebookPreprocessor._dom_distance(post_elem, comment_elem)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            posts[best_idx]["comments"].append(comment)

        return posts

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _hierarchy_to_text(hierarchical: dict[str, Any]) -> str:
        """Convert hierarchical JSON to readable text for LLM."""
        lines: list[str] = []
        page = hierarchical.get("page", {})
        lines.append(f"PÁGINA: {page.get('title', '')}")
        lines.append(f"URL: {page.get('url', '')}")
        lines.append("=" * 50)

        for i, post in enumerate(hierarchical.get("posts", []), 1):
            lines.append(f"\nPUBLICACIÓN {i}:")
            lines.append(f"Autor: {post.get('author', 'Desconocido')}")
            lines.append(f"Fecha: {post.get('date', 'Desconocida')}")
            lines.append(f"Likes: {post.get('likes', 0)}")
            lines.append(f"Comentarios: {post.get('comments_count', 0)}")
            lines.append(f"Compartidos: {post.get('shares', 0)}")
            lines.append("-" * 40)
            lines.append(f"Texto:\n{post.get('text', '')}")

            if "comments" in post:
                lines.append(f"\n  COMENTARIOS ({len(post['comments'])}):")
                for j, comment in enumerate(post["comments"], 1):
                    text = comment.get("text", "")[:100]
                    lines.append(f"    {j}. {comment.get('author', 'Anónimo')}: {text}...")
                    lines.append(
                        f"      Likes: {comment.get('likes', 0)}, Fecha: {comment.get('date', '')}"
                    )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Legacy date parsing (kept for compatibility)
    # ------------------------------------------------------------------
    # NOTE: ``_parse_fb_date`` was removed in favor of ``_parse_date``
    # which is used by the scraper. See ``FacebookScraper._parse_date``.
    # ------------------------------------------------------------------
