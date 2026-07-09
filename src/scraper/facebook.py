"""Facebook scraper using ScrapeGraphAI SmartScraperGraph (Playwright) with HTML preprocessing."""

import ast
import asyncio
import hashlib
import json
import logging
import random
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.config import get_settings
from src.scraper.facebook_preprocessor import FacebookPreprocessor
from src.scraper.models import Comment, ContentSource, Post, ScrapeResult
from src.scraper.strategies import (
    ExtractionStrategy,  # noqa: F401  (kept for public API compatibility)
)
from src.scraper.url_utils import is_facebook_reel_url

# Valid JSON escape sequences: " \\ / b f n r t uXXXX
_INVALID_JSON_ESCAPE = re.compile(r'\\([^"\\/bfnrtu])')


def _fix_json_escapes(raw: str) -> str:
    """Remove backslashes before non-standard JSON escape sequences.

    Ollama sometimes returns JSON with invalid escapes like ``\\[``, ``\\]``,
    ``\\_`` which are not valid per the JSON spec.
    """
    return _INVALID_JSON_ESCAPE.sub(r"\1", raw)


def _parse_json_safe(raw: str) -> Any:
    """Parse LLM output as JSON, handling common model quirks.

    Ollama may return Python-style syntax (single quotes, None, True/False)
    or invalid JSON escape sequences (``\\[``, ``\\]``, etc).
    Tries strict JSON first, then fallbacks to Python literal eval.
    """
    if not raw or not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Last-resort cleanup: only replace single quotes when the LLM
    # returned Python-style dicts (``{'key': 'val'}``). This is a
    # blunt hammer that can break valid JSON with apostrophes inside
    # values, so we try it only after strict parsing fails.
    cleaned = raw.replace("'", '"')
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fix invalid JSON escapes (e.g. \[  \]  \_  \.)
    fixed = _fix_json_escapes(cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(fixed)
    except (ValueError, SyntaxError, MemoryError):
        logger.debug("_parse_json_safe could not parse LLM output", exc_info=True)
    return None


logger = logging.getLogger(__name__)


class _PostList(BaseModel):
    """Wrapper model for LLM structured output of posts."""

    posts: list[dict]


class _CommentList(BaseModel):
    """Wrapper model for LLM structured output of comments."""

    comments: list[dict]


class FacebookScraper:
    """Scraper for Facebook using ScrapeGraphAI (Playwright + Ollama)."""

    def __init__(
        self,
        max_posts: int = 50,
        max_comments: int = 100,
        delay: float = 2.0,
        headless: bool = True,
        use_interactive: bool | None = None,
        strategy: ExtractionStrategy | None = None,
    ):
        """Initialize Facebook scraper.

        Args:
            max_posts: Maximum posts to scrape per page
            max_comments: Maximum comments per post
            delay: Delay between requests in seconds
            headless: Run browser in headless mode
            use_interactive: Use interactive comment extraction via Playwright
            strategy: Extraction strategy to use (default: DOMExtractionStrategy)
        """
        self.settings = get_settings()
        self.max_posts = max_posts
        self.max_comments = max_comments
        self.delay = delay
        self.headless = (
            self.settings.scraper.headless
            if hasattr(self.settings.scraper, "headless")
            else headless
        )
        if use_interactive is not None:
            self.use_interactive = use_interactive
        else:
            self.use_interactive = getattr(self.settings.scraper, "use_interactive", True)
        # ``strategy`` is accepted for API compatibility but currently
        # unused — the scraper calls FacebookPreprocessor directly.

    def _generate_post_id(
        self, url: str, author: str, date: str, text: str = "", idx: int = 0
    ) -> str:
        """Generate unique post ID from URL, metadata, and content hash.

        Uses a truncated text hash to avoid collisions when multiple posts
        from the same page have identical or missing author/date.
        """
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        content = f"{url}_{author}_{date}_{text_hash}_{idx}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    @staticmethod
    def _extract_post_id_from_url(url: str) -> str | None:
        """Extract the numeric post id from a Facebook post/reel URL.

        Supports:
          - ``/posts/<id>``         (regular posts)
          - ``story.php?story_fbid=`` (legacy story permalinks)
          - ``/reel/<id>``          (reels)

        Returns ``None`` if the URL doesn't match a known pattern.
        """
        m = re.search(r"/posts/(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"story_fbid=(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/reel/(\d+)", url)
        if m:
            return m.group(1)
        return None

    def _generate_comment_id(
        self, url: str, author: str, date: str, text: str = "", idx: int = 0
    ) -> str:
        """Generate unique comment ID from URL, metadata, and content hash."""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        content = f"{url}_{author}_{date}_{text_hash}_{idx}_comment"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    @staticmethod
    def _detect_login_wall(html: str) -> bool:
        """Detect if Facebook is showing a login wall.

        Uses tight indicators that only appear on the actual login page,
        avoiding false positives from notifications or nav links that
        mention "iniciar sesión" inside real posts.

        A real login wall shows a centered form with the email/password
        inputs and a primary submit button. We look for the form's
        ``name="email"`` input or the password field combined with
        a dedicated login heading.
        """
        lower = html.lower()
        indicators = [
            'name="email"',
            'name="pass"',
            'id="login_form"',
            'autocomplete="current-password"',
            # Spanish login page heading, not a notification
            'class="_9ay7"',
            'aria-label="iniciar sesión"',
        ]
        # Require at least 2 indicators to reduce false positives from
        # stray occurrences of a single term.
        return sum(1 for ind in indicators if ind in lower) >= 2

    @staticmethod
    def _detect_captcha(html: str) -> bool:
        """Detect if Facebook is showing a captcha/security check.

        Uses tight indicators (form/iframe/wrapper for the challenge),
        avoiding noisy internal references like ``arkose_captcha`` that
        appear in normal Facebook pages.
        """
        lower = html.lower()
        indicators = [
            'name="captcha_response"',
            'id="captcha"',
            "checkpoint/checktest",  # Facebook's URL pattern for security checks
            "security_check_challenge",
            "por favor, completa el siguiente control de seguridad",
            "please complete the following security check",
        ]
        return any(ind in lower for ind in indicators)

    USER_AGENTS: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0",
    ]

    # Magic-number defaults. Override via Settings where it matters;
    # keep these as constants so they show up in one place.
    MAX_PAGE_SCROLLS: int = 15
    PAGE_SCROLL_STALE_THRESHOLD: int = 2
    POST_NAVIGATE_WAIT_MS: int = 2000
    SCROLL_PAUSE_MS: int = 1500
    COMMENTS_PANEL_WAIT_MS: int = 3000
    REEL_POLL_ATTEMPTS: int = 5
    REEL_POLL_PAUSE_MS: int = 2000

    def _get_user_agent(self) -> str:
        """Return a rotated user-agent string."""
        return random.choice(self.USER_AGENTS)

    def _build_llm_config(self) -> dict:
        """Build ScrapeGraphAI config from settings."""
        storage_path = self.settings.storage.database_path
        auth_file = Path(storage_path).parent.parent / "data" / "facebook_auth.json"
        config: dict = {
            "llm": {
                "model": f"ollama/{self.settings.ollama.llm_model}",
                "base_url": str(self.settings.ollama.base_url),
                "temperature": self.settings.analyzer.temperature,
                "model_tokens": 8192,
            },
            "loader_kwargs": {
                "timeout": self.settings.scraper.timeout * 1000,
                "load_state": "load",
                "user_agent": self._get_user_agent(),
            },
            "headless": self.headless,
            "verbose": self.settings.app.debug,
            "html_mode": False,
            "timeout": self.settings.scraper.timeout,
        }
        if auth_file.exists():
            config["storage_state"] = str(auth_file)
            logger.info("Usando sesión guardada de Facebook: %s", auth_file)
        return config

    def _cache_path(self, url: str) -> Path:
        """Return cache file path for a given URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        cache_dir = Path(self.settings.storage.database_path).parent / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{url_hash}.html"

    async def _fetch_html_cached(self, url: str, ttl_hours: int = 24) -> str:
        """Fetch HTML with file-based caching.

        Returns cached HTML if it exists and is younger than ``ttl_hours``.
        Otherwise fetches fresh HTML and writes it to cache.

        If the freshly fetched HTML is a login wall or captcha page,
        the cache file is evicted so subsequent calls don't keep
        serving the bad response for ``ttl_hours``.
        """
        cache_file = self._cache_path(url)
        if cache_file.exists():
            age_hours = (
                datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            ).total_seconds() / 3600
            if age_hours < ttl_hours:
                logger.info("Using cached HTML for %s (age: %.1fh)", url, age_hours)
                return cache_file.read_text(encoding="utf-8")

        html = await self._fetch_html_directly(url)
        if html:
            # Don't cache blocked pages — they will resolve once
            # the user re-authenticates or the rate limit clears.
            if self._detect_login_wall(html) or self._detect_captcha(html):
                self._evict_cache(url)
            else:
                cache_file.write_text(html, encoding="utf-8")
                logger.info("Cached HTML for %s (%d chars)", url, len(html))
        return html

    def _evict_cache(self, url: str) -> None:
        """Delete the cache file for ``url`` if it exists."""
        cache_file = self._cache_path(url)
        try:
            if cache_file.exists():
                cache_file.unlink()
                logger.info("Evicted cache for %s", url)
        except OSError as e:
            logger.warning("Failed to evict cache for %s: %s", url, e)

    async def _fetch_html_directly(self, url: str) -> str:
        """Fetch HTML directly using Playwright to allow preprocessing.

        This bypasses ScrapeGraphAI's FetchNode to get raw HTML we can preprocess.
        Uses Playwright directly to avoid ChromiumLoader issues.
        """
        try:
            from playwright.async_api import async_playwright

            config = self._build_llm_config()
            storage_state = config.get("storage_state")
            headless = config.get("headless", True)
            timeout = config.get("timeout", 60) * 1000  # Convert to ms
            load_state = "load"  # Facebook works better with "load" than "networkidle"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                try:
                    # Create context with saved session if available
                    context = await browser.new_context(
                        storage_state=storage_state if storage_state else None
                    )

                    page = await context.new_page()

                    # Set timeout
                    page.set_default_timeout(timeout)

                    # Navigate to URL
                    logger.info("Navigating to %s", url)
                    await page.goto(url, wait_until=load_state)

                    # Wait a bit for dynamic content
                    await page.wait_for_timeout(self.POST_NAVIGATE_WAIT_MS)

                    # Scroll to load more posts (adaptive: stop when scrollHeight stalls)
                    last_height = await page.evaluate("document.body.scrollHeight")
                    stale_scrolls = 0
                    max_scrolls = self.MAX_PAGE_SCROLLS

                    for scroll_i in range(max_scrolls):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(self.SCROLL_PAUSE_MS)

                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            stale_scrolls += 1
                            if stale_scrolls >= self.PAGE_SCROLL_STALE_THRESHOLD:
                                logger.info(
                                    "Scroll height stalled after %d scrolls, stopping",
                                    scroll_i + 1,
                                )
                                break
                        else:
                            stale_scrolls = 0
                            last_height = new_height

                    # Get HTML content
                    html = await page.content()

                    logger.info("Fetched HTML from %s (%d chars)", url, len(html))
                    return html
                finally:
                    try:
                        await browser.close()
                    except Exception:
                        logger.debug("Failed to close browser", exc_info=True)

        except Exception as e:
            logger.error("Error fetching HTML from %s: %s", url, e)
            return ""

    async def _run_graph_with_preprocessing(
        self, url: str, prompt: str, schema: type[BaseModel] | None = None
    ) -> str:
        """Run SmartScraperGraph with HTML preprocessing."""
        try:
            # Step 1: Fetch HTML directly
            html = await self._fetch_html_cached(url)
            if not html:
                return '{"posts": []}' if "posts" in prompt else '{"comments": []}'

            # Step 2: First, try to extract structured data from FULL HTML
            # This is more reliable than sending raw HTML to LLM
            from src.scraper.facebook_preprocessor import FacebookPreprocessor

            logger.info("Extracting structured data from full HTML (%d chars)...", len(html))
            extracted_posts = FacebookPreprocessor.extract_posts(html, url)
            extracted_comments = FacebookPreprocessor.extract_comments(html, url)

            logger.info(
                "Extracted %d posts, %d comments from HTML",
                len(extracted_posts),
                len(extracted_comments),
            )

            # Step 3: Build preprocessed content from extracted data.
            # Use the shared helper that handles line breaks correctly.
            if extracted_posts:
                preprocessed_content = FacebookPreprocessor.preprocess_for_llm(html, url)
                logger.info(
                    "Built preprocessed content from %d posts (%d chars)",
                    len(extracted_posts),
                    len(preprocessed_content),
                )
            else:
                # Fallback: reduce HTML and use it
                logger.warning("No posts extracted from HTML, using reduced HTML as fallback")
                reduced_html = FacebookPreprocessor.reduce_html_size(html, max_chars=50000)
                preprocessed_content = reduced_html

            logger.info("Final content length: %d chars", len(preprocessed_content))

            # Step 4: Create temporary file with preprocessed content
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(preprocessed_content)
                temp_file = f.name

            # Step 5: Run SmartScraperGraph with the preprocessed content as source
            from scrapegraphai.graphs import SmartScraperGraph  # type: ignore[import-untyped]

            config = self._build_llm_config()
            # Force html_mode=True to send text directly to LLM
            config["html_mode"] = True
            config["force"] = True  # Force markdown conversion

            # Debug: log what we're sending to LLM
            logger.debug(
                "Content being sent to LLM (first 500 chars):\\n%s", preprocessed_content[:500]
            )

            # Use the temp file as source
            graph = SmartScraperGraph(prompt=prompt, source=temp_file, config=config, schema=schema)

            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, graph.run)

            # Clean up temp file
            Path(temp_file).unlink(missing_ok=True)

            # graph.run() may return str or dict with 'content' key
            if isinstance(raw, dict):
                result: str = raw.get("content", str(raw))
                return result
            return str(raw)

        except Exception as e:
            logger.error("Error in _run_graph_with_preprocessing for %s: %s", url, e)
            # Fallback to original method
            return await self._run_graph_original(url, prompt, schema)

    async def _run_graph_original(
        self, url: str, prompt: str, schema: type[BaseModel] | None = None
    ) -> str:
        """Original SmartScraperGraph runner (for fallback)."""
        from scrapegraphai.graphs import SmartScraperGraph  # type: ignore[import-untyped]

        config = self._build_llm_config()
        graph = SmartScraperGraph(prompt=prompt, source=url, config=config, schema=schema)

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, graph.run)

        # graph.run() may return str or dict with 'content' key
        if isinstance(raw, dict):
            result: str = raw.get("content", str(raw))
            return result
        return str(raw)

    async def _run_graph(self, url: str, prompt: str, schema: type[BaseModel] | None = None) -> str:
        """Run SmartScraperGraph and return raw response as string.

        Uses preprocessing by default, falls back to original if needed.
        """
        return await self._run_graph_with_preprocessing(url, prompt, schema)

    def _parse_post_list(self, raw: str) -> list[Post]:
        """Parse LLM JSON response into Post objects."""
        data = _parse_json_safe(raw)
        if data is None:
            logger.warning("LLM response is not valid JSON: %.100s", raw)
            return []

        posts_data: list = []
        if isinstance(data, list):
            posts_data = data
        elif isinstance(data, dict):
            extracted = data.get("posts", data.get("post", []))
            if isinstance(extracted, dict):
                posts_data = [extracted]
            elif isinstance(extracted, list):
                posts_data = extracted

        posts = []
        for idx, item in enumerate(posts_data[: self.max_posts]):
            try:
                text = item.get("text", item.get("content", ""))
                post = Post(
                    id=self._generate_post_id(
                        item.get("url", ""),
                        item.get("author", ""),
                        item.get("date", ""),
                        text=text,
                        idx=idx,
                    ),
                    text=text,
                    author=item.get("author", ""),
                    date=self._parse_date(item.get("date")),
                    likes=int(item.get("likes", 0) or 0),
                    comments_count=int(item.get("comments_count", item.get("comments", 0)) or 0),
                    shares=int(item.get("shares", 0) or 0),
                    url=item.get("url", ""),
                )
                posts.append(post)
            except Exception as e:
                logger.warning("Failed to parse post item: %s", e)
                continue

        return posts

    def _parse_comment_list(self, raw: str, post_id: str) -> list[Comment]:
        """Parse LLM JSON response into Comment objects."""
        data = _parse_json_safe(raw)
        if data is None:
            logger.warning("LLM response is not valid JSON: %.100s", raw)
            return []

        comments_data: list = []
        if isinstance(data, list):
            comments_data = data
        elif isinstance(data, dict):
            extracted = data.get("comments", data.get("comment", []))
            if isinstance(extracted, dict):
                comments_data = [extracted]
            elif isinstance(extracted, list):
                comments_data = extracted

        comments = []
        for idx, item in enumerate(comments_data[: self.max_comments]):
            try:
                text = item.get("text", item.get("content", ""))
                comment = Comment(
                    id=self._generate_comment_id(
                        item.get("url", ""),
                        item.get("author", ""),
                        item.get("date", ""),
                        text=text,
                        idx=idx,
                    ),
                    text=text,
                    author=item.get("author", ""),
                    date=self._parse_date(item.get("date")),
                    likes=int(item.get("likes", 0) or 0),
                    post_id=post_id,
                    url=item.get("url", ""),
                )
                comments.append(comment)
            except Exception as e:
                logger.warning("Failed to parse comment item: %s", e)
                continue

        return comments

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Parse date string in various formats."""
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    async def scrape_page(self, page_url: str) -> list[Post]:
        """Scrape posts from a Facebook page using ScrapeGraphAI.

        Uses HTML preprocessing first (DOM-based extraction), which is faster
        and more reliable than LLM-based extraction. Falls back to LLM only
        if preprocessing fails.

        Saves the preprocessed data (page, posts, comments) to the database.

        Args:
            page_url: URL of the Facebook page or post

        Returns:
            List of Post objects
        """
        try:
            # Step 1: Fetch HTML (with cache)
            html = await self._fetch_html_cached(page_url)
            if not html:
                logger.warning("No HTML retrieved from %s", page_url)
                self._save_page_to_db(
                    page_url,
                    [],
                    html_size=0,
                    scrape_status="error",
                    error_message="No HTML retrieved",
                )
                return []

            # Step 1b: Detect blocking states
            if self._detect_login_wall(html):
                logger.error("Facebook login wall detected for %s", page_url)
                self._evict_cache(page_url)
                self._save_page_to_db(
                    page_url,
                    [],
                    html_size=len(html),
                    scrape_status="error",
                    error_message="Facebook login wall detected — session may have expired",
                )
                return []

            if self._detect_captcha(html):
                logger.error("Facebook captcha/security check detected for %s", page_url)
                self._evict_cache(page_url)
                self._save_page_to_db(
                    page_url,
                    [],
                    html_size=len(html),
                    scrape_status="error",
                    error_message="Facebook captcha/security check detected",
                )
                return []

            # Step 2: Try to extract posts using DOM-based preprocessor
            extracted_posts = FacebookPreprocessor.extract_posts(html, page_url)
            extracted_comments = FacebookPreprocessor.extract_comments(html, page_url)

            if extracted_posts:
                logger.info(
                    "Preprocessor extracted %d posts, %d comments from %s",
                    len(extracted_posts),
                    len(extracted_comments),
                    page_url,
                )

                # Get page metadata
                page_meta = FacebookPreprocessor.extract_page_metadata(html, page_url)

                # Save to database
                page_id = self._generate_page_id(page_url)
                self._save_page_to_db(
                    page_url=page_url,
                    posts_data=extracted_posts,
                    html_size=len(html),
                    page_id=page_id,
                    title=page_meta.get("title", ""),
                    preprocessed_data=FacebookPreprocessor.create_hierarchical_json(html, page_url),
                    raw_metadata=page_meta,
                    scrape_status="success",
                )

                # Convert to Post objects
                posts = []
                for idx, item in enumerate(extracted_posts[: self.max_posts]):
                    try:
                        text = item.get("text", "")
                        post = Post(
                            id=self._generate_post_id(
                                item.get("url", ""),
                                item.get("author", ""),
                                item.get("date", ""),
                                text=text,
                                idx=idx,
                            ),
                            text=text,
                            author=item.get("author", ""),
                            date=self._parse_date(item.get("date")),
                            likes=int(item.get("likes", 0) or 0),
                            comments_count=int(item.get("comments_count", 0) or 0),
                            shares=int(item.get("shares", 0) or 0),
                            url=item.get("url", ""),
                        )
                        posts.append(post)
                    except Exception as e:
                        logger.warning("Failed to create Post object: %s", e)
                        continue

                logger.info("Scraped %d posts from %s (via preprocessor)", len(posts), page_url)
                return posts

            # Step 3: Fallback to LLM-based extraction
            logger.info("Preprocessor found no posts, falling back to LLM for %s", page_url)
            prompt = (
                "Extraé todos los posts públicos visibles en esta página de Facebook. "
                "Para cada post, devolvé un objeto JSON con estos campos:\n"
                "- text: texto completo del post\n"
                "- author: nombre del autor o página que publicó\n"
                "- date: fecha de publicación en formato ISO (YYYY-MM-DD)\n"
                "- likes: número de likes (entero, 0 si no se ve)\n"
                "- comments_count: número de comentarios (entero, 0 si no se ve)\n"
                "- shares: número de compartidos (entero, 0 si no se ve)\n"
                "- url: URL completa del post\n\n"
                'Devolvé SOLO un objeto JSON con la clave "posts" conteniendo un array. '
                'Si no hay posts, devolvé {"posts": []}.\n'
                "NO incluyas explicaciones ni texto adicional, solo JSON válido."
            )

            raw = await self._run_graph(page_url, prompt, schema=_PostList)
            posts = self._parse_post_list(raw)

            # Save LLM result to DB
            if posts:
                page_id = self._generate_page_id(page_url)
                llm_posts_data = [
                    {
                        "id": p.id,
                        "text": p.text,
                        "author": p.author,
                        "date": p.date.isoformat() if p.date else "",
                        "likes": p.likes,
                        "comments_count": p.comments_count,
                        "shares": p.shares,
                        "url": p.url,
                    }
                    for p in posts
                ]
                self._save_page_to_db(
                    page_url=page_url,
                    posts_data=llm_posts_data,
                    html_size=len(html),
                    page_id=page_id,
                    scrape_status="partial",
                )

            logger.info("Scraped %d posts from %s (via LLM)", len(posts), page_url)
            return posts

        except Exception as e:
            logger.error("Error scraping page %s: %s", page_url, e)
            self._save_page_to_db(
                page_url, [], html_size=0, scrape_status="error", error_message=str(e)
            )
            return []

    def _generate_page_id(self, url: str) -> str:
        """Generate unique page ID from URL."""
        return hashlib.md5(url.encode()).hexdigest()[:16]

    @staticmethod
    def _clean_posts_for_db(posts_data: list[dict]) -> list[dict]:
        """Remove non-serializable BeautifulSoup tags before saving to DB."""
        cleaned = []
        for post in posts_data:
            clean_post = {k: v for k, v in post.items() if not k.startswith("_")}
            if "comments" in clean_post:
                clean_post["comments"] = [
                    {k: v for k, v in c.items() if not k.startswith("_")}
                    for c in clean_post["comments"]
                ]
            cleaned.append(clean_post)
        return cleaned

    def _save_page_to_db(
        self,
        page_url: str,
        posts_data: list[dict],
        html_size: int = 0,
        page_id: str | None = None,
        title: str = "",
        preprocessed_data: dict | None = None,
        raw_metadata: dict | None = None,
        scrape_status: str = "success",
        error_message: str | None = None,
    ) -> None:
        """Save preprocessed page data to the database.

        Args:
            page_url: URL of the page
            posts_data: List of post dicts (may include 'comments' key)
            html_size: Size of the raw HTML in chars
            page_id: Optional pre-generated page ID
            title: Page title
            preprocessed_data: Hierarchical JSON from preprocessor
            raw_metadata: Page metadata
            scrape_status: 'success', 'error', or 'partial'
            error_message: Optional error message
        """
        try:
            from src.storage import get_database

            db = get_database(self.settings.get_database_url())
            pid = page_id or self._generate_page_id(page_url)

            db.save_page_with_posts(
                page_id=pid,
                url=page_url,
                title=title,
                posts_data=self._clean_posts_for_db(posts_data),
                html_size=html_size,
                preprocessed_data=preprocessed_data,
                raw_metadata=raw_metadata,
                scrape_status=scrape_status,
                error_message=error_message,
            )
            logger.debug("Saved page %s to database with %d posts", page_url, len(posts_data))
        except Exception as e:
            logger.warning("Failed to save page to database: %s", e)

    async def scrape_comments(self, post_url: str, post_id: str = "") -> list[Comment]:
        """Scrape comments from a Facebook post using OmniScraperGraph.

        Args:
            post_url: URL of the Facebook post
            post_id: ID of the parent post

        Returns:
            List of Comment objects
        """
        prompt = (
            "Extraé todos los comentarios visibles en este post de Facebook. "
            "Para cada comentario, devolvé un objeto JSON con estos campos:\n"
            "- text: texto completo del comentario\n"
            "- author: nombre de la persona que comentó\n"
            "- date: fecha de publicación en formato ISO (YYYY-MM-DD)\n"
            "- likes: número de likes del comentario (entero, 0 si no se ve)\n"
            "- url: URL completa del comentario\n\n"
            'Devolvé SOLO un objeto JSON con la clave "comments" conteniendo un array. '
            'Si no hay comentarios, devolvé {"comments": []}.\n'
            "NO incluyas explicaciones ni texto adicional, solo JSON válido."
        )

        await asyncio.sleep(self.delay * random.uniform(0.5, 1.5))

        try:
            raw = await self._run_graph(post_url, prompt, schema=_CommentList)
            comments = self._parse_comment_list(raw, post_id)
            logger.info("Scraped %d comments from %s", len(comments), post_url)
            return comments
        except Exception as e:
            logger.error("Error scraping comments %s: %s", post_url, e)
            return []

    async def _scrape_comments_from_url(self, post_id: str, post_url: str) -> list[Comment]:
        """Try to scrape comments from ``facebook.com/{post_id}/comments/``.

        Facebook loads comments lazily on the post page, but the
        ``/comments/`` endpoint sometimes returns a page with the first
        batch already in the HTML. This is a cheaper alternative to the
        interactive scroll-and-click approach.

        Args:
            post_id: Numeric post id extracted from the JSON.
            post_url: Original post URL (used as a base for the comments URL
                and as ``parent_id`` for the resulting ``Comment`` objects).

        Returns:
            List of ``Comment`` objects, empty if the request fails or
            no comments are found.
        """
        if not post_id or not str(post_id).isdigit():
            return []

        comments_url = f"https://www.facebook.com/{post_id}/comments/"
        logger.info("Trying /comments/ URL for post %s: %s", post_id, comments_url)

        try:
            html = await self._fetch_html_cached(comments_url)
        except Exception as e:
            logger.warning("Failed to fetch /comments/ URL %s: %s", comments_url, e)
            return []

        if not html:
            return []
        if self._detect_login_wall(html) or self._detect_captcha(html):
            logger.warning("Login wall/captcha on /comments/ URL %s", comments_url)
            self._evict_cache(comments_url)
            return []

        comments_data = FacebookPreprocessor.extract_comments(html, comments_url)
        if not comments_data:
            logger.info("No comments found via /comments/ URL for %s", post_id)
            return []

        out: list[Comment] = []
        for idx, c in enumerate(comments_data):
            try:
                text = (c.get("text") or "").strip()
                if len(text) < 5:
                    continue
                out.append(
                    Comment(
                        id=self._generate_comment_id(
                            comments_url,
                            c.get("author", ""),
                            c.get("date", ""),
                            text=text,
                            idx=idx,
                        ),
                        text=text,
                        author=c.get("author", "Unknown"),
                        date=self._parse_date(c.get("date")),
                        likes=int(c.get("likes", 0) or 0),
                        post_id=post_id,
                        url=c.get("url", f"{comments_url}#comment_{idx}"),
                    )
                )
            except Exception as e:
                logger.debug("Failed to build Comment from /comments/ data: %s", e)
                continue

        logger.info("Extracted %d comments from /comments/ URL %s", len(out), post_id)
        return out

    async def _scrape_comments_interactive(self, post_url: str) -> list[Comment]:
        """Open the post in a browser, click the comments button, and
        expand the dialog to extract visible comments.

        Used as a fallback for posts/reels where neither the HTML nor the
        ``/comments/`` endpoint exposes a usable comment list. Returns an
        empty list on any failure (timeouts, EPIPE, missing buttons).
        """
        try:
            from playwright.async_api import async_playwright

            from src.scraper.comment_interactor import CommentInteractor

            config = self._build_llm_config()
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=config.get("headless", True))
                context = await browser.new_context(
                    storage_state=config.get("storage_state") or None
                )
                page = await context.new_page()
                page.set_default_timeout(self.settings.scraper.timeout * 1000)
                await page.goto(post_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(self.COMMENTS_PANEL_WAIT_MS)

                interactor = CommentInteractor(
                    page=page,
                    max_comments=self.max_comments,
                    delay=self.delay,
                )
                comments = await interactor.extract_all_visible_comments()
                await browser.close()
                return comments
        except Exception as e:
            logger.warning("Interactive comment extraction failed for %s: %s", post_url, e)
            return []

    async def _scrape_reel_comments_interactive(self, reel_url: str) -> list[Comment]:
        """Open a reel in a browser and click the comment count to load
        the comments panel.

        Unlike posts, reels don't have a "Comments" button that opens a
        modal. The trick is to click the engagement count element
        (``aria-label="Comentar"`` or the text ``"<n> mil"``) which
        expands the comments inline. This method:

        1. Navigates to the reel URL
        2. Clicks the "Comentar" / comment-count element
        3. Scrolls the now-expanded panel to load more comments
        4. Clicks "Ver más comentarios" as needed
        5. Extracts comment elements with ``aria-label="Comentario de..."``

        Returns an empty list on any failure.
        """
        browser = None
        try:
            from playwright.async_api import async_playwright

            from src.scraper.comment_interactor import CommentInteractor

            config = self._build_llm_config()
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=config.get("headless", True))
                context = await browser.new_context(
                    storage_state=config.get("storage_state") or None
                )
                page = await context.new_page()
                # Cap timeout to avoid hanging on slow loads
                page.set_default_timeout(min(self.settings.scraper.timeout * 1000, 20000))
                await page.goto(reel_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(self.COMMENTS_PANEL_WAIT_MS)

                # Try to click the "Comentar" / comment-count element
                # to expand the comments inline.
                clicked = False
                try:
                    comment_btn = page.locator('[aria-label="Comentar" i]').first
                    if await comment_btn.count() > 0:
                        await comment_btn.click(timeout=5000)
                        clicked = True
                        logger.info("Clicked 'Comentar' button for reel %s", reel_url)
                except Exception as e:
                    logger.debug("Could not click 'Comentar' button: %s", e)

                if not clicked:
                    try:
                        count_btn = page.locator("text=/^\\d+([.,]\\d+)?\\s*mil$/i").first
                        if await count_btn.count() > 0:
                            await count_btn.click(timeout=5000)
                            clicked = True
                            logger.info("Clicked count text for reel %s", reel_url)
                    except Exception as e:
                        logger.debug("Could not click count text: %s", e)

                if not clicked:
                    logger.warning("Could not find comment button for reel %s", reel_url)
                    try:
                        await browser.close()
                    except Exception:
                        logger.debug("Failed to close browser", exc_info=True)
                    return []

                # Give Facebook time to start loading, then poll for
                # comments with scroll-and-retry to handle reels where
                # the lazy load is slow. Up to ~10s total.
                interactor = CommentInteractor(
                    page=page,
                    max_comments=self.max_comments,
                    delay=self.delay,
                )

                elements: list = []
                for attempt in range(5):
                    try:
                        # Try to wait for the first comment element with
                        # a short timeout on the last attempts only.
                        if attempt == 0:
                            try:
                                await page.wait_for_selector(
                                    '[aria-label^="Comentario de" i]',
                                    timeout=8000,
                                    state="visible",
                                )
                            except Exception:
                                logger.debug("wait_for_selector for Comentario de timed out")

                        # Scroll down a bit to trigger lazy loading of
                        # comments that may be below the fold.
                        try:
                            await page.evaluate(
                                "window.scrollBy(0, window.innerHeight * 0.6)",
                                timeout=5000,
                            )
                            await page.wait_for_timeout(1500)
                        except Exception:
                            logger.debug("Scroll after Comentar failed", exc_info=True)

                        elements = await interactor.find_comment_elements_in(page)
                        if elements:
                            logger.info(
                                "Found %d comment elements on attempt %d for %s",
                                len(elements),
                                attempt + 1,
                                reel_url,
                            )
                            break
                    except Exception:
                        logger.debug(
                            "Comment polling attempt %d failed for %s",
                            attempt + 1,
                            reel_url,
                            exc_info=True,
                        )
                    await page.wait_for_timeout(2000)

                if not elements:
                    logger.info("No comment elements after polling for %s", reel_url)

                # Parse each comment element directly without scrolling
                comments: list[Comment] = []
                if elements:
                    for idx, el in enumerate(elements[: self.max_comments]):
                        try:
                            parsed = await interactor._parse_element(el)
                            if parsed and parsed.get("text"):
                                cid = self._generate_comment_id(
                                    reel_url,
                                    parsed.get("author", ""),
                                    "",
                                    text=parsed.get("text", ""),
                                    idx=idx,
                                )
                                comments.append(
                                    Comment(
                                        id=cid,
                                        text=parsed.get("text", ""),
                                        author=parsed.get("author", "Unknown"),
                                        likes=parsed.get("likes", 0),
                                        post_id=self._extract_post_id_from_url(reel_url) or "",
                                        url=f"{reel_url}#comment_{idx}",
                                    )
                                )
                        except Exception:
                            logger.debug(
                                "Failed to parse reel comment %d for %s",
                                idx,
                                reel_url,
                                exc_info=True,
                            )
                            continue

                try:
                    await browser.close()
                except Exception:
                    logger.debug("Failed to close browser", exc_info=True)
                return comments
        except Exception as e:
            logger.warning("Reel interactive comment extraction failed for %s: %s", reel_url, e)
            if browser:
                try:
                    await browser.close()
                except Exception:
                    logger.debug("Failed to close browser", exc_info=True)
            return []

    async def scrape_post(self, post_url: str) -> list[Post]:
        """Scrape a single Facebook post/reel (URL + comments).

        Args:
            post_url: URL of the Facebook post or reel

        Returns:
            List with a single Post object (or empty on failure)
        """
        is_reel = is_facebook_reel_url(post_url)
        content_type = "reel" if is_reel else "post"

        try:
            html = await self._fetch_html_cached(post_url)
            if not html:
                logger.warning("No HTML retrieved from %s", post_url)
                return []

            if self._detect_login_wall(html):
                logger.error("Facebook login wall detected for %s", post_url)
                self._evict_cache(post_url)
                return []

            if self._detect_captcha(html):
                logger.error("Facebook captcha detected for %s", post_url)
                self._evict_cache(post_url)
                return []

            # Try DOM extraction first
            extracted_posts = FacebookPreprocessor.extract_posts(html, post_url)
            page_meta = FacebookPreprocessor.extract_page_metadata(html, post_url)

            if not extracted_posts:
                logger.info(
                    "No %s found via preprocessor, falling back to LLM for %s",
                    content_type,
                    post_url,
                )
                prompt = (
                    f"Extraé el {content_type} visible en esta URL de Facebook. "
                    "Devolvé un objeto JSON con la clave 'posts' conteniendo un array "
                    "con un único objeto que tenga estos campos:\n"
                    "- text: texto completo del post\n"
                    "- author: nombre del autor o página\n"
                    "- date: fecha en formato ISO (YYYY-MM-DD)\n"
                    "- likes: número de likes\n"
                    "- comments_count: número de comentarios\n"
                    "- shares: número de compartidos\n"
                    "- url: URL completa\n\n"
                    'Si no hay contenido, devolvé {"posts": []}.\n'
                    "Solo JSON válido, sin explicaciones."
                )
                raw = await self._run_graph(post_url, prompt, schema=_PostList)
                extracted_posts = [
                    {
                        "text": p.text,
                        "author": p.author,
                        "date": p.date.isoformat() if p.date else "",
                        "likes": p.likes,
                        "comments_count": p.comments_count,
                        "shares": p.shares,
                        "url": p.url,
                    }
                    for p in self._parse_post_list(raw)
                ]

            if not extracted_posts:
                logger.warning("No %s content extracted from %s", content_type, post_url)
                return []

            # Build single Post object from first extracted item
            item = extracted_posts[0]
            text = item.get("text", "")
            post_id = self._generate_post_id(
                post_url,
                item.get("author", ""),
                item.get("date", ""),
                text=text,
                idx=0,
            )
            post = Post(
                id=post_id,
                text=text,
                author=item.get("author", ""),
                date=self._parse_date(item.get("date")),
                likes=int(item.get("likes", 0) or 0),
                comments_count=int(item.get("comments_count", 0) or 0),
                shares=int(item.get("shares", 0) or 0),
                url=post_url,
                source=ContentSource.FACEBOOK_POST,
            )

            # Extract comments using a three-level fallback strategy:
            #   1. /comments/ endpoint (cheap, may have first batch)
            #   2. Interactive (dialog for posts, scroll for reels)
            #   3. LLM on the post HTML (last resort, often empty since
            #      comments are loaded lazily)
            comments: list[Comment] = []
            # Only pass a numeric post_id to the /comments/ endpoint:
            # share/photo/story URLs lack a numeric id and would be
            # silently rejected by the endpoint's isdigit() check.
            numeric_post_id = self._extract_post_id_from_url(post_url)
            comments = await self._scrape_comments_from_url(numeric_post_id or "", post_url)
            if not comments and self.use_interactive:
                if is_reel:
                    comments = await self._scrape_reel_comments_interactive(post_url)
                else:
                    comments = await self._scrape_comments_interactive(post_url)
            if not comments:
                comments = await self.scrape_comments(post_url, post.id)

            post.comments = comments
            post.comments_count = len(comments)

            # Save to DB
            self._save_page_to_db(
                page_url=post_url,
                posts_data=[
                    {
                        "id": post.id,
                        "text": post.text,
                        "author": post.author,
                        "date": post.date.isoformat() if post.date else "",
                        "likes": post.likes,
                        "comments_count": post.comments_count,
                        "shares": post.shares,
                        "url": post.url,
                        "source": post.source.value,
                        "comments": [c.to_dict() for c in comments],
                    }
                ],
                html_size=len(html),
                page_id=self._generate_page_id(post_url),
                title=page_meta.get("title", ""),
                preprocessed_data=FacebookPreprocessor.create_hierarchical_json(html, post_url),
                scrape_status="success",
            )

            logger.info(
                "Scraped %s from %s with %d comments", content_type, post_url, len(comments)
            )
            return [post]

        except Exception as e:
            logger.error("Error scraping %s %s: %s", content_type, post_url, e)
            return []

    async def scrape_reel(self, reel_url: str) -> list[Post]:
        """Scrape a single Facebook reel.

        Reels are handled similarly to posts but logged/distinguished separately.
        Future enhancements may use reel-specific selectors.
        """
        logger.info("Scraping reel: %s", reel_url)
        return await self.scrape_post(reel_url)

    def _run_sync(self, coro):
        """Run an async coroutine from sync code, creating a loop if needed."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def scrape_post_sync(self, post_url: str) -> list[Post]:
        """Synchronous version of scrape_post."""
        return self._run_sync(self.scrape_post(post_url))

    def scrape_reel_sync(self, reel_url: str) -> list[Post]:
        """Synchronous version of scrape_reel."""
        return self._run_sync(self.scrape_reel(reel_url))

    async def scrape_full(self, page_url: str) -> ScrapeResult:
        """Scrape page and all comments.

        Args:
            page_url: URL of the Facebook page

        Returns:
            ScrapeResult with posts and comments
        """
        result = ScrapeResult(success=True)

        try:
            if self.use_interactive:
                posts = await self.scrape_page_interactive(page_url)
                result.posts.extend(posts)
                result.posts_found = len(posts)
                result.comments_found = sum(len(p.comments) for p in posts)
            else:
                posts = await self.scrape_page(page_url)
                result.posts.extend(posts)
                result.posts_found = len(posts)

                for i, post in enumerate(posts):
                    if post.url:
                        if i > 0:
                            await asyncio.sleep(self.delay * random.uniform(0.5, 1.5))
                        comments = await self.scrape_comments(post.url, post.id)
                        result.comments.extend(comments)

                result.comments_found = len(result.comments)

            result.pages_scraped = 1

        except Exception as e:
            result.success = False
            result.add_error(str(e))

        return result

    async def scrape_page_interactive(self, page_url: str) -> list[Post]:
        """Scrape posts with interactive comment extraction.

        Keeps Playwright alive to expand "Ver más comentarios" buttons and
        extract real comments from the live DOM.

        Args:
            page_url: URL of the Facebook page

        Returns:
            List of Post objects, each with ``.comments`` populated
        """
        try:
            from playwright.async_api import async_playwright

            from src.scraper.comment_interactor import CommentInteractor

            config = self._build_llm_config()
            headless = config.get("headless", True)

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                storage_state = config.get("storage_state")
                context = await browser.new_context(
                    storage_state=storage_state if storage_state else None
                )
                page = await context.new_page()
                page.set_default_timeout(self.settings.scraper.timeout * 1000)

                await page.goto(page_url, wait_until="load")
                await page.wait_for_timeout(self.COMMENTS_PANEL_WAIT_MS)

                # ---- Scroll para cargar más posts ----
                max_posts_target = min(self.max_posts, 10)
                logger.info("Scrolling to load ~%d posts...", max_posts_target)

                last_count = 0
                stale_scrolls = 0

                for scroll_attempt in range(8):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1500)

                    try:
                        post_count = len(
                            await page.locator(
                                'div[aria-label*="publicación" i], '
                                'div[aria-label*="Acciones en esta" i]'
                            ).all()
                        )
                    except Exception:
                        logger.debug("Failed to count posts on scroll", exc_info=True)
                        post_count = 0

                    logger.info(
                        "Scroll %d: %d posts visible",
                        scroll_attempt + 1,
                        post_count,
                    )

                    if post_count >= max_posts_target:
                        logger.info("Reached %d posts, stopping scroll", post_count)
                        break

                    if post_count == last_count:
                        stale_scrolls += 1
                        if stale_scrolls >= 2:
                            logger.info(
                                "No new posts after %d stale scrolls, stopping", stale_scrolls
                            )
                            break
                    else:
                        stale_scrolls = 0
                        last_count = post_count

                html = await page.content()
                logger.info("Fetched HTML (%d chars) with scroll", len(html))

                extracted_posts = FacebookPreprocessor.extract_posts(html, page_url)
                if not extracted_posts:
                    logger.warning("No posts found in page")
                    await browser.close()
                    return []

                interactor = CommentInteractor(
                    page=page,
                    max_comments=self.max_comments,
                    delay=self.delay,
                )

                posts_with_comments = []
                for idx, item in enumerate(extracted_posts[: self.max_posts]):
                    text = item.get("text", "")
                    post_id = self._generate_post_id(
                        item.get("url", ""),
                        item.get("author", ""),
                        item.get("date", ""),
                        text=text,
                        idx=idx,
                    )

                    post_obj = Post(
                        id=post_id,
                        text=item.get("text", ""),
                        author=item.get("author", ""),
                        date=self._parse_date(item.get("date")),
                        likes=int(item.get("likes", 0) or 0),
                        comments_count=int(item.get("comments_count", 0) or 0),
                        shares=int(item.get("shares", 0) or 0),
                        url=item.get("url", ""),
                    )

                    logger.info(
                        "Post %d/%d: abriendo modal de comentarios...",
                        idx + 1,
                        min(len(extracted_posts), self.max_posts),
                    )

                    comments = await interactor.extract_comments_for_post(idx)
                    post_obj.comments = comments
                    post_obj.comments_count = len(comments)

                    posts_with_comments.append(post_obj)

                    if idx < len(extracted_posts) - 1:
                        await asyncio.sleep(self.delay * random.uniform(0.5, 1.5))

                await browser.close()

                logger.info(
                    "Interactive scrape: %d posts, %d total comments",
                    len(posts_with_comments),
                    sum(len(p.comments) for p in posts_with_comments),
                )

                # Save page with posts and comments to DB
                posts_data = []
                for p_obj in posts_with_comments:
                    pd = {
                        "id": p_obj.id,
                        "text": p_obj.text,
                        "author": p_obj.author,
                        "date": p_obj.date.isoformat() if p_obj.date else "",
                        "likes": p_obj.likes,
                        "comments_count": p_obj.comments_count,
                        "shares": p_obj.shares,
                        "url": p_obj.url,
                    }
                    if hasattr(p_obj, "comments") and p_obj.comments:
                        pd["comments"] = [
                            {
                                "id": c.id,
                                "text": c.text,
                                "author": c.author,
                                "date": c.date.isoformat() if c.date else "",
                                "likes": c.likes,
                                "url": c.url,
                            }
                            for c in p_obj.comments
                        ]
                    posts_data.append(pd)

                page_meta = FacebookPreprocessor.extract_page_metadata(html, page_url)
                self._save_page_to_db(
                    page_url=page_url,
                    posts_data=posts_data,
                    html_size=len(html),
                    page_id=self._generate_page_id(page_url),
                    title=page_meta.get("title", ""),
                    preprocessed_data=FacebookPreprocessor.create_hierarchical_json(html, page_url),
                    scrape_status="success",
                )

                logger.info(
                    "Interactive scrape: %d posts, %d total comments",
                    len(posts_with_comments),
                    sum(len(p.comments) for p in posts_with_comments),
                )
                return posts_with_comments

        except Exception as e:
            logger.error("Interactive scrape failed for %s: %s", page_url, e, exc_info=True)
            return []

    def scrape_page_sync(self, page_url: str) -> list[Post]:
        """Synchronous version of scrape_page."""
        return self._run_sync(self.scrape_page(page_url))

    def scrape_comments_sync(self, post_url: str, post_id: str = "") -> list[Comment]:
        """Synchronous version of scrape_comments."""
        return self._run_sync(self.scrape_comments(post_url, post_id))

    def scrape_page_interactive_sync(self, page_url: str) -> list[Post]:
        """Synchronous version of scrape_page_interactive."""
        return self._run_sync(self.scrape_page_interactive(page_url))

    def scrape_full_sync(self, page_url: str) -> ScrapeResult:
        """Synchronous version of scrape_full."""
        return self._run_sync(self.scrape_full(page_url))
