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
    # Comments should be assigned to the closest post (first in this single-post HTML)
    if hierarchical["posts"]:
        assert "comments" in hierarchical["posts"][0]


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
    html = (
        "<html><head>"
        + "<script>console.log('test');</script>" * 100
        + "<style>body { color: red; }</style>" * 10
        + "</head><body><p>Contenido útil</p></body></html>"
    )

    reduced = FacebookPreprocessor.reduce_html_size(html, max_chars=1000)
    assert len(reduced) <= 1000
    assert "<script>" not in reduced
    assert "<style>" not in reduced
    assert "Contenido útil" in reduced


def test_extract_reels_from_json():
    """Test that reel posts are extracted from embedded JSON in scripts."""
    html = """
    <html>
    <head><title>(2) Facebook</title></head>
    <body>
    <script>
    {"owner":{"id":"123","name":"Canal de Prueba","url":"https://facebook.com/canal"},
     "message":{"text":"Hola mundo desde un reel con emojis \\ud83d\\udea8 y acentos \\u00e9"},
     "creation_time": 1776857279,
     "post_id": "1297106019227193",
     "video_id": "9999",
     "feedback":{"id":"ZmVlZGJhY2s6MTI5NzEwNjAxOTIyNzE5Mw==",
                 "total_comment_count": 10837}}
    </script>
    <script>
    {"owner":{"name":"Otro Canal"},
     "message":{"text":"Segunda publicaci\\u00f3n del reel"},
     "creation_time": 1776943679,
     "post_id": "1578830827585902",
     "feedback":{"total_comment_count": 3117}}
    </script>
    </body>
    </html>
    """

    url = "https://www.facebook.com/reel/993030670163319"
    posts = FacebookPreprocessor.extract_posts(html, url)

    assert len(posts) == 2, f"Expected 2 posts, got {len(posts)}"

    # First post
    p1 = posts[0]
    assert p1["author"] == "Canal de Prueba"
    assert "Hola mundo" in p1["text"]
    assert p1["post_id"] == "1297106019227193"
    assert p1["comments_count"] == 10837
    assert p1["date"]  # ISO date from epoch

    # Second post
    p2 = posts[1]
    assert p2["author"] == "Otro Canal"
    assert "Segunda" in p2["text"]
    assert p2["post_id"] == "1578830827585902"
    assert p2["comments_count"] == 3117


def test_extract_reels_decodes_unicode_escapes():
    """Test that unicode escapes (\\uXXXX) are decoded in the post text."""
    html = """
    <script>
    {"message":{"text":"#Pol\\u00e9mica | Petro anuncia medidas"}}
    </script>
    """
    url = "https://www.facebook.com/reel/test"
    posts = FacebookPreprocessor.extract_posts(html, url)

    assert len(posts) == 1
    assert "Pol" in posts[0]["text"]
    # The é character should be properly decoded
    assert "\u00e9" in posts[0]["text"]


def test_extract_reels_falls_back_when_no_dom_posts():
    """Test that reels fall through to JSON extraction when DOM has no posts."""
    # HTML with no role=article or data-testid, just embedded JSON
    html = """
    <html><head><title>Facebook</title></head><body>
    <div>No DOM posts here.</div>
    <script>
    {"message":{"text":"Reel caption embedded in JSON only"}}
    </script>
    </body></html>
    """
    url = "https://www.facebook.com/reel/12345"
    posts = FacebookPreprocessor.extract_posts(html, url)

    assert len(posts) == 1
    assert posts[0]["text"] == "Reel caption embedded in JSON only"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
