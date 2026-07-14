"""Comment interaction module — extracts Facebook comments from modal dialogs.

Flow for each post:
  1. Find the "Comentarios" button in the page
  2. Click it → a modal dialog opens with the comments
  3. Find the modal (``[role="dialog"]``)
  4. Inside the modal, expand "Ver más comentarios" and extract all comments
  5. Close the modal before processing the next post
"""

import asyncio
import hashlib
import logging
import re

from src.scraper.models import Comment
from src.scraper.text_cleaner import strip_comment_noise

logger = logging.getLogger(__name__)


def clean_comment_text(
    raw_text: str, known_author: str | None = None
) -> tuple[str, str | None, int]:
    """Strip the author prefix and the trailing UI bits from a comment.

    Facebook renders each comment as a single string::

        [Fan destacado ] <author> <body> <N> sem Me gusta Responder [Editado] <count>

    This helper extracts ``(clean_text, time_ago, responses)`` so the
    body goes into ``Comment.text`` and the metadata goes into the
    dedicated columns (``time_ago``, ``responses``).

    Thin wrapper around :func:`src.scraper.text_cleaner.strip_comment_noise`.
    Kept here for backwards compatibility — the rest of the codebase
    still imports ``clean_comment_text`` from this module.

    Args:
        raw_text: Text as extracted from the DOM (includes author
            prefix and trailing buttons).
        known_author: Author of the comment (when known). If supplied,
            the prefix is removed by direct comparison instead of a
            regex guess, which is more robust for non-Spanish names.

    Returns:
        Tuple of ``(clean_text, time_ago, responses)``. When no
        trailing UI bits are found, ``time_ago`` is ``None`` and
        ``responses`` is 0.
    """
    return strip_comment_noise(raw_text, known_author=known_author)


