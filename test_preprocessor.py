"""Integration test for Facebook preprocessor."""

import pytest

from src.scraper.facebook_preprocessor import FacebookPreprocessor


def test_preprocessor_extracts_hierarchy():
    """Test that preprocessor creates hierarchical structure."""
    # Sample Facebook-like HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Facebook - Juan Pérez</title>
        <meta property="og:title" content="Publicación de Juan Pérez">
        <meta property="og:description" content="Esta es una publicación de prueba">
    </head>
    <body>
        <div data-testid="post_message">
            <p>Este es el texto de una publicación de prueba en Facebook.</p>
            <a href="/juan.perez">Juan Pérez</a>
            <time datetime="2024-01-15T10:30:00Z">15 de enero de 2024</time>
            <div>
                <span>42 reacciones</span>
                <span>5 comentarios</span>
                <span>2 compartidos</span>
            </div>
        </div>
        <div data-testid="comment">
            <p>Este es un comentario de prueba.</p>
            <a href="/maria.gomez">María Gómez</a>
            <time datetime="2024-01-15T11:00:00Z">15 de enero de 2024</time>
            <span>3 Likes</span>
        </div>
    </body>
    </html>
    """

    url = "https://www.facebook.com/share/1bgM59UnFE/"

    # Test page metadata extraction
    page_meta = FacebookPreprocessor.extract_page_metadata(html, url)
    assert "title" in page_meta
    assert "url" in page_meta
    assert page_meta["url"] == url

    # Test post extraction
    posts = FacebookPreprocessor.extract_posts(html, url)
    assert len(posts) > 0
    if posts:
        post = posts[0]
        assert "text" in post
        assert "author" in post
        assert "date" in post
        assert "likes" in post
        assert "comments_count" in post
        assert "shares" in post
        assert "url" in post

    # Test comment extraction
    comments = FacebookPreprocessor.extract_comments(html, url)
    assert len(comments) > 0
    if comments:
        comment = comments[0]
        assert "text" in comment
        assert "author" in comment
        assert "date" in comment
        assert "likes" in comment
        assert "url" in comment

    # Test hierarchical JSON creation
    hierarchical = FacebookPreprocessor.create_hierarchical_json(html, url)
    assert "page" in hierarchical
    assert "posts" in hierarchical
    assert isinstance(hierarchical["posts"], list)


def test_preprocess_for_llm():
    """Test that preprocessor creates readable text for LLM."""
    html = """
    <html>
    <body>
        <div data-testid="post_message">
            <p>Publicación de prueba.</p>
        </div>
    </body>
    </html>
    """

    url = "https://www.facebook.com/test"
    result = FacebookPreprocessor.preprocess_for_llm(html, url)

    assert isinstance(result, str)
    assert len(result) > 0
    assert "PÁGINA:" in result
    assert "PUBLICACIÓN" in result


def test_reduce_html_size():
    """Test HTML size reduction."""
    # Create large HTML with unnecessary elements
    html = "<html><head>" + "<script>console.log('test');</script>" * 100 + "<style>body { color: red; }</style>" * 10 + "</head><body><p>Contenido útil</p></body></html>"

    reduced = FacebookPreprocessor.reduce_html_size(html, max_chars=1000)
    assert len(reduced) <= 1000
    assert "<script>" not in reduced
    assert "<style>" not in reduced
    assert "Contenido útil" in reduced


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
