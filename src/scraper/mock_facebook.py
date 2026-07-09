"""Mock Facebook scraper for testing pipeline without real Facebook access."""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.scraper.facebook import FacebookScraper
from src.scraper.models import Comment, Post, ScrapeResult

logger = logging.getLogger(__name__)


class MockFacebookScraper(FacebookScraper):
    """Mock scraper that uses fixture data instead of real Facebook."""

    def __init__(self, use_mock_data: bool = True, *args, **kwargs):
        """Initialize mock scraper.

        Args:
            use_mock_data: If True, use fixture data; if False, fall back to parent
        """
        super().__init__(*args, **kwargs)
        self.use_mock_data = use_mock_data
        self._load_fixtures()

    def _load_fixtures(self):
        """Load fixture data from tests/fixtures/."""
        fixtures_path = Path(__file__).parent.parent.parent / "tests" / "fixtures"

        self.mock_posts = []
        self.mock_comments = []

        try:
            # Load posts sample
            posts_file = fixtures_path / "posts_sample.json"
            if posts_file.exists():
                with open(posts_file, encoding="utf-8") as f:
                    posts_data = json.load(f)
                    for post_data in posts_data:
                        post = Post(
                            id=post_data.get("id", ""),
                            text=post_data.get("text", ""),
                            author=post_data.get("author", ""),
                            date=datetime.fromisoformat(post_data.get("date", "2024-01-01")),
                            likes=post_data.get("likes", 0),
                            comments_count=post_data.get("comments_count", 0),
                            shares=post_data.get("shares", 0),
                            url=post_data.get("url", ""),
                        )
                        self.mock_posts.append(post)

                logger.info("Loaded %d mock posts", len(self.mock_posts))

            # Load Facebook pages for seed data
            pages_file = fixtures_path / "facebook_pages.json"
            if pages_file.exists():
                with open(pages_file, encoding="utf-8") as f:
                    self.mock_pages = json.load(f)
                    logger.info("Loaded %d mock pages", len(self.mock_pages))

        except Exception as e:
            logger.warning("Failed to load fixtures: %s", e)

    async def scrape_page(self, page_url: str) -> list[Post]:
        """Mock implementation that returns fixture posts."""
        if not self.use_mock_data:
            return await super().scrape_page(page_url)

        logger.info("Using mock data for %s", page_url)

        # Return all mock posts or filter by URL pattern
        posts_to_return = self.mock_posts[: self.max_posts]

        # Simulate processing delay
        import asyncio

        await asyncio.sleep(0.1)

        logger.info("Mock scraped %d posts from %s", len(posts_to_return), page_url)
        return posts_to_return

    async def scrape_comments(self, post_url: str, post_id: str = "") -> list[Comment]:
        """Mock implementation that returns fixture comments."""
        if not self.use_mock_data:
            return await super().scrape_comments(post_url, post_id)

        logger.info("Using mock comments for %s", post_url)

        # Create mock comments for the post
        comments = []
        for i in range(min(5, self.max_comments)):
            comment = Comment(
                id=f"comment_{post_id}_{i}",
                text=f"Comentario de prueba {i} para el post {post_id}",
                author=f"Usuario Mock {i}",
                date=datetime.now(),
                likes=i * 2,
                post_id=post_id,
                url=f"{post_url}#comment_{i}",
            )
            comments.append(comment)

        # Simulate processing delay
        import asyncio

        await asyncio.sleep(0.05)

        logger.info("Mock scraped %d comments from %s", len(comments), post_url)
        return comments

    async def scrape_full(self, page_url: str) -> ScrapeResult:
        """Mock implementation combining posts and comments."""
        if not self.use_mock_data:
            return await super().scrape_full(page_url)

        result = ScrapeResult(success=True)

        try:
            posts = await self.scrape_page(page_url)
            result.posts.extend(posts)
            result.posts_found = len(posts)

            for i, post in enumerate(posts):
                if i > 0:
                    import asyncio

                    await asyncio.sleep(self.delay * 0.5)

                comments = await self.scrape_comments(post.url or "", post.id)
                result.comments.extend(comments)

            result.comments_found = len(result.comments)
            result.pages_scraped = 1

        except Exception as e:
            result.success = False
            result.add_error(str(e))

        return result

    async def scrape_post(self, post_url: str) -> list[Post]:
        """Mock implementation that returns fixture posts for a single post URL."""
        if not self.use_mock_data:
            return await super().scrape_post(post_url)
        return await self.scrape_page(post_url)

    def scrape_post_sync(self, post_url: str) -> list[Post]:
        """Synchronous mock version for a single post."""
        if not self.use_mock_data:
            return super().scrape_post_sync(post_url)
        return self.scrape_page_sync(post_url)

    async def scrape_reel(self, reel_url: str) -> list[Post]:
        """Mock implementation that returns fixture posts for a reel URL."""
        if not self.use_mock_data:
            return await super().scrape_reel(reel_url)
        return await self.scrape_page(reel_url)

    def scrape_reel_sync(self, reel_url: str) -> list[Post]:
        """Synchronous mock version for a reel."""
        if not self.use_mock_data:
            return super().scrape_reel_sync(reel_url)
        return self.scrape_page_sync(reel_url)

    def scrape_page_sync(self, page_url: str) -> list[Post]:
        """Synchronous mock version."""
        if not self.use_mock_data:
            return super().scrape_page_sync(page_url)

        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.scrape_page(page_url))

    def scrape_comments_sync(self, post_url: str, post_id: str = "") -> list[Comment]:
        """Synchronous mock version."""
        if not self.use_mock_data:
            return super().scrape_comments_sync(post_url, post_id)

        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.scrape_comments(post_url, post_id))

    def scrape_full_sync(self, page_url: str) -> ScrapeResult:
        """Synchronous mock version."""
        if not self.use_mock_data:
            return super().scrape_full_sync(page_url)

        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.scrape_full(page_url))
