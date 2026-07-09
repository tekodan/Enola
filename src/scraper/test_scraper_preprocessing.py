"""Integration test for Facebook scraper with preprocessing."""

from unittest.mock import AsyncMock, patch

import pytest

from src.scraper.facebook import FacebookScraper
from src.scraper.models import ContentSource


@pytest.mark.asyncio
async def test_scraper_uses_preprocessing():
    """Test scraper extracts posts via DOM preprocessor when HTML contains posts."""
    scraper = FacebookScraper(max_posts=2, max_comments=5)

    mock_html = """
    <html>
    <head>
        <title>Facebook - Test Page</title>
    </head>
    <body>
        <div data-testid="post_message">
            <p>Publicación de prueba 1.</p>
            <a href="/test.user">Usuario Test</a>
            <time datetime="2024-01-15T10:30:00Z">15 de enero de 2024</time>
        </div>
        <div data-testid="post_message">
            <p>Publicación de prueba 2.</p>
            <a href="/test.user2">Usuario Test 2</a>
            <time datetime="2024-01-16T11:30:00Z">16 de enero de 2024</time>
        </div>
    </body>
    </html>
    """

    # Mock _fetch_html_cached to return our HTML (bypasses Playwright + cache)
    with patch.object(scraper, "_fetch_html_cached", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_html

        # Test scrape_page — should use preprocessor, not fall back to LLM
        posts = await scraper.scrape_page("https://www.facebook.com/test")

        assert mock_fetch.called
        # Verify posts parsed via preprocessor (not LLM fallback)
        assert len(posts) >= 1
        if len(posts) >= 1:
            assert "prueba 1" in posts[0].text or "Publicación" in posts[0].text


@pytest.mark.asyncio
async def test_scraper_fallback_to_llm():
    """Test scraper falls back to LLM when preprocessor finds no posts."""
    scraper = FacebookScraper(max_posts=2)

    # Mock _fetch_html_cached to return HTML without any post markers
    with patch.object(scraper, "_fetch_html_cached", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "<html><body><p>No posts here</p></body></html>"

        # Mock the graph runner to return structured response directly
        with patch.object(scraper, "_run_graph", new_callable=AsyncMock) as mock_run_graph:
            mock_run_graph.return_value = (
                '{"posts": [{"text": "Fallback post", "author": "Fallback Author", '
                '"date": "2024-01-15", "likes": 0, "comments_count": 0, '
                '"shares": 0, "url": "https://facebook.com/fallback"}]}'
            )

            # Test scrape_page — should fallback
            posts = await scraper.scrape_page("https://www.facebook.com/test")

            # Verify fallback was used
            assert mock_run_graph.called
            assert len(posts) == 1
            assert posts[0].text == "Fallback post"


@pytest.mark.asyncio
async def test_scrape_post_extracts_single_post():
    """Test scrape_post extracts a single post from HTML and marks source."""
    scraper = FacebookScraper(max_posts=1, max_comments=5)

    mock_html = """
    <html>
    <head><title>Facebook - Post</title></head>
    <body>
        <div data-testid="post_message">
            <p>Texto del post individual.</p>
            <a href="/autor.test">Autor Test</a>
            <time datetime="2024-03-10T18:00:00Z">10 de marzo de 2024</time>
        </div>
    </body>
    </html>
    """

    with patch.object(scraper, "_fetch_html_cached", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_html

        with patch.object(scraper, "scrape_comments", new_callable=AsyncMock) as mock_comments:
            mock_comments.return_value = []

            posts = await scraper.scrape_post("https://www.facebook.com/page/posts/123")

            assert len(posts) == 1
            assert "post individual" in posts[0].text.lower()
            assert posts[0].source == ContentSource.FACEBOOK_POST


@pytest.mark.asyncio
async def test_scrape_reel_routes_to_post_extractor():
    """Test scrape_reel delegates to the same extraction flow and marks source."""
    scraper = FacebookScraper(max_posts=1, max_comments=5)

    mock_html = """
    <html>
    <head><title>Facebook - Reel</title></head>
    <body>
        <div data-testid="post_message">
            <p>Texto del reel.</p>
            <a href="/autor.reel">Autor Reel</a>
            <time datetime="2024-04-20T12:00:00Z">20 de abril de 2024</time>
        </div>
    </body>
    </html>
    """

    with patch.object(scraper, "_fetch_html_cached", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_html

        with patch.object(scraper, "scrape_comments", new_callable=AsyncMock) as mock_comments:
            mock_comments.return_value = []

            posts = await scraper.scrape_reel("https://www.facebook.com/reel/123456")

            assert len(posts) == 1
            assert "reel" in posts[0].text.lower()
            assert posts[0].source == ContentSource.FACEBOOK_POST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
