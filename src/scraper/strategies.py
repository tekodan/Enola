"""Extraction strategies for Facebook scraping.

Provides a strategy pattern for extracting posts and comments from Facebook.
Allows switching between DOM-based extraction and LLM-based extraction
without changing the scraper's core logic.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.scraper.facebook_preprocessor import FacebookPreprocessor
from src.scraper.models import Comment, Post


class ExtractionStrategy(ABC):
    """Abstract base class for extraction strategies."""

    @abstractmethod
    async def extract_posts(self, html: str, page_url: str, max_posts: int) -> list[Post]:
        """Extract posts from the given HTML.

        Args:
            html: Raw HTML content
            page_url: URL of the page being scraped
            max_posts: Maximum number of posts to extract

        Returns:
            List of Post objects
        """
        ...

    @abstractmethod
    async def extract_comments(self, html: str, post_url: str, max_comments: int) -> list[Comment]:
        """Extract comments from the given HTML.

        Args:
            html: Raw HTML content
            post_url: URL of the post
            max_comments: Maximum number of comments to extract

        Returns:
            List of Comment objects
        """
        ...


class DOMExtractionStrategy(ExtractionStrategy):
    """Extract posts and comments using DOM-based heuristics.

    Fast and cheap — does not require LLM calls.
    """

    async def extract_posts(self, html: str, page_url: str, max_posts: int) -> list[Post]:
        """Extract posts using FacebookPreprocessor."""
        raw_posts = FacebookPreprocessor.extract_posts(html, page_url)
        posts: list[Post] = []
        for idx, item in enumerate(raw_posts[:max_posts]):
            posts.append(
                Post(
                    id=_generate_id(page_url, item, idx),
                    text=item.get("text", ""),
                    author=item.get("author", ""),
                    likes=item.get("likes", 0),
                    comments_count=item.get("comments_count", 0),
                    shares=item.get("shares", 0),
                    url=item.get("url", ""),
                )
            )
        return posts

    async def extract_comments(self, html: str, post_url: str, max_comments: int) -> list[Comment]:
        """Extract comments using FacebookPreprocessor."""
        raw_comments = FacebookPreprocessor.extract_comments(html, post_url)
        comments: list[Comment] = []
        for idx, item in enumerate(raw_comments[:max_comments]):
            comments.append(
                Comment(
                    id=_generate_id(post_url, item, idx),
                    text=item.get("text", ""),
                    author=item.get("author", ""),
                    likes=item.get("likes", 0),
                    url=item.get("url", ""),
                )
            )
        return comments


class LLMExtractionStrategy(ExtractionStrategy):
    """Extract posts and comments using an LLM (placeholder for future use).

    Currently delegates to DOMExtractionStrategy as fallback.
    Can be extended to use SmartScraperGraph directly.
    """

    def __init__(self) -> None:
        self._fallback = DOMExtractionStrategy()

    async def extract_posts(self, html: str, page_url: str, max_posts: int) -> list[Post]:
        """Extract posts using LLM (fallback to DOM for now)."""
        return await self._fallback.extract_posts(html, page_url, max_posts)

    async def extract_comments(self, html: str, post_url: str, max_comments: int) -> list[Comment]:
        """Extract comments using LLM (fallback to DOM for now)."""
        return await self._fallback.extract_comments(html, post_url, max_comments)


def _generate_id(base_url: str, item: dict[str, Any], idx: int) -> str:
    """Generate a deterministic ID from URL and item content."""
    import hashlib

    text = item.get("text", "")[:50]
    content = f"{base_url}_{item.get('author', '')}_{item.get('date', '')}_{text}_{idx}"
    return hashlib.md5(content.encode()).hexdigest()[:16]
