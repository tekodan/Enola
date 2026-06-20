"""Integration test for Facebook scraper with preprocessing."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from src.scraper.facebook import FacebookScraper


@pytest.mark.asyncio
async def test_scraper_with_preprocessing():
    """Test scraper uses preprocessing."""
    scraper = FacebookScraper(max_posts=2, max_comments=5)

    # Mock HTML response
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

    # Mock ChromiumLoader to return our HTML
    with patch('scrapegraphai.docloaders.chromium.ChromiumLoader') as MockLoader:
        mock_doc = Mock()
        mock_doc.page_content = mock_html
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [mock_doc]
        MockLoader.return_value = mock_loader_instance

        # Mock SmartScraperGraph to return structured response
        with patch('scrapegraphai.graphs.SmartScraperGraph') as MockGraph:
            mock_graph_instance = Mock()
            mock_graph_instance.run.return_value = {
                "content": '{"posts": [{"text": "Publicación de prueba 1", "author": "Usuario Test", "date": "2024-01-15", "likes": 42, "comments_count": 5, "shares": 2, "url": "https://facebook.com/test1"}, {"text": "Publicación de prueba 2", "author": "Usuario Test 2", "date": "2024-01-16", "likes": 0, "comments_count": 0, "shares": 0, "url": "https://facebook.com/test2"}]}'
            }
            MockGraph.return_value = mock_graph_instance

            # Test scrape_page
            posts = await scraper.scrape_page("https://www.facebook.com/test")

            # Verify preprocessing was called (loader should have been called)
            assert MockLoader.called
            assert MockGraph.called

            # Verify posts parsed (might be 1 or 2 depending on parsing)
            assert len(posts) > 0
            if len(posts) >= 1:
                assert posts[0].text == "Publicación de prueba 1"
                assert posts[0].author == "Usuario Test"


@pytest.mark.asyncio
async def test_scraper_fallback_to_original():
    """Test scraper falls back to original method when preprocessing fails."""
    scraper = FacebookScraper(max_posts=2)

    # Mock ChromiumLoader to raise exception (simulating preprocessing failure)
    with patch('scrapegraphai.docloaders.chromium.ChromiumLoader') as MockLoader:
        MockLoader.side_effect = Exception("Loader failed")

        # Mock original SmartScraperGraph to return response
        with patch('scrapegraphai.graphs.SmartScraperGraph') as MockGraph:
            mock_graph_instance = Mock()
            mock_graph_instance.run.return_value = {
                "content": '{"posts": [{"text": "Fallback post", "author": "Fallback Author", "date": "2024-01-15", "likes": 0, "comments_count": 0, "shares": 0, "url": "https://facebook.com/fallback"}]}'
            }
            MockGraph.return_value = mock_graph_instance

            # Test scrape_page - should fallback
            posts = await scraper.scrape_page("https://www.facebook.com/test")

            # Verify fallback was used (original graph called)
            assert MockGraph.called
            assert len(posts) == 1
            assert posts[0].text == "Fallback post"


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_scraper_with_preprocessing())
    print("✓ test_scraper_with_preprocessing passed")

    asyncio.run(test_scraper_fallback_to_original())
    print("✓ test_scraper_fallback_to_original passed")
