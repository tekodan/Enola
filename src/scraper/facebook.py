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
from src.scraper.models import Comment, Post, ScrapeResult

# Valid JSON escape sequences: " \\ / b f n r t uXXXX
_INVALID_JSON_ESCAPE = re.compile(r'\\([^"\\/bfnrtu])')


def _fix_json_escapes(raw: str) -> str:
    """Remove backslashes before non-standard JSON escape sequences.

    Ollama sometimes returns JSON with invalid escapes like ``\\[``, ``\\]``,
    ``\\_`` which are not valid per the JSON spec.
    """
    return _INVALID_JSON_ESCAPE.sub(r'\1', raw)


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
        pass
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
    ):
        """Initialize Facebook scraper.

        Args:
            max_posts: Maximum posts to scrape per page
            max_comments: Maximum comments per post
            delay: Delay between requests in seconds
            headless: Run browser in headless mode
        """
        self.settings = get_settings()
        self.max_posts = max_posts
        self.max_comments = max_comments
        self.delay = delay
        self.headless = self.settings.scraper.headless if hasattr(self.settings.scraper, 'headless') else headless

    def _generate_post_id(self, url: str, author: str, date: str) -> str:
        """Generate unique post ID from URL and metadata."""
        content = f"{url}_{author}_{date}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _generate_comment_id(self, url: str, author: str, date: str) -> str:
        """Generate unique comment ID."""
        content = f"{url}_{author}_{date}_comment"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _build_llm_config(self) -> dict:
        """Build ScrapeGraphAI config from settings."""
        storage_path = self.settings.storage.database_path
        auth_file = (
            Path(storage_path).parent.parent / "data" / "facebook_auth.json"
        )
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
                await page.wait_for_timeout(2000)

                # Scroll to load more posts
                for scroll_i in range(10):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1500)
                    cur = len(await page.locator(
                        'div[aria-label*="publicación" i]'
                    ).all())
                    if cur >= 5:
                        break

                # Get HTML content
                html = await page.content()

                await browser.close()

                logger.info("Fetched HTML from %s (%d chars)", url, len(html))
                return html

        except Exception as e:
            logger.error("Error fetching HTML from %s: %s", url, e)
            return ""

    async def _run_graph_with_preprocessing(
        self, url: str, prompt: str, schema: type[BaseModel] | None = None
    ) -> str:
        """Run SmartScraperGraph with HTML preprocessing."""
        try:
            # Step 1: Fetch HTML directly
            html = await self._fetch_html_directly(url)
            if not html:
                return '{"posts": []}' if "posts" in prompt else '{"comments": []}'

            # Step 2: First, try to extract structured data from FULL HTML
            # This is more reliable than sending raw HTML to LLM
            from src.scraper.facebook_preprocessor import FacebookPreprocessor

            logger.info("Extracting structured data from full HTML (%d chars)...", len(html))
            extracted_posts = FacebookPreprocessor.extract_posts(html, url)
            extracted_comments = FacebookPreprocessor.extract_comments(html, url)

            logger.info("Extracted %d posts, %d comments from HTML",
                       len(extracted_posts), len(extracted_comments))

            # Step 3: Build preprocessed content from extracted data
            if extracted_posts:
                preprocessed_content = FacebookPreprocessor.create_hierarchical_json(html, url)
                # Convert to readable text
                lines = []
                lines.append(f"PÁGINA: {preprocessed_content['page'].get('title', '')}")
                lines.append(f"URL: {url}")
                lines.append("=" * 50)

                for i, post in enumerate(preprocessed_content['posts'], 1):
                    lines.append(f"\\nPUBLICACIÓN {i}:")
                    lines.append(f"Autor: {post.get('author', 'Desconocido')}")
                    lines.append(f"Fecha: {post.get('date', 'Desconocida')}")
                    lines.append(f"Likes: {post.get('likes', 0)}")
                    lines.append(f"Comentarios: {post.get('comments_count', 0)}")
                    lines.append(f"Compartidos: {post.get('shares', 0)}")
                    lines.append("-" * 40)
                    lines.append(f"Texto:\\n{post.get('text', '')}")

                preprocessed_content = "\\n".join(lines)
                logger.info("Built preprocessed content from %d posts (%d chars)",
                           len(extracted_posts), len(preprocessed_content))
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
            logger.debug("Content being sent to LLM (first 500 chars):\\n%s", preprocessed_content[:500])

            # Use the temp file as source
            graph = SmartScraperGraph(
                prompt=prompt,
                source=temp_file,
                config=config,
                schema=schema
            )

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

    async def _run_graph(
        self, url: str, prompt: str, schema: type[BaseModel] | None = None
    ) -> str:
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
        for item in posts_data[: self.max_posts]:
            try:
                post = Post(
                    id=self._generate_post_id(
                        item.get("url", ""),
                        item.get("author", ""),
                        item.get("date", ""),
                    ),
                    text=item.get("text", item.get("content", "")),
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
        for item in comments_data[: self.max_comments]:
            try:
                comment = Comment(
                    id=self._generate_comment_id(
                        item.get("url", ""),
                        item.get("author", ""),
                        item.get("date", ""),
                    ),
                    text=item.get("text", item.get("content", "")),
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
            # Step 1: Fetch HTML directly
            html = await self._fetch_html_directly(page_url)
            if not html:
                logger.warning("No HTML retrieved from %s", page_url)
                self._save_page_to_db(page_url, [], html_size=0, scrape_status="error",
                                     error_message="No HTML retrieved")
                return []

            # Step 2: Try to extract posts using DOM-based preprocessor
            extracted_posts = FacebookPreprocessor.extract_posts(html, page_url)
            extracted_comments = FacebookPreprocessor.extract_comments(html, page_url)

            if extracted_posts:
                logger.info("Preprocessor extracted %d posts, %d comments from %s",
                          len(extracted_posts), len(extracted_comments), page_url)

                # Attach comments to posts (simple strategy: all comments to first post)
                if extracted_comments and extracted_posts:
                    extracted_posts[0]["comments"] = extracted_comments

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
                for item in extracted_posts[: self.max_posts]:
                    try:
                        post = Post(
                            id=self._generate_post_id(
                                item.get("url", ""),
                                item.get("author", ""),
                                item.get("date", ""),
                            ),
                            text=item.get("text", ""),
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
            self._save_page_to_db(page_url, [], html_size=0, scrape_status="error", error_message=str(e))
            return []

    def _generate_page_id(self, url: str) -> str:
        """Generate unique page ID from URL."""
        return hashlib.md5(url.encode()).hexdigest()[:16]

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
                posts_data=posts_data,
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

    async def scrape_full(self, page_url: str) -> ScrapeResult:
        """Scrape page and all comments.

        Args:
            page_url: URL of the Facebook page

        Returns:
            ScrapeResult with posts and comments
        """
        result = ScrapeResult(success=True)

        try:
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
                await page.wait_for_timeout(3000)

                # ---- Scroll para cargar más posts ----
                max_posts_target = min(self.max_posts, 10)
                logger.info("Scrolling to load ~%d posts...", max_posts_target)

                last_count = 0
                stale_scrolls = 0

                for scroll_attempt in range(8):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1500)

                    try:
                        post_count = len(await page.locator(
                            'div[aria-label*="publicación" i], '
                            'div[aria-label*="Acciones en esta" i]'
                        ).all())
                    except Exception:
                        post_count = 0

                    logger.info(
                        "Scroll %d: %d posts visible",
                        scroll_attempt + 1, post_count,
                    )

                    if post_count >= max_posts_target:
                        logger.info("Reached %d posts, stopping scroll", post_count)
                        break

                    if post_count == last_count:
                        stale_scrolls += 1
                        if stale_scrolls >= 2:
                            logger.info("No new posts after %d stale scrolls, stopping", stale_scrolls)
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
                    post_id = self._generate_post_id(
                        item.get("url", ""),
                        item.get("author", ""),
                        item.get("date", ""),
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
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.scrape_page(page_url))

    def scrape_comments_sync(self, post_url: str, post_id: str = "") -> list[Comment]:
        """Synchronous version of scrape_comments."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.scrape_comments(post_url, post_id))

    def scrape_page_interactive_sync(self, page_url: str) -> list[Post]:
        """Synchronous version of scrape_page_interactive."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.scrape_page_interactive(page_url))

    def scrape_full_sync(self, page_url: str) -> ScrapeResult:
        """Synchronous version of scrape_full."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.scrape_full(page_url))