class CommentInteractor:
    """Extracts Facebook comments from modal dialogs using Playwright.

    Args:
        page: Playwright page instance (must be navigated to a Facebook page)
        max_comments: Maximum comments to extract per post
        delay: Seconds to wait between interactions
    """

    BUTTON_SELECTORS = [
        'a[href*="/posts/" i]',
        'a[href*="/photo/" i]',
        'a[href*="/videos/" i]',
    ]

    POST_SELECTOR = 'div[aria-label*="publicación" i], div[aria-label*="Acciones en esta" i]'

    MODAL_SELECTORS = [
        '[role="dialog"]',
        'div[aria-label="Comentarios" i]',
        'div[aria-label*="omentarios" i]',
    ]

    COMMENT_SELECTOR = '[aria-label^="Comentario de" i]'

    MORE_SELECTOR = (
        ':has-text("Ver más comentarios"), '
        ':has-text("View more comments"), '
        ':has-text("ver más"), '
        ':has-text("Mostrar más comentarios")'
    )

    REPLY_SELECTOR = (
        ':has-text("Ver más respuestas"), '
        ':has-text("Ver respuestas"), '
        ':has-text("View more replies"), '
        ':has-text("View replies")'
    )

    def __init__(
        self,
        page,
        max_comments: int = 100,
        delay: float = 1.5,
    ):
        self.page = page
        self.max_comments = max_comments
        self.delay = delay

    # ---------- button / post detection ----------

    async def find_all_comment_buttons(self) -> list:
        """Find visible links page-wide that open post modals.

        Searches the entire page for ``/posts/``, ``/photo/``, and ``/video/``
        links, returning only visible ones.  These are matched to posts by DOM
        order (both are interleaved in the same order on the page).
        """
        links = []
        for sel in self.BUTTON_SELECTORS:
            try:
                all_els = await self.page.locator(sel).all()
                for el in all_els:
                    try:
                        if await el.is_visible():
                            links.append(el)
                    except Exception:
                        logger.debug("Button visibility check failed", exc_info=True)
                        continue
            except Exception:
                logger.debug("find_all_comment_buttons locator failed", exc_info=True)
                continue
        return links

    async def find_all_post_elements(self) -> list:
        """Find all post container elements in the page."""
        try:
            return await self.page.locator(self.POST_SELECTOR).all()
        except Exception:
            logger.debug("find_all_post_elements failed", exc_info=True)
            return []

    async def find_comment_button(self, post_idx: int) -> object | None:
        """Get clickable element for post at ``post_idx``.

        1. Page-wide visible links (matched by DOM order)
        2. Falls back to the post container element
        """
        buttons = await self.find_all_comment_buttons()
        if post_idx < len(buttons):
            return buttons[post_idx]

        posts = await self.find_all_post_elements()
        if post_idx < len(posts):
            logger.debug("Fallback: clicking post element for post %d", post_idx)
            return posts[post_idx]

        return None

    # ---------- modal detection ----------

    async def find_modal(self) -> object | None:
        """Find the FIRST visible modal dialog.

        Waits up to 5 seconds, polling every 500ms.
        Picks the first visible ``[role="dialog"]``, skipping hidden ones.
        """
        for _ in range(10):
            try:
                all_dialogs = await self.page.locator('[role="dialog"]').all()
                for d in all_dialogs:
                    try:
                        if await d.is_visible():
                            logger.debug("Found visible modal dialog")
                            return d
                    except Exception:
                        logger.debug("Modal visibility check failed", exc_info=True)
                        continue
            except Exception:
                logger.debug("Modal dialog locator failed", exc_info=True)
            await asyncio.sleep(0.5)
        logger.debug("No visible modal found after waiting")
        return None

    async def close_modal(self) -> None:
        """Close the comments modal by pressing Escape."""
        try:
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            logger.debug("Modal closed via Escape")
        except Exception as e:
            logger.debug("Failed to close modal: %s", e)

    # ---------- extraction inside container ----------

    async def find_comment_elements_in(self, container) -> list:
        """Find comment elements inside a container (modal or page section)."""
        try:
            loc = container.locator(self.COMMENT_SELECTOR)
            elements = []
            count = await loc.count()
            for i in range(count):
                try:
                    if await loc.nth(i).is_visible():
                        elements.append(loc.nth(i))
                except Exception:
                    logger.debug("Comment element visibility failed", exc_info=True)
                    continue
            return elements
        except Exception:
            logger.debug("find_comment_elements_in failed", exc_info=True)
            return []

    async def find_more_buttons_in(self, container) -> list:
        """Find 'Ver más comentarios' buttons inside a container."""
        try:
            loc = container.locator(self.MORE_SELECTOR)
            buttons = []
            count = await loc.count()
            for i in range(count):
                try:
                    if await loc.nth(i).is_visible():
                        buttons.append(loc.nth(i))
                except Exception:
                    logger.debug("More-button visibility failed", exc_info=True)
                    continue
            return buttons
        except Exception:
            logger.debug("find_more_buttons_in failed", exc_info=True)
            return []

    async def _find_reply_buttons_in(self, container) -> list:
        """Find 'Ver más respuestas' buttons inside a container."""
        try:
            loc = container.locator(self.REPLY_SELECTOR)
            buttons = []
            count = await loc.count()
            for i in range(count):
                try:
                    if await loc.nth(i).is_visible():
                        buttons.append(loc.nth(i))
                except Exception:
                    logger.debug("Reply-button visibility failed", exc_info=True)
                    continue
            return buttons
        except Exception:
            logger.debug("_find_reply_buttons_in failed", exc_info=True)
            return []

    async def expand_and_extract(self, container) -> list[Comment]:
        """Inside a container: expand comments, extract, return list."""
        all_comments = []
        seen_texts = set()
        attempt = 0

        for attempt in range(12):
            if len(all_comments) >= self.max_comments:
                break

            # Find and parse current visible comments
            elements = await self.find_comment_elements_in(container)
            for el in elements:
                if len(all_comments) >= self.max_comments:
                    break
                comment = await self._parse_element(el)
                if comment and comment["text"] not in seen_texts:
                    seen_texts.add(comment["text"])
                    all_comments.append(comment)

            # Scroll inside container to trigger lazy loading
            try:
                await container.evaluate("el => el.scrollTop = el.scrollHeight")
                await asyncio.sleep(0.3)
            except Exception:
                logger.debug("Container scroll failed", exc_info=True)

            # Find "Ver más" buttons AND reply buttons
            more = await self.find_more_buttons_in(container)
            replies = await self._find_reply_buttons_in(container)
            all_buttons = more + replies

            if not all_buttons:
                # One more scroll + retry
                try:
                    await container.evaluate("el => el.scrollTop = el.scrollHeight")
                    await asyncio.sleep(0.5)
                except Exception:
                    logger.debug("Retry scroll failed", exc_info=True)
                all_buttons = more + await self._find_reply_buttons_in(container)

            if not all_buttons:
                logger.debug("No more buttons to click (round %d)", attempt + 1)
                break

            for btn in all_buttons:
                try:
                    await btn.scroll_into_view_if_needed()
                    await btn.click(force=True)
                    await asyncio.sleep(self.delay * 0.7)
                except Exception:
                    logger.debug("Click on expand button failed", exc_info=True)
                    continue

            await asyncio.sleep(self.delay)

        logger.info(
            "Extracted %d comments from container (%d rounds)",
            len(all_comments),
            min(attempt + 1, 5),
        )
        return self._to_objects(all_comments[: self.max_comments])

    # ---------- parse ----------

    async def _parse_element(self, element) -> dict | None:
        """Parse a comment DOM element into a structured dict."""
        try:
            text = await element.inner_text()
        except Exception:
            logger.debug("inner_text failed on comment element", exc_info=True)
            return None
        if not text or len(text.strip()) < 5:
            return None

        aria = ""
        try:
            aria = await element.get_attribute("aria-label") or ""
        except Exception:
            logger.debug("aria-label read failed", exc_info=True)
            pass

        author = ""
        time_str = ""
        match = re.search(r"Comentario de (.+?) (?:hace|ago|·)", aria, re.IGNORECASE)
        if match:
            author = match.group(1).strip()
            time_m = re.search(r"(hace .+)", aria, re.IGNORECASE)
            if time_m:
                time_str = time_m.group(1).strip()

        if not author:
            try:
                link = element.locator("a").first
                if await link.count() > 0:
                    author = (await link.inner_text()).strip()
            except Exception:
                logger.debug("Author link read failed", exc_info=True)

        likes = 0
        try:
            inner = await element.inner_html()
            lm = re.search(r"(\d+)\s*(?:Me gusta|Like|likes)", inner, re.IGNORECASE)
            if lm:
                likes = int(lm.group(1))
        except Exception:
            logger.debug("Likes regex failed", exc_info=True)

        # Strip the author prefix and trailing UI bits so the body
        # stored in ``text`` is clean and the metadata lands in the
        # dedicated columns (``time_ago`` and ``responses``).
        clean_body, time_ago, responses = clean_comment_text(
            text.strip(), known_author=author or None
        )
        clean_body = self._clean(clean_body)

        return {
            "text": clean_body,
            "author": author,
            "date": time_str,
            "likes": likes,
            "time_ago": time_ago,
            "responses": responses,
        }

    @staticmethod
    def _clean(text: str) -> str:
        """Remove Facebook scramble: single chars separated by spaces.

        Uses threshold 10 to avoid eating real short-word comments.
        """
        cleaned = re.sub(r"(?:\s+[a-zA-Z0-9]\s*){10,}", " ", text)
        return re.sub(r"\s+", " ", cleaned).strip()

    # ---------- per-post flow ----------

    async def _click_with_retry(self, btn, post_idx: int) -> bool:
        """Click a button with exponential backoff retry.

        Returns True if the click succeeded, False otherwise.
        """
        for attempt in range(3):
            try:
                tag = await btn.evaluate("el => el.tagName")
                if tag == "A":
                    await btn.scroll_into_view_if_needed()
                await btn.click(force=True)
                return True
            except Exception as e:
                wait = 1 * (2**attempt)  # 1s, 2s, 4s
                logger.warning(
                    "Click failed for post %d (attempt %d/3), retrying in %ds: %s",
                    post_idx,
                    attempt + 1,
                    wait,
                    e,
                )
                await asyncio.sleep(wait)
        return False

    async def extract_comments_for_post(self, post_idx: int) -> list[Comment]:
        """Full per-post flow: click button → modal → extract → close.

        Args:
            post_idx: Index of the post

        Returns:
            List of Comment objects extracted from the modal
        """
        btn = await self.find_comment_button(post_idx)
        if btn is None:
            logger.debug("No clickable element for post %d", post_idx)
            return []

        if not await self._click_with_retry(btn, post_idx):
            return []

        await asyncio.sleep(self.delay)

        modal = await self.find_modal()
        if modal is None:
            logger.debug("No modal appeared after clicking post %d", post_idx)
            # Fallback: extract from page directly
            elements = await self.find_comment_elements_in(self.page)
            if elements:
                logger.info("Fallback: found %d comment elements in page", len(elements))
                return await self.expand_and_extract(self.page)
            return []

        comments = await self.expand_and_extract(modal)

        await self.close_modal()
        await asyncio.sleep(0.5)

        return comments

    # ---------- page-wide flow ----------

    async def extract_all_visible_comments(self) -> list[Comment]:
        """Extract comments visible directly in the page (no modal).

        Used when comments are already expanded inline (not in a modal).
        """
        elements = await self.find_comment_elements_in(self.page)
        if not elements:
            logger.info("No inline comment elements found in page")
            return []

        logger.info("Found %d inline comment elements", len(elements))
        return await self.expand_and_extract(self.page)

    # ---------- converter ----------

    @staticmethod
    def _to_objects(raw: list[dict]) -> list[Comment]:
        """Convert raw dicts to Comment models."""
        comments = []
        for i, item in enumerate(raw):
            cid = hashlib.md5(
                f"{item.get('author', '')}_{item.get('text', '')[:50]}_{i}".encode()
            ).hexdigest()[:16]
            comments.append(
                Comment(
                    id=cid,
                    text=item.get("text", ""),
                    author=item.get("author", ""),
                    date=None,
                    likes=item.get("likes", 0),
                    url="",
                    time_ago=item.get("time_ago"),
                    responses=item.get("responses", 0),
                )
            )
        return comments
